#!/usr/bin/env python3
"""Behavioral source checks for coupled high-tier Psion save outcomes."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def text(name: str) -> str:
    return (ROOT / "lib" / name).read_text(encoding="utf-8")


def copy_block(source: str, marker: str) -> str:
    """Return one COPY_EXISTING block through its matching BUT_ONLY."""
    start = source.index(marker)
    end = source.index("BUT_ONLY", start)
    return source[start : end + len("BUT_ONLY")]


def dice(block: str) -> list[int]:
    return [int(value) for value in re.findall(r"dicenumber = (\d+)", block)]


def assert_single_save_gate(
    parent: str,
    child: str,
    *,
    save: str,
    resource: str,
) -> None:
    assert parent.count("savingthrow = ") == 1, parent
    assert f"savingthrow = {save}" in parent, parent
    assert parent.count("opcode = 146") == 1, parent
    assert f"resource = ~{resource}~" in parent, parent
    assert "parameter2 = 1" in parent, parent
    assert "savingthrow = " not in child, child


def validate_telekinetic_sphere() -> None:
    source = text("level8-powers.tpa")
    child = copy_block(
        source,
        "COPY_EXISTING ~PS8TKSP.spl~ ~override/PS8TKSB.spl~",
    )
    parent = copy_block(
        source,
        "COPY_EXISTING ~PS8TKSP.spl~ ~override~",
    )

    assert_single_save_gate(parent, child, save="BIT1", resource="PS8TKSB")
    assert "opcode = 175" in child
    assert "opcode = 0" in child and "parameter1 = (0 - 6)" in child
    assert "ps_resist_opcode = 86" in child
    assert "parameter1 = 50" in child
    assert "opcode = 175" not in parent


def validate_crisis_of_life() -> None:
    source = text("level7-powers.tpa")
    child = copy_block(
        source,
        "COPY_EXISTING ~PS7CLIF.spl~ ~override/PS7CLIB.spl~",
    )
    parent = copy_block(
        source,
        "COPY_EXISTING ~PS7CLIF.spl~ ~override~",
    )

    assert_single_save_gate(parent, child, save="BIT2", resource="PS7CLIB")
    assert dice(parent) == [5], dice(parent)
    assert dice(child) == [5], dice(child)
    assert sum(dice(parent) + dice(child)) == 10
    assert "dicesize = 6" in parent and "dicesize = 6" in child
    assert "opcode = 175" in child and "duration = 6" in child
    assert "opcode = 175" not in parent


def validate_tornado_blast() -> None:
    source = text("level9-powers.tpa")
    child = copy_block(
        source,
        "COPY_EXISTING ~PSTORNB.spl~ ~override~",
    )
    parent = copy_block(
        source,
        "COPY_EXISTING ~PS9TORN.spl~ ~override~",
    )

    assert_single_save_gate(parent, child, save="BIT1", resource="PSTORNB")
    assert dice(parent) == [8], dice(parent)
    assert dice(child) == [9], dice(child)
    assert sum(dice(parent) + dice(child)) == 17
    assert "dicesize = 6" in parent and "dicesize = 6" in child
    assert "CRUSHING" in parent and "CRUSHING" in child
    assert "opcode = 238" in child and "parameter1 = 8" in child
    assert "opcode = 238" not in parent


def main() -> None:
    validate_telekinetic_sphere()
    validate_crisis_of_life()
    validate_tornado_blast()
    print("Psion high-tier single-save package validation passed.")


if __name__ == "__main__":
    main()
