#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "common" / "guiscripts"
sys.path.insert(0, str(COMMON))

EXPECTED = {
    "ARTISTE": (1, "PXCART", "ECTOPLASMIC_CRAFT", 3),
    "FRIENDLY": (2, "PXCFRND", "INFLUENCE", 3),
    "OBSERVANT": (3, "PXCOBS", "AWARENESS", 3),
    "SAGE": (4, "PXCSAGE", "PSIONIC_KNOWLEDGE", 3),
    "SINGLE_MINDED": (5, "PXCSING", "CONCENTRATION", 3),
}


def lines(name):
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name):
    return lines(name)[2].split()


def rows(name):
    return [line.split() for line in lines(name)[3:] if line.strip()]


def fake_table(name):
    columns = header(name)
    data = rows(name)

    class Table:
        names = [row[0] for row in data]
        values = {row[0]: dict(zip(columns, row[1:])) for row in data}

        def GetValue(self, row, column):
            return self.values[str(row)][column]

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

    return Table()


def static_checks():
    personality_rows = rows("pscryst.2da")
    parsed = {
        row[0]: (int(row[1]), row[2], row[4], int(row[5]))
        for row in personality_rows
    }
    assert parsed == EXPECTED, parsed
    assert len({value[0] for value in EXPECTED.values()}) == len(EXPECTED)
    assert all(len(value[1]) <= 8 for value in EXPECTED.values())

    builder = (ROOT / "lib" / "psicrystal.tpa").read_text(encoding="utf-8")
    assert "ps_resref = ~PXCRYST~" in builder
    assert "opcode = 214" in builder
    assert "resource = ~PSCRYST~" in builder
    for _, resref, _, _ in EXPECTED.values():
        assert f"ps_resref = ~{resref}~" in builder

    runtime = (ROOT / "guiscripts" / "Psionics.py").read_text(encoding="utf-8")
    for fragment in (
        'PSICRYSTAL_SELECTOR_RESOURCE = "PXCRYST"',
        "PSICRYSTAL_PERSONALITY_MARKER = 0x50534350",
        'PSICRYSTAL_PERSONALITY_RESOURCE = "PSCRPERS"',
        "def psicrystal_choice_info(resref):",
        "def psicrystal_personality(actor):",
        "def available_psicrystal_choices(actor):",
        "def _ensure_psicrystal_selector_known(actor):",
        "def _sync_psicrystal_selector(actor):",
        "def _choose_psicrystal(actor, resref):",
        "def psicrystal_skill_bonus(actor, skill):",
        '("PSICRYSTAL", key)',
    ):
        assert fragment in runtime, fragment

    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    powers = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    assert "pscryst.2da" in setup
    assert "psicrystal.tpa" in powers
    for filename in (
        "clabpsee.2da", "clabpsha.2da", "clabpkin.2da",
        "clabpego.2da", "clabpnom.2da", "clabptel.2da",
    ):
        assert "GA_PXCRYST" not in (ROOT / "tables" / filename).read_text(encoding="utf-8")


