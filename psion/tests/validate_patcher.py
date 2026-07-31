#!/usr/bin/env python3
"""Backup, idempotence, and uninstall checks for GemRB GUI patching."""

from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_patcher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions_text = '''import GemRB\nimport Spellbook\n\ndef ActionCastPressed ():\n\t"""Opens the spell choice scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_CAST)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\t"""Opens the innate spell scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_INNATE)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")\n'''
    spellbook_text = '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\ti = 0\n\treturn memorizedSpells\n'''
    rest_text = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        actions = folder / "ActionsWindow.py"
        spellbook = folder / "Spellbook.py"
        menu = folder / "MenuWindow.py"
        store = folder / "GUISTORE.py"
        actions.write_text(actions_text, encoding="utf-8")
        spellbook.write_text(spellbook_text, encoding="utf-8")
        menu.write_text(rest_text, encoding="utf-8")
        store.write_text(rest_text, encoding="utf-8")

        assert module.patch(actions, "actions")
        assert module.patch(spellbook, "spellbook")
        assert module.patch(menu, "rest")
        assert module.patch(store, "rest")
        assert "Psionics.begin_manifest" in actions.read_text(encoding="utf-8")
        assert "Psionics.filter_spellinfo" in spellbook.read_text(encoding="utf-8")
        assert not module.patch(actions, "actions")
        assert module.remove(actions)
        assert module.remove(spellbook)
        assert actions.read_text(encoding="utf-8") == actions_text
        assert spellbook.read_text(encoding="utf-8") == spellbook_text

    print("Psion GUI patcher validation passed.")


if __name__ == "__main__":
    main()
