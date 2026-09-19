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


if __name__ == "__main__":
    unittest.main()
