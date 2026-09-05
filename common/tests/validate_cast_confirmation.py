#!/usr/bin/env python3
"""Class transactions commit at the accepted-cast event, not a second click."""
from pathlib import Path
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CastConfirmation(unittest.TestCase):
    def setUp(self):
        self.core = load("cast_core", "common/guiscripts/GemRBModCore.py")
        self.transactions = load("cast_transactions", "common/guiscripts/Transactions.py")
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.SetSpellCastCheck = self.register
        self.selected = [1001]
        self.gemrb.GetSelectedActors = lambda: self.selected[:]
        self.logs = []
        self.gemrb.Log = lambda *args: self.logs.append(args)
        self.modules = patch.dict(sys.modules, {"GemRB": self.gemrb, "Transactions": self.transactions})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.callback = None
        self.pool = {1: 20, 2: 20}
        self.commits = []
        self.legal = True
        self.commit_result = True
        self.commit_error = False
        self.resources = {"PSPOWER", "PSOTHER", "PXL0001", "PSMT03", "PSMT034", "CI8RKNI", "CI8RK3"}
        self.selection = "PSPOWER"
        self.replacement = None
        self.handler = types.SimpleNamespace(
            __name__="TestHandler",
            action_info=lambda ref: {"resref": ref} if ref in self.resources else None,
            resolve_power_entry=lambda book, actor, raw: {"SpellResRef": self.selection} if raw else None,
            prepare_action_entry=self.prepare,
            begin_manifest=self.reserve_or_commit,
            cancel_pending=lambda actor: self.transactions.cancel("Psionics", actor),
        )
        self.core._handlers = lambda: [self.handler]

    def register(self, callback):
        self.callback = callback

    def prepare(self, book, actor, entry):
        if self.replacement:
            entry["CastResRef"] = self.replacement
        return entry

    def reserve_or_commit(self, actor, resource):
        def commit():
            if self.commit_error:
                raise RuntimeError("commit failed")
            if self.commit_result:
                self.pool[actor] -= 5
                self.commits.append((actor, resource))
            return self.commit_result
        return self.transactions.begin(
            "Psionics", actor, resource, lambda: self.legal and self.pool[actor] >= 5, commit,
        )

    def test_click_only_reserves_accepted_event_commits_once(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertEqual(self.pool[1], 20)
        self.assertEqual(self.commits, [])
        self.assertTrue(self.callback(1, "pspower"))
        self.assertEqual(self.pool[1], 15)
        self.assertTrue(self.callback(1, "PSPOWER"))  # another accepted target
        self.assertEqual(self.commits, [(1, "PSPOWER")])
        self.assertEqual(self.pool[1], 15)

    def test_cancel_then_same_selection_is_a_new_reservation(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        # Escape produces no accepted-cast event. The next actual click must
        # replace the reservation, not impersonate the old second callback.
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertEqual(self.pool[1], 20)
        self.assertTrue(self.callback(1, "PSPOWER"))
        self.assertEqual(self.pool[1], 15)

    def test_unprepared_managed_cast_is_rejected(self):
        self.assertFalse(self.core.confirm_spell(1, "PSPOWER"))
        self.assertEqual(self.commits, [])

    def test_actor_and_exact_substitution_are_bound(self):
        self.selection, self.replacement = "CI8RKNI", "CI8RK3"
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertFalse(self.callback(2, "CI8RK3"))
        self.assertEqual(self.pool, {1: 20, 2: 20})
        self.assertTrue(self.callback(1, "CI8RK3"))
        self.assertEqual(self.commits, [(1, "CI8RKNI")])

    def test_wrong_resource_never_commits_even_if_it_is_native(self):
        for wrong in ("PSOTHER", "NATIVE"):
            with self.subTest(wrong=wrong):
                self.assertTrue(self.core.begin_spell(None, 1, 1))
                self.assertFalse(self.callback(1, wrong))
                self.assertEqual(self.pool[1], 20)
                self.assertFalse(self.callback(1, "PSPOWER"))

    def test_same_party_slot_with_different_actor_cannot_reuse_reservation(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.selected[:] = [1002]
        self.assertFalse(self.callback(1, "PSPOWER"))
        self.assertEqual(self.pool[1], 20)
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertTrue(self.callback(1, "PSPOWER"))
        self.assertEqual(self.pool[1], 15)

    def test_canonical_learning_and_dc_cost_survive_substitution(self):
        for selected, actual in (("PXL0001", "PXL0001"), ("PSMT03", "PSMT034")):
            with self.subTest(selected=selected):
                self.selection, self.replacement = selected, actual
                self.assertTrue(self.core.begin_spell(None, 1, 1))
                self.assertTrue(self.callback(1, actual))
                self.assertEqual(self.commits[-1], (1, selected))

    def test_legality_is_rechecked_and_failure_cannot_reserve_again(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.legal = False
        self.assertFalse(self.callback(1, "PSPOWER"))
        self.legal = True
        self.assertFalse(self.callback(1, "PSPOWER"))
        self.assertEqual(self.pool[1], 20)

    def test_failed_or_throwing_commit_clears_both_pending_states(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                self.commit_result, self.commit_error = False, raises
                self.assertTrue(self.core.begin_spell(None, 1, 1))
                if raises:
                    with self.assertRaisesRegex(RuntimeError, "commit failed"):
                        self.callback(1, "PSPOWER")
                else:
                    self.assertFalse(self.callback(1, "PSPOWER"))
                self.assertNotIn(1, self.core._pending_casts)
                self.assertEqual(self.transactions._pending, {})
                self.assertFalse(self.callback(1, "PSPOWER"))
                self.assertEqual(self.pool[1], 20)

    def test_native_selection_clears_stale_runtime_reservation(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertTrue(self.core.begin_spell(None, 1, 0))
        self.assertTrue(self.callback(1, "NATIVE"))
        self.assertEqual(self.pool[1], 20)
        self.assertFalse(self.callback(1, "PSPOWER"))

    def test_rest_and_explicit_cancellation_invalidate_confirmation(self):
        for cancel in (lambda: self.core.cancel_pending(1), self.core.restore_party):
            with self.subTest(cancel=cancel):
                self.assertTrue(self.core.begin_spell(None, 1, 1))
                cancel()
                self.assertFalse(self.callback(1, "PSPOWER"))
                self.assertEqual(self.pool[1], 20)

    def test_missing_engine_capability_fails_closed(self):
        del self.gemrb.SetSpellCastCheck
        self.assertFalse(self.core.begin_spell(None, 1, 1))
        self.assertEqual(self.core._pending_casts, {})
        self.assertEqual(self.transactions._pending, {})
        self.assertIn("SetSpellCastCheck", self.logs[-1][-1])
        self.assertTrue(self.core.begin_spell(None, 1, 0))  # native unaffected

    def test_unknown_internal_resource_uses_explicit_cast_without_learning(self):
        casts = []
        self.gemrb.SpellCast = lambda *args: casts.append(args)
        self.selection, self.replacement = "PSMT03", "PSMT034"
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.core.cast_spell(1, 255, 0)
        self.assertEqual(casts, [(1, -3, 0, "PSMT034")])
        self.assertEqual(self.pool[1], 20)  # target is not accepted yet
        self.core.cast_spell(1, -1, 0)
        self.assertEqual(casts[-1], (1, -1, 0))  # clear is not a cast
        self.assertTrue(self.callback(1, "PSMT034"))
        self.assertEqual(self.pool[1], 15)

    def test_native_and_unsubstituted_cast_arguments_are_unchanged(self):
        casts = []
        self.gemrb.SpellCast = lambda *args: casts.append(args)
        self.core.cast_spell(1, 4, 7)
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.core.cast_spell(1, 4, 8)
        self.assertEqual(casts, [(1, 4, 7), (1, 4, 8)])

    def test_patched_hook_does_not_cast_after_dispatcher_exception(self):
        installer = load("cast_installer", "common/tools/install_guiscripts.py")
        source = "def SpellPressed ():\n\tpc = 1\n\tSpell = GemRB.GetVar (\"Spell\")\n\tType = 4\n\tGemRB.SpellCast (pc, Type, Spell)\n"
        source = installer._patch_spell_pressed(source)
        self.gemrb.GetVar = lambda name: 0 if name == "SettingButtons" else 4000
        cast = []
        self.gemrb.SpellCast = lambda *args: cast.append(args)
        self.core._handlers = lambda: (_ for _ in ()).throw(RuntimeError("broken handler"))
        spellbook = types.SimpleNamespace(GetUsableMemorizedSpells=lambda *args: [{"SpellResRef": "PSPOWER", "SpellIndex": 4000}])
        namespace = {"GemRB": self.gemrb, "GemRBModCore": self.core, "Spellbook": spellbook}
        exec(compile(source, "patched-ActionsWindow.py", "exec"), namespace)
        namespace["SpellPressed"]()
        self.assertEqual(cast, [])
        self.assertIn("broken handler", self.logs[-1][-1])

    def test_error_abort_clears_actor_binding_and_transaction_only_for_actor(self):
        self.assertTrue(self.core.begin_spell(None, 1, 1))
        self.assertTrue(self.core.begin_spell(None, 2, 1))
        self.core.abort_action(1, RuntimeError("broken handler"))
        self.assertNotIn(1, self.core._pending_casts)
        self.assertNotIn(("Psionics", 1), self.transactions._pending)
        self.assertIn(2, self.core._pending_casts)
        self.assertIn(("Psionics", 2), self.transactions._pending)
        self.assertFalse(self.callback(1, "PSPOWER"))
        self.assertTrue(self.callback(2, "PSPOWER"))
        self.assertEqual(self.pool, {1: 20, 2: 15})


if __name__ == "__main__":
    unittest.main()
