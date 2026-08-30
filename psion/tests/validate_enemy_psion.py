#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]


def main():
    actor = 2001
    target = 3001
    state = {"pool": 20, "focus": False}
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
    psionics.discipline = lambda who: "SEER" if who == actor else ""

    def ensure_pool(who, refill=False):
        if refill:
            state["pool"] = 20
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
    psionics._dc_modifier = lambda who: 7
    psionics._dc_variant_resref = lambda resref, modifier: resref + str(modifier)
    psionics._dc_resource_exists = lambda resref: resref.endswith("7")

    def write_pool(who, value):
        state["pool"] = max(0, int(value))
        return state["pool"]

    psionics._write_pool_state = write_pool

    old_gemrb = sys.modules.get("GemRB")
    old_psionics = sys.modules.get("Psionics")
    sys.modules["GemRB"] = gemrb
    sys.modules["Psionics"] = psionics
    try:
        spec = importlib.util.spec_from_file_location("enemy_psion_test", ROOT / "guiscripts/PsionAI.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.initialize(actor, True)
        assert state == {"pool": 20, "focus": True}
        assert module.choose_power(actor, "offense") == "PS3EBLT"
        assert module.choose_power(actor, "defense") == "PS1IARM"
        assert module.choose_power(actor, "mobility") == "PS1BRST"
        assert module.exact_dc_resource(actor, "PS3EBLT") == "PS3EBLT7"

        assert module.manifest(actor, "PS3EBLT", target)
        assert applied == [(target, "PS3EBLT7", actor)]
        assert state["pool"] == 15

        state["pool"] = 0
        assert not module.manifest(actor, "PS3EBLT", target)
        assert applied == [(target, "PS3EBLT7", actor)]
        assert state["pool"] == 0
        assert module.choose_power(actor, "offense") == ""
        assert not module.initialize(9999, True)

        print("Enemy Psion runtime validation passed")
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
