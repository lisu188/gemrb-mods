#!/usr/bin/env python3
"""Install a single shared GemRB GUI hook layer for optional class runtimes."""
from pathlib import Path
import argparse
import re
import shutil

MARK_BEGIN = "# GEMRB MOD CORE BEGIN"
MARK_END = "# GEMRB MOD CORE END"
CORE_BACKUP_SUFFIX = ".gemrbmodcore.bak"
COMMON_MODULES = (
    "GemRBModCore.py",
    "GemRBModClassChoice.py",
    "GemRBModPsionChoice.py",
    "Transactions.py",
    "InnateCharges.py",
    "PersistentState.py",
    "Selectors.py",
)


def _insert_import(text, path):
    if "import GemRBModCore\n" in text:
        return text
    needle = "import GemRB\n"
    if needle not in text:
        raise RuntimeError(f"{path.name} GemRB import not found")
    return text.replace(needle, needle + "import GemRBModCore\n", 1)


def _function_bounds(text, function_name):
    start = text.find(f"def {function_name} (")
    if start < 0:
        start = text.find(f"def {function_name}(")
    if start < 0:
        raise RuntimeError(f"{function_name} not found")
    next_def = text.find("\ndef ", start + 1)
    return start, len(text) if next_def < 0 else next_def


def _insert_before(text, function_name, needle, hook):
    start, end = _function_bounds(text, function_name)
    pos = text.find(needle, start, end)
    if pos < 0:
        raise RuntimeError(f"{function_name} layout not recognized")
    return text[:pos] + hook + text[pos:]


def _patch_spell_pressed(text):
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\tif GemRB.GetVar(\"SettingButtons\"):\n"
        "\t\tGemRBModCore.cancel_pending(pc)\n"
        "\telse:\n"
        "\t\ttry:\n"
        "\t\t\traw_spell = GemRB.GetVar(\"Spell\")\n"
        "\t\t\tif not GemRBModCore.begin_spell(Spellbook, pc, raw_spell):\n"
        "\t\t\t\treturn\n"
        "\t\texcept Exception as error:\n"
        "\t\t\tGemRB.Log(2, \"GemRBModCore\", str(error))\n"
        "\t" + MARK_END + "\n\n"
    )
    return _insert_before(text, "SpellPressed", '\tSpell = GemRB.GetVar ("Spell")', hook)


def _patch_quickspell(text):
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\ttry:\n"
        "\t\tpcStats = GemRB.GetPCStats(pc)\n"
        "\t\tquickResRef = \"\"\n"
        "\t\tif pcStats and 0 <= which < len(pcStats[\"QuickSpells\"]):\n"
        "\t\t\tquickResRef = pcStats[\"QuickSpells\"][which]\n"
        "\t\tquickInfo = GemRBModCore.action_info(quickResRef)\n"
        "\t\tif quickInfo:\n"
        "\t\t\tGemRBModCore.cancel_pending(pc)\n"
        "\t\t\tGemRBModCore.refresh_innate_charges(pc)\n"
        "\t\t\tentry = None\n"
        "\t\t\tfor candidate in Spellbook.GetUsableMemorizedSpells(pc, quickInfo[\"innate_type\"]):\n"
        "\t\t\t\tif candidate.get(\"SpellResRef\", \"\").upper() == quickInfo[\"parent\"].upper():\n"
        "\t\t\t\t\tentry = candidate\n"
        "\t\t\t\t\tbreak\n"
        "\t\t\tif not entry:\n"
        "\t\t\t\treturn\n"
        "\t\t\tGemRB.SetVar(\"QSpell\", None)\n"
        "\t\t\tGemRB.SetVar(\"Spell\", entry[\"SpellIndex\"])\n"
        "\t\t\tGemRB.SetVar(\"Type\", 1 << quickInfo[\"innate_type\"])\n"
        "\t\t\tSpellPressed()\n"
        "\t\t\treturn\n"
        "\texcept Exception as error:\n"
        "\t\tGemRB.Log(2, \"GemRBModCore\", \"quickspell routing failed: %s\" % error)\n"
        "\t" + MARK_END + "\n\n"
    )
    start, end = _function_bounds(text, "ActionQSpellPressed")
    match = re.search(r"(?m)^\tpc = GemRB\.GameGetFirstSelectedActor \(\)\n", text[start:end])
    if not match:
        raise RuntimeError("ActionQSpellPressed actor lookup not recognized")
    pos = start + match.end()
    return text[:pos] + "\n" + hook + text[pos:]


