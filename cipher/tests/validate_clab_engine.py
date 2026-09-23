#!/usr/bin/env python3
"""Check Cipher grants through real GemRB callbacks with synthetic engine APIs."""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "common" / "tests"))
from clab_engine import Table, engine_callbacks

LEVELS = (1, 2, 3, 9, 10, 19, 20, 30)


def expected_passives(level):
    resources = ["CIFCORE"]
    if level >= 10:
        resources.append("CIFSW15")
    if level >= 20:
        resources.append("CIFSW20")
    return [(1, resource) for resource in resources]


def validate(gemrb_root, table_directory):
    path = next(path for path in table_directory.iterdir() if path.name.casefold() == "clabciph.2da")
    delivered, applied = [], []
    engine = engine_callbacks(gemrb_root, {"clabciph": Table(path)}, delivered, applied)
    selector = [
        (1, "CILRN", engine["IE_SPELL_TYPE_INNATE"], 0, 1, engine["LS_MEMO"]),
        (1, "CISUB", engine["IE_SPELL_TYPE_INNATE"], 0, 1, engine["LS_MEMO"]),
    ]
    for level in LEVELS:
        delivered.clear()
        applied.clear()
        engine["AddClassAbilities"](1, "clabciph", Level=level, LevelDiff=level)
        assert delivered == selector, ("creation", level, "learning selector", delivered)
        assert applied == expected_passives(level), ("creation", level, "Soul Whip", applied)

    delivered.clear()
    applied.clear()
    engine["AddClassAbilities"](1, "clabciph", Level=1, LevelDiff=1)
    for previous, level in zip(LEVELS, LEVELS[1:]):
        engine["AddClassAbilities"](1, "clabciph", Level=level, LevelDiff=level - previous)
        assert delivered == selector, ("level-up", previous, level, "duplicate selector", delivered)
        assert applied == expected_passives(level), ("level-up", previous, level, "Soul Whip", applied)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gemrb_root", type=Path)
    parser.add_argument("--tables", type=Path, default=ROOT / "tables", help="Source tables or a disposable installed override directory")
    args = parser.parse_args()
    validate(args.gemrb_root.resolve(), args.tables.resolve())
    print("Cipher CLAB passed actual GemRB callbacks: level-1 learning/subclass/core, Soul Whip upgrades at 10/20, and level-30 cap (synthetic API coverage only).")


if __name__ == "__main__":
    main()
