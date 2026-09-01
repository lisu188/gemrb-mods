#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

MODS = {
    "cipher": ("Cipher", "setup-cipher.tp2"),
    "psion": ("Psion", "setup-psion.tp2"),
    "sorcerer-monk": ("Sorcerer/Monk", "setup-sorcerer-monk.tp2"),
}


def read(path):
    return path.read_text(encoding="utf-8")


def version_from_tp2(path):
    match = re.search(r"(?m)^VERSION\s+~([^~]+)~\s*$", read(path))
    assert match, f"VERSION not found in {path}"
    return match.group(1)


def version_from_readme(path):
    match = re.search(r"\*\*Current version: `([^`]+)`\*\*", read(path))
    assert match, f"Current version marker not found in {path}"
    return match.group(1)


def validate_versions():
    compatibility = read(ROOT / "docs" / "compatibility.md")
    top_readme = read(ROOT / "README.md")
    for folder, (display, tp2_name) in MODS.items():
        version = version_from_tp2(ROOT / folder / tp2_name)
        documented = version_from_readme(ROOT / folder / "README.md")
        assert documented == version, f"{folder}: README {documented} != TP2 {version}"
        assert f"| {display} | {version} |" in compatibility, f"{folder}: compatibility matrix version drift"
        assert version in top_readme, f"{folder}: top-level release overview missing {version}"


def validate_psion_current_docs():
    readme = read(ROOT / "psion" / "README.md")
    changelog = read(ROOT / "psion" / "CHANGELOG.md")
    current = changelog.split("## 1.0.0", 1)[0]

    stale = (
        "Version 1.0.0 is the first merged release",
        "extends the fixed class progression",
        "Intelligence above 15 currently increases bonus PP",
        "player-selected power learning, psicrystals",
        "cannot yet dynamically alter an installed SPL's save bonus",
    )
    for phrase in stale:
        assert phrase not in readme, f"stale Psion README assertion: {phrase}"
        assert phrase not in current, f"stale Psion current changelog assertion: {phrase}"

    required_readme = (
        "player-selected powers known",
        "Psionics.prepare_action_entry()",
        "GemRB.PrepareSpontaneousCast()",
        "psionknown.2da` defines how many powers",
    )
    for phrase in required_readme:
        assert phrase in readme, f"missing Psion README fact: {phrase}"

    required_changelog = (
        "player-selected learning",
        "exact current-Intelligence save-DC substitution",
    )
    for phrase in required_changelog:
        assert phrase in current, f"missing Psion changelog fact: {phrase}"


def validate_acceptance_language():
    compatibility = read(ROOT / "docs" / "compatibility.md")
    sm_readme = read(ROOT / "sorcerer-monk" / "README.md")
    assert "live campaign qualification pending in #51" in compatibility
    assert "full live GemRB campaign qualification is tracked separately in #51" in sm_readme
    assert "real-engine cross-mod acceptance gate is tracked in #50" in read(ROOT / "psion" / "README.md")
    assert "real-engine cross-mod acceptance suite is tracked separately in #50" in read(ROOT / "cipher" / "README.md")


def main():
    validate_versions()
    validate_psion_current_docs()
    validate_acceptance_language()
    print("Release metadata validation passed.")


if __name__ == "__main__":
    main()
