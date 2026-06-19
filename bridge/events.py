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


def read_seq(rcon: RconClient, channel: str = "seqTribute") -> int:
    # "Storage overlord:bridge has the following value at seqTribute: 7"
    out = rcon.command(f"data get storage overlord:bridge {channel}")
    return _last_int(out, default=0)


def read_demand_result(rcon: RconClient) -> str:
    out = rcon.command("data get storage overlord:bridge demandResult")
    # response contains a quoted string; pull what's inside the quotes
    m = re.search(r'"(met|failed|judge)"', out)
    return m.group(1) if m else ""


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


# Milestone codes set by the datapack on ovMilestone, mapped to a human phrase the
# overlord reacts to. Adding a milestone is a new code here plus a datapack detector.
MILESTONES = {
    1: "struck their first diamond",
    2: "crossed into the Nether for the first time",
    3: "dared to sleep in your world",
    4: "endured the night and lived to see the dawn",
    5: "stands idle, doing nothing in your domain",
}


def collect_milestones(rcon: RconClient) -> list[dict]:
    """Players flagged with ovMilestone > 0 since the last poll. Resets them."""
    out = []
    for name in online_players(rcon):
        code = get_score(rcon, name, "ovMilestone")
        if code > 0:
            reset_score(rcon, name, "ovMilestone", 0)
            out.append({"player": name, "code": code,
                        "what": MILESTONES.get(code, "did something notable")})
    return out


def read_prayer_text(rcon: RconClient) -> str:
    """Best-effort extraction of a prayer's words from the written book copied into
    `storage overlord:prayer`. NBT paths for books can shift between versions, so we
    parse the SNBT tolerantly: pull quoted text, unwrap any JSON text component, and
    drop structural tokens. The Server Management Protocol is the clean long-term path."""
    out = rcon.command("data get storage overlord:prayer book")
    pieces: list[str] = []
    for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", out):
        s = (a or b).strip()
        if not s or s.startswith("minecraft:"):
            continue
        if s in ("text", "raw", "filtered", "color", "bold", "italic", "underlined"):
            continue
        jm = re.search(r'"text"\s*:\s*"([^"]*)"', s)  # unwrap {"text":"..."}
        if jm:
            s = jm.group(1)
        if s:
            pieces.append(s)
    text = " ".join(pieces).strip()
    return text[:500] if text else "(an unreadable prayer)"


def collect_prayer(rcon: RconClient) -> tuple[str, str]:
    """The praying player (flagged ovPrayer > 0; reset) and their words."""
    player = ""
    for name in online_players(rcon):
        if get_score(rcon, name, "ovPrayer") > 0:
            reset_score(rcon, name, "ovPrayer", 0)
            if not player:
                player = name
    return player, read_prayer_text(rcon)


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
        "wrath_level": get_score(rcon, "#wrath", "ovGlobal"),
        "wrath_max": get_score(rcon, "#wrathMax", "ovGlobal"),
        "favor_pool": get_score(rcon, "#favorPool", "ovGlobal"),
        "players": players,
    }
