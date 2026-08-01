#!/usr/bin/env python3
"""Semantic validation for installed SAVEPSI and Psion class save references."""

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

EXPECTED_LEVELS = {
    "normalized": 20,
    "native": 41,
    "legacy": 40,
}


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


def read_2da(path: Path) -> tuple[list[str], list[list[str]]]:
    path = casefold_path(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(lines) >= 3 and lines[0].strip().upper() == "2DA V1.0", path
    columns = lines[2].split()
    rows: list[list[str]] = []
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        rows.append(stripped.split())
    return columns, rows


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_save_install.py GAME_ROOT LAYOUT")

    root = Path(sys.argv[1]) / "override"
    layout = sys.argv[2]
    expected_levels = EXPECTED_LEVELS[layout]

    wizard_columns, wizard_rows = read_2da(root / "savewiz.2da")
    psion_columns, psion_rows = read_2da(root / "savepsi.2da")

    assert len(wizard_columns) == expected_levels, (
        layout,
        len(wizard_columns),
        expected_levels,
    )
    assert psion_columns == wizard_columns, (layout, psion_columns, wizard_columns)
    assert len(wizard_rows) == len(psion_rows) == 5, (
        layout,
        len(wizard_rows),
        len(psion_rows),
    )

    for row_index, (wizard, psion) in enumerate(zip(wizard_rows, psion_rows)):
        assert psion[0] == wizard[0], (layout, row_index, wizard[0], psion[0])
        assert len(psion) == len(wizard) == expected_levels + 1
        for column_index, (wizard_value, psion_value) in enumerate(
            zip(wizard[1:], psion[1:]),
            start=1,
        ):
            expected = int(wizard_value) - 2 if row_index in (1, 4) else int(wizard_value)
            assert int(psion_value) == expected, (
                layout,
                row_index,
                column_index,
                wizard_value,
                psion_value,
                expected,
            )

    class_columns, class_rows = read_2da(root / "classes.2da")
    assert "SAVE" in class_columns, (layout, class_columns)
    save_column = class_columns.index("SAVE")
    class_map = {row[0]: row[1:] for row in class_rows}
    for discipline in DISCIPLINES:
        assert discipline in class_map, (layout, discipline)
        assert class_map[discipline][save_column].upper() == "SAVEPSI", (
            layout,
            discipline,
            class_map[discipline][save_column],
        )

    print(
        f"Psion {layout} SAVEPSI matches Mage saves with -2 wand/spell bonuses."
    )


if __name__ == "__main__":
    main()
