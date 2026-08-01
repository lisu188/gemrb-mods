#!/usr/bin/env python3
"""Fast static checks for Psion class progression and chargen semantics."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    fixture = (ROOT / "tests" / "make_weidu_fixture.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "tests" / "validate_weidu_install.sh").read_text(encoding="utf-8")

    for fragment in (
        "COPY_EXISTING ~xplevel.2da~ ~override~",
        "COUNT_2DA_COLS ps_xp_cols",
        "COUNT_2DA_ROWS ps_xp_cols ps_xp_rows",
        "STRING_EQUAL_CASE ~MAGE~",
        "FOR (ps_col = 1; ps_col < ps_xp_cols; ++ps_col)",
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

    # Class-common owns chargen minima, proficiency limits and the campaign cap.
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

    layout_pos = setup.index("INCLUDE ~psion/lib/class-layout.tpa~")
    progression_pos = setup.index("INCLUDE ~psion/lib/class-progression.tpa~")
    common_pos = setup.index("INCLUDE ~psion/lib/class-common.tpa~")
    assert layout_pos < progression_pos < common_pos

    for fragment in (
        '"normalized": 20',
        '"native": 41',
        '"legacy": 40',
        'override / "xplevel.2da"',
        'override / "thac0.2da"',
        'override / "lore.2da"',
        'override / "profs.2da"',
        'override / "abclasrq.2da"',
        'override / "weapprof.2da"',
        '("MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHR")',
        '("ID", "NAME_REF", "DESC_REF", "MAGE", "SORCERER")',
        '"QUARTERSTAFF"',
        '"CROSSBOW"',
        '135000',
        '("RATE",)',
    ):
        assert fragment in fixture, fragment

    for fragment in (
        '"abclasrq.2da", "weapprof.2da"',
        'ability_rows.get(discipline) == ["0", "0", "0", "15", "0", "0"]',
        'allowed = {"DAGGER", "CLUB", "SPEAR", "QUARTERSTAFF", "CROSSBOW", "DART", "SLING"}',
        'xp_rows.get(discipline) == xp_rows["MAGE"]',
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

    print("Psion XP, THAC0, Lore, weapon, chargen, and cap validation passed.")


if __name__ == "__main__":
    main()
