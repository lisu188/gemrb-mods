#!/usr/bin/env python3
from pathlib import Path
import contextlib
import importlib.util
import io
import itertools
import json
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MODS = ("cipher", "psion", "sorcerer-monk")
HANDLERS = {"cipher": "Cipher", "psion": "Psionics", "sorcerer-monk": "SorcererMonkUI"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts}


class ArchiveOrderTests(unittest.TestCase):
    def setUp(self):
        self.builder = load("three_class_builder_unit", ROOT / "common/tools/build_release.py")

    def test_manifest_is_sorted_between_psion_and_sorcerer_monk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contexts = {mod: {
                "runtime": {"runtime_api": 1, "revision": "test"},
                "package": {"name": mod, "version": "test", "runtime_api": 1,
                            "handler": HANDLERS[mod], "weidu": {"component": 0}},
            } for mod in MODS}
            files = {}
            for mod in MODS:
                path = root / mod / "README.md"
                path.parent.mkdir()
                path.write_text(mod + "\n", encoding="utf-8")
                files[f"{mod}/README.md"] = path
            first, manifest = self.builder.write_release(root / "first", MODS, contexts, files)
            second, repeated = self.builder.write_release(root / "second", MODS, contexts, files)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(manifest, repeated)
            self.assertTrue(self.builder.verify_archive(first, MODS, contexts, files))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), [
                    "cipher/README.md", "psion/README.md", "release-manifest.json",
                    "sorcerer-monk/README.md",
                ])

    def test_both_command_line_interfaces_accept_sorcerer_monk(self):
        driver = load("three_class_driver_unit", ROOT / "gemrb_mods.py")
        self.assertEqual(tuple(driver.SUPPORTED_MODS), MODS)
        self.assertEqual(tuple(self.builder.SUPPORTED_MODS), MODS)
        for command in ("preflight", "install", "uninstall"):
            args = driver.build_parser().parse_args([
                command, "sorcerer-monk", "--game", ".", "--guiscripts", ".",
            ])
            self.assertEqual(args.mod, "sorcerer-monk")
        self.assertEqual(self.builder.parse_args(["sorcerer-monk"]).mod, ["sorcerer-monk"])

    def test_manifest_registers_the_existing_shared_handler(self):
        driver = load("three_class_manifest_unit", ROOT / "gemrb_mods.py")
        path = ROOT / "sorcerer-monk/package.json"
        package = driver.validate_package_manifest(driver.read_json(path), path, "sorcerer-monk")
        self.assertEqual(package["handler"], "SorcererMonkUI")
        self.assertEqual(package["runtime_source"], "sorcerer-monk/guiscripts/SorcererMonkUI.py")
        self.assertEqual(package["weidu"], {
            "tp2": "sorcerer-monk/setup-sorcerer-monk.tp2", "component": 0, "language": 0,
        })
        self.assertEqual(package["version"], "2.0")


class ThreeClassIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.builder = load("three_class_builder", ROOT / "common/tools/build_release.py")
        self.runner = load("three_class_runner", ROOT / "common/tests/validate_release_builder.py")
        self.shared = load("three_class_shared_fixture", ROOT / "common/tests/validate.py")

    def run_driver(self, game, guiscripts, weidu, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            try:
                return self.runner.run_driver(game, guiscripts, weidu, *args)
            except Exception as error:
                self.fail(output.getvalue() + "\n" + str(error))

    def test_all_seven_archive_combinations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for size in range(1, len(MODS) + 1):
                for mods in itertools.combinations(MODS, size):
                    with self.subTest(mods=mods):
                        first, manifest = self.builder.build_release(mods, root / "first")
                        second, repeated = self.builder.build_release(mods, root / "second")
                        self.assertEqual(first.read_bytes(), second.read_bytes())
                        self.assertEqual(manifest, repeated)
                        self.assertEqual([row["name"] for row in manifest["packages"]], list(mods))
                        with zipfile.ZipFile(first) as archive:
                            names = archive.namelist()
                            self.assertEqual(names, sorted(names))
                            for mod in MODS:
                                self.assertEqual(f"{mod}/package.json" in names, mod in mods)
                            for required in ("docs/compatibility.md", "docs/cast-runtime.md",
                                             "docs/install-three-classes.md"):
                                self.assertIn(required, names)
                            game = root / ("extracted-" + "-".join(mods))
                            archive.extractall(game)
                        driver = load("extracted_three_class_driver", game / "gemrb_mods.py")
                        for mod in mods:
                            context = driver.load_package_context(game, mod)
                            self.assertEqual(context["package"]["handler"], HANDLERS[mod])
                            self.assertTrue(context["tp2"].is_file())
                            self.assertTrue(context["runtime_source"].is_file())

    def test_all_36_install_and_uninstall_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, _ = self.builder.build_release(MODS, root / "release")
            weidu = root / "weidu"
            self.runner.write_fake_weidu(weidu)
            orders = list(itertools.permutations(MODS))
            for index, (install_order, uninstall_order) in enumerate(itertools.product(orders, repeat=2)):
                with self.subTest(install=install_order, uninstall=uninstall_order):
                    game = root / str(index) / "game"
                    game.mkdir(parents=True)
                    with zipfile.ZipFile(archive) as bundle:
                        bundle.extractall(game)
                    (game / "chitin.key").write_bytes(b"synthetic-game")
                    (game / "gemrb_path.txt").write_text("GemRB_Data_Path = synthetic\n", encoding="utf-8")
                    gui = game.parent / "GUIScripts"
                    originals = dict(self.shared.fixture_texts())
                    originals["foreign_mod.py"] = "FOREIGN_MOD = True\n"
                    for handler in HANDLERS.values():
                        originals[f"{handler}.py"] = "ORIGINAL_HANDLER = True\n"
                    self.shared.write_fixture(gui, originals)
                    pristine = snapshot(gui)
                    active = set()
                    for mod in install_order:
                        self.run_driver(game, gui, weidu, "preflight", mod)
                        self.run_driver(game, gui, weidu, "install", mod)
                        active.add(mod)
                        self.assert_active(game, gui, weidu, active)
                    installed = snapshot(gui)
                    for mod in install_order:
                        self.run_driver(game, gui, weidu, "install", mod)
                    self.assertEqual(snapshot(gui), installed, "reinstallation changed GUI ownership")
                    for mod in uninstall_order:
                        self.run_driver(game, gui, weidu, "uninstall", mod)
                        active.remove(mod)
                        self.assert_active(game, gui, weidu, active)
                        if active:
                            self.assertTrue((gui / "GemRBModCore.py").is_file())
                    self.assertEqual(snapshot(gui), pristine, "last uninstall did not restore original GUI bytes")
                    self.assertFalse((game / "WeiDU.log").exists())
            print("All 36 three-class GUI install/uninstall orderings passed (synthetic WeiDU boundary).")

    def assert_active(self, game, gui, weidu, active):
        rows = json.loads(self.run_driver(game, gui, weidu, "status", "--json"))
        self.assertEqual({row["mod"] for row in rows}, set(MODS))
        expected_handlers = sorted(HANDLERS[mod].casefold() for mod in active)
        for row in rows:
            expected = "not installed"
            if row["mod"] in active:
                expected = "installed with other handlers" if len(active) > 1 else "installed"
            self.assertEqual(row["state"], expected, row)
            self.assertEqual(row["active_handlers"], expected_handlers)


if __name__ == "__main__":
    unittest.main()
