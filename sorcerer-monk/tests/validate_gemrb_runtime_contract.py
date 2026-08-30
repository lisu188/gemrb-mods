#!/usr/bin/env python3
"""Validate the upstream GemRB invariants Sorcerer/Monk depends on.

This is intentionally a source-contract test, not a substitute for an in-game
smoke test. It catches upstream changes to BG class slots, multiclass identity
and XP splitting, component CLAB/fist levels, or Sorcerer spellbook/caster-level
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
    require("GetMonkLevel()" in setup, "GemRB SetupFist no longer consults the Monk component level")
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
        re.search(r"case\s+2\s*:.*?sorcerer\s*=\s*1\s*<<\s*IE_SPELL_TYPE_WIZARD\s*;", change, re.S) is not None,
        "GemRB BOOKTYPE=2 no longer enables the wizard Sorcerer-style spellbook",
    )
    require(
        re.search(r"spellbook\.SetBookType\s*\(\s*sorcerer\s*\)\s*;", change) is not None,
        "GemRB no longer commits the derived Sorcerer-style spellbook type",
    )


def validate_sorcerer_caster_level(source: str) -> None:
    caster = block(
        source,
        r"ieDword\s+Actor::GetBaseCasterLevel\s*\([^)]*\)\s*const\s*\{",
        r"\n\}\n\nint\s+Actor::GetWildMod",
        "Actor::GetBaseCasterLevel",
    )
    wizard = re.search(
        r"case\s+IE_SPL_WIZARD\s*:(?P<body>.*?)\bbreak\s*;",
        caster,
        re.S,
    )
    require(wizard is not None, "GemRB wizard caster-level branch not found")
    require(
        re.search(r"level\s*=\s*GetMageLevel\s*\(\s*\)\s*;", wizard.group("body")) is not None,
        "GemRB wizard caster-level lookup no longer starts with Mage",
    )
    require(
        re.search(r"if\s*\(\s*!level\s*\)\s*level\s*=\s*GetSorcererLevel\s*\(\s*\)\s*;", wizard.group("body")) is not None,
        "GemRB wizard caster-level lookup no longer falls through to the Sorcerer component level",
    )


def validate_multiclass_identity(source: str) -> None:
    has_bits = block(
        source,
        r"def\s+HasMultiClassBits\s*\([^)]*\)\s*:",
        r"\ndef\s+IsDualClassed\s*\(",
        "GUICommon.HasMultiClassBits",
    )
    require(
        re.search(r"GetValue\s*\(\s*GetClassRowName\s*\(\s*actor\s*\)\s*,\s*[\"']MULTI[\"']", has_bits) is not None,
        "GemRB no longer reads multiclass component bits from the active class MULTI field",
    )

    is_multi = block(
        source,
        r"def\s+IsMultiClassed\s*\([^)]*\)\s*:",
        r"\ndef\s+IsNamelessOne\s*\(",
        "GUICommon.IsMultiClassed",
    )
    require(
        re.search(r"ClassNames\s*=\s*GetClassRowName\s*\(\s*actor\s*\)\.split\s*\(\s*[\"']_[\"']\s*\)", is_multi) is not None,
        "GemRB no longer orders multiclass components from the active class row name",
    )
    require(
        re.search(r"if\s+IsMulti\s*&\s*Mask\s*==\s*0", is_multi) is not None,
        "GemRB no longer expands the active class MULTI bitmask",
    )
    require(
        re.search(r"Classes\s*\[\s*j\s*\]\s*=\s*i", is_multi) is not None,
        "GemRB no longer maps MULTI bits back to component class IDs",
    )


def validate_multiclass_xp(source: str) -> None:
    next_exp = block(
        source,
        r"def\s+GetNextLevelExp\s*\([^)]*\)\s*:",
        r"\ndef\s+GetNextLevels\s*\(",
        "LUCommon.GetNextLevelExp",
    )
    require(
        re.search(r"CommonTables\.NextLevel\.GetRowIndex\s*\(\s*Class\s*\)", next_exp) is not None,
        "GemRB no longer resolves next-level XP from the component class XPLEVEL row",
    )

    next_levels = block(
        source,
        r"def\s+GetNextLevels\s*\([^)]*\)\s*:",
        r"\ndef\s+GetLevelDiff\s*\(",
        "LUCommon.GetNextLevels",
    )
    require(
        re.search(r"NumClasses\s*=\s*len\s*\(\s*\[x\s+for\s+x\s+in\s+Classes\s+if\s+x\s*>\s*0\]\s*\)", next_levels) is not None,
        "GemRB no longer counts active multiclass components before splitting XP",
    )
    require(
        re.search(r"IE_XP\s*\)\s*//\s*NumClasses\s*,\s*Classes\s*\[\s*i\s*\]", next_levels) is not None,
        "GemRB no longer divides total XP evenly and advances each component independently",
    )

    can_level = block(
        source,
        r"def\s+CanLevelUp\s*\([^)]*\)\s*:",
        r"\ndef\s+GetAllClasses\s*\(",
        "LUCommon.CanLevelUp",
    )
    require(
        re.search(r"xp\s*=\s*xp\s*//\s*Multi\s*\[\s*0\s*\]", can_level) is not None,
        "GemRB no longer divides multiclass XP by the number of components for level-up eligibility",
    )
    require(
        re.search(r"GetClassRowName\s*\(\s*Multi\s*\[\s*i\s*\+\s*1\s*\]\s*,\s*[\"']class[\"']\s*\)", can_level) is not None,
        "GemRB no longer resolves each multiclass component's class row during level-up",
    )
    require(
        re.search(r"GetNextLevelExp\s*\(\s*Levels\s*\[\s*i\s*\]\s*,\s*TmpClassName\s*\)", can_level) is not None,
        "GemRB no longer checks each component against its own XPLEVEL progression",
    )


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: validate_gemrb_runtime_contract.py <Actor.cpp> <GUICommon.py> <LUCommon.py>"
        )
    actor = Path(sys.argv[1]).read_text(encoding="utf-8")
    gui_common = Path(sys.argv[2]).read_text(encoding="utf-8")
    lu_common = Path(sys.argv[3]).read_text(encoding="utf-8")

    validate_level_slots(actor)
    validate_multiclass_clabs(actor)
    validate_monk_fists(actor)
    validate_sorcerer_book(actor)
    validate_sorcerer_caster_level(actor)
    validate_multiclass_identity(gui_common)
    validate_multiclass_xp(lu_common)
    print("GemRB Sorcerer/Monk runtime contract validated")


if __name__ == "__main__":
    main()
