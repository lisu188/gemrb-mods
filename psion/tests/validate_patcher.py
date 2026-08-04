#!/usr/bin/env python3
"""Backup, idempotence, runtime ownership, selector, indentation, and preflight checks."""

from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_patcher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions_text = '''import GemRB\nimport Spellbook\n\ndef UpdateActionsWindow ():\n\tpass\n\ndef ActionQSpellPressed (which):\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tGemRB.SpellCast (pc, -2, which)\n\tUpdateActionsWindow ()\n\treturn\n\ndef ActionCastPressed ():\n\t"""Opens the spell choice scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_CAST)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\t"""Opens the innate spell scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_INNATE)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")\n'''
    spellbook_text = '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\ti = 0\n\tfor resRef in spellResRefs:\n\t\tmemorizedSpells.append({\n\t\t\t"SpellIndex": i + 1000 * 255,\n\t\t\t"SpellResRef": resRef,\n\t\t})\n\t\ti += 1\n\treturn memorizedSpells\n'''
    rest_text = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''
    nested_rest_text = '''import GemRB\n\ndef Rest():\n\tif True:\n\t\tGemRB.RestParty(0, 0)\n\t\treturn True\n'''
    runtime_source = ROOT / "guiscripts" / "Psionics.py"

    nested_rendered = module.render_patch(nested_rest_text, "rest", Path("NestedRest.py"))
    assert nested_rendered is not None
    assert "\t\t# PSION MOD BEGIN\n" in nested_rendered
    assert "\t\tPsionics.restore_party()\n" in nested_rendered
    assert "\t\t# PSION MOD END\n\t\treturn True\n" in nested_rendered
    compile(nested_rendered, "NestedRest.py", "exec")

    try:
        module.render_patch(
            rest_text.replace("import GemRB\n", "import SomethingElse\n"),
            "rest",
            Path("NoGemRB.py"),
        )
    except RuntimeError as error:
        assert str(error) == "NoGemRB.py GemRB import not found"
    else:
        raise AssertionError("missing GemRB import should fail preflight")

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
        patched_spellbook = spellbook.read_text(encoding="utf-8")
        assert "Psionics.resolve_power_entry(Spellbook, pc, raw_spell)" in patched_actions
        assert "Psionics.begin_manifest" in patched_actions
        assert "Psionics.refresh_innate_charges" in patched_actions
        assert "if GemRB.GetVar(\"SettingButtons\")" in patched_actions
        assert "quickInfo = Psionics.action_info(quickResRef)" in patched_actions
        assert "SpellPressed()" in patched_actions
        assert "Psionics.cancel_pending(pc)" in patched_actions
        assert patched_actions.count("Psionics.refresh_innate_charges") == 2
        assert "Psionics.filter_spellinfo(actor, [entry[\"SpellResRef\"] for entry in memorizedSpells])" in patched_spellbook
        assert "spellResRefs = Psionics.filter_spellinfo" not in patched_spellbook

        # Configuration mode clears reservations without starting a Psion action.
        config_gemrb = types.ModuleType("GemRB")
        config_gemrb.GameGetFirstSelectedActor = lambda: 1
        config_gemrb.GetVar = lambda name: 1 if name == "SettingButtons" else 4000
        config_gemrb.Log = lambda *_: None
        config_spellbook = types.ModuleType("Spellbook")
        config_psionics = types.ModuleType("Psionics")
        config_calls = {"cancel": 0, "resolve": 0, "begin": 0}

        def config_cancel(actor):
            config_calls["cancel"] += 1

        def config_resolve(*_):
            config_calls["resolve"] += 1
            return {"SpellResRef": "PS1VIGR"}

        def config_begin(*_):
            config_calls["begin"] += 1
            return True

        config_psionics.cancel_pending = config_cancel
        config_psionics.resolve_power_entry = config_resolve
        config_psionics.begin_manifest = config_begin
        config_psionics.refresh_innate_charges = lambda *_: 0
        old_modules = {name: sys.modules.get(name) for name in ("GemRB", "Spellbook", "Psionics")}
        sys.modules["GemRB"] = config_gemrb
        sys.modules["Spellbook"] = config_spellbook
        sys.modules["Psionics"] = config_psionics
        try:
            namespace = {}
            exec(compile(patched_actions, "ActionsWindow.py", "exec"), namespace)
            namespace["SpellPressed"]()
            assert config_calls == {"cancel": 1, "resolve": 0, "begin": 0}
        finally:
            for name, previous in old_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

        # Classic quickspells bypass SpellPressed. Both PP powers and Center Mind
        # must instead route through the registered Psion action API.
        quick_vars = {"SettingButtons": 0, "Spell": 0, "Type": 0, "QSpell": None}
        quick_direct_casts = []
        quick_gemrb = types.ModuleType("GemRB")
        quick_gemrb.GameGetFirstSelectedActor = lambda: 1
        quick_gemrb.GetPCStats = lambda actor: {
            "QuickSpells": ["PS1VIGR", "PXCNTR", "SPWI112"]
        }
        quick_gemrb.GetVar = lambda name: quick_vars.get(name)
        quick_gemrb.SetVar = lambda name, value: quick_vars.__setitem__(name, value)
        quick_gemrb.SpellCast = lambda *args: quick_direct_casts.append(args)
        quick_gemrb.Log = lambda *_: None

        quick_spellbook = types.ModuleType("Spellbook")
        quick_spellbook.GetUsableMemorizedSpells = lambda actor, book_type: [
            {"SpellIndex": 4000, "SpellResRef": "PS1VIGR"},
            {"SpellIndex": 4001, "SpellResRef": "PXCNTR"},
        ]

        quick_psionics = types.ModuleType("Psionics")
        quick_psionics.INNATE_TYPE = 2
        quick_calls = {"cancel": 0, "refresh": 0, "resolve": 0, "begin": 0}

        def quick_action_info(resref):
            key = str(resref).upper()
            if key in ("PS1VIGR", "PXCNTR"):
                return {"parent": key}
            return None

        def quick_cancel(actor):
            quick_calls["cancel"] += 1

        def quick_refresh(actor):
            quick_calls["refresh"] += 1
            return 1

        def quick_resolve(spellbook_module, actor, raw_spell):
            quick_calls["resolve"] += 1
            mapping = {4000: "PS1VIGR", 4001: "PXCNTR"}
            return {"SpellIndex": raw_spell, "SpellResRef": mapping[raw_spell]}

        def quick_begin(actor, resref):
            quick_calls["begin"] += 1
            assert resref in ("PS1VIGR", "PXCNTR")
            return True

        quick_psionics.action_info = quick_action_info
        quick_psionics.cancel_pending = quick_cancel
        quick_psionics.refresh_innate_charges = quick_refresh
        quick_psionics.resolve_power_entry = quick_resolve
        quick_psionics.begin_manifest = quick_begin

        old_modules = {name: sys.modules.get(name) for name in ("GemRB", "Spellbook", "Psionics")}
        sys.modules["GemRB"] = quick_gemrb
        sys.modules["Spellbook"] = quick_spellbook
        sys.modules["Psionics"] = quick_psionics
        try:
            namespace = {}
            exec(compile(patched_actions, "ActionsWindow.py", "exec"), namespace)

            namespace["ActionQSpellPressed"](0)
            assert quick_vars["Spell"] == 4000
            assert quick_vars["Type"] == 4
            assert quick_vars["QSpell"] is None
            assert quick_calls == {"cancel": 1, "refresh": 1, "resolve": 1, "begin": 1}
            assert quick_direct_casts == []

            # A canceled target leaves no confirmation callback. Re-pressing the
            # same quickslot must clear the stale reservation before starting over.
            namespace["ActionQSpellPressed"](0)
            assert quick_calls == {"cancel": 2, "refresh": 2, "resolve": 2, "begin": 2}
            assert quick_direct_casts == []

            # Center Mind is a runtime action too, so quickslot use must not take
            # GemRB's direct SpellCast(-2) path.
            namespace["ActionQSpellPressed"](1)
            assert quick_vars["Spell"] == 4001
            assert quick_calls == {"cancel": 3, "refresh": 3, "resolve": 3, "begin": 3}
            assert quick_direct_casts == []

            # An unrelated quickspell remains untouched.
            namespace["ActionQSpellPressed"](2)
            assert quick_direct_casts == [(1, -2, 2)]
        finally:
            for name, previous in old_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

        # Affordability filtering happens only after original type-255 indexes.
        fake_gemrb = types.ModuleType("GemRB")
        fake_gemrb.GetSpelldata = lambda actor: ["PSRF04", "PSRF01", "SPWI112"]
        fake_psionics = types.ModuleType("Psionics")
        fake_psionics.filter_spellinfo = lambda actor, refs: [ref for ref in refs if ref != "PSRF04"]
        old_gemrb = sys.modules.get("GemRB")
        old_psionics = sys.modules.get("Psionics")
        sys.modules["GemRB"] = fake_gemrb
        sys.modules["Psionics"] = fake_psionics
        try:
            namespace = {}
            exec(compile(patched_spellbook, "Spellbook.py", "exec"), namespace)
            entries = namespace["GetSpellinfoSpells"](1, 255)
            assert [entry["SpellResRef"] for entry in entries] == ["PSRF01", "SPWI112"]
            assert [entry["SpellIndex"] for entry in entries] == [255001, 255002]
        finally:
            if old_gemrb is None:
                sys.modules.pop("GemRB", None)
            else:
                sys.modules["GemRB"] = old_gemrb
            if old_psionics is None:
                sys.modules.pop("Psionics", None)
            else:
                sys.modules["Psionics"] = old_psionics

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

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        originals = {
            "ActionsWindow.py": actions_text,
            "Spellbook.py": spellbook_text,
            "MenuWindow.py": rest_text,
            "GUISTORE.py": "import GemRB\n\ndef Rest():\n\tpass\n",
        }
        for name, text in originals.items():
            (folder / name).write_text(text, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(path), str(folder)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "GUISTORE.py rest call not found" in (result.stdout + result.stderr)
        assert not (folder / "Psionics.py").exists()
        for name, text in originals.items():
            target = folder / name
            assert target.read_text(encoding="utf-8") == text
            assert not target.with_suffix(target.suffix + ".psion.bak").exists()

    print("Psion GUI patcher, selector index, Psion-action quickslot routing, configuration, runtime lifecycle, indentation, import, and preflight validation passed.")


if __name__ == "__main__":
    main()
