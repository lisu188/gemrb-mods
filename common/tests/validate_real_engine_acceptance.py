#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "common" / "tools" / "gemrb_acceptance.py"
SMOKE = ROOT / "common" / "acceptance" / "scenarios" / "harness-smoke.json"


def load_harness():
    spec = importlib.util.spec_from_file_location("gemrb_acceptance", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(output):
    return json.loads((output / "manifest.json").read_text(encoding="utf-8"))


def run_case(harness, root, name, code, scenario=None, extra=None):
    output = root / name
    arguments = [
        "--scenario", str(scenario or SMOKE),
        "--output", str(output),
        "--game-type", "synthetic",
        "--fixture-id", "public-ci",
        "--gemrb-commit", "synthetic",
        "--component", "cipher",
        "--component", "psion",
        "--install-order", "cipher",
        "--install-order", "psion",
    ]
    if extra:
        arguments.extend(extra)
    arguments.extend(["--", sys.executable, "-c", code])
    return harness.main(arguments), output


def main():
    harness = load_harness()
    with tempfile.TemporaryDirectory() as folder_name:
        root = Path(folder_name)

        result, output = run_case(
            harness,
            root,
            "success",
            "print('GEMRB_ACCEPTANCE_READY')",
        )
        assert result == 0
        data = manifest(output)
        assert data["schema_version"] == 1
        assert data["status"] == "success"
        assert data["failures"] == []
        assert data["metadata"]["fixture_id"] == "public-ci"
        assert data["metadata"]["components"] == ["cipher", "psion"]
        assert data["metadata"]["install_order"] == ["cipher", "psion"]
        assert data["engine_returncode"] == 0
        assert data["engine_log"] == "gemrb.log"
        assert "GEMRB_ACCEPTANCE_READY" in (output / "gemrb.log").read_text(encoding="utf-8")

        result, output = run_case(
            harness,
            root,
            "forbidden",
            "print('GEMRB_ACCEPTANCE_READY'); print('GEMRB_ACCEPTANCE_FATAL')",
        )
        assert result == 1
        data = manifest(output)
        assert data["status"] == "failure"
        assert any(
            failure["kind"] == "forbidden_log_marker"
            and failure["detail"] == "GEMRB_ACCEPTANCE_FATAL"
            for failure in data["failures"]
        )

        missing_scenario = root / "missing.json"
        missing_scenario.write_text(json.dumps({
            "id": "missing-marker",
            "timeout_seconds": 2,
            "expected_exit_codes": [0],
            "expected_log_markers": ["NEVER_PRINTED"],
        }), encoding="utf-8")
        result, output = run_case(
            harness,
            root,
            "missing",
            "print('ordinary output')",
            scenario=missing_scenario,
        )
        assert result == 1
        assert any(
            failure["kind"] == "missing_log_marker"
            for failure in manifest(output)["failures"]
        )

        timeout_scenario = root / "timeout.json"
        timeout_scenario.write_text(json.dumps({
            "id": "timeout",
            "timeout_seconds": 0.1,
            "expected_exit_codes": [0],
        }), encoding="utf-8")
        result, output = run_case(
            harness,
            root,
            "timeout",
            "import time; time.sleep(60)",
            scenario=timeout_scenario,
        )
        assert result == 1
        data = manifest(output)
        assert data["timed_out"] is True
        assert any(failure["kind"] == "timeout" for failure in data["failures"])

        traceback_scenario = root / "traceback.json"
        traceback_scenario.write_text(json.dumps({
            "id": "traceback",
            "timeout_seconds": 2,
            "expected_exit_codes": [1],
        }), encoding="utf-8")
        result, output = run_case(
            harness,
            root,
            "traceback",
            "raise RuntimeError('boom')",
            scenario=traceback_scenario,
        )
        assert result == 1
        assert any(
            failure["kind"] == "forbidden_log_marker"
            and failure["detail"] == "Traceback (most recent call last):"
            for failure in manifest(output)["failures"]
        )

        malformed = root / "malformed.json"
        malformed.write_text('{"description": "no id"}', encoding="utf-8")
        try:
            harness.load_scenario(malformed)
        except ValueError as error:
            assert "id" in str(error)
        else:
            raise AssertionError("malformed scenario was accepted")

    print("Reusable real-engine acceptance harness validation passed")


if __name__ == "__main__":
    main()
