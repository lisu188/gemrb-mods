#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
POWERS = ROOT / "psion" / "tables" / "psionpowers.2da"
MATRIX = ROOT / "psion" / "docs" / "high-tier-fidelity.md"


def high_tier_resrefs():
    result = set()
    for line in POWERS.read_text(encoding="utf-8").splitlines()[3:]:
        columns = line.split()
        if len(columns) < 3:
            continue
        if columns[2].isdigit() and 6 <= int(columns[2]) <= 9:
            result.add(columns[0])
    return result


def main():
    matrix = MATRIX.read_text(encoding="utf-8")
    rows = set(re.findall(r"^\| [^|]+ \| (PS[0-9A-Z]+) \|", matrix, re.MULTILINE))
    expected = high_tier_resrefs()
    missing = expected - rows
    stale = rows - expected
    assert not missing, "High-tier fidelity matrix missing powers: " + ", ".join(sorted(missing))
    assert not stale, "High-tier fidelity matrix contains stale powers: " + ", ".join(sorted(stale))
    assert len(rows) == 24, len(rows)
    print("Psion high-tier fidelity matrix covers all 24 level 6-9 powers.")


if __name__ == "__main__":
    main()
