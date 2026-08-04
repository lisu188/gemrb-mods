#!/usr/bin/env python3
"""Static regression checks for psionic focus and runtime-backed bonus feats."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

DISCIPLINE_CLABS = (
    "clabpsee.2da",
    "clabpsha.2da",
    "clabpkin.2da",
    "clabpego.2da",
    "clabpnom.2da",
    "clabptel.2da",
)


def table_rows(name: str) -> list[list[str]]:
    lines = (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines[3:] if line.strip()]


def section(text: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind("LAF psion_create_focus_action", 0, marker_pos)
    assert start >= 0, (resref, "missing focus-action builder call")
    next_start = text.find("LAF psion_create_focus_action", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def main() -> None:
    feat_rows = table_rows("psionfeatpick.2da")
    assert feat_rows == [
        ["PXFTALT", "PSIONIC_TALENT", "1", "0", "1"],
        ["PXFBODY", "PSIONIC_BODY", "1", "0", "0"],
        ["PXFSPD", "SPEED_OF_THOUGHT", "1", "13", "0"],
    ], feat_rows

    selector_rows = table_rows("psfsel.2da")
    assert selector_rows == [
        ["PSIONIC_TALENT", "PXFTALT", "3"],
        ["PSIONIC_BODY", "PXFBODY", "3"],
        ["SPEED_OF_THOUGHT", "PXFSPD", "3"],
    ], selector_rows

    # Psionic Meditation remains deliberately absent until Concentration ranks
    # exist, so its Concentration 7 prerequisite cannot accidentally be skipped.
    assert all("MEDIT" not in token for row in feat_rows for token in row)

    for filename in DISCIPLINE_CLABS:
        text = (ROOT / "tables" / filename).read_text(encoding="utf-8")
        rows = table_rows(filename)
        level1 = next(row for row in rows if row[0] == "1")
        assert level1.count("GA_PXCNTR") == 1, filename
        assert level1.count("GA_PXFSEL") == 1, filename
        assert text.count("GA_PXCNTR") == 1, filename
        assert text.count("GA_PXFSEL") == 1, filename
        # Level thresholds are runtime credits, not repeated spell grants.
        for level in ("5", "10", "15", "20"):
            row = next(row for row in rows if row[0] == level)
            assert "GA_PXFSEL" not in row, (filename, level)

    builder = (ROOT / "lib" / "focus-feats.tpa").read_text(encoding="utf-8")
    created = set(re.findall(r"ps_resref = ~(PX[A-Z0-9]+)~", builder))
    assert created == {
        "PXCNTR",
        "PXFSEL",
        "PXFTALT",
        "PXFBODY",
        "PXFSPD",
        "PXFSPED",
        "PXFSPOF",
    }, created

    center = section(builder, "PXCNTR")
    for fragment in (
        "ps_speed = 9",
        "psion_focus_state_marker = 0x50534643",
        "opcode = 206",
        "parameter1 = 1",
        "parameter2 = psion_focus_state_marker",
        "timing = 9",
        "resource = ~PSFOCUS~",
        "opcode = 146",
        "parameter2 = 1",
        "resource = ~PXFSPED~",
    ):
        assert fragment in center or fragment in builder, fragment

    selector = section(builder, "PXFSEL")
    assert "opcode = 214" in selector
    assert "resource = ~PSFSEL~" in selector

    speed_on = section(builder, "PXFSPED")
    for fragment in (
        "opcode = 321",
        "resource = ~PXFSPED~",
        "opcode = 126",
        "parameter1 = 133",
        "parameter2 = 2",
        "timing = 9",
    ):
        assert fragment in speed_on, fragment

    speed_off = section(builder, "PXFSPOF")
    assert "opcode = 321" in speed_off
    assert "resource = ~PXFSPED~" in speed_off
    assert "opcode = 126" not in speed_off

    runtime = (ROOT / "guiscripts" / "Psionics.py").read_text(encoding="utf-8")
    for fragment in (
        "BONUS_FEAT_LEVELS = (1, 5, 10, 15, 20)",
        "BONUS_FEAT_SPENT_RESOURCE = \"PSFSPENT\"",
        "SPEED_BLOCK_MARKER = 0x50534642",
        "\"PXFTALT\": \"PXTALST\"",
        "\"PXFBODY\": \"PXBODST\"",
        "\"PXFSPD\": \"PXSPDST\"",
        "state_resource = FEAT_STATE_RESOURCES.get(key)",
        "state_resource = FEAT_STATE_RESOURCES[key]",
        "def bonus_feat_spent(actor):",
        "def _write_bonus_feat_spent(actor, spent):",
        "def bonus_feat_slots(actor):",
        "def bonus_feats_remaining(actor):",
        "bonus_feat_slots(actor) - bonus_feat_spent(actor)",
        "_write_bonus_feat_spent(actor, spent + 1)",
        "def available_feat_choices(actor):",
        "if key == FEAT_SELECTOR_RESOURCE:",
        "return bonus_feats_remaining(actor) > 0",
        "focused = focused or bool(int(effect.get(\"Param1\", 0)))",
        "def _sync_speed_gate(actor, owns_speed=None):",
        "SPEED_BLOCK_MARKER",
        "SPEED_ON_RESOURCE",
        "_sync_speed_gate(actor, owns_speed)",
        "_sync_speed_gate(actor)",
        "PXCNTR.spl itself writes the focus marker and casts PXFSPED",
        "lambda: True",
    ):
        assert fragment in runtime, fragment

    # Center Mind confirmation must neither restore focus nor directly apply the
    # focused movement helper before the speed-9 spell actually resolves.
    center_runtime = runtime[runtime.index('if info["kind"] == "center":') :]
    center_runtime = center_runtime[: center_runtime.index('if info["kind"] == "feat_selector":')]
    assert "_write_focus_state(actor, True)" not in center_runtime
    assert "GemRB.ApplySpell(actor, SPEED_ON_RESOURCE)" not in center_runtime
    assert "_sync_speed_gate(actor)" in center_runtime

    # The serialized feat carriers must never reuse live SPL resource names.
    for live in ("PXFTALT", "PXFBODY", "PXFSPD"):
        assert f'"{live}": "{live}"' not in runtime

    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "psionfeatpick.2da" in setup
    assert "psfsel.2da" in setup
    powers = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    assert "focus-feats.tpa" in powers

    print("Psion resolution-safe focus, immediate focus-passive sync, private feat state, bonus-feat credit, CLAB, and helper-resource validation passed.")


if __name__ == "__main__":
    main()
