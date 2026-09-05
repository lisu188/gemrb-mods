#!/usr/bin/env python3
"""Upgrade recognized shared cast hooks without removing sibling ownership."""
from pathlib import Path
import ast
import importlib.util
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Exact previously shipped block, including its exception fall-through.
OLD_HOOK = '''\t# GEMRB MOD CORE BEGIN
\tif GemRB.GetVar("SettingButtons"):
\t\tGemRBModCore.cancel_pending(pc)
\telse:
\t\ttry:
\t\t\traw_spell = GemRB.GetVar("Spell")
\t\t\tif not GemRBModCore.begin_spell(Spellbook, pc, raw_spell):
\t\t\t\treturn
\t\texcept Exception as error:
\t\t\tGemRB.Log(2, "GemRBModCore", str(error))
\t# GEMRB MOD CORE END

'''

OLD_QUICK = '''\t# GEMRB MOD CORE BEGIN
\ttry:
\t\tpcStats = GemRB.GetPCStats(pc)
\t\tquickResRef = ""
\t\tif pcStats and 0 <= which < len(pcStats["QuickSpells"]):
\t\t\tquickResRef = pcStats["QuickSpells"][which]
\t\tquickInfo = GemRBModCore.action_info(quickResRef)
\t\tif quickInfo:
\t\t\tGemRBModCore.cancel_pending(pc)
\t\t\tGemRBModCore.refresh_innate_charges(pc)
\t\t\tentry = None
\t\t\tfor candidate in Spellbook.GetUsableMemorizedSpells(pc, quickInfo["innate_type"]):
\t\t\t\tif candidate.get("SpellResRef", "").upper() == quickInfo["parent"].upper():
\t\t\t\t\tentry = candidate
\t\t\t\t\tbreak
\t\t\tif not entry:
\t\t\t\treturn
\t\t\tGemRB.SetVar("QSpell", None)
\t\t\tGemRB.SetVar("Spell", entry["SpellIndex"])
\t\t\tGemRB.SetVar("Type", 1 << quickInfo["innate_type"])
\t\t\tSpellPressed()
\t\t\treturn
\texcept Exception as error:
\t\tGemRB.Log(2, "GemRBModCore", "quickspell routing failed: %s" % error)
\t# GEMRB MOD CORE END

'''


