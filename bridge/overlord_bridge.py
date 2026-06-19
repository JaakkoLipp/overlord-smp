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
        self.last_wrath_decay = 0.0
        self.resolved_since_fold = 0
        self.seq_tribute = 0
        self.seq_demand = 0
        self.seq_milestone = 0
        self.seq_prayer = 0
        self.last_milestone_react = 0.0
        self.last_prayer_react = 0.0
        self.last_pulse = 0.0
        # Foreshadowed actions: (fire_at_epoch, {tool, args}) scheduled by the bridge.
        self.pending_omens: list[tuple[float, dict]] = []

    # -- lifecycle ------------------------------------------------------ #
    def start(self):
        self.rcon.connect()
        self.seq_tribute = events.read_seq(self.rcon, "seqTribute")
        self.seq_demand = events.read_seq(self.rcon, "seqDemand")
        self.seq_milestone = events.read_seq(self.rcon, "seqMilestone")
        self.seq_prayer = events.read_seq(self.rcon, "seqPrayer")
        # Re-push wrath fractions + bossbar from the persisted level so storage,
        # the scoreboard, and the visible bar stay consistent after a restart.
        self.last_wrath_decay = time.time()
        self.last_pulse = time.time()  # first pulse is pulse_minutes after boot
        wrath = self._set_wrath(events.get_score(self.rcon, "#wrath", "ovGlobal"))
        # Keep the favor-pool bossbar scale in sync with config, then refresh it.
        self.rcon.command(f"scoreboard players set #favorMax ovGlobal {self.cfg.favor_pool_max}")
        self.rcon.command("function overlord:favor/show_bar")
        log.info("bridge online. tribute=%s demand=%s wrath=%s, %d tools, model=%s",
                 self.seq_tribute, self.seq_demand, wrath, len(self.registry),
                 self.cfg.llm_model)

    def loop(self):
        while _running:
            try:
                self._poll_tribute()
                self._poll_demand()
                self._poll_milestones()
                self._poll_prayers()
                self._maybe_issue_demand()
                self._maybe_pulse()
                self._maybe_decay_wrath()
                self._fire_due_omens()
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
        self._wrath_after_demand(result)
        self.log.append("demand_met" if result == "met" else "demand_failed",
                        kind=active["kind"], text=active["description"])
        self._maybe_fold()

    # -- milestones (reactive: the overlord notices the world) --------- #
    def _poll_milestones(self):
        seq = events.read_seq(self.rcon, "seqMilestone")
        if seq <= self.seq_milestone:
            self.seq_milestone = seq
            return
        self.seq_milestone = seq
        flagged = events.collect_milestones(self.rcon)  # always resets flags
        if not flagged:
            return
        if time.time() - self.last_milestone_react < self.cfg.milestone_cooldown_s:
            return  # drop the reaction (flags already cleared) to stay un-chatty
        self.last_milestone_react = time.time()
        # Batch what happened this tick into one headline; react to it as the group.
        parts = [f"{m['player']} {m['what']}" for m in flagged]
        headline = "; ".join(parts)
        who = flagged[0]["player"]
        log.info("milestone: %s", headline)
        self.log.append("milestone", text=headline, player=who)
        self._react_event(headline, "", who)

    # -- prayers (reactive: a player speaks to the overlord) ----------- #
    def _poll_prayers(self):
        seq = events.read_seq(self.rcon, "seqPrayer")
        if seq <= self.seq_prayer:
            self.seq_prayer = seq
            return
        self.seq_prayer = seq
        who, text = events.collect_prayer(self.rcon)
        if time.time() - self.last_prayer_react < self.cfg.prayer_cooldown_s:
            return
        self.last_prayer_react = time.time()
        headline = f"{who or 'A supplicant'} leaves a written prayer upon your altar"
        log.info("prayer from %s: %s", who or "?", text)
        self.log.append("prayer", player=who, text=text)
        spoke = self._react_event(headline, text, who)
        if not spoke:  # acknowledge so the supplicant knows they were heard
            self.rcon.command('tellraw @a {"text":"[Overlord] The presence hears your '
                              'prayer... and says nothing.","color":"dark_gray","italic":true}')

    def _react_event(self, headline: str, detail: str, who: str | None) -> bool:
        """Shared reactive turn for milestones and prayers. Returns True if the overlord
        acted (any tool fired), False if it chose silence."""
        state = events.world_state(self.rcon)
        ctx = build_context(self.log, self.chron, donor=who or None)
        actions = self.overlord.react_event(headline, detail, state, ctx)
        if not actions:
            return False
        self._execute(actions, who=who or "@a")
        return True

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

        if spec["kind"] == "survive":
            # A survive ordeal escalates via the surge plumbing; give it a themed mob
            # so the datapack's ramped waves have something to draw from.
            mob = random.choice(self.cfg.surge_mobs) if self.cfg.surge_mobs else "zombie"
            self.rcon.command(
                'data modify storage overlord:event set value '
                '{event:"ordeal",magnitude:3,duration:0,cadence:5,cap:12,'
                f'surge_mob:"{mob}",weather:"thunder"}}')

        item = spec["item"] or "minecraft:air"
        text = _snbt_str(spec["description"])
        snbt = ('{kind:%d,threshold:%d,seconds:%d,overtime:%d,source:%d,item:"%s",text:"%s"}'
                % (spec["kind_n"], spec["threshold"], spec["seconds"],
                   self.cfg.demand_overtime_s, spec["source_n"], _snbt_str(item), text))
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
                continue
            if name == "foreshadow":
                self._schedule_omen(params)

    def _schedule_omen(self, params):
        """The omen line is already spoken by the tool; here we queue its deferred
        payload (if any) to fire after a clamped delay."""
        secs = max(self.cfg.foreshadow_min_s,
                   min(self.cfg.foreshadow_max_s, int(getattr(params, "seconds_until", 120))))
        self.log.append("foreshadow", note=getattr(params, "omen", ""), fire_in=secs)
        payload = getattr(params, "then", None)
        if not isinstance(payload, dict) or "tool" not in payload:
            return  # pure prophecy: mood only, nothing scheduled
        if payload["tool"] in ("foreshadow", "issue_demand"):
            log.info("omen payload %r not schedulable; speaking prophecy only", payload["tool"])
            return
        self.pending_omens.append((time.time() + secs, payload))
        log.info("omen scheduled: %s in %ss", payload["tool"], secs)

    def _fire_due_omens(self):
        if not self.pending_omens:
            return
        now = time.time()
        due = [o for o in self.pending_omens if o[0] <= now]
        if not due:
            return
        self.pending_omens = [o for o in self.pending_omens if o[0] > now]
        for _, payload in due:
            log.info("omen strikes: %s", payload.get("tool"))
            self.rcon.command('tellraw @a {"text":"[Overlord] The omen comes to pass.",'
                              '"color":"dark_red","italic":true}')
            self._fire_stake(payload)

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

    # -- autonomous pulse (the overlord's own rhythm) ------------------ #
    def _maybe_pulse(self):
        """On its own clock, give the overlord an unprompted turn to act or watch.
        Not a second escalator: it ratchets nothing by itself, and a demand in flight
        (its own focused moment) suppresses it."""
        if self.cfg.pulse_minutes <= 0 or self.active_demand is not None:
            return
        if time.time() - self.last_pulse < self.cfg.pulse_minutes * 60:
            return
        if len(events.online_players(self.rcon)) < self.cfg.pulse_min_players:
            return  # no one to rule; retry next loop without resetting the clock
        self.last_pulse = time.time()
        self._pulse()

    def _pulse(self):
        log.info("overlord pulse (autonomous turn)")
        state = events.world_state(self.rcon)
        ctx = build_context(self.log, self.chron)
        actions = self.overlord.consider(state, ctx)
        if not actions:
            log.info("  -> the overlord watches in silence")
            return
        self.log.append("pulse", actions=len(actions))
        self._execute(actions, who="@a")

    # -- wrath (the overlord's disposition, made shared + visible) ------ #
    def _set_wrath(self, level: int) -> int:
        """Push a clamped wrath level through the typed set_wrath tool."""
        tool = self.registry.get("set_wrath")
        level = max(0, min(self.cfg.wrath_max, int(level)))
        if tool is None:
            return level
        try:
            tool.run(self.rcon, tool.Params(level=level))
        except Exception as exc:  # never let an ambient effect crash the loop
            log.warning("wrath push failed: %s", exc)
        return level

    def _adjust_wrath(self, delta: int) -> int:
        cur = events.get_score(self.rcon, "#wrath", "ovGlobal")
        new = max(0, min(self.cfg.wrath_max, cur + delta))
        if new != cur:
            self._set_wrath(new)
            log.info("wrath %s -> %s (%+d)", cur, new, delta)
        return new

    def _wrath_after_demand(self, result: str):
        """A met demand soothes the overlord; a failed one stokes it, harder on a
        failure streak. This is the one dial coupling demands to the shared mood."""
        if result == "met":
            self._adjust_wrath(-self.cfg.wrath_on_success)
            return
        streak = events.get_score(self.rcon, "#failStreak", "ovGlobal")
        new = self._adjust_wrath(self.cfg.wrath_on_fail * max(1, streak))
        self.last_wrath_decay = time.time()  # a fresh spike must not instantly decay
        # At peak wrath, repeated defiance erupts into a blood moon (bounded, timed).
        if new >= self.cfg.wrath_max and "blood_moon" in self.cfg.world_events:
            tool = self.registry.get("world_event")
            if tool is not None:
                try:
                    tool.run(self.rcon, tool.Params(
                        event="blood_moon", magnitude=3,
                        duration_seconds=min(180, self.cfg.event_max_duration_s)))
                    log.info("peak wrath: blood moon unleashed")
                except Exception as exc:
                    log.warning("blood moon trigger failed: %s", exc)

    def _maybe_decay_wrath(self):
        """Idle self-healing: drop one wrath level every wrath_decay_minutes of calm,
        so the world relaxes when the overlord goes quiet (mood, not ratchet)."""
        if self.cfg.wrath_decay_minutes <= 0 or self.active_demand is not None:
            return
        if time.time() - self.last_wrath_decay < self.cfg.wrath_decay_minutes * 60:
            return
        self.last_wrath_decay = time.time()
        cur = events.get_score(self.rcon, "#wrath", "ovGlobal")
        if cur > 0:
            self._set_wrath(cur - 1)
            log.info("wrath decayed to %s (idle)", cur - 1)


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
