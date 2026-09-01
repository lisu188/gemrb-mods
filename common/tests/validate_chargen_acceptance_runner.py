#!/usr/bin/env python3
from pathlib import Path
import builtins
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "common" / "tools" / "run_chargen_text_acceptance.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("chargen_acceptance_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load_runner()
    original_input = builtins.input
    original_capture = runner.capture
    try:
        builtins.input = lambda prompt="": ""

        def fake_capture(output):
            output.write_bytes(b"fake-png")
            return "test-capture"

        runner.capture = fake_capture
        with tempfile.TemporaryDirectory() as folder_name:
            output = Path(folder_name) / "acceptance"
            result = runner.main([
                "--output", str(output),
                "--screen", "class-selection",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(60)",
            ])
            assert result == 0
            screenshot = output / "screenshots" / "01-class-selection.png"
            log_path = output / "gemrb.log"
            manifest_path = output / "manifest.json"
            assert screenshot.read_bytes() == b"fake-png"
            assert log_path.is_file()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["screenshot_backend"] == "test-capture"
            assert manifest["engine_log"] == "gemrb.log"
            assert manifest["captures"][0]["screen"] == "class-selection"
            assert manifest["captures"][0]["screenshot"] == "screenshots/01-class-selection.png"
            assert manifest["engine_returncode"] is not None
    finally:
        builtins.input = original_input
        runner.capture = original_capture
    print("Chargen live acceptance recorder validation passed")


if __name__ == "__main__":
    main()
