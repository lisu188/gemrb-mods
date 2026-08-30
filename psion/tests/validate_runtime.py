#!/usr/bin/env python3
"""Fake-GemRB PP, skill, focus, feat, selector, and persistence checks."""

from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "common" / "guiscripts"
sys.path.insert(0, str(COMMON))


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
    ie_spells = types.ModuleType("ie_spells")
    ie_spells.LS_MEMO = 8

    stats = {
        (1, 38): 18,
        (1, 39): 14,
        (1, 41): 14,
        (1, 34): 20,
        (1, 239): 0,
    }
    base_stats = dict(stats)
    effects = {1: []}
    tables = {
        name: fake_table(name + ".2da")
        for name in (
            "psionpool",
            "psionpowers",
            "psionaugment",
            "psionfeatpick",
            "psionskills",
            "psskill",
        )
    }
    known_innates = [
        {"SpellResRef": "PS1ERAY"},
        {"SpellResRef": "PS1VIGR"},
        {"SpellResRef": "PXCNTR"},
        {"SpellResRef": "PXFSEL"},
        {"SpellResRef": "PXSKILL"},
        {"SpellResRef": "SPCL900"},
    ]
    memorized_innates = [
        {"SpellResRef": "PS1ERAY", "Flags": 0},
        {"SpellResRef": "PS1VIGR", "Flags": 1},
        {"SpellResRef": "PXCNTR", "Flags": 0},
        {"SpellResRef": "PXFSEL", "Flags": 0},
        {"SpellResRef": "PXSKILL", "Flags": 1},
        {"SpellResRef": "SPCL900", "Flags": 0},
    ]
    raw_spellinfo = ["PSMT03", "PSNOTMOD"]
    applied_spells = []
    roll_value = {"value": 20}

    gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""

    def get_player_stat(actor, stat, base=0):
        source = base_stats if base else stats
        return source.get((actor, stat), 0)

    gemrb.GetPlayerStat = get_player_stat
    gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    gemrb.LoadTable = lambda name, *_: tables[name.lower()]
    gemrb.DisplayString = lambda *_: None
    gemrb.Log = lambda *_: None
    gemrb.Roll = lambda dice, sides, bonus: roll_value["value"] + bonus
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

    def remove_spell(actor, resref, *args):
        key = str(resref).upper()
        old_known = len(known_innates)
        known_innates[:] = [
            spell for spell in known_innates
            if str(spell["SpellResRef"]).upper() != key
        ]
        memorized_innates[:] = [
            spell for spell in memorized_innates
            if str(spell["SpellResRef"]).upper() != key
        ]
        return len(known_innates) != old_known

    def learn_spell(actor, resref, flags=0, *args):
        key = str(resref).upper()
        if any(str(spell["SpellResRef"]).upper() == key for spell in known_innates):
            return 1
        known_innates.append({"SpellResRef": key})
        if int(flags) & ie_spells.LS_MEMO:
            memorized_innates.append({"SpellResRef": key, "Flags": 1})
        return 0

    gemrb.UnmemorizeSpell = unmemorize
    gemrb.MemorizeSpell = memorize
    gemrb.RemoveSpell = remove_spell
    gemrb.LearnSpell = learn_spell

    old_gemrb = sys.modules.get("GemRB")
    old_gui = sys.modules.get("GUICommon")
    old_ie_spells = sys.modules.get("ie_spells")
    sys.modules["GemRB"] = gemrb
    sys.modules["GUICommon"] = gui
    sys.modules["ie_spells"] = ie_spells
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psion_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        real_begin_manifest = module.begin_manifest
        callback_counts = {}

        def gui_begin_manifest(actor, resref):
            info = module.action_info(resref)
            transactional = bool(
                info
                and (
                    info["kind"] in ("center", "feat_choice", "skill_choice")
                    or (info["kind"] == "power" and not info.get("selector", False))
                )
            )
            result = real_begin_manifest(actor, resref)
            if not transactional:
                return result
            key = (actor, str(resref).upper())
            count = callback_counts.get(key, 0) + 1
            if not result or count >= 2:
                callback_counts.pop(key, None)
                module.cancel_pending(actor)
            else:
                callback_counts[key] = count
            return result

        module.begin_manifest = gui_begin_manifest

        def speed_helper_blocked():
            return any(
                effect["Param2"] == module.SPEED_BLOCK_MARKER
                and effect["Resource1"] == module.SPEED_ON_RESOURCE
                for effect in get_effects(1, module.STATE_EFFECT_OPCODE)
            )

        def resolve_center_mind(resource=None):
            """Model both native effects of a successfully resolved Center SPL."""
            source = resource or module._center_resource_for_actor(1)
            apply_effect(
                1,
                module.STATE_EFFECT_OPCODE,
                1,
                module.FOCUS_EFFECT_MARKER,
                module.FOCUS_EFFECT_RESOURCE,
                "",
                "",
                source,
                9,
            )
            if not speed_helper_blocked():
                applied_spells.append((1, module.SPEED_ON_RESOURCE))

        def known_refs():
            return {str(spell["SpellResRef"]).upper() for spell in known_innates}

        def memorized_refs():
            return {str(spell["SpellResRef"]).upper() for spell in memorized_innates}

        initial_cap = module.maximum_pool(1)
        assert initial_cap == 383
        assert module.ensure_pool(1) == initial_cap
        assert stats[(1, 239)] == module.POOL_STATE_SIGNATURE | initial_cap
        persistent = get_effects(1, module.STATE_EFFECT_OPCODE)
        pool = [effect for effect in persistent if effect["Param2"] == module.POOL_EFFECT_MARKER]
        assert len(pool) == 1 and pool[0]["Param1"] == initial_cap
        stats[(1, 239)] = 0
        assert module.ensure_pool(1) == initial_cap

        assert module.ensure_focus(1, True)
        assert module._write_pool_state(1, 0) == 0
        assert module.ensure_pool(1) == 0
        assert not module.is_focused(1)
        assert not module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.ensure_pool(1, True) == initial_cap
        assert not module.is_focused(1)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        resolve_center_mind(module.CENTER_RESOURCE)
        assert module.is_focused(1)

        module._write_pool_state(1, 1)
        module._write_focus_state(1, True)
        assert module.begin_manifest(1, "PSMT01")
        assert module.begin_manifest(1, "PSMT01")
        assert module.ensure_pool(1) == 0
        assert not module.is_focused(1)
        assert module.ensure_pool(1, True) == initial_cap
        assert not module.is_focused(1)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        resolve_center_mind(module.CENTER_RESOURCE)
        assert module.is_focused(1)

        assert speed_helper_blocked()
        assert module.expend_focus(1)
        assert not module.is_focused(1)
        assert applied_spells[-1] == (1, module.SPEED_OFF_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        before_resolution = len(applied_spells)
        resolve_center_mind(module.CENTER_RESOURCE)
        assert module.is_focused(1)
        assert len(applied_spells) == before_resolution

        stats[(1, 34)] = 1
        assert module.sync_skill_points(1) == 24
        assert module.skill_points_remaining(1) == 24
        assert module.skill_rank_cap(1) == 4
        choices = set(module.available_skill_choices(1))
        assert {
            "PXSCONC", "PXSPSIC", "PXSSELF", "PXSKNOW", "PXSDEVC", "PXSHEAL"
        } <= choices
        assert "PXSAWAR" not in choices
        assert "PXSECTO" not in choices
        assert "PXSENRG" not in choices
        assert "PXSSPAT" not in choices
        assert "PXSINFL" not in choices
        assert module.action_info(module.SKILL_SELECTOR_RESOURCE)["kind"] == "skill_selector"
        assert module.begin_manifest(1, module.SKILL_SELECTOR_RESOURCE)

        for expected_rank in range(1, 5):
            before_points = module.skill_points_remaining(1)
            assert module.begin_manifest(1, "PXSCONC")
            assert module.skill_rank(1, "CONCENTRATION") == expected_rank - 1
            assert module.begin_manifest(1, "PXSCONC")
            assert module.skill_rank(1, "CONCENTRATION") == expected_rank
            assert module.skill_points_remaining(1) == before_points - 1
        assert module.skill_points_remaining(1) == 20
        assert not module.can_train_skill(1, "PXSCONC")
        assert module.can_train_skill(1, "PXSHEAL")
        assert not module.can_train_skill(1, "PXSAWAR")

        assert not module.concentration_check(1, 20, roll=13)
        assert module.concentration_check(1, 20, roll=14)
        assert module.expend_focus(1)
        roll_value["value"] = 13
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        roll_value["value"] = 14
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        resolve_center_mind(module.CENTER_RESOURCE)
        assert module.is_focused(1)
        roll_value["value"] = 20

        stats[(1, 34)] = 5
        assert module.sync_skill_points(1) == 44
        stats[(1, 38)] = 22
        base_stats[(1, 38)] = 22
        stats[(1, 34)] = 6
        assert module.sync_skill_points(1) == 52
        stats[(1, 38)] = 18
        base_stats[(1, 38)] = 18

        assert not module.can_select_feat(1, module.PSIONIC_MEDITATION)
        for expected_rank in range(5, 8):
            assert module.begin_manifest(1, "PXSCONC")
            assert module.begin_manifest(1, "PXSCONC")
            assert module.skill_rank(1, "CONCENTRATION") == expected_rank
        assert module.skill_points_remaining(1) == 49
        stats[(1, 39)] = 12
        assert not module.can_select_feat(1, module.PSIONIC_MEDITATION)
        stats[(1, 39)] = 14
        assert module.can_select_feat(1, module.PSIONIC_MEDITATION)
        assert module.feat_choice_info(module.PSIONIC_MEDITATION)["rank"] == 7

        assert module.bonus_feat_spent(1) == 0
        assert module.begin_manifest(1, module.PSIONIC_MEDITATION)
        assert module.feat_rank(1, module.PSIONIC_MEDITATION) == 0
        assert module.begin_manifest(1, module.PSIONIC_MEDITATION)
        assert module.feat_rank(1, module.PSIONIC_MEDITATION) == 1
        assert module.bonus_feat_spent(1) == 1
        assert module.CENTER_RESOURCE not in known_refs()
        assert module.CENTER_RESOURCE not in memorized_refs()
        assert module.MEDITATION_CENTER_RESOURCE in known_refs()
        assert module.MEDITATION_CENTER_RESOURCE in memorized_refs()
        assert module._center_resource_for_actor(1) == module.MEDITATION_CENTER_RESOURCE

        assert module.expend_focus(1)
        assert not module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.MEDITATION_CENTER_RESOURCE)
        assert module.begin_manifest(1, module.MEDITATION_CENTER_RESOURCE)
        assert not module.is_focused(1)
        resolve_center_mind(module.MEDITATION_CENTER_RESOURCE)
        assert module.is_focused(1)

        module._write_feat_rank(1, module.PSIONIC_MEDITATION, 0)
        module._write_bonus_feat_spent(1, 0)
        assert module._sync_center_action(1)
        assert module.CENTER_RESOURCE in known_refs()
        assert module.CENTER_RESOURCE in memorized_refs()
        assert module.MEDITATION_CENTER_RESOURCE not in known_refs()
        assert module.MEDITATION_CENTER_RESOURCE not in memorized_refs()

        for spell in memorized_innates:
            if spell["SpellResRef"] == "PXSKILL":
                spell["Flags"] = 0
        restored = module.refresh_innate_charges(1)
        assert restored >= 1
        assert next(
            spell for spell in memorized_innates if spell["SpellResRef"] == "PXSKILL"
        )["Flags"] == 1

        for level, slots in ((1, 1), (4, 1), (5, 2), (9, 2), (10, 3), (15, 4), (20, 5)):
            stats[(1, 34)] = level
            assert module.bonus_feat_slots(1) == slots
        stats[(1, 34)] = 20
        assert module.bonus_feats_remaining(1) == 5
        assert module.action_info(module.FEAT_SELECTOR_RESOURCE)["kind"] == "feat_selector"
        assert module.begin_manifest(1, module.FEAT_SELECTOR_RESOURCE)

        for spell in memorized_innates:
            if spell["SpellResRef"] in ("PS1ERAY", module.CENTER_RESOURCE, "PXFSEL"):
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 3
        states = {spell["SpellResRef"]: spell["Flags"] for spell in memorized_innates}
        assert states["PS1ERAY"] == 1
        assert states[module.CENTER_RESOURCE] == 1
        assert states["PXFSEL"] == 1
        assert states["PXSKILL"] == 1
        for spell in memorized_innates:
            if spell["SpellResRef"] == "PXFSEL":
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 1
        assert next(spell for spell in memorized_innates if spell["SpellResRef"] == "PXFSEL")["Flags"] == 1

        assert module.can_select_feat(1, "PXFTALT")
        assert module.can_select_feat(1, "PXFBODY")
        assert module.can_select_feat(1, "PXFSPD")
        assert module.can_select_feat(1, module.PSIONIC_MEDITATION)
        stats[(1, 39)] = 12
        assert not module.can_select_feat(1, "PXFSPD")
        assert not module.can_select_feat(1, module.PSIONIC_MEDITATION)
        assert module.filter_spellinfo(
            1, ["SPWI112", "PXFTALT", "PXFSPD", module.PSIONIC_MEDITATION]
        ) == ["SPWI112", "PXFTALT"]
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
        assert not speed_helper_blocked()
        assert applied_spells[-1] == (1, module.SPEED_ON_RESOURCE)
        assert [effect["Param1"] for effect in get_effects(1, "MaximumHPModifier")] == [6, 2]
        assert module.expend_focus(1)
        assert applied_spells[-1] == (1, module.SPEED_OFF_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert module.begin_manifest(1, module.CENTER_RESOURCE)
        assert not module.is_focused(1)
        resolve_center_mind(module.CENTER_RESOURCE)
        assert module.is_focused(1)
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
        assert module.bonus_feat_spent(1) == 5
        assert module.bonus_feats_remaining(1) == 0
        assert not module.can_select_feat(1, "PXFTALT")
        assert not module.begin_manifest(1, module.FEAT_SELECTOR_RESOURCE)
        assert module.available_feat_choices(1) == []

        for spell in memorized_innates:
            if spell["SpellResRef"] == "PXFSEL":
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 0
        assert next(spell for spell in memorized_innates if spell["SpellResRef"] == "PXFSEL")["Flags"] == 0

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
                    {"SpellIndex": 4001, "SpellResRef": module.CENTER_RESOURCE},
                    {"SpellIndex": 4002, "SpellResRef": module.MEDITATION_CENTER_RESOURCE},
                    {"SpellIndex": 4003, "SpellResRef": "PXSKILL"},
                ]

        collision = CollisionSpellbook()
        raw_spellinfo[:] = ["PSMT03", "PSNOTMOD", "PXSCONC"]
        entry = module.resolve_power_entry(collision, 1, 255000)
        assert entry == {"SpellIndex": 255000, "SpellResRef": "PSMT03"}
        assert module.resolve_power_entry(collision, 1, 255001) is None
        skill_child = module.resolve_power_entry(collision, 1, 255002)
        assert skill_child == {"SpellIndex": 255002, "SpellResRef": "PXSCONC"}
        ordinary = module.resolve_power_entry(collision, 1, 4000)
        assert ordinary["SpellResRef"] == "PS1VIGR"
        normal_center = module.resolve_power_entry(collision, 1, 4001)
        fast_center = module.resolve_power_entry(collision, 1, 4002)
        assert normal_center["SpellResRef"] == module.CENTER_RESOURCE
        assert fast_center["SpellResRef"] == module.MEDITATION_CENTER_RESOURCE
        assert not module.begin_manifest(1, module.MEDITATION_CENTER_RESOURCE)
        skill_parent = module.resolve_power_entry(collision, 1, 4003)
        assert skill_parent["SpellResRef"] == "PXSKILL"

        module.ensure_pool(1, True)
        selected = module.resolve_power_entry(collision, 1, 255000)
        assert module.begin_manifest(1, selected["SpellResRef"])
        module._write_pool_state(1, 0)
        confirmed = module.resolve_power_entry(collision, 1, 255000)
        assert not module.begin_manifest(1, confirmed["SpellResRef"])
        module.ensure_pool(1, True)

        for spell in memorized_innates:
            if spell["SpellResRef"] in ("PS1ERAY", module.CENTER_RESOURCE):
                spell["Flags"] = 0
        assert module.refresh_innate_charges(1) == 2
        states = {spell["SpellResRef"]: spell["Flags"] for spell in memorized_innates}
        assert states["PS1ERAY"] == 1
        assert states["PS1VIGR"] == 1
        assert states[module.CENTER_RESOURCE] == 1
        assert states["PXFSEL"] == 0
        assert states["PXSKILL"] == 1
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
        if old_ie_spells is None:
            sys.modules.pop("ie_spells", None)
        else:
            sys.modules["ie_spells"] = old_ie_spells

    print("Psion fake-GemRB PP-zero focus lifecycle, Psionic Meditation swap/prerequisites, persistent skills, Concentration, feats, selectors, and persistence validation passed.")


if __name__ == "__main__":
    main()
