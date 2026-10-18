#!/usr/bin/env python3
"""Exercise automatic companion maintenance and shared hook ownership."""
import ast
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


companions = load("sync_companions", "psion/tests/validate_psicrystal_companion.py")
installer = load("sync_installer", "common/tools/install_guiscripts.py")
lifecycle = load("sync_lifecycle", "common/tests/validate.py")


class PartySyncTests(unittest.TestCase):
    def setUp(self):
        self.fx = companions.CompanionTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.core = self.fx.fx.core
        self.psion = self.fx.psion
        self.timers = []
        self.logs = []
        self.available = True
        self.fx.gemrb.SetTimer = lambda *args: self.timers.append(args)
        self.fx.gemrb.Log = lambda *args: self.logs.append(args)
        self.gui = sys.modules["GUICommon"]
        self.gui.GameControl = types.SimpleNamespace(GetFrame=self.frame)

    def frame(self):
        if not self.available:
            raise RuntimeError("GameControl unavailable")
        return {}

    def test_redraws_and_periodic_callbacks_share_one_timer(self):
        body = self.fx.manifest()
        self.fx.fx.stats[body, 0] = 3
        self.fx.bodies[1]["InArea"] = False
        self.core._pending_casts[1] = {"selected": "PS1CHAR"}
        pending = copy.deepcopy(self.core._pending_casts)
        effects = copy.deepcopy(self.fx.fx.effects)
        transactions = copy.deepcopy(self.fx.fx.transactions._pending)
        writes = list(self.fx.fx.writes)
        for _ in range(5):
            self.core.sync_party()
        self.assertTrue(self.fx.bodies[1]["InArea"])
        self.assertEqual(len(self.timers), 1)
        callback, interval, repeats = self.timers[0]
        self.assertEqual((interval, repeats), (1000, -1))
        self.assertIs(callback, self.core.sync_party)
        self.fx.bodies[1]["InArea"] = False
        callback()
        self.assertTrue(self.fx.bodies[1]["InArea"])
        self.assertEqual(self.fx.fx.stats[body, 0], 3)
        self.assertEqual(self.fx.bodies[1]["ActorID"], body)
        self.assertEqual(sum(mode == 1 for _, mode in self.fx.calls), 1)
        self.assertEqual(self.fx.fx.writes, writes)
        self.assertEqual(self.fx.fx.effects, effects)
        self.assertEqual(self.core._pending_casts, pending)
        self.assertEqual(self.fx.fx.transactions._pending, transactions)

    def test_timer_skips_menu_and_requeries_party_after_load(self):
        old_body = self.fx.manifest()
        self.core.sync_party()
        callback = self.timers[0][0]
        self.available = False
        calls = list(self.fx.calls)
        callback()
        self.core.sync_party()
        self.assertEqual(self.fx.calls, calls)
        self.available = True
        self.fx.gemrb.GetPartySize = lambda: 1
        new_body = old_body + 100
        self.fx.fx.effects[new_body] = []
        self.fx.fx.stats[new_body, 0] = 7
        self.fx.bodies = {1: {"ActorID": new_body, "Alive": True, "InArea": False}}
        callback()
        self.assertEqual(self.fx.calls[len(calls):], [(1, 3)])
        self.assertTrue(self.fx.bodies[1]["InArea"])
        self.assertEqual(self.fx.fx.stats[new_body, 0], 7)
        self.assertEqual(len(self.timers), 1)
        self.assertNotIn(4, self.fx.bodies)

    def test_unselected_owner_death_is_detected_without_innate_refresh(self):
        self.fx.manifest()
        self.core.sync_party()
        # Selection remains on another actor; synchronization scans the party.
        self.fx.gemrb.GetSelectedActors = lambda: [2002]
        self.fx.fx.stats[1, 0] = 0
        self.timers[0][0]()
        self.assertNotIn(1, self.fx.bodies)
        self.assertTrue(self.psion._psicrystal_used(1))
        self.assertEqual(sum(mode == 1 for _, mode in self.fx.calls), 1)

    def test_absent_optional_sync_handler_does_not_register_timer(self):
        self.core._handlers = lambda: [types.SimpleNamespace()]
        self.core.sync_party()
        self.assertEqual(self.timers, [])

    def test_failure_does_not_duplicate_or_disable_timer(self):
        self.core.sync_party()
        callback = self.timers[0][0]
        def broken():
            raise RuntimeError("unavailable companion state")
        self.core._handlers = lambda: [types.SimpleNamespace(sync_party=broken)]
        callback()
        self.assertIn("unavailable companion state", self.logs[-1][-1])
        self.assertFalse(self.core._party_sync_running)
        self.core._handlers = lambda: [self.psion]
        callback()
        self.assertEqual(len(self.timers), 1)

    def test_rendered_hook_runs_after_guard_for_every_selection_size(self):
        text = lifecycle.fixture_texts()["ActionsWindow.py"]
        text = text.replace("\t\treturn\n\ndef ActionQSpellPressed", "\t\treturn\n\tif GemRB.GetSelectedSize() != 1:\n\t\treturn\n\ndef ActionQSpellPressed", 1)
        text = installer.render_patch(text, "actions", Path("ActionsWindow.py"))
        function = next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == "UpdateActionsWindow")
        namespace = {"GemRB": self.fx.gemrb, "GemRBModCore": self.core, "GUICommon": self.gui}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "ActionsWindow.py", "exec"), namespace)
        self.available = False
        namespace["UpdateActionsWindow"]()
        self.assertEqual(self.timers, [])
        self.available = True
        for selected in (0, 1, 2):
            self.fx.gemrb.GetSelectedSize = lambda: selected
            namespace["UpdateActionsWindow"]()
        self.assertEqual(len(self.timers), 1)


