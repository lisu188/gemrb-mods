#!/usr/bin/env python3
"""Interrupted native rests must not restore shared class resources."""
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


installer = load("rest_installer", "common/tools/install_guiscripts.py")
lifecycle = load("rest_lifecycle_fixture", "common/tests/validate.py")


class RestCompletionTests(unittest.TestCase):
    def setUp(self):
        self.clock = 100
        self.elapsed = 0
        self.calls = []
        self.restores = []
        self.result = {"Error": False, "ErrorMsg": -1, "Cutscene": False, "Extra": object()}
        self.gemrb = types.ModuleType("GemRB")
        self.gemrb.GetGameTime = lambda: self.clock
        self.gemrb.RestParty = self.native_rest
        self.core = load("rest_core", "common/guiscripts/GemRBModCore.py")
        self.core._handlers = lambda: [
            types.SimpleNamespace(restore_party=lambda: self.restores.append("Psionics")),
            types.SimpleNamespace(restore_party=lambda: self.restores.append("Cipher")),
        ]
        modules = patch.dict(sys.modules, {"GemRB": self.gemrb, "GemRBModCore": self.core})
        modules.start()
        self.addCleanup(modules.stop)

    def native_rest(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        self.clock += self.elapsed
        return self.result

    def test_zero_five_seconds_and_one_through_seven_hours_do_not_restore(self):
        for elapsed in (0, 5, *(hour * 300 for hour in range(1, 8)), 2399):
            with self.subTest(elapsed=elapsed):
                self.elapsed = elapsed
                self.assertIs(self.core.rest_party(15, 0, 1), self.result)
                self.assertEqual(self.restores, [])

    def test_partial_attempts_never_accumulate_into_a_complete_rest(self):
        self.elapsed = 1800
        for _ in range(8):
            self.core.rest_party(15, 2, 1)
        self.assertEqual(self.clock, 100 + 8 * 1800)
        self.assertEqual(self.restores, [])

    def test_full_rest_with_or_without_dream_preserves_args_and_result(self):
        for cutscene in (False, True):
            with self.subTest(cutscene=cutscene):
                self.elapsed = 2400
                self.result["Cutscene"] = cutscene
                self.restores.clear()
                self.assertIs(self.core.rest_party(15, 2, hp=1), self.result)
                self.assertEqual(self.calls[-1], ((15, 2), {"hp": 1}))
                self.assertEqual(self.restores, ["Psionics", "Cipher"])

    def test_inn_and_repeat_until_healed_dispatch_once_per_native_call(self):
        for args, elapsed in (((18, 1, 4), 2400), ((15, 0, 1), 7200), ((0, -1, 0), 2400)):
            with self.subTest(args=args, elapsed=elapsed):
                self.restores.clear()
                self.elapsed = elapsed
                before = len(self.calls)
                self.assertIs(self.core.rest_party(*args), self.result)
                self.assertEqual(len(self.calls), before + 1)
                self.assertEqual(self.calls[-1], (args, {}))
                self.assertEqual(self.restores, ["Psionics", "Cipher"])

    def test_refusal_cannot_restore_even_with_large_elapsed_time(self):
        self.result.update(Error=True, ErrorMsg=16500)
        self.elapsed = 7200
        self.assertIs(self.core.rest_party(15, 0, 1), self.result)
        self.assertEqual(self.restores, [])

    def test_cutscene_true_alone_does_not_prove_completed_rest(self):
        self.result["Cutscene"] = True
        self.elapsed = 5
        self.core.rest_party(15, 0, 1)
        self.assertEqual(self.restores, [])

    def test_native_exception_propagates_without_resource_restoration(self):
        error = RuntimeError("native rest failed")
        with patch.object(self.gemrb, "RestParty", side_effect=error) as native:
            with self.assertRaises(RuntimeError) as raised:
                self.core.rest_party(15, 0, 1)
            self.assertIs(raised.exception, error)
            native.assert_called_once_with(15, 0, 1)
        self.assertEqual(self.restores, [])

    def test_missing_false_error_or_invalid_clock_does_not_restore(self):
        self.elapsed = 2400
        for result in (None, {}, {"Error": 0}, {"Error": None}, {"Error": "false"}):
            with self.subTest(result=result):
                self.result = result
                self.assertIs(self.core.rest_party(15, 0, 1), result)
                self.assertEqual(self.restores, [])
        self.result = {"Error": False}
        for before, after in ((True, 2401), (0, 2400.0), (None, 2400), (5000, 0)):
            with self.subTest(clock=(before, after)), patch.object(self.gemrb, "GetGameTime", side_effect=[before, after]):
                self.core.rest_party(15, 0, 1)
                self.assertEqual(self.restores, [])

    def test_failed_clock_observation_cannot_restore(self):
        for values in ([RuntimeError("clock failed")], [100, RuntimeError("clock failed")]):
            with self.subTest(values=values), patch.object(self.gemrb, "GetGameTime", side_effect=values):
                with self.assertRaisesRegex(RuntimeError, "clock failed"):
                    self.core.rest_party(15, 0, 1)
                self.assertEqual(self.restores, [])

    def test_pending_transactions_cancel_only_when_rest_is_completed(self):
        self.core._pending_casts[1] = {"cast": "PS1MTHR"}
        self.elapsed = 5
        self.core.rest_party(15, 0, 1)
        self.assertEqual(self.core._pending_casts, {1: {"cast": "PS1MTHR"}})
        self.elapsed = 2400
        self.core.rest_party(15, 0, 1)
        self.assertEqual(self.core._pending_casts, {})

    def test_rendered_assigned_and_unassigned_hooks_keep_native_call_semantics(self):
        for assigned in (True, False):
            text = ("import GemRB\n\ndef Rest():\n\t"
                    + ("info = " if assigned else "") + "GemRB.RestParty (18, 1, 4)\n"
                    + ("\treturn info\n" if assigned else ""))
            rendered = installer.render_patch(text, "rest", Path("GUISTORE.py"))
            namespace = {}
            exec(compile(rendered, "rendered_rest", "exec"), namespace)
            self.elapsed = 5
            self.assertIs(namespace["Rest"](), self.result if assigned else None)
            self.assertEqual(self.restores, [])
            self.assertEqual(self.calls[-1], ((18, 1, 4), {}))
            self.elapsed = 2400
            namespace["Rest"]()
            self.assertEqual(self.restores, ["Psionics", "Cipher"])
            self.restores.clear()


class RealHandlerDispatchTests(unittest.TestCase):
    def test_actual_psion_and_cipher_resources_wait_for_complete_rest(self):
        fixture = load("rest_actor_fixture", "common/tests/validate_actor_state_failures.py")
        fx = fixture.ActorStateFailures()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        psion, cipher = fx.psion, fx.cipher
        fx.gemrb.GetPartySize = lambda: 3
        fx.gemrb.ManageCompanion = lambda *args: None
        fx.seed(psion.POOL_EFFECT_MARKER, psion.POOL_EFFECT_RESOURCE, 0)
        fx.seed(psion.FOCUS_EFFECT_MARKER, psion.FOCUS_EFFECT_RESOURCE, 0)
        fx.seed(psion.PSICRYSTAL_USED_MARKER, psion.PSICRYSTAL_USED_RESOURCE, 5)
        fx.seed(psion.PSICRYSTAL_PERSONALITY_MARKER, psion.PSICRYSTAL_PERSONALITY_RESOURCE, 1)
        clock = [4680]
        fx.gemrb.GetGameTime = lambda: clock[0]
        def rest(*args):
            clock[0] += elapsed
            return {"Error": False, "Cutscene": False}
        fx.gemrb.RestParty = rest
        original = copy.deepcopy(fx.effects)
        elapsed = 5
        fx.core.rest_party(15, 2, 1)
        self.assertEqual(fx.effects, original)
        self.assertEqual(fx.writes, [])
        self.assertEqual(psion._read_persistent_pool_state(1), (True, 0))
        self.assertEqual(psion._read_focus_state(1), (True, False))
        self.assertEqual(psion._psicrystal_used_state(1), 5)
        elapsed = 2400
        fx.core.rest_party(18, 1, 4)
        self.assertEqual(psion._read_persistent_pool_state(1), (True, psion.maximum_pool(1)))
        self.assertEqual(psion._read_focus_state(1), (True, True))
        self.assertEqual(psion._psicrystal_used_state(1), 6)
        self.assertIn(("spell", (2, "CIFS4", 2)), fx.writes)


def legacy_patch(text, path):
    """The exact previously shipped assigned/unassigned restoration blocks."""
    match = installer._rest_call(text, path)
    indent, result = match.group(1), match.group(2)
    block = match.group(0) + indent + installer.MARK_BEGIN + "\n"
    if result:
        block += indent + f'if not {result}["Error"]:\n' + indent + "\tGemRBModCore.restore_party()\n"
    else:
        block += indent + "GemRBModCore.restore_party()\n"
    block += indent + installer.MARK_END + "\n"
    return text[:match.start()] + block + text[match.end():]


class RestInstallerTests(unittest.TestCase):
    def test_upgrade_both_handler_orders_preserves_backup_and_unrelated_edits(self):
        for first, second in (("Psionics", "Cipher"), ("Cipher", "Psionics")):
            with self.subTest(order=(first, second)), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                originals = lifecycle.fixture_texts()
                lifecycle.write_fixture(folder, originals)
                runtime = {"Psionics": ROOT/"psion/guiscripts/Psionics.py", "Cipher": ROOT/"cipher/guiscripts/Cipher.py"}
                with patch.object(installer, "_patch_rest", side_effect=legacy_patch):
                    installer.install_handler(folder, first, runtime[first])
                for name in ("MenuWindow.py", "GUISTORE.py"):
                    path = folder/name
                    path.write_text(path.read_text() + "\nUSER_SETTING = 'preserved'\n")
                installer.install_handler(folder, second, runtime[second])
                current = {}
                for name in ("MenuWindow.py", "GUISTORE.py"):
                    path = folder/name
                    current[name] = path.read_bytes()
                    self.assertEqual(path.with_suffix(path.suffix+installer.CORE_BACKUP_SUFFIX).read_text(), originals[name])
                    self.assertIn("USER_SETTING = 'preserved'", path.read_text())
                    self.assertEqual(path.read_text().count(installer.REST_CHECK_MARKER), 1)
                    self.assertNotIn("GemRBModCore.restore_party()", path.read_text())
                installer.install_handler(folder, first, runtime[first])
                for name, content in current.items(): self.assertEqual((folder/name).read_bytes(), content)
                installer.uninstall_handler(folder, first)
                for name, content in current.items(): self.assertEqual((folder/name).read_bytes(), content)
                self.assertTrue((folder/(second+".py")).exists())
                installer.uninstall_handler(folder, second)
                for name, content in originals.items(): self.assertEqual((folder/name).read_text(), content)
                for name in installer.COMMON_MODULES: self.assertFalse((folder/name).exists())

    def test_unknown_modified_legacy_or_current_blocks_fail_closed(self):
        original = lifecycle.fixture_texts()["MenuWindow.py"]
        old = legacy_patch(installer._insert_import(original, Path("MenuWindow.py")), Path("MenuWindow.py"))
        new = installer.render_patch(original, "rest", Path("MenuWindow.py"))
        variants = [old.replace('if not info["Error"]:', 'if True:'),
                    old.replace('GemRBModCore.restore_party()', 'GemRBModCore.restore_party(); custom()'),
                    new.replace(installer.REST_CHECK_MARKER, installer.REST_CHECK_MARKER.replace("v1", "v9")),
                    new.replace(installer.MARK_END, "custom()\n\t" + installer.MARK_END)]
        for text in variants:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/"MenuWindow.py"; path.write_text(text)
                backup = path.with_suffix(path.suffix+installer.CORE_BACKUP_SUFFIX); backup.write_text(original)
                with self.assertRaisesRegex(RuntimeError, "unrecognized|not recognized"):
                    installer.render_patch(path.read_text(), "rest", path)
                self.assertEqual(path.read_text(), text)
                self.assertEqual(backup.read_text(), original)

    def test_ambiguous_rest_calls_fail_closed(self):
        text = lifecycle.fixture_texts()["MenuWindow.py"].replace("\treturn info", "\tGemRB.RestParty(15,0,0)\n\treturn info")
        with self.assertRaisesRegex(RuntimeError, "unique rest call"):
            installer.render_patch(text, "rest", Path("MenuWindow.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
