#!/usr/bin/env python3
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "cipher/guiscripts/Cipher.py"
ENTRY = {"SpellResRef": "CI8RKNI", "BookType": 2, "SpellLevel": 0, "SpellIndex": 17}


class ReapingIdentityTests(unittest.TestCase):
    def setUp(self):
        self.party = ["A", "B", "ally1", "ally2"]
        self.effects = {name: [] for name in self.party}
        self.saved_globals = {}
        self.variables = {}
        self.prepared = []
        self.logs = []
        self.owner_states = {}
        self.carriers = {}
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.GetEffects = self.get_effects
        self.gemrb.ApplyEffect = self.apply_effect
        self.gemrb.GetGameVar = lambda name: self.saved_globals.get(name, 0)
        self.gemrb.SetGlobal = self.set_global
        self.gemrb.PrepareSpontaneousCast = self.prepare
        self.gemrb.SetVar = self.variables.__setitem__
        self.gemrb.Log = lambda *args: self.logs.append(args)
        modules = {"GemRB": self.gemrb}
        for name in ("Transactions", "InnateCharges", "Selectors", "ie_spells"):
            modules[name] = types.ModuleType(name)
        modules["ie_spells"].LS_MEMO = 8
        self.patched_modules = patch.dict(sys.modules, modules)
        self.patched_modules.start()
        self.addCleanup(self.patched_modules.stop)
        self.reload_runtime()

    def reload_runtime(self):
        spec = importlib.util.spec_from_file_location("reaping_identity_runtime", RUNTIME)
        self.runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runtime)

    def get_effects(self, actor, opcode):
        return [dict(effect) for effect in self.effects[self.party[actor - 1]] if effect["Opcode"] == opcode]

    def apply_effect(self, actor, opcode, value, marker, resource="", resource2="", resource3="", source="", timing=9):
        self.effects[self.party[actor - 1]].append({
            "Opcode": opcode, "Param1": value, "Param2": marker,
            "Resource1": resource, "Resource2": resource2,
            "Resource3": resource3, "Source": source, "Timing": timing,
        })

    def set_global(self, name, context, value):
        self.assertEqual(context, "GLOBAL")
        self.saved_globals[name] = value

    def prepare(self, actor, source, book, level, replacement):
        self.prepared.append((self.party[actor - 1], source, book, level, replacement))
        return 12

    def prepare_for(self, name):
        return self.runtime.prepare_action_entry(None, self.party.index(name) + 1, dict(ENTRY))

    def model_resolved_cast(self, owner, ally):
        self.assertIsNot(self.prepare_for(owner), False)
        token = int(self.prepared[-1][-1][5:])
        self.owner_states[owner] = token
        self.carriers[ally] = token
        return token

    def model_hit_recipients(self, ally):
        token = self.carriers[ally]
        return [name for name in self.party if self.owner_states.get(name) == token]

    def identity_effect(self, token):
        return {
            "Opcode": self.runtime.REAPING_OWNER_OPCODE,
            "Param1": token,
            "Param2": self.runtime.REAPING_OWNER_MARKER,
            "Resource1": self.runtime.REAPING_OWNER_RESOURCE,
            "Timing": 9,
        }

    def test_first_owner_is_not_the_party_slot(self):
        self.assertIsNot(self.prepare_for("B"), False)
        self.assertEqual(self.prepared[-1][-1], "CI8RK7")
        self.assertEqual(self.saved_globals, {"CIRKNEXT": 7})
        self.assertEqual(self.effects["B"][0]["Timing"], 9)
        self.assertEqual(self.effects["B"][0]["Param1"], 7)
        self.assertEqual(self.variables["Spell"], 4012)

    def test_overlapping_casts_reorder_and_recast_have_one_correct_recipient(self):
        self.assertEqual(self.model_resolved_cast("A", "ally1"), 7)
        self.assertEqual(self.model_resolved_cast("B", "ally2"), 8)
        self.party[0], self.party[1] = self.party[1], self.party[0]
        self.assertEqual(self.model_resolved_cast("A", "ally1"), 7)
        self.assertEqual(self.model_hit_recipients("ally1"), ["A"])
        self.assertEqual(self.model_hit_recipients("ally2"), ["B"])
        self.assertEqual(self.saved_globals["CIRKNEXT"], 8)

    def test_owner_supports_multiple_allies_across_recasts(self):
        self.model_resolved_cast("A", "ally1")
        self.party.reverse()
        self.model_resolved_cast("A", "ally2")
        self.assertEqual(self.model_hit_recipients("ally1"), ["A"])
        self.assertEqual(self.model_hit_recipients("ally2"), ["A"])
        self.assertEqual(len(self.effects["A"]), 1)

    def test_dismissal_and_replacement_never_reuse_old_owner(self):
        self.model_resolved_cast("A", "ally1")
        self.model_resolved_cast("B", "ally2")
        self.party[1] = "C"
        self.effects["C"] = []
        self.assertIsNot(self.prepare_for("C"), False)
        self.assertEqual(self.prepared[-1][-1], "CI8RK9")
        self.assertEqual(self.model_hit_recipients("ally2"), [])
        self.party.append("B")
        self.assertIsNot(self.prepare_for("B"), False)
        self.assertEqual(self.prepared[-1][-1], "CI8RK8")
        self.assertEqual(self.model_hit_recipients("ally2"), ["B"])
        self.assertEqual(self.model_hit_recipients("ally1"), ["A"])

    def test_save_reload_restores_identity_without_module_state(self):
        self.model_resolved_cast("A", "ally1")
        self.model_resolved_cast("B", "ally2")
        payload = json.dumps([self.effects, self.saved_globals, self.owner_states, self.carriers])
        self.effects, self.saved_globals, self.owner_states, self.carriers = json.loads(payload)
        self.reload_runtime()
        self.party.reverse()
        self.model_resolved_cast("A", "ally1")
        self.assertEqual(self.prepared[-1][-1], "CI8RK7")
        self.assertEqual(self.model_hit_recipients("ally1"), ["A"])
        self.assertEqual(self.model_hit_recipients("ally2"), ["B"])

    def test_unresolved_preparations_allocate_distinct_identities(self):
        self.prepare_for("A")
        self.prepare_for("B")
        self.assertEqual([entry[-1] for entry in self.prepared], ["CI8RK7", "CI8RK8"])
        self.assertEqual(self.owner_states, {})

    def test_repeated_preparation_does_not_consume_identities(self):
        for _ in range(20):
            self.assertIsNot(self.prepare_for("A"), False)
        self.assertEqual({entry[-1] for entry in self.prepared}, {"CI8RK7"})
        self.assertEqual(self.saved_globals["CIRKNEXT"], 7)
        self.assertEqual(len(self.effects["A"]), 1)

    def test_full_registry_allows_existing_owner_and_blocks_new_owner(self):
        self.saved_globals["CIRKNEXT"] = 255
        self.effects["A"] = [self.identity_effect(255)]
        self.assertIsNot(self.prepare_for("A"), False)
        self.assertEqual(self.prepared[-1][-1], "CI8RK255")
        self.assertIs(self.prepare_for("B"), False)
        self.assertEqual(len(self.prepared), 1)
        self.assertEqual(self.effects["B"], [])

    def test_global_write_failure_blocks_preparation(self):
        self.gemrb.SetGlobal = lambda *args: None
        self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.prepared, [])
        self.assertEqual(self.effects["A"], [])

    def test_global_write_exception_blocks_preparation(self):
        with patch.object(self.gemrb, "SetGlobal", side_effect=RuntimeError("write failed")):
            self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.prepared, [])
        self.assertEqual(self.effects["A"], [])

    def test_failed_actor_write_burns_token_without_reusing_it(self):
        with patch.object(self.gemrb, "ApplyEffect", return_value=None):
            self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.saved_globals["CIRKNEXT"], 7)
        self.assertEqual(self.prepared, [])
        self.assertIsNot(self.prepare_for("B"), False)
        self.assertEqual(self.prepared[-1][-1], "CI8RK8")

    def test_actor_write_exception_blocks_preparation(self):
        with patch.object(self.gemrb, "ApplyEffect", side_effect=RuntimeError("write failed")):
            self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.prepared, [])

    def test_state_read_failure_is_not_treated_as_new_actor(self):
        with patch.object(self.gemrb, "GetEffects", side_effect=RuntimeError("read failed")):
            self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.saved_globals, {})
        self.assertEqual(self.prepared, [])

    def test_invalid_and_duplicate_identity_records_fail_closed(self):
        for values in ([6], [256], [9], [7, 7], ["bad"]):
            with self.subTest(values=values):
                self.saved_globals["CIRKNEXT"] = 8
                self.effects["A"] = [self.identity_effect(value) for value in values]
                self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.prepared, [])
        self.assertEqual(self.saved_globals["CIRKNEXT"], 8)

    def test_invalid_registry_fails_closed(self):
        for value in (-1, 256, "bad"):
            with self.subTest(value=value):
                self.saved_globals["CIRKNEXT"] = value
                self.assertIs(self.prepare_for("A"), False)
        self.assertEqual(self.prepared, [])

    def test_unrelated_effects_are_preserved(self):
        unrelated = {"Opcode": self.runtime.REAPING_OWNER_OPCODE, "Param1": 23,
                     "Param2": self.runtime.REAPING_OWNER_MARKER + 1, "Resource1": "OTHER"}
        self.effects["A"] = [copy.deepcopy(unrelated)]
        self.assertIsNot(self.prepare_for("A"), False)
        self.assertEqual(self.effects["A"][0], unrelated)
        self.assertEqual(len(self.effects["A"]), 2)

    def test_other_power_never_touches_owner_state(self):
        entry = dict(ENTRY, SpellResRef="CI7TPAR")
        with patch.object(self.gemrb, "GetGameVar", side_effect=AssertionError("unexpected registry access")):
            self.assertIs(self.runtime.prepare_action_entry(None, 1, entry), entry)
        self.assertEqual(self.prepared, [])
        self.assertEqual(self.effects["A"], [])

    def test_resource_bank_covers_every_owner_and_preserves_legacy_range(self):
        source = (ROOT / "cipher/lib/reaping-knives-focus.tpa").read_text()
        self.assertIn("OUTER_SET ci_rk_owner_token_limit = 255", source)
        self.assertEqual(source.count("ci_rk_slot <= ci_rk_owner_token_limit;"), 2)
        self.assertIn("parameter1 = ci_rk_slot parameter2 = ci_rk_owner_state_index", source)
        self.assertIn("CIPHER_RK_OWNER_%ci_rk_slot% %ci_rk_owner_state_stat% %ci_rk_slot% 1", source)
        for token in range(1, self.runtime.REAPING_OWNER_LAST + 1):
            for prefix in ("CI8RK", "CIRKG", "CIRKE", "CIRKA", "CIRKC"):
                self.assertLessEqual(len(prefix + str(token)), 8)
        self.assertEqual(self.runtime.REAPING_OWNER_FIRST, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
