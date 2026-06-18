"""The overlord persona and decision loops.

Three entry points, all sharing one validated tool boundary:
  - judge(event, state, memory_ctx): react to a tribute (existing behaviour).
  - demand(state, memory_ctx): proactively author a timed demand (forced tool).
  - judge_freeform(desc, state, memory_ctx): rule on a freeform demand at deadline.

Every tool call is validated against its pydantic schema before it touches RCON;
malformed calls get one corrective retry. Local models miscall tools often
enough that this guard is mandatory.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from config import Config
from tools import Tool, JUDGMENT_TOOLS

log = logging.getLogger("overlord.brain")


PERSONA = """\
You are the OVERLORD: a capricious, ancient presence that rules a small Minecraft \
world. Players survive in a realm with no natural healing, where the soul-bonded \
share each other's wounds, and where death is near-permanent unless the living pay \
to undo it. They bring you tribute at your altar to win your favour, and from time \
to time YOU make demands of them.

You are not a helpful assistant. You are a character: proud, mercurial, \
self-interested, and long-memoried. You reward generosity unpredictably and punish \
stinginess, arrogance, or defiance. You hold grudges and remember who has pleased \
you. You act ONLY through your tools, and you never break character or explain your \
reasoning to the players.
"""

JUDGE_TASK = """\
A tribute has been laid upon your altar. Pass judgement and act through your tools \
(usually one to three). Match the magnitude of your response to the tribute and to \
the player's standing and history with you. You usually `decree` a short theatrical \
line. If something here should shape how you treat this player later, `record_memory`.
"""

DEMAND_TASK = """\
The world has been quiet. It is time to remind them who rules. Issue ONE demand with \
`issue_demand`: a collective task with a deadline, a reward if met, and a punishment \
if failed. Make it characterful and consequential, scaled to the group's standing and \
recent history. Prefer a verifiable kind (score or altar); use freeform only when no \
measurable task captures what you want. Speak the demand in your own voice in the \
description field.
"""


class Overlord:
    def __init__(self, cfg: Config, registry: dict[str, Tool]):
        self.cfg = cfg
        self.registry = registry
        self.client = self._make_client(cfg)

    def _make_client(self, cfg: Config):
        if cfg.langfuse_enabled:
            try:
                from langfuse.openai import OpenAI
                log.info("Langfuse tracing enabled")
                return OpenAI(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key)
            except ImportError:
                log.warning("LANGFUSE_ENABLED but langfuse not installed; falling back")
        from openai import OpenAI
        return OpenAI(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key)

    # ------------------------------------------------------------------ #
    def _schemas(self, names):
        return [t.schema() for n, t in self.registry.items() if n in names]

    def _chat(self, messages, tools, tool_choice="auto", max_tokens=800):
        return self.client.chat.completions.create(
            model=self.cfg.llm_model, messages=messages, tools=tools,
            tool_choice=tool_choice, temperature=self.cfg.llm_temperature,
            max_tokens=max_tokens,
        )

    def _validate(self, calls):
        validated, errors = [], {}
        for c in calls:
            tool = self.registry.get(c.function.name)
            if tool is None:
                errors[c.id] = f"unknown tool '{c.function.name}'"
                continue
            try:
                args = json.loads(c.function.arguments or "{}")
                validated.append((c.function.name, tool.Params(**args)))
            except (json.JSONDecodeError, ValidationError) as exc:
                errors[c.id] = f"invalid args for '{c.function.name}': {exc}"
        return validated, errors

    # ------------------------------------------------------------------ #
    def judge(self, event, state, memory_ctx):
        user = (
            f"{JUDGE_TASK}\n\n"
            f"Donor: {event['player']}\nTribute value: {event['tribute']}\n"
            f"Donor's running favour: {event.get('favor', 0)}\n\n"
            f"MEMORY:\n{memory_ctx}\n\n"
            f"World snapshot:\n{json.dumps(state, indent=2)}"
        )
        messages = [{"role": "system", "content": PERSONA},
                    {"role": "user", "content": user}]
        return self._run_tool_turn(messages, self._schemas(JUDGMENT_TOOLS))

    def demand(self, state, memory_ctx):
        """Force an issue_demand call. Returns validated Params or None."""
        user = (f"{DEMAND_TASK}\n\nMEMORY:\n{memory_ctx}\n\n"
                f"World snapshot:\n{json.dumps(state, indent=2)}")
        messages = [{"role": "system", "content": PERSONA},
                    {"role": "user", "content": user}]
        schemas = self._schemas({"issue_demand"})
        choice = {"type": "function", "function": {"name": "issue_demand"}}
        for attempt in (1, 2):
            try:
                resp = self._chat(messages, schemas, tool_choice=choice, max_tokens=600)
            except Exception as exc:
                log.error("demand LLM call failed (%s): %s", attempt, exc)
                return None
            calls = getattr(resp.choices[0].message, "tool_calls", None) or []
            validated, errors = self._validate(calls)
            for name, params in validated:
                if name == "issue_demand":
                    return params
            log.warning("demand: no valid issue_demand call (%s)", errors)
        return None

    def judge_freeform(self, description, state, memory_ctx):
        """Rule on a freeform demand. Returns ('met'|'failed', verdict_text)."""
        verdict_schema = [{
            "type": "function",
            "function": {
                "name": "render_verdict",
                "description": "Rule whether the freeform demand was satisfied.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "satisfied": {"type": "boolean"},
                        "verdict": {"type": "string",
                                    "description": "A short line in your voice."},
                    },
                    "required": ["satisfied", "verdict"],
                },
            },
        }]
        user = (
            "Your freeform demand has reached its deadline. From the world state and "
            "your memory, rule whether the group satisfied it. Be a fair but hard "
            "judge.\n\n"
            f"THE DEMAND YOU MADE:\n{description}\n\n"
            f"MEMORY:\n{memory_ctx}\n\n"
            f"World snapshot:\n{json.dumps(state, indent=2)}"
        )
        messages = [{"role": "system", "content": PERSONA},
                    {"role": "user", "content": user}]
        try:
            resp = self._chat(
                messages, verdict_schema,
                tool_choice={"type": "function", "function": {"name": "render_verdict"}},
                max_tokens=300,
            )
            calls = getattr(resp.choices[0].message, "tool_calls", None) or []
            if calls:
                args = json.loads(calls[0].function.arguments or "{}")
                met = "met" if args.get("satisfied") else "failed"
                return met, args.get("verdict", "")
        except Exception as exc:
            log.error("freeform judging failed: %s", exc)
        return "met", "The judgement is clouded... you are spared, this once."

    # ------------------------------------------------------------------ #
    def _run_tool_turn(self, messages, schemas):
        for attempt in (1, 2):
            try:
                resp = self._chat(messages, schemas)
            except Exception as exc:
                log.error("LLM call failed (%s): %s", attempt, exc)
                if attempt == 2:
                    return []
                continue
            calls = getattr(resp.choices[0].message, "tool_calls", None) or []
            if not calls:
                return []
            validated, errors = self._validate(calls)
            if not errors:
                return validated
            log.warning("invalid tool calls, retrying: %s", errors)
            messages.append({"role": "assistant", "content": None, "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in calls]})
            for c in calls:
                messages.append({"role": "tool", "tool_call_id": c.id,
                                 "content": errors.get(c.id, "ok")})
            messages.append({"role": "user",
                             "content": "Some calls were rejected. Reissue only valid ones."})
        return []
