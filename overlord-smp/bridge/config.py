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

    def require(self) -> "Config":
        if not self.rcon_password:
            raise SystemExit("RCON_PASSWORD is required (set it in .env or the environment).")
        return self
