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
        '\t# SpellPressed is also used while assigning quick/action-bar buttons.\n'
        '\t# Configuration must never reserve or spend PP; it also cancels any\n'
        '\t# stale targeting reservation before the configured slot is saved.\n'
        '\tif GemRB.GetVar("SettingButtons"):\n'
        '\t\tPsionics.cancel_pending(pc)\n'
        '\telse:\n'
        '\t\t# Resolve the selected Psion runtime action from the encoded spell token.\n'
        '\t\t# SpellPressed runs twice: reserve first, commit on confirmation.\n'
        '\t\ttry:\n'
        '\t\t\traw_spell = GemRB.GetVar("Spell")\n'
        '\t\t\tentry = Psionics.resolve_power_entry(Spellbook, pc, raw_spell)\n'
        '\t\t\tif entry and not Psionics.begin_manifest(pc, entry["SpellResRef"]):\n'
        '\t\t\t\treturn\n'
        '\t\texcept Exception as error:\n'
        '\t\t\tGemRB.Log(2, "Psionics", str(error))\n'
        '\t' + MARK_END + '\n\n'
        '\tSpell = GemRB.GetVar ("Spell")'
    )
    if needle not in text:
        raise RuntimeError("ActionsWindow.py SpellPressed layout not recognized")
    return text.replace(needle, hook, 1)


def _patch_quickspell_pressed(text: str) -> str:
    """Route Psion powers and utility actions through SpellPressed."""
    needle = (
        'def ActionQSpellPressed (which):\n'
        '\tpc = GemRB.GameGetFirstSelectedActor ()\n\n'
        '\tGemRB.SpellCast (pc, -2, which)\n'
        '\tUpdateActionsWindow ()\n'
        '\treturn\n'
    )
    replacement = (
        'def ActionQSpellPressed (which):\n'
        '\tpc = GemRB.GameGetFirstSelectedActor ()\n\n'
        '\t' + MARK_BEGIN + '\n'
        '\t# Classic GemRB quickspells call SpellCast(-2, which) directly, bypassing\n'
        '\t# SpellPressed. Registered Psion actions must re-enter the normal path so\n'
        '\t# PP accounting and focus state transitions still apply.\n'
        '\ttry:\n'
        '\t\tpcStats = GemRB.GetPCStats(pc)\n'
        '\t\tquickResRef = ""\n'
        '\t\tif pcStats and 0 <= which < len(pcStats["QuickSpells"]):\n'
        '\t\t\tquickResRef = pcStats["QuickSpells"][which]\n'
        '\t\tquickInfo = Psionics.action_info(quickResRef)\n'
        '\t\tif quickInfo:\n'
        '\t\t\t# A canceled target leaves the old first-phase reservation behind.\n'
        '\t\t\t# Every new quickslot attempt starts a fresh transaction.\n'
        '\t\t\tPsionics.cancel_pending(pc)\n'
        '\t\t\tPsionics.refresh_innate_charges(pc)\n'
        '\t\t\tparent = quickInfo["parent"]\n'
        '\t\t\tentry = None\n'
        '\t\t\tfor candidate in Spellbook.GetUsableMemorizedSpells(pc, Psionics.INNATE_TYPE):\n'
        '\t\t\t\tif candidate.get("SpellResRef", "").upper() == parent.upper():\n'
        '\t\t\t\t\tentry = candidate\n'
        '\t\t\t\t\tbreak\n'
        '\t\t\tif not entry:\n'
        '\t\t\t\treturn\n'
        '\t\t\tGemRB.SetVar("QSpell", None)\n'
        '\t\t\tGemRB.SetVar("Spell", entry["SpellIndex"])\n'
        '\t\t\tGemRB.SetVar("Type", 1 << Psionics.INNATE_TYPE)\n'
        '\t\t\tSpellPressed()\n'
        '\t\t\treturn\n'
        '\texcept Exception as error:\n'
        '\t\tGemRB.Log(2, "Psionics", "quickspell routing failed: %s" % error)\n'
        '\t' + MARK_END + '\n\n'
        '\tGemRB.SpellCast (pc, -2, which)\n'
        '\tUpdateActionsWindow ()\n'
        '\treturn\n'
    )
    if needle not in text:
        raise RuntimeError("ActionsWindow.py ActionQSpellPressed layout not recognized")
    return text.replace(needle, replacement, 1)


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
    """Hide illegal Psion children without renumbering GemRB spellinfo slots."""
    function_needle = (
        'def GetSpellinfoSpells(actor, BookType):\n'
        '\tmemorizedSpells = []\n'
        '\tspellResRefs = GemRB.GetSpelldata (actor)\n'
    )
    start = text.find(function_needle)
    if start < 0:
        raise RuntimeError("Spellbook.py GetSpellinfoSpells layout not recognized")

    return_needle = '\treturn memorizedSpells'
    return_pos = text.find(return_needle, start + len(function_needle))
    next_def = text.find('\ndef ', start + len(function_needle))
    if return_pos < 0 or (next_def >= 0 and return_pos > next_def):
        raise RuntimeError("Spellbook.py GetSpellinfoSpells return not recognized")

    hook = (
        '\t' + MARK_BEGIN + '\n'
        '\t# Keep original synthetic SpellIndex values; hide only completed entries.\n'
        '\tpsionAllowedResRefs = Psionics.filter_spellinfo(actor, [entry["SpellResRef"] for entry in memorizedSpells])\n'
        '\tmemorizedSpells = [entry for entry in memorizedSpells if entry["SpellResRef"] in psionAllowedResRefs]\n'
        '\t' + MARK_END + '\n'
    )
    return text[:return_pos] + hook + text[return_pos:]


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
        text = _patch_quickspell_pressed(text)
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
