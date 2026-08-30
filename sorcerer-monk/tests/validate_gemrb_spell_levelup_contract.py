#!/usr/bin/env python3
"""Validate GemRB's Sorcerer component spell progression at level-up."""

from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def function_block(source: str, name: str, next_name: str) -> str:
    match = re.search(
        rf"def\s+{re.escape(name)}\s*\([^)]*\)\s*:(?P<body>.*?)\ndef\s+{re.escape(next_name)}\s*\(",
        source,
        re.S,
    )
    require(match is not None, f"GemRB spell contract changed: {name} block not found")
    return match.group("body")


def validate_book_detection(source: str) -> None:
    body = function_block(source, "HasSorcererBook", "CannotLearnSlotSpell")
    require(
        re.search(
            r"ClassName\s*=\s*GUICommon\.GetClassRowName\s*\(\s*cls\s*,\s*[\"']class[\"']\s*\)",
            body,
        ) is not None,
        "GemRB no longer resolves Sorcerer-style book metadata from the supplied component class ID",
    )
    require(
        re.search(
            r"SorcererBook\s*=\s*CommonTables\.ClassSkills\.GetValue\s*\(\s*ClassName\s*,\s*[\"']BOOKTYPE[\"']\s*\)",
            body,
        ) is not None,
        "GemRB no longer reads BOOKTYPE from the selected component's CLSKILLS row",
    )
    require(
        re.search(r"return\s+SorcererBook\s+if\s+IsSorcererBook\s*\(\s*SorcererBook\s*\)\s+else\s+0", body) is not None,
        "GemRB no longer returns Sorcerer-style BOOKTYPE semantics for the selected component",
    )


def validate_levelup_slots(source: str) -> None:
    body = function_block(source, "GetNewSpells", "SaveNewSpells")
    require(
        re.search(r"for\s+i\s+in\s+range\s*\(\s*len\s*\(\s*Classes\s*\)\s*\)", body) is not None,
        "GemRB no longer scans each component class for spell progression",
    )
    require(
        re.search(
            r"TmpClassName\s*=\s*GUICommon\.GetClassRowName\s*\(\s*Classes\s*\[\s*i\s*\]\s*,\s*[\"']class[\"']\s*\)",
            body,
        ) is not None,
        "GemRB no longer resolves spell progression from each component class row",
    )
    require(
        re.search(
            r"MageTable\s*=\s*CommonTables\.ClassSkills\.GetValue\s*\(\s*TmpClassName\s*,\s*[\"']MAGESPELL[\"']\s*,\s*GTV_STR\s*\)",
            body,
        ) is not None,
        "GemRB no longer reads MAGESPELL from the Sorcerer component CLSKILLS row",
    )
    require(
        re.search(r"StartLevel\s*=\s*Level\s*\[\s*i\s*\]\s*-\s*LevelDiff\s*\[\s*i\s*\]", body) is not None,
        "GemRB no longer calculates old Sorcerer spell slots from the component level",
    )
    require(
        re.search(r"NewWSpells\s*\[\s*j\s*\]\s*=\s*MageTable\.GetValue\s*\(\s*str\s*\(\s*Level\s*\[\s*i\s*\]\s*\)", body) is not None,
        "GemRB no longer calculates new wizard slots from the Sorcerer component level",
    )


def validate_spontaneous_selection(source: str) -> None:
    body = function_block(source, "OpenLevelUpWindow", "HideSkills")
    require(
        re.search(
            r"Spellbook\.HasSorcererBook\s*\(\s*pc\s*,\s*Classes\s*\[\s*c\s*\]\s*\)\s+and\s+DeltaWSpells\s*>\s*0",
            body,
        ) is not None,
        "GemRB no longer tests Sorcerer-style learning against each component class",
    )
    require(
        re.search(
            r"ClassName\s*=\s*GUICommon\.GetClassRowName\s*\(\s*Classes\s*\[\s*c\s*\]\s*,\s*[\"']class[\"']\s*\)",
            body,
        ) is not None,
        "GemRB no longer resolves the component class before spontaneous spell selection",
    )
    require(
        re.search(
            r"MageTable\s*=\s*CommonTables\.ClassSkills\.GetValue\s*\(\s*ClassName\s*,\s*[\"']MAGESPELL[\"']\s*,\s*GTV_STR\s*\)",
            body,
        ) is not None,
        "GemRB no longer selects the Sorcerer component's MAGESPELL table for learning",
    )
    require(
        re.search(
            r"LUSpellSelection\.OpenSpellsWindow\s*\(\s*pc\s*,\s*MageTable\s*,\s*Level\s*\[\s*c\s*\]\s*,\s*LevelDiff\s*\[\s*c\s*\]\s*\)",
            body,
        ) is not None,
        "GemRB no longer opens spontaneous selection with the Sorcerer component level/delta",
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_gemrb_spell_levelup_contract.py <LevelUp.py> <Spellbook.py>")
    levelup = Path(sys.argv[1]).read_text(encoding="utf-8")
    spellbook = Path(sys.argv[2]).read_text(encoding="utf-8")
    validate_book_detection(spellbook)
    validate_levelup_slots(levelup)
    validate_spontaneous_selection(levelup)
    print("GemRB Sorcerer/Monk spell level-up contract validated")


if __name__ == "__main__":
    main()
