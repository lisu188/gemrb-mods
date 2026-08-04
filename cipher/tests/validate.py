#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import py_compile
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
CIPHER = ROOT / "cipher"


def read_2da(path: Path):
    lines = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = lines[2]
    return header, {row[0]: row[1:] for row in lines[3:]}


def test_tables():
    header, powers = read_2da(CIPHER / "tables" / "cipherpowers.2da")
    assert header == ["TIER", "UNLOCK", "COST"]
    assert len(powers) == 18
    expected_unlocks = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 16, 9: 19}
    expected_costs = {1: 10, 2: 15, 3: 20, 4: 25, 5: 30, 6: 35, 7: 40, 8: 50, 9: 60}
    for values in powers.values():
        tier, unlock, cost = map(int, values)
        assert unlock == expected_unlocks[tier]
        assert cost == expected_costs[tier]

    clab = (CIPHER / "tables" / "clabciph.2da").read_text(encoding="utf-8")
    for resref in powers:
        assert f"GA_{resref}" in clab
    assert "AP_CIFCORE" in clab
    assert "AP_CIFSW15" in clab
    assert "AP_CIFSW20" in clab


def test_sources():
    setup = (CIPHER / "setup-cipher.tp2").read_text(encoding="utf-8")
    for required in (
        "cipher/lib/class.tpa",
        "cipher/lib/class-skills-fix.tpa",
        "cipher/lib/powers.tpa",
        "cipher/lib/focus.tpa",
    ):
        assert required in setup
    assert "override/mxcipher.2da" in setup
    assert "override/mxpsion.2da" not in setup

    focus = (CIPHER / "lib" / "focus.tpa").read_text(encoding="utf-8")
    assert "opcode = 146" in focus
    assert "opcode = 282" in focus
    assert "opcode = 326" in focus
    assert "ci_unit = 33; ci_unit >= 0; --ci_unit" in focus
    assert "ci_attack_type = 1" in focus
    assert "ci_attack_type = 2" in focus

    powers = (CIPHER / "lib" / "powers.tpa").read_text(encoding="utf-8")
    for resref in read_2da(CIPHER / "tables" / "cipherpowers.2da")[1]:
        assert f"~{resref}~" in powers
    assert "parameter1 = 10 parameter2 = 0" in powers
    assert "parameter1 = 15 parameter2 = 0" in powers
    assert "parameter1 = 20 parameter2 = 0" in powers


def load_runtime():
    state = {34: 10, 165: 4}

    class Table:
        def GetValue(self, row, column):
            _, powers = read_2da(CIPHER / "tables" / "cipherpowers.2da")
            index = {"TIER": 0, "UNLOCK": 1, "COST": 2}[column]
            return powers[row][index]

    gemrb = types.ModuleType("GemRB")
    gemrb.GetPlayerStat = lambda actor, stat: state.get(stat, 0)
    gemrb.SetPlayerStat = lambda actor, stat, value: state.__setitem__(stat, value)
    gemrb.LoadTable = lambda name, *args: Table()
    gemrb.DisplayString = lambda *args: None
    gemrb.Log = lambda *args: None
    gemrb.GetKnownSpellsCount = lambda *args: 0
    gemrb.GetMemorizedSpellsCount = lambda *args: 0
    sys.modules["GemRB"] = gemrb

    gui_common = types.ModuleType("GUICommon")
    gui_common.GetClassRowName = lambda actor: "CIPHER"
    sys.modules["GUICommon"] = gui_common

    spec = importlib.util.spec_from_file_location("cipher_runtime", CIPHER / "guiscripts" / "Cipher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, state


def test_runtime():
    runtime, state = load_runtime()
    assert runtime.maximum_focus(1) == 70
    assert runtime.current_focus(1) == 20
    runtime.set_focus(1, 200)
    assert runtime.current_focus(1) == 70
    runtime.set_focus(1, 25)
    assert runtime.can_manifest(1, "CI2MBND")
    assert runtime.begin_manifest(1, "CI2MBND")
    assert runtime.current_focus(1) == 25
    assert runtime.begin_manifest(1, "CI2MBND")
    assert runtime.current_focus(1) == 10
    assert not runtime.can_manifest(1, "CI2MBND")
    runtime.restore_party()
    assert state[165] == 4
    assert runtime.current_focus(1) == 20


def test_python_syntax():
    py_compile.compile(str(CIPHER / "guiscripts" / "Cipher.py"), doraise=True)
    py_compile.compile(str(CIPHER / "tools" / "install_guiscripts.py"), doraise=True)


def test_patcher():
    spec = importlib.util.spec_from_file_location("cipher_patcher", CIPHER / "tools" / "install_guiscripts.py")
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    actions = '''import GemRB\nimport Spellbook\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tSpell = GemRB.GetVar ("Spell")\n\n\ndef ActionQSpellPressed (which):\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tGemRB.SpellCast (pc, -2, which)\n\n\ndef ActionInnatePressed ():\n\tGemRB.SetVar ("QSpell", None)\n'''
    path = Path("ActionsWindow.py")
    patched = patcher.render_patch(actions, "actions", path)
    assert patched.count(patcher.MARK_BEGIN) == 3
    assert "import Cipher" in patched
    assert patcher.render_patch(patched, "actions", path) is None

    rest = "import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0, 0)\n"
    patched_rest = patcher.render_patch(rest, "rest", Path("MenuWindow.py"))
    assert "Cipher.restore_party()" in patched_rest


def main():
    test_tables()
    test_sources()
    test_runtime()
    test_python_syntax()
    test_patcher()
    print("Cipher validation passed")


if __name__ == "__main__":
    main()
