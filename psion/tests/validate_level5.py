#!/usr/bin/env python3
"""Static regression checks for the purpose-built level-5 Psion powers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

LEVEL5_REFS = {
    "PS5ADBD", "PS5CATP", "PS5PRES", "PS5PCRU", "PS5TRUE", "PS5TELE",
    "PS5SCHN", "PS5HOCR", "PS5ECUR", "PS5PFDB", "PS5BALT", "PS5MPRB",
}


def section(text: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind("LAF psion_create_level5_power", 0, marker_pos)
    if start < 0:
        raise AssertionError((resref, "missing builder call"))
    next_start = text.find("LAF psion_create_level5_power", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def main() -> None:
    builder = (ROOT / "lib" / "level5-powers.tpa").read_text(encoding="utf-8")
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    prototype = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")
    table = (ROOT / "tables" / "psionpowers.2da").read_text(encoding="utf-8")

    assert "level5-powers.tpa" in driver
    assert "COPY_EXISTING" not in prototype
    assert "ACTION_PHP_EACH" not in prototype
    assert "WRITE_LONG 0x34 5" in builder
    assert "WRITE_LONG 0x18 ps_flags" in builder
    assert "FOR_EACH " not in builder.replace("PATCH_FOR_EACH ", "")

    created = set(re.findall(r"ps_resref = ~(PS5[A-Z0-9]+)~", builder))
    assert created == LEVEL5_REFS, (created, LEVEL5_REFS)

    table_refs = {
        line.split()[0]
        for line in table.splitlines()[3:]
        if line.strip() and line.split()[2] == "5"
    }
    assert table_refs == LEVEL5_REFS, (table_refs, LEVEL5_REFS)

    required = {
        "PS5ADBD": (
            "opcode = 101", "parameter2 = 25", "parameter2 = 78",
            "ps_energy_opcode = 27", "duration = 540",
        ),
        "PS5CATP": (
            "PATCH_FOR_EACH ps_failure_type IN 0 1 2", "opcode = 60",
            "parameter1 = 30", "duration = 30", "savingthrow = BIT0",
        ),
        "PS5PRES": ("opcode = 166", "parameter1 = 21", "duration = 540"),
        "PS5PCRU": (
            "opcode = 12", "dicenumber = 8", "dicesize = 6", "special = BIT8",
            "opcode = 175", "duration = 12",
        ),
        "PS5TRUE": ("opcode = 193", "opcode = 292", "parameter2 = 74", "duration = 60"),
        "PS5TELE": ("opcode = 124", "target = 1", "parameter2 = 1"),
        "PS5SCHN": ("opcode = 321", "opcode = 0", "opcode = 54", "parameter1 = 2", "parameter1 = (0 - 2)", "duration = 18"),
        "PS5HOCR": ("opcode = 12", "SLASHING", "dicenumber = 9", "dicesize = 4", "special = BIT8"),
        "PS5ECUR": (
            "dicenumber = 5", "PATCH_FOR_EACH ps_delay IN 6 12 18 24",
            "timing = 4", "dicenumber = 2", "ELECTRICITY", "savingthrow = BIT1",
        ),
        "PS5PFDB": (
            "opcode = 321", "opcode = 15", "opcode = 44", "opcode = 10",
            "parameter1 = 2", "duration = 30",
        ),
        "PS5BALT": ("dicenumber = 9", "dicesize = 6", "opcode = 40", "duration = 18", "savingthrow = BIT2"),
        "PS5MPRB": ("ps_save_opcode = 33", "parameter1 = 2", "duration = 30", "savingthrow = BIT0"),
    }
    for resref, fragments in required.items():
        power = section(builder, resref)
        for fragment in fragments:
            assert fragment in power, (resref, fragment)

    second_chance = section(builder, "PS5SCHN")
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = 2" in second_chance
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = (0 - 2)" not in second_chance

    for resref in ("PS5CATP", "PS5PCRU", "PS5HOCR", "PS5ECUR", "PS5BALT", "PS5MPRB"):
        assert "ps_flags = psion_level5_hostile_flags" in section(builder, resref)

    # Psychic Crush is heavy damage plus a brief hold, deliberately not the
    # tabletop save-or-die. Opcode 13 (Death) must never appear here.
    assert "opcode = 13 " not in section(builder, "PS5PCRU")
    # Cognitive Overload was not an EPH power; nothing may reintroduce it.
    assert "PS5COGL" not in builder

    for resref in ("PS5ADBD", "PS5PRES", "PS5TRUE", "PS5SCHN", "PS5PFDB"):
        assert "opcode = 321" in section(builder, resref)

    print("Psion level-5 resource validation passed.")


if __name__ == "__main__":
    main()
