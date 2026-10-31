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
    assert run.status == RunStatus.done, run.error
    assert page.url.endswith("confirm.html")
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
    assert loaded.run.findings_verified + loaded.run.findings_rejected >= 0 and len(loaded.steps) == 1


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
    assert run.status == RunStatus.done, run.error
    assert [s.url.rsplit("/", 1)[-1] for s in loaded.steps] == ["product.html", "cart.html", "checkout.html"]
    assert all(t["type"] == "computer" for call in auditor_calls(client) for t in call["tools"])
    result: AgentResult = AgentResult(**next(e for e in loaded.events if e.type == "run.finished").data["agent"])
    assert result.finished is True and result.finish_forced is False and "checkout" in result.summary
