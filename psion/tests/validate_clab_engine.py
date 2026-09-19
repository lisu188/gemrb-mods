#!/usr/bin/env python3
"""Run GemRB's real class-ability callbacks on source or installed Psion CLABs.

Only table loading and ability delivery are mocked. These public synthetic API
checks establish CLAB orientation/progression, not live campaign acceptance.
"""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "common" / "tests"))
from clab_engine import Table, engine_callbacks

CLABS = ("clabpsee", "clabpsha", "clabpkin", "clabpego", "clabpnom", "clabptel")
UTILITIES = ("PXPLRN", "PXCNTR", "PXFSEL", "PXSKILL")
LEVELS = (1, 2, 3, 17, 30)




def validate(gemrb_root, table_directory):
    files = {path.name.casefold(): path for path in table_directory.iterdir() if path.is_file()}
    tables = {name: Table(files[name + ".2da"]) for name in CLABS}
    delivered, applied = [], []
    engine = engine_callbacks(gemrb_root, tables, delivered, applied)
    expected = [(1, resource, engine["IE_SPELL_TYPE_INNATE"], 0, 1, engine["LS_MEMO"]) for resource in UTILITIES]
    for name in CLABS:
        # Chargen or a fresh high-level actor receives every level-1 utility
        # exactly once, even above the last explicit CLAB level column.
        for level in LEVELS:
            delivered.clear()
            engine["AddClassAbilities"](1, name, Level=level, LevelDiff=level)
            assert delivered == expected, (name, "creation", level, delivered, expected)
            assert not applied, (name, "unexpected applied ability", level, applied)

        # Normal advancement must not grant delayed or duplicate selectors.
        delivered.clear()
        engine["AddClassAbilities"](1, name, Level=1, LevelDiff=1)
        for previous, level in zip(LEVELS, LEVELS[1:]):
            engine["AddClassAbilities"](1, name, Level=level, LevelDiff=level - previous)
            assert delivered == expected, (name, "level-up", previous, level, delivered)
            assert not applied, (name, "unexpected applied ability", previous, level, applied)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gemrb_root", type=Path)
    parser.add_argument("--tables", type=Path, default=ROOT / "tables", help="Source tables or a disposable installed override directory")
    args = parser.parse_args()
    validate(args.gemrb_root.resolve(), args.tables.resolve())
    print("Six Psion CLABs passed actual GemRB ability callbacks at levels 1/2/3/17/30 and incremental advancement (synthetic API coverage only).")


if __name__ == "__main__":
    main()
