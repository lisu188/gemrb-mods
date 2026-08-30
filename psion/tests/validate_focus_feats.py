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
        ["PXFTALT", "PSIONIC_TALENT", "1", "0", "1", "****", "0"],
        ["PXFBODY", "PSIONIC_BODY", "1", "0", "0", "****", "0"],
        ["PXFSPD", "SPEED_OF_THOUGHT", "1", "13", "0", "****", "0"],
        ["PXFMEDI", "PSIONIC_MEDITATION", "1", "13", "0", "CONCENTRATION", "7"],
    ], feat_rows

    selector_rows = table_rows("psfsel.2da")
    assert selector_rows == [
        ["PSIONIC_TALENT", "PXFTALT", "3"],
        ["PSIONIC_BODY", "PXFBODY", "3"],
        ["SPEED_OF_THOUGHT", "PXFSPD", "3"],
        ["PSIONIC_MEDITATION", "PXFMEDI", "3"],
    ], selector_rows

    for filename in DISCIPLINE_CLABS:
        text = (ROOT / "tables" / filename).read_text(encoding="utf-8")
        rows = table_rows(filename)
        level1 = next(row for row in rows if row[0] == "1")
        assert level1.count("GA_PXPLRN") == 1, filename
        assert level1.count("GA_PXCNTR") == 1, filename
        assert level1.count("GA_PXFSEL") == 1, filename
        assert text.count("GA_PXPLRN") == 1, filename
        assert text.count("GA_PXCNTR") == 1, filename
        assert text.count("GA_PXFSEL") == 1, filename
        for level in ("5", "10", "15", "20"):
            row = next(row for row in rows if row[0] == level)
            assert "GA_PXFSEL" not in row, (filename, level)

    builder = (ROOT / "lib" / "focus-feats.tpa").read_text(encoding="utf-8")
    created = set(re.findall(r"ps_resref = ~(PX[A-Z0-9]+)~", builder))
    assert created == {
        "PXCNTR",
        "PXCMEDI",
        "PXPLRN",
        "PXFSEL",
        "PXFTALT",
        "PXFBODY",
        "PXFSPD",
        "PXFMEDI",
        "PXFSPED",
        "PXFSPOF",
    }, created

    for resref, speed in (("PXCNTR", "9"), ("PXCMEDI", "5")):
        center = section(builder, resref)
        for fragment in (
            f"ps_speed = {speed}",
            "opcode = 206",
            "parameter1 = 1",
            "parameter2 = psion_focus_state_marker",
            "timing = 9",
            "resource = ~PSFOCUS~",
            "opcode = 146",
            "parameter2 = 1",
            "resource = ~PXFSPED~",
        ):
            assert fragment in center, (resref, fragment)
    assert "psion_focus_state_marker = 0x50534643" in builder

    meditation = section(builder, "PXFMEDI")
    assert "Psionic Meditation" in meditation
    assert "Wisdom 13" in meditation
    assert "7 ranks in Concentration" in meditation

    selector = section(builder, "PXFSEL")
    assert "opcode = 214" in selector
    assert "resource = ~PSFSEL~" in selector

    power_selector = section(builder, "PXPLRN")
    assert "opcode = 214" in power_selector
    assert "resource = ~PSPICK~" in power_selector

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
        "from ie_spells import LS_MEMO",
        'MEDITATION_CENTER_RESOURCE = "PXCMEDI"',
        'PSIONIC_MEDITATION = "PXFMEDI"',
        '"PXFMEDI": 0x50534604',
        '"PXFMEDI": "PXMEDST"',
        'skill = str(table.GetValue(key, "SKILL")).upper()',
        '"rank": int(table.GetValue(key, "RANK"))',
        'if info["skill"] and skill_rank(actor, info["skill"]) < info["rank"]:',
        "def _center_resource_for_actor(actor):",
        "def _sync_center_action(actor):",
        "GemRB.RemoveSpell(actor, unwanted)",
        "GemRB.LearnSpell(actor, wanted, LS_MEMO)",
        'if info["resref"] == PSIONIC_MEDITATION:',
        "if current == 0 and is_psion(actor):",
        "_write_focus_state(actor, False)",
        "if ensure_pool(actor) <= 0:",
        "key == _center_resource_for_actor(actor)",
        "and ensure_pool(actor) > 0",
        "lambda: concentration_check(actor, 20)",
    ):
        assert fragment in runtime, fragment

    # Neither normal nor Meditation Center confirmation may write focus or apply
    # the focused movement helper before the chosen SPL actually resolves.
    center_runtime = runtime[runtime.index('if info["kind"] == "center":') :]
    center_runtime = center_runtime[: center_runtime.index('if info["kind"] == "feat_selector":')]
    assert "_write_focus_state(actor, True)" not in center_runtime
    assert "GemRB.ApplySpell(actor, SPEED_ON_RESOURCE)" not in center_runtime
    assert "concentration_check(actor, 20)" in center_runtime
    assert "ensure_pool(actor) > 0" in center_runtime

    for live in ("PXFTALT", "PXFBODY", "PXFSPD", "PXFMEDI"):
        assert f'"{live}": "{live}"' not in runtime

    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "psionfeatpick.2da" in setup
    assert "psfsel.2da" in setup
    assert "pspick.2da" in setup
    powers = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    assert "focus-feats.tpa" in powers

    print("Psion Meditation prerequisites, move-action Center swap, zero-PP focus loss, resolution-safe focus, and private feat-state validation passed.")


if __name__ == "__main__":
    main()
