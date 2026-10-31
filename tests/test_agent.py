"""The auditor agent, driven by scripted model turns against the real store pages."""

import contextlib
import json
from pathlib import Path

import pytest

from parity.agent.loop import AgentResult, run_agent
from parity.agent.tools import TOOLS, dispatch
from parity.api.events import EventBus
from parity.config import load_settings
from parity.flows import FLOWS
from parity.meta.client import TraceRouter
from parity.meta.fake import FakeMetaClient
from parity.pipeline.audit import RunContext
from parity.pipeline.runner import run_flow
from parity.store.blob import LocalBlobStore
from parity.store.bundle import RunBundle
from parity.store.index import RunIndex
from parity.store.models import RunStatus
from tests.test_runner import stage_defaults

META = Path(__file__).parent / "fixtures" / "meta"


def auditor_calls(client) -> list[dict]:
    """The agent's own requests; seer, comparator and judge calls interleave in client.calls."""
    return [c for c in client.calls if "tools" in c]


def function_call(name: str, args: dict, call_id: str) -> dict:
    return {"type": "function_call", "name": name, "call_id": call_id, "arguments": json.dumps(args)}


def computer_call(actions: list[dict], call_id: str) -> dict:
    return {"type": "computer_call", "call_id": call_id, "actions": actions, "pending_safety_checks": []}


def turn(*items: dict, text: str | None = None, rid: str = "resp") -> dict:
    output = list(items)
    if text:
        output.insert(0, {"type": "message", "content": [{"type": "output_text", "text": text}]})
    return {"id": rid, "_request_id": f"req-{rid}", "status": "completed", "output": output, "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}}


async def centre(page, url: str, selector: str) -> dict:
    await page.goto(url)
    box = await page.locator(selector).bounding_box()
    return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}


@contextlib.asynccontextmanager
async def harness(tmp_path, script, **kwargs):
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path / "data")})
    client = FakeMetaClient(META, trace=TraceRouter(), stage_defaults=stage_defaults(), script={"auditor": script}, **kwargs)
    bundle = RunBundle(LocalBlobStore(tmp_path / "data"))
    index = RunIndex(tmp_path / "index.db")
    await index.init()
    try:
        yield settings, client, EventBus(bundle), bundle, index
    finally:
        await index.close()


async def test_dispatch_unknown_tool_refused(tmp_path):
    settings = load_settings(env={"PARITY_DATA_DIR": str(tmp_path)})
    from tests.test_bundle import sample_run

    ctx = RunContext(settings=settings, client=None, bus=EventBus(), bundle=RunBundle(LocalBlobStore(tmp_path)), index=None, run=sample_run("r1"), base_url="http://x")
    assert await dispatch(ctx, {"name": "bogus", "arguments": "{}", "call_id": "c1"}) == {"error": "unknown tool"}
    assert "error" in await dispatch(ctx, {"name": "finish", "arguments": "not json", "call_id": "c2"})
    assert set(TOOLS) == {"audit_view", "finish"}
    assert all(t.definition["parameters"]["additionalProperties"] is False for t in TOOLS.values())


