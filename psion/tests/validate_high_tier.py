#!/usr/bin/env python3
"""Behavioral source checks for coupled high-tier Psion save, PR, and bounce outcomes."""

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


def validate_effect_power_and_reddopsi() -> None:
    helper = text("spell-functions.tpa")
    assert "power = 255" in helper
    assert "READ_LONG 0x34 ps_effect_power" in helper
    assert "WRITE_BYTE (ps_new_effect + 0x03) ps_effect_power" in helper
    assert "WRITE_BYTE (ps_new_effect + 0x03) power" not in helper

    source = text("level7-powers.tpa")
    reddopsi = copy_block(source, "COPY_EXISTING ~PS7RDOP.spl~ ~override~")
    assert reddopsi.count("opcode = 199") == 1, reddopsi  # one loop source line
    assert "opcode = 200" not in reddopsi, reddopsi
    assert "ps_bounce_level = 1" in reddopsi
    assert "ps_bounce_level <= 9" in reddopsi
    assert "parameter1 = ps_bounce_level" in reddopsi
    assert "parameter2 = ps_bounce_level" not in reddopsi
    assert "duration = 60" in reddopsi


def validate_mass_cocoon_and_time_hop() -> None:
    level7 = text("level7-powers.tpa")
    cocoon = copy_block(level7, "COPY_EXISTING ~PS7MCOC.spl~ ~override~")
    assert cocoon.count("savingthrow = BIT1") == 1, cocoon
    assert "resist_dispel = BIT0" not in cocoon, cocoon
    assert "resist_dispel = BIT1" in cocoon, cocoon

    level8 = text("level8-powers.tpa")
    time_hop = copy_block(level8, "COPY_EXISTING ~PS8MTHP.spl~ ~override~")
    assert time_hop.count("savingthrow = BIT0") == 1, time_hop
    assert "resist_dispel = BIT0" not in time_hop, time_hop
    assert "resist_dispel = BIT1" in time_hop, time_hop


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

    # SRD: Reflex negates, PR Yes. The one parent opcode therefore owns both
    # the one PR/MR check and the one save; the applied package bypasses both.
    assert_single_save_gate(parent, child, save="BIT1", resource="PS8TKSB")
    assert parent.count("resist_dispel = BIT0") == 1, parent
    assert "resist_dispel = BIT0" not in child, child
    assert "opcode = 175" in child
    assert "opcode = 0" in child and "parameter1 = (0 - 6)" in child
    assert "ps_resist_opcode = 86" in child
    assert "parameter1 = 50" in child
    assert "opcode = 175" not in parent


def validate_crisis_of_life() -> None:
    source = text("level7-powers.tpa")
    failure = copy_block(
        source,
        "COPY_EXISTING ~PS7CLIF.spl~ ~override/PS7CLIB.spl~",
    )
    resolution = copy_block(
        source,
        "COPY_EXISTING ~PS7CLIF.spl~ ~override/PS7CLIR.spl~",
    )
    parent = copy_block(
        source,
        "COPY_EXISTING ~PS7CLIF.spl~ ~override~",
    )

    # SRD: Fortitude partial, PR Yes. Parent does exactly one PR/MR check and no
    # save. The resolution child bypasses PR, deals the SRD successful-save 7d6
    # and owns the only save; the failure child bypasses PR/save and adds 3d6
    # plus hold as the portable substitute for the tabletop instant-death branch.
    assert parent.count("opcode = 146") == 1, parent
    assert "resource = ~PS7CLIR~" in parent, parent
    assert "savingthrow = " not in parent, parent
    assert parent.count("resist_dispel = BIT0") == 1, parent
    assert dice(parent) == [], dice(parent)

    assert_single_save_gate(
        resolution,
        failure,
        save="BIT2",
        resource="PS7CLIB",
    )
    assert "resist_dispel = BIT0" not in resolution, resolution
    assert "resist_dispel = BIT0" not in failure, failure
    assert dice(resolution) == [7], dice(resolution)
    assert dice(failure) == [3], dice(failure)
    assert sum(dice(resolution) + dice(failure)) == 10
    assert "dicesize = 6" in resolution and "dicesize = 6" in failure
    assert "opcode = 175" in failure and "duration = 6" in failure
    assert "opcode = 175" not in resolution


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

    # SRD: Reflex half, PR No. One save controls the extra damage/knockback and
    # no effect in either resource may opt into magic/power resistance.
    assert_single_save_gate(parent, child, save="BIT1", resource="PSTORNB")
    assert "resist_dispel = BIT0" not in parent, parent
    assert "resist_dispel = BIT0" not in child, child
    assert parent.count("resist_dispel = BIT1") >= 2, parent
    assert child.count("resist_dispel = BIT1") >= 2, child
    assert dice(parent) == [8], dice(parent)
    assert dice(child) == [9], dice(child)
    assert sum(dice(parent) + dice(child)) == 17
    assert "dicesize = 6" in parent and "dicesize = 6" in child
    assert "CRUSHING" in parent and "CRUSHING" in child
    assert "opcode = 238" in child and "parameter1 = 8" in child
    assert "opcode = 238" not in parent


def validate_psychic_chirurgery() -> None:
    source = text("level9-powers.tpa")
    child = copy_block(
        source,
        "COPY_EXISTING ~PS9PCHI.spl~ ~override/PS9PCHB.spl~",
    )
    parent = copy_block(
        source,
        "COPY_EXISTING ~PS9PCHI.spl~ ~override~",
    )

    # SRD: Will negates, PR Yes. One parent gate owns both defenses; the child
    # carries the complete restorative approximation and cannot trigger either
    # defense a second time.
    assert_single_save_gate(parent, child, save="BIT0", resource="PS9PCHB")
    assert parent.count("resist_dispel = BIT0") == 1, parent
    assert "resist_dispel = BIT0" not in child, child
    assert "opcode = 224" in child
    assert "opcode = 321" in child
    assert "parameter2 = 5" in child
    assert "parameter2 = 128" in child
    assert "opcode = 224" not in parent


def main() -> None:
    validate_effect_power_and_reddopsi()
    validate_mass_cocoon_and_time_hop()
    validate_telekinetic_sphere()
    validate_crisis_of_life()
    validate_tornado_blast()
    validate_psychic_chirurgery()
    print("Psion high-tier bounce, single-save and power-resistance validation passed.")


if __name__ == "__main__":
    main()
