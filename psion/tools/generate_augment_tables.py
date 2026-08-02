#!/usr/bin/env python3
"""Regenerate the Psion augmentation tables.

D&D 3.5 lets a manifester spend up to their manifester level in power points on
a single manifestation, so an augment ladder should run as far as the level cap
rather than stopping at the highest base cost. Writing those ladders by hand is
impractical -- at the current ceiling they come to well over a hundred rows
spread across five tables -- and the rows have to stay consistent with the
selector tables the engine reads and with the WeiDU loops that build the SPL
resources.

This script is the single producer of all of that table data. Change
MAX_AUGMENT_COST here and in power-data.tpa's psion_max_augment_cost, rerun, and
commit the result; validate_core.py asserts the two agree so they cannot drift.

Usage:  python psion/tools/generate_augment_tables.py [--check]

--check regenerates in memory and exits non-zero if any checked-in table
differs, which is what CI uses to prove the committed tables are current.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TABLES = Path(__file__).resolve().parents[1] / "tables"

# Must match psion_max_augment_cost in psion/lib/power-data.tpa.
MAX_AUGMENT_COST = 20

# Energy Ray: one ladder per energy type. Sonic trades a smaller die for the
# rarity of sonic resistance, per the tabletop energy-descriptor rules.
ENERGY_TYPES = [
    ("FIRE", "PSRF"),
    ("COLD", "PSRC"),
    ("ELECTRICITY", "PSRE"),
    ("SONIC", "PSRS"),
]

# Animal Affinity is a mode selector rather than a ladder: each child grants +4
# to one ability at the power's flat base cost. Spending more power points buys
# an additional ability by manifesting again, not a larger bonus.
ANIMAL_AFFINITY = [
    ("STRENGTH", "PSAASTR"),
    ("DEXTERITY", "PSAADEX"),
    ("CONSTITUTION", "PSAACON"),
    ("CHARISMA", "PSAACHA"),
]
ANIMAL_AFFINITY_COST = 3

# Swarm of Crystals is a 2nd-level power, so its ladder starts at its base cost.
SWARM_BASE_COST = 3
SWARM_PREFIX = "PSSC"

VIGOR_PREFIX = "PSVG"
MIND_THRUST_PREFIX = "PSMT"


def resref(prefix: str, cost: int) -> str:
    """Resrefs are zero padded so they sort naturally and stay 8 characters."""
    return f"{prefix}{cost:02d}"


def augment_rows() -> list[tuple[str, str, int, str, str]]:
    """Every augment child as (resref, parent, total_cost, effect, value)."""
    rows: list[tuple[str, str, int, str, str]] = []
    for energy, prefix in ENERGY_TYPES:
        for cost in range(1, MAX_AUGMENT_COST + 1):
            rows.append((resref(prefix, cost), "PS1ERAY", cost, "ENERGY", energy))
    for cost in range(1, MAX_AUGMENT_COST + 1):
        rows.append((resref(MIND_THRUST_PREFIX, cost), "PS1MTHR", cost, "DAMAGE", "MIND"))
    for cost in range(1, MAX_AUGMENT_COST + 1):
        rows.append((resref(VIGOR_PREFIX, cost), "PS1VIGR", cost, "TEMP_HP", "FIVE_PER_PP"))
    for cost in range(SWARM_BASE_COST, MAX_AUGMENT_COST + 1):
        rows.append((resref(SWARM_PREFIX, cost), "PS2SWCR", cost, "DAMAGE", "SHARDS"))
    for ability, child in ANIMAL_AFFINITY:
        rows.append((child, "PS2AAFF", ANIMAL_AFFINITY_COST, "ABILITY", ability))
    return rows


def render(header: list[str], rows: list[list[str]], default: str) -> str:
    """Render a 2DA, padding each column to the widest cell as the hand-written
    tables do. The header line is indented by the row-name column's width."""
    columns = [header] + rows
    widths = [max(len(row[index]) for row in columns) for index in range(len(header))]
    lines = ["2DA V1.0", default]
    lines.append(
        " " * widths[0]
        + " "
        + " ".join(header[index].ljust(widths[index]) for index in range(1, len(header))).rstrip()
    )
    for row in rows:
        lines.append(
            " ".join(row[index].ljust(widths[index]) for index in range(len(header))).rstrip()
        )
    return "\n".join(lines) + "\n"


def build() -> dict[str, str]:
    """Return {filename: contents} for every generated table."""
    rows = augment_rows()

    files = {
        "psionaugment.2da": render(
            ["", "PARENT", "TOTAL_COST", "EFFECT", "VALUE"],
            [[r[0], r[1], str(r[2]), r[3], r[4]] for r in rows],
            "*",
        )
    }

    def selector(rows_in: list[tuple[str, str]]) -> str:
        return render(
            ["", "ResRef", "Type"],
            [[name, child, "3"] for name, child in rows_in],
            "****",
        )

    energy_rows = [
        (f"{energy}_{cost}_PP", resref(prefix, cost))
        for energy, prefix in ENERGY_TYPES
        for cost in range(1, MAX_AUGMENT_COST + 1)
    ]
    files["ps1eray.2da"] = selector(energy_rows)
    files["ps1mthr.2da"] = selector(
        [(f"{c}_PP", resref(MIND_THRUST_PREFIX, c)) for c in range(1, MAX_AUGMENT_COST + 1)]
    )
    files["ps1vigr.2da"] = selector(
        [(f"{c}_PP", resref(VIGOR_PREFIX, c)) for c in range(1, MAX_AUGMENT_COST + 1)]
    )
    files["ps2swcr.2da"] = selector(
        [
            (f"{c}_PP", resref(SWARM_PREFIX, c))
            for c in range(SWARM_BASE_COST, MAX_AUGMENT_COST + 1)
        ]
    )
    files["ps2aaff.2da"] = selector([(ability, child) for ability, child in ANIMAL_AFFINITY])
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the checked-in tables match this generator instead of writing",
    )
    args = parser.parse_args()

    stale = []
    for name, contents in build().items():
        path = TABLES / name
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != contents:
                stale.append(name)
        else:
            path.write_text(contents, encoding="utf-8")

    if args.check:
        if stale:
            print(
                "Augment tables are stale; rerun "
                "psion/tools/generate_augment_tables.py: " + ", ".join(sorted(stale)),
                file=sys.stderr,
            )
            return 1
        print("Psion augment tables are up to date.")
    else:
        print(f"Regenerated Psion augment tables at ceiling {MAX_AUGMENT_COST} PP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
