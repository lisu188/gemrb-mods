#!/usr/bin/env python3
"""Seed a deterministic SAVEWIZ.2DA into the pinned GemRB fixture tree.

GemRB's unhardcoded BG2 data references SAVEWIZ from CLASSES.2DA but does not
ship the original game table. The Psion installer legitimately clones that
campaign resource, so CI supplies a non-proprietary stand-in only inside the
vendor fixture checkout.
"""

from pathlib import Path
import sys


def main() -> None:
    root = Path(sys.argv[1])
    target = root / "gemrb" / "unhardcoded" / "shared" / "savewiz.2da"
    target.parent.mkdir(parents=True, exist_ok=True)

    levels = 41
    columns = [str(level) for level in range(1, levels + 1)]
    starts = [14, 12, 13, 15, 11]
    rows = []
    for row, start in enumerate(starts):
        values = [str(max(1, start - min((level - 1) // 4, 8))) for level in range(1, levels + 1)]
        rows.append(f"{row} " + " ".join(values))

    target.write_text(
        "2DA V1.0\n20\n        " + " ".join(columns) + "\n" + "\n".join(rows) + "\n",
        encoding="ascii",
    )
    print(f"Seeded {target} with {levels} saving-throw columns")


if __name__ == "__main__":
    main()
