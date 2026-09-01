#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import tempfile
import types

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "gemrb_mods.py"


def load_driver():
    spec = importlib.util.spec_from_file_location("gemrb_mods_driver", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_package_root(root, mod="cipher", runtime_api=1, package_api=1):
    common = root / "common"
    package_dir = root / mod
    (common / "guiscripts").mkdir(parents=True)
    package_dir.mkdir(parents=True)
    (package_dir / "guiscripts").mkdir()
    (common / "runtime-version.json").write_text(json.dumps({
        "schema_version": 1,
        "runtime_api": runtime_api,
        "revision": "test",
    }), encoding="utf-8")
    handler = "Cipher" if mod == "cipher" else "Psionics"
    version = "0.2.0" if mod == "cipher" else "1.3.0"
    (package_dir / "package.json").write_text(json.dumps({
        "schema_version": 1,
        "name": mod,
        "version": version,
        "runtime_api": package_api,
        "handler": handler,
        "runtime_source": f"{mod}/guiscripts/{handler}.py",
        "weidu": {
            "tp2": f"{mod}/setup-{mod}.tp2",
            "component": 0,
            "language": 0,
        },
    }), encoding="utf-8")
    (package_dir / f"setup-{mod}.tp2").write_text(f"VERSION ~{version}~\n", encoding="utf-8")
    (package_dir / "guiscripts" / f"{handler}.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "chitin.key").write_bytes(b"fixture")
    (root / "gemrb_path.txt").write_text("GemRB_Data_Path = fixture\n", encoding="utf-8")
    return root


def add_weidu_log(game, mod="cipher"):
    tp2 = f"{mod.upper()}/SETUP-{mod.upper()}.TP2"
    (game / "WeiDU.log").write_text(f"~{tp2}~ #0 #0 // installed\n", encoding="utf-8")


def main():
    driver = load_driver()

    cipher = driver.load_package_context(ROOT, "cipher")
    psion = driver.load_package_context(ROOT, "psion")
    assert cipher["runtime"]["runtime_api"] == 1
    assert psion["runtime"]["runtime_api"] == 1
    assert cipher["package"]["version"] == "0.2.0"
    assert psion["package"]["version"] == "1.3.0"
    assert driver.weidu_command(cipher, Path("/game"), "weidu", True)[-2:] == ["--force-install-list", "0"]
    assert driver.weidu_command(cipher, Path("/game"), "weidu", False)[-2:] == ["--force-uninstall", "0"]

    with tempfile.TemporaryDirectory() as folder_name:
        root = Path(folder_name) / "game"
        root.mkdir()
        write_package_root(root, runtime_api=2, package_api=1)
        guiscripts = Path(folder_name) / "GUIScripts"
        guiscripts.mkdir()
        sentinel = guiscripts / "ActionsWindow.py"
        sentinel.write_text("original\n", encoding="utf-8")
        try:
            driver.preflight_install(root, guiscripts, "cipher", "definitely-missing-weidu")
        except RuntimeError as error:
            assert "runtime API mismatch" in str(error)
        else:
            raise AssertionError("runtime API mismatch was accepted")
        assert sentinel.read_text(encoding="utf-8") == "original\n"
        assert list(guiscripts.iterdir()) == [sentinel]

    with tempfile.TemporaryDirectory() as folder_name:
        game = Path(folder_name) / "game"
        game.mkdir()
        write_package_root(game)
        guiscripts = Path(folder_name) / "GUIScripts"
        guiscripts.mkdir()
        context = driver.load_package_context(game, "cipher")

        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "not installed", state

        add_weidu_log(game)
        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "weidu only", state

        (game / "WeiDU.log").unlink()
        (guiscripts / ".gemrbmodcore.cipher.active").write_text("active\n", encoding="utf-8")
        (guiscripts / "Cipher.py").write_text("runtime\n", encoding="utf-8")
        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "runtime only/inconsistent", state

        add_weidu_log(game)
        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "installed", state

        (guiscripts / ".gemrbmodcore.psionics.active").write_text("active\n", encoding="utf-8")
        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "installed with other handlers", state
        assert state["other_handlers"] == ["psionics"], state

        (guiscripts / "Cipher.py").unlink()
        state = driver.status_for_context(game, guiscripts, context)
        assert state["state"] == "runtime only/inconsistent", state
        assert state["weidu_installed"] is True

    with tempfile.TemporaryDirectory() as folder_name:
        game = Path(folder_name) / "game"
        game.mkdir()
        write_package_root(game)
        guiscripts = Path(folder_name) / "GUIScripts"
        guiscripts.mkdir()
        sentinel = guiscripts / "sentinel.txt"
        sentinel.write_text("original\n", encoding="utf-8")
        context = driver.load_package_context(game, "cipher")
        original_load = driver.load_gui_module
        calls = []
        fake = types.SimpleNamespace(
            COMMON_MODULES=(),
            install_handler=lambda copied, handler, source: (
                calls.append((copied, handler, source)),
                (copied / "sentinel.txt").write_text("changed-copy\n", encoding="utf-8"),
            ),
        )
        driver.load_gui_module = lambda value: fake
        try:
            driver.validate_gui_install(context, guiscripts)
        finally:
            driver.load_gui_module = original_load
        assert len(calls) == 1
        assert calls[0][0] != guiscripts
        assert calls[0][1] == "Cipher"
        assert sentinel.read_text(encoding="utf-8") == "original\n"

    with tempfile.TemporaryDirectory() as folder_name:
        game = Path(folder_name) / "game"
        game.mkdir()
        write_package_root(game)
        guiscripts = Path(folder_name) / "GUIScripts"
        guiscripts.mkdir()
        context = driver.load_package_context(game, "cipher")
        original_preflight_install = driver.preflight_install
        original_preflight_uninstall = driver.preflight_uninstall
        original_run_weidu = driver.run_weidu
        original_load = driver.load_gui_module
        original_status = driver.status_for_context
        calls = []
        fake = types.SimpleNamespace(
            install_handler=lambda *args: calls.append("gui-install"),
            uninstall_handler=lambda *args: calls.append("gui-uninstall"),
        )
        try:
            driver.preflight_install = lambda *args: (context, game, guiscripts, "weidu")
            driver.preflight_uninstall = lambda *args: (context, game, guiscripts, "weidu")
            driver.load_gui_module = lambda value: fake
            driver.run_weidu = lambda context, game, weidu, install: calls.append(
                "weidu-install" if install else "weidu-uninstall"
            )
            driver.status_for_context = lambda *args: {
                "state": "installed",
                "mod": "cipher",
            }
            result = driver.install_package(game, guiscripts, "cipher")
            assert result["state"] == "installed"
            assert calls == ["weidu-install", "gui-install"], calls

            calls.clear()
            driver.status_for_context = lambda *args: {
                "state": "not installed",
                "mod": "cipher",
            }
            result = driver.uninstall_package(game, guiscripts, "cipher")
            assert result["state"] == "not installed"
            assert calls == ["gui-uninstall", "weidu-uninstall"], calls

            calls.clear()
            driver.status_for_context = lambda *args: {
                "state": "weidu only",
                "mod": "cipher",
            }
            fake.install_handler = lambda *args: (_ for _ in ()).throw(RuntimeError("gui boom"))
            try:
                driver.install_package(game, guiscripts, "cipher")
            except RuntimeError as error:
                assert "WeiDU succeeded" in str(error)
                assert "weidu only" in str(error)
            else:
                raise AssertionError("GUI phase failure was hidden")
            assert calls == ["weidu-install"], calls
        finally:
            driver.preflight_install = original_preflight_install
            driver.preflight_uninstall = original_preflight_uninstall
            driver.run_weidu = original_run_weidu
            driver.load_gui_module = original_load
            driver.status_for_context = original_status

    print("Unified package driver validation passed")


if __name__ == "__main__":
    main()
