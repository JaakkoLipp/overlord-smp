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

    # --- Memory ---
    state_dir: str = os.getenv("STATE_DIR", "state")
    chronicle_every: int = int(os.getenv("CHRONICLE_EVERY", "4"))  # fold after N resolved events

    def require(self) -> "Config":
        if not self.rcon_password:
            raise SystemExit("RCON_PASSWORD is required (set it in .env or the environment).")
        return self
