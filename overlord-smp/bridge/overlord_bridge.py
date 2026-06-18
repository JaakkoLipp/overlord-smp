"""Overlord SMP bridge :: main loop.

Poll the datapack's event sequence over RCON. On each new tribute, snapshot the
world, ask the overlord for typed tool calls, validate, and execute them back
over RCON. Latency is theatre: the datapack already told players "the presence
deliberates" when the tribute landed, so the few seconds of inference read as
the god making up its mind.

Run:  python overlord_bridge.py
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from config import Config
import events
from overlord import Overlord
from rcon import RconClient
from tools import build_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)
log = logging.getLogger("overlord.bridge")

_running = True


def _stop(*_):
    global _running
    _running = False
    log.info("shutdown requested")


def main() -> int:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    cfg = Config().require()
    rcon = RconClient(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password)
    rcon.connect()
    registry = build_registry(cfg)
    overlord = Overlord(cfg, registry)

    last_seq = events.read_seq(rcon)
    log.info("bridge online. baseline seq=%s, %d tools, model=%s",
             last_seq, len(registry), cfg.llm_model)

    while _running:
        try:
            seq = events.read_seq(rcon)
            if seq < last_seq:
                # datapack reloaded (seq reset). resync without firing.
                log.info("seq reset detected (%s -> %s); resyncing", last_seq, seq)
                last_seq = seq
            elif seq > last_seq:
                last_seq = seq
                donors = events.collect_donors(rcon)
                if not donors:
                    log.debug("seq advanced but no donor scored; skipping")
                state = events.world_state(rcon)
                for event in donors:
                    _handle_tribute(cfg, rcon, overlord, event, state)
        except Exception as exc:  # never let one bad cycle kill the bridge
            log.exception("poll cycle error: %s", exc)
            time.sleep(2.0)

        time.sleep(cfg.poll_interval)

    rcon.close()
    log.info("bridge stopped")
    return 0


def _handle_tribute(cfg, rcon, overlord, event, state) -> None:
    log.info("tribute: %s gave %s (favour=%s)",
             event["player"], event["tribute"], event.get("favor"))
    actions = overlord.decide(event, state)
    if not actions:
        # the god ignores you -- still flavourful
        rcon.command('tellraw @a {"text":"The presence considers your offering... and turns away.",'
                     '"color":"dark_gray","italic":true}')
        return
    for name, params in actions:
        try:
            result = registry_run(rcon, overlord, name, params)
            log.info("  -> %s(%s): %s", name, params.model_dump(), result)
        except Exception as exc:
            log.error("  -> tool %s failed: %s", name, exc)


def registry_run(rcon, overlord, name, params) -> str:
    return overlord.registry[name].run(rcon, params)


if __name__ == "__main__":
    sys.exit(main())
