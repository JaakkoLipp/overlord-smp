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
import random
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator

from config import Config
from rcon import RconClient

log = logging.getLogger("overlord.tools")


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _fmt(x: float) -> str:
    # Compact decimal string, safe to substitute into a command via a datapack
    # macro (no type suffix that the parser would reject).
    return f"{x:.4f}".rstrip("0").rstrip(".") or "0"


def _wrath_frac(table: list[float], level: int) -> float:
    # Clamp the lookup so a custom WRATH_MAX that outruns the table reuses the
    # last entry rather than throwing.
    if not table:
        return 0.0
    return table[min(level, len(table) - 1)]


_WRATH_LABELS = ["Dormant", "Stirring", "Roused", "Seething", "Furious", "Apocalyptic"]


def _wrath_appearance(level: int, maximum: int) -> tuple[str, str]:
    """Bossbar colour + label for a wrath level. Colours are valid bossbar colours."""
    if level <= 0:
        return "white", "Dormant"
    frac = level / max(1, maximum)
    color = "yellow" if frac < 0.34 else ("red" if frac < 0.67 else "purple")
    label = _WRATH_LABELS[min(level, len(_WRATH_LABELS) - 1)]
    return color, label


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
# Wrath, mass effects, world events, external rituals (the palette expansion). #
# Each is one more typed tool with its own clamps and allow-lists; the growth  #
# path is more tools, never rawer access.                                      #
# --------------------------------------------------------------------------- #
class SetWrath(Tool):
    name = "set_wrath"
    description = (
        "Set your WRATH: a shared, visible meter (0..max) that is your disposition "
        "made mechanical. Higher wrath empowers hostile mobs near players and "
        "darkens the world's mood bar for everyone. It is meant to fall when you "
        "are appeased and it decays on its own when you are idle, so it is your "
        "hand on the dial, not a runaway timer. Raise it to make the realm seethe; "
        "lower it to grant respite."
    )

    class Params(BaseModel):
        level: int = Field(..., description="Target wrath level; clamped to 0..max.")

    def run(self, rcon, p):
        lvl = _clamp(p.level, 0, self.cfg.wrath_max)
        dmg = _wrath_frac(self.cfg.wrath_mob_dmg, lvl)
        hp = _wrath_frac(self.cfg.wrath_mob_hp, lvl)
        color, label = _wrath_appearance(lvl, self.cfg.wrath_max)
        # Fractions are stored as strings so the datapack macro substitutes a clean
        # number into the attribute command (no NBT type suffix to trip the parser).
        snbt = ('{level:%d,dmg:"%s",hp:"%s",radius:%d,color:"%s",label:"%s"}'
                % (lvl, _fmt(dmg), _fmt(hp), self.cfg.wrath_buff_radius, color, label))
        rcon.command(f"data modify storage overlord:wrath set value {snbt}")
        rcon.command(f"scoreboard players set #wrath ovGlobal {lvl}")
        rcon.command(f"scoreboard players set #wrathMax ovGlobal {self.cfg.wrath_max}")
        if lvl >= 1:
            rcon.command("function overlord:wrath/show_bar")
        else:
            rcon.command("bossbar set overlord:wrath visible false")
        return f"wrath set to {lvl}/{self.cfg.wrath_max} ({label})"


class MassEffect(Tool):
    name = "mass_effect"
    description = (
        "Impose a status effect on ALL players at once (beneficial or harmful, your "
        "choice from the allow-list). The per-player bless/curse remain for singling "
        "someone out; this is the group-scale version."
    )

    class Params(BaseModel):
        effect: str
        seconds: int = 30
        amplifier: int = 0

    def run(self, rcon, p):
        eff = p.effect.removeprefix("minecraft:")
        if eff not in self.cfg.mass_effects:
            return f"refused: '{eff}' is not in the mass-effect allow-list"
        dur = _clamp(p.seconds, 1, self.cfg.max_duration_s)
        amp = _clamp(p.amplifier, 0, self.cfg.max_amplifier)
        rcon.command(f"effect give @a minecraft:{eff} {dur} {amp}")
        return f"imposed {eff} (lvl {amp + 1}, {dur}s) on all players"