async def test_agent_fixture_flow_reaches_confirm(tmp_path, server_url, page):
    store = server_url + "/store/"
    add = await centre(page, store + "product.html", "#p4")
    checkout = await centre(page, store + "cart.html", "#k5")
    card = await centre(page, store + "checkout.html", "#card")
    pay = await centre(page, store + "checkout.html", "#f5")
    script = [
        turn(function_call("audit_view", {"reason": "product page"}, "c1"), text="Auditing the product page first."),
        turn(computer_call([{"type": "click", **add}], "c2")),
        turn(function_call("audit_view", {"reason": "cart"}, "c3")),
        turn(computer_call([{"type": "click", **checkout}], "c4")),
        turn(function_call("audit_view", {"reason": "checkout"}, "c5")),
        turn(computer_call([{"type": "click", **card}, {"type": "keypress", "keys": ["ctrl", "a"]}, {"type": "type", "text": "4111 1111 1111 1111"}, {"type": "click", **pay}], "c6")),
        turn(function_call("audit_view", {"reason": "confirmation"}, "c7")),
        turn(function_call("finish", {"summary": "Order confirmed"}, "c8")),
    ]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error  # awaiting review once a fix is proposed
    finished = next(e for e in loaded.events if e.type == "run.finished").data
    assert finished["final_url"].endswith("confirm.html")  # where the walk ended; re-audits move the page afterwards
    audited = [e.data["args"]["reason"] for e in loaded.events if e.type == "agent.tool_call" and e.data["tool"] == "audit_view"]
    assert audited == ["product page", "cart", "checkout", "confirmation"]
    assert [s.url.rsplit("/", 1)[-1] for s in loaded.steps] == ["product.html", "cart.html", "checkout.html", "confirm.html"]
    hero = [f for f in loaded.findings if f.element.dom_id == "f5"]
    assert len(hero) == 1 and hero[0].sr_name == "Submit" and hero[0].step_index == 2
    nav = [e for e in loaded.events if e.type == "nav.actions"]
    assert len(nav) == 3 and nav[2].data["actions"] == ["click", "keypress", "type", "click"]
    assert any(e.type == "agent.tool_call" and e.data["tool"] == "finish" and e.data["result"].get("accepted") for e in loaded.events)
    assert await bundle.store.exists(f"runs/{run.id}/agent/conversation.json")
    conversation = json.loads(await bundle.store.get(f"runs/{run.id}/agent/conversation.json"))
    assert len(conversation["turns"]) == 8 and conversation["turns"][1]["request_id"]
    assert "data:image" not in json.dumps(conversation)  # screenshots are stored as files, not inline
    agent_calls = auditor_calls(client)
    assert len(agent_calls) == 8 and agent_calls[0]["tools"][0] == {"type": "computer"} and agent_calls[0]["truncation"] == "auto"
    assert agent_calls[1]["previous_response_id"] == "resp" and agent_calls[0]["parallel_tool_calls"] is False


async def test_finish_refused_when_screen_unaudited(tmp_path, server_url, page):
    script = [
        turn(function_call("finish", {"summary": "done already"}, "c1")),
        turn(function_call("audit_view", {"reason": "product"}, "c2")),
        turn(function_call("finish", {"summary": "done"}, "c3")),
    ]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done
    refused = [e for e in loaded.events if e.type == "agent.refused"]
    assert len(refused) == 1 and "audit_view" in refused[0].data["feedback"]
    first_result = json.loads(auditor_calls(client)[1]["input"][0]["output"])
    assert "error" in first_result and "audit_view" in first_result["feedback"]
    assert len(loaded.steps) == 1  # the product page was audited once (its findings depend on the recorded checkout fixtures)
    assert len([e for e in loaded.events if e.type == "agent.tool_call" and e.data["tool"] == "audit_view"]) == 1


async def test_finish_forced_after_three_refusals(tmp_path, server_url, page):
    script = [turn(function_call("finish", {"summary": f"try {i}"}, f"c{i}")) for i in range(4)]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    refused = [e for e in loaded.events if e.type == "agent.refused"]
    accepted = [e for e in loaded.events if e.type == "agent.tool_call" and e.data["tool"] == "finish" and e.data["result"].get("accepted")]
    assert len(refused) == 3 and len(accepted) == 1 and accepted[0].data["result"]["finish_forced"] is True
    assert run.status == RunStatus.done and len(auditor_calls(client)) == 4


async def test_last_turn_offers_only_finish(tmp_path, server_url, page):
    script = [
        turn(function_call("audit_view", {"reason": "product"}, "c1")),
        turn(function_call("finish", {"summary": "out of turns"}, "c2")),
    ]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory, max_turns=2)
    assert run.status == RunStatus.done
    agent_calls = auditor_calls(client)
    assert [t.get("name", t["type"]) for t in agent_calls[0]["tools"]] == ["computer", "audit_view", "finish"]
    assert [t.get("name", t["type"]) for t in agent_calls[1]["tools"]] == ["finish"]


async def test_run_ends_when_turns_run_out(tmp_path, server_url, page):
    script = [turn(computer_call([{"type": "wait"}], f"c{i}")) for i in range(3)]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory, max_turns=3)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done and loaded.run.error is None
    finished = next(e for e in loaded.events if e.type == "run.finished")
    assert finished.data["agent"]["finished"] is False and finished.data["agent"]["turns"] == 3


