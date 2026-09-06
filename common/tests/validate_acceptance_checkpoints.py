#!/usr/bin/env python3
"""Public synthetic checks of evidence validation, not live gameplay proof."""

from contextlib import redirect_stdout
from pathlib import Path
import argparse
import ast
import importlib.util
import io
import json
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "common" / "acceptance" / "scenarios"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def kinds(failures):
    return {failure["kind"] for failure in failures}


def validate_campaign_inventory(harness):
    """Keep every required gate while excluding campaign-impossible levels."""
    acceptance = SCENARIOS.parent
    inventory = json.loads((acceptance / "matrices/three-class-acceptance.json").read_text())
    runs = inventory["scenario_runs"]
    lifecycle = inventory["lifecycle_runs"]
    all_runs = runs + lifecycle
    assert len({run["id"] for run in all_runs}) == len(all_runs)
    assert len({run["manifest"] for run in all_runs}) == len(all_runs)
    for run in all_runs:
        manifest = Path(run["manifest"])
        assert not manifest.is_absolute() and ".." not in manifest.parts
        assert manifest.parts[0] == run["game_type"]
        assert run["id"].startswith(run["game_type"] + ".")
    assert {run["game_type"] for run in all_runs} == {"bgee", "bg2ee"}

    expected = {
        (family, scenario)
        for family in ("bgee", "bg2ee")
        for scenario in (
            "chargen-three-classes", "psion-six-disciplines-chargen",
            *(name + "-gameplay-progression-" + family
              for name in ("psion", "cipher", "sorcerer-monk")),
        )
    }
    expected.add(("bg2ee", "sorcerer-monk-tob-hla"))
    actual = set()
    for run in runs:
        scenario = harness.load_scenario(acceptance / run["scenario"])
        actual.add((run["game_type"], scenario["id"]))
        assert run["game_type"] in scenario["supported_game_types"]
        assert scenario["expected_exit_codes"] == [0]
        assert scenario["prerequisites"] and scenario["instructions"]
        required = scenario["required_checkpoints"]
        assert required
        # Exercise the real strict classifier for every inventory entry; these
        # synthetic observations establish no gameplay acceptance.
        lines = [harness.CHECKPOINT_PREFIX + json.dumps({
            "id": checkpoint, "actual": 7, "expected": 7,
        }) for checkpoint in required]
        log = "\n".join(lines)
        assert harness.classify_result(scenario, 0, False, None, log) == []
        assert kinds(harness.classify_result(scenario, 0, False, None, "\n".join(lines[:-1]))) == {"missing_checkpoint"}
        assert kinds(harness.classify_result(scenario, 0, True, None, log)) == {"timeout"}
        assert kinds(harness.classify_result(scenario, 0, False, None,
                                             log + "\n[GUIScript/ERROR]: Unhandled target type: 2")) == {"forbidden_log_marker"}
        if scenario["id"] == "chargen-three-classes":
            assert {"chargen.restrictions", "chargen.initial-spellbooks", "chargen.action-bars"} <= set(required)
        if scenario["id"] == "sorcerer-monk-tob-hla":
            assert run["campaign"] == "tob"
    assert actual == expected and len(runs) == len(expected)

    assert len(lifecycle) == 2
    assert {run["game_type"] for run in lifecycle} == {"bgee", "bg2ee"}
    for run in lifecycle:
        matrix = json.loads((acceptance / run["matrix"]).read_text())
        assert {(tuple(case["install_order"]), tuple(case["uninstall_order"]))
                for case in matrix["cases"]} == {
                    (install, uninstall)
                    for install in (("cipher", "psion"), ("psion", "cipher"))
                    for uninstall in (("cipher", "psion"), ("psion", "cipher"))
                }

    for name in ("psion", "cipher", "sorcerer-monk"):
        legacy = harness.load_scenario(SCENARIOS / (name + "-gameplay-progression.json"))
        bgee_path = SCENARIOS / (name + "-gameplay-progression-bgee.json")
        bgee = harness.load_scenario(bgee_path)
        bg2ee = harness.load_scenario(SCENARIOS / (name + "-gameplay-progression-bg2ee.json"))
        assert bgee["supported_game_types"] == ["bgee"]
        assert bg2ee["supported_game_types"] == ["bg2ee"]
        assert bg2ee["required_checkpoints"] == legacy["required_checkpoints"]
        original = set(legacy["required_checkpoints"])
        current = set(bgee["required_checkpoints"])
        removed = {
            "psion": {"psion.level.17-plus"},
            "cipher": {"cipher.level.16", "cipher.level.19",
                       "cipher.reaping-knives.owner", "cipher.reaping-knives.transfer",
                       "cipher.reaping-knives.expiry", "cipher.reaping-knives.save-reload"},
            "sorcerer-monk": {"sorcerer-monk.level.high"},
        }[name]
        added = {name + ".level.cap"}
        if name == "cipher":
            added.add("cipher.tier-restrictions")
        assert original - current == removed
        assert current - original == added
        assert original - removed <= current
        for scenario in (bgee, bg2ee):
            assert any("XPCAP" in item and "XPLEVEL" in item for item in scenario["prerequisites"])
        # Wrong-family and EET requests fail before launching any process.
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "must-not-launch"
            for game_type in ("bg2ee", "eet"):
                try:
                    harness.main(["--scenario", str(bgee_path), "--output", str(output),
                                  "--game-type", game_type, "--", sys.executable,
                                  "-c", "raise RuntimeError('must not launch')"])
                except ValueError as error:
                    assert "does not support game type" in str(error)
                else:
                    raise AssertionError("wrong-family scenario was accepted")
                assert not output.exists()