def _patch_open(text, function_name, refresh=False):
    lines = ["\t" + MARK_BEGIN, "\tGemRBModCore.cancel_pending(GemRB.GameGetFirstSelectedActor ())"]
    if refresh:
        lines.append("\tGemRBModCore.refresh_innate_charges(GemRB.GameGetFirstSelectedActor ())")
    lines.extend(["\t" + MARK_END, ""])
    return _insert_before(text, function_name, '\tGemRB.SetVar ("QSpell", None)', "\n".join(lines) + "\n")


def _patch_spellinfo(text):
    function_needle = 'def GetSpellinfoSpells(actor, BookType):\n'
    start = text.find(function_needle)
    if start < 0:
        raise RuntimeError("Spellbook.py GetSpellinfoSpells layout not recognized")
    return_needle = '\treturn memorizedSpells'
    pos = text.find(return_needle, start)
    next_def = text.find('\ndef ', start + len(function_needle))
    if pos < 0 or (next_def >= 0 and pos > next_def):
        raise RuntimeError("Spellbook.py GetSpellinfoSpells return not recognized")
    hook = (
        "\t" + MARK_BEGIN + "\n"
        "\tallowed = GemRBModCore.filter_spellinfo(actor, [entry[\"SpellResRef\"] for entry in memorizedSpells])\n"
        "\tmemorizedSpells = [entry for entry in memorizedSpells if entry[\"SpellResRef\"] in allowed]\n"
        "\t" + MARK_END + "\n"
    )
    return text[:pos] + hook + text[pos:]


def _patch_rest(text, path):
    match = re.search(
        r"(?m)^([ \t]*)(?:([A-Za-z_]\w*)[ \t]*=[ \t]*)?GemRB\.RestParty[ \t]*\([^\n]*\)\n",
        text,
    )
    if not match:
        raise RuntimeError(f"{path.name} rest call not found")
    indent = match.group(1)
    result = match.group(2)
    hook = match.group(0) + indent + MARK_BEGIN + "\n"
    if result:
        hook += indent + f'if not {result}["Error"]:\n'
        hook += indent + "\tGemRBModCore.restore_party()\n"
    else:
        hook += indent + "GemRBModCore.restore_party()\n"
    hook += indent + MARK_END + "\n"
    return text[:match.start()] + hook + text[match.end():]


def render_patch(text, kind, path):
    if MARK_BEGIN in text:
        return None
    text = _insert_import(text, path)
    if kind == "actions":
        text = _patch_spell_pressed(text)
        text = _patch_quickspell(text)
        text = _patch_open(text, "ActionInnatePressed", True)
        if "def ActionCastPressed" in text:
            text = _patch_open(text, "ActionCastPressed", False)
    elif kind == "spellbook":
        text = _patch_spellinfo(text)
    elif kind == "rest":
        text = _patch_rest(text, path)
    else:
        raise ValueError(kind)
    return text


def render_class_choice_patch(text, path):
    if MARK_BEGIN in text:
        return None
    import_needle = "import GemRB\n"
    function_needle = "def OnLoad():\n"
    if import_needle not in text or function_needle not in text:
        raise RuntimeError(f"{path.name} BG1 class screen layout not recognized")
    text = text.replace(import_needle, import_needle + "import GemRBModClassChoice\n", 1)
    wrapper = (
        "def OnLoad():\n"
        "\t" + MARK_BEGIN + "\n"
        "\tGemRBModClassChoice.on_load(globals())\n"
        "\t" + MARK_END + "\n\n"
        "def _GemRBModCoreOriginalOnLoad():\n"
    )
    return text.replace(function_needle, wrapper, 1)


