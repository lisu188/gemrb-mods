#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "common" / "tools" / "prepare_acceptance_fixture.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("prepare_acceptance_fixture", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    tool = load_tool()
    with tempfile.TemporaryDirectory() as folder_name:
        root = Path(folder_name)
        source_game = root / "source-game"
        source_gui = root / "source-guiscripts"
        repo = root / "repo"
        output = root / "prepared"
        source_game.mkdir()
        source_gui.mkdir()
        (source_game / "chitin.key").write_bytes(b"game-key")
        (source_game / "dialog.tlk").write_bytes(b"tlk")
        (source_gui / "ActionsWindow.py").write_text("original\n", encoding="utf-8")
        for package in ("common", "cipher", "psion"):
            path = repo / package
            path.mkdir(parents=True)
            (path / "package.txt").write_text(package, encoding="utf-8")

        manifest_path, manifest = tool.prepare(
            source_game,
            source_gui,
            output,
            repo,
            ["cipher", "psion"],
            "fixture-test",
            "bgee",
        )
        assert manifest_path == output / "fixture.json"
        assert manifest["schema_version"] == 1
        assert manifest["fixture_id"] == "fixture-test"
        assert manifest["game_type"] == "bgee"
        assert manifest["packages"] == ["common", "cipher", "psion"]
        assert (output / "game" / "chitin.key").read_bytes() == b"game-key"
        assert (output / "game" / "common" / "package.txt").read_text(encoding="utf-8") == "common"
        assert (output / "game" / "cipher" / "package.txt").read_text(encoding="utf-8") == "cipher"
        assert (output / "game" / "psion" / "package.txt").read_text(encoding="utf-8") == "psion"
        assert (output / "guiscripts" / "ActionsWindow.py").read_text(encoding="utf-8") == "original\n"
        loaded, game, guiscripts = tool.load_fixture(manifest_path)
        assert loaded["fixture_id"] == "fixture-test"
        assert game == (output / "game").resolve()
        assert guiscripts == (output / "guiscripts").resolve()

        try:
            tool.prepare(
                source_game,
                source_gui,
                output,
                repo,
                ["cipher"],
                "duplicate",
                "bgee",
            )
        except ValueError as error:
            assert "already exists" in str(error)
        else:
            raise AssertionError("existing output was accepted")

        dirty_game = root / "dirty-game"
        dirty_game.mkdir()
        (dirty_game / "common").mkdir()
        dirty_output = root / "dirty-output"
        try:
            tool.prepare(
                dirty_game,
                source_gui,
                dirty_output,
                repo,
                ["cipher"],
                "dirty",
                "bgee",
            )
        except ValueError as error:
            assert "not clean" in str(error)
        else:
            raise AssertionError("dirty source fixture was accepted")
        assert not dirty_output.exists()

    print("Acceptance fixture preparation validation passed")


if __name__ == "__main__":
    main()