class SharedHookUpgrade(unittest.TestCase):
    def setUp(self):
        self.installer = load("upgrade_installer", "common/tools/install_guiscripts.py")
        fixtures = load("upgrade_fixtures", "common/tests/validate.py")
        self.temp = tempfile.TemporaryDirectory(prefix="shared-hook-upgrade-")
        self.addCleanup(self.temp.cleanup)
        self.gui = Path(self.temp.name)
        self.originals = fixtures.fixture_texts()
        fixtures.write_fixture(self.gui, self.originals)
        self.installer.install_handler(self.gui, "SorcererMonkUI", ROOT / "sorcerer-monk/guiscripts/SorcererMonkUI.py")
        self.actions = self.gui / "ActionsWindow.py"
        self.backup = self.actions.with_suffix(".py" + self.installer.CORE_BACKUP_SUFFIX)
        self.baseline_backup = self.backup.read_bytes()

    def legacy(self, fail_closed=False, checked_call=False):
        hook = OLD_HOOK
        if fail_closed:
            hook = hook.replace('\t\t\tGemRB.Log(2, "GemRBModCore", str(error))\n',
                                '\t\t\tGemRB.Log(2, "GemRBModCore", str(error))\n\t\t\treturn\n')
        text = self.actions.read_text().replace(self.installer._spell_pressed_hook(), hook)
        text = text.replace(self.installer._quickspell_hook(), OLD_QUICK)
        if not checked_call:
            text = text.replace("GemRBModCore.cast_spell(pc, Type, Spell)", "GemRB.SpellCast (pc, Type, Spell)")
        text = "# unrelated user extension\n" + text
        text = text.replace('\tSpell = GemRB.GetVar ("Spell")', '\t# unrelated in-function extension\n\tSpell = GemRB.GetVar ("Spell")')
        self.actions.write_text(text)
        return text

    def install_cipher(self):
        self.installer.install_handler(self.gui, "Cipher", ROOT / "cipher/guiscripts/Cipher.py")

    def test_old_hook_upgrades_in_place_with_sibling_and_original_backup(self):
        self.legacy()
        self.install_cipher()
        actual = self.actions.read_text()
        self.assertIn(self.installer.CAST_CHECK_MARKER, actual)
        self.assertIn(self.installer.QUICK_CHECK_MARKER, actual)
        self.assertIn(self.installer._spell_pressed_hook(), actual)
        self.assertIn("GemRBModCore.cast_spell(pc, Type, Spell)", actual)
        self.assertNotIn("GemRB.SpellCast (pc, Type, Spell)", actual)
        self.assertIn("# unrelated user extension", actual)
        self.assertIn("# unrelated in-function extension", actual)
        self.assertEqual(self.backup.read_bytes(), self.baseline_backup)
        self.assertTrue((self.gui / ".gemrbmodcore.sorcerermonkui.active").exists())
        tree = ast.parse(actual)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "SpellPressed")
        handler = next(node for node in ast.walk(function) if isinstance(node, ast.ExceptHandler))
        self.assertIsInstance(handler.body[-1], ast.If)
        self.assertIsInstance(handler.body[-1].body[-1], ast.Return)
        self.install_cipher()
        self.assertEqual(self.actions.read_text(), actual, "upgrade must be idempotent")
        self.installer.uninstall_handler(self.gui, "Cipher")
        self.assertEqual(self.actions.read_text(), actual, "sibling retains updated shared hook")
        self.installer.uninstall_handler(self.gui, "SorcererMonkUI")
        self.assertEqual(self.actions.read_bytes(), self.baseline_backup)

    def test_intermediate_unversioned_checked_hook_upgrades(self):
        self.legacy(fail_closed=True, checked_call=True)
        self.install_cipher()
        self.assertIn(self.installer._spell_pressed_hook(), self.actions.read_text())
        self.assertEqual(self.backup.read_bytes(), self.baseline_backup)

    def test_upstream_and_previous_versioned_hooks_upgrade_exactly(self):
        for version in ("upstream", "v1"):
            with self.subTest(version=version):
                self.legacy()
                spell, quick = OLD_HOOK, OLD_QUICK
                if version == "upstream":
                    spell = spell.replace('\t\ttry:\n', '\t\traw_spell = None\n\t\ttry:\n').replace(
                        '\t\t\tGemRB.Log(2, "GemRBModCore", str(error))\n',
                        '\t\t\tif not GemRBModCore.spell_error(Spellbook, pc, raw_spell, error):\n\t\t\t\treturn\n')
                    quick = quick.replace('\t\tquickResRef = ""\n', '').replace(
                        '\ttry:\n', '\tquickResRef = ""\n\ttry:\n').replace(
                        '\t\tGemRB.Log(2, "GemRBModCore", "quickspell routing failed: %s" % error)\n',
                        '\t\tGemRBModCore.abort_action(pc, error)\n\t\tif not quickResRef or GemRBModCore.is_managed_action(quickResRef):\n\t\t\treturn\n')
                else:
                    spell = spell.replace('\t# GEMRB MOD CORE BEGIN\n', '\t# GEMRB MOD CORE BEGIN\n\t# GEMRB MOD CORE CAST CHECK v1\n').replace(
                        '\t\t\tGemRB.Log(2, "GemRBModCore", str(error))\n',
                        '\t\t\tGemRB.Log(2, "GemRBModCore", str(error))\n\t\t\treturn\n')
                    quick = quick.replace('\t# GEMRB MOD CORE BEGIN\n', '\t# GEMRB MOD CORE BEGIN\n\t# GEMRB MOD CORE QUICK CAST CHECK v1\n').replace(
                        '\t\tGemRB.Log(2, "GemRBModCore", "quickspell routing failed: %s" % error)\n',
                        '\t\tGemRB.Log(2, "GemRBModCore", "quickspell routing failed: %s" % error)\n\t\treturn\n')
                self.actions.write_text(self.actions.read_text().replace(OLD_HOOK, spell).replace(OLD_QUICK, quick))
                self.install_cipher()
                self.assertIn(self.installer._spell_pressed_hook(), self.actions.read_text())
                self.assertIn(self.installer._quickspell_hook(), self.actions.read_text())
                self.assertIn("# unrelated user extension", self.actions.read_text())
                self.assertEqual(self.backup.read_bytes(), self.baseline_backup)

    def test_unknown_owned_block_fails_without_overwriting_any_file(self):
        text = self.legacy().replace('raw_spell = GemRB.GetVar("Spell")', 'raw_spell = custom_selection()')
        self.actions.write_text(text)
        before = {str(path.relative_to(self.gui)): path.read_bytes() for path in self.gui.rglob("*") if path.is_file()}
        with self.assertRaisesRegex(RuntimeError, "unrecognized modified SpellPressed hook"):
            self.install_cipher()
        self.assertEqual({str(path.relative_to(self.gui)): path.read_bytes() for path in self.gui.rglob("*") if path.is_file()}, before)

    def test_unknown_native_boundary_fails_without_losing_backup(self):
        text = self.legacy().replace("GemRB.SpellCast (pc, Type, Spell)", "custom_cast(pc, Type, Spell)")
        self.actions.write_text(text)
        with self.assertRaisesRegex(RuntimeError, "cast boundary not recognized"):
            self.install_cipher()
        self.assertEqual(self.actions.read_text(), text)
        self.assertEqual(self.backup.read_bytes(), self.baseline_backup)

    def test_upgraded_quickslot_lookup_and_refresh_errors_cannot_fall_through(self):
        self.legacy()
        self.install_cipher()
        tree = ast.parse(self.actions.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "ActionQSpellPressed")
        for failure in ("lookup", "refresh"):
            with self.subTest(failure=failure):
                casts, logs = [], []

                def broken(*args):
                    raise RuntimeError("controlled " + failure + " failure")

                gemrb = types.SimpleNamespace(
                    GameGetFirstSelectedActor=lambda: 1,
                    GetPCStats=broken if failure == "lookup" else lambda pc: {"QuickSpells": ["POWER"]},
                    SpellCast=lambda *args: casts.append(args),
                    Log=lambda *args: logs.append(args),
                )
                core = types.SimpleNamespace(action_info=lambda ref: {"parent": ref},
                                             cancel_pending=lambda pc: None, refresh_innate_charges=broken,
                                             abort_action=lambda *args: logs.append(args),
                                             is_managed_action=lambda ref: True)
                namespace = {"GemRB": gemrb, "GemRBModCore": core, "UpdateActionsWindow": lambda: None}
                exec(compile(ast.Module(body=[function], type_ignores=[]), "upgraded-ActionsWindow.py", "exec"), namespace)
                namespace["ActionQSpellPressed"](0)
                self.assertEqual(casts, [])
                self.assertEqual(len(logs), 1)

    def test_unknown_quickslot_hook_fails_without_overwrite(self):
        text = self.legacy().replace("pcStats = GemRB.GetPCStats(pc)", "pcStats = custom_stats(pc)")
        self.actions.write_text(text)
        with self.assertRaisesRegex(RuntimeError, "unrecognized modified ActionQSpellPressed hook"):
            self.install_cipher()
        self.assertEqual(self.actions.read_text(), text)
        self.assertEqual(self.backup.read_bytes(), self.baseline_backup)


if __name__ == "__main__":
    unittest.main()