def render_spell_selection_patch(text, path):
    if MARK_BEGIN in text:
        return None
    import_needle = "import GemRB\n"
    function_needle = "def OnLoad():\n"
    if import_needle not in text or function_needle not in text:
        raise RuntimeError(f"{path.name} BG2 spell-selection layout not recognized")
    text = text.replace(import_needle, import_needle + "import GemRBModClassChoice\n", 1)
    hook = (
        function_needle
        + "\t" + MARK_BEGIN + "\n"
        + "\tif GemRBModClassChoice.skip_spell_selection():\n"
        + "\t\treturn\n"
        + "\t" + MARK_END + "\n"
    )
    return text.replace(function_needle, hook, 1)


def render_spell_window_patch(text, path):
    if MARK_BEGIN in text:
        return None
    needle = "\t\tSpellsTextArea = SpellsWindow.GetControl (41 if GameCheck.IsAnyEE() else 27)\n"
    if needle not in text:
        raise RuntimeError(f"{path.name} spell-description control layout not recognized")
    bg2_or_ee = "GameCheck.IsBG2OrEE ()"
    if bg2_or_ee not in text:
        raise RuntimeError(f"{path.name} BG2 chargen routing layout not recognized")
    replacement = (
        needle
        + "\t\t" + MARK_BEGIN + "\n"
        + "\t\tif not SpellsTextArea and GameCheck.IsBGEE():\n"
        + "\t\t\tSpellsTextArea = SpellsWindow.GetControl (27)\n"
        + "\t\t" + MARK_END + "\n"
    )
    text = text.replace(needle, replacement, 1)
    return text.replace(
        bg2_or_ee,
        "(GameCheck.IsBG2OrEE () or GameCheck.IsBGEE ())",
    )


def _legacy_clean(path):
    text = path.read_text(encoding="utf-8")
    changed = False
    for marker, suffix in (("# CIPHER MOD BEGIN", ".cipher.bak"), ("# PSION MOD BEGIN", ".psion.bak")):
        while marker in text:
            backup = path.with_suffix(path.suffix + suffix)
            if not backup.exists():
                raise RuntimeError(f"{path.name} contains legacy {marker} without {backup.name}")
            shutil.copy2(backup, path)
            backup.unlink()
            text = path.read_text(encoding="utf-8")
            changed = True
    return changed


def apply_patch(path, rendered):
    if rendered is None:
        return False
    backup = path.with_suffix(path.suffix + CORE_BACKUP_SUFFIX)
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(rendered, encoding="utf-8")
    return True


def remove_patch(path):
    backup = path.with_suffix(path.suffix + CORE_BACKUP_SUFFIX)
    if not backup.exists():
        return False
    shutil.copy2(backup, path)
    backup.unlink()
    return True


def _owned_paths(target, owner):
    tag = owner.lower()
    return target.with_suffix(target.suffix + f".gemrbmodcore.{tag}.bak"), target.with_suffix(target.suffix + f".gemrbmodcore.{tag}.created")


def _legacy_runtime_paths(target, owner):
    tag = owner.lower()
    legacy_tag = "psion" if tag == "psionics" else tag
    return target.with_suffix(target.suffix + f".{legacy_tag}.bak"), target.with_suffix(target.suffix + f".{legacy_tag}.created")


def _migrate_legacy_runtime_ownership(target, owner):
    legacy_backup, legacy_created = _legacy_runtime_paths(target, owner)
    if not legacy_backup.exists() and not legacy_created.exists():
        return False
    if legacy_backup.exists() and legacy_created.exists():
        raise RuntimeError(f"{target.name} has conflicting legacy ownership markers")

    backup, created = _owned_paths(target, owner)
    if backup.exists() or created.exists():
        raise RuntimeError(f"{target.name} has both legacy and shared ownership markers")

    source = legacy_backup if legacy_backup.exists() else legacy_created
    destination = backup if legacy_backup.exists() else created
    shutil.move(str(source), str(destination))
    return True


