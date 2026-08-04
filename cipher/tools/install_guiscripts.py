#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import shutil

MARK_BEGIN = "# CIPHER MOD BEGIN"
MARK_END = "# CIPHER MOD END"


def _insert_import(text: str, path: Path) -> str:
    if "import Cipher\n" in text:
        return text
    needle = "import GemRB\n"
    if needle not in text:
        raise RuntimeError(f"{path.name} GemRB import not found")
    return text.replace(needle, needle + "import Cipher\n", 1)


def _function_bounds(text: str, function_name: str) -> tuple[int, int]:
    start = text.find(f"def {function_name} (")
    if start < 0:
        start = text.find(f"def {function_name}(")
    if start < 0:
        raise RuntimeError(f"{function_name} not found")
    next_def = text.find("\ndef ", start + 1)
    return start, len(text) if next_def < 0 else next_def


def _insert_before_in_function(text: str, function_name: str, needle: str, hook: str) -> str:
    start, end = _function_bounds(text, function_name)
    pos = text.find(needle, start, end)
    if pos < 0:
        raise RuntimeError(f"{function_name} layout not recognized")
    return text[:pos] + hook + text[pos:]


def _patch_spell_pressed(text: str) -> str:
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\tif not GemRB.GetVar(\"SettingButtons\"):\n"
        "\t\ttry:\n"
        "\t\t\traw_spell = GemRB.GetVar(\"Spell\")\n"
        "\t\t\tentry = Cipher.resolve_power_entry(Spellbook, pc, raw_spell)\n"
        "\t\t\tif entry and not Cipher.begin_manifest(pc, entry[\"SpellResRef\"]):\n"
        "\t\t\t\treturn\n"
        "\t\texcept Exception as error:\n"
        "\t\t\tGemRB.Log(2, \"Cipher\", str(error))\n"
        "\t" + MARK_END + "\n\n"
    )
    return _insert_before_in_function(
        text,
        "SpellPressed",
        '\tSpell = GemRB.GetVar ("Spell")',
        hook,
    )


def _patch_quickspell(text: str) -> str:
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\ttry:\n"
        "\t\tpcStats = GemRB.GetPCStats(pc)\n"
        "\t\tquickResRef = \"\"\n"
        "\t\tif pcStats and 0 <= which < len(pcStats[\"QuickSpells\"]):\n"
        "\t\t\tquickResRef = pcStats[\"QuickSpells\"][which]\n"
        "\t\tquickInfo = Cipher.power_info(quickResRef)\n"
        "\t\tif quickInfo:\n"
        "\t\t\tCipher.cancel_pending(pc)\n"
        "\t\t\tCipher.refresh_innate_charges(pc)\n"
        "\t\t\tentry = None\n"
        "\t\t\tfor candidate in Spellbook.GetUsableMemorizedSpells(pc, Cipher.INNATE_TYPE):\n"
        "\t\t\t\tif candidate.get(\"SpellResRef\", \"\").upper() == quickInfo[\"resref\"]:\n"
        "\t\t\t\t\tentry = candidate\n"
        "\t\t\t\t\tbreak\n"
        "\t\t\tif not entry:\n"
        "\t\t\t\treturn\n"
        "\t\t\tGemRB.SetVar(\"QSpell\", None)\n"
        "\t\t\tGemRB.SetVar(\"Spell\", entry[\"SpellIndex\"])\n"
        "\t\t\tGemRB.SetVar(\"Type\", 1 << Cipher.INNATE_TYPE)\n"
        "\t\t\tSpellPressed()\n"
        "\t\t\treturn\n"
        "\texcept Exception as error:\n"
        "\t\tGemRB.Log(2, \"Cipher\", \"quickspell routing failed: %s\" % error)\n"
        "\t" + MARK_END + "\n\n"
    )
    start, end = _function_bounds(text, "ActionQSpellPressed")
    match = re.search(r"(?m)^\tpc = GemRB\.GameGetFirstSelectedActor \(\)\n", text[start:end])
    if not match:
        raise RuntimeError("ActionQSpellPressed actor lookup not recognized")
    pos = start + match.end()
    return text[:pos] + "\n" + hook + text[pos:]


def _patch_innate_open(text: str) -> str:
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\tCipher.cancel_pending(GemRB.GameGetFirstSelectedActor ())\n"
        "\tCipher.refresh_innate_charges(GemRB.GameGetFirstSelectedActor ())\n"
        "\t" + MARK_END + "\n"
    )
    return _insert_before_in_function(
        text,
        "ActionInnatePressed",
        '\tGemRB.SetVar ("QSpell", None)',
        hook,
    )


def _patch_rest(text: str, path: Path) -> str:
    match = re.search(r"(?m)^([ \t]*)(GemRB\.RestParty\([^\n]*\)\n)", text)
    if not match:
        raise RuntimeError(f"{path.name} rest call not found")
    indent = match.group(1)
    hook = (
        indent + match.group(2)
        + indent + MARK_BEGIN + "\n"
        + indent + "Cipher.restore_party()\n"
        + indent + MARK_END + "\n"
    )
    return text[:match.start()] + hook + text[match.end():]


def render_patch(text: str, kind: str, path: Path) -> str | None:
    if MARK_BEGIN in text:
        return None
    text = _insert_import(text, path)
    if kind == "actions":
        text = _patch_spell_pressed(text)
        text = _patch_quickspell(text)
        text = _patch_innate_open(text)
    elif kind == "rest":
        text = _patch_rest(text, path)
    else:
        raise ValueError(kind)
    return text


def apply_patch(path: Path, rendered: str | None) -> bool:
    if rendered is None:
        return False
    backup = path.with_suffix(path.suffix + ".cipher.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(rendered, encoding="utf-8")
    return True


def remove(path: Path) -> bool:
    backup = path.with_suffix(path.suffix + ".cipher.bak")
    if not backup.exists():
        return False
    shutil.copy2(backup, path)
    backup.unlink()
    return True


def _runtime_paths(target: Path) -> tuple[Path, Path]:
    return target.with_suffix(target.suffix + ".cipher.bak"), target.with_suffix(target.suffix + ".cipher.created")


def install_runtime(source: Path, target: Path) -> bool:
    backup, created = _runtime_paths(target)
    source_bytes = source.read_bytes()
    if target.is_file() and target.read_bytes() == source_bytes:
        return False
    if target.exists():
        if not backup.exists() and not created.exists():
            shutil.copy2(target, backup)
    else:
        created.write_text("created by Cipher mod\n", encoding="utf-8")
    shutil.copy2(source, target)
    return True


def remove_runtime(target: Path) -> bool:
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
        (args.guiscripts / "MenuWindow.py", "rest"),
        (args.guiscripts / "GUISTORE.py", "rest"),
    ]
    for path, _ in targets:
        if not path.exists():
            raise SystemExit(f"Missing {path}")

    runtime_source = Path(__file__).resolve().parents[1] / "guiscripts" / "Cipher.py"
    runtime_target = args.guiscripts / "Cipher.py"

    if args.uninstall:
        for path, _ in targets:
            changed = remove(path)
            print(("updated " if changed else "unchanged ") + str(path))
        changed = remove_runtime(runtime_target)
        print(("updated " if changed else "unchanged ") + str(runtime_target))
        return

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
