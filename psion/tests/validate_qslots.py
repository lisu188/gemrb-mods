#!/usr/bin/env python3
"""Regression checks for Psion QSLOTS action-bar layout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)

# GemRB PCStatStruct action IDs:
# 3/4/5 = quickspell 1/2/3, 2 = cast, 8 = use, 9/11/12 = quick items,
# 13 = innate. Action 0 is stealth and must never occupy a Psion class slot.
EXPECTED = "3 4 5 2 8 9 11 12 13"


def main() -> None:
    source = (ROOT / "lib" / "class-common.tpa").read_text(encoding="utf-8")
    for discipline in DISCIPLINES:
        expected = f"APPEND ~qslots.2da~ ~{discipline} {EXPECTED}~ UNLESS ~{discipline}~"
        assert expected in source, (discipline, expected)
        assert f"~{discipline} 0 3 4 2 8 9 11 12 13~" not in source, discipline
    print("Psion QSLOTS action-bar validation passed.")


if __name__ == "__main__":
    main()
