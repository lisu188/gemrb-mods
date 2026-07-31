#!/usr/bin/env python3
"""Backup, idempotence, runtime ownership, and uninstall checks."""

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
    runtime_source = ROOT / "guiscripts" / "Psionics.py"

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        actions = folder / "ActionsWindow.py"
        spellbook = folder / "Spellbook.py"
        menu = folder / "MenuWindow.py"
        store = folder / "GUISTORE.py"
        runtime = folder / "Psionics.py"
        original_runtime = "# pre-existing third-party Psionics module\n"
        actions.write_text(actions_text, encoding="utf-8")
        spellbook.write_text(spellbook_text, encoding="utf-8")
        menu.write_text(rest_text, encoding="utf-8")
        store.write_text(rest_text, encoding="utf-8")
        runtime.write_text(original_runtime, encoding="utf-8")

        # Replacing a pre-existing runtime creates one backup, and reinstalling
        # identical bytes is idempotent rather than overwriting that backup.
        assert module.install_runtime(runtime_source, runtime)
        backup, created = module._runtime_paths(runtime)
        assert backup.read_text(encoding="utf-8") == original_runtime
        assert not created.exists()
        assert runtime.read_bytes() == runtime_source.read_bytes()
        assert not module.install_runtime(runtime_source, runtime)
        assert backup.read_text(encoding="utf-8") == original_runtime

        assert module.patch(actions, "actions")
        assert module.patch(spellbook, "spellbook")
        assert module.patch(menu, "rest")
        assert module.patch(store, "rest")
        patched_actions = actions.read_text(encoding="utf-8")
        assert "Psionics.begin_manifest" in patched_actions
        assert "Psionics.refresh_innate_charges" in patched_actions
        assert patched_actions.count("Psionics.refresh_innate_charges") == 1
        assert "Psionics.filter_spellinfo" in spellbook.read_text(encoding="utf-8")
        assert not module.patch(actions, "actions")

        assert module.remove(actions)
        assert module.remove(spellbook)
        assert module.remove(menu)
        assert module.remove(store)
        assert module.remove_runtime(runtime)
        assert actions.read_text(encoding="utf-8") == actions_text
        assert spellbook.read_text(encoding="utf-8") == spellbook_text
        assert runtime.read_text(encoding="utf-8") == original_runtime
        assert not backup.exists()

        # When no runtime existed before installation, uninstall removes the
        # mod-owned file instead of leaving an importable module behind.
        runtime.unlink()
        assert module.install_runtime(runtime_source, runtime)
        backup, created = module._runtime_paths(runtime)
        assert created.exists()
        assert not backup.exists()
        assert not module.install_runtime(runtime_source, runtime)
        assert module.remove_runtime(runtime)
        assert not runtime.exists()
        assert not created.exists()
        assert not module.remove_runtime(runtime)

    print("Psion GUI patcher and runtime lifecycle validation passed.")


if __name__ == "__main__":
    main()
