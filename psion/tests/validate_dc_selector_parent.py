#!/usr/bin/env python3
"""Keep native temporary DC choices authorized after the parent charge is spent."""
from pathlib import Path
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemporaryDCParentTests(unittest.TestCase):
    def setUp(self):
        fixture = load('dc_selector_tables', ROOT / 'psion/tests/validate_runtime.py')
        self.tables = {name: fixture.fake_table(source + '.2da') for name, source in {
            'pspowers': 'psionpowers', 'psaugmnt': 'psionaugment', 'pspick': 'pspick',
            'psfeatpk': 'psionfeatpick', 'psskill': 'psskill',
        }.items()}
        self.known = {1: [{'SpellResRef': 'PS1MTHR'}], 2: []}
        # A real parent selector cast consumes the charge before child input.
        self.memorized = [{'SpellResRef': 'PS1MTHR', 'Flags': 0}]
        self.stats = {38: 18, 34: 1}
        self.pool = 4
        self.class_row = 'PSION_SHAPER'
        self.spellinfo = ['PSMT01']
        self.casts = []
        self.usable_calls = []
        gemrb = types.ModuleType('GemRB')
        gemrb.GetPlayerStat = lambda actor, stat, *args: self.stats.get(stat, 0)
        gemrb.LoadTable = lambda name, *args: self.tables[name.lower()[:8]]
        gemrb.GetKnownSpellsCount = lambda actor, book, level: len(self.known[actor])
        gemrb.GetKnownSpell = lambda actor, book, level, index: dict(self.known[actor][index])
        gemrb.GetMemorizedSpellsCount = lambda *args: len(self.memorized)
        gemrb.GetMemorizedSpell = lambda actor, book, level, index: dict(self.memorized[index])
        gemrb.GetSpelldata = lambda actor: list(self.spellinfo)
        gemrb.GetSpelldataIndex = lambda *args: -1  # ordinary spells absent in temporary book
        gemrb.GetSelectedActors = lambda: [10001]
        gemrb.SetSpellCastCheck = lambda callback: None
        gemrb.GetEffects = lambda *args: []
        gemrb.GetSpell = lambda resource, *args: ({'SpellResRef': resource} if resource in ('PSMT014', 'PSMT024') else None)
        gemrb.DisplayString = lambda *args: None
        gemrb.Log = lambda *args: None
        gemrb.SpellCast = lambda *args: self.casts.append(args)
        self.gemrb = gemrb
        modules = patch.dict(sys.modules, {'GemRB': gemrb,
            'GUICommon': types.SimpleNamespace(GetClassRowName=lambda actor: self.class_row),
            'ie_spells': types.SimpleNamespace(LS_MEMO=8)})
        modules.start(); self.addCleanup(modules.stop)
        for name in ('Transactions', 'InnateCharges', 'PersistentState', 'Selectors'):
            sys.modules[name] = load(name, ROOT / 'common/guiscripts' / (name + '.py'))
        self.psion = load('selector_psion', ROOT / 'psion/guiscripts/Psionics.py')
        self.psion._pool_snapshot = lambda actor: self.pool
        self.core = load('selector_core', ROOT / 'common/guiscripts/GemRBModCore.py')
        self.core._handlers = lambda: [self.psion]
        def unusable(actor, book):
            self.usable_calls.append((actor, book))
            return []
        self.book = types.SimpleNamespace(GetUsableMemorizedSpells=unusable)

    def test_native_depleted_parent_and_missing_ordinary_index_allow_known_child(self):
        self.assertTrue(self.core.begin_spell(self.book, 1, 255000))
        self.assertEqual(self.core._pending_casts[1]['selected'], 'PSMT01')
        self.assertEqual(self.core._pending_casts[1]['cast'], 'PSMT014')
        self.core.cast_spell(1, 255, 0)
        self.assertEqual(self.casts, [(1, -3, 0, 'PSMT014')])
        self.assertEqual(self.usable_calls, [])
        self.assertEqual(self.memorized, [{'SpellResRef': 'PS1MTHR', 'Flags': 0}])
        self.assertEqual(self.known[1], [{'SpellResRef': 'PS1MTHR'}])
        self.assertEqual(self.pool, 4)  # preparation neither spends nor replenishes PP

    def test_temporary_child_never_queries_the_ordinary_usable_book(self):
        def fail(*args): raise AssertionError('Temporary book has no ordinary indices')
        self.book.GetUsableMemorizedSpells = fail
        self.assertTrue(self.core.begin_spell(self.book, 1, 255000))

    def test_unlearned_parent_and_another_actors_known_parent_are_rejected(self):
        self.assertFalse(self.core.begin_spell(self.book, 2, 255000))
        self.known[1] = [{'SpellResRef': 'PSMT01'}, {'SpellResRef': 'PS1VIGR'}]
        self.assertFalse(self.core.begin_spell(self.book, 1, 255000))
        self.assertEqual(self.core._pending_casts, {})
        self.assertEqual(self.casts, [])

    def test_unreadable_known_book_does_not_authorize_child(self):
        def fail(*args): raise RuntimeError('native known book unavailable')
        self.gemrb.GetKnownSpell = fail
        with self.assertRaisesRegex(RuntimeError, 'known-power scan failed'):
            self.core.begin_spell(self.book, 1, 255000)
        self.assertEqual(self.core._pending_casts, {})

    def test_existing_class_discipline_intelligence_level_and_pp_gates_still_apply(self):
        for gate in ('class', 'discipline', 'intelligence', 'level', 'pp'):
            with self.subTest(gate=gate):
                self.class_row = 'FIGHTER' if gate == 'class' else 'PSION_SHAPER'
                self.tables['pspowers'].values['PS1MTHR']['DISCIPLINE'] = 'TELEPATH' if gate == 'discipline' else 'GENERAL'
                self.stats[38] = 10 if gate == 'intelligence' else 18
                self.spellinfo[:] = ['PSMT02' if gate == 'level' else 'PSMT01']
                self.pool = 0 if gate == 'pp' else 4
                self.assertFalse(self.core.begin_spell(self.book, 1, 255000))
                self.assertEqual(self.core._pending_casts, {})
                self.assertEqual(self.casts, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
