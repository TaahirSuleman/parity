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

log = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parent.parent / "meta" / "prompts"
PROMPT_TOOLS = (PROMPTS / "auditor.md").read_text()
PROMPT_FALLBACK = (PROMPTS / "auditor_fallback.md").read_text()
NUDGE = "Plain text is not accepted. Call audit_view for an unaudited screen, use the computer tool to continue, or call finish."
AgentMode = Literal["tools", "fallback"]


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


async def _audit_if_new(ctx: RunContext, state: AgentState, page: Page, reason: str) -> None:
    key = screen_key(page.url)
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
        body: dict[str, Any] = {
            "model": model, "tools": tools, "reasoning": {"effort": "low"}, "truncation": "auto", "parallel_tool_calls": False,
            "instructions": PROMPT_TOOLS if mode == "tools" else PROMPT_FALLBACK, "input": input_items,
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
        for item in items:
            kind = item.get("type")
            if kind == "computer_call":
                actions = item.get("actions") or ([item["action"]] if item.get("action") else [])
                await ctx.emit("nav.actions", {"turn": turn, "actions": [a.get("type") for a in actions], "n": len(actions)})
                for action in actions:
                    await execute(page, action)
                await settle(page)
                if not is_allowed_target(page.url, settings, ctx.base_url):
                    await ctx.emit("nav.blocked", {"turn": turn, "url": page.url, "reason": "navigated outside the allowed origins"})
                    state.summary = f"stopped: the page navigated to {page.url}, outside the allowed origins"
                    await conversation.record(turn, resp.request_id, resp.response_id, input_items, items, [t.get("name", t["type"]) for t in tools])
                    return AgentResult(turns, False, False, state.summary)
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
                if "error" in result:
                    await ctx.emit("agent.refused", {"turn": turn, "tool": item.get("name"), "args": args, "feedback": result.get("feedback") or result["error"]})
                else:
                    await ctx.emit("agent.tool_call", {"turn": turn, "tool": item.get("name"), "args": args, "result": result})
                outputs.append({"type": "function_call_output", "call_id": item.get("call_id"), "output": json.dumps(result)})
                if result.get("status") == "paused":
                    paused = result["error"]
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