def dynamic_checks():
    gemrb = types.ModuleType("GemRB")
    gui = types.ModuleType("GUICommon")
    ie_spells = types.ModuleType("ie_spells")
    ie_spells.LS_MEMO = 8

    tables = {
        "pscryst": fake_table("pscryst.2da"),
        "psionskills": fake_table("psionskills.2da"),
    }
    class_rows = {1: "PSION_SHAPER", 2: "PSION_EGOIST", 3: "FIGHTER"}
    stats = {
        (1, 34): 5,
        (1, 38): 18,
        (1, 39): 14,
        (1, 41): 14,
        (2, 34): 5,
        (2, 38): 18,
        (2, 39): 14,
        (2, 41): 14,
    }
    effects = {1: [], 2: [], 3: []}
    known = {1: [], 2: [], 3: []}
    memorized = {1: [], 2: [], 3: []}

    gui.GetClassRowName = lambda actor: class_rows.get(actor, "")
    gemrb.GetPlayerStat = lambda actor, stat, base=0: stats.get((actor, stat), 0)

    def load_table(name, *_):
        key = str(name).lower()
        if key not in tables:
            raise KeyError(key)
        return tables[key]

    gemrb.LoadTable = load_table
    gemrb.Log = lambda *_: None
    gemrb.DisplayString = lambda *_: None
    gemrb.Roll = lambda dice, sides, bonus: 10 + bonus
    gemrb.ApplySpell = lambda *_: None

    def get_effects(actor, opcode):
        return [
            {key: value for key, value in effect.items() if key != "Opcode"}
            for effect in effects.get(actor, [])
            if effect["Opcode"] == opcode
        ]

    def dispel_effect(actor, opcode, param2):
        effects[actor] = [
            effect for effect in effects.get(actor, [])
            if not (effect["Opcode"] == opcode and effect["Param2"] == param2)
        ]

    def apply_effect(
        actor,
        opcode,
        param1,
        param2,
        resource1="",
        resource2="",
        resource3="",
        source="",
        timing=9,
    ):
        effects.setdefault(actor, []).append({
            "Opcode": opcode,
            "Param1": param1,
            "Param2": param2,
            "Resource1": resource1,
            "Resource2": resource2,
            "Resource3": resource3,
            "Source": source,
            "Timing": timing,
        })

    gemrb.GetEffects = get_effects
    gemrb.DispelEffect = dispel_effect
    gemrb.ApplyEffect = apply_effect
    gemrb.GetKnownSpellsCount = lambda actor, spell_type, level: len(known[actor])
    gemrb.GetKnownSpell = lambda actor, spell_type, level, index: dict(known[actor][index])
    gemrb.GetMemorizedSpellsCount = lambda actor, spell_type, level, real: len(memorized[actor])
    gemrb.GetMemorizedSpell = lambda actor, spell_type, level, index: dict(memorized[actor][index])

    def learn_spell(actor, resref, flags=0, *args):
        key = str(resref).upper()
        if any(spell["SpellResRef"] == key for spell in known[actor]):
            return 1
        known[actor].append({"SpellResRef": key})
        if int(flags) & ie_spells.LS_MEMO:
            memorized[actor].append({"SpellResRef": key, "Flags": 1})
        return 0

    def remove_spell(actor, resref, *args):
        key = str(resref).upper()
        known[actor][:] = [spell for spell in known[actor] if spell["SpellResRef"] != key]
        memorized[actor][:] = [spell for spell in memorized[actor] if spell["SpellResRef"] != key]
        return True

    def unmemorize(actor, spell_type, level, index):
        memorized[actor].pop(index)
        return True

    def memorize(actor, spell_type, level, known_index, usable):
        memorized[actor].append({
            "SpellResRef": known[actor][known_index]["SpellResRef"],
            "Flags": 1 if usable else 0,
        })
        return True

    gemrb.LearnSpell = learn_spell
    gemrb.RemoveSpell = remove_spell
    gemrb.UnmemorizeSpell = unmemorize
    gemrb.MemorizeSpell = memorize

    old_modules = {name: sys.modules.get(name) for name in ("GemRB", "GUICommon", "ie_spells")}
    sys.modules["GemRB"] = gemrb
    sys.modules["GUICommon"] = gui
    sys.modules["ie_spells"] = ie_spells
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psicrystal_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        combinations = 0
        for class_row, discipline in module.PSION_CLASSES.items():
            for personality_id, resref, skill, bonus in EXPECTED.values():
                class_rows[4] = class_row
                effects[4] = []
                known[4] = []
                memorized[4] = []
                module.cancel_pending(4)
                for stat in (34, 36, 38, 39, 40, 41, 42):
                    stats[(4, stat)] = 5 if stat == 34 else 18
                access = module.skill_rule_info(skill)["access"]
                allowed = access in ("CORE", discipline)
                assert module.can_choose_psicrystal(4, resref) == allowed, (class_row, resref)
                assert (resref in module.available_psicrystal_choices(4)) == allowed
                assert (resref in module.filter_spellinfo(4, [resref])) == allowed
                assert module._ensure_psicrystal_selector_known(4)
                assert module.begin_manifest(4, resref) == allowed
                assert module.psicrystal_personality(4) == 0
                if allowed:
                    baseline = module.skill_check_total(4, skill, roll=10)
                    assert baseline is not None
                    assert module.begin_manifest(4, resref)
                    assert module.psicrystal_personality(4) == personality_id
                    assert module.skill_check_total(4, skill, roll=10) == baseline + bonus
                    effects[4] = [dict(effect) for effect in effects[4]]
                    assert module.psicrystal_personality(4) == personality_id
                    assert not module.can_choose_psicrystal(4, resref)
                    assert "PXCRYST" not in {spell["SpellResRef"] for spell in known[4]}
                else:
                    assert not module._choose_psicrystal(4, resref)
                    assert module.psicrystal_personality(4) == 0
                    assert "PXCRYST" in {spell["SpellResRef"] for spell in known[4]}
                combinations += 1
        assert combinations == 30

        effects[4] = []
        module.cancel_pending(4)
        class_rows[4] = "PSION_SHAPER"
        assert module.begin_manifest(4, "PXCART")
        class_rows[4] = "PSION_EGOIST"
        assert not module.begin_manifest(4, "PXCART")
        assert module.psicrystal_personality(4) == 0
        module.cancel_pending(4)
        class_rows.pop(4)

        assert module.psicrystal_personality(1) == 0
        assert set(module.available_psicrystal_choices(1)) == {
            "PXCART", "PXCSAGE", "PXCSING"
        }
        assert module.action_info(module.PSICRYSTAL_SELECTOR_RESOURCE)["kind"] == "psicrystal_selector"
        assert module._ensure_psicrystal_selector_known(1)
        assert module._ensure_psicrystal_selector_known(1)
        assert [spell["SpellResRef"] for spell in known[1]].count("PXCRYST") == 1

        assert module.begin_manifest(1, "PXCART")
        assert module.psicrystal_personality(1) == 0
        module.cancel_pending(1)
        assert module.psicrystal_personality(1) == 0
        assert module.begin_manifest(1, "PXCART")
        assert module.begin_manifest(1, "PXCART")
        assert module.psicrystal_personality(1) == 1
        assert module.psicrystal_personality_info(1)["personality"] == "ARTISTE"
        assert not module.available_psicrystal_choices(1)
        assert "PXCRYST" not in {spell["SpellResRef"] for spell in known[1]}
        assert module.psicrystal_skill_bonus(1, "ECTOPLASMIC_CRAFT") == 3
        assert module.psicrystal_skill_bonus(1, "CONCENTRATION") == 0
        assert module.skill_check_total(1, "ECTOPLASMIC_CRAFT", roll=10) == 17

        assert module._ensure_psicrystal_selector_known(2)
        assert module.begin_manifest(2, "PXCSING")
        assert module.begin_manifest(2, "PXCSING")
        assert module.psicrystal_personality(2) == 5
        assert module.psicrystal_personality(1) == 1
        assert module.skill_check_total(2, "CONCENTRATION", roll=10) == 15
        assert module.concentration_check(2, 15, roll=10)
        assert not module.can_choose_psicrystal(2, "PXCSAGE")

        state_effects = [
            effect for effect in effects[1]
            if effect["Param2"] == module.PSICRYSTAL_PERSONALITY_MARKER
        ]
        assert len(state_effects) == 1
        assert state_effects[0]["Param1"] == 1
        assert state_effects[0]["Resource1"] == module.PSICRYSTAL_PERSONALITY_RESOURCE
        assert not module._choose_psicrystal(1, "PXCART")
        state_effects = [
            effect for effect in effects[1]
            if effect["Param2"] == module.PSICRYSTAL_PERSONALITY_MARKER
        ]
        assert len(state_effects) == 1

        assert module.psicrystal_personality(3) == 0
        assert not module.available_psicrystal_choices(3)
    finally:
        for name, value in old_modules.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def main():
    static_checks()
    dynamic_checks()
    print("Psicrystal personality table, transaction, persistence, actor isolation, lazy selector migration, and skill bonus validation passed.")


if __name__ == "__main__":
    main()
