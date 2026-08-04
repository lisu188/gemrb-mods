#!/usr/bin/env python3
"""Shared runtime primitive, dispatcher, and GUI lifecycle validation."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "common"
GUI = COMMON / "guiscripts"
TOOLS = COMMON / "tools"
sys.path.insert(0, str(GUI))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_transactions():
    transactions = load("transactions_test", GUI / "Transactions.py")
    calls = []
    assert transactions.begin("X", 1, ("A", 5), lambda: True)
    assert not calls
    assert transactions.begin("X", 1, ("A", 5), lambda: True, lambda: calls.append("commit") or True)
    assert calls == ["commit"]
    assert transactions.begin("X", 1, ("B", 2), lambda: True)
    transactions.cancel("X", 1)
    assert transactions.begin("X", 1, ("B", 2), lambda: True)
    transactions.cancel("X")
    transactions.clear()


def test_state_and_charges():
    gemrb = types.ModuleType("GemRB")
    effects = []
    known = [{"SpellResRef": "MODA"}, {"SpellResRef": "OTHER"}]
    memorized = [
        {"SpellResRef": "MODA", "Flags": 0},
        {"SpellResRef": "OTHER", "Flags": 0},
    ]

    gemrb.GetEffects = lambda actor, opcode: [dict(e) for e in effects if e["Opcode"] == opcode]
    gemrb.DispelEffect = lambda actor, opcode, marker: effects.__setitem__(slice(None), [e for e in effects if not (e["Opcode"] == opcode and e["Param2"] == marker)])

    def apply_effect(actor, opcode, p1, p2, r1="", r2="", r3="", source=""):
        effects.append({"Opcode": opcode, "Param1": p1, "Param2": p2, "Resource1": r1})

    gemrb.ApplyEffect = apply_effect
    gemrb.GetKnownSpellsCount = lambda *args: len(known)
    gemrb.GetKnownSpell = lambda actor, st, sl, index: dict(known[index])
    gemrb.GetMemorizedSpellsCount = lambda *args: len(memorized)
    gemrb.GetMemorizedSpell = lambda actor, st, sl, index: dict(memorized[index])
    gemrb.UnmemorizeSpell = lambda actor, st, sl, index: memorized.pop(index) is not None

    def memorize(actor, st, sl, known_index, usable):
        memorized.append({"SpellResRef": known[known_index]["SpellResRef"], "Flags": usable})
        return True

    gemrb.MemorizeSpell = memorize
    previous = sys.modules.get("GemRB")
    sys.modules["GemRB"] = gemrb
    try:
        state = load("persistent_state_test", GUI / "PersistentState.py")
        charges = load("innate_charges_test", GUI / "InnateCharges.py")
        assert not state.read(1, "Protection:Spell", 7, "STATE")[0]
        assert state.write(1, "Protection:Spell", 7, "STATE", 9, "SRC") == 9
        assert state.read(1, "Protection:Spell", 7, "STATE") == (True, 9)
        assert charges.refresh(1, lambda resref: resref == "MODA") == 1
        assert any(row["SpellResRef"] == "MODA" and row["Flags"] for row in memorized)
        assert any(row["SpellResRef"] == "OTHER" and not row["Flags"] for row in memorized)
    finally:
        if previous is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = previous


def test_dispatcher():
    psion = types.ModuleType("Psionics")
    cipher = types.ModuleType("Cipher")
    psion.INNATE_TYPE = 2
    cipher.INNATE_TYPE = 2
    calls = []
    psion.action_info = lambda r: {"resref": r, "parent": r} if r == "PSX" else None
    cipher.power_info = lambda r: {"resref": r} if r == "CIX" else None
    psion.resolve_power_entry = lambda sb, actor, raw: {"SpellResRef": "PSX"} if raw == 1 else None
    cipher.resolve_power_entry = lambda sb, actor, raw: {"SpellResRef": "CIX"} if raw == 2 else None
    psion.begin_manifest = lambda actor, r: calls.append(("psion", actor, r)) or True
    cipher.begin_manifest = lambda actor, r: calls.append(("cipher", actor, r)) or True
    psion.cancel_pending = lambda actor=None: calls.append(("cancel-psion", actor))
    cipher.cancel_pending = lambda actor=None: calls.append(("cancel-cipher", actor))
    psion.restore_party = lambda: calls.append(("rest-psion",))
    cipher.restore_party = lambda: calls.append(("rest-cipher",))
    psion.refresh_innate_charges = lambda actor: 2
    cipher.refresh_innate_charges = lambda actor: 3
    psion.filter_spellinfo = lambda actor, refs: [r for r in refs if r != "BAD"]

    old = {name: sys.modules.get(name) for name in ("Psionics", "Cipher")}
    sys.modules["Psionics"] = psion
    sys.modules["Cipher"] = cipher
    try:
        core = load("core_dispatch_test", GUI / "GemRBModCore.py")
        assert core.begin_spell(None, 4, 1)
        assert core.begin_spell(None, 4, 2)
        assert calls[:2] == [("psion", 4, "PSX"), ("cipher", 4, "CIX")]
        assert core.action_info("PSX")["handler"] == "Psionics"
        assert core.action_info("CIX")["handler"] == "Cipher"
        assert core.refresh_innate_charges(4) == 5
        assert core.filter_spellinfo(4, ["OK", "BAD"]) == ["OK"]
        core.cancel_pending(4)
        core.restore_party()
    finally:
        for name, previous in old.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def fixture_texts():
    return {
        "ActionsWindow.py": '''import GemRB\nimport Spellbook\n\ndef UpdateActionsWindow ():\n\tpass\n\ndef ActionQSpellPressed (which):\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tGemRB.SpellCast (pc, -2, which)\n\tUpdateActionsWindow ()\n\treturn\n\ndef ActionCastPressed ():\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tSpell = GemRB.GetVar ("Spell")\n''',
        "Spellbook.py": '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\tfor i, resRef in enumerate(spellResRefs):\n\t\tmemorizedSpells.append({"SpellIndex": i + 255000, "SpellResRef": resRef})\n\treturn memorizedSpells\n''',
        "MenuWindow.py": "import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n",
        "GUISTORE.py": "import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n",
    }


def write_fixture(folder, originals):
    for name, text in originals.items():
        (folder / name).write_text(text, encoding="utf-8")


def exercise_order(first, second):
    installer = load("core_installer_%s_%s" % (first, second), TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    runtime = {
        "Psionics": ROOT / "psion" / "guiscripts" / "Psionics.py",
        "Cipher": ROOT / "cipher" / "guiscripts" / "Cipher.py",
    }
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)

        installer.install_handler(folder, first, runtime[first])
        installer.install_handler(folder, second, runtime[second])
        actions = (folder / "ActionsWindow.py").read_text(encoding="utf-8")
        spellbook = (folder / "Spellbook.py").read_text(encoding="utf-8")
        assert actions.count(installer.MARK_BEGIN) == 4
        assert spellbook.count(installer.MARK_BEGIN) == 1
        assert "import GemRBModCore" in actions
        assert "GemRBModCore.begin_spell" in actions
        assert "GemRBModCore.action_info" in actions
        assert (folder / ".gemrbmodcore.psionics.active").exists()
        assert (folder / ".gemrbmodcore.cipher.active").exists()
        for name in installer.COMMON_MODULES:
            assert (folder / name).exists()

        installer.uninstall_handler(folder, first)
        assert installer.MARK_BEGIN in (folder / "ActionsWindow.py").read_text(encoding="utf-8")
        assert (folder / (second + ".py")).exists()
        installer.uninstall_handler(folder, second)
        for name, text in originals.items():
            assert (folder / name).read_text(encoding="utf-8") == text
        for name in installer.COMMON_MODULES:
            assert not (folder / name).exists()


def exercise_legacy_runtime_upgrade(handler, legacy_tag):
    installer = load("legacy_installer_%s" % handler, TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    runtime_source = ROOT / ("psion" if handler == "Psionics" else "cipher") / "guiscripts" / (handler + ".py")

    # Legacy replacement: preserve the true pre-mod runtime through migration.
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        runtime_target = folder / (handler + ".py")
        runtime_target.write_text("legacy installed runtime\n", encoding="utf-8")
        legacy_backup = runtime_target.with_suffix(runtime_target.suffix + f".{legacy_tag}.bak")
        legacy_backup.write_text("original user runtime\n", encoding="utf-8")

        installer.install_handler(folder, handler, runtime_source)
        backup, created = installer._owned_paths(runtime_target, handler)
        assert not legacy_backup.exists()
        assert backup.read_text(encoding="utf-8") == "original user runtime\n"
        assert not created.exists()
        assert runtime_target.read_bytes() == runtime_source.read_bytes()

        installer.uninstall_handler(folder, handler)
        assert runtime_target.read_text(encoding="utf-8") == "original user runtime\n"
        assert not backup.exists()

    # Legacy creation: keep ownership as "created", so uninstall removes it.
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        runtime_target = folder / (handler + ".py")
        runtime_target.write_text("legacy installed runtime\n", encoding="utf-8")
        legacy_created = runtime_target.with_suffix(runtime_target.suffix + f".{legacy_tag}.created")
        legacy_created.write_text("legacy owner\n", encoding="utf-8")

        installer.install_handler(folder, handler, runtime_source)
        backup, created = installer._owned_paths(runtime_target, handler)
        assert not legacy_created.exists()
        assert not backup.exists()
        assert created.exists()
        assert runtime_target.read_bytes() == runtime_source.read_bytes()

        installer.uninstall_handler(folder, handler)
        assert not runtime_target.exists()
        assert not created.exists()


def test_gui_lifecycle():
    exercise_order("Psionics", "Cipher")
    exercise_order("Cipher", "Psionics")
    exercise_legacy_runtime_upgrade("Psionics", "psion")
    exercise_legacy_runtime_upgrade("Cipher", "cipher")


def main():
    test_transactions()
    test_state_and_charges()
    test_dispatcher()
    test_gui_lifecycle()
    print("Shared GemRB runtime and GUI lifecycle validation passed")


if __name__ == "__main__":
    main()
