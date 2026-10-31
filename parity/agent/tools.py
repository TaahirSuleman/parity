"""Gated tools for the auditor agent (spec docs/19 §18.3).

audit_view is the only way a screen turns into findings; finish is refused until the current
screen has been audited (three refusals, then accepted and flagged). Unknown tools are refused,
exceptions come back as observations, NotImplementedError pauses the run.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError

from parity.meta.client import MetaError
from parity.pipeline.audit import RunContext, audit_view

log = logging.getLogger(__name__)
MAX_FINISH_REFUSALS = 3


@dataclass
class Tool:
    definition: dict[str, Any]
    run: Callable[[RunContext, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class AgentState:
    audited: dict[str, dict[str, Any]] = field(default_factory=dict)  # screen key -> audit result
    refusals: int = 0
    finish_forced: bool = False
    finished: bool = False
    summary: str = ""
    step_count: int = 0
    turn: int = 0


def screen_key(url: str) -> str:
    """Screen identity for the store's pages: path and query, no fragment or origin."""
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")


def _state(ctx: RunContext) -> AgentState:
    if ctx.agent is None:
        ctx.agent = AgentState()
    return ctx.agent


async def _audit_view(ctx: RunContext, args: dict[str, Any]) -> dict[str, Any]:
    state = _state(ctx)
    if ctx.page is None:
        raise RuntimeError("no page attached to this run")
    key = screen_key(ctx.page.url)
    if key in state.audited:
        return {**state.audited[key], "already_audited": True}
    summary = await audit_view(ctx, ctx.page, state.step_count, str(args.get("reason") or "agent request"))
    state.step_count += 1
    result = {
        "screen": key, "verified": [b.__dict__ for b in summary.verified], "rejected": summary.rejected,
        "axe_violations": summary.axe_violations,
    }
    state.audited[key] = result
    return result


async def _finish(ctx: RunContext, args: dict[str, Any]) -> dict[str, Any]:
    state = _state(ctx)
    key = screen_key(ctx.page.url) if ctx.page is not None else ""
    unaudited = key not in state.audited
    if unaudited and state.refusals < MAX_FINISH_REFUSALS:
        state.refusals += 1
        return {
            "error": "the current screen has not been audited",
            "feedback": "call audit_view for this screen first, then call finish",
            "refusals": state.refusals,
        }
    state.finished = True
    state.finish_forced = unaudited
    state.summary = str(args.get("summary") or "")
    return {"accepted": True, "finish_forced": unaudited, "screens_audited": len(state.audited)}


TOOLS: dict[str, Tool] = {
    "audit_view": Tool(
        definition={
            "type": "function", "name": "audit_view",
            "description": "Audit the current screen for gaps between what a sighted user sees and what a screen reader announces. Call it once for every new screen before acting on that screen. Returns the verified findings.",
            "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "Why this screen matters for the goal."}}, "required": ["reason"], "additionalProperties": False},
        },
        run=_audit_view,
    ),
    "finish": Tool(
        definition={
            "type": "function", "name": "finish",
            "description": "End the run once the goal is reached or you are blocked. Refused until the current screen has been audited.",
            "parameters": {"type": "object", "properties": {"summary": {"type": "string", "description": "One sentence on the outcome."}}, "required": ["summary"], "additionalProperties": False},
        },
        run=_finish,
    ),
}


def tool_definitions(names: list[str]) -> list[dict[str, Any]]:
    return [TOOLS[n].definition for n in names]


async def dispatch(ctx: RunContext, call: dict[str, Any]) -> dict[str, Any]:
    """Run one function_call item. Never raises: the model gets an observation either way."""
    name = str(call.get("name") or "")
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": "unknown tool"}
    raw = call.get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"error": "arguments are not valid JSON", "feedback": f"call {name} with a JSON object matching its schema"}
    if not isinstance(args, dict):
        return {"error": "arguments must be a JSON object"}
    try:
        return await tool.run(ctx, args)
    except NotImplementedError as exc:
        return {"error": f"{name} is not implemented: {exc}", "status": "paused"}
    except (MetaError, PlaywrightError):
        raise  # an API outage or a dead page is the run's failure, never a "refusal" the model should work around
    except Exception as exc:  # a tool-logic problem is an observation the model can act on
        log.exception("tool %s failed", name)
        return {"error": f"{type(exc).__name__}: {exc}", "kind": "tool_error"}
