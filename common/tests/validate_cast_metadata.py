#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class MissingCastMetadataTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("metadata_core", ROOT / "common/guiscripts/GemRBModCore.py")
        self.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.core)
        self.core._handlers = lambda: []
        self.logs = []
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.Log = lambda *args: self.logs.append(args)
        self.gemrb.GetSpelldata = lambda actor: ["PXL0001"]
        self.patcher = patch.dict(sys.modules, {"GemRB": self.gemrb})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.rows = [{"SpellResRef": "PS1MTHR", "SpellIndex": 4003}]
        self.book = types.SimpleNamespace(GetUsableMemorizedSpells=lambda actor, book: self.rows)

    def test_orphaned_power_cannot_begin_before_any_engine_callback_is_registered(self):
        for resref in ("PS1MTHR", "CI1MMIS", "PXL0001", "CI8RK3", "PSMT034"):
            with self.subTest(resref=resref):
                self.rows[0]["SpellResRef"] = resref
                self.assertFalse(self.core.begin_spell(self.book, 1, 4003))
                self.assertEqual(self.core._pending_casts, {})

    def test_missing_handler_metadata_cannot_be_mistaken_for_a_native_action(self):
        handler = types.SimpleNamespace(resolve_power_entry=lambda *args: None, action_info=lambda ref: None)
        self.core._handlers = lambda: [handler]
        self.assertFalse(self.core.begin_spell(self.book, 1, 4003))
        self.assertFalse(self.core.confirm_spell(1, "PS1MTHR"))

    def test_unprepared_internal_resources_fail_closed_without_rule_tables(self):
        for resref in ("ps1mthr", "CI1MMIS", "PXL0001", "CI8RK3", "PSMT034"):
            with self.subTest(resref=resref):
                self.assertFalse(self.core.confirm_spell(1, resref))
                self.assertIn(resref.upper(), self.logs[-1][-1])

    def test_native_sorcerer_monk_spells_remain_available(self):
        for resref in ("SPWI103", "SPIN101", "OTHER123"):
            with self.subTest(resref=resref):
                self.rows[0]["SpellResRef"] = resref
                self.assertTrue(self.core.begin_spell(self.book, 1, 4003))
                self.assertTrue(self.core.confirm_spell(1, resref))

    def test_temporary_learning_selector_cannot_bypass_missing_metadata(self):
        self.assertFalse(self.core.begin_spell(self.book, 1, 255000))
        self.gemrb.GetSpelldata = lambda actor: ["SPWI103"]
        self.assertTrue(self.core.begin_spell(self.book, 1, 255000))

    def test_empty_or_ambiguous_selection_fails_closed(self):
        for rows in ([], [{"SpellIndex": 4003}], [
            {"SpellResRef": "SPWI103", "SpellIndex": 4003},
            {"SpellResRef": "CI1MMIS", "SpellIndex": 4003},
        ]):
            with self.subTest(rows=rows):
                self.rows = rows
                self.assertFalse(self.core.begin_spell(self.book, 1, 4003))

    def test_unreadable_spellbook_is_not_authorization_to_cast(self):
        self.book.GetUsableMemorizedSpells = lambda *args: (_ for _ in ()).throw(RuntimeError("unavailable"))
        self.assertFalse(self.core.begin_spell(self.book, 1, 4003))

    def test_confirmation_does_not_depend_on_metadata_lookup(self):
        self.core.action_info = lambda ref: (_ for _ in ()).throw(AssertionError("metadata lookup must not authorize an unprepared cast"))
        self.assertFalse(self.core.confirm_spell(1, "CI1MMIS"))
        self.assertTrue(self.core.confirm_spell(1, "SPWI103"))

    def test_quickslots_reject_orphan_powers_before_callback_registration(self):
        spec = importlib.util.spec_from_file_location("metadata_installer", ROOT / "common/tools/install_guiscripts.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        source = "def ActionQSpellPressed (which):\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tGemRB.SpellCast (pc, -2, which)\n"
        source = installer._patch_quickspell(source)
        self.gemrb.GameGetFirstSelectedActor = lambda: 1
        casts = []
        self.gemrb.SpellCast = lambda *args: casts.append(args)
        namespace = {"GemRB": self.gemrb, "GemRBModCore": self.core, "Spellbook": self.book}
        exec(compile(source, "patched-quickspell.py", "exec"), namespace)
        transactions = types.SimpleNamespace(cancel=lambda *args: None)
        with patch.dict(sys.modules, {"Transactions": transactions}):
            for resref in ("PS1MTHR", "CI1MMIS", "PXL0001", "SPWI103", "SPIN101"):
                with self.subTest(resref=resref):
                    casts.clear()
                    self.gemrb.GetPCStats = lambda actor: {"QuickSpells": [resref]}
                    namespace["ActionQSpellPressed"](0)
                    self.assertEqual(casts, [] if self.core.is_managed_action(resref) else [(1, -2, 0)])

    def test_native_known_wizard_selection_preserves_wild_magic(self):
        self.book.UAW_ALLMAGE = 5
        self.book.IE_SPELL_TYPE_WIZARD = 1
        self.book.GetKnownSpells = lambda actor, book: [{"SpellResRef": "SPWI103"}]
        self.gemrb.GetVar = lambda name: 5 if name == "ActionLevel" else 3
        self.rows = []
        self.assertTrue(self.core.begin_spell(self.book, 1, 2000))
        self.assertTrue(self.core.confirm_spell(1, "SPWI103"))
        self.assertFalse(self.core.begin_spell(self.book, 1, 4000))
        self.assertFalse(self.core.begin_spell(self.book, 1, 2001))

    def test_known_wizard_mode_does_not_authorize_managed_powers(self):
        self.book.UAW_ALLMAGE = 5
        self.book.IE_SPELL_TYPE_WIZARD = 1
        self.book.GetKnownSpells = lambda actor, book: [{"SpellResRef": "PS1MTHR"}]
        self.gemrb.GetVar = lambda name: 5 if name == "ActionLevel" else 3
        self.rows = [{"SpellResRef": "SPWI103", "SpellIndex": 2000}]
        self.assertFalse(self.core.begin_spell(self.book, 1, 2000))

    def test_ordinary_casting_cannot_fall_back_to_known_wizard_spells(self):
        self.book.UAW_ALLMAGE = 5
        self.book.IE_SPELL_TYPE_WIZARD = 1
        self.book.GetKnownSpells = lambda actor, book: [{"SpellResRef": "SPWI103"}]
        self.gemrb.GetVar = lambda name: 2 if name == "ActionLevel" else 3
        self.rows = []
        self.assertFalse(self.core.begin_spell(self.book, 1, 2000))


if __name__ == "__main__":
    unittest.main()
