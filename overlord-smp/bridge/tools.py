"""Typed semantic tools = the safety boundary.

The model never emits a command string. It selects a tool and fills typed,
validated, clamped parameters; the tool body constructs the RCON command from
those validated fields. A valid-but-dumb target (cursing the wrong player) is
allowed -- that is a capricious god, which is the aesthetic. A catastrophic
command (/fill a million blocks, /kill @e, /stop) is simply not expressible,
because no tool is shaped like that.

Each tool exposes:
  - an OpenAI function-calling schema (for the model)
  - a pydantic params model (validation + clamping)
  - run(rcon, params) -> human-readable result (also handed back to the model)
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator

from config import Config
from rcon import RconClient

log = logging.getLogger("overlord.tools")


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _sanitize_player(name: str) -> str:
    # Player names are alnum + underscore; reject anything that could carry a
    # command separator or selector trickery into the constructed command.
    if not name or len(name) > 16 or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"invalid player name: {name!r}")
    return name


class Tool:
    name: str
    description: str
    Params: type[BaseModel]

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.Params.model_json_schema(),
            },
        }

    def run(self, rcon: RconClient, params: BaseModel) -> str:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Powers                                                                       #
# --------------------------------------------------------------------------- #
class Decree(Tool):
    name = "decree"
    description = "Speak to all players as the overlord. Pure flavour; no mechanical effect."

    class Params(BaseModel):
        message: str = Field(..., max_length=240)

    def run(self, rcon, p):
        text = p.message.replace('"', "'")
        return rcon.command(
            f'tellraw @a {{"text":"\\u00a7l[Overlord] \\u00a7r{text}","color":"dark_purple","italic":true}}'
        )


class _EffectTool(Tool):
    allow_attr: str  # "bless_effects" | "curse_effects"

    class Params(BaseModel):
        player: str
        effect: str
        amplifier: int = 0
        duration_seconds: int = 30

        @field_validator("player")
        @classmethod
        def _p(cls, v):
            return _sanitize_player(v)

    def run(self, rcon, p):
        allowed = getattr(self.cfg, self.allow_attr)
        eff = p.effect.removeprefix("minecraft:")
        if eff not in allowed:
            return f"refused: '{eff}' is not in the allow-list for {self.name}"
        amp = _clamp(p.amplifier, 0, self.cfg.max_amplifier)
        dur = _clamp(p.duration_seconds, 1, self.cfg.max_duration_s)
        return rcon.command(f"effect give {p.player} minecraft:{eff} {dur} {amp}")


class Bless(_EffectTool):
    name = "bless"
    description = "Grant a beneficial status effect to one player."
    allow_attr = "bless_effects"


class Curse(_EffectTool):
    name = "curse"
    description = "Inflict a harmful status effect on one player."
    allow_attr = "curse_effects"


class Mercy(Tool):
    name = "mercy"
    description = (
        "Grant temporary natural-style healing to one player by giving Regeneration. "
        "The world has no passive regen, so this is a real gift."
    )

    class Params(BaseModel):
        player: str
        duration_seconds: int = 20

        @field_validator("player")
        @classmethod
        def _p(cls, v):
            return _sanitize_player(v)

    def run(self, rcon, p):
        dur = _clamp(p.duration_seconds, 1, self.cfg.max_duration_s)
        return rcon.command(f"effect give {p.player} minecraft:regeneration {dur} 1")


class SummonThreat(Tool):
    name = "summon_threat"
    description = "Summon a small group of hostile mobs near one player as a trial."

    class Params(BaseModel):
        player: str
        mob: str
        count: int = 2

        @field_validator("player")
        @classmethod
        def _p(cls, v):
            return _sanitize_player(v)

    def run(self, rcon, p):
        mob = p.mob.removeprefix("minecraft:")
        if mob not in self.cfg.threat_mobs:
            return f"refused: '{mob}' is not in the threat allow-list"
        n = _clamp(p.count, 1, self.cfg.max_threat_count)
        out = []
        for _ in range(n):
            # spawn in a small ring around the player; magic/no-target so they aggro naturally
            out.append(rcon.command(
                f"execute as {p.player} at @s run summon minecraft:{mob} "
                f"^ ^ ^3"
            ))
        return f"summoned {n}x {mob} near {p.player}"


# --------------------------------------------------------------------------- #
# Dials (modulate our custom survival systems)                                #
# --------------------------------------------------------------------------- #
class TightenBonds(Tool):
    name = "set_soullink_coefficient"
    description = (
        "Set the soul-link bleed coefficient (percent of damage a bonded player "
        "transfers to their partner). Higher = crueller bonds."
    )

    class Params(BaseModel):
        percent: int

    def run(self, rcon, p):
        v = _clamp(p.percent, self.cfg.coeff_min, self.cfg.coeff_max)
        rcon.command(f"scoreboard players set #coeff ovGlobal {v}")
        return f"soul-link coefficient set to {v}%"


class SetRevivalCost(Tool):
    name = "set_revival_cost"
    description = "Set the XP-level cost to revive a fallen player at the altar."

    class Params(BaseModel):
        levels: int

    def run(self, rcon, p):
        v = _clamp(p.levels, self.cfg.revival_min, self.cfg.revival_max)
        rcon.command(f"scoreboard players set #revivalXp ovGlobal {v}")
        return f"revival cost set to {v} levels"


class SetLinkRadius(Tool):
    name = "set_soullink_radius"
    description = (
        "Set the soul-link proximity radius in blocks (only meaningful in proximity "
        "mode). Shrinking it forces bonded players to scatter to avoid shared pain; "
        "widening it makes grouping up dangerous."
    )

    class Params(BaseModel):
        blocks: int

    def run(self, rcon, p):
        v = _clamp(p.blocks, self.cfg.link_radius_min, self.cfg.link_radius_max)
        rcon.command(f"scoreboard players set #linkRadius ovGlobal {v}")
        return f"soul-link radius set to {v} blocks"


# --------------------------------------------------------------------------- #
# Stakes: a reward/punishment is a deferred call to another (judgment) tool.   #
# Validated structurally here; fully validated + executed at resolution time.  #
# --------------------------------------------------------------------------- #
def _validate_stake(registry_names: set[str], stake: dict, label: str) -> dict:
    if not isinstance(stake, dict) or "tool" not in stake:
        raise ValueError(f"{label} must be an object with a 'tool' field")
    name = stake["tool"]
    if name not in registry_names:
        raise ValueError(f"{label} names unknown tool '{name}'")
    args = stake.get("args", {})
    if not isinstance(args, dict):
        raise ValueError(f"{label} args must be an object")
    return {"tool": name, "args": args}


# Tools that may NOT be used as a demand stake (no recursion / meta).
_STAKE_FORBIDDEN = {"issue_demand", "record_memory"}


class IssueDemand(Tool):
    name = "issue_demand"
    description = (
        "Issue a timed, collective demand to all players, enforced by a visible "
        "countdown. Choose how it is verified:\n"
        "  kind='score'    -> progress is measured on a vanilla scoreboard "
        "criterion (pick one from the allowed list), summed across the group.\n"
        "  kind='altar'    -> players must deliver `threshold` of an item (give its "
        "id, e.g. minecraft:diamond) onto the altar.\n"
        "  kind='freeform' -> any objective you describe in words; YOU will judge "
        "whether it was satisfied when the deadline expires.\n"
        "Provide a reward (fired if met) and a punishment (fired if failed), each as "
        "{tool, args} naming one of your other tools."
    )

    class Params(BaseModel):
        description: str = Field(..., max_length=240,
                                 description="The demand, in your voice, shown to players.")
        kind: str = Field(..., description="score | altar | freeform")
        threshold: int = Field(1, description="Target count (score/altar).")
        deadline_minutes: int = 10
        criterion: str | None = Field(None, description="Scoreboard criterion for kind=score.")
        item: str | None = Field(None, description="Item id for kind=altar, e.g. minecraft:diamond.")
        reward: dict = Field(..., description="{tool, args} fired if the demand is met.")
        punishment: dict = Field(..., description="{tool, args} fired if the demand fails.")

        @field_validator("kind")
        @classmethod
        def _k(cls, v):
            if v not in ("score", "altar", "freeform"):
                raise ValueError("kind must be score, altar, or freeform")
            return v

    def __init__(self, cfg: Config, registry_names: set[str]):
        super().__init__(cfg)
        self._names = registry_names - _STAKE_FORBIDDEN

    def validate_full(self, p: "IssueDemand.Params") -> dict:
        """Cross-field validation + clamping. Returns a normalized demand dict."""
        if p.kind == "score":
            if p.criterion not in self.cfg.demand_criteria:
                raise ValueError(f"criterion not allowed: {p.criterion!r}")
        if p.kind == "altar":
            if not p.item or not all(c.isalnum() or c in "_:" for c in p.item):
                raise ValueError(f"invalid item id: {p.item!r}")
        reward = _validate_stake(self._names, p.reward, "reward")
        punishment = _validate_stake(self._names, p.punishment, "punishment")
        kind_n = {"score": 0, "altar": 1, "freeform": 2}[p.kind]
        threshold = _clamp(p.threshold, 1, self.cfg.demand_threshold_max)
        minutes = _clamp(p.deadline_minutes, self.cfg.demand_deadline_min,
                         self.cfg.demand_deadline_max)
        return {
            "description": p.description, "kind": p.kind, "kind_n": kind_n,
            "threshold": threshold, "seconds": minutes * 60,
            "criterion": p.criterion, "item": p.item,
            "reward": reward, "punishment": punishment,
        }


class RecordMemory(Tool):
    name = "record_memory"
    description = (
        "Record a salient memory to your chronicle: a grudge, a debt owed to you, a "
        "promise, or something to remember about a player. Use sparingly, for things "
        "that should shape how you treat them later."
    )

    class Params(BaseModel):
        note: str = Field(..., max_length=300)
        player: str | None = None

    def run(self, rcon, p):
        # Side effect is handled by the bridge (memory write); nothing to do in-world.
        return f"remembered: {p.note}"


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
def build_registry(cfg: Config) -> dict[str, Tool]:
    base = [
        Decree(cfg), Bless(cfg), Curse(cfg), Mercy(cfg), SummonThreat(cfg),
        TightenBonds(cfg), SetRevivalCost(cfg), SetLinkRadius(cfg),
        RecordMemory(cfg),
    ]
    names = {t.name for t in base} | {"issue_demand"}
    tools = base + [IssueDemand(cfg, names)]
    return {t.name: t for t in tools}


# Tool names offered to the model when judging tribute (everything except the
# proactive demand tool, which is only offered in demand mode).
JUDGMENT_TOOLS = {
    "decree", "bless", "curse", "mercy", "summon_threat",
    "set_soullink_coefficient", "set_revival_cost", "set_soullink_radius",
    "record_memory",
}
