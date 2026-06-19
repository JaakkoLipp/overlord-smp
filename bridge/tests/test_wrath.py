"""Tests for the wrath / world-event / mass-effect / ritual palette.

These exercise the typed-tool boundary (validation, clamping, allow-list refusals,
constructed commands) and the bridge's wrath coupling (rise on a failed demand,
fall on a met one, idle decay). They run with only pydantic installed: the openai
import in overlord.py is lazy, and Overlord is stubbed so no model client is built.

Run:  python -m pytest bridge/tests   (or)   python -m unittest discover bridge/tests
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest

# Make the bridge package importable whether run from repo root or bridge/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, _csv_float, _kv  # noqa: E402
import tools as tools_mod  # noqa: E402
from tools import build_registry  # noqa: E402


class FakeRcon:
    """Captures every command; answers `scoreboard players get`, `list`, and any
    exact command supplied in `responses`."""

    def __init__(self, scores=None, players=None, responses=None):
        self.commands: list[str] = []
        self.scores = scores or {}
        self.players = players or []
        self.responses = responses or {}

    def command(self, cmd: str) -> str:
        self.commands.append(cmd)
        if cmd in self.responses:
            return self.responses[cmd]
        if cmd == "list":
            return f"There are {len(self.players)} online: {', '.join(self.players)}"
        if cmd.startswith("scoreboard players get "):
            parts = cmd.split()
            val = self.scores.get((parts[3], parts[4]), 0)
            return f"{parts[3]} has {val} [obj]"
        return ""

    def find(self, needle: str) -> list[str]:
        return [c for c in self.commands if needle in c]

    def has(self, needle: str) -> bool:
        return any(needle in c for c in self.commands)


def cfg() -> Config:
    return Config()


# --------------------------------------------------------------------------- #
# config parsing helpers                                                        #
# --------------------------------------------------------------------------- #
class TestConfigHelpers(unittest.TestCase):
    def test_csv_float(self):
        self.assertEqual(_csv_float("DOES_NOT_EXIST", "0.0,0.5,0.75"), [0.0, 0.5, 0.75])

    def test_kv(self):
        os.environ["RIT_TEST"] = "plague=mypack:plague, boon = mypack:bless_all ,bad"
        try:
            self.assertEqual(
                _kv("RIT_TEST", ""),
                {"plague": "mypack:plague", "boon": "mypack:bless_all"},
            )
        finally:
            del os.environ["RIT_TEST"]

    def test_kv_empty(self):
        self.assertEqual(_kv("RIT_EMPTY", ""), {})


# --------------------------------------------------------------------------- #
# set_wrath                                                                     #
# --------------------------------------------------------------------------- #
class TestSetWrath(unittest.TestCase):
    def setUp(self):
        self.c = cfg()
        self.tool = build_registry(self.c)["set_wrath"]

    def test_clamps_high(self):
        r = FakeRcon()
        out = self.tool.run(r, self.tool.Params(level=99))
        self.assertIn(f"{self.c.wrath_max}", out)
        self.assertTrue(r.has(f"scoreboard players set #wrath ovGlobal {self.c.wrath_max}"))
        self.assertTrue(r.has(f"scoreboard players set #wrathMax ovGlobal {self.c.wrath_max}"))

    def test_clamps_low_hides_bar(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(level=-5))
        self.assertTrue(r.has("scoreboard players set #wrath ovGlobal 0"))
        self.assertTrue(r.has("bossbar set overlord:wrath visible false"))
        self.assertFalse(r.has("function overlord:wrath/show_bar"))

    def test_positive_shows_bar_and_pushes_fractions(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(level=2))
        self.assertTrue(r.has("function overlord:wrath/show_bar"))
        storage = r.find("data modify storage overlord:wrath set value")
        self.assertEqual(len(storage), 1)
        # level-2 defaults: dmg 0.2, hp 0.15
        self.assertIn('dmg:"0.2"', storage[0])
        self.assertIn('hp:"0.15"', storage[0])
        self.assertIn("level:2", storage[0])

    def test_fmt_no_type_suffix(self):
        # Fractions must serialise as bare numbers (a macro must not emit 0.5d etc.)
        self.assertEqual(tools_mod._fmt(0.0), "0")
        self.assertEqual(tools_mod._fmt(0.5), "0.5")
        self.assertEqual(tools_mod._fmt(0.35), "0.35")
        self.assertEqual(tools_mod._fmt(0.75), "0.75")

    def test_frac_table_lookup_clamps(self):
        self.assertEqual(tools_mod._wrath_frac([0.0, 0.1, 0.2], 99), 0.2)
        self.assertEqual(tools_mod._wrath_frac([], 3), 0.0)


# --------------------------------------------------------------------------- #
# mass_effect                                                                   #
# --------------------------------------------------------------------------- #
class TestMassEffect(unittest.TestCase):
    def setUp(self):
        self.c = cfg()
        self.tool = build_registry(self.c)["mass_effect"]

    def test_rejects_off_allowlist(self):
        r = FakeRcon()
        out = self.tool.run(r, self.tool.Params(effect="instant_damage", seconds=10))
        self.assertTrue(out.startswith("refused"))
        self.assertEqual(r.commands, [])  # nothing sent

    def test_clamps_duration_and_amplifier(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(effect="poison", seconds=99999, amplifier=99))
        sent = r.find("effect give @a minecraft:poison")
        self.assertEqual(len(sent), 1)
        self.assertIn(f"poison {self.c.max_duration_s} {self.c.max_amplifier}", sent[0])

    def test_strips_namespace(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(effect="minecraft:strength", seconds=10))
        self.assertTrue(r.has("effect give @a minecraft:strength 10 0"))


# --------------------------------------------------------------------------- #
# world_event                                                                   #
# --------------------------------------------------------------------------- #
class TestWorldEvent(unittest.TestCase):
    def setUp(self):
        self.c = cfg()
        self.tool = build_registry(self.c)["world_event"]

    def test_rejects_unregistered(self):
        r = FakeRcon()
        out = self.tool.run(r, self.tool.Params(event="meteor", magnitude=3))
        self.assertTrue(out.startswith("refused"))
        self.assertEqual(r.commands, [])

    def test_rejects_separator_in_name(self):
        with self.assertRaises(Exception):
            self.tool.Params(event="storm; say hi")

    def test_storm_clamps_duration_and_runs_function(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(event="storm", magnitude=3, duration_seconds=99999))
        storage = r.find("data modify storage overlord:event set value")
        self.assertEqual(len(storage), 1)
        self.assertIn(f"duration:{self.c.event_max_duration_s}", storage[0])
        self.assertIn('weather:"thunder"', storage[0])  # magnitude 3 -> thunder
        self.assertTrue(r.has("function overlord:event/storm"))

    def test_surge_mob_from_allowlist(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(event="spawn_surge", magnitude=2, duration_seconds=60))
        storage = r.find("data modify storage overlord:event set value")[0]
        chosen = storage.split('surge_mob:"')[1].split('"')[0]
        self.assertIn(chosen, self.c.surge_mobs)

    def test_cap_bounded(self):
        r = FakeRcon()
        self.tool.run(r, self.tool.Params(event="blood_moon", magnitude=3, duration_seconds=60))
        storage = r.find("data modify storage overlord:event set value")[0]
        cap = int(storage.split("cap:")[1].split(",")[0])
        self.assertLessEqual(cap, self.c.event_spawn_cap)
        self.assertGreaterEqual(cap, 1)


# --------------------------------------------------------------------------- #
# invoke_ritual                                                                 #
# --------------------------------------------------------------------------- #
class TestInvokeRitual(unittest.TestCase):
    def test_no_rituals_registered(self):
        c = cfg()
        c.external_rituals = {}
        tool = build_registry(c)["invoke_ritual"]
        r = FakeRcon()
        out = tool.run(r, tool.Params(name="anything"))
        self.assertIn("no rituals", out)
        self.assertEqual(r.commands, [])

    def test_refuses_unknown_name(self):
        c = cfg()
        c.external_rituals = {"plague": "mypack:plague"}
        tool = build_registry(c)["invoke_ritual"]
        r = FakeRcon()
        out = tool.run(r, tool.Params(name="boon"))
        self.assertTrue(out.startswith("refused"))
        self.assertEqual(r.commands, [])

    def test_runs_registered_function(self):
        c = cfg()
        c.external_rituals = {"plague": "mypack:plague"}
        tool = build_registry(c)["invoke_ritual"]
        r = FakeRcon()
        tool.run(r, tool.Params(name="plague"))
        self.assertTrue(r.has("function mypack:plague"))

    def test_rejects_bad_name_charset(self):
        c = cfg()
        tool = build_registry(c)["invoke_ritual"]
        with self.assertRaises(Exception):
            tool.Params(name="evil:function")


# --------------------------------------------------------------------------- #
# stake eligibility                                                             #
# --------------------------------------------------------------------------- #
class TestStakeEligibility(unittest.TestCase):
    def test_new_tools_eligible_as_stakes(self):
        from tools import _STAKE_FORBIDDEN, JUDGMENT_TOOLS
        for name in ("set_wrath", "mass_effect", "world_event", "invoke_ritual"):
            self.assertIn(name, JUDGMENT_TOOLS)
            self.assertNotIn(name, _STAKE_FORBIDDEN)


# --------------------------------------------------------------------------- #
# bridge wrath coupling (Overlord stubbed; no model client built)               #
# --------------------------------------------------------------------------- #
class _StubOverlord:
    def __init__(self, cfg, registry):
        self.client = None
        self.react_return = []
        self.react_calls = []

    def react_event(self, headline, detail, state, memory_ctx):
        self.react_calls.append((headline, detail))
        return self.react_return


def _make_bridge(scores):
    import overlord_bridge
    overlord_bridge.Overlord = _StubOverlord  # avoid building a real model client
    c = cfg()
    c.state_dir = tempfile.mkdtemp(prefix="ovtest_")
    b = overlord_bridge.Bridge(c)
    b.rcon = FakeRcon(scores)
    # rebuild registry so its tools issue commands through the fake rcon
    return b


class TestBridgeWrathCoupling(unittest.TestCase):
    def test_met_demand_lowers_wrath(self):
        b = _make_bridge({("#wrath", "ovGlobal"): 3})
        b._wrath_after_demand("met")
        self.assertTrue(b.rcon.has("scoreboard players set #wrath ovGlobal 2"))

    def test_failed_demand_raises_scaled_by_streak(self):
        b = _make_bridge({("#wrath", "ovGlobal"): 1, ("#failStreak", "ovGlobal"): 2})
        b._wrath_after_demand("failed")
        # 1 + (wrath_on_fail * 2) = 3, clamped to wrath_max
        expected = min(b.cfg.wrath_max, 1 + b.cfg.wrath_on_fail * 2)
        self.assertTrue(b.rcon.has(f"scoreboard players set #wrath ovGlobal {expected}"))

    def test_peak_wrath_triggers_blood_moon(self):
        b = _make_bridge({("#wrath", "ovGlobal"): 4, ("#failStreak", "ovGlobal"): 5})
        b._wrath_after_demand("failed")
        self.assertTrue(b.rcon.has("function overlord:event/blood_moon"))

    def test_idle_decay_drops_one_level(self):
        b = _make_bridge({("#wrath", "ovGlobal"): 2})
        b.active_demand = None
        b.last_wrath_decay = 0.0  # long ago -> eligible to decay
        b._maybe_decay_wrath()
        self.assertTrue(b.rcon.has("scoreboard players set #wrath ovGlobal 1"))

    def test_no_decay_during_active_demand(self):
        b = _make_bridge({("#wrath", "ovGlobal"): 2})
        b.active_demand = {"kind": "score"}
        b.last_wrath_decay = 0.0
        b._maybe_decay_wrath()
        self.assertFalse(b.rcon.has("scoreboard players set #wrath ovGlobal 1"))


# --------------------------------------------------------------------------- #
# spend_favor                                                                   #
# --------------------------------------------------------------------------- #
class TestSpendFavor(unittest.TestCase):
    def setUp(self):
        self.c = cfg()
        self.tool = build_registry(self.c)["spend_favor"]

    def test_rejects_off_allowlist_boon(self):
        r = FakeRcon({("#favorPool", "ovGlobal"): 9999})
        out = self.tool.run(r, self.tool.Params(boon="apocalypse"))
        self.assertTrue(out.startswith("refused"))
        self.assertFalse(r.has("scoreboard players remove #favorPool"))

    def test_refuses_when_pool_too_thin(self):
        r = FakeRcon({("#favorPool", "ovGlobal"): 1})
        out = self.tool.run(r, self.tool.Params(boon="mercy"))
        self.assertTrue(out.startswith("refused"))
        self.assertFalse(r.has("scoreboard players remove #favorPool"))

    def test_mercy_spends_and_heals_group(self):
        r = FakeRcon({("#favorPool", "ovGlobal"): 9999})
        self.tool.run(r, self.tool.Params(boon="mercy"))
        self.assertTrue(r.has(f"scoreboard players remove #favorPool ovGlobal {self.c.favor_spend_cost}"))
        self.assertTrue(r.has("effect give @a minecraft:regeneration"))

    def test_calm_lowers_wrath_through_push(self):
        r = FakeRcon({("#favorPool", "ovGlobal"): 9999, ("#wrath", "ovGlobal"): 3})
        self.tool.run(r, self.tool.Params(boon="calm"))
        self.assertTrue(r.has("scoreboard players set #wrath ovGlobal 2"))


# --------------------------------------------------------------------------- #
# foreshadow                                                                    #
# --------------------------------------------------------------------------- #
class TestForeshadow(unittest.TestCase):
    def setUp(self):
        self.tool = build_registry(cfg())["foreshadow"]

    def test_speaks_omen(self):
        r = FakeRcon()
        out = self.tool.run(r, self.tool.Params(omen="In ten minutes, I collect."))
        self.assertIn("omen", out)
        self.assertTrue(any("[An Omen]" in c for c in r.commands))

    def test_then_is_optional(self):
        # A pure prophecy validates with no deferred action.
        p = self.tool.Params(omen="A reckoning nears.")
        self.assertIsNone(p.then)

    def test_forbidden_as_stake(self):
        from tools import _STAKE_FORBIDDEN
        self.assertIn("foreshadow", _STAKE_FORBIDDEN)


# --------------------------------------------------------------------------- #
# issue_demand: survive + sacrifice kinds                                       #
# --------------------------------------------------------------------------- #
class TestDemandKinds(unittest.TestCase):
    def setUp(self):
        self.c = cfg()
        self.tool = build_registry(self.c)["issue_demand"]

    def _params(self, **kw):
        base = dict(description="Endure.", kind="survive",
                    reward={"tool": "decree", "args": {}},
                    punishment={"tool": "decree", "args": {}})
        base.update(kw)
        return self.tool.Params(**base)

    def test_survive_kind_maps(self):
        spec = self.tool.validate_full(self._params(kind="survive"))
        self.assertEqual(spec["kind_n"], 3)
        self.assertEqual(spec["source_n"], 0)

    def test_sacrifice_altar(self):
        spec = self.tool.validate_full(self._params(kind="sacrifice", source="altar", threshold=64))
        self.assertEqual(spec["kind_n"], 4)
        self.assertEqual(spec["source_n"], 0)

    def test_sacrifice_pool(self):
        spec = self.tool.validate_full(self._params(kind="sacrifice", source="pool", threshold=300))
        self.assertEqual(spec["kind_n"], 4)
        self.assertEqual(spec["source_n"], 1)

    def test_sacrifice_bad_source_rejected(self):
        with self.assertRaises(ValueError):
            self.tool.validate_full(self._params(kind="sacrifice", source="moon"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(Exception):
            self._params(kind="vibes")


# --------------------------------------------------------------------------- #
# bridge: foreshadow scheduling                                                 #
# --------------------------------------------------------------------------- #
class TestBridgeOmens(unittest.TestCase):
    def _omen_params(self, **kw):
        tool = build_registry(cfg())["foreshadow"]
        base = dict(omen="An omen.", seconds_until=30,
                    then={"tool": "decree", "args": {"message": "boom"}})
        base.update(kw)
        return tool.Params(**base)

    def test_schedules_payload(self):
        b = _make_bridge({})
        b._schedule_omen(self._omen_params())
        self.assertEqual(len(b.pending_omens), 1)

    def test_pure_prophecy_schedules_nothing(self):
        b = _make_bridge({})
        b._schedule_omen(self._omen_params(then=None))
        self.assertEqual(b.pending_omens, [])

    def test_forbidden_payload_not_scheduled(self):
        b = _make_bridge({})
        b._schedule_omen(self._omen_params(then={"tool": "issue_demand", "args": {}}))
        self.assertEqual(b.pending_omens, [])

    def test_seconds_until_clamped(self):
        b = _make_bridge({})
        b._schedule_omen(self._omen_params(seconds_until=10_000_000))
        fire_at, _ = b.pending_omens[0]
        self.assertLessEqual(fire_at, time.time() + b.cfg.foreshadow_max_s + 1)

    def test_due_omen_fires_payload(self):
        b = _make_bridge({})
        b.pending_omens = [(0.0, {"tool": "decree", "args": {"message": "now"}})]
        b._fire_due_omens()
        self.assertEqual(b.pending_omens, [])
        self.assertTrue(any("[Overlord]" in c for c in b.rcon.commands))


# --------------------------------------------------------------------------- #
# milestones + prayers (event sensing)                                          #
# --------------------------------------------------------------------------- #
class TestMilestoneSensing(unittest.TestCase):
    def test_collect_milestones_reads_and_resets(self):
        import events
        r = FakeRcon(players=["Alice", "Bob"],
                     scores={("Alice", "ovMilestone"): 1, ("Bob", "ovMilestone"): 0})
        out = events.collect_milestones(r)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["player"], "Alice")
        self.assertEqual(out[0]["code"], 1)
        self.assertIn("diamond", out[0]["what"])
        self.assertTrue(r.has("scoreboard players set Alice ovMilestone 0"))

    def test_milestone_codes_have_phrases(self):
        import events
        for code in (1, 2, 3, 4, 5):
            self.assertIn(code, events.MILESTONES)


class TestPrayerParsing(unittest.TestCase):
    def _book(self, snbt):
        return FakeRcon(responses={"data get storage overlord:prayer book": snbt})

    def test_extracts_page_text(self):
        import events
        snbt = ('Storage overlord:prayer has the following value: '
                '{components: {"minecraft:written_book_content": {author: "Steve", '
                'pages: [\'{"text":"Spare us, great one"}\'], title: {raw: "Plea"}}}, '
                'count: 1, id: "minecraft:written_book"}')
        text = events.read_prayer_text(self._book(snbt))
        self.assertIn("Spare us, great one", text)
        self.assertNotIn("minecraft:written_book", text)

    def test_plain_string_pages(self):
        import events
        snbt = ("{components: {\"minecraft:written_book_content\": "
                "{pages: ['Bring us diamonds']}}, id: \"minecraft:written_book\"}")
        text = events.read_prayer_text(self._book(snbt))
        self.assertIn("Bring us diamonds", text)

    def test_unreadable_book_is_graceful(self):
        import events
        text = events.read_prayer_text(FakeRcon())  # empty response
        self.assertTrue(text)  # never empty

    def test_collect_prayer_resets_flag(self):
        import events
        r = FakeRcon(players=["Carol"], scores={("Carol", "ovPrayer"): 1},
                     responses={"data get storage overlord:prayer book":
                                "{pages: ['mercy please']}"})
        who, text = events.collect_prayer(r)
        self.assertEqual(who, "Carol")
        self.assertIn("mercy please", text)
        self.assertTrue(r.has("scoreboard players set Carol ovPrayer 0"))


# --------------------------------------------------------------------------- #
# bridge: reactive polling (milestones + prayers)                               #
# --------------------------------------------------------------------------- #
def _bridge_with_seq(channel, value, **fake_kwargs):
    b = _make_bridge({})
    resp = fake_kwargs.pop("responses", {})
    resp[f"data get storage overlord:bridge {channel}"] = (
        f"Storage overlord:bridge has the following value at {channel}: {value}")
    b.rcon = FakeRcon(responses=resp, **fake_kwargs)
    return b


class TestBridgeReactive(unittest.TestCase):
    def test_milestone_rise_triggers_reaction(self):
        b = _bridge_with_seq("seqMilestone", 7, players=["Alice"],
                             scores={("Alice", "ovMilestone"): 1})
        b.seq_milestone = 0
        b.last_milestone_react = 0.0
        b._poll_milestones()
        self.assertEqual(b.seq_milestone, 7)
        self.assertEqual(len(b.overlord.react_calls), 1)

    def test_milestone_respects_cooldown(self):
        b = _bridge_with_seq("seqMilestone", 7, players=["Alice"],
                             scores={("Alice", "ovMilestone"): 1})
        b.seq_milestone = 0
        b.last_milestone_react = time.time()  # just reacted
        b._poll_milestones()
        self.assertEqual(b.overlord.react_calls, [])  # suppressed
        self.assertTrue(b.rcon.has("scoreboard players set Alice ovMilestone 0"))  # still reset

    def test_prayer_silence_acknowledges(self):
        b = _bridge_with_seq("seqPrayer", 3, players=["Bob"],
                             scores={("Bob", "ovPrayer"): 1},
                             responses={"data get storage overlord:prayer book":
                                        "{pages: ['help us']}"})
        b.seq_prayer = 0
        b.last_prayer_react = 0.0
        b.overlord.react_return = []  # overlord chooses silence
        b._poll_prayers()
        self.assertEqual(len(b.overlord.react_calls), 1)
        self.assertTrue(any("says nothing" in c for c in b.rcon.commands))


if __name__ == "__main__":
    unittest.main()
