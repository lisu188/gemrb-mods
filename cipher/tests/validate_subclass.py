#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "common/guiscripts"
CIPHER = ROOT / "cipher"
sys.path.insert(0, str(COMMON))


def main():
    effects = {1: [], 2: []}
    known = {1: [], 2: []}
    memorized = {1: [], 2: []}
    focus = {1: 50, 2: 50}
    applied = []

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

    cipher = types.ModuleType("Cipher")
    cipher.is_cipher = lambda actor: actor in (1, 2)
    cipher.current_focus = lambda actor: focus[actor]

    def set_focus(actor, amount):
        focus[actor] = max(0, int(amount))
        return focus[actor]

    cipher.set_focus = set_focus

    old_gemrb = sys.modules.get("GemRB")
    old_cipher = sys.modules.get("Cipher")
    sys.modules["GemRB"] = gemrb
    sys.modules["Cipher"] = cipher
    for name in ("PersistentState", "InnateCharges", "Selectors", "Transactions"):
        sys.modules.pop(name, None)
    try:
        spec = importlib.util.spec_from_file_location("cipher_subclass_test", CIPHER / "guiscripts/CipherSubclass.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.subclass_id(1) == 0
        assert module.modify_focus_gain(1, 5, "weapon") == 5
        assert module.modify_focus_cap(1, 100) == 100
        assert module.modify_power_cost(1, "CI1WHSP", 10) == 10
        assert module.can_choose(1)

        assert module.begin_manifest(1, module.SOUL_BLADE_CHOICE)
        assert module.subclass_id(1) == 0
        assert module.begin_manifest(1, module.SOUL_BLADE_CHOICE)
        assert module.subclass_id(1) == module.SOUL_BLADE_ID
        assert module.subclass(1) == "SOUL_BLADE"
        assert module.subclass_id(2) == 0
        assert module.SOUL_BLADE_ACTION in known[1]
        assert any(actor == 1 and resource == module.SOUL_BLADE_PASSIVE for actor, resource, _ in applied)
        assert not module.can_choose(1)

        before = focus[1]
        assert module.begin_manifest(1, module.SOUL_BLADE_ACTION)
        assert focus[1] == before
        assert module.begin_manifest(1, module.SOUL_BLADE_ACTION)
        assert focus[1] == before - module.SOUL_BLADE_COST

        focus[1] = module.SOUL_BLADE_COST - 5
        assert not module.begin_manifest(1, module.SOUL_BLADE_ACTION)
        assert focus[1] == module.SOUL_BLADE_COST - 5

        filtered = module.filter_spellinfo(1, [module.SELECTOR_RESOURCE, module.SOUL_BLADE_CHOICE, "OTHER"])
        assert filtered == ["OTHER"]

        assert module.begin_manifest(2, module.SOUL_BLADE_CHOICE)
        assert module.begin_manifest(2, module.SOUL_BLADE_CHOICE)
        assert module.subclass_id(2) == module.SOUL_BLADE_ID
        assert module.subclass_id(1) == module.SOUL_BLADE_ID

        print("Cipher subclass persistence validation passed")
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_cipher is None:
            sys.modules.pop("Cipher", None)
        else:
            sys.modules["Cipher"] = old_cipher


if __name__ == "__main__":
    main()
