#!/usr/bin/env python3
"""Validate the upstream GemRB invariants Sorcerer/Monk depends on.

This is intentionally a source-contract test, not a substitute for an in-game
smoke test. It catches upstream changes to the hardcoded BG class-level mapping,
multiclass CLAB level lookup, Monk fist level lookup, or Sorcerer-style book
selection before they silently invalidate the installer assumptions.
"""

from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def block(source: str, start_pattern: str, end_pattern: str, label: str) -> str:
    start = re.search(start_pattern, source, re.S)
    require(start is not None, f"GemRB runtime contract changed: {label} start not found")
    end = re.search(end_pattern, source[start.end():], re.S)
    require(end is not None, f"GemRB runtime contract changed: {label} end not found")
    return source[start.start(): start.end() + end.end()]


def validate_level_slots(source: str) -> None:
    match = re.search(
        r"static\s+const\s+std::array<int,\s*23>\s+levelslotsbg\s*=\s*\{(?P<body>.*?)\};",
        source,
        re.S,
    )
    require(match is not None, "GemRB runtime contract changed: levelslotsbg not found")
    tokens = re.findall(r"\b(?:IS[A-Z0-9_]+|0)\b", match.group("body"))
    require(len(tokens) == 23, f"GemRB runtime contract changed: levelslotsbg has {len(tokens)} entries")
    require(tokens[19] == "ISSORCERER", f"BG class slot 19 is now {tokens[19]}, expected ISSORCERER")
    require(tokens[20] == "ISMONK", f"BG class slot 20 is now {tokens[20]}, expected ISMONK")


def validate_multiclass_clabs(source: str) -> None:
    apply_kit = block(
        source,
        r"bool\s+Actor::ApplyKit\s*\([^)]*\)\s*\{",
        r"\n\}\n\nvoid\s+Actor::ApplyClab",
        "Actor::ApplyKit",
    )
    multi = re.search(
        r"if\s*\(multiclass\)\s*\{(?P<body>.*?)\n\s*return\s+true\s*;\s*\n\s*\}",
        apply_kit,
        re.S,
    )
    require(multi is not None, "GemRB runtime contract changed: ApplyKit multiclass branch not found")
    body = multi.group("body")
    require(
        re.search(r"max\s*=\s*GetLevelInClass\s*\(\s*i\s*\)\s*;", body) is not None,
        "GemRB no longer derives multiclass CLAB level from GetLevelInClass(i)",
    )
    require(
        re.search(r"ApplyClab\s*\(\s*class2kits\s*\[\s*i\s*\]\.clab\s*,\s*max\b", body) is not None,
        "GemRB no longer applies component CLABs with the component-specific level",
    )


def validate_monk_fists(source: str) -> None:
    setup = block(
        source,
        r"void\s+Actor::SetupFist\s*\([^)]*\)\s*\{",
        r"\n\}",
        "Actor::SetupFist",
    )
    require(
        "GetMonkLevel()" in setup,
        "GemRB SetupFist no longer consults the Monk component level",
    )
    require(
        re.search(r"if\s*\(\s*monkLevel\s*\)\s*col\s*=\s*monkLevel\s*;", setup) is not None,
        "GemRB SetupFist no longer overrides multiclass fist lookup with Monk level",
    )


def validate_sorcerer_book(source: str) -> None:
    pcf_class = block(
        source,
        r"static\s+void\s+pcf_class\s*\([^)]*\)\s*\{",
        r"\n\}",
        "pcf_class",
    )
    require(
        re.search(r"ChangeSorcererType\s*\(\s*newValue\s*\)\s*;", pcf_class) is not None,
        "GemRB no longer refreshes the Sorcerer-style book from the active class",
    )

    change = block(
        source,
        r"void\s+Actor::ChangeSorcererType\s*\([^)]*\)\s*\{",
        r"\n\}",
        "Actor::ChangeSorcererType",
    )
    require(
        re.search(r"switch\s*\(\s*bookTypes\s*\[\s*classIdx\s*\]\s*\)", change) is not None,
        "GemRB no longer derives spontaneous casting from the active class BOOKTYPE",
    )
    require(
        re.search(
            r"case\s+2\s*:.*?sorcerer\s*=\s*1\s*<<\s*IE_SPELL_TYPE_WIZARD\s*;",
            change,
            re.S,
        ) is not None,
        "GemRB BOOKTYPE=2 no longer enables the wizard Sorcerer-style spellbook",
    )
    require(
        re.search(r"spellbook\.SetBookType\s*\(\s*sorcerer\s*\)\s*;", change) is not None,
        "GemRB no longer commits the derived Sorcerer-style spellbook type",
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_gemrb_runtime_contract.py <Actor.cpp>")
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    validate_level_slots(source)
    validate_multiclass_clabs(source)
    validate_monk_fists(source)
    validate_sorcerer_book(source)
    print("GemRB Sorcerer/Monk runtime contract validated")


if __name__ == "__main__":
    main()
