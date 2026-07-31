#!/usr/bin/env python3
"""Install or remove small GemRB GUI hooks for Psion point accounting."""
from pathlib import Path
import argparse
import re
import shutil

MARK_BEGIN = "# PSION MOD BEGIN"
MARK_END = "# PSION MOD END"


def _insert_import(text: str) -> str:
    if "import Psionics\n" not in text:
        text = text.replace("import GemRB\n", "import GemRB\nimport Psionics\n", 1)
    return text


def _patch_spell_pressed(text: str) -> str:
    needle = 'pc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")'
    hook = (
        'pc = GemRB.GameGetFirstSelectedActor ()\n\n'
        '\t' + MARK_BEGIN + '\n'
        '\t# Resolve the selected power from the encoded spell token. GemRB calls\n'
        '\t# SpellPressed twice: reserve on the first call and commit on the second.\n'
        '\ttry:\n'
        '\t\traw_spell = GemRB.GetVar("Spell")\n'
        '\t\tencoded_type = raw_spell // 1000\n'
        '\t\tspell_index = raw_spell % 1000\n'
        '\t\tbook_types = [i for i in range(16) if encoded_type & (1 << i)]\n'
        '\t\tif not book_types:\n'
        '\t\t\tbook_types = range(16)\n'
        '\t\tentry = None\n'
        '\t\tfor book_type in book_types:\n'
        '\t\t\tfor candidate in Spellbook.GetUsableMemorizedSpells(pc, book_type):\n'
        '\t\t\t\tif candidate.get("SpellIndex", -1) % 1000 == spell_index:\n'
        '\t\t\t\t\tif candidate.get("SpellResRef", "").upper().startswith("PS"):\n'
        '\t\t\t\t\t\tentry = candidate\n'
        '\t\t\t\t\t\tbreak\n'
        '\t\t\tif entry:\n'
        '\t\t\t\tbreak\n'
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
    replacement = needle.replace(
        '\tGemRB.SetVar ("QSpell", None)',
        '\tPsionics.cancel_pending(GemRB.GameGetFirstSelectedActor ())\n'
        '\tGemRB.SetVar ("QSpell", None)',
    )
    if needle not in text:
        raise RuntimeError(f"ActionsWindow.py {function_name} layout not recognized")
    return text.replace(needle, replacement, 1)


def patch(path: Path, kind: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARK_BEGIN in text:
        return False

    backup = path.with_suffix(path.suffix + ".psion.bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = _insert_import(text)

    if kind == "actions":
        text = _patch_spell_pressed(text)
        text = _patch_cancel_on_open(text, "ActionCastPressed", "ACT_CAST")
        text = _patch_cancel_on_open(text, "ActionInnatePressed", "ACT_INNATE")
    else:
        match = re.search(r"(GemRB\.RestParty\([^\n]*\)\n)", text)
        if not match:
            raise RuntimeError(f"{path.name} rest call not found")
        hook = (
            match.group(1)
            + "\t" + MARK_BEGIN + "\n"
            + "\tPsionics.restore_party()\n"
            + "\t" + MARK_END + "\n"
        )
        text = text[: match.start()] + hook + text[match.end() :]

    path.write_text(text, encoding="utf-8")
    return True


def remove(path: Path) -> bool:
    backup = path.with_suffix(path.suffix + ".psion.bak")
    if backup.exists():
        shutil.copy2(backup, path)
        backup.unlink()
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("guiscripts", type=Path)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    targets = [
        (args.guiscripts / "ActionsWindow.py", "actions"),
        (args.guiscripts / "MenuWindow.py", "rest"),
        (args.guiscripts / "GUISTORE.py", "rest"),
    ]
    for path, kind in targets:
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        changed = remove(path) if args.uninstall else patch(path, kind)
        print(("updated " if changed else "unchanged ") + str(path))


if __name__ == "__main__":
    main()
