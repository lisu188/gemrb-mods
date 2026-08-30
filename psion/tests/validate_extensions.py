#!/usr/bin/env python3
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
PSION = ROOT / "psion"
COMMON = ROOT / "common"


def main():
    setup = (PSION / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "VERSION ~1.4.0~" in setup
    assert "psion/tables/pscrpick.2da" in setup
    assert "psion/lib/psicrystal.tpa" in setup
    assert "BEGIN ~Psion discipline equipment~" in setup
    assert "DESIGNATED 200" in setup
    assert "psion/lib/equipment.tpa" in setup
    assert "AT_NOW ~python \"psion/tools/generate_learning_proxies.py\"" in setup
    assert "AT_NOW ~python3" not in setup

    wrapper = (PSION / "tools/install_guiscripts.py").read_text(encoding="utf-8")
    assert "Psicrystal.py" in wrapper
    assert "PsionAI.py" in wrapper

    dispatcher = (COMMON / "guiscripts/GemRBModCore.py").read_text(encoding="utf-8")
    assert '"Psicrystal"' in dispatcher
    assert '"Psionics"' in dispatcher

    psicrystal = (PSION / "guiscripts/Psicrystal.py").read_text(encoding="utf-8")
    ast.parse(psicrystal)
    for fragment in (
        "PERSONALITY_MARKER",
        "PersistentState.read",
        "PersistentState.write",
        "available_choices",
        "SUMMON_RESOURCE",
        "manifester_level",
        "restore_party",
    ):
        assert fragment in psicrystal

    crystal_rules = (PSION / "lib/psicrystal.tpa").read_text(encoding="utf-8")
    for resref in ("PXCRYS", "PXCRSM", "PXCRHERO", "PXCRNIMB", "PXCROBSV", "PXCRRESO"):
        assert resref in crystal_rules
    assert "familiar.2da" not in crystal_rules.lower()
    assert "opcode = 67" in crystal_rules

    ai = (PSION / "guiscripts/PsionAI.py").read_text(encoding="utf-8")
    ast.parse(ai)
    for fragment in (
        "OFFENSE_BY_DISCIPLINE",
        "DEFENSE",
        "MOBILITY",
        "Psionics.ensure_pool",
        "Psionics.can_manifest",
        "Psionics._dc_variant_resref",
        "Psionics._write_pool_state",
    ):
        assert fragment in ai

    equipment = (PSION / "lib/equipment.tpa").read_text(encoding="utf-8")
    for index in range(1, 7):
        assert f"PSIITM{index:02d}" in equipment
    for class_id in (
        "ps_seer_id",
        "ps_shaper_id",
        "ps_kineticist_id",
        "ps_egoist_id",
        "ps_nomad_id",
        "ps_telepath_id",
    ):
        assert class_id in equipment
    assert "opcode = 319" in equipment
    assert "parameter2 = 5 power = 1" in equipment
    assert "SetPlayerStat" not in equipment

    fidelity = (PSION / "lib/high-tier-fidelity.tpa").read_text(encoding="utf-8")
    assert "PSFISS01" in fidelity
    assert "opcode = 67" in fidelity
    assert "WRITE_SHORT ps7clib_death 13" in fidelity
    matrix = (PSION / "docs/high-tier-fidelity.md").read_text(encoding="utf-8")
    for level in (6, 7, 8, 9):
        assert f"| {level} |" in matrix

    print("Psion extension validation passed")


if __name__ == "__main__":
    main()
