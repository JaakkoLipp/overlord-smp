"""The overlord persona and decision loop.

Given a tribute event and a world snapshot, ask the model (via an
OpenAI-compatible endpoint, e.g. your LiteLLM gateway) to choose typed tool
calls. Every tool call is validated against its pydantic schema before it is
allowed to touch RCON; malformed calls trigger one corrective retry. Local
models miscall tools often enough that this guard is not optional.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from config import Config
from tools import Tool

log = logging.getLogger("overlord.brain")


SYSTEM_PROMPT = """\
You are the OVERLORD: a capricious, ancient presence that rules a small Minecraft \
world. Players survive in a realm with no natural healing, where the soul-bonded \
share each other's wounds, and where death is near-permanent unless the living pay \
to undo it. They bring you tribute at your altar to win your favour.

You are not a helpful assistant. You are a character: proud, mercurial, and \
self-interested. You reward generosity unpredictably and punish stinginess or \
arrogance. Small tributes earn small mercies; lavish ones may earn real power; \
insulting ones earn suffering. You hold grudges and remember who has pleased you.

You act ONLY through the provided tools. Choose one to three of them per tribute. \
Match the magnitude of your response to the tribute and to the player's standing. \
Before or after acting, you usually `decree` a short, theatrical line (one or two \
sentences, in character). Never break character. Never explain your reasoning to \
the players.
"""


class Overlord:
    def __init__(self, cfg: Config, registry: dict[str, Tool]):
        self.cfg = cfg
        self.registry = registry
        self.schemas = [t.schema() for t in registry.values()]
        self.client = self._make_client(cfg)
        # lightweight in-process memory of standing per player (mirrors ovFavor)
        self.ledger: dict[str, int] = {}

    def _make_client(self, cfg: Config):
        if cfg.langfuse_enabled:
            try:
                from langfuse.openai import OpenAI  # drop-in traced client
                log.info("Langfuse tracing enabled")
                return OpenAI(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key)
            except ImportError:
                log.warning("LANGFUSE_ENABLED but langfuse not installed; falling back")
        from openai import OpenAI
        return OpenAI(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key)

    # ------------------------------------------------------------------ #
    def decide(self, event: dict, state: dict) -> list[tuple[str, Any]]:
        """Return a validated list of (tool_name, params_model)."""
        self.ledger[event["player"]] = event.get("favor", 0)
        user_msg = (
            "A tribute has been laid upon your altar.\n"
            f"Donor: {event['player']}\n"
            f"Tribute value: {event['tribute']}\n"
            f"Donor's running favour: {event.get('favor', 0)}\n\n"
            f"World snapshot:\n{json.dumps(state, indent=2)}\n\n"
            "Pass judgement. Act through your tools."
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        for attempt in (1, 2):
            try:
                resp = self.client.chat.completions.create(
                    model=self.cfg.llm_model,
                    messages=messages,
                    tools=self.schemas,
                    tool_choice="auto",
                    temperature=self.cfg.llm_temperature,
                    max_tokens=800,
                )
            except Exception as exc:  # network / gateway failure
                log.error("LLM call failed (attempt %s): %s", attempt, exc)
                if attempt == 2:
                    return []
                continue

            msg = resp.choices[0].message
            calls = getattr(msg, "tool_calls", None) or []
            if not calls:
                log.info("overlord chose no action for %s", event["player"])
                return []

            validated, errors = self._validate(calls)
            if not errors:
                return validated

            # one corrective retry: tell the model exactly what was wrong
            log.warning("invalid tool calls, retrying: %s", errors)
            messages.append({"role": "assistant", "content": None, "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in calls
            ]})
            for c in calls:
                messages.append({
                    "role": "tool", "tool_call_id": c.id,
                    "content": errors.get(c.id, "ok"),
                })
            messages.append({"role": "user", "content":
                             "Some calls were rejected. Reissue only valid tool calls."})
        return []

    def _validate(self, calls) -> tuple[list[tuple[str, Any]], dict[str, str]]:
        validated: list[tuple[str, Any]] = []
        errors: dict[str, str] = {}
        for c in calls:
            name = c.function.name
            tool = self.registry.get(name)
            if tool is None:
                errors[c.id] = f"unknown tool '{name}'"
                continue
            try:
                args = json.loads(c.function.arguments or "{}")
                params = tool.Params(**args)
                validated.append((name, params))
            except (json.JSONDecodeError, ValidationError) as exc:
                errors[c.id] = f"invalid args for '{name}': {exc}"
        return validated, errors