# Spawn-surge events draw one themed mob; non-surge events ignore the field.
_EVENT_SURGE_MOB = {"blood_moon": "zombie", "spawn_surge": ""}


class WorldEvent(Tool):
    name = "world_event"
    description = (
        "Unleash a temporary, self-reverting world event. Pick one registered event, "
        "a magnitude (1 minor, 2 moderate, 3 major), and a duration in seconds. "
        "Spawn surges are capped and timed; storms and effects expire on their own. "
        "Registered events: spawn_surge, storm, nightfall, dread, blood_moon (the "
        "exact set is server-configured)."
    )

    class Params(BaseModel):
        event: str
        magnitude: int = 2
        duration_seconds: int = 120

        @field_validator("event")
        @classmethod
        def _e(cls, v):
            v = v.strip()
            if not v or not all(c.isalnum() or c == "_" for c in v):
                raise ValueError(f"invalid event name: {v!r}")
            return v

    def run(self, rcon, p):
        ev = p.event
        if ev not in self.cfg.world_events:
            return (f"refused: '{ev}' is not a registered world event "
                    f"({', '.join(self.cfg.world_events)})")
        mag = _clamp(p.magnitude, 1, 3)
        dur = _clamp(p.duration_seconds, 1, self.cfg.event_max_duration_s)
        cadence = {1: 8, 2: 6, 3: 4}[mag]            # seconds between surge waves
        cap = _clamp((self.cfg.event_spawn_cap * mag) // 3, 1, self.cfg.event_spawn_cap)
        mob = self._surge_mob(ev)                    # always from the allow-list
        weather = "thunder" if mag >= 2 else "rain"
        snbt = ('{event:"%s",magnitude:%d,duration:%d,cadence:%d,cap:%d,'
                'surge_mob:"%s",weather:"%s"}'
                % (ev, mag, dur, cadence, cap, mob, weather))
        rcon.command(f"data modify storage overlord:event set value {snbt}")
        # Event functions are macros (they read $(duration) etc.), so they must be
        # invoked with the storage source. Non-macro events ignore it harmlessly.
        rcon.command(f"function overlord:event/{ev} with storage overlord:event")
        return f"unleashed world event '{ev}' (magnitude {mag}, {dur}s)"

    def _surge_mob(self, event: str) -> str:
        if not self.cfg.surge_mobs:
            return "zombie"
        themed = _EVENT_SURGE_MOB.get(event)
        if themed and themed in self.cfg.surge_mobs:
            return themed
        return random.choice(self.cfg.surge_mobs)


class InvokeRitual(Tool):
    name = "invoke_ritual"
    description = (
        "Invoke a ritual from an external datapack by its friendly name. The server "
        "owner vets and registers these; you may only name a registered ritual, "
        "never an arbitrary function. If none are registered, nothing happens."
    )

    class Params(BaseModel):
        name: str = Field(..., max_length=48)

        @field_validator("name")
        @classmethod
        def _n(cls, v):
            if not v or not all(c.isalnum() or c in "_-" for c in v):
                raise ValueError(f"invalid ritual name: {v!r}")
            return v

    def run(self, rcon, p):
        rituals = self.cfg.external_rituals
        if not rituals:
            return "no rituals are registered on this server"
        fid = rituals.get(p.name)
        if not fid:
            return (f"refused: '{p.name}' is not a registered ritual "
                    f"({', '.join(rituals) or 'none'})")
        rcon.command(f"function {fid}")
        return f"invoked ritual '{p.name}' ({fid})"


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
        SetWrath(cfg), MassEffect(cfg), WorldEvent(cfg), InvokeRitual(cfg),
        RecordMemory(cfg),
    ]
    names = {t.name for t in base} | {"issue_demand"}
    tools = base + [IssueDemand(cfg, names)]
    return {t.name: t for t in tools}


# Tool names offered to the model when judging tribute (everything except the
# proactive demand tool, which is only offered in demand mode). All of these are
# also automatically eligible as demand stakes unless listed in _STAKE_FORBIDDEN.
JUDGMENT_TOOLS = {
    "decree", "bless", "curse", "mercy", "summon_threat",
    "set_soullink_coefficient", "set_revival_cost", "set_soullink_radius",
    "set_wrath", "mass_effect", "world_event", "invoke_ritual",
    "record_memory",
}
