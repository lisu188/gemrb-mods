#!/usr/bin/env python3
"""Synthetic tamper/incompleteness tests; no live campaign acceptance is claimed."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def load_checker():
    spec = importlib.util.spec_from_file_location("check_acceptance_matrix", ROOT / "common/tools/check_acceptance_matrix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")
    return path


def main():
    check = load_checker()
    engine, mods = "a" * 40, "b" * 40
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        binary = root / "synthetic-engine"
        binary.write_text("Synthetic executable placeholder for provenance tests only")
        build = write(root / "build.json", {"engine_commit": engine, "engine_status": "",
                      "install_root": str(root), "files": {binary.name: check.digest(binary)}})
        frozen = write(root / "frozen.json", {"engine_commit": engine, "mods_commit": mods,
                       "fixture_id": "synthetic", "family": "bg2ee"})
        scenario_path = check.ACCEPTANCE / "scenarios/sorcerer-monk-tob-hla.json"
        scenario = check.load_scenario(scenario_path)
        provenance = write(root / "provenance.json", {"engine_commit": engine, "mods_commit": mods,
            "fixture_id": "synthetic", "game_type": "bg2ee", "build": str(build),
            "build_sha256": check.digest(build), "frozen_fixture": str(frozen),
            "frozen_fixture_sha256": check.digest(frozen), "scenario": str(scenario_path),
            "scenario_sha256": check.digest(scenario_path)})
        image = root / "synthetic.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic signature test, not a screenshot")
        records = [{"id": name, "actual": 7, "expected": 7,
                    "context": {"oracle": "synthetic test oracle", "screenshot": str(image)}}
                   for name in scenario["required_checkpoints"]]
        log = root / "gemrb.log"
        log.write_text("\n".join("GEMRB_ACCEPTANCE_CHECKPOINT|" + json.dumps(r) for r in records))
        checkpoints, failures = check.parse_checkpoints(log.read_text(), scenario["required_checkpoints"])
        assert not failures
        manifest = {"schema_version": 1, "scenario": {"id": scenario["id"]},
                    "metadata": {"gemrb_commit": engine, "mods_commit": mods, "game_type": "bg2ee",
                                 "fixture_id": "synthetic", "campaign": "tob",
                                 "components": sorted(check.COMPONENTS), "install_order": sorted(check.COMPONENTS),
                                 "provenance": {"path": str(provenance), "sha256": check.digest(provenance)}},
                    "status": "success", "failures": [], "timed_out": False,
                    "engine_returncode": 0, "engine_log": "gemrb.log", "checkpoints": checkpoints}
        manifest_path = write(root / "manifest.json", manifest)
        entry = {"id": "synthetic.tob", "game_type": "bg2ee", "campaign": "tob",
                 "scenario": "scenarios/sorcerer-monk-tob-hla.json", "manifest": "manifest.json"}
        matrix = write(root / "matrix.json", {"id": "synthetic-only", "scenario_runs": [entry], "lifecycle_runs": []})

        def result():
            return check.check_matrix(root, engine, mods, matrix)

        assert result()["status"] == "success"
        for label, mutation in (
            ("stale mods", lambda d: d["metadata"].update(mods_commit="c" * 40)),
            ("missing ToB", lambda d: d["metadata"].update(campaign="soa")),
            ("fake success", lambda d: d.update(engine_returncode=-11)),
            ("edited checkpoints", lambda d: d["checkpoints"].pop()),
        ):
            changed = copy.deepcopy(manifest)
            mutation(changed)
            write(manifest_path, changed)
            assert result()["status"] == "failure", label
        write(manifest_path, manifest)
        original = log.read_text()
        log.write_text(original + "\n[GUIScript/ERROR]: Runtime Error:")
        assert result()["status"] == "failure"
        log.write_text(original)
        binary.write_text("changed binary")
        assert result()["status"] == "failure"
        binary.write_text("Synthetic executable placeholder for provenance tests only")
        image.unlink()
        assert result()["status"] == "failure"
        manifest_path.unlink()
        assert result()["status"] == "failure"
        full = check.check_matrix(root, engine, mods)
        assert full["status"] == "failure" and len(full["runs"]) == 13

        lifecycle_entry = {"game_type": "bgee", "matrix": "matrices/cipher-psion-lifecycle.json"}
        required = check.read_json(check.ACCEPTANCE / lifecycle_entry["matrix"])
        steps_log = root / "install.log"
        steps_log.write_text("synthetic install output")
        cases = []
        for case in required["cases"]:
            current, steps = set(), []
            for action, order in (("install", case["install_order"]), ("uninstall", case["uninstall_order"])):
                for mod in order:
                    phases = ("weidu-install", "gui-install") if action == "install" else ("gui-uninstall", "weidu-uninstall")
                    for phase in phases:
                        step = {"phase": phase, "mod": mod, "returncode": 0, "log": str(steps_log)}
                        if phase.startswith("gui-"):
                            handler = {"cipher": "cipher", "psion": "psionics"}[mod]
                            current.add(handler) if action == "install" else current.remove(handler)
                            step["active_handlers"] = sorted(current)
                        steps.append(step)
            cases.append(dict(case, restored=True, steps=steps))
        lifecycle = {"schema_version": 1, "matrix": {"id": required["id"]},
                     "fixture": {"game_type": "bgee"}, "status": "success", "failure": None, "cases": cases}
        check.check_lifecycle(lifecycle, root / "lifecycle.json", lifecycle_entry)
        for action in (lambda d: d["cases"].pop(),
                       lambda d: d["cases"][0].update(restored=False),
                       lambda d: d["cases"][0]["steps"][1].update(active_handlers=[])):
            invalid = copy.deepcopy(lifecycle)
            action(invalid)
            try:
                check.check_lifecycle(invalid, root / "lifecycle.json", lifecycle_entry)
            except ValueError:
                pass
            else:
                raise AssertionError("incomplete lifecycle accepted")
    print("Acceptance matrix evidence validation passed (synthetic only)")


if __name__ == "__main__":
    main()
