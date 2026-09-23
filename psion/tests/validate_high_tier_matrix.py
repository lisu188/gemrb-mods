#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "psion" / "README.md"
MATRIX = ROOT / "psion" / "docs" / "high-tier-fidelity.md"


def approximation_names(text):
    marker = "## High-level portable approximations"
    section = text.split(marker, 1)[1]
    section = section.split("\n## ", 1)[0]
    names = []
    for line in section.splitlines():
        if not line.startswith("- "):
            continue
        name = line[2:].split(" expresses ", 1)[0]
        name = name.split(" deals ", 1)[0]
        name = name.split(" and Greater", 1)[0] if name.startswith("Fusion and Greater") else name
        if line.startswith("- Fusion and Greater Metamorphosis"):
            names.extend(["Fusion", "Greater Metamorphosis"])
        elif line.startswith("- Mass Time Hop"):
            names.append("Time Hop, Mass")
        elif line.startswith("- Teleportation Circle"):
            names.append("Teleportation Circle (Psionic)")
        elif line.startswith("- Psychic Chirurgery"):
            names.append("Psychic Chirurgery")
        else:
            names.append(name)
    return names


def main():
    readme = README.read_text(encoding="utf-8")
    matrix = MATRIX.read_text(encoding="utf-8")
    expected = set(approximation_names(readme))
    rows = set(re.findall(r"^\| ([^|]+?) \| PS[0-9A-Z]+ \|", matrix, re.MULTILINE))
    missing = expected - rows
    assert not missing, "High-tier fidelity matrix missing README approximations: " + ", ".join(sorted(missing))
    assert rows == expected, "Matrix contains stale/untracked rows: " + ", ".join(sorted(rows - expected))
    print("Psion high-tier fidelity matrix matches README approximations.")


if __name__ == "__main__":
    main()
