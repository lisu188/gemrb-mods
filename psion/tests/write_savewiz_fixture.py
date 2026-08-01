#!/usr/bin/env python3
"""Write a deterministic SAVEWIZ.2DA for real-WeiDU fixture lifecycles."""

from __future__ import annotations

import sys
from pathlib import Path

LEVELS = {
    "normalized": 20,
    "native": 41,
    "legacy": 40,
}

ROW_BASES = (
    ("DEATH", 18),
    ("WANDS", 17),
    ("POLYMORPH", 16),
    ("BREATH", 15),
    ("SPELL", 14),
)


def progression(base: int, level_count: int) -> tuple[str, ...]:
    # Keep every value positive even after the Psion's -2 bonus while making
    # columns vary enough to catch accidental constant-row or width bugs.
    return tuple(
        str(max(4, base - ((level - 1) // 5)))
        for level in range(1, level_count + 1)
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: write_savewiz_fixture.py OUTPUT LAYOUT")

    output = Path(sys.argv[1])
    layout = sys.argv[2]
    if layout not in LEVELS:
        raise SystemExit(f"unsupported layout: {layout}")

    level_count = LEVELS[layout]
    columns = tuple(str(level) for level in range(1, level_count + 1))
    rows = tuple(
        (name, *progression(base, level_count))
        for name, base in ROW_BASES
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["2DA V1.0", "0", "        " + " ".join(columns)]
    lines.extend(" ".join(row) for row in rows)
    output.write_text("\n".join(lines) + "\n", encoding="ascii")

    print(
        f"Wrote {layout} SAVEWIZ fixture with five rows and {level_count} level columns"
    )


if __name__ == "__main__":
    main()