class PartySyncInstallerTests(unittest.TestCase):
    def test_fresh_upgrade_reinstall_and_every_sibling_uninstall_order(self):
        handlers = ("Psionics", "Cipher")
        runtime = {"Psionics": ROOT / "psion/guiscripts/Psionics.py",
                   "Cipher": ROOT / "cipher/guiscripts/Cipher.py"}
        for first, second in (handlers, handlers[::-1]):
            for remove_first, remove_second in (handlers, handlers[::-1]):
                with self.subTest(install=(first, second), remove=(remove_first, remove_second)), tempfile.TemporaryDirectory(prefix="party-sync-") as directory:
                    folder = Path(directory)
                    originals = lifecycle.fixture_texts()
                    lifecycle.write_fixture(folder, originals)
                    # Simulate the shipped shared hooks before party sync.
                    with patch.object(installer, "_patch_party_sync", side_effect=lambda text, path: text):
                        installer.install_handler(folder, first, runtime[first])
                    actions = folder / "ActionsWindow.py"
                    actions.write_text(actions.read_text() + "\nUSER_EXTENSION = True\n")
                    backup = actions.with_suffix(".py" + installer.CORE_BACKUP_SUFFIX)
                    before_backup = backup.read_bytes()
                    installer.install_handler(folder, second, runtime[second])
                    current = actions.read_bytes()
                    self.assertEqual(actions.read_text().count(installer.PARTY_SYNC_MARKER), 1)
                    self.assertIn("USER_EXTENSION = True", actions.read_text())
                    self.assertEqual(backup.read_bytes(), before_backup)
                    installer.install_handler(folder, first, runtime[first])
                    self.assertEqual(actions.read_bytes(), current)
                    installer.uninstall_handler(folder, remove_first)
                    self.assertEqual(actions.read_bytes(), current)
                    installer.uninstall_handler(folder, remove_second)
                    self.assertEqual(actions.read_text(), originals["ActionsWindow.py"])
                    self.assertFalse(backup.exists())

    def test_unknown_sync_block_is_rejected_before_any_file_changes(self):
        for change in (lambda text: text.replace(installer.PARTY_SYNC_MARKER, installer.PARTY_SYNC_MARKER.replace("v1", "v99")),
                       lambda text: text.replace("GemRBModCore.sync_party()", "custom_sync()")):
            with self.subTest(change=change), tempfile.TemporaryDirectory(prefix="party-sync-") as directory:
                folder = Path(directory)
                lifecycle.write_fixture(folder, lifecycle.fixture_texts())
                installer.install_handler(folder, "Psionics", ROOT / "psion/guiscripts/Psionics.py")
                actions = folder / "ActionsWindow.py"
                actions.write_text(change(actions.read_text()))
                snapshot = {path.relative_to(folder): path.read_bytes() for path in folder.rglob("*") if path.is_file()}
                with self.assertRaisesRegex(RuntimeError, "unrecognized modified party sync hook"):
                    installer.install_handler(folder, "Cipher", ROOT / "cipher/guiscripts/Cipher.py")
                self.assertEqual({path.relative_to(folder): path.read_bytes() for path in folder.rglob("*") if path.is_file()}, snapshot)


if __name__ == "__main__":
    unittest.main()
