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
    original_parse = runner.parse_soundset_diagnostics
    diagnostic = {
        "raw": "GEMRB_MODS_SOUNDSET|family=bg1|count=3|slot=1|class=CIPHER|gender=1|sample=['a', 'b', 'c']",
        "family": "bg1",
        "count": 3,
        "slot": "1",
        "class": "CIPHER",
        "gender": "1",
        "sample": "['a', 'b', 'c']",
    }
    try:
        builtins.input = lambda prompt="": ""

        def fake_capture(output):
            output.write_bytes(b"fake-png")
            return "test-capture"

        runner.capture = fake_capture
        runner.parse_soundset_diagnostics = lambda path: [dict(diagnostic)]
        with tempfile.TemporaryDirectory() as folder_name:
            output = Path(folder_name) / "acceptance"
            result = runner.main([
                "--output", str(output),
                "--screen", "soundset",
                "--gemrb-commit", "fixture-commit",
                "--game-type", "bgee",
                "--fixture-id", "test-fixture",
                "--component", "cipher",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(60)",
            ])
            assert result == 0
            screenshot = output / "screenshots" / "01-soundset.png"
            log_path = output / "gemrb.log"
            manifest_path = output / "manifest.json"
            assert screenshot.read_bytes() == b"fake-png"
            assert log_path.is_file()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["schema_version"] == 1
            assert manifest["scenario"]["id"] == "chargen-manual-capture"
            assert manifest["metadata"]["gemrb_commit"] == "fixture-commit"
            assert manifest["metadata"]["game_type"] == "bgee"
            assert manifest["metadata"]["fixture_id"] == "test-fixture"
            assert manifest["metadata"]["components"] == ["cipher"]
            assert manifest["screenshot_backend"] == "test-capture"
            assert manifest["engine_log"] == "gemrb.log"
            assert manifest["captures"][0]["screen"] == "soundset"
            assert manifest["captures"][0]["screenshot"] == "screenshots/01-soundset.png"
            assert manifest["engine_returncode"] is not None
            assert manifest["soundset_diagnostics"] == [diagnostic]

            parser_log = output / "soundset-parser.log"
            parser_log.write_text(
                "prefix GEMRB_MODS_SOUNDSET|family=bg2|count=2|slot=4|class=FIGHTER|gender=2|sample=['v1', 'v2']\n",
                encoding="utf-8",
            )
            parsed = original_parse(parser_log)
            assert len(parsed) == 1
            assert parsed[0]["family"] == "bg2"
            assert parsed[0]["count"] == 2
            assert parsed[0]["slot"] == "4"
            assert parsed[0]["class"] == "FIGHTER"
            assert parsed[0]["gender"] == "2"
            assert parsed[0]["sample"] == "['v1', 'v2']"
    finally:
        builtins.input = original_input
        runner.capture = original_capture
        runner.parse_soundset_diagnostics = original_parse
    print("Chargen live acceptance recorder validation passed")


if __name__ == "__main__":
    main()
