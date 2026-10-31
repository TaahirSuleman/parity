"""The auditor agent loop (spec docs/19 §18.3).

One model loop: Spark computer use plus the gated function tools. The whole conversation is
persisted per turn (screenshots as files), so a run can be inspected or branched later.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from playwright.async_api import Page

from parity.agent.tools import AgentState, dispatch, screen_key, tool_definitions
from parity.flows import Flow
from parity.meta.client import text_of
from parity.meta.images import png_to_data_url
from parity.pipeline.actions import execute, is_allowed_target, settle
from parity.pipeline.audit import RunContext, audit_view
from parity.pipeline.guard import CHALLENGE_PROBES, Blocked, challenge_reason, guard_action

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parent.parent / "meta" / "prompts"
PROMPT_TOOLS = (PROMPTS / "auditor.md").read_text()
PROMPT_FALLBACK = (PROMPTS / "auditor_fallback.md").read_text()
LAST_TURN_NOTICE = "\n\nThis is your last turn. Call finish with a one-sentence summary of where the flow stands."
NUDGE = "Plain text is not accepted. Call audit_view for an unaudited screen, use the computer tool to continue, or call finish."
AgentMode = Literal["tools", "fallback"]
# Spark attaches this code to every batch. On our own store it is acknowledged as routine; in public mode it is acknowledged
# because the read-only guard screens every action first; any other code stops the run.
ROUTINE_SAFETY_CODES = {"computer_action_requires_confirmation"}


class InspectionFailed(RuntimeError):
    """The element under an action could not be read; in public mode the action is refused rather than guessed at."""


@dataclass
class AgentResult:
    turns: int
    finished: bool
    finish_forced: bool
    summary: str


class _Conversation:
    """Persists every turn; screenshots are written once by hash under runs/<id>/agent/."""

    def __init__(self, ctx: RunContext, mode: str):
        self.ctx = ctx
        self.turns: list[dict[str, Any]] = []
        self.mode = mode
        self._written: set[str] = set()

    async def _strip(self, items: Any) -> Any:
        if isinstance(items, dict):
            if isinstance(items.get("image_url"), str) and items["image_url"].startswith("data:image"):
                sha = await self._store(items["image_url"])
                return {**items, "image_url": f"png:{sha}"}
            return {k: await self._strip(v) for k, v in items.items()}
        if isinstance(items, list):
            return [await self._strip(i) for i in items]
        return items

    async def _store(self, data_url: str) -> str:
        import base64

        png = base64.b64decode(data_url.split(",", 1)[1])
        sha = hashlib.sha256(png).hexdigest()[:16]
        if sha not in self._written:
            await self.ctx.bundle.store.put(f"runs/{self.ctx.run.id}/agent/{sha}.png", png, "image/png")
            self._written.add(sha)
        return sha

    async def record(self, turn: int, request_id: str, response_id: str, input_items: Any, output_items: Any, tools: list[str]) -> None:
        self.turns.append({
            "turn": turn, "request_id": request_id, "response_id": response_id, "tools": tools,
            "input": await self._strip(input_items), "output": await self._strip(output_items),
        })
        payload = {"run_id": self.ctx.run.id, "mode": self.mode, "turns": self.turns}
        await self.ctx.bundle.store.put(f"runs/{self.ctx.run.id}/agent/conversation.json", json.dumps(payload, indent=1).encode(), "application/json")


_TARGET_JS = """([x, y, kind]) => {
  const el = kind === "click" || kind === "double_click" ? document.elementFromPoint(x, y) : document.activeElement;
  if (!el || el === document.body) return null;
  const ctl = el.closest("button, a, input, select, textarea, summary, label, iframe, [onclick], [role=button], [role=link], [role=menuitem], [role=tab], [role=checkbox], [role=switch], [tabindex]") || el;
  const attr = (n, a) => (n.getAttribute && n.getAttribute(a)) || "";
  // Every source a name can come from, not the one the accessible-name algorithm would pick: a title beside visible text,
  // aria-labelledby pointing elsewhere, split text in an onclick div, an image's alt. Any of them matching is enough to refuse.
  const sources = [attr(ctl, "aria-label"), attr(ctl, "title"), attr(ctl, "value"), (ctl.innerText || ctl.textContent || "")];
  for (const id of attr(ctl, "aria-labelledby").split(/\\s+/).filter(Boolean)) { const n = document.getElementById(id); if (n) sources.push(n.textContent || ""); }
  if (ctl.querySelectorAll) for (const img of ctl.querySelectorAll("img[alt], [aria-label], [title]")) sources.push(attr(img, "alt"), attr(img, "aria-label"), attr(img, "title"));
  const name = Array.from(new Set(sources.map(s => s.replace(/\\s+/g, " ").trim()).filter(Boolean))).join(" | ");
  const type = [attr(ctl, "type"), attr(ctl, "autocomplete")].join(" ").trim() || null;
  const submits = !!(ctl.form && (ctl.type === "submit" || ctl.tagName === "BUTTON" && !ctl.getAttribute("type")));
  return { tag: ctl.tagName.toLowerCase(), role: attr(ctl, "role") || ctl.tagName.toLowerCase(), name: name.slice(0, 300), type, submits };
}"""


async def inspect_target(page: Page, action: dict[str, Any]):
    """The element an action would land on, for the public-site guard: (AxNode-ish, field type tokens, submits?).
    Raises InspectionFailed when the page cannot be read: the guard then refuses rather than guesses."""
    from parity.store.models import AxNode

    try:
        info = await page.evaluate(_TARGET_JS, [action.get("x", 0), action.get("y", 0), str(action.get("type") or "")])
    except Exception as exc:
        raise InspectionFailed(f"the element under the action could not be inspected: {type(exc).__name__}") from exc
    if not info:
        return None, None, False
    field_type = (info.get("type") or "").lower() or None
    node = AxNode(backend_id=0, role=str(info.get("role") or ""), name=str(info.get("name") or ""))
    return node, field_type, bool(info.get("submits"))


_WALL_JS = """(probes) => {
  const visible = (n) => { const r = n.getBoundingClientRect(); const cs = getComputedStyle(n); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none"; };
  return { title: document.title || "", markers: probes.filter(sel => { try { return Array.from(document.querySelectorAll(sel)).some(visible) || (sel.startsWith("#") && !!document.querySelector(sel)); } catch (e) { return false; } }) };
}"""


async def wall_reason(page: Page) -> str | None:
    """'blocked by site: …' when the current screen is a CAPTCHA, bot challenge or login wall (spec §17), else None."""
    try:
        info = await page.evaluate(_WALL_JS, list(CHALLENGE_PROBES))
    except Exception:
        return None
    return challenge_reason(str(info.get("title") or ""), page.url, list(info.get("markers") or []))


async def _audit_if_new(ctx: RunContext, state: AgentState, page: Page, reason: str) -> None:
    key = await screen_key(page)
    if key in state.audited:
        return
    summary = await audit_view(ctx, page, state.step_count, reason)
    state.step_count += 1
    state.audited[key] = {"screen": key, "verified": [b.__dict__ for b in summary.verified], "rejected": summary.rejected, "axe_violations": summary.axe_violations}


async def run_agent(ctx: RunContext, page: Page, flow: Flow, max_turns: int = 12, mode: AgentMode = "tools") -> AgentResult:
    state = AgentState()
    ctx.agent = state
    ctx.page = page
    settings, run = ctx.settings, ctx.run
    model = settings.model_for("navigator")
    tool_names = ["audit_view", "finish"] if mode == "tools" else []
    full_tools: list[dict[str, Any]] = [{"type": "computer"}, *tool_definitions(tool_names)]
    conversation = _Conversation(ctx, mode)
    if ctx.public and (wall := await wall_reason(page)):
        await ctx.emit("nav.blocked", {"turn": 0, "url": page.url, "reason": wall})
        state.summary = wall
        return AgentResult(0, False, False, wall)  # never bypassed, never audited, never sent to the model
    if mode == "fallback":
        await _audit_if_new(ctx, state, page, "first screen")
    input_items: list[dict[str, Any]] = [{"role": "user", "content": [
        {"type": "input_text", "text": flow.goal},
        {"type": "input_image", "image_url": png_to_data_url(await page.screenshot())},
    ]}]
    previous: str | None = None
    turns = 0
    for turn in range(1, max_turns + 1):
        state.turn = turn
        last = turn == max_turns
        tools = tool_definitions(["finish"]) if (last and mode == "tools") else full_tools
        if last and mode == "tools":
            # Only finish is offered now; its precondition must be satisfiable, so code audits the current screen.
            await _audit_if_new(ctx, state, page, "last turn: audited by code before finish")
        instructions = PROMPT_TOOLS if mode == "tools" else PROMPT_FALLBACK
        if last and mode == "tools":
            # The notice rides in the instructions: a chained request must answer the pending tool call with its output
            # alone; mixing a new user message into that input is rejected by the API (seen live: HTTP 400 on turn 12).
            instructions += LAST_TURN_NOTICE
        body: dict[str, Any] = {
            "model": model, "tools": tools, "reasoning": {"effort": "low"}, "truncation": "auto", "parallel_tool_calls": False,
            "instructions": instructions, "input": input_items,
        }
        if previous:
            body["previous_response_id"] = previous
        resp = await ctx.client.responses(body, stage="auditor", run_id=run.id)
        turns = turn
        previous = resp.response_id or previous
        items = resp.raw.get("output") or []
        outputs: list[dict[str, Any]] = []
        text_reply = text_of(resp.raw).strip()
        paused: str | None = None
        try:  # whatever happens below, the turn is recorded: the conversation is the debugging trail
            for item in items:
                kind = item.get("type")
                if kind == "computer_call":
                    actions = item.get("actions") or ([item["action"]] if item.get("action") else [])
                    safety = item.get("pending_safety_checks") or []
                    if safety:
                        # Spark attaches computer_action_requires_confirmation to every batch: a routine "confirm to
                        # proceed" that code acknowledges on the demo store we own. Any other code, or a page off the
                        # store, is treated as the provider's injection signal: nothing is executed and the run stops.
                        codes = [c.get("code") for c in safety if isinstance(c, dict)]
                        on_store = page.url.startswith(ctx.base_url.rstrip("/") + "/")
                        if on_store and set(codes) <= ROUTINE_SAFETY_CODES:
                            reason = "routine confirmation; the public-site guard screens each action before it runs" if ctx.public else "routine confirmation on the demo store"
                            await ctx.emit("nav.safety_check", {"turn": turn, "codes": codes, "acknowledged": True, "reason": reason})
                        else:
                            await ctx.emit("nav.blocked", {"turn": turn, "reason": "the model raised a safety check; the batch was not executed", "safety_codes": codes, "url": page.url})
                            state.summary = f"stopped: safety check {codes} raised by the model; no action was taken"
                            return AgentResult(turns, False, False, state.summary)
                    executed = dropped = 0
                    off_origin = False
                    for action in actions:
                        if ctx.public:
                            try:
                                target, field_type, submits = await inspect_target(page, action)
                                verdict = guard_action(action, target, field_type, submits=submits)
                            except InspectionFailed as exc:
                                verdict = Blocked(f"{exc}; refused rather than guessed")
                            if isinstance(verdict, Blocked):
                                await ctx.emit("nav.blocked", {"turn": turn, "action": action.get("type"), "url": page.url, "reason": f"stopped before irreversible step: {verdict.reason}"})
                                state.summary = f"stopped before irreversible step: {verdict.reason}"
                                return AgentResult(turns, False, False, state.summary)
                        if await execute(page, action):
                            executed += 1
                        else:
                            dropped += 1
                            await ctx.emit("nav.blocked", {"turn": turn, "action": action.get("type"), "detail": {k: v for k, v in action.items() if k != "type"}, "reason": "action refused by the allow-listed executor"})
                        if not is_allowed_target(page.url, settings, ctx.base_url):
                            off_origin = True
                            break  # the rest of the batch (typing, clicks) must not land on an external page
                    await settle(page)
                    await ctx.emit("nav.actions", {"turn": turn, "actions": [a.get("type") for a in actions], "n": len(actions), "executed": executed, "dropped": dropped,
                                                   "safety_checks": len(safety), "safety_codes": [c.get("code") for c in safety if isinstance(c, dict)]})
                    if off_origin or not is_allowed_target(page.url, settings, ctx.base_url):
                        await ctx.emit("nav.blocked", {"turn": turn, "url": page.url, "reason": "navigated outside the allowed origins"})
                        state.summary = f"stopped: the page navigated to {page.url}, outside the allowed origins"
                        return AgentResult(turns, False, False, state.summary)  # recorded by the finally below
                    if ctx.public and (wall := await wall_reason(page)):
                        await ctx.emit("nav.blocked", {"turn": turn, "url": page.url, "reason": wall})
                        state.summary = wall
                        return AgentResult(turns, False, False, wall)
                    outputs.append({
                        "type": "computer_call_output", "call_id": item.get("call_id"),
                        "acknowledged_safety_checks": item.get("pending_safety_checks", []),
                        "output": {"type": "computer_screenshot", "image_url": png_to_data_url(await page.screenshot())},
                    })
                    if mode == "fallback":
                        await _audit_if_new(ctx, state, page, f"screen changed after turn {turn}")
                elif kind == "function_call":
                    result = await dispatch(ctx, item)
                    args = item.get("arguments")
                    try:
                        args = json.loads(args) if isinstance(args, str) else args
                    except (json.JSONDecodeError, TypeError):
                        pass
                    if "error" in result and result.get("kind") == "tool_error":
                        await ctx.emit("agent.tool_error", {"turn": turn, "tool": item.get("name"), "args": args, "error": result["error"]})
                    elif "error" in result:
                        await ctx.emit("agent.refused", {"turn": turn, "tool": item.get("name"), "args": args, "feedback": result.get("feedback") or result["error"]})
                    else:
                        await ctx.emit("agent.tool_call", {"turn": turn, "tool": item.get("name"), "args": args, "result": result})
                    outputs.append({"type": "function_call_output", "call_id": item.get("call_id"), "output": json.dumps(result)})
                    if result.get("status") == "paused":
                        paused = result["error"]
        finally:
            await conversation.record(turn, resp.request_id, resp.response_id, input_items, items, [t.get("name", t["type"]) for t in tools])
        if paused:
            raise RuntimeError(f"paused: {paused}")
        if state.finished:
            break
        if not outputs:
            if mode == "fallback":
                await _audit_if_new(ctx, state, page, "final screen")
                state.finished, state.summary = True, text_reply
                break
            input_items = [{"role": "user", "content": [{"type": "input_text", "text": NUDGE}]}]
            continue
        input_items = outputs
    await ctx.bundle.flush(run.id)
    return AgentResult(turns, state.finished, state.finish_forced, state.summary or text_reply)


def result_dict(result: AgentResult) -> dict[str, Any]:
    return asdict(result)
