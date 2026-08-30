#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "common/guiscripts"
PSION = ROOT / "psion"
sys.path.insert(0, str(COMMON))


def main():
    effects = {1: [], 2: []}
    known = {1: [], 2: []}
    memorized = {1: [], 2: []}
    applied = []
    levels = {1: 1, 2: 15}

    gemrb = types.ModuleType("GemRB")
    gemrb.GetEffects = lambda actor, opcode: [dict(row) for row in effects[actor] if row["Opcode"] == opcode]

    def dispel(actor, opcode, marker):
        effects[actor][:] = [row for row in effects[actor] if not (row["Opcode"] == opcode and row["Param2"] == marker)]

    def apply_effect(actor, opcode, p1, p2, r1="", r2="", r3="", source="", *args):
        effects[actor].append({"Opcode": opcode, "Param1": p1, "Param2": p2, "Resource1": r1})

    def learn(actor, resref, flags=0, *args):
        key = str(resref).upper()
        if key not in known[actor]:
            known[actor].append(key)
            if int(flags) & 8:
                memorized[actor].append({"SpellResRef": key, "Flags": 1})
        return 0

    gemrb.DispelEffect = dispel
    gemrb.ApplyEffect = apply_effect
    gemrb.GetKnownSpellsCount = lambda actor, *args: len(known[actor])
    gemrb.GetKnownSpell = lambda actor, st, sl, index: {"SpellResRef": known[actor][index]}
    gemrb.GetMemorizedSpellsCount = lambda actor, *args: len(memorized[actor])
    gemrb.GetMemorizedSpell = lambda actor, st, sl, index: dict(memorized[actor][index])
    gemrb.LearnSpell = learn
    gemrb.UnmemorizeSpell = lambda actor, st, sl, index: memorized[actor].pop(index) is not None

    def memorize(actor, st, sl, known_index, usable):
        memorized[actor].append({"SpellResRef": known[actor][known_index], "Flags": 1 if usable else 0})
        return True

    gemrb.MemorizeSpell = memorize
    gemrb.ApplySpell = lambda actor, resource, caster=None: applied.append((actor, resource, caster))
    gemrb.Log = lambda *args: None
    gemrb.GetSpelldata = lambda actor: []

    psionics = types.ModuleType("Psionics")
    psionics.is_psion = lambda actor: actor in (1, 2)
    psionics.manifester_level = lambda actor: levels[actor]

    ie_spells = types.ModuleType("ie_spells")
    ie_spells.LS_MEMO = 8

    old_gemrb = sys.modules.get("GemRB")
    old_psionics = sys.modules.get("Psionics")
    old_ie_spells = sys.modules.get("ie_spells")
    sys.modules["GemRB"] = gemrb
    sys.modules["Psionics"] = psionics
    sys.modules["ie_spells"] = ie_spells
    for name in ("PersistentState", "InnateCharges", "Selectors", "Transactions"):
        sys.modules.pop(name, None)
    try:
        spec = importlib.util.spec_from_file_location("psicrystal_test", PSION / "guiscripts/Psicrystal.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.can_choose(1)
        assert module.available_choices(1) == ["PXCRHERO", "PXCRNIMB", "PXCROBSV", "PXCRRESO"]
        assert module.begin_manifest(1, "PXCRHERO")
        assert module.personality_id(1) == 0
        assert module.begin_manifest(1, "PXCRHERO")
        assert module.personality_id(1) == 1
        assert module.personality(1) == "HEROIC"
        assert module.SUMMON_RESOURCE in known[1]
        assert any(resource == "PXCRP11" for _, resource, _ in applied)

        summon = next(row for row in memorized[1] if row["SpellResRef"] == module.SUMMON_RESOURCE)
        summon["Flags"] = 0
        assert module.refresh_innate_charges(1) == 0
        assert next(row for row in memorized[1] if row["SpellResRef"] == module.SUMMON_RESOURCE)["Flags"] == 0
        module.restore_party()
        assert next(row for row in memorized[1] if row["SpellResRef"] == module.SUMMON_RESOURCE)["Flags"] == 1
        assert module.personality_id(1) == 1

        assert module.begin_manifest(2, "PXCRRESO")
        assert module.begin_manifest(2, "PXCRRESO")
        assert module.personality_id(2) == 4
        assert module.personality_id(1) == 1
        assert any(actor == 2 and resource == "PXCRP43" for actor, resource, _ in applied)

        levels[1] = 8
        module.refresh_innate_charges(1)
        assert any(actor == 1 and resource == "PXCRP12" for actor, resource, _ in applied)

        print("Psicrystal persistence validation passed")
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_psionics is None:
            sys.modules.pop("Psionics", None)
        else:
            sys.modules["Psionics"] = old_psionics
        if old_ie_spells is None:
            sys.modules.pop("ie_spells", None)
        else:
            sys.modules["ie_spells"] = old_ie_spells


if __name__ == "__main__":
    main()
