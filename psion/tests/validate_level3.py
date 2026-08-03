#!/usr/bin/env python3
"""Static regression checks for the purpose-built level-3 Psion powers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

LEVEL3_REFS = {
    "PS3DPSI", "PS3BADJ", "PS3EBLT", "PS3MBAR", "PS3TSGT", "PS3THOP",
    "PS3DANG", "PS3COCO", "PS3ECON", "PS3HUST", "PS3SSTP", "PS3CBRE",
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
        "PS3MBAR": ("opcode = 321", "parameter1 = (0 - 4)", "parameter1 = (0 - 2)", "opcode = 292", "duration = 6"),
        "PS3TSGT": ("opcode = 193", "opcode = 292", "parameter2 = 74"),
        "PS3THOP": ("opcode = 213", "duration = 18", "savingthrow = BIT0"),
        "PS3DANG": ("opcode = 91", "parameter1 = 20", "parameter1 = (0 - 2)", "opcode = 292"),
        "PS3COCO": ("opcode = 175", "duration = 18", "savingthrow = BIT1"),
        "PS3ECON": ("psion_cone_projectile", "dicenumber = 5", "savingthrow = BIT1"),
        "PS3HUST": ("opcode = 321", "parameter1 = 200", "parameter2 = 2", "duration = 6"),
        "PS3SSTP": ("opcode = 124", "parameter2 = 1", "ps_target = 4"),
        # Crisis of Breath: choking damage plus silence and slow. Asserting the
        # absence of opcode 175 pins the replacement of Mental Stasis, whose
        # signature led with hold.
        "PS3CBRE": ("opcode = 12", "dicenumber = 3", "opcode = 38", "opcode = 40", "duration = 18"),
    }
    for resref, fragments in required.items():
        power = section(builder, resref)
        for fragment in fragments:
            assert fragment in power, (resref, fragment)

    for resref in ("PS3DPSI", "PS3EBLT", "PS3THOP", "PS3COCO", "PS3ECON", "PS3CBRE"):
        assert "ps_flags = psion_level3_hostile_flags" in section(builder, resref)

    # Mental Stasis was not an EPH power; nothing may reintroduce it.
    crisis_of_breath = section(builder, "PS3CBRE")
    assert "opcode = 175" not in crisis_of_breath
    assert "PS3MSTL" not in builder

    # SRD gives Crisis of Breath "Will negates", so the save must negate rather
    # than halve. special = BIT8 on the damage would silently make it half.
    assert "special = BIT8" not in crisis_of_breath

    # Body Adjustment heals a flat 1d12; the tabletop power has no +5 rider.
    body_adjustment = section(builder, "PS3BADJ")
    assert "opcode = 17" in body_adjustment
    assert "parameter1 = 5" not in body_adjustment

    # Hustle grants an extra move action, never an extra attack (opcode 1).
    hustle = section(builder, "PS3HUST")
    assert "opcode = 1 target" not in hustle

    # The cocoon's hardness belongs to the shell, so the trapped creature must
    # not receive damage resistance (opcodes 86-89).
    cocoon = section(builder, "PS3COCO")
    assert "ps_resist_opcode" not in cocoon
    assert "parameter1 = 50" not in cocoon

    for resref in ("PS3MBAR", "PS3TSGT", "PS3DANG", "PS3HUST"):
        assert "opcode = 321" in section(builder, resref)

    print("Psion level-3 resource validation passed.")


if __name__ == "__main__":
    main()
