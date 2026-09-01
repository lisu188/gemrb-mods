#!/usr/bin/env python3
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from gemrb_acceptance import MANIFEST_SCHEMA_VERSION, utc_now, write_manifest
from prepare_acceptance_fixture import load_fixture

MODS = {
    "cipher": {
        "tp2": "cipher/setup-cipher.tp2",
        "handler": "cipher",
        "wrapper": "cipher/tools/install_guiscripts.py",
    },
    "psion": {
        "tp2": "psion/setup-psion.tp2",
        "handler": "psionics",
        "wrapper": "psion/tools/install_guiscripts.py",
    },
}

WATCHED_FILES = (
    "ActionsWindow.py",
    "Spellbook.py",
    "MenuWindow.py",
    "GUISTORE.py",
    "LUSpellSelection.py",
    "LUProfsSelection.py",
    "bg1/GUICG2.py",
    "bg1/GUICG3.py",
    "bg2/GUICG2.py",
    "bg2/GUICG3.py",
    "bg2/GUICG7.py",
    "GemRBModCore.py",
    "GemRBModClassChoice.py",
    "GemRBModPsionChoice.py",
    "GemRBModStrings.py",
    "Transactions.py",
    "InnateCharges.py",
    "PersistentState.py",
    "Selectors.py",
    "Cipher.py",
    "Psionics.py",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_files(guiscripts):
    guiscripts = Path(guiscripts)
    result = {}
    for relative in WATCHED_FILES:
        path = guiscripts / relative
        result[relative] = None if not path.is_file() else sha256(path)
    return result


def active_handlers(guiscripts):
    prefix = ".gemrbmodcore."
    suffix = ".active"
    result = []
    for path in Path(guiscripts).glob(f"{prefix}*{suffix}"):
        name = path.name[len(prefix):-len(suffix)]
        if name:
            result.append(name)
    return sorted(result)


def expected_handlers(mods):
    return sorted(MODS[mod]["handler"] for mod in mods)


def verify_handlers(guiscripts, mods):
    expected = expected_handlers(mods)
    actual = active_handlers(guiscripts)
    if actual != expected:
        raise RuntimeError(f"active handler mismatch: expected {expected}, got {actual}")
    return actual


def load_matrix(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        raise ValueError("matrix must contain a string id")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("matrix must contain at least one case")
    seen = set()
    normalized = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise ValueError("every matrix case must contain a string id")
        if case["id"] in seen:
            raise ValueError(f"duplicate matrix case id: {case['id']}")
        seen.add(case["id"])
        install = case.get("install_order")
        uninstall = case.get("uninstall_order")
        if sorted(install or []) != sorted(MODS):
            raise ValueError(f"{case['id']}: install_order must contain cipher and psion exactly once")
        if sorted(uninstall or []) != sorted(MODS):
            raise ValueError(f"{case['id']}: uninstall_order must contain cipher and psion exactly once")
        normalized.append({
            "id": case["id"],
            "install_order": list(install),
            "uninstall_order": list(uninstall),
        })
    return {
        "id": data["id"],
        "description": str(data.get("description", "")),
        "source": str(path),
        "cases": normalized,
    }


def weidu_command(weidu, mod, install):
    action = "--force-install" if install else "--force-uninstall"
    return [
        str(weidu),
        MODS[mod]["tp2"],
        "--use-lang", "en_US",
        action, "0",
        "--no-exit-pause",
    ]


def gui_command(python, game, guiscripts, mod, install):
    command = [
        str(python),
        str(Path(game) / MODS[mod]["wrapper"]),
        str(guiscripts),
    ]
    if not install:
        command.append("--uninstall")
    return command


def run_command(command, cwd, log_path, timeout=600):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("command: %s\n" % " ".join(command))
        log.flush()
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    record = {
        "command": list(command),
        "cwd": str(cwd),
        "log": str(log_path),
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with {completed.returncode}: {' '.join(command)}")
    return record


def execute_case(case, game, guiscripts, output, weidu, python):
    case_output = Path(output) / case["id"]
    case_output.mkdir(parents=True, exist_ok=True)
    baseline = snapshot_files(guiscripts)
    if active_handlers(guiscripts):
        raise RuntimeError(f"fixture begins with active handlers: {active_handlers(guiscripts)}")
    records = []
    installed = []
    sequence = 0

    def invoke(phase, mod, command):
        nonlocal sequence
        sequence += 1
        log_path = case_output / f"{sequence:02d}-{phase}-{mod}.log"
        record = run_command(command, game, log_path)
        record.update({"phase": phase, "mod": mod})
        records.append(record)

    for mod in case["install_order"]:
        invoke("weidu-install", mod, weidu_command(weidu, mod, True))
        invoke("gui-install", mod, gui_command(python, game, guiscripts, mod, True))
        installed.append(mod)
        records[-1]["active_handlers"] = verify_handlers(guiscripts, installed)

    for mod in case["uninstall_order"]:
        invoke("gui-uninstall", mod, gui_command(python, game, guiscripts, mod, False))
        installed.remove(mod)
        records[-1]["active_handlers"] = verify_handlers(guiscripts, installed)
        invoke("weidu-uninstall", mod, weidu_command(weidu, mod, False))

    restored = snapshot_files(guiscripts)
    differences = [
        relative for relative in WATCHED_FILES
        if restored[relative] != baseline[relative]
    ]
    if differences:
        raise RuntimeError(f"GemRB GUI/runtime restoration mismatch: {differences}")
    return {
        "id": case["id"],
        "install_order": case["install_order"],
        "uninstall_order": case["uninstall_order"],
        "steps": records,
        "restored": True,
    }


def run_matrix(matrix, fixture, output, weidu="weidu", python=sys.executable, case_id=None):
    fixture_data, game, guiscripts = load_fixture(fixture)
    required = {"common", "cipher", "psion"}
    packages = set(fixture_data.get("packages", []))
    missing = sorted(required - packages)
    if missing:
        raise ValueError(f"fixture is missing required packages: {missing}")
    cases = matrix["cases"]
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            raise ValueError(f"unknown matrix case: {case_id}")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    results = []
    failure = None
    try:
        for case in cases:
            results.append(execute_case(case, game, guiscripts, output, weidu, python))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        failure = str(error)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "matrix": {
            "id": matrix["id"],
            "description": matrix["description"],
            "source": matrix["source"],
        },
        "fixture": {
            "id": fixture_data.get("fixture_id", ""),
            "game_type": fixture_data.get("game_type", ""),
        },
        "started_at": started.isoformat(),
        "finished_at": utc_now().isoformat(),
        "status": "failure" if failure else "success",
        "failure": failure,
        "cases": results,
    }
    manifest_path = output / "lifecycle-manifest.json"
    write_manifest(manifest_path, manifest)
    return manifest_path, manifest


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Exercise Cipher/Psion WeiDU and shared GemRB GUI ownership in both lifecycle orders."
    )
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weidu", default="weidu")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--case")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    matrix = load_matrix(args.matrix)
    manifest_path, manifest = run_matrix(
        matrix,
        args.fixture,
        args.output,
        args.weidu,
        args.python,
        args.case,
    )
    print(manifest_path)
    if manifest["status"] != "success":
        print(f"FAILED {matrix['id']}: {manifest['failure']}", file=sys.stderr)
        return 1
    print(f"PASSED {matrix['id']}: {len(manifest['cases'])} lifecycle cases")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
