#!/usr/bin/env python3
"""Install or remove documented GemRB GUI hooks for the Psion subsystem.

The patcher modifies four shared scripts and stores byte-for-byte backups:
ActionsWindow handles PP transactions and reusable Psion innate charges,
Spellbook filters augmentation choices, and MenuWindow/GUISTORE restore PP after
ordinary and temple resting. It also installs the standalone Psionics runtime
module into the selected GemRB GUIScripts directory.
"""
from pathlib import Path
import argparse
import re
import shutil

MARK_BEGIN = "# PSION MOD BEGIN"
MARK_END = "# PSION MOD END"


def _insert_import(text: str, path: Path) -> str:
    if "import Psionics\n" in text:
        return text
    needle = "import GemRB\n"
    if needle not in text:
        raise RuntimeError(f"{path.name} GemRB import not found")
    return text.replace(needle, needle + "import Psionics\n", 1)


def _patch_spell_pressed(text: str) -> str:
    needle = 'pc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")'
    hook = (
        'pc = GemRB.GameGetFirstSelectedActor ()\n\n'
        '\t' + MARK_BEGIN + '\n'
        '\t# Resolve the selected power from the encoded spell token. GemRB calls\n'
        '\t# SpellPressed twice: reserve on the first call and commit on the second.\n'
        '\ttry:\n'
        '\t\traw_spell = GemRB.GetVar("Spell")\n'
        '\t\tentry = Psionics.resolve_power_entry(Spellbook, pc, raw_spell)\n'
        '\t\tif entry and not Psionics.begin_manifest(pc, entry["SpellResRef"]):\n'
        '\t\t\treturn\n'
        '\texcept Exception as error:\n'
        '\t\tGemRB.Log(2, "Psionics", str(error))\n'
        '\t' + MARK_END + '\n\n'
        '\tSpell = GemRB.GetVar ("Spell")'
    )
    if needle not in text:
        raise RuntimeError("ActionsWindow.py SpellPressed layout not recognized")
    return text.replace(needle, hook, 1)


def _patch_cancel_on_open(text: str, function_name: str, action_constant: str) -> str:
    doc = (
        '\t"""Opens the spell choice scrollbar."""\n\n'
        if function_name == "ActionCastPressed"
        else '\t"""Opens the innate spell scrollbar."""\n\n'
    )
    needle = (
        f'def {function_name} ():\n'
        + doc
        + '\tif GemRB.GetVar ("SettingButtons"):\n'
        + f'\t\tSaveActionButton ({action_constant})\n'
        + '\t\treturn\n\n'
        + '\tGemRB.SetVar ("QSpell", None)'
    )
    before_qspell = '\tPsionics.cancel_pending(GemRB.GameGetFirstSelectedActor ())\n'
    if function_name == "ActionInnatePressed":
        before_qspell += '\tPsionics.refresh_innate_charges(GemRB.GameGetFirstSelectedActor ())\n'
    replacement = needle.replace(
        '\tGemRB.SetVar ("QSpell", None)',
        before_qspell + '\tGemRB.SetVar ("QSpell", None)',
    )
    if needle not in text:
        raise RuntimeError(f"ActionsWindow.py {function_name} layout not recognized")
    return text.replace(needle, replacement, 1)


def _patch_spellinfo_filter(text: str) -> str:
    """Filter only Psion augmentation children in temporary spell selectors."""
    needle = (
        'def GetSpellinfoSpells(actor, BookType):\n'
        '\tmemorizedSpells = []\n'
        '\tspellResRefs = GemRB.GetSpelldata (actor)\n'
    )
    replacement = (
        needle
        + '\t' + MARK_BEGIN + '\n'
        + '\t# Preserve unrelated opcode-214 selectors; Psionics filters only\n'
        + '\t# resources registered as augmentation children.\n'
        + '\tspellResRefs = Psionics.filter_spellinfo(actor, spellResRefs)\n'
        + '\t' + MARK_END + '\n'
    )
    if needle not in text:
        raise RuntimeError("Spellbook.py GetSpellinfoSpells layout not recognized")
    return text.replace(needle, replacement, 1)


