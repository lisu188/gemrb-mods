#!/usr/bin/env python3
"""Validate the upstream GemRB HLA calculation Sorcerer/Monk relies on."""

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
    require(match is not None, f"GemRB HLA contract changed: {name} block not found")
    return match.group("body")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_gemrb_hla_contract.py <LevelUp.py>")

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    body = function_block(source, "OpenLevelUpWindow", "GetNewSpells")

    require(
        re.search(r"for\s+i\s+in\s+range\s*\(\s*NumClasses\s*\)", body) is not None,
        "GemRB no longer calculates HLA eligibility per active component class",
    )
    require(
        re.search(
            r"MultiName\s*=\s*GUICommon\.GetClassRowName\s*\(\s*Classes\s*\[\s*i\s*\]\s*,\s*[\"']class[\"']\s*\)",
            body,
        ) is not None,
        "GemRB no longer resolves each multiclass component name for LUNUMAB lookup",
    )
    require(
        re.search(
            r"MultiName\s*=\s*[\"']MULTI[\"']\s*\+\s*str\s*\(\s*NumClasses\s*\)\s*\+\s*MultiName",
            body,
        ) is not None,
        "GemRB no longer builds MULTI2/MULTI3 component LUNUMAB row names",
    )
    require(
        re.search(
            r"FirstLevel\s*=\s*HLATable\.GetValue\s*\(\s*MultiName\s*,\s*[\"']FIRST_LEVEL[\"']\s*,\s*GTV_INT\s*\)",
            body,
        ) is not None,
        "GemRB no longer takes multiclass HLA thresholds from component LUNUMAB rows",
    )
    require(
        re.search(r"HLACount\s*\+=\s*LevelDiff\s*\[\s*i\s*\]", body) is not None,
        "GemRB no longer accumulates HLA picks from each component's level gains",
    )
    require(
        re.search(
            r"HLACount\s*=\s*HLACount\s*//\s*HLATable\.GetValue\s*\(\s*ClassName\s*,\s*[\"']RATE[\"']\s*,\s*GTV_INT\s*\)",
            body,
        ) is not None,
        "GemRB no longer applies the combined class LUNUMAB RATE to accumulated HLA picks",
    )

    print("GemRB Sorcerer/Monk HLA runtime contract validated")


if __name__ == "__main__":
    main()
