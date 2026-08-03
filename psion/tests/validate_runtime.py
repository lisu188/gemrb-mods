#!/usr/bin/env python3
"""Fake-GemRB PP, persistence, focus, feat, selector, and charge checks."""

from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]


def lines(name: str) -> list[str]:
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name: str) -> list[str]:
    return lines(name)[2].split()


def rows(name: str) -> list[list[str]]:
    return [line.split() for line in lines(name)[3:] if line.strip()]


def fake_table(name: str):
    columns, data = header(name), rows(name)

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


def main() -> None:
    gemrb = types.ModuleType("GemRB")
    gui = types.ModuleType("GUICommon")
    stats = {(1, 38): 18, (1, 39): 14, (1, 34): 20, (1, 239): 0}
    effects = {1: []}
    tables = {
        name: fake_table(name + ".2da")
        for name in ("psionpool", "psionpowers", "psionaugment", "psionfeatpick")
    }
    known_innates = [
        {"SpellResRef": "PS1ERAY"},
        {"SpellResRef": "PS1VIGR"},
        {"SpellResRef": "PXCNTR"},
        {"SpellResRef": "PXFSEL"},
        {"SpellResRef": "SPCL900"},
    ]
    memorized_innates = [
        {"SpellResRef": "PS1ERAY", "Flags": 0},
        {"SpellResRef": "PS1VIGR", "Flags": 1},
        {"SpellResRef": "PXCNTR", "Flags": 0},
        {"SpellResRef": "PXFSEL", "Flags": 0},
        {"SpellResRef": "SPCL900", "Flags": 0},
    ]
    raw_spellinfo = ["PSMT03", "PSNOTMOD"]
    applied_spells = []

    gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""
    gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)
    gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    gemrb.LoadTable = lambda name, *_: tables[name.lower()]
    gemrb.DisplayString = lambda *_: None
    gemrb.Log = lambda *_: None
    gemrb.GetSpelldata = lambda actor: list(raw_spellinfo)
    gemrb.ApplySpell = lambda actor, resref, *_: applied_spells.append((actor, resref))
    gemrb.GetKnownSpellsCount = lambda actor, spell_type, level: len(known_innates)
    gemrb.GetKnownSpell = lambda actor, spell_type, level, index: dict(known_innates[index])
    gemrb.GetMemorizedSpellsCount = lambda actor, spell_type, level, real: len(memorized_innates)
    gemrb.GetMemorizedSpell = lambda actor, spell_type, level, index: dict(memorized_innates[index])

    def get_effects(actor, opcode):
        return [
            {key: value for key, value in effect.items() if key != "Opcode"}
            for effect in effects.get(actor, [])
            if effect["Opcode"] == opcode
        ]

    def dispel_effect(actor, opcode, param2):
        effects[actor] = [
            effect
            for effect in effects.get(actor, [])
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
        effects.setdefault(actor, []).append(
            {
                "Opcode": opcode,
                "Param1": param1,
                "Param2": param2,
                "Resource1": resource1,
                "Resource2": resource2,
                "Resource3": resource3,
                "Source": source,
                "Timing": timing,
            }
        )

    gemrb.GetEffects = get_effects
    gemrb.DispelEffect = dispel_effect
    gemrb.ApplyEffect = apply_effect

    def unmemorize(actor, spell_type, level, index):
        memorized_innates.pop(index)
        return True

    def memorize(actor, spell_type, level, known_index, usable):
        memorized_innates.append(
            {
                "SpellResRef": known_innates[known_index]["SpellResRef"],
                "Flags": 1 if usable else 0,
            }
        )
        return True

    gemrb.UnmemorizeSpell = unmemorize
    gemrb.MemorizeSpell = memorize

    old_gemrb, old_gui = sys.modules.get("GemRB"), sys.modules.get("GUICommon")
    sys.modules["GemRB"], sys.modules["GUICommon"] = gemrb, gui
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psion_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        initial_cap = module.maximum_pool(1)
        assert initial_cap == 383
        assert module.ensure_pool(1) == initial_cap
        assert stats[(1, 239)] == module.POOL_STATE_SIGNATURE | initial_cap
        persistent = get_effects(1, module.STATE_EFFECT_OPCODE)
        pool = [effect for effect in persistent if effect["Param2"] == module.POOL_EFFECT_MARKER]
        assert len(pool) == 1 and pool[0]["Param1"] == initial_cap
        stats[(1, 239)] = 0
        assert module.ensure_pool(1) == initial_cap
        assert module._write_pool_state(1, 0) == 0
        stats[(1, 239)] = 0
        assert module.ensure_pool(1) == 0
        assert module.ensure_pool(1, True) == initial_cap

        assert module.ensure_focus(1)
        focus = [
            effect for effect in get_effects(1, module.STATE_EFFECT_OPCODE)
            if effect["Param2"] == module.FOCUS_EFFECT_MARKER
        ]
        assert len(focus) == 1 and focus[0]["Param1"] == 1
        assert module.expend_focus(1)
        assert not module.is_focused(1)
        assert applied_spells[-1] == (1, module.SPEED_OFF_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.is_focused(1)

        # Class bonus-feat credits unlock exactly at the SRD Psion thresholds.
        for level, slots in ((1, 1), (4, 1), (5, 2), (9, 2), (10, 3), (15, 4), (20, 5)):
            stats[(1, 34)] = level
            assert module.bonus_feat_slots(1) == slots
        stats[(1, 34)] = 20
        assert module.bonus_feats_remaining(1) == 5
        assert module.action_info(module.FEAT_SELECTOR_RESOURCE)["kind"] == "feat_selector"
        assert module.begin_manifest(1, module.FEAT_SELECTOR_RESOURCE)

        # Canceling/opening the selector cannot destroy an earned credit. While
        # credit remains, charge refresh restores the selector just like Center.
        assert module.refresh_innate_charges(1) == 3
        states = {spell["SpellResRef"]: spell["Flags"] for spell in memorized_innates}
        assert states["PS1ERAY"] == 1
        assert states["PXCNTR"] == 1
        assert states["PXFSEL"] == 1
        for spell in memorized_innates:
            if spell["SpellResRef"] == "PXFSEL":
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 1
        assert next(spell for spell in memorized_innates if spell["SpellResRef"] == "PXFSEL")["Flags"] == 1

        assert module.can_select_feat(1, "PXFTALT")
        assert module.can_select_feat(1, "PXFBODY")
        assert module.can_select_feat(1, "PXFSPD")
        stats[(1, 39)] = 12
        assert not module.can_select_feat(1, "PXFSPD")
        assert module.filter_spellinfo(1, ["SPWI112", "PXFTALT", "PXFSPD"]) == ["SPWI112", "PXFTALT"]
        stats[(1, 39)] = 14

        module.ensure_pool(1, True)
        assert module.begin_manifest(1, "PXFTALT")
        assert module.feat_rank(1, "PXFTALT") == 0
        assert module.begin_manifest(1, "PXFTALT")
        assert module.feat_rank(1, "PXFTALT") == 1
        assert module.maximum_pool(1) == initial_cap + 2
        assert module.ensure_pool(1) == initial_cap + 2
        assert module.bonus_feats_remaining(1) == 4

        assert module.begin_manifest(1, "PXFTALT")
        assert module.begin_manifest(1, "PXFTALT")
        assert module.feat_rank(1, "PXFTALT") == 2
        assert module.psionic_talent_bonus(1) == 5
        assert module.maximum_pool(1) == initial_cap + 5
        assert module.ensure_pool(1) == initial_cap + 5
        assert module.bonus_feats_remaining(1) == 3

        assert module.begin_manifest(1, "PXFBODY")
        assert module.begin_manifest(1, "PXFBODY")
        assert module.feat_rank(1, "PXFBODY") == 1
        assert module.psionic_feat_count(1) == 3
        assert [effect["Param1"] for effect in get_effects(1, "MaximumHPModifier")] == [6]
        assert [effect["Param1"] for effect in get_effects(1, "CurrentHPModifier")] == [6]
        assert not module.can_select_feat(1, "PXFBODY")

        assert module.begin_manifest(1, "PXFSPD")
        assert module.begin_manifest(1, "PXFSPD")
        assert module.feat_rank(1, "PXFSPD") == 1
        assert applied_spells[-1] == (1, module.SPEED_ON_RESOURCE)
        assert [effect["Param1"] for effect in get_effects(1, "MaximumHPModifier")] == [6, 2]
        assert module.expend_focus(1)
        assert applied_spells[-1] == (1, module.SPEED_OFF_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert applied_spells[-1] == (1, module.SPEED_ON_RESOURCE)
        assert not module.can_select_feat(1, "PXFSPD")

        before_pp = module.ensure_pool(1)
        before_cap = module.maximum_pool(1)
        assert module.begin_manifest(1, "PXFTALT")
        assert module.begin_manifest(1, "PXFTALT")
        assert module.feat_rank(1, "PXFTALT") == 3
        assert module.maximum_pool(1) == before_cap + 4
        assert module.ensure_pool(1) == before_pp + 4
        assert [effect["Param1"] for effect in get_effects(1, "MaximumHPModifier")] == [6, 2, 2]
        assert module.psionic_feat_count(1) == 5
        assert module.bonus_feats_remaining(1) == 0
        assert not module.can_select_feat(1, "PXFTALT")
        assert not module.begin_manifest(1, module.FEAT_SELECTOR_RESOURCE)
        assert module.available_feat_choices(1) == []

        # Once all five credits are spent, a depleted selector is no longer
        # recharged and therefore disappears until a future implementation adds
        # another legal feat source.
        for spell in memorized_innates:
            if spell["SpellResRef"] == "PXFSEL":
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 0
        assert next(spell for spell in memorized_innates if spell["SpellResRef"] == "PXFSEL")["Flags"] == 0

        # Retain the original low-level affordability regression at level 3.
        stats[(1, 34)] = 3
        for parent in ("PS1ERAY", "PS1MTHR", "PS1VIGR", "PS2AAFF"):
            assert module.power_info(parent)["selector"]
            assert module.can_manifest(1, parent)
        assert module.power_info("PSAADEX")["cost"] == 3
        mixed = ["SPWI112", "PSRF01", "PSRF04", "PSAADEX"]
        assert module.filter_spellinfo(1, mixed) == ["SPWI112", "PSRF01", "PSAADEX"]

        class CollisionSpellbook:
            def __init__(self):
                self.memorized_calls = 0

            def GetSpellinfoSpells(self, actor, book_type):
                raise AssertionError("type-255 resolution must use raw spellinfo")

            def GetUsableMemorizedSpells(self, actor, book_type):
                self.memorized_calls += 1
                return [
                    {"SpellIndex": 4000, "SpellResRef": "PS1VIGR"},
                    {"SpellIndex": 4001, "SpellResRef": "PXCNTR"},
                ]

        collision = CollisionSpellbook()
        raw_spellinfo[:] = ["PSMT03", "PSNOTMOD"]
        entry = module.resolve_power_entry(collision, 1, 255000)
        assert entry == {"SpellIndex": 255000, "SpellResRef": "PSMT03"}
        assert module.resolve_power_entry(collision, 1, 255001) is None
        ordinary = module.resolve_power_entry(collision, 1, 4000)
        assert ordinary["SpellResRef"] == "PS1VIGR"
        center = module.resolve_power_entry(collision, 1, 4001)
        assert center["SpellResRef"] == "PXCNTR"

        module.ensure_pool(1, True)
        selected = module.resolve_power_entry(collision, 1, 255000)
        assert module.begin_manifest(1, selected["SpellResRef"])
        module._write_pool_state(1, 0)
        confirmed = module.resolve_power_entry(collision, 1, 255000)
        assert not module.begin_manifest(1, confirmed["SpellResRef"])
        module.ensure_pool(1, True)

        # Reusable ordinary powers and Center Mind remain charge-backed. The
        # exhausted bonus-feat selector and unrelated innate are untouched.
        for spell in memorized_innates:
            if spell["SpellResRef"] in ("PS1ERAY", "PXCNTR"):
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 2
        states = {spell["SpellResRef"]: spell["Flags"] for spell in memorized_innates}
        assert states["PS1ERAY"] == 1
        assert states["PS1VIGR"] == 1
        assert states["PXCNTR"] == 1
        assert states["PXFSEL"] == 0
        assert states["SPCL900"] == 0
        assert module.refresh_innate_charges(2) == 0
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_gui is None:
            sys.modules.pop("GUICommon", None)
        else:
            sys.modules["GUICommon"] = old_gui

    print("Psion fake-GemRB PP, focus, feat-credit, selector, and persistence validation passed.")


if __name__ == "__main__":
    main()