def install_owned_file(source, target, owner):
    backup, created = _owned_paths(target, owner)
    source_bytes = source.read_bytes()
    if target.is_file() and target.read_bytes() == source_bytes:
        return False
    if target.exists():
        if not backup.exists() and not created.exists():
            shutil.copy2(target, backup)
    else:
        created.write_text(f"created by GemRB mod core for {owner}\n", encoding="utf-8")
    shutil.copy2(source, target)
    return True


def remove_owned_file(target, owner):
    backup, created = _owned_paths(target, owner)
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


def _marker(folder, handler):
    return folder / (".gemrbmodcore.%s.active" % handler.lower())


def _active_handlers(folder):
    return list(folder.glob(".gemrbmodcore.*.active"))


def install_handler(guiscripts, handler, runtime_source):
    targets = [
        (guiscripts / "ActionsWindow.py", "actions"),
        (guiscripts / "Spellbook.py", "spellbook"),
        (guiscripts / "MenuWindow.py", "rest"),
        (guiscripts / "GUISTORE.py", "rest"),
    ]
    for path, _ in targets:
        if not path.exists():
            raise RuntimeError(f"Missing {path}")

    class_choices = [
        path
        for path in (guiscripts / "bg1" / "GUICG2.py", guiscripts / "bg2" / "GUICG2.py")
        if path.exists()
    ]

    for path, _ in targets:
        _legacy_clean(path)
    prepared = [(path, render_patch(path.read_text(encoding="utf-8"), kind, path)) for path, kind in targets]
    spell_window = guiscripts / "LUSpellSelection.py"
    if not spell_window.exists():
        raise RuntimeError(f"Missing {spell_window}")
    prepared_spell_window = (
        spell_window,
        render_spell_window_patch(spell_window.read_text(encoding="utf-8"), spell_window),
    )
    prepared_class_choices = [
        (path, render_class_choice_patch(path.read_text(encoding="utf-8"), path))
        for path in class_choices
    ]
    spell_selection = guiscripts / "bg2" / "GUICG7.py"
    prepared_spell_selection = None
    if spell_selection.exists():
        prepared_spell_selection = (
            spell_selection,
            render_spell_selection_patch(
                spell_selection.read_text(encoding="utf-8"), spell_selection
            ),
        )

    runtime_target = guiscripts / (handler + ".py")
    _migrate_legacy_runtime_ownership(runtime_target, handler)

    common_source = Path(__file__).resolve().parents[1] / "guiscripts"
    for name in COMMON_MODULES:
        install_owned_file(common_source / name, guiscripts / name, "core")
    install_owned_file(runtime_source, runtime_target, handler)
    for path, rendered in prepared:
        apply_patch(path, rendered)
    apply_patch(*prepared_spell_window)
    for path, rendered in prepared_class_choices:
        apply_patch(path, rendered)
    if prepared_spell_selection:
        apply_patch(*prepared_spell_selection)
    _marker(guiscripts, handler).write_text("active\n", encoding="utf-8")


def uninstall_handler(guiscripts, handler):
    _marker(guiscripts, handler).unlink(missing_ok=True)
    remove_owned_file(guiscripts / (handler + ".py"), handler)
    if _active_handlers(guiscripts):
        return
    for name in ("ActionsWindow.py", "Spellbook.py", "MenuWindow.py", "GUISTORE.py", "LUSpellSelection.py"):
        remove_patch(guiscripts / name)
    for game_type in ("bg1", "bg2"):
        remove_patch(guiscripts / game_type / "GUICG2.py")
    remove_patch(guiscripts / "bg2" / "GUICG7.py")
    for name in COMMON_MODULES:
        remove_owned_file(guiscripts / name, "core")


def main_for_handler(handler, runtime_source):
    parser = argparse.ArgumentParser()
    parser.add_argument("guiscripts", type=Path)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    try:
        if args.uninstall:
            uninstall_handler(args.guiscripts, handler)
        else:
            install_handler(args.guiscripts, handler, Path(runtime_source))
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    raise SystemExit("Use the Psion or Cipher wrapper so the handler is explicit.")
