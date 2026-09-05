#!/usr/bin/env python3
from pathlib import Path
import argparse
import datetime as dt
import json
import subprocess
import sys
import time

MANIFEST_SCHEMA_VERSION = 1
CHECKPOINT_PREFIX = "GEMRB_ACCEPTANCE_CHECKPOINT|"
DEFAULT_FORBIDDEN_LOG_MARKERS = (
    "Traceback (most recent call last):",
    "[GUIScript/ERROR]: Runtime Error:",
    "[GUIScript/ERROR]: Unhandled target type",
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


def _required_checkpoints(value):
    checkpoints = _string_list(value, "required_checkpoints")
    if len(set(checkpoints)) != len(checkpoints):
        raise ValueError("scenario field required_checkpoints must not contain duplicate IDs")
    if any(item != item.strip() for item in checkpoints):
        raise ValueError("scenario field required_checkpoints IDs must not have surrounding whitespace")
    return checkpoints


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
        "required_checkpoints": _required_checkpoints(data.get("required_checkpoints")),
        "prerequisites": _string_list(data.get("prerequisites"), "prerequisites"),
        "instructions": _string_list(data.get("instructions"), "instructions"),
        "source": str(path),
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"non-finite JSON value {value}")


def parse_checkpoints(log_text, required=()):
    """Compare emitted observations; a claimed success flag is never an oracle."""
    records = []
    failures = []
    seen = set()
    for line_number, line in enumerate(log_text.splitlines(), 1):
        # The runner's command header can contain literal checkpoint examples.
        if line.startswith("command: ") or CHECKPOINT_PREFIX not in line:
            continue
        payload = line.split(CHECKPOINT_PREFIX, 1)[1].strip()
        try:
            record = json.loads(
                payload, object_pairs_hook=_unique_object, parse_constant=_invalid_constant,
            )
            if not isinstance(record, dict):
                raise ValueError("checkpoint must be a JSON object")
            if set(record) - {"id", "actual", "expected", "context"}:
                raise ValueError("checkpoint has unsupported fields")
            if not {"id", "actual", "expected"}.issubset(record):
                raise ValueError("checkpoint requires id, actual and expected")
            checkpoint_id = record["id"]
            if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
                raise ValueError("checkpoint id must be a non-empty string")
            if checkpoint_id != checkpoint_id.strip():
                raise ValueError("checkpoint id must not have surrounding whitespace")
            if "context" in record and not isinstance(record["context"], dict):
                raise ValueError("checkpoint context must be an object")
            # JSON numeric overflow also produces infinity inside metadata.
            # Validate the whole record so every retained value is finite JSON.
            json.dumps(record, allow_nan=False)
            # Canonical JSON distinguishes true from 1, unlike Python equality.
            actual = json.dumps(record["actual"], sort_keys=True, allow_nan=False)
            expected = json.dumps(record["expected"], sort_keys=True, allow_nan=False)
        except (ValueError, TypeError) as error:
            failures.append({"kind": "malformed_checkpoint", "detail": f"line {line_number}: {error}"})
            continue
        duplicate = checkpoint_id in seen
        seen.add(checkpoint_id)
        status = "failure" if duplicate or actual != expected else "success"
        records.append(dict(record, line=line_number, status=status))
        if duplicate:
            failures.append({"kind": "duplicate_checkpoint", "detail": checkpoint_id})
        if actual != expected:
            failures.append({"kind": "checkpoint_mismatch", "detail": checkpoint_id})
    for checkpoint_id in required:
        if checkpoint_id not in seen:
            failures.append({"kind": "missing_checkpoint", "detail": checkpoint_id})
    return records, failures


def classify_result(scenario, returncode, timed_out, launch_error, log_text, checkpoint_failures=None):
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
    if checkpoint_failures is None:
        _, checkpoint_failures = parse_checkpoints(log_text, scenario.get("required_checkpoints", ()))
    failures.extend(checkpoint_failures)
    return failures


def run_process(command, log_path, timeout_seconds):
    timed_out = False
    launch_error = None
    returncode = None
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command: %s\n" % json.dumps(list(command)))
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
    checkpoints, checkpoint_failures = parse_checkpoints(log_text, scenario.get("required_checkpoints", ()))
    failures = classify_result(scenario, returncode, timed_out, launch_error, log_text, checkpoint_failures)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "scenario": {
            "id": scenario["id"],
            "description": scenario["description"],
            "source": scenario["source"],
            "prerequisites": scenario.get("prerequisites", []),
            "instructions": scenario.get("instructions", []),
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
        "checkpoints": checkpoints,
        "assertions": {
            "expected_exit_codes": scenario["expected_exit_codes"],
            "expected_log_markers": scenario["expected_log_markers"],
            "forbidden_log_markers": list(DEFAULT_FORBIDDEN_LOG_MARKERS) + scenario["forbidden_log_markers"],
            "required_checkpoints": scenario.get("required_checkpoints", []),
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
