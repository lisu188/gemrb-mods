#!/usr/bin/env python3
"""Install or remove small GemRB GUI hooks for Psion pool accounting."""
from pathlib import Path
import argparse
import re
import shutil

MARK_BEGIN = "# PSION MOD BEGIN"
MARK_END = "# PSION MOD END"


def patch(path: Path, kind: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARK_BEGIN in text:
        return False

    backup = path.with_suffix(path.suffix + ".psion.bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = text.replace("import GemRB\n", "import GemRB\nimport Psionics\n", 1)

    if kind == "actions":
        needle = 'pc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")'
        hook = (
            'pc = GemRB.GameGetFirstSelectedActor ()\n\n'
            '\t' + MARK_BEGIN + '\n'
            '\t# Charge the selected Psion power before target selection starts.\n'
            '\ttry:\n'
            '\t\ttype_value = GemRB.GetVar("Type")\n'
            '\t\tspell_value = GemRB.GetVar("Spell")\n'
            '\t\tbook_type = type_value if type_value >= 0 else 0\n'
            '\t\tentries = Spellbook.GetUsableMemorizedSpells(pc, book_type)\n'
            '\t\tentry = next((s for s in entries if s.get("SpellIndex") == spell_value), None)\n'
            '\t\tif entry and entry["SpellResRef"].upper().startswith("PS"):\n'
            '\t\t\tif not Psionics.spend(pc, entry["SpellResRef"]):\n'
            '\t\t\t\treturn\n'
            '\texcept Exception as error:\n'
            '\t\tGemRB.Log(2, "Psionics", str(error))\n'
            '\t' + MARK_END + '\n\n'
            '\tSpell = GemRB.GetVar ("Spell")'
        )
        if needle not in text:
            raise RuntimeError("ActionsWindow.py layout not recognized")
        text = text.replace(needle, hook, 1)
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
