#!/usr/bin/env python3
"""Verify installed QSLOTS rows for all Psion discipline classes."""

from __future__ import annotations

import sys
from pathlib import Path

DISCIPLINES = (
    "PSION_SEER",
    "PSION_SHAPER",
    "PSION_KINETICIST",
    "PSION_EGOIST",
    "PSION_NOMAD",
    "PSION_TELEPATH",
)

EXPECTED = ["3", "4", "5", "2", "8", "9", "11", "12", "13"]


def casefold_path(path: Path) -> Path:
    if path.exists():
        return path
    matches = [
        candidate
        for candidate in path.parent.iterdir()
        if candidate.name.lower() == path.name.lower()
    ]
    assert len(matches) == 1, (path, matches)
    return matches[0]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_qslots_install.py GAME_ROOT LAYOUT")

    game = Path(sys.argv[1])
    layout = sys.argv[2]
    path = casefold_path(game / "override" / "qslots.2da")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(lines) >= 3 and lines[0].strip().upper() == "2DA V1.0", (layout, path)

    rows: dict[str, list[str]] = {}
    for line in lines[3:]:
        fields = line.split()
        if fields:
            rows[fields[0]] = fields[1:]

    for discipline in DISCIPLINES:
        assert rows.get(discipline) == EXPECTED, (
            layout,
            discipline,
            rows.get(discipline),
            EXPECTED,
        )

    print(f"{layout}: all Psion QSLOTS rows use three quickspells and no stealth slot.")


if __name__ == "__main__":
    main()
