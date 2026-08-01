#!/usr/bin/env python3
"""Regression checks for BG-family Psion character-generation startup data."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = (
    "PSION_SEER",
    "PSION_SHAPER",
    "PSION_KINETICIST",
    "PSION_EGOIST",
    "PSION_NOMAD",
    "PSION_TELEPATH",
)

# Canonical BG2EE Mage ToB starter package in GemRB CharGenEnd slot order.
MAGE_TOB_EQUIPMENT = (
    "*", "*", "*", "BAG29", "RING06", "RING40", "*", "BOOT01",
    "AMUL21", "BRAC15", "BELT10", "AROW11,40", "BULL03,40", "BOLT06,40",
    "POTN52,5", "POTN04,2", "POTN14,5", "SLNG05", "DAGG05,20", "STAF20",
)


def main() -> None:
    startup = (ROOT / "lib" / "class-startup.tpa").read_text(encoding="utf-8")
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")

    assert "INCLUDE ~psion/lib/class-startup.tpa~" in setup

    # Starting gold must follow the active campaign's Mage row, not a fixed BG2
    # number. The runtime lookup uses the custom class row name directly.
    for fragment in (
        "FILE_EXISTS_IN_GAME ~strtgold.2da~",
        "STRING_EQUAL_CASE ~MAGE~",
        "READ_2DA_ENTRY ps_row ps_col ps_startgold_cols ps_value",
        "FAIL ~The Psion mod could not locate the MAGE row in STRTGOLD.2DA.~",
    ):
        assert fragment in startup, fragment

    for discipline in DISCIPLINES:
        assert (
            f"APPEND ~strtgold.2da~ ~{discipline}%ps_startgold_values%~"
            in startup
        ), discipline

    # GemRB's ToB GiveEquipment function has a fixed twenty-entry RealSlots
    # mapping. The installer must enforce that shape before APPEND_COL.
    assert "PATCH_IF ps_25stweap_rows = 20" in startup
    assert "FAIL ~The Psion mod requires the standard twenty-row 25STWEAP.2DA layout.~" in startup

    match = re.search(
        r"OUTER_SPRINT ps_tob_mage_equipment ~([^~]+)~",
        startup,
    )
    assert match, "missing ToB Mage equipment definition"
    equipment = tuple(match.group(1).split())
    assert equipment == MAGE_TOB_EQUIPMENT, (equipment, MAGE_TOB_EQUIPMENT)
    assert len(equipment) == 20

    for discipline in DISCIPLINES:
        assert (
            f"APPEND_COL ~25stweap.2da~ ~$ $ {discipline} %ps_tob_mage_equipment%~"
            in startup
        ), discipline

    # ToB LevelUp.py indexes LUNUMAB by exact class name even before opening the
    # HLA picker and divides by RATE. Version 1.0 has no Psion HLA subsystem, so
    # every discipline needs a nonzero RATE and an unreachable FIRST_LEVEL.
    assert "FILE_EXISTS_IN_GAME ~lunumab.2da~" in startup
    for discipline in DISCIPLINES:
        assert (
            f"APPEND ~lunumab.2da~ ~{discipline} 99 1 99 1~"
            in startup
        ), discipline

    print("Psion character-generation and ToB level-up table validation passed.")


if __name__ == "__main__":
    main()
