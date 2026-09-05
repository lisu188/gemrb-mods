#!/usr/bin/env python3
import ast
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GUI = ROOT / "common/guiscripts"
ACTIONS = '''import GemRB

def SpellPressed():
	pc = GemRB.GameGetFirstSelectedActor ()
	Spell = GemRB.GetVar ("Spell")
	calls.append("cast")

def ActionQSpellPressed(which):
	pc = GemRB.GameGetFirstSelectedActor ()
	calls.append("direct-quickspell")

def ActionInnatePressed():
	GemRB.SetVar ("QSpell", None)

def ActionCastPressed():
	GemRB.SetVar ("QSpell", None)
'''


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fail(*args, **kwargs):
    raise RuntimeError("injected runtime failure")


class CastingRegression(unittest.TestCase):
    def setUp(self):
        self.variables = {"Spell": 4000, "SettingButtons": 0}
        self.calls = []
        self.entries = [{"SpellResRef": "PS1MTHR", "SpellIndex": 4000}]
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.GetVar = self.variables.get
        self.gemrb.SetVar = self.variables.__setitem__
        self.gemrb.GameGetFirstSelectedActor = lambda: 1
        self.gemrb.GetPCStats = lambda actor: {"QuickSpells": ["PS1MTHR"]}
        self.gemrb.GetSpelldata = lambda actor: ["PSVG01"]
        self.gemrb.Log = lambda *args: None
        self.transactions = load("review_transactions", GUI / "Transactions.py")
        self.core = load("review_core", GUI / "GemRBModCore.py")
        self.modules = patch.dict(sys.modules, {
            "GemRB": self.gemrb,
            "Transactions": self.transactions,
            "GemRBModCore": self.core,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.spellbook = types.SimpleNamespace(
            GetUsableMemorizedSpells=lambda actor, book: list(self.entries)
        )
        self.patcher = load("review_patcher", ROOT / "common/tools/install_guiscripts.py")
        source = self.patcher.render_patch(ACTIONS, "actions", Path("ActionsWindow.py"))
        self.actions = {"Spellbook": self.spellbook, "calls": self.calls}
        exec(compile(source, "ActionsWindow.py", "exec"), self.actions)

    def reserve(self):
        for namespace in ("Psionics", "Cipher"):
            self.transactions.begin(namespace, 1, ("old",), lambda: True)
        self.transactions.begin("Psionics", 2, ("other actor",), lambda: True)

    def assert_cancelled(self):
        self.assertEqual(self.calls, [])
        self.assertNotIn(("Psionics", 1), self.transactions._pending)
        self.assertNotIn(("Cipher", 1), self.transactions._pending)
        self.assertIn(("Psionics", 2), self.transactions._pending)

    def test_resolution_preparation_and_transaction_exceptions(self):
        for stage in ("resolve", "prepare", "commit"):
            with self.subTest(stage=stage):
                self.calls.clear()
                self.transactions.clear()
                self.reserve()
                handler = types.SimpleNamespace(
                    resolve_power_entry=lambda *args: dict(self.entries[0]),
                    prepare_action_entry=lambda sb, actor, entry: entry,
                    begin_manifest=lambda *args: True,
                )
                setattr(handler, {
                    "resolve": "resolve_power_entry",
                    "prepare": "prepare_action_entry",
                    "commit": "begin_manifest",
                }[stage], fail)
                self.core._handlers = lambda: [handler]
                self.actions["SpellPressed"]()
                self.assert_cancelled()

    def test_missing_handler_dependency_fails_closed(self):
        self.reserve()
        self.core._handlers = fail
        self.actions["SpellPressed"]()
        self.assert_cancelled()

    def test_logging_failure_cannot_resume_cast(self):
        self.reserve()
        self.core._handlers = fail
        self.gemrb.Log = fail
        self.actions["SpellPressed"]()
        self.assert_cancelled()

    def test_temporary_selector_failure_cannot_cast(self):
        self.reserve()
        self.variables["Spell"] = 255000
        self.core._handlers = fail
        self.actions["SpellPressed"]()
        self.assert_cancelled()

    def test_unresolvable_action_fails_closed(self):
        self.reserve()
        self.core._handlers = fail
        self.spellbook.GetUsableMemorizedSpells = fail
        self.actions["SpellPressed"]()
        self.assert_cancelled()

    def test_vanilla_spell_survives_unrelated_handler_failure(self):
        self.entries[0]["SpellResRef"] = "SPWI112"
        self.core._handlers = fail
        self.actions["SpellPressed"]()
        self.assertEqual(self.calls, ["cast"])

    def test_vanilla_quickslot_does_not_import_custom_handlers(self):
        self.gemrb.GetPCStats = lambda actor: {"QuickSpells": ["SPWI112"]}
        self.core._handlers = fail
        self.actions["ActionQSpellPressed"](0)
        self.assertEqual(self.calls, ["direct-quickspell"])

    def test_managed_quickslot_failures_do_not_fall_back(self):
        for stage in ("lookup", "refresh", "entries"):
            with self.subTest(stage=stage):
                self.calls.clear()
                self.transactions.clear()
                self.reserve()
                self.core.action_info = lambda ref: {"parent": ref, "innate_type": 2}
                self.core.cancel_pending = lambda actor: None
                self.core.refresh_innate_charges = lambda actor: None
                self.spellbook.GetUsableMemorizedSpells = lambda *args: self.entries
                if stage == "lookup":
                    self.core.action_info = fail
                elif stage == "refresh":
                    self.core.refresh_innate_charges = fail
                else:
                    self.spellbook.GetUsableMemorizedSpells = fail
                self.actions["ActionQSpellPressed"](0)
                self.assert_cancelled()

    def test_unknown_quickslot_failure_fails_closed(self):
        self.reserve()
        self.gemrb.GetPCStats = fail
        self.actions["ActionQSpellPressed"](0)
        self.assert_cancelled()

    def test_upgrade_replaces_owned_hooks_without_replacing_backup(self):
        current = self.patcher.render_patch(ACTIONS, "actions", Path("ActionsWindow.py"))
        legacy = current.replace("GemRBModCore.spell_error(", "LegacyCore.spell_error(")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ActionsWindow.py"
            target.write_text(ACTIONS)
            self.patcher.apply_patch(target, legacy)
            upgraded = self.patcher.render_patch(target.read_text(), "actions", target)
            self.assertIsNotNone(upgraded)
            self.patcher.apply_patch(target, upgraded)
            self.assertNotIn("LegacyCore", target.read_text())
            self.assertEqual(target.read_text().count(self.patcher.MARK_BEGIN), 4)
            self.assertEqual(target.with_suffix(".py" + self.patcher.CORE_BACKUP_SUFFIX).read_text(), ACTIONS)
            self.assertIsNone(self.patcher.render_patch(target.read_text(), "actions", target))
            self.patcher.remove_patch(target)
            self.assertEqual(target.read_text(), ACTIONS)


class HitPointRegression(unittest.TestCase):
    def body_function(self, hp, maximum):
        state = {"hp": hp, "maximum": maximum, "effects": []}

        def apply(actor, opcode, amount, mode, *args):
            state["effects"].append((opcode, amount, mode))
            if opcode == "MaximumHPModifier":
                state["maximum"] += amount
                if mode == 0:
                    state["hp"] += amount
                else:
                    self.assertEqual(mode, 3)
            elif opcode == "CurrentHPModifier":
                state["hp"] = min(state["maximum"], state["hp"] + amount)
            else:
                self.fail(opcode)

        source = ROOT / "psion/guiscripts/Psionics.py"
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_apply_body_hp")
        namespace = {"GemRB": types.SimpleNamespace(ApplyEffect=apply)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        return namespace["_apply_body_hp"], state

    def test_injured_body_grants_current_hp_once(self):
        apply, state = self.body_function(10, 50)
        apply(1, 6)
        self.assertEqual((state["hp"], state["maximum"]), (16, 56))
        apply(1, 2)
        self.assertEqual((state["hp"], state["maximum"]), (18, 58))

    def test_full_body_grants_both_values_once(self):
        apply, state = self.body_function(50, 50)
        apply(1, 6)
        self.assertEqual((state["hp"], state["maximum"]), (56, 56))

    def test_zero_and_negative_body_grants_are_noops(self):
        apply, state = self.body_function(10, 50)
        apply(1, 0)
        apply(1, -2)
        self.assertEqual(state["effects"], [])

    def test_vigor_uses_maximum_only_mode_and_one_instant_heal(self):
        source = (ROOT / "psion/lib/mind-vigor-augment.tpa").read_text()
        effects = re.findall(r"LPF ADD_SPELL_EFFECT INT_VAR (opcode = (?:17|18)\b[^\n]+) END", source)
        self.assertEqual(len(effects), 2)
        maximum = next(effect for effect in effects if effect.startswith("opcode = 18 "))
        current = next(effect for effect in effects if effect.startswith("opcode = 17 "))
        self.assertIn("parameter2 = 3", maximum)
        self.assertIn("timing = 0 duration = 60", maximum)
        self.assertIn("parameter1 = ps_vigor_hp", maximum)
        self.assertIn("parameter1 = ps_vigor_hp timing = 1", current)
        self.assertIn("ps_strip_cost <= psion_max_augment_cost", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
