#!/usr/bin/env python3
"""Keep native enemy evidence on an ordinary save and a restored actor identity."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class NativeEnemyFixtureTests(unittest.TestCase):
    def setUp(self):
        self.enemy = 10016
        self.target = 10017
        self.restored = 10026
        self.loaded = False
        self.idle = False
        self.peaceful = False
        self.pool = 35
        self.delivered = False
        self.stats = {}
        self.timers = []
        self.actions = []
        self.saves = []
        self.quit = False
        self.output = io.StringIO()
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.SetTimer = lambda callback, *args: self.timers.append(callback)
        self.gemrb.ManageCompanion = self.companion
        self.gemrb.CreateCreature = lambda *args: self.target
        self.gemrb.GetPlayerName = self.name
        self.gemrb.SetPlayerScript = lambda *args: None
        self.gemrb.LoadTable = lambda *args: types.SimpleNamespace(GetValue=lambda *args: 44)
        self.gemrb.SetPlayerStat = lambda actor, stat, value: self.stats.__setitem__((actor, stat), value)
        self.gemrb.GetPlayerStat = lambda actor, stat: int(self.delivered) if stat == 201 else self.stats[actor, stat]
        self.gemrb.CountEffects = self.effects
        self.gemrb.GetPartySize = lambda: 1
        self.gemrb.EvaluateString = self.evaluate
        self.gemrb.SetNonPartySpellCastCheck = lambda callback: setattr(self, "accepted", callback)
        self.gemrb.ExecuteString = self.execute
        self.gemrb.SaveGame = self.save
        self.gemrb.GetGamePreview = lambda: "preview"
        self.gemrb.GetSaveGames = lambda: ["save"]
        self.gemrb.LoadGame = lambda *args: setattr(self, "loaded", True)
        self.gemrb.EnterGame = lambda: None
        self.gemrb.Quit = lambda: setattr(self, "quit", True)
        self.core = types.ModuleType("GemRBModCore")
        self.core.install_engine_hooks = lambda: True
        self.core.confirm_nonparty_spell = self.confirm
        self.psion = types.ModuleType("Psionics")
        self.psion.is_psion = lambda actor: actor == (self.restored if self.loaded else self.enemy)
        self.psion.discipline = lambda actor: "NOMAD"
        self.psion.ensure_pool = self.read_pool
        self.psion.manifestation_plan = lambda *args: {"allowed": True, "cost": 5}
        modules = patch.dict(sys.modules, {"GemRB": self.gemrb, "GemRBModCore": self.core, "Psionics": self.psion})
        modules.start()
        self.addCleanup(modules.stop)
        spec = importlib.util.spec_from_file_location("enemy_fixture_test", ROOT / "psion/tests/enemy_psion_native_scenario.py")
        self.scenario = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.scenario)

    def companion(self, owner, resource, mode):
        self.assertEqual((owner, resource), (1, "PSCRBODY"))
        self.assertEqual(mode, 0 if self.loaded else 1)
        return {"ActorID": self.restored if self.loaded else self.enemy, "Created": not self.loaded, "Alive": True}

    def name(self, actor, mode):
        self.assertEqual(mode, 2)
        if actor == self.target:
            return "PSCRBODY"
        self.assertEqual(actor, self.restored if self.loaded else self.enemy)
        return "gmcPSCRBODY00000001"

    def read_pool(self, actor, *args):
        self.assertEqual(actor, self.restored if self.loaded else self.enemy)
        return self.pool

    def confirm(self, actor, resref):
        self.assertEqual((actor, resref), (self.enemy, "PS3THOP"))
        self.pool -= 5
        return "PS3THOP4"

    def evaluate(self, trigger, quiet):
        self.assertTrue(quiet)
        if trigger.startswith("InParty("):
            return False
        if trigger.startswith("ObjectActionListEmpty("):
            self.assertIn("gmcPSCRBODY00000001", trigger)
            return self.idle
        self.assertEqual(trigger, "CombatCounter(0)")
        return self.peaceful

    def execute(self, action, actor):
        self.actions.append((action, actor))
        self.assertEqual((action, actor), ('ForceSpellRES("PS3THOP","PSCRBODY")', self.enemy))
        self.accepted(actor, "PS3THOP")
        self.delivered = True

    def effects(self, actor, opcode, p1, p2, *args):
        self.assertEqual((actor, opcode, p1, p2), (self.target, "Maze", -1, -1))
        if args:
            self.assertEqual(args, ("", "PS3THOP4"))
        return int(self.delivered)

    def save(self, *args):
        self.assertTrue(self.idle and self.peaceful)
        self.assertEqual(self.stats[self.enemy, 234], 128)
        self.assertEqual(self.pool, 30)
        self.assertEqual(args, (None, "Enemy Psion runtime", 0, "preview"))
        self.saves.append(args)
        return 0

    def test_save_waits_for_completed_combat_and_load_resolves_new_actor(self):
        with contextlib.redirect_stdout(self.output):
            self.scenario.start()
            self.timers.pop(0)()  # after_cast: the accepted action is still busy
            self.assertFalse(self.saves)
            self.assertFalse(self.loaded)
            self.idle = True
            self.timers.pop(0)()  # action complete, combat still active
            self.assertFalse(self.saves)
            self.peaceful = True
            self.timers.pop(0)()  # ordinary safe save then LoadGame
            self.timers.pop(0)()  # after_load: old GlobalID is invalid
        self.assertTrue(self.quit)
        self.assertEqual(len(self.saves), 1)
        self.assertEqual(len(self.actions), 1)
        records = [json.loads(line.split("ENEMY_PSION_NATIVE ", 1)[1])
                   for line in self.output.getvalue().splitlines() if line.startswith("ENEMY_PSION_NATIVE {")]
        self.assertEqual([entry["checkpoint"] for entry in records],
                         ["accepted_hook", "power_delivered", "pp_spent_once", "combat_completed", "saved", "loaded"])
        self.assertEqual((records[0]["caster_ea"], records[0]["target_ea"]), (255, 4))
        self.assertEqual((records[-1]["actor"], records[-1]["previous_actor"]), (self.restored, self.enemy))
        self.assertEqual(records[-1]["pool"], 30)
        self.assertIn("ENEMY_PSION_NATIVE_PASS", self.output.getvalue())

    def test_unfinished_combat_never_saves(self):
        with contextlib.redirect_stdout(self.output):
            self.scenario.start()
            with self.assertRaises(AssertionError):
                self.scenario.await_safe_save(30)
        self.assertFalse(self.saves)
        self.assertFalse(self.loaded)

    def test_accepted_cast_without_delivered_power_fails(self):
        with contextlib.redirect_stdout(self.output), contextlib.redirect_stderr(self.output):
            self.scenario.start()
            self.delivered = False
            self.timers.pop(0)()
        self.assertFalse(self.saves)
        self.assertFalse(self.loaded)
        self.assertIn("ENEMY_PSION_NATIVE_FAIL", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
