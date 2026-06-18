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


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
def build_registry(cfg: Config) -> dict[str, Tool]:
    tools = [
        Decree(cfg), Bless(cfg), Curse(cfg), Mercy(cfg), SummonThreat(cfg),
        TightenBonds(cfg), SetRevivalCost(cfg),
    ]
    return {t.name: t for t in tools}