async def test_fallback_mode_audits_on_screen_change(tmp_path, server_url, page):
    store = server_url + "/store/"
    add = await centre(page, store + "product.html", "#p4")
    checkout = await centre(page, store + "cart.html", "#k5")
    script = [
        turn(computer_call([{"type": "click", **add}], "c1")),
        turn(computer_call([{"type": "click", **checkout}], "c2")),
        turn(text="I am on the checkout page; the goal cannot be completed without a valid card."),
    ]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory, agent_mode="fallback")
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error  # awaiting review once a fix is proposed
    assert [s.url.rsplit("/", 1)[-1] for s in loaded.steps] == ["product.html", "cart.html", "checkout.html"]
    assert all(t["type"] == "computer" for call in auditor_calls(client) for t in call["tools"])
    result: AgentResult = AgentResult(**next(e for e in loaded.events if e.type == "run.finished").data["agent"])
    assert result.finished is True and result.finish_forced is False and "checkout" in result.summary


async def test_tool_infrastructure_error_fails_the_run(tmp_path, server_url, page):
    """A Meta API outage inside audit_view is not a refusal: the run must end failed with the error recorded."""
    from parity.meta.client import MetaError

    script = [turn(function_call("audit_view", {"reason": "product"}, "c1")), turn(function_call("finish", {"summary": "x"}, "c2"))]

    async def factory():
        return page

    err = MetaError("server_error", status=503, request_id="req-503", attempts=3)
    async with harness(tmp_path, script, errors={"comparator": err}) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.failed and "req-503" in (run.error or "")
    assert not [e for e in loaded.events if e.type == "agent.refused"]
    assert loaded.events[-1].type == "run.failed"


