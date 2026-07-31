#!/usr/bin/env python3
"""Static regression checks for the purpose-built level-3 Psion powers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

LEVEL3_REFS = {
    "PS3DPSI", "PS3BADJ", "PS3EBLT", "PS3MBAR", "PS3TSGT", "PS3THOP",
    "PS3DANG", "PS3COCO", "PS3ECON", "PS3HUST", "PS3SSTP", "PS3MSTL",
}


def section(text: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind("LAF psion_create_level3_power", 0, marker_pos)
    if start < 0:
        raise AssertionError((resref, "missing builder call"))
    next_start = text.find("LAF psion_create_level3_power", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def main() -> None:
    builder = (ROOT / "lib" / "level3-powers.tpa").read_text(encoding="utf-8")
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    table = (ROOT / "tables" / "psionpowers.2da").read_text(encoding="utf-8")

    assert "level3-powers.tpa" in driver
    assert "WRITE_LONG 0x34 3" in builder
    assert "WRITE_LONG 0x18 ps_flags" in builder

    created = set(re.findall(r"ps_resref = ~(PS3[A-Z0-9]+)~", builder))
    assert created == LEVEL3_REFS, (created, LEVEL3_REFS)

    table_refs = {
        line.split()[0]
        for line in table.splitlines()[3:]
        if line.strip() and line.split()[2] == "3"
    }
    assert table_refs == LEVEL3_REFS, (table_refs, LEVEL3_REFS)

    required = {
        "PS3DPSI": ("opcode = 58", "parameter1 = 5", "parameter2 = 1"),
        "PS3BADJ": ("opcode = 17", "dicenumber = 1", "dicesize = 12"),
        "PS3EBLT": ("psion_level3_line_projectile", "dicenumber = 5", "savingthrow = BIT1"),
        "PS3MBAR": ("opcode = 321", "parameter1 = -4", "opcode = 292", "duration = 6"),
        "PS3TSGT": ("opcode = 193", "opcode = 292", "parameter2 = 74"),
        "PS3THOP": ("opcode = 213", "duration = 18", "savingthrow = BIT0"),
        "PS3DANG": ("opcode = 91", "parameter1 = 20", "opcode = 292"),
        "PS3COCO": ("opcode = 175", "parameter1 = 50", "duration = 18"),
        "PS3ECON": ("psion_cone_projectile", "dicenumber = 5", "savingthrow = BIT1"),
        "PS3HUST": ("opcode = 321", "parameter1 = 200", "opcode = 1", "duration = 6"),
        "PS3SSTP": ("opcode = 124", "parameter2 = 1", "ps_target = 4"),
        "PS3MSTL": ("opcode = 175", "opcode = 38", "opcode = 40", "duration = 18"),
    }
    for resref, fragments in required.items():
        power = section(builder, resref)
        for fragment in fragments:
            assert fragment in power, (resref, fragment)

    for resref in ("PS3EBLT", "PS3THOP", "PS3COCO", "PS3ECON", "PS3MSTL"):
        assert "ps_flags = psion_level3_hostile_flags" in section(builder, resref)

    for resref in ("PS3MBAR", "PS3TSGT", "PS3DANG", "PS3HUST"):
        assert "opcode = 321" in section(builder, resref)

    print("Psion level-3 resource validation passed.")


if __name__ == "__main__":
    main()
