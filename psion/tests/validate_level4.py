#!/usr/bin/env python3
"""Static regression checks for the purpose-built level-4 Psion powers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

LEVEL4_REFS = {
    "PS4EADP", "PS4FOMV", "PS4DDOR", "PS4IFOR", "PS4TKMN", "PS4PLEE",
    "PS4RVIE", "PS4WECT", "PS4EBAL", "PS4META", "PS4PFLY", "PS4COMP",
}


def section(text: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind("LAF psion_create_level4_power", 0, marker_pos)
    if start < 0:
        raise AssertionError((resref, "missing builder call"))
    next_start = text.find("LAF psion_create_level4_power", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def main() -> None:
    builder = (ROOT / "lib" / "level4-powers.tpa").read_text(encoding="utf-8")
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    table = (ROOT / "tables" / "psionpowers.2da").read_text(encoding="utf-8")

    assert "level4-powers.tpa" in driver
    assert "WRITE_LONG 0x34 4" in builder
    assert "WRITE_LONG 0x18 ps_flags" in builder
    assert "FOR_EACH " not in builder.replace("PATCH_FOR_EACH ", "")

    created = set(re.findall(r"ps_resref = ~(PS4[A-Z0-9]+)~", builder))
    assert created == LEVEL4_REFS, (created, LEVEL4_REFS)

    table_refs = {
        line.split()[0]
        for line in table.splitlines()[3:]
        if line.strip() and line.split()[2] == "4"
    }
    assert table_refs == LEVEL4_REFS, (table_refs, LEVEL4_REFS)

    required = {
        "PS4EADP": ("opcode = 321", "ps_energy_opcode = 27", "parameter1 = 25", "duration = 420"),
        "PS4FOMV": ("opcode = 162", "opcode = 163", "PATCH_FOR_EACH ps_blocked_opcode", "opcode = 101"),
        "PS4DDOR": ("opcode = 124", "target = 1", "parameter2 = 1"),
        "PS4IFOR": ("opcode = 31", "parameter1 = 50", "parameter1 = (0 - 2)", "ps_save_opcode = 33", "duration = 18"),
        "PS4TKMN": ("opcode = 238", "parameter1 = 8", "opcode = 39", "duration = 6"),
        "PS4PLEE": ("PATCH_FOR_EACH ps_failure_type IN 0 1 2", "opcode = 60", "parameter1 = 20"),
        "PS4RVIE": ("opcode = 193", "opcode = 21", "opcode = 91", "parameter1 = 30"),
        "PS4WECT": ("opcode = 67", "resource = ~PSACON01~", "duration = 60"),
        "PS4EBAL": ("opcode = 12", "ELECTRICITY", "dicenumber = 7", "special = BIT8", "savingthrow = BIT1"),
        "PS4META": ("opcode = 44", "opcode = 10", "opcode = 1", "parameter1 = (0 - 2)", "ps_resist_opcode = 86"),
        "PS4PFLY": ("opcode = 126", "parameter1 = 150", "parameter2 = 2", "parameter1 = (0 - 2)", "opcode = 292", "PATCH_FOR_EACH ps_flight_immunity"),
        "PS4COMP": ("opcode = 5", "duration = 30", "savingthrow = BIT0"),
    }
    for resref, fragments in required.items():
        power = section(builder, resref)
        for fragment in fragments:
            assert fragment in power, (resref, fragment)

    for resref in ("PS4TKMN", "PS4PLEE", "PS4EBAL", "PS4COMP"):
        assert "ps_flags = psion_level4_hostile_flags" in section(builder, resref)

    for resref in ("PS4EADP", "PS4FOMV", "PS4IFOR", "PS4RVIE", "PS4META", "PS4PFLY"):
        assert "opcode = 321" in section(builder, resref)

    print("Psion level-4 resource validation passed.")


if __name__ == "__main__":
    main()
