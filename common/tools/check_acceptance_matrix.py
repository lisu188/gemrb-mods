#!/usr/bin/env python3
"""Check retained campaign evidence; this does not run or authenticate gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from gemrb_acceptance import classify_result, load_scenario, parse_checkpoints

ACCEPTANCE = TOOLS.parent / "acceptance"
COMPONENTS = {"cipher", "psion", "sorcerer-monk"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"not a JSON object: {path}")
    return value


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve_file(value, base):
    require(isinstance(value, str) and bool(value), "missing evidence path")
    path = Path(value)
    path = path if path.is_absolute() else base / path
    require(path.is_file() and path.stat().st_size > 0, f"missing or empty evidence: {path}")
    return path.resolve()


def bound_file(value, sha256, base):
    path = resolve_file(value, base)
    require(isinstance(sha256, str) and re.fullmatch(r"[0-9a-f]{64}", sha256),
            f"missing SHA-256 for {path}")
    require(digest(path) == sha256, f"SHA-256 mismatch: {path}")
    return path


def verify_provenance(manifest, path, entry, engine_commit, mods_commit):
    metadata = manifest.get("metadata", {})
    require(isinstance(metadata, dict), "metadata must be an object")
    require(metadata.get("gemrb_commit") == engine_commit, "engine revision mismatch")
    require(metadata.get("mods_commit") == mods_commit, "mods revision mismatch")
    ref = metadata.get("provenance", {})
    source = bound_file(ref.get("path"), ref.get("sha256"), path.parent)
    provenance = read_json(source)
    for key, expected in (("engine_commit", engine_commit), ("mods_commit", mods_commit),
                          ("game_type", entry["game_type"])):
        require(provenance.get(key) == expected, f"provenance {key} mismatch")
    fixture = manifest.get("fixture", {})
    fixture_id = metadata.get("fixture_id", fixture.get("id"))
    require(fixture_id and provenance.get("fixture_id") == fixture_id, "fixture identity mismatch")
    build_path = bound_file(provenance.get("build"), provenance.get("build_sha256"), source.parent)
    build = read_json(build_path)
    require(build.get("engine_commit") == engine_commit and build.get("engine_status") == "",
            "build is not from the exact clean engine revision")
    files = build.get("files")
    require(isinstance(files, dict) and files, "build file hashes absent")
    install = Path(build.get("install_root", str(build_path.parent)))
    for filename, sha256 in files.items():
        bound_file(filename, sha256, install)
    frozen_path = bound_file(provenance.get("frozen_fixture"),
                             provenance.get("frozen_fixture_sha256"), source.parent)
    frozen = read_json(frozen_path)
    require(frozen.get("engine_commit") == engine_commit and frozen.get("mods_commit") == mods_commit,
            "frozen fixture revision mismatch")
    require(frozen.get("fixture_id") == fixture_id, "frozen fixture identity mismatch")
    require(frozen.get("family", frozen.get("game_type")) == entry["game_type"],
            "frozen fixture game family mismatch")
    if "scenario" in entry:
        scenario = ACCEPTANCE / entry["scenario"]
        recorded = bound_file(provenance.get("scenario"), provenance.get("scenario_sha256"), source.parent)
        require(digest(recorded) == digest(scenario), "scenario differs from current required scenario")
    return provenance


def check_scenario(manifest, path, entry):
    scenario = load_scenario(ACCEPTANCE / entry["scenario"])
    require(manifest.get("schema_version") == 1, "scenario requires schema version 1")
    require(manifest.get("scenario", {}).get("id") == scenario["id"], "scenario identity mismatch")
    require(manifest.get("metadata", {}).get("game_type") == entry["game_type"], "game family mismatch")
    require(manifest.get("status") == "success" and manifest.get("failures") == [], "scenario unsuccessful")
    require(manifest.get("engine_returncode") == 0 and manifest.get("timed_out") is False,
            "engine did not exit normally")
    metadata = manifest["metadata"]
    require(sorted(metadata.get("components", [])) == sorted(COMPONENTS), "combined components missing")
    require(sorted(metadata.get("install_order", [])) == sorted(COMPONENTS), "invalid install order")
    log_path = resolve_file(manifest.get("engine_log"), path.parent)
    log = log_path.read_text(encoding="utf-8", errors="replace")
    checkpoints, failures = parse_checkpoints(log, scenario["required_checkpoints"])
    failures = classify_result(scenario, manifest["engine_returncode"], False, None, log, failures)
    require(not failures, f"retained log fails current scenario: {failures}")
    require(checkpoints == manifest.get("checkpoints"), "manifest checkpoints differ from retained log")
    for checkpoint in checkpoints:
        context = checkpoint.get("context", {})
        require(context.get("oracle"), f"{checkpoint['id']}: independent oracle reference missing")
        images = context.get("screenshots", [])
        if context.get("screenshot"):
            images = [context["screenshot"], *images]
        require(isinstance(images, list) and images, f"{checkpoint['id']}: rendered evidence missing")
        for filename in images:
            image = resolve_file(filename, path.parent)
            require(image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"not a PNG screenshot: {image}")
    if entry.get("campaign"):
        require(metadata.get("campaign") == entry["campaign"], "actual ToB campaign metadata missing")


def check_lifecycle(manifest, path, entry):
    required = read_json(ACCEPTANCE / entry["matrix"])
    require(manifest.get("schema_version") == 1, "lifecycle requires schema version 1")
    require(manifest.get("matrix", {}).get("id") == required["id"], "lifecycle identity mismatch")
    require(manifest.get("fixture", {}).get("game_type") == entry["game_type"], "lifecycle family mismatch")
    require(manifest.get("status") == "success" and manifest.get("failure") is None,
            "lifecycle unsuccessful")
    cases = manifest.get("cases", [])
    require(len(cases) == len(required["cases"]), "lifecycle case count mismatch")
    for expected, case in zip(required["cases"], cases):
        require(all(case.get(key) == expected[key] for key in ("id", "install_order", "uninstall_order")),
                "lifecycle case identity/order mismatch")
        require(case.get("restored") is True, "lifecycle restoration incomplete")
        steps = case.get("steps", [])
        sequence = [(phase, mod) for action, order in (("install", case["install_order"]),
                                                     ("uninstall", case["uninstall_order"]))
                    for mod in order for phase in
                    (("weidu-install", "gui-install") if action == "install"
                     else ("gui-uninstall", "weidu-uninstall"))]
        require([(s.get("phase"), s.get("mod")) for s in steps] == sequence, "lifecycle transitions missing")
        active = set()
        for step in steps:
            require(step.get("returncode") == 0, "lifecycle command failed")
            resolve_file(step.get("log"), path.parent)
            if step["phase"].startswith("gui-"):
                handler = {"cipher": "cipher", "psion": "psionics"}[step["mod"]]
                active.add(handler) if step["phase"] == "gui-install" else active.remove(handler)
                require(step.get("active_handlers") == sorted(active), "lifecycle handler transition mismatch")


def check_ownership(path, entry, engine_commit, mods_commit):
    manifest = read_json(path)
    verify_provenance(manifest, path, entry, engine_commit, mods_commit)
    require(manifest.get("status") == "success", "Sorcerer/Monk ownership incomplete")
    cases = manifest.get("cases", [])
    require({c.get("id") for c in cases} == {"remove-sorcerer-monk-first", "retain-sorcerer-monk-last"}
            and len(cases) == 2, "Sorcerer/Monk ownership cases missing")
    for case in cases:
        require(case.get("gui_restored") is True and case.get("override_restored") is True,
                "Sorcerer/Monk restoration incomplete")
        order = case.get("uninstall_order", [])
        require(sorted(case.get("install_order", [])) == sorted(COMPONENTS)
                and sorted(order) == sorted(COMPONENTS), "Sorcerer/Monk installation order incomplete")
        index = 0 if case["id"] == "remove-sorcerer-monk-first" else -1
        require(order[index] == "sorcerer-monk", "Sorcerer/Monk ownership order mismatch")
        require(len(case.get("steps", [])) == 6, "Sorcerer/Monk ownership transitions incomplete")
        expected_steps = [(phase, mod) for phase, order in (("install", case["install_order"]),
                                                          ("uninstall", case["uninstall_order"]))
                          for mod in order]
        require([(s.get("phase"), s.get("mod")) for s in case["steps"]] == expected_steps,
                "Sorcerer/Monk ownership transition order mismatch")
        active = set()
        for step in case["steps"]:
            handler = {"cipher": "cipher", "psion": "psionics", "sorcerer-monk": "sorcerermonkui"}[step["mod"]]
            active.add(handler) if step["phase"] == "install" else active.remove(handler)
            require(step.get("state", {}).get("active_handlers") == sorted(active),
                    "Sorcerer/Monk ownership handler transition mismatch")
            require(step.get("logs"), "Sorcerer/Monk installation log missing")
            for filename in step["logs"]:
                resolve_file(filename, path.parent)
    standalone = manifest.get("standalone", {})
    require(standalone.get("state", {}).get("active_handlers") == ["sorcerermonkui"],
            "standalone Sorcerer/Monk handler missing")
    require(standalone.get("logs"), "standalone installation logs missing")
    for filename in standalone["logs"]:
        resolve_file(filename, path.parent)
    resolve_file(standalone.get("oracle"), path.parent)


def check_matrix(evidence_root, engine_commit, mods_commit, matrix=None):
    for revision in (engine_commit, mods_commit):
        require(re.fullmatch(r"[0-9a-f]{40}", revision or ""), "supply exact 40-character Git revisions")
    root = Path(evidence_root).resolve()
    matrix = read_json(matrix or ACCEPTANCE / "matrices/three-class-acceptance.json")
    entries = matrix["scenario_runs"] + matrix["lifecycle_runs"]
    require(len({e["id"] for e in entries}) == len(entries), "duplicate matrix run ID")
    require(len({e["manifest"] for e in entries}) == len(entries), "duplicate matrix manifest")
    results = []
    for entry in entries:
        try:
            relative = Path(entry["manifest"])
            require(not relative.is_absolute() and ".." not in relative.parts, "unsafe matrix manifest path")
            path = root / relative
            manifest = read_json(path)
            verify_provenance(manifest, path, entry, engine_commit, mods_commit)
            if "scenario" in entry:
                check_scenario(manifest, path, entry)
            else:
                check_lifecycle(manifest, path, entry)
                check_ownership(root / entry["ownership_manifest"], entry, engine_commit, mods_commit)
            results.append({"id": entry["id"], "status": "success"})
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
            results.append({"id": entry["id"], "status": "failure", "detail": str(error)})
    return {"schema_version": 1, "matrix": matrix["id"], "engine_commit": engine_commit,
            "mods_commit": mods_commit, "status": "success" if all(r["status"] == "success" for r in results) else "failure",
            "review_required": "Inspect rendered UI, independent oracles and fixture preparation; this checker cannot authenticate gameplay.",
            "runs": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--engine-commit", required=True)
    parser.add_argument("--mods-commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = check_matrix(args.evidence_root, args.engine_commit, args.mods_commit)
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