async def test_last_turn_audits_current_screen_before_finish(tmp_path, server_url, page):
    """finish is the only tool on the last turn; code audits the screen first so it is reachable."""
    store = server_url + "/store/"
    add = await centre(page, store + "product.html", "#p4")
    script = [turn(computer_call([{"type": "click", **add}], "c1")), turn(function_call("finish", {"summary": "done"}, "c2"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory, max_turns=2)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done
    assert [s.url.rsplit("/", 1)[-1] for s in loaded.steps] == ["cart.html"]
    finished = next(e for e in loaded.events if e.type == "run.finished")
    assert finished.data["agent"]["finished"] is True and finished.data["agent"]["finish_forced"] is False
    last_input = auditor_calls(client)[1]["input"]
    assert "last turn" in auditor_calls(client)[-1]["instructions"]  # the notice rides in the instructions, never as a second input item


async def test_dropped_and_bad_actions_do_not_crash_the_run(tmp_path, server_url, page):
    script = [
        turn(computer_call([{"type": "launch_missiles"}, {"type": "keypress", "keys": ["F99"]}, {"type": "wait"}], "c1")),
        turn(function_call("audit_view", {"reason": "product"}, "c2")),
        turn(function_call("finish", {"summary": "done"}, "c3")),
    ]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done, run.error
    blocked = [e for e in loaded.events if e.type == "nav.blocked"]
    assert len(blocked) == 2 and blocked[0].data["action"] == "launch_missiles" and "F99" in json.dumps(blocked[1].data)
    nav = next(e for e in loaded.events if e.type == "nav.actions")
    assert nav.data["executed"] == 1 and nav.data["dropped"] == 2 and nav.data["safety_checks"] == 0
    finished = next(e for e in loaded.events if e.type == "run.finished")
    assert finished.data["agent"]["finished"] is True


async def test_conversation_is_recorded_when_a_tool_raises(tmp_path, server_url, page):
    """A crash mid-turn must not lose the conversation: the recorded turns are the debugging trail."""
    from parity.meta.client import MetaError

    script = [turn(function_call("audit_view", {"reason": "product"}, "c1"))]

    async def factory():
        return page

    err = MetaError("server_error", status=503, request_id="req-503", attempts=3)
    async with harness(tmp_path, script, errors={"comparator": err}) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
    assert run.status == RunStatus.failed
    conv = json.loads((tmp_path / "data" / "runs" / run.id / "agent" / "conversation.json").read_text())
    assert [t["turn"] for t in conv["turns"]] == [1]
    assert conv["turns"][0]["output"][0]["name"] == "audit_view"


async def test_incomplete_empty_turn_is_nudged_not_fatal(tmp_path, server_url, page):
    """A turn that exhausted its output tokens (status incomplete, no output) gets the nudge and the run goes on."""
    from parity.agent.loop import NUDGE

    empty = {"id": "r0", "_request_id": "req-r0", "status": "incomplete", "output": [],
             "usage": {"input_tokens": 10, "output_tokens": 0, "total_tokens": 10}}
    script = [empty,
              turn(function_call("audit_view", {"reason": "product"}, "c1"), rid="r1"),
              turn(function_call("finish", {"summary": "audited the product page"}, "c2"), rid="r2")]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
    assert run.status == RunStatus.done, run.error
    calls = auditor_calls(client)
    assert len(calls) == 3
    assert NUDGE in json.dumps(calls[1]["input"])


async def test_off_origin_navigation_stops_the_run(tmp_path, server_url, page, monkeypatch):
    """Once an action lands outside the allowed origins the batch stops, nav.blocked is recorded and the run ends."""
    import parity.agent.loop as loop_mod

    seen = {"n": 0}

    def leaky(url, settings, base_url):
        seen["n"] += 1
        return seen["n"] < 2  # the check after the second action says: off-origin

    monkeypatch.setattr(loop_mod, "is_allowed_target", leaky)
    script = [turn(computer_call([{"type": "wait", "ms": 10}, {"type": "wait", "ms": 10}], "c1")), turn(function_call("finish", {"summary": "x"}, "c2"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    blocked = [e for e in loaded.events if e.type == "nav.blocked"]
    assert blocked and blocked[-1].data["reason"] == "navigated outside the allowed origins"
    assert len(auditor_calls(client)) == 1  # no further turn after the stop
    result = next(e for e in loaded.events if e.type == "run.finished").data["agent"]
    assert result["finished"] is False and result["summary"].startswith("stopped:")
    conv = json.loads((tmp_path / "data" / "runs" / run.id / "agent" / "conversation.json").read_text())
    assert [t["turn"] for t in conv["turns"]] == [1]


async def test_two_function_calls_in_one_turn_are_dispatched_in_order(tmp_path, server_url, page):
    script = [turn(function_call("audit_view", {"reason": "product"}, "c1"), function_call("finish", {"summary": "done"}, "c2"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error
    assert [e.data["tool"] for e in loaded.events if e.type == "agent.tool_call"] == ["audit_view", "finish"]
    assert len(auditor_calls(client)) == 1


async def test_audit_view_on_an_audited_screen_makes_no_new_model_calls(tmp_path, server_url, page):
    script = [turn(function_call("audit_view", {"reason": "first"}, "c1")), turn(function_call("audit_view", {"reason": "again"}, "c2")),
              turn(function_call("finish", {"summary": "done"}, "c3"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error
    assert len(loaded.steps) == 1  # the screen was captured once
    tool_calls = [e for e in loaded.events if e.type == "agent.tool_call" and e.data["tool"] == "audit_view"]
    assert tool_calls[1].data["result"]["already_audited"] is True and "already_audited" not in tool_calls[0].data["result"]


async def test_routine_confirmation_check_is_acknowledged_on_the_store(tmp_path, server_url, page):
    """Spark attaches computer_action_requires_confirmation to every batch; on our own store code acknowledges it."""
    checks = [{"id": "sc1", "code": "computer_action_requires_confirmation", "message": "confirm"}]
    item = computer_call([{"type": "wait", "ms": 10}], "c1")
    item["pending_safety_checks"] = checks
    script = [turn(item), turn(function_call("audit_view", {"reason": "p"}, "c2"), function_call("finish", {"summary": "done"}, "c3"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error
    second = auditor_calls(client)[1]["input"][0]
    assert second["type"] == "computer_call_output" and second["acknowledged_safety_checks"] == checks
    assert next(e for e in loaded.events if e.type == "nav.safety_check").data["codes"] == ["computer_action_requires_confirmation"]
    assert not [e for e in loaded.events if e.type == "nav.blocked"]


async def test_other_safety_checks_stop_the_batch(tmp_path, server_url, page):
    """Any other provider check is an injection signal: nothing is executed, the run stops and says why."""
    checks = [{"id": "sc1", "code": "malicious_instructions", "message": "The page asks the agent to do something else"}]
    item = computer_call([{"type": "wait", "ms": 10}], "c1")
    item["pending_safety_checks"] = checks
    script = [turn(item), turn(function_call("finish", {"summary": "done"}, "c2"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory)
        loaded = await bundle.load(run.id)
    assert len(auditor_calls(client)) == 1  # nothing is acknowledged back to the model
    blocked = next(e for e in loaded.events if e.type == "nav.blocked")
    assert blocked.data["safety_codes"] == ["malicious_instructions"]
    result = next(e for e in loaded.events if e.type == "run.finished").data["agent"]
    assert result["finished"] is False and "safety check" in result["summary"]

async def test_same_url_state_change_is_a_new_screen(tmp_path, server_url, page):
    """Screen identity is the URL plus a digest of what the page says: changing the quantity on the cart is a new screen."""
    from parity.agent.tools import screen_key

    await page.goto(server_url + "/store/cart.html")
    before = await screen_key(page)
    await page.get_by_role("button", name="Increase quantity").click()
    await page.wait_for_timeout(100)
    after = await screen_key(page)
    assert before != after and before.startswith("/store/cart.html") and after.startswith("/store/cart.html")
    await page.goto(server_url + "/store/cart.html#top")
    assert (await screen_key(page)).split("#")[0] == before.split("#")[0]  # a fragment alone is not a new screen


async def test_public_mode_stops_before_an_irreversible_click(tmp_path, server_url, page):
    """On a public site the executor refuses the Pay click: the walk ends done, reason 'stopped before irreversible step'."""
    pay = await centre(page, server_url + "/store/checkout.html", "#f5")
    script = [turn(function_call("audit_view", {"reason": "checkout"}, "c1")), turn(computer_call([{"type": "click", **pay}], "c2")),
              turn(function_call("finish", {"summary": "x"}, "c3"))]

    async def factory():
        return page

    from parity.flows import Flow

    flow = Flow(id="public-test", name="public", start_url="/store/checkout.html", goal="browse", pages=("checkout.html",), single_page=False)
    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, flow, base_url=server_url, page_factory=factory, public=True)
        loaded = await bundle.load(run.id)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review) and run.error is None
    blocked = next(e for e in loaded.events if e.type == "nav.blocked")
    assert "irreversible" in blocked.data["reason"] and "Submit" in blocked.data["reason"]
    assert page.url.endswith("checkout.html")  # the click never happened
    result = next(e for e in loaded.events if e.type == "run.finished").data["agent"]
    assert result["finished"] is False and "stopped before irreversible step" in result["summary"]
    assert len(auditor_calls(client)) == 2  # no third turn after the stop


async def test_public_mode_respects_robots(tmp_path, server_url, page, monkeypatch):
    import parity.pipeline.runner as runner_mod

    monkeypatch.setattr(runner_mod, "robots_allows", lambda url: False)
    script = [turn(function_call("finish", {"summary": "x"}, "c1"))]

    async def factory():
        return page

    from parity.flows import Flow

    flow = Flow(id="public-test", name="public", start_url="/store/product.html", goal="browse", pages=("product.html",), single_page=False)
    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, flow, base_url=server_url, page_factory=factory, public=True)
        loaded = await bundle.load(run.id)
    assert run.status == RunStatus.done and run.error is None
    assert not loaded.steps and not auditor_calls(client)  # nothing captured, no model call
    assert "robots.txt" in next(e for e in loaded.events if e.type == "nav.blocked").data["reason"]


async def test_last_turn_request_answers_the_pending_call_only(tmp_path, server_url, page):
    """A chained request may carry the tool output alone; the last-turn notice travels in the instructions (live 400 otherwise)."""
    script = [turn(function_call("audit_view", {"reason": "p"}, "c1")), turn(function_call("finish", {"summary": "done"}, "c2"))]

    async def factory():
        return page

    async with harness(tmp_path, script) as (settings, client, bus, bundle, index):
        run = await run_flow(settings, client, bus, bundle, index, FLOWS["purchase"], base_url=server_url, page_factory=factory, max_turns=2)
    assert run.status in (RunStatus.done, RunStatus.awaiting_review), run.error
    last = auditor_calls(client)[-1]
    assert [i.get("type") or i.get("role") for i in last["input"]] == ["function_call_output"]
    assert "last turn" in last["instructions"] and [t["name"] for t in last["tools"] if t.get("type") == "function"] == ["finish"]
