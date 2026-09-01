#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "common" / "tools" / "run_shared_runtime_lifecycle.py"
MATRIX = ROOT / "common" / "acceptance" / "matrices" / "cipher-psion-lifecycle.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("run_shared_runtime_lifecycle", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    tool = load_tool()
    matrix = tool.load_matrix(MATRIX)
    assert matrix["id"] == "cipher-psion-shared-runtime"
    assert len(matrix["cases"]) == 4
    assert {tuple(case["install_order"]) for case in matrix["cases"]} == {
        ("cipher", "psion"),
        ("psion", "cipher"),
    }
    assert {tuple(case["uninstall_order"]) for case in matrix["cases"]} == {
        ("cipher", "psion"),
        ("psion", "cipher"),
    }

    assert tool.weidu_command("weidu", "cipher", True)[-3:] == [
        "--force-install", "0", "--no-exit-pause",
    ]
    assert "--force-uninstall" in tool.weidu_command("weidu", "psion", False)

    with tempfile.TemporaryDirectory() as folder_name:
        root = Path(folder_name)
        game = root / "game"
        guiscripts = root / "guiscripts"
        output = root / "output"
        game.mkdir()
        guiscripts.mkdir()
        actions = guiscripts / "ActionsWindow.py"
        actions.write_text("original-actions\n", encoding="utf-8")
        baseline_bytes = actions.read_bytes()
        original_run_command = tool.run_command

        def fake_run_command(command, cwd, log_path, timeout=600):
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("ok\n", encoding="utf-8")
            command_text = " ".join(command)
            if "install_guiscripts.py" in command_text:
                mod = "cipher" if "/cipher/" in command_text.replace("\\", "/") else "psion"
                handler = tool.MODS[mod]["handler"]
                marker = guiscripts / f".gemrbmodcore.{handler}.active"
                uninstall = "--uninstall" in command
                if uninstall:
                    marker.unlink(missing_ok=True)
                    if not tool.active_handlers(guiscripts):
                        actions.write_bytes(baseline_bytes)
                else:
                    marker.write_text("active\n", encoding="utf-8")
                    actions.write_text("patched-actions\n", encoding="utf-8")
            return {
                "command": list(command),
                "cwd": str(cwd),
                "log": str(log_path),
                "returncode": 0,
            }

        tool.run_command = fake_run_command
        try:
            for case in matrix["cases"]:
                result = tool.execute_case(
                    case,
                    game,
                    guiscripts,
                    output,
                    "weidu",
                    "python",
                )
                assert result["restored"] is True
                assert result["install_order"] == case["install_order"]
                assert result["uninstall_order"] == case["uninstall_order"]
                assert tool.active_handlers(guiscripts) == []
                assert actions.read_bytes() == baseline_bytes
                gui_steps = [
                    step for step in result["steps"]
                    if step["phase"].startswith("gui-")
                ]
                assert len(gui_steps) == 4
                assert gui_steps[0]["active_handlers"] == [tool.MODS[case["install_order"][0]]["handler"]]
                assert sorted(gui_steps[1]["active_handlers"]) == ["cipher", "psionics"]
                assert len(gui_steps[2]["active_handlers"]) == 1
                assert gui_steps[3]["active_handlers"] == []
        finally:
            tool.run_command = original_run_command

    print("Shared runtime lifecycle orchestration validation passed")


if __name__ == "__main__":
    main()
