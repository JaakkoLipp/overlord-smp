"""Overlord SMP bridge :: main loop.

Polls two event channels over RCON: tribute (reactive judgement) and demand
resolution (a timed demand was met/failed/needs judging). Also self-triggers an
occasional proactive demand. All model decisions flow through the typed-tool
safety boundary, and everything notable is written to the persistent event log
so the overlord remembers across restarts.

Run:  python overlord_bridge.py
"""
from __future__ import annotations

import logging
import random
import signal
import sys
import time

from pydantic import ValidationError

from config import Config
import events
from memory import EventLog, Chronicle, build_context
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


def _snbt_str(s: str) -> str:
    # make a Python string safe to embed inside a double-quoted SNBT string
    return s.replace("\\", "").replace('"', "'")


class Bridge:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rcon = RconClient(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password)
        self.registry = build_registry(cfg)
        self.overlord = Overlord(cfg, self.registry)
        self.log = EventLog(f"{cfg.state_dir}/events.jsonl")
        self.chron = Chronicle(f"{cfg.state_dir}/chronicle.json")
        self.active_demand: dict | None = None
        self.last_demand_end = 0.0
        self.resolved_since_fold = 0
        self.seq_tribute = 0
        self.seq_demand = 0

    # -- lifecycle ------------------------------------------------------ #
    def start(self):
        self.rcon.connect()
        self.seq_tribute = events.read_seq(self.rcon, "seqTribute")
        self.seq_demand = events.read_seq(self.rcon, "seqDemand")
        log.info("bridge online. tribute=%s demand=%s, %d tools, model=%s",
                 self.seq_tribute, self.seq_demand, len(self.registry), self.cfg.llm_model)

    def loop(self):
        while _running:
            try:
                self._poll_tribute()
                self._poll_demand()
                self._maybe_issue_demand()
            except Exception as exc:
                log.exception("cycle error: %s", exc)
                time.sleep(2.0)
            time.sleep(self.cfg.poll_interval)
        self.rcon.close()
        log.info("bridge stopped")

    # -- tribute (reactive) -------------------------------------------- #
    def _poll_tribute(self):
        seq = events.read_seq(self.rcon, "seqTribute")
        if seq < self.seq_tribute:
            self.seq_tribute = seq
            return
        if seq == self.seq_tribute:
            return
        self.seq_tribute = seq
        donors = events.collect_donors(self.rcon)
        if not donors:
            return
        state = events.world_state(self.rcon)
        for ev in donors:
            self._judge_tribute(ev, state)

    def _judge_tribute(self, ev, state):
        log.info("tribute: %s gave %s (favour=%s)", ev["player"], ev["tribute"], ev.get("favor"))
        self.log.append("tribute", player=ev["player"], value=ev["tribute"])
        self.chron.adjust_standing(ev["player"], ev["tribute"])
        ctx = build_context(self.log, self.chron, donor=ev["player"])
        actions = self.overlord.judge(ev, state, ctx)
        if not actions:
            self.rcon.command('tellraw @a {"text":"The presence considers your offering... and turns away.",'
                              '"color":"dark_gray","italic":true}')
            return
        self._execute(actions, who=ev["player"])

    # -- demand resolution --------------------------------------------- #
    def _poll_demand(self):
        seq = events.read_seq(self.rcon, "seqDemand")
        if seq < self.seq_demand:
            self.seq_demand = seq
            return
        if seq == self.seq_demand:
            return
        self.seq_demand = seq
        result = events.read_demand_result(self.rcon)
        log.info("demand resolved: %s", result)
        self._resolve_demand(result)

    def _resolve_demand(self, result: str):
        active = self.active_demand
        self.active_demand = None
        self.last_demand_end = time.time()
        # always clean up the score objective if one was created
        self.rcon.command("scoreboard objectives remove ovDemand")
        if not active:
            log.warning("demand resolved with no active demand tracked; ignoring stakes")
            return
        state = events.world_state(self.rcon)
        ctx = build_context(self.log, self.chron)
        if result == "judge":
            verdict, line = self.overlord.judge_freeform(active["description"], state, ctx)
            result = verdict
            if line:
                self.rcon.command(
                    f'tellraw @a [{{"text":"[Overlord] ","color":"dark_purple","bold":true}},'
                    f'{{"text":"{_snbt_str(line)}","color":"light_purple","italic":true}}]')
        stake = active["reward"] if result == "met" else active["punishment"]
        self._fire_stake(stake)
        self.log.append("demand_met" if result == "met" else "demand_failed",
                        kind=active["kind"], text=active["description"])
        self._maybe_fold()

    # -- proactive demand ---------------------------------------------- #
    def _maybe_issue_demand(self):
        if self.active_demand is not None:
            return
        if time.time() - self.last_demand_end < self.cfg.demand_cooldown_minutes * 60:
            return
        online = events.online_players(self.rcon)
        if len(online) < self.cfg.demand_min_players:
            return
        p = self.cfg.poll_interval / max(1.0, self.cfg.demand_mean_minutes * 60)
        if random.random() >= p:
            return
        log.info("proactive demand trigger (%d online)", len(online))
        self._issue_demand()

    def _issue_demand(self):
        state = events.world_state(self.rcon)
        ctx = build_context(self.log, self.chron)
        params = self.overlord.demand(state, ctx)
        if params is None:
            log.info("overlord declined to issue a demand")
            return
        try:
            spec = self.registry["issue_demand"].validate_full(params)
        except (ValidationError, ValueError) as exc:
            log.warning("demand rejected by validation: %s", exc)
            return

        if spec["kind"] == "score":
            self.rcon.command("scoreboard objectives remove ovDemand")
            self.rcon.command(f'scoreboard objectives add ovDemand {spec["criterion"]}')
            time.sleep(0.4)  # let statistic values populate before baselining

        item = spec["item"] or "minecraft:air"
        text = _snbt_str(spec["description"])
        snbt = ('{kind:%d,threshold:%d,seconds:%d,overtime:%d,item:"%s",text:"%s"}'
                % (spec["kind_n"], spec["threshold"], spec["seconds"],
                   self.cfg.demand_overtime_s, _snbt_str(item), text))
        self.rcon.command(f"data modify storage overlord:demand set value {snbt}")
        self.rcon.command("function overlord:demand/begin")
        self.rcon.command(
            f'tellraw @a [{{"text":"\\n[A DEMAND] ","color":"dark_red","bold":true}},'
            f'{{"text":"{text}","color":"white"}}]')
        self.active_demand = spec
        self.log.append("demand_issued", kind=spec["kind"], threshold=spec["threshold"],
                        text=spec["description"])
        log.info("demand issued: kind=%s threshold=%s '%s'",
                 spec["kind"], spec["threshold"], spec["description"])

    # -- shared ---------------------------------------------------------#
    def _execute(self, actions, who):
        for name, params in actions:
            if name == "record_memory":
                tgt = getattr(params, "player", None) or who
                self.log.append("memory", note=params.note, player=tgt)
                log.info("  -> recorded memory about %s: %s", tgt, params.note)
                continue
            try:
                res = self.registry[name].run(self.rcon, params)
                log.info("  -> %s: %s", name, res)
            except Exception as exc:
                log.error("  -> %s failed: %s", name, exc)

    def _fire_stake(self, stake: dict):
        tool = self.registry.get(stake.get("tool"))
        if tool is None:
            log.warning("stake names unknown tool: %s", stake)
            return
        try:
            params = tool.Params(**stake.get("args", {}))
        except ValidationError as exc:
            log.warning("stake args invalid for %s: %s", stake.get("tool"), exc)
            return
        try:
            res = tool.run(self.rcon, params)
            log.info("stake fired: %s -> %s", stake["tool"], res)
        except Exception as exc:
            log.error("stake %s failed: %s", stake["tool"], exc)

    def _maybe_fold(self):
        self.resolved_since_fold += 1
        if self.resolved_since_fold >= self.cfg.chronicle_every:
            self.resolved_since_fold = 0
            self.chron.fold(self.overlord.client, self.cfg.llm_model, self.log.recent(8))


def main() -> int:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    cfg = Config().require()
    bridge = Bridge(cfg)
    bridge.start()
    bridge.loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
