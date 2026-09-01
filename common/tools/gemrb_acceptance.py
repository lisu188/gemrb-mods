#!/usr/bin/env python3
from pathlib import Path
import argparse
import datetime as dt
import json
import subprocess
import sys
import time

MANIFEST_SCHEMA_VERSION = 1
DEFAULT_FORBIDDEN_LOG_MARKERS = (
    "Traceback (most recent call last):",
)


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def terminate_process(process, grace_seconds=5):
    if process.poll() is not None:
        return process.returncode
    process.terminate()
    try:
        return process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=grace_seconds)


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _string_list(value, field):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"scenario field {field} must be a list of non-empty strings")
    return list(value)


def _int_list(value, field):
    if value is None:
        return [0]
    if not isinstance(value, list) or not value or not all(isinstance(item, int) for item in value):
        raise ValueError(f"scenario field {field} must be a non-empty list of integers")
    return list(value)


def load_scenario(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scenario root must be an object")
    scenario_id = data.get("id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("scenario field id must be a non-empty string")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise ValueError("scenario field description must be a string")
    timeout = data.get("timeout_seconds", 120)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("scenario field timeout_seconds must be a positive number")
    supported = _string_list(data.get("supported_game_types"), "supported_game_types")
    return {
        "id": scenario_id.strip(),
        "description": description,
        "timeout_seconds": float(timeout),
        "expected_exit_codes": _int_list(data.get("expected_exit_codes"), "expected_exit_codes"),
        "expected_log_markers": _string_list(data.get("expected_log_markers"), "expected_log_markers"),
        "forbidden_log_markers": _string_list(data.get("forbidden_log_markers"), "forbidden_log_markers"),
        "supported_game_types": supported,
        "source": str(path),
    }


def classify_result(scenario, returncode, timed_out, launch_error, log_text):
    failures = []
    if launch_error:
        failures.append({"kind": "launch_failure", "detail": launch_error})
    if timed_out:
        failures.append({"kind": "timeout", "detail": f"exceeded {scenario['timeout_seconds']:g}s"})
    if returncode is not None and returncode not in scenario["expected_exit_codes"]:
        failures.append({
            "kind": "exit_code",
            "detail": f"expected {scenario['expected_exit_codes']}, got {returncode}",
        })
    for marker in scenario["expected_log_markers"]:
        if marker not in log_text:
            failures.append({"kind": "missing_log_marker", "detail": marker})
    forbidden = list(DEFAULT_FORBIDDEN_LOG_MARKERS)
    for marker in scenario["forbidden_log_markers"]:
        if marker not in forbidden:
            forbidden.append(marker)
    for marker in forbidden:
        if marker in log_text:
            failures.append({"kind": "forbidden_log_marker", "detail": marker})
    return failures


def run_process(command, log_path, timeout_seconds):
    timed_out = False
    launch_error = None
    returncode = None
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command: %s\n" % " ".join(command))
        log.flush()
        try:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as error:
            launch_error = str(error)
            log.write(f"launch error: {error}\n")
            return returncode, timed_out, launch_error
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = terminate_process(process)
    return returncode, timed_out, launch_error


def run_scenario(scenario, command, output, metadata=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "gemrb.log"
    manifest_path = output / "manifest.json"
    started = utc_now()
    monotonic_started = time.monotonic()
    returncode, timed_out, launch_error = run_process(
        command,
        log_path,
        scenario["timeout_seconds"],
    )
    finished = utc_now()
    duration = time.monotonic() - monotonic_started
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    failures = classify_result(scenario, returncode, timed_out, launch_error, log_text)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "scenario": {
            "id": scenario["id"],
            "description": scenario["description"],
            "source": scenario["source"],
        },
        "metadata": dict(metadata or {}),
        "command": list(command),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round(duration, 3),
        "engine_log": str(log_path.relative_to(output)),
        "engine_returncode": returncode,
        "timed_out": timed_out,
        "status": "success" if not failures else "failure",
        "failures": failures,
        "assertions": {
            "expected_exit_codes": scenario["expected_exit_codes"],
            "expected_log_markers": scenario["expected_log_markers"],
            "forbidden_log_markers": list(DEFAULT_FORBIDDEN_LOG_MARKERS) + scenario["forbidden_log_markers"],
        },
    }
    write_manifest(manifest_path, manifest)
    return manifest_path, manifest


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one deterministic GemRB acceptance scenario and emit a machine-readable manifest."
    )
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("gemrb-acceptance"))
    parser.add_argument("--gemrb-version", default="")
    parser.add_argument("--gemrb-commit", default="")
    parser.add_argument("--game-type", default="")
    parser.add_argument("--fixture-id", default="")
    parser.add_argument("--component", action="append", default=[])
    parser.add_argument("--install-order", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("GemRB/scenario command is required after --")
    return args


def main(argv=None):
    args = parse_args(argv)
    scenario = load_scenario(args.scenario)
    if scenario["supported_game_types"] and args.game_type:
        if args.game_type not in scenario["supported_game_types"]:
            raise ValueError(
                f"scenario {scenario['id']} does not support game type {args.game_type}; "
                f"expected one of {scenario['supported_game_types']}"
            )
    metadata = {
        "gemrb_version": args.gemrb_version,
        "gemrb_commit": args.gemrb_commit,
        "game_type": args.game_type,
        "fixture_id": args.fixture_id,
        "components": args.component,
        "install_order": args.install_order,
    }
    manifest_path, manifest = run_scenario(scenario, args.command, args.output, metadata)
    print(manifest_path)
    if manifest["failures"]:
        first = manifest["failures"][0]
        print(
            f"FAILED {scenario['id']}: {first['kind']}: {first['detail']}",
            file=sys.stderr,
        )
        return 1
    print(f"PASSED {scenario['id']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
