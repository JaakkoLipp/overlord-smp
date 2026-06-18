"""Environment-driven configuration for the overlord bridge.

Everything tunable lives here so the running policy (which effects are allowed,
how hard the overlord may hit, which model) is auditable in one place.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional
    pass


def _csv(name: str, default: str) -> list[str]:
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]


def _csv_float(name: str, default: str) -> list[float]:
    return [float(s) for s in os.getenv(name, default).split(",") if s.strip()]


def _kv(name: str, default: str) -> dict[str, str]:
    """Parse `name1=val1,name2=val2` into a dict. Used for the ritual allow-list."""
    out: dict[str, str] = {}
    for pair in os.getenv(name, default).split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and v:
            out[k] = v
    return out


@dataclass
class Config:
    # --- RCON ---
    rcon_host: str = os.getenv("RCON_HOST", "127.0.0.1")
    rcon_port: int = int(os.getenv("RCON_PORT", "25575"))
    rcon_password: str = os.getenv("RCON_PASSWORD", "")
    poll_interval: float = float(os.getenv("POLL_INTERVAL", "1.0"))

    # --- LLM (OpenAI-compatible; point at your LiteLLM gateway) ---
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:4000")
    llm_api_key: str = os.getenv("LLM_API_KEY", "sk-local")
    llm_model: str = os.getenv("LLM_MODEL", "qwen-local")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.85"))

    # --- Langfuse (optional tracing) ---
    langfuse_enabled: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

    # --- Safety policy: the typed-tool boundary's allow-lists and bounds ---
    # Beneficial effects the overlord may grant.
    bless_effects: list[str] = field(default_factory=lambda: _csv(
        "BLESS_EFFECTS",
        "regeneration,absorption,strength,resistance,speed,haste,saturation,fire_resistance,night_vision",
    ))
    # Harmful effects the overlord may inflict.
    curse_effects: list[str] = field(default_factory=lambda: _csv(
        "CURSE_EFFECTS",
        "weakness,slowness,mining_fatigue,hunger,poison,blindness,nausea,wither,levitation,glowing",
    ))
    # Mobs the overlord may summon as a threat.
    threat_mobs: list[str] = field(default_factory=lambda: _csv(
        "THREAT_MOBS",
        "zombie,husk,skeleton,creeper,spider,pillager,vindicator,phantom,blaze,sulfur_cube",
    ))

    max_amplifier: int = int(os.getenv("MAX_AMPLIFIER", "4"))          # 0..4 (effect level 1..5)
    max_duration_s: int = int(os.getenv("MAX_DURATION_S", "120"))      # seconds
    max_threat_count: int = int(os.getenv("MAX_THREAT_COUNT", "6"))    # mobs per summon
    coeff_min: int = int(os.getenv("COEFF_MIN", "0"))                  # soul-link %
    coeff_max: int = int(os.getenv("COEFF_MAX", "80"))
    revival_min: int = int(os.getenv("REVIVAL_MIN", "5"))             # XP levels
    revival_max: int = int(os.getenv("REVIVAL_MAX", "60"))
    link_radius_min: int = int(os.getenv("LINK_RADIUS_MIN", "4"))     # proximity blocks
    link_radius_max: int = int(os.getenv("LINK_RADIUS_MAX", "64"))

    # --- Demands (proactive, occasional) ---
    demand_mean_minutes: float = float(os.getenv("DEMAND_MEAN_MINUTES", "60"))
    demand_cooldown_minutes: float = float(os.getenv("DEMAND_COOLDOWN_MINUTES", "15"))
    demand_min_players: int = int(os.getenv("DEMAND_MIN_PLAYERS", "2"))
    demand_deadline_min: int = int(os.getenv("DEMAND_DEADLINE_MIN", "3"))     # minutes
    demand_deadline_max: int = int(os.getenv("DEMAND_DEADLINE_MAX", "30"))
    demand_threshold_max: int = int(os.getenv("DEMAND_THRESHOLD_MAX", "2000"))
    demand_overtime_s: int = int(os.getenv("DEMAND_OVERTIME_S", "45"))        # reckoning window
    # Allow-list of vanilla scoreboard criteria the model may demand progress on.
    demand_criteria: list[str] = field(default_factory=lambda: _csv(
        "DEMAND_CRITERIA",
        "minecraft.mined:minecraft.diamond_ore,"
        "minecraft.mined:minecraft.ancient_debris,"
        "minecraft.mined:minecraft.iron_ore,"
        "minecraft.killed:minecraft.zombie,"
        "minecraft.killed:minecraft.skeleton,"
        "minecraft.killed:minecraft.creeper,"
        "minecraft.custom:minecraft.mob_kills,"
        "minecraft.custom:minecraft.player_kills,"
        "minecraft.custom:minecraft.damage_dealt,"
        "minecraft.custom:minecraft.walk_one_cm,"
        "minecraft.custom:minecraft.jump,"
        "minecraft.crafted:minecraft.bread",
    ))

    # --- Wrath (the overlord's disposition, made shared + visible) ---
    # Wrath is NOT a second escalator: it falls on appeasement and decays toward
    # calm when the overlord is idle. It is the overlord's own hand on the dial,
    # expressed as one legible, world-wide condition.
    wrath_max: int = int(os.getenv("WRATH_MAX", "5"))
    # Per-level mob buffs, as fractions applied via add_multiplied_base modifiers.
    # Index = wrath level (0..wrath_max); clamped on lookup so a custom WRATH_MAX
    # that outruns the table just reuses the last entry.
    wrath_mob_dmg: list[float] = field(default_factory=lambda: _csv_float(
        "WRATH_MOB_DMG", "0.0,0.1,0.2,0.35,0.5,0.75"))
    wrath_mob_hp: list[float] = field(default_factory=lambda: _csv_float(
        "WRATH_MOB_HP", "0.0,0.0,0.15,0.25,0.4,0.6"))
    wrath_buff_radius: int = int(os.getenv("WRATH_BUFF_RADIUS", "48"))  # near-players scan bound
    wrath_decay_minutes: float = float(os.getenv("WRATH_DECAY_MINUTES", "25"))
    wrath_on_fail: int = int(os.getenv("WRATH_ON_FAIL", "1"))       # base rise per failed demand
    wrath_on_success: int = int(os.getenv("WRATH_ON_SUCCESS", "1"))  # fall per met demand

    # --- World events (the open-ended temporary-flavour channel) ---
    # event name -> datapack function overlord:event/<name>. Adding an event is a
    # config entry plus one function file; the enum is meant to grow.
    world_events: list[str] = field(default_factory=lambda: _csv(
        "WORLD_EVENTS", "spawn_surge,storm,nightfall,dread,blood_moon"))
    event_max_duration_s: int = int(os.getenv("EVENT_MAX_DURATION_S", "300"))
    event_spawn_cap: int = int(os.getenv("EVENT_SPAWN_CAP", "12"))   # concurrent surge mobs
    # Themed mobs a spawn surge may draw from (allow-listed; the model never names one).
    surge_mobs: list[str] = field(default_factory=lambda: _csv(
        "SURGE_MOBS", "zombie,husk,skeleton,spider,creeper,phantom,pillager"))
    # Group-wide potion effects the overlord may impose (positive or negative).
    mass_effects: list[str] = field(default_factory=lambda: _csv(
        "MASS_EFFECTS",
        "regeneration,strength,resistance,speed,fire_resistance,night_vision,"
        "weakness,slowness,mining_fatigue,hunger,poison,blindness,darkness,nausea",
    ))
    # External-datapack rituals: friendly name -> vetted function id. The model may
    # only name a registered friendly name; the bridge runs the mapped function.
    external_rituals: dict[str, str] = field(default_factory=lambda: _kv(
        "EXTERNAL_RITUALS", ""))

    # --- Memory ---
    state_dir: str = os.getenv("STATE_DIR", "state")
    chronicle_every: int = int(os.getenv("CHRONICLE_EVERY", "4"))  # fold after N resolved events

    def require(self) -> "Config":
        if not self.rcon_password:
            raise SystemExit("RCON_PASSWORD is required (set it in .env or the environment).")
        return self
