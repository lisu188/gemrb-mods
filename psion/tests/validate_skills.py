#!/usr/bin/env python3
"""Static regression checks for persistent Psion skill training."""

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

EXPECTED_SKILL_CHOICES = {
    "CONCENTRATION": "PXSCONC",
    "PSICRAFT": "PXSPSIC",
    "SELF_DISCIPLINE": "PXSSELF",
    "PSIONIC_KNOWLEDGE": "PXSKNOW",
    "DEVICE_LORE": "PXSDEVC",
    "AWARENESS": "PXSAWAR",
    "ECTOPLASMIC_CRAFT": "PXSECTO",
    "ENERGY_LORE": "PXSENRG",
    "HEAL": "PXSHEAL",
    "SPATIAL_NAVIGATION": "PXSSPAT",
    "INFLUENCE": "PXSINFL",
}


def table_rows(name: str) -> list[list[str]]:
    lines = (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines[3:] if line.strip()]


def main() -> None:
    skill_rows = table_rows("psionskills.2da")
    assert {row[0] for row in skill_rows} == set(EXPECTED_SKILL_CHOICES)
    assert len(skill_rows) == 11
    assert all(int(row[3]) == 1 for row in skill_rows), skill_rows
    assert {row[2] for row in skill_rows if row[2] != "CORE"} == {
        "SEER", "SHAPER", "KINETICIST", "EGOIST", "NOMAD", "TELEPATH",
    }

    selector_rows = table_rows("psskill.2da")
    selector = {row[0]: row[1] for row in selector_rows}
    assert selector == EXPECTED_SKILL_CHOICES, selector
    assert all(row[2] == "3" for row in selector_rows)

    for filename in DISCIPLINE_CLABS:
        rows = table_rows(filename)
        level1 = next(row for row in rows if row[0] == "1")
        assert level1.count("GA_PXSKILL") == 1, filename
        for row in rows[1:]:
            assert "GA_PXSKILL" not in row, (filename, row[0])

    builder = (ROOT / "lib" / "skills.tpa").read_text(encoding="utf-8")
    created = set(re.findall(r"ps_resref = ~(PX[A-Z0-9]+)~", builder))
    assert created == {"PXSKILL", *EXPECTED_SKILL_CHOICES.values()}, created
    selector_start = builder.index("ps_resref = ~PXSKILL~")
    selector_end = builder.index("ps_resref = ~PXSCONC~")
    selector_section = builder[selector_start:selector_end]
    assert "opcode = 214" in selector_section
    assert "resource = ~PSSKILL~" in selector_section

    runtime = (ROOT / "guiscripts" / "Psionics.py").read_text(encoding="utf-8")
    for fragment in (
        'SKILL_SELECTOR_RESOURCE = "PXSKILL"',
        "SKILL_POINTS_MARKER = 0x50535350",
        "SKILL_LEVEL_MARKER = 0x5053534C",
        '"CONCENTRATION": 0x50535301',
        '"INFLUENCE": 0x5053530B',
        "def skill_rule_info(skill):",
        "def skill_choice_info(resref):",
        "def skill_rank(actor, skill):",
        "def _base_ability_modifier(actor, ability):",
        "GemRB.GetPlayerStat(actor, stat, 1)",
        'return max(1, 2 + _base_ability_modifier(actor, "INT"))',
        "def skill_rank_cap(actor):",
        "def sync_skill_points(actor):",
        "earned = per_level * (level + 3)",
        "points += per_level * (level - accounted)",
        "def can_train_skill(actor, resref):",
        "def available_skill_choices(actor):",
        "def _ensure_skill_selector_known(actor):",
        "GemRB.LearnSpell(actor, SKILL_SELECTOR_RESOURCE, LS_MEMO)",
        "def _train_skill(actor, resref):",
        "def skill_check_total(actor, skill, roll=None):",
        "def concentration_check(actor, dc=20, roll=None):",
        "lambda: concentration_check(actor, 20)",
        'if info["kind"] == "skill_selector":',
        'if info["kind"] == "skill_choice":',
        "return bool(available_skill_choices(actor))",
        "_ensure_skill_selector_known(actor)",
    ):
        assert fragment in runtime, fragment

    marker_values = [
        0x50535050,
        0x50534643,
        0x50534642,
        0x50534653,
        0x50535350,
        0x5053534C,
        *range(0x50535301, 0x5053530C),
    ]
    assert len(marker_values) == len(set(marker_values))

    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    powers = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    assert "psskill.2da" in setup
    assert "skills.tpa" in powers

    print("Psion skill table, base-INT ledger, migrated selector, serialized ranks, rank-cap, Concentration, CLAB, and installer validation passed.")


if __name__ == "__main__":
    main()