def validate_console_checkpoint(helper, harness, gemrb_root):
    """Execute the actual upstream console callback without starting GemRB."""
    source = gemrb_root / "gemrb" / "GUIScripts" / "Console.py"
    parsed = ast.parse(source.read_text(encoding="utf-8"))
    callback = next(node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name == "Exec")
    displayed = []
    console = SimpleNamespace(Append=displayed.append)
    namespace = {"GemRB": SimpleNamespace(GetView=lambda *args: console)}
    exec(compile(ast.Module(body=[callback], type_ignores=[]), str(source), "exec"), namespace)
    previous = sys.modules.get("GemRBAcceptance")
    sys.modules["GemRBAcceptance"] = helper
    captured = io.StringIO()
    try:
        with redirect_stdout(captured):
            result = namespace["Exec"]("GemRBAcceptance.checkpoint('console.observation', 7, 7)")
            assert sys.stdout is captured
    finally:
        if previous is None:
            del sys.modules["GemRBAcceptance"]
        else:
            sys.modules["GemRBAcceptance"] = previous
    records, failures = harness.parse_checkpoints(captured.getvalue(), ["console.observation"])
    assert not failures, failures
    assert records[0]["actual"] == records[0]["expected"] == 7
    assert result["id"] == "console.observation"
    assert len(displayed) == 1 and helper.CHECKPOINT_PREFIX in displayed[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemrb-root", type=Path, help="Also exercise the actual GemRB Console.Exec callback")
    args = parser.parse_args()
    harness = load_module("gemrb_acceptance", ROOT / "common" / "tools" / "gemrb_acceptance.py")
    helper = load_module("GemRBAcceptance", ROOT / "common" / "acceptance" / "GemRBAcceptance.py")
    prefix = harness.CHECKPOINT_PREFIX
    assert helper.CHECKPOINT_PREFIX == prefix
    observation = {
        "id": "pool.after-cast",
        "actual": {"pool": 7, "powers": ["power1", "power2"]},
        "expected": {"powers": ["power1", "power2"], "pool": 7},
        "context": {"oracle": "before 10 minus installed cost 3"},
    }
    line = prefix + json.dumps(observation)
    records, failures = harness.parse_checkpoints("[Python/Message]: " + line, [observation["id"]])
    assert not failures
    assert records == [dict(observation, line=1, status="success")]

    for actual, expected in [(True, 1), ([1, 2], [2, 1]), ({"pool": 9}, {"pool": 7})]:
        payload = dict(observation, actual=actual, expected=expected)
        records, failures = harness.parse_checkpoints(prefix + json.dumps(payload))
        assert kinds(failures) == {"checkpoint_mismatch"}
        assert records[0]["status"] == "failure"

    malformed_payloads = [
        "{not json}",
        "[]",
        '{"id":"pool.after-cast","passed":true}',
        '{"id":"pool.after-cast","actual":0}',
        '{"id":"pool.after-cast","actual":0,"expected":1,"passed":true}',
        '{"id":"pool.after-cast","actual":NaN,"expected":NaN}',
        '{"id":"pool.after-cast","actual":1e999,"expected":1e999}',
        '{"id":"pool.after-cast","actual":1,"expected":1,"context":{"cost":1e999}}',
        '{"id":"pool.after-cast","actual":1,"expected":1,"context":{"oracle":{"costs":[-1e999]}}}',
        '{"id":"pool.after-cast","actual":0,"actual":1,"expected":1}',
        '{"id":"pool.after-cast","actual":{"x":0,"x":1},"expected":{"x":1}}',
        '{"id":" ","actual":0,"expected":0}',
        '{"id":" pool.after-cast","actual":0,"expected":0}',
        '{"id":1,"actual":0,"expected":0}',
        '{"id":"pool.after-cast","actual":0,"expected":0,"context":"not object"}',
        json.dumps(observation) + " trailing text",
    ]
    for payload in malformed_payloads:
        records, failures = harness.parse_checkpoints(prefix + payload, [observation["id"]])
        assert records == [], payload
        assert kinds(failures) == {"malformed_checkpoint", "missing_checkpoint"}, payload

    records, failures = harness.parse_checkpoints(line + "\n" + line, [observation["id"]])
    assert kinds(failures) == {"duplicate_checkpoint"}
    assert [record["status"] for record in records] == ["success", "failure"]
    records, failures = harness.parse_checkpoints("ordinary output", ["never-emitted"])
    assert records == []
    assert failures == [{"kind": "missing_checkpoint", "detail": "never-emitted"}]

    # The helper must read engine state without invoking any mutating API.
    calls = []
    def stat(actor, stat_id, base):
        calls.append(("stat", actor, stat_id, base))
        return {5: 23, 6: 0}[stat_id]
    def variable(name):
        calls.append(("variable", name))
        return 1
    original_gemrb = sys.modules.get("GemRB")
    sys.modules["GemRB"] = SimpleNamespace(GetPlayerStat=stat, GetVar=variable)
    try:
        actual = helper.capture_actor(1, {"class": 5, "kit": 6}, ["Slot"], base=True)
    finally:
        if original_gemrb is None:
            del sys.modules["GemRB"]
        else:
            sys.modules["GemRB"] = original_gemrb
    assert actual == {"actor": 1, "stats": {"class": 23, "kit": 0}, "variables": {"Slot": 1}}
    assert calls == [("stat", 1, 5, 1), ("stat", 1, 6, 1), ("variable", "Slot")]
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        helper.checkpoint("actor.identity", actual, {"wrong": True}, {"oracle": "independent"})
    records, failures = harness.parse_checkpoints(buffer.getvalue(), ["actor.identity"])
    assert kinds(failures) == {"checkpoint_mismatch"}
    assert records[0]["actual"] == actual
    # GemRB's interactive Console.OutputCapture intentionally exposes write()
    # without flush(). A newline still forwards the observation to its logger.
    written = []
    with redirect_stdout(SimpleNamespace(write=written.append)):
        helper.checkpoint("write-only.console", 7, 7)
    records, failures = harness.parse_checkpoints("".join(written), ["write-only.console"])
    assert not failures, failures
    if args.gemrb_root:
        validate_console_checkpoint(helper, harness, args.gemrb_root.resolve())
    for arguments in [("", 0, 0), (" padded ", 0, 0), ("pool", float("nan"), 0), ("pool", 0, 0, "bad context")]:
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                helper.checkpoint(*arguments)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"invalid helper call accepted: {arguments}")
        assert buffer.getvalue() == ""

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        scenario_path = root / "scenario.json"
        scenario_data = {"id": "pool", "timeout_seconds": 5, "required_checkpoints": ["pool.after-cast"]}
        scenario_path.write_text(json.dumps(scenario_data), encoding="utf-8")
        scenario = harness.load_scenario(scenario_path)
        for name, code, expected_kinds in [
            ("success", f"print({line!r})", set()),
            ("claimed-success", "print('PASSED pool')", {"missing_checkpoint"}),
            ("command-only", f"unused = {line!r}\nprint('ordinary output')", {"missing_checkpoint"}),
            ("multiline-command-only", f"unused = '''\n{line}\n'''", {"missing_checkpoint"}),
            ("duplicate", f"print({line!r}); print({line!r})", {"duplicate_checkpoint"}),
            ("mismatch", f"print({(prefix + json.dumps(dict(observation, actual=0)))!r})", {"checkpoint_mismatch"}),
            ("malformed", f"print({(prefix + '{')!r})", {"malformed_checkpoint", "missing_checkpoint"}),
            ("gui-runtime-error", f"print({line!r}); print('[GUIScript/ERROR]: Runtime Error:')", {"forbidden_log_marker"}),
            ("invalid-spell-target", f"print({line!r}); print('[GUIScript/ERROR]: Unhandled target type: 2')", {"forbidden_log_marker"}),
        ]:
            path, data = harness.run_scenario(scenario, [sys.executable, "-c", code], root / name)
            assert kinds(data["failures"]) == expected_kinds, (name, data["failures"])
            assert data["status"] == ("failure" if expected_kinds else "success")
            assert json.loads(path.read_text(encoding="utf-8"))["checkpoints"] == data["checkpoints"]
            assert data["assertions"]["required_checkpoints"] == ["pool.after-cast"]

        for required in [["duplicate", "duplicate"], [" padded "], [False], "not-a-list"]:
            scenario_path.write_text(json.dumps(dict(scenario_data, required_checkpoints=required)), encoding="utf-8")
            try:
                harness.load_scenario(scenario_path)
            except ValueError as error:
                assert "required_checkpoints" in str(error)
            else:
                raise AssertionError(f"invalid required checkpoints accepted: {required}")

    for scenario_id in (
        "chargen-three-classes", "psion-six-disciplines-chargen",
        "psion-gameplay-progression", "cipher-gameplay-progression",
        "sorcerer-monk-gameplay-progression", "sorcerer-monk-tob-hla",
    ):
        scenario = harness.load_scenario(SCENARIOS / (scenario_id + ".json"))
        assert scenario["id"] == scenario_id
        assert scenario["required_checkpoints"]
        assert scenario["prerequisites"] and scenario["instructions"]
        assert "synthetic" not in scenario["supported_game_types"]
        _, failures = harness.parse_checkpoints("", scenario["required_checkpoints"])
        assert len(failures) == len(scenario["required_checkpoints"])
    tob = harness.load_scenario(SCENARIOS / "sorcerer-monk-tob-hla.json")
    assert "bgee" not in tob["supported_game_types"]
    validate_campaign_inventory(harness)
    print("Structured acceptance checkpoint validation passed (synthetic harness coverage only)")


if __name__ == "__main__":
    main()
