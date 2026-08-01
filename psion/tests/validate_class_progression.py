#!/usr/bin/env python3
"""Fast static checks for Psion XP, THAC0, and Lore progression wiring."""

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
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    fixture = (ROOT / "tests" / "make_weidu_fixture.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "tests" / "validate_weidu_install.sh").read_text(encoding="utf-8")

    # XP progression must be copied from the complete active-game MAGE row,
    # not hard-coded to one BG-family table width.
    for fragment in (
        "COPY_EXISTING ~xplevel.2da~ ~override~",
        "COUNT_2DA_COLS ps_xp_cols",
        "COUNT_2DA_ROWS ps_xp_cols ps_xp_rows",
        "STRING_EQUAL_CASE ~MAGE~",
        "FOR (ps_col = 1; ps_col < ps_xp_cols; ++ps_col)",
    ):
        assert fragment in progression, fragment

    # Attack progression is generated explicitly for however many level columns
    # the installed game exposes.
    for fragment in (
        "COPY_EXISTING ~thac0.2da~ ~override~",
        "COUNT_2DA_COLS ps_thac0_cols",
        "SET ps_value = 20 - (ps_col / 2)",
        "PATCH_IF ps_value < 0",
        "SET ps_value = 0",
    ):
        assert fragment in progression, fragment

    # GemRB's level-up code looks up LORE.2DA by exact class row name, so every
    # discipline must define the designed +5 Lore/level rate explicitly.
    for fragment in (
        "COPY_EXISTING ~lore.2da~ ~override~",
        "COUNT_2DA_COLS ps_lore_cols",
        "PATCH_IF ps_lore_cols = 2",
        "standard single-RATE LORE.2DA layout",
    ):
        assert fragment in progression, fragment

    for discipline in DISCIPLINES:
        assert f"APPEND ~xplevel.2da~ ~{discipline}%ps_xp_values%~" in progression
        assert f"APPEND ~thac0.2da~ ~{discipline}%ps_thac0_values%~" in progression
        assert f"APPEND ~lore.2da~ ~{discipline} 5~" in progression

    layout_pos = setup.index("INCLUDE ~psion/lib/class-layout.tpa~")
    progression_pos = setup.index("INCLUDE ~psion/lib/class-progression.tpa~")
    common_pos = setup.index("INCLUDE ~psion/lib/class-common.tpa~")
    assert layout_pos < progression_pos < common_pos

    # The three fixtures intentionally differ in width; this prevents a fixed
    # 20-level implementation from accidentally passing all lifecycle tests.
    for fragment in (
        '"normalized": 20',
        '"native": 41',
        '"legacy": 40',
        'override / "xplevel.2da"',
        'override / "thac0.2da"',
        'override / "lore.2da"',
        '135000',
        '("RATE",)',
    ):
        assert fragment in fixture, fragment

    # Lifecycle validation must verify install values and exact rollback for
    # all three class-progression resources.
    for fragment in (
        '"xplevel.2da", "thac0.2da", "lore.2da"',
        'xp_rows.get(discipline) == xp_rows["MAGE"]',
        '20 - (level // 2)',
        'assert xp_rows["MAGE"][8] == "135000"',
        'lore_rows.get(discipline) == ["5"]',
    ):
        assert fragment in lifecycle, fragment

    expected = [max(0, 20 - (level // 2)) for level in range(1, 42)]
    assert expected[:10] == [20, 19, 19, 18, 18, 17, 17, 16, 16, 15]
    assert expected[19] == 10
    assert expected[-1] == 0

    print("Psion XP, THAC0, and Lore progression validation passed.")


if __name__ == "__main__":
    main()