def _patch_rest(text: str, path: Path) -> str:
    match = re.search(r"(?m)^([ \t]*)(GemRB\.RestParty\([^\n]*\)\n)", text)
    if not match:
        raise RuntimeError(f"{path.name} rest call not found")
    indent = match.group(1)
    hook = (
        indent + match.group(2)
        + indent + MARK_BEGIN + "\n"
        + indent + "Psionics.restore_party()\n"
        + indent + MARK_END + "\n"
    )
    return text[: match.start()] + hook + text[match.end() :]


def render_patch(text: str, kind: str, path: Path) -> str | None:
    """Render one patch without mutating the target file."""
    if MARK_BEGIN in text:
        return None

    text = _insert_import(text, path)
    if kind == "actions":
        text = _patch_spell_pressed(text)
        text = _patch_cancel_on_open(text, "ActionCastPressed", "ACT_CAST")
        text = _patch_cancel_on_open(text, "ActionInnatePressed", "ACT_INNATE")
    elif kind == "spellbook":
        text = _patch_spellinfo_filter(text)
    elif kind == "rest":
        text = _patch_rest(text, path)
    else:
        raise ValueError(f"Unknown patch kind: {kind}")
    return text


def apply_patch(path: Path, rendered: str | None) -> bool:
    """Write a preflighted patch and preserve the original bytes once."""
    if rendered is None:
        return False
    backup = path.with_suffix(path.suffix + ".psion.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(rendered, encoding="utf-8")
    return True


def patch(path: Path, kind: str) -> bool:
    rendered = render_patch(path.read_text(encoding="utf-8"), kind, path)
    return apply_patch(path, rendered)


def remove(path: Path) -> bool:
    backup = path.with_suffix(path.suffix + ".psion.bak")
    if backup.exists():
        shutil.copy2(backup, path)
        backup.unlink()
        return True
    return False


def _runtime_paths(target: Path) -> tuple[Path, Path]:
    return (
        target.with_suffix(target.suffix + ".psion.bak"),
        target.with_suffix(target.suffix + ".psion.created"),
    )


def install_runtime(source: Path, target: Path) -> bool:
    """Install Psionics.py while preserving any pre-existing module."""
    if not source.is_file():
        raise RuntimeError(f"Missing Psion runtime source {source}")

    backup, created = _runtime_paths(target)
    source_bytes = source.read_bytes()
    if target.is_file() and target.read_bytes() == source_bytes:
        return False

    if target.exists():
        if not backup.exists() and not created.exists():
            shutil.copy2(target, backup)
    else:
        created.write_text("created by the Psion mod\n", encoding="utf-8")

    shutil.copy2(source, target)
    return True


def remove_runtime(target: Path) -> bool:
    """Restore a replaced runtime module or remove one created by this mod."""
    backup, created = _runtime_paths(target)
    if backup.exists():
        shutil.copy2(backup, target)
        backup.unlink()
        created.unlink(missing_ok=True)
        return True
    if created.exists():
        target.unlink(missing_ok=True)
        created.unlink()
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("guiscripts", type=Path)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    targets = [
        (args.guiscripts / "ActionsWindow.py", "actions"),
        (args.guiscripts / "Spellbook.py", "spellbook"),
        (args.guiscripts / "MenuWindow.py", "rest"),
        (args.guiscripts / "GUISTORE.py", "rest"),
    ]
    for path, _ in targets:
        if not path.exists():
            raise SystemExit(f"Missing {path}")

    runtime_source = Path(__file__).resolve().parents[1] / "guiscripts" / "Psionics.py"
    runtime_target = args.guiscripts / "Psionics.py"

    if args.uninstall:
        for path, _ in targets:
            changed = remove(path)
            print(("updated " if changed else "unchanged ") + str(path))
        changed = remove_runtime(runtime_target)
        print(("updated " if changed else "unchanged ") + str(runtime_target))
        return

    # Validate every supported layout before copying or modifying anything.
    # An incompatible shared script therefore fails without leaving a partial
    # installation that imports a missing or only partly wired runtime.
    try:
        prepared = [
            (path, render_patch(path.read_text(encoding="utf-8"), kind, path))
            for path, kind in targets
        ]
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error

    changed = install_runtime(runtime_source, runtime_target)
    print(("updated " if changed else "unchanged ") + str(runtime_target))
    for path, rendered in prepared:
        changed = apply_patch(path, rendered)
        print(("updated " if changed else "unchanged ") + str(path))


if __name__ == "__main__":
    main()
