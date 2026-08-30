#!/usr/bin/env python3
"""Fast static checks for Psion class progression and chargen semantics."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "common"
DISCIPLINES = (
    "PSION_SEER",
    "PSION_SHAPER",
    "PSION_KINETICIST",
    "PSION_EGOIST",
    "PSION_NOMAD",
    "PSION_TELEPATH",
)


def main() -> None:
    progression = (ROOT / "lib" / "class-progression.tpa").read_text(encoding="utf-8")
    class_common = (ROOT / "lib" / "class-common.tpa").read_text(encoding="utf-8")
    class_saves = (ROOT / "lib" / "class-saves.tpa").read_text(encoding="utf-8")
    class_layout = (ROOT / "lib" / "class-layout.tpa").read_text(encoding="utf-8")
    item_usability = (ROOT / "lib" / "item-usability.tpa").read_text(encoding="utf-8")
    spell_helpers = (COMMON / "weidu" / "spell-functions.tpa").read_text(encoding="utf-8")
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    fixture = (ROOT / "tests" / "make_weidu_fixture.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "tests" / "validate_weidu_install.sh").read_text(encoding="utf-8")

    for fragment in (
        "COPY_EXISTING ~xplevel.2da~ ~override~",
        "COUNT_2DA_COLS ps_xp_cols",
        "COUNT_2DA_ROWS ps_xp_cols ps_xp_rows",
        "SET ps_mage_start = INDEX_BUFFER (~^MAGE[ %TAB%]+~)",
        "READ_ASCII ps_mage_start ps_mage_row",
        "REPLACE_TEXTUALLY ~^MAGE[ %TAB%]+~ ~~",
        "OUTER_SPRINT ps_xp_values ~ %ps_values%~",
        "FOR (ps_col = 21; ps_col < ps_xp_cols; ++ps_col)",
        "SET_2DA_ENTRY ps_row ps_col ps_xp_cols ~2147483647~",
    ):
        assert fragment in progression, fragment

    for fragment in (
        "COPY_EXISTING ~thac0.2da~ ~override~",
        "COUNT_2DA_COLS ps_thac0_cols",
        "SET ps_value = 20 - (ps_col / 2)",
        "PATCH_IF ps_value < 0",
        "SET ps_value = 0",
    ):
        assert fragment in progression, fragment

    for fragment in (
        "COPY_EXISTING ~lore.2da~ ~override~",
        "COUNT_2DA_COLS ps_lore_cols",
        "PATCH_IF ps_lore_cols = 2",
        "standard single-RATE LORE.2DA layout",
    ):
        assert fragment in progression, fragment

    for fragment in (
        "COPY_EXISTING ~savewiz.2da~ ~override/savepsi.2da~",
        "COUNT_2DA_COLS ps_save_cols",
        "COUNT_2DA_ROWS ps_save_cols ps_save_rows",
        "ps_save_rows != 5",
        "PATCH_FOR_EACH ps_save_row IN 1 4",
        "READ_2DA_ENTRY ps_save_row ps_save_col ps_save_cols ps_save_value",
        "SET ps_save_value = ps_save_value - 2",
        "SET_2DA_ENTRY ps_save_row ps_save_col ps_save_cols ~%ps_save_value%~",
    ):
        assert fragment in class_saves, fragment

    for fragment in (
        "COPY_EXISTING ~weapprof.2da~ ~override~",
        "READ_2DA_ENTRY ps_i 0 ps_weapprof_cols ps_prof_name",
        "STRING_EQUAL_CASE ~DAGGER~",
        "STRING_EQUAL_CASE ~CLUB~",
        "STRING_EQUAL_CASE ~SPEAR~",
        "STRING_EQUAL_CASE ~QUARTERSTAFF~",
        "STRING_EQUAL_CASE ~CROSSBOW~",
        "STRING_EQUAL_CASE ~DART~",
        "STRING_EQUAL_CASE ~SLING~",
        "COPY_EXISTING ~abclasrq.2da~ ~override~",
        "PATCH_IF ps_abclasrq_cols = 7",
        "COPY_EXISTING ~xpcap.2da~ ~override~",
        "OUTER_SET ps_xpcap_value = ps_cap",
        "could not locate the MAGE cap in XPCAP.2DA",
    ):
        assert fragment in class_common, fragment
    assert "8000000" not in class_common

    for discipline in DISCIPLINES:
        assert f"APPEND ~xplevel.2da~ ~{discipline}%ps_xp_values%~" in progression
        assert f"APPEND ~thac0.2da~ ~{discipline}%ps_thac0_values%~" in progression
        assert f"APPEND ~lore.2da~ ~{discipline} 5~" in progression
        assert f"APPEND ~profs.2da~ ~{discipline} 2 4~" in class_common
        assert f"APPEND ~abclasrq.2da~ ~{discipline} 0 0 0 15 0 0~" in class_common
        assert f"APPEND ~xpcap.2da~ ~{discipline} %ps_xpcap_value%~" in class_common
        assert f"APPEND_COL ~weapprof.2da~ ~$ $ {discipline}%ps_weapprof_values%~" in class_common

    assert "0x40000" not in class_layout
    assert "SAVEWIZ" not in class_layout
    assert class_layout.count(" SAVEPSI 0 0 ") >= 6
    assert class_layout.count(" SAVEPSI 0 %ps_") >= 6
    assert "DEFINE_PATCH_FUNCTION ~ADD_ITEM_EQEFFECT~" in spell_helpers
    assert "ITM V1" in spell_helpers
    for fragment in (
        "DEFINE_PATCH_FUNCTION PSION_ADD_CLASS_RESTRICTION",
        "COPY_EXISTING_REGEXP GLOB ~.*\\.itm~ ~override~",
        "READ_SHORT 0x1c ps_item_type",
        "READ_LONG 0x1e ps_item_usability",
        "READ_BYTE 0x31 ps_item_proficiency",
        "ps_item_usability BAND 0x40000",
        "ps_item_type = 2",
        "ps_item_type = 12",
        "ps_item_type = 14",
        "ps_item_type = 31",
        "ps_item_proficiency = 0x60",
        "ps_item_proficiency = 0x62",
        "ps_item_proficiency = 0x66",
        "ps_item_proficiency = 0x67",
        "ps_item_proficiency = 0x6a",
        "ps_item_proficiency = 0x6b",
        "ps_item_proficiency = 0x73",
        "ps_has_restriction = 0",
    ):
        assert fragment in item_usability, fragment
    for variable in (
        "ps_seer_id", "ps_shaper_id", "ps_kineticist_id",
        "ps_egoist_id", "ps_nomad_id", "ps_telepath_id",
    ):
        assert f"LPF PSION_ADD_CLASS_RESTRICTION INT_VAR class_id = {variable} END" in item_usability

    saves_pos = setup.index("INCLUDE ~psion/lib/class-saves.tpa~")
    layout_pos = setup.index("INCLUDE ~psion/lib/class-layout.tpa~")
    progression_pos = setup.index("INCLUDE ~psion/lib/class-progression.tpa~")
    common_pos = setup.index("INCLUDE ~psion/lib/class-common.tpa~")
    usability_pos = setup.index("INCLUDE ~psion/lib/item-usability.tpa~")
    assert saves_pos < layout_pos < progression_pos < common_pos < usability_pos
    assert "BEGIN ~Psion late item compatibility patch~" in setup
    assert "DESIGNATED 100" in setup
    assert setup.count("INCLUDE ~psion/lib/item-usability.tpa~") == 2

    for fragment in (
        '"normalized": 20',
        '"native": 41',
        '"legacy": 40',
        'override / "xplevel.2da"',
        'newline="\\r\\n"',
        'override / "thac0.2da"',
        'override / "lore.2da"',
        'override / "profs.2da"',
        'override / "abclasrq.2da"',
        'override / "weapprof.2da"',
        '("MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHR")',
        '("ID", "NAME_REF", "DESC_REF", "MAGE", "SORCERER")',
        '"QUARTERSTAFF"',
        '"CROSSBOW"',
        '"MAGE", "161000"',
        'ITEM_USABILITY_FIXTURES',
        '"psspear.itm": (29, 0x40000, 0x62)',
        '"psclub.itm": (17, 0x40000, 0x73)',
        '"psmace.itm": (17, 0, 0x65)',
        '135000',
        '("RATE",)',
    ):
        assert fragment in fixture, fragment

    for fragment in (
        '"abclasrq.2da", "weapprof.2da"',
        'ability_rows.get(discipline) == ["0", "0", "0", "15", "0", "0"]',
        'allowed = {"DAGGER", "CLUB", "SPEAR", "QUARTERSTAFF", "CROSSBOW", "DART", "SLING"}',
        'xpcap_rows["MAGE"] == ["161000"]',
        'restricted_items = {',
        'legal_items = {',
        '(319, 2, 0, 5, 2)',
        'expected_xp = xp_rows["MAGE"][:20] + ["2147483647"] * max(0, len(xp_columns) - 20)',
        '20 - (level // 2)',
        'assert xp_rows["MAGE"][8] == "135000"',
        'lore_rows.get(discipline) == ["5"]',
        'profs_rows.get(discipline) == ["2", "4"]',
    ):
        assert fragment in lifecycle, fragment

    expected = [max(0, 20 - (level // 2)) for level in range(1, 42)]
    assert expected[:10] == [20, 19, 19, 18, 18, 17, 17, 16, 16, 15]
    assert expected[19] == 10
    assert expected[-1] == 0

    print("Psion capped XP, THAC0, saves, Lore, weapon, chargen, and item usability validation passed.")


if __name__ == "__main__":
    main()
