#!/usr/bin/env python3
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
CIPHER = ROOT / "cipher"


def read_2da(path):
    lines = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[2], {row[0]: row[1:] for row in lines[3:]}


def main():
    header, rows = read_2da(CIPHER / "tables" / "ciphersub.2da")
    assert header == ["ID", "CHOICE", "CAP_MOD", "COST_DELTA", "GAIN_UNITS", "PASSIVE", "WEAPON", "ENABLED"]
    assert rows["BASE"] == ["0", "*", "0", "0", "1", "*", "BASE", "1"]
    assert rows["SOUL_BLADE"] == ["1", "CISBLD", "10", "5", "2", "CISB1", "SOUL_BLADE", "1"]
    identifiers = [int(values[0]) for values in rows.values()]
    assert len(identifiers) == len(set(identifiers))
    assert identifiers[0] == 0

    pick_header, picks = read_2da(CIPHER / "tables" / "cisubpk.2da")
    assert pick_header == ["ResRef", "Type"]
    enabled_choices = {
        values[1]
        for key, values in rows.items()
        if int(values[-1]) and int(values[0]) != 0
    }
    assert {values[0] for values in picks.values()} == enabled_choices

    runtime_source = (CIPHER / "guiscripts" / "Cipher.py").read_text(encoding="utf-8")
    assert "SUBCLASS_MIRROR_STAT = 164" in runtime_source
    assert "FOCUS_STAT = 165" in runtime_source
    assert "PersistentState.read(" in runtime_source
    assert "PersistentState.write(" in runtime_source
    assert "def focus_cap(actor, base_cap):" in runtime_source
    assert "def power_cost(actor, info, base_cost=None):" in runtime_source
    assert "def focus_gain_units(actor, source_kind, base_units=1):" in runtime_source
    assert "def passive_resource(actor):" in runtime_source
    assert "def weapon_policy(actor):" in runtime_source
    assert runtime_source.count("def begin_manifest(") == 1
    handlers = [path.name for path in (CIPHER / "guiscripts").glob("*.py") if path.name.startswith("Cipher")]
    assert handlers == ["Cipher.py"], handlers

    focus_source = (CIPHER / "lib" / "focus.tpa").read_text(encoding="utf-8")
    assert "CIPHER_SOUL_BLADE 164 1 1" in focus_source
    assert focus_source.count("STR_VAR resource = ~CIFSTEP~") >= 2
    assert "ci_soul_blade_splprot" in focus_source

    subclass_source = (CIPHER / "lib" / "subclass-soul-blade.tpa").read_text(encoding="utf-8")
    for resref in ("CISUBCL", "CISBLD", "CISB0", "CISB1"):
        assert resref in subclass_source
    assert "parameter2 = 8" in subclass_source

    spec = importlib.util.spec_from_file_location("cipher_validation", CIPHER / "tests" / "validate.py")
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)
    runtime, states, _, known, _, effects = validation.load_runtime()

    before = runtime.known_power_refs(1)
    assert runtime.subclass_id(1) == 0
    assert runtime.subclass_id(2) == 0
    assert runtime.begin_manifest(1, "CISBLD")
    assert runtime.subclass_id(1) == 0
    assert runtime.begin_manifest(1, "CISBLD")
    assert runtime.subclass_id(1) == 1
    assert runtime.subclass_id(2) == 0
    assert runtime.known_power_refs(1) == before
    assert runtime.maximum_focus(1) == 80
    assert runtime.maximum_focus(2) == 70
    assert runtime.power_cost(1, runtime.power_info("CI2MBND")) == 20
    assert runtime.power_cost(2, runtime.power_info("CI2MBND")) == 15
    assert runtime.focus_gain_units(1, "weapon") == 2
    assert runtime.focus_gain_units(2, "weapon") == 1
    assert states[1][164] == 1 and states[2][164] == 0

    states[1][164] = 0
    runtime._sync_subclass_passive(1)
    assert states[1][164] == 1
    assert runtime.subclass_id(1) == 1
    assert len([
        effect for effect in effects[1]
        if effect["Param2"] == runtime.SUBCLASS_STATE_MARKER
        and effect["Resource1"] == runtime.SUBCLASS_STATE_RESOURCE
    ]) == 1
    assert "CISUBCL" not in {spell["SpellResRef"] for spell in known[1]}

    print("Cipher subclass registry, persistence, policy hooks, Soul Blade routing and actor isolation validated")


if __name__ == "__main__":
    main()
