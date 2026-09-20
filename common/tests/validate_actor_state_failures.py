#!/usr/bin/env python3
"""Unreadable actor state must not become a fresh character or a free choice."""
from pathlib import Path
import copy
import importlib.util
import re
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


class Table:
    def __init__(self, path):
        lines = [line.split("//", 1)[0].split() for line in path.read_text().splitlines()]
        lines = [line for line in lines if line]
        self.columns = [column.upper() for column in lines[2]]
        self.rows = {row[0].upper(): row[1:] for row in lines[3:]}

    def GetValue(self, row, column, *args):
        if isinstance(row, int):
            row = self.GetRowName(row)
        if isinstance(column, str):
            column = self.columns.index(column.upper())
        return self.rows[str(row).upper()][column]

    def GetRowCount(self):
        return len(self.rows)

    def GetRowName(self, index):
        return list(self.rows)[index]


class ActorStateFailures(unittest.TestCase):
    def setUp(self):
        self.effects = {1: [], 2: [], 3: []}
        self.known = {1: [], 2: [], 3: []}
        self.stats = {}
        self.writes = []
        self.effect_error = None
        self.count_error = False
        self.entry_error = None
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.GetEffects = self.get_effects
        self.gemrb.DispelEffect = self.dispel
        self.gemrb.ApplyEffect = self.apply
        self.gemrb.GetPlayerStat = lambda actor, stat, *args: self.stats.get((actor, stat), {34: 1, 38: 16, 39: 14, 41: 14}.get(stat, 0))
        self.gemrb.SetPlayerStat = self.set_stat
        self.gemrb.GetKnownSpellsCount = self.known_count
        self.gemrb.GetKnownSpell = self.known_entry
        self.gemrb.LearnSpell = lambda *args: self.writes.append(("learn", args)) or 0
        self.gemrb.RemoveSpell = lambda *args: self.writes.append(("remove", args))
        self.gemrb.ApplySpell = lambda *args: self.writes.append(("spell", args))
        self.gemrb.Log = lambda *args: None
        self.gemrb.GetSelectedActors = lambda: [1001]
        self.gemrb.SetSpellCastCheck = lambda callback: None
        self.gemrb.GetSpell = lambda *args: None
        self.tables = {}
        for mod in ("psion", "cipher"):
            text = (ROOT / mod / f"setup-{mod}.tp2").read_text()
            for source, target in re.findall(r"COPY\s+~([^~]+\.2da)~\s+~override/([^~]+\.2da)~", text):
                self.tables[Path(target).stem.casefold()] = Table(ROOT / source)
        self.gemrb.LoadTable = lambda name, *args: self.tables[name.casefold()]
        gui = types.ModuleType("GUICommon")
        gui.GetClassRowName = lambda actor: {1: "PSION_SEER", 2: "CIPHER", 3: "SORCERER_MONK"}[actor]
        spells = types.ModuleType("ie_spells")
        spells.LS_MEMO = 1
        self.modules = patch.dict(sys.modules, {"GemRB": self.gemrb, "GUICommon": gui, "ie_spells": spells})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        for name in ("Transactions", "PersistentState", "InnateCharges", "Selectors"):
            sys.modules[name] = load(name, f"common/guiscripts/{name}.py")
        self.state = sys.modules["PersistentState"]
        self.transactions = sys.modules["Transactions"]
        self.psion = load("Psionics", "psion/guiscripts/Psionics.py")
        self.cipher = load("Cipher", "cipher/guiscripts/Cipher.py")
        self.core = load("GemRBModCore", "common/guiscripts/GemRBModCore.py")
        self.core._handlers = lambda: [self.psion, self.cipher]

    def get_effects(self, actor, opcode):
        if self.effect_error:
            raise self.effect_error
        return copy.deepcopy([effect for effect in self.effects[actor] if effect["Opcode"] == opcode])

    def apply(self, actor, opcode, p1, p2, r1="", r2="", r3="", source="", *args):
        self.writes.append(("apply", actor, p1, p2))
        self.effects[actor].append({"Opcode": opcode, "Param1": p1, "Param2": p2, "Resource1": r1})

    def dispel(self, actor, opcode, marker):
        self.writes.append(("dispel", actor, marker))
        self.effects[actor] = [effect for effect in self.effects[actor] if not (effect["Opcode"] == opcode and effect["Param2"] == marker)]

    def set_stat(self, actor, stat, value):
        self.writes.append(("stat", actor, stat, value))
        self.stats[actor, stat] = value

    def known_count(self, actor, *args):
        if self.count_error:
            raise RuntimeError("known spell count unavailable")
        return len(self.known[actor])

    def known_entry(self, actor, book, level, index):
        if index == self.entry_error:
            raise RuntimeError("known spell entry unavailable")
        return {"SpellResRef": self.known[actor][index]}

    def seed(self, marker, resource, value, actor=1):
        self.effects[actor].append({"Opcode": "Protection:Spell", "Param1": value, "Param2": marker, "Resource1": resource})

    def test_missing_state_and_saved_zero_remain_distinct(self):
        self.assertEqual(self.state.read(1, "Protection:Spell", 7, "STATE"), (False, 0))
        self.seed(7, "state", 0)
        self.assertEqual(self.state.read(1, "Protection:Spell", 7, "STATE"), (True, 0))
        self.assertEqual(self.state.read(2, "Protection:Spell", 7, "STATE"), (False, 0))
        self.assertEqual(self.writes, [])

    def test_unreadable_state_is_not_absence(self):
        for error in (RuntimeError("engine read failed"), OSError("actor unavailable")):
            with self.subTest(error=type(error).__name__):
                self.effect_error = error
                with self.assertRaises(RuntimeError):
                    self.state.read(1, "Protection:Spell", 7, "STATE")
        self.assertEqual(self.writes, [])

    def test_malformed_matching_state_is_not_absence(self):
        self.seed(7, "STATE", "invalid")
        with self.assertRaises(RuntimeError):
            self.state.read(1, "Protection:Spell", 7, "STATE")
        self.assertEqual(self.writes, [])

    def test_failed_pool_read_cannot_refill_or_write_cache(self):
        psion = self.psion
        self.seed(psion.POOL_EFFECT_MARKER, psion.POOL_EFFECT_RESOURCE, 0)
        before = copy.deepcopy(self.effects)
        self.effect_error = RuntimeError("saved PP unavailable")
        with patch.object(psion, "maximum_pool", return_value=4):
            with self.assertRaises(RuntimeError):
                psion.ensure_pool(1)
        self.assertEqual(self.effects, before)
        self.assertEqual(self.writes, [])
        self.effect_error = None
        self.assertEqual(psion.ensure_pool(1), 0)

    def test_saved_pool_recovers_after_read_failure_without_free_refill(self):
        psion = self.psion
        self.seed(psion.POOL_EFFECT_MARKER, psion.POOL_EFFECT_RESOURCE, 2)
        self.effect_error = RuntimeError("temporary state failure")
        with self.assertRaises(RuntimeError):
            psion.ensure_pool(1)
        self.assertEqual(self.writes, [])
        self.effect_error = None
        self.assertEqual(psion.ensure_pool(1), 2)
        self.assertEqual(psion.maximum_pool(1), 3)

    def test_focus_read_error_cannot_grant_focus(self):
        psion = self.psion
        self.seed(psion.FOCUS_EFFECT_MARKER, psion.FOCUS_EFFECT_RESOURCE, 0)
        before = copy.deepcopy(self.effects)
        self.effect_error = RuntimeError("focus unavailable")
        with patch.object(psion, "ensure_pool", return_value=2):
            with self.assertRaises(RuntimeError):
                psion.ensure_focus(1)
        self.assertEqual(self.effects, before)
        self.assertEqual(self.writes, [])

    def test_feat_read_error_cannot_reset_existing_rank(self):
        self.effect_error = RuntimeError("feat state unavailable")
        with self.assertRaises(RuntimeError):
            self.psion.feat_rank(1, self.psion.PSIONIC_TALENT)
        self.assertEqual(self.writes, [])

    def test_skill_read_error_cannot_initialize_new_credits(self):
        self.effect_error = RuntimeError("skill state unavailable")
        with self.assertRaises(RuntimeError):
            self.psion.sync_skill_points(1)
        self.assertEqual(self.writes, [])

    def test_personality_read_error_cannot_authorize_second_choice(self):
        psion = self.psion
        self.seed(psion.PSICRYSTAL_PERSONALITY_MARKER, psion.PSICRYSTAL_PERSONALITY_RESOURCE, 4)
        self.effect_error = RuntimeError("personality unavailable")
        with self.assertRaises(RuntimeError):
            psion.can_choose_psicrystal(1, "PXCSING")
        with self.assertRaises(RuntimeError):
            psion._choose_psicrystal(1, "PXCSING")
        self.assertEqual(self.writes, [])

    def test_confirmation_read_error_vetoes_choice_and_clears_reservation(self):
        book = types.SimpleNamespace(GetUsableMemorizedSpells=lambda actor, kind: [{"SpellIndex": 4000, "SpellResRef": "PXCSING"}])
        self.assertTrue(self.core.begin_spell(book, 1, 4000))
        self.assertEqual(self.writes, [])
        self.effect_error = RuntimeError("state disappeared before confirmation")
        with self.assertRaises(RuntimeError):
            self.core.confirm_spell(1, "PXCSING")
        self.assertEqual(self.writes, [])
        self.assertNotIn(1, self.core._pending_casts)
        self.assertEqual(self.transactions._pending, {})
        self.effect_error = None
        self.assertFalse(self.core.confirm_spell(1, "PXCSING"))

    def test_unreadable_known_count_cannot_grant_power_learning_credit(self):
        self.count_error = True
        for handler, actor, choice in ((self.psion, 1, "PXL0007"), (self.cipher, 2, "CIL0002")):
            with self.subTest(handler=handler.__name__):
                with self.assertRaises(RuntimeError):
                    handler.can_learn_power(actor, choice)
                with self.assertRaises(RuntimeError):
                    handler._learn_power(actor, choice)
        self.assertEqual(self.writes, [])

    def test_partial_known_scan_never_returns_a_smaller_known_set(self):
        for handler, actor, known in ((self.psion, 1, ["PS1IARM", "PS1FSCR", "PS1EMND"]), (self.cipher, 2, ["SPIN999", "CI1WHSP"])):
            with self.subTest(handler=handler.__name__):
                self.known[actor] = known
                self.entry_error = 1
                with self.assertRaises(RuntimeError):
                    handler.known_power_refs(actor)
        self.assertEqual(self.writes, [])

    def test_native_sorcerer_monk_spell_does_not_read_psion_state(self):
        self.effect_error = RuntimeError("unrelated state read")
        self.count_error = True
        book = types.SimpleNamespace(GetUsableMemorizedSpells=lambda actor, kind: [{"SpellIndex": 2000, "SpellResRef": "SPWI112"}])
        self.assertTrue(self.core.begin_spell(book, 3, 2000))
        self.assertTrue(self.core.confirm_spell(3, "SPWI112"))
        self.assertEqual(self.writes, [])


if __name__ == "__main__":
    unittest.main()
