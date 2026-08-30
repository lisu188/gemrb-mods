#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/enemy_psion_encounter.json"


def load_controller(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "guiscripts/PsionAI.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["schema"] == 1
    actor = int(fixture["actor"])
    target = int(fixture["target"])
    discipline = str(fixture["discipline"])
    state = {"pool": int(fixture["starting_pp"]), "focus": False, "discipline": discipline}
    applied = []
    powers = {
        "PS1ERAY": {"resref": "PS1ERAY", "cost": 1, "level": 1, "selector": False},
        "PS3EBLT": {"resref": "PS3EBLT", "cost": 5, "level": 3, "selector": False},
        "PS1IARM": {"resref": "PS1IARM", "cost": 1, "level": 1, "selector": False},
        "PS1BRST": {"resref": "PS1BRST", "cost": 1, "level": 1, "selector": False},
    }

    gemrb = types.ModuleType("GemRB")
    gemrb.ApplySpell = lambda victim, resource, caster=None: applied.append((victim, resource, caster))
    gemrb.Log = lambda *args: None

    psionics = types.ModuleType("Psionics")
    psionics.is_psion = lambda who: who == actor
    psionics.discipline = lambda who: state["discipline"] if who == actor else ""

    def ensure_pool(who, refill=False):
        if refill:
            state["pool"] = int(fixture["starting_pp"])
        return state["pool"]

    def ensure_focus(who, refill=False):
        if refill:
            state["focus"] = True
        return state["focus"]

    psionics.ensure_pool = ensure_pool
    psionics.ensure_focus = ensure_focus
    psionics.power_info = lambda resref: powers.get(str(resref).upper())
    psionics.can_manifest = lambda who, resref: who == actor and resref in powers and powers[resref]["cost"] <= state["pool"]
    psionics._dc_canonical_resref = lambda resref: str(resref).upper()
    psionics._dc_modifier = lambda who: int(fixture["intelligence_modifier"])
    psionics._dc_variant_resref = lambda resref, modifier: resref + str(modifier)
    psionics._dc_resource_exists = lambda resref: resref.endswith(str(fixture["intelligence_modifier"]))

    def write_pool(who, value):
        state["pool"] = max(0, int(value))
        return state["pool"]

    psionics._write_pool_state = write_pool

    old_gemrb = sys.modules.get("GemRB")
    old_psionics = sys.modules.get("Psionics")
    sys.modules["GemRB"] = gemrb
    sys.modules["Psionics"] = psionics
    try:
        module = load_controller("enemy_psion_test")

        assert module.initialize(actor, True)
        assert state["pool"] == fixture["starting_pp"]
        assert state["focus"] is True
        for role, expected in fixture["roles"].items():
            assert module.choose_power(actor, role) == expected

        manifestation = fixture["manifestation"]
        power = manifestation["power"]
        assert module.exact_dc_resource(actor, power) == manifestation["expected_dc_resource"]
        assert module.manifest(actor, power, target)
        assert applied == [(target, manifestation["expected_dc_resource"], actor)]
        assert state["pool"] == manifestation["expected_remaining_pp"]

        saved_state = dict(state)
        reloaded = load_controller("enemy_psion_reload_test")
        assert reloaded.current_pp(actor) == fixture["save_reload"]["expected_remaining_pp"]
        assert state["focus"] is fixture["save_reload"]["expected_focus"]
        assert psionics.discipline(actor) == fixture["save_reload"]["expected_discipline"]
        assert state == saved_state

        state["pool"] = 0
        assert not reloaded.manifest(actor, power, target)
        assert applied == [(target, manifestation["expected_dc_resource"], actor)]
        assert state["pool"] == 0
        assert reloaded.choose_power(actor, "offense") == ""
        assert not reloaded.initialize(9999, True)

        print("Enemy Psion encounter fixture validation passed")
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_psionics is None:
            sys.modules.pop("Psionics", None)
        else:
            sys.modules["Psionics"] = old_psionics


if __name__ == "__main__":
    main()
