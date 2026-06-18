"""Senses + event detection, all over RCON (no log-file access required).

The datapack mirrors an incrementing sequence number into
`storage overlord:bridge seq`. We poll it; when it rises, a tribute happened.
We then resolve donors by reading each online player's ovTribute score and
reset it. World-state queries give the overlord eyes before it acts.
"""
from __future__ import annotations

import logging
import re

from rcon import RconClient

log = logging.getLogger("overlord.events")

_INT_RE = re.compile(r"(-?\d+)")
_SCORE_RE = re.compile(r"\bhas\b.*?(-?\d+)")
_LIST_RE = re.compile(r"online:\s*(.*)$")


def _last_int(text: str, default: int = 0) -> int:
    m = list(_INT_RE.finditer(text))
    return int(m[-1].group(1)) if m else default


def read_seq(rcon: RconClient) -> int:
    # "Storage overlord:bridge has the following value at seq: 7"
    out = rcon.command("data get storage overlord:bridge seq")
    return _last_int(out, default=0)


def online_players(rcon: RconClient) -> list[str]:
    out = rcon.command("list")
    m = _LIST_RE.search(out)
    if not m or not m.group(1).strip():
        return []
    return [n.strip() for n in m.group(1).split(",") if n.strip()]


def get_score(rcon: RconClient, player: str, objective: str) -> int:
    out = rcon.command(f"scoreboard players get {player} {objective}")
    if "none is set" in out.lower() or "unknown" in out.lower():
        return 0
    m = _SCORE_RE.search(out)
    return int(m.group(1)) if m else 0


def reset_score(rcon: RconClient, player: str, objective: str, value: int = 0) -> None:
    rcon.command(f"scoreboard players set {player} {objective} {value}")


def get_health(rcon: RconClient, player: str) -> float:
    out = rcon.command(f"data get entity {player} Health")
    m = re.search(r"(-?\d+(?:\.\d+)?)f?", out)
    return float(m.group(1)) if m else -1.0


def collect_donors(rcon: RconClient) -> list[dict]:
    """Players whose ovTribute > 0 since the last poll. Resets them to 0."""
    donors = []
    for name in online_players(rcon):
        trib = get_score(rcon, name, "ovTribute")
        if trib > 0:
            reset_score(rcon, name, "ovTribute", 0)
            donors.append({"player": name, "tribute": trib,
                           "favor": get_score(rcon, name, "ovFavor")})
    return donors


def world_state(rcon: RconClient) -> dict:
    """A compact snapshot the overlord sees before deciding."""
    players = []
    for name in online_players(rcon):
        players.append({
            "name": name,
            "health": get_health(rcon, name),
            "favor": get_score(rcon, name, "ovFavor"),
            "dead": get_score(rcon, name, "ovDeaths") > 0,  # transient; mostly informational
        })
    return {
        "time": rcon.command("time query daytime").strip(),
        "soullink_coefficient": get_score(rcon, "#coeff", "ovGlobal"),
        "revival_cost_levels": get_score(rcon, "#revivalXp", "ovGlobal"),
        "players": players,
    }
