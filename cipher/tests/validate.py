#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import py_compile
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
CIPHER = ROOT / "cipher"
COMMON = ROOT / "common" / "guiscripts"
sys.path.insert(0, str(COMMON))


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
        "common/weidu/spell-functions.tpa",
        "cipher/lib/class.tpa",
        "cipher/lib/class-skills-fix.tpa",
        "cipher/lib/class-thac0-fix.tpa",
        "cipher/lib/powers.tpa",
        "cipher/lib/power-thac0-fix.tpa",
        "cipher/lib/soul-whip-fix.tpa",
        "cipher/lib/focus.tpa",
        "cipher/lib/focus-core.tpa",
        "cipher/lib/critical-focus.tpa",
    ):
        assert required in setup
    assert "psion/lib/spell-functions.tpa" not in setup
    assert "override/mxcipher.2da" in setup
    assert "override/mxpsion.2da" not in setup

    runtime = (CIPHER / "guiscripts" / "Cipher.py").read_text(encoding="utf-8")
    assert "import Transactions" in runtime
    assert "import InnateCharges" in runtime
    assert "Transactions.begin" in runtime
    assert "InnateCharges.refresh" in runtime

    focus = (CIPHER / "lib" / "focus.tpa").read_text(encoding="utf-8")
    assert "CIPHER_HOSTILE 0x108 2 1" in focus
    assert "ci_hostile_splprot" in focus
    assert "WRITE_SHORT ci_new_effect 326" in focus
    assert "WRITE_BYTE (ci_new_effect + 0x02) 2" in focus
    assert "WRITE_LONG (ci_new_effect + 0x08) ci_hostile_splprot" in focus
    assert "opcode = 282" in focus
    assert "opcode = 321" in focus
    assert "opcode = 326" in focus
    assert "timing = 9 parameter1 = ci_unit parameter2 = 9" in focus
    assert "ci_unit = 33; ci_unit >= 0; --ci_unit" in focus
    assert "ci_location = 1" in focus
    assert "ci_attack_type = 1" in focus
    assert "ci_attack_type = 2" in focus
    assert "ci_attack_type = 3" in focus
    assert "ci_equipping_index" in focus

    focus_core = (CIPHER / "lib" / "focus-core.tpa").read_text(encoding="utf-8")
    assert "CIFS4" in focus_core
    assert "WRITE_SHORT ci_core_effect 146" in focus_core

    critical = (CIPHER / "lib" / "critical-focus.tpa").read_text(encoding="utf-8")
    assert "0x155 CastSpellOnCriticalHit" in critical
    assert "CIFCRIT" in critical
    assert "opcode = 326 target = 2" in critical
    assert "parameter2 = ci_hostile_splprot" in critical
    assert "opcode = 341 target = 1 timing = 9" in critical
    for resref in ("CIFCORE", "CIFSW15", "CIFSW20"):
        assert resref in critical

    thac0_fix = (CIPHER / "lib" / "class-thac0-fix.tpa").read_text(encoding="utf-8")
    assert "20 - ((ci_thac0_fix_col - 1) / 2)" in thac0_fix

    power_thac0_fix = (CIPHER / "lib" / "power-thac0-fix.tpa").read_text(encoding="utf-8")
    assert "CI5BINS" in power_thac0_fix
    assert "CI7TPAR" in power_thac0_fix
    assert "CI8RKNI" in power_thac0_fix
    assert "(0 - 2)" in power_thac0_fix
    assert "(0 - 3)" in power_thac0_fix
    assert "(0 - 4)" in power_thac0_fix

    soul_whip_fix = (CIPHER / "lib" / "soul-whip-fix.tpa").read_text(encoding="utf-8")
    assert "ci_whip_bonus = 1" in soul_whip_fix
    assert "ci_whip_bonus = 2" in soul_whip_fix
    assert "ci_whip_bonus = 3" in soul_whip_fix
    assert "ci_whip_opcode = 332" in soul_whip_fix
    assert "ci_whip_parameter2 = 0" in soul_whip_fix

    powers = (CIPHER / "lib" / "powers.tpa").read_text(encoding="utf-8")
    for resref in read_2da(CIPHER / "tables" / "cipherpowers.2da")[1]:
        assert f"~{resref}~" in powers


def load_runtime():
    state = {34: 10, 165: 4}
    applied = []

    class Table:
        def GetValue(self, row, column):
            _, powers = read_2da(CIPHER / "tables" / "cipherpowers.2da")
            index = {"TIER": 0, "UNLOCK": 1, "COST": 2}[column]
            return powers[row][index]

    def apply_spell(actor, resref, caster=None):
        applied.append((actor, resref, caster))
        if resref.startswith("CIFS"):
            state[165] = int(resref[4:])

    gemrb = types.ModuleType("GemRB")
    gemrb.GetPlayerStat = lambda actor, stat, *args: state.get(stat, 0)
    gemrb.ApplySpell = apply_spell
    gemrb.LoadTable = lambda name, *args: Table()
    gemrb.DisplayString = lambda *args: None
    gemrb.Log = lambda *args: None
    gemrb.GetKnownSpellsCount = lambda *args: 0
    gemrb.GetMemorizedSpellsCount = lambda *args: 0
    sys.modules["GemRB"] = gemrb

    gui_common = types.ModuleType("GUICommon")
    gui_common.GetClassRowName = lambda actor: "CIPHER"
    sys.modules["GUICommon"] = gui_common

    sys.modules.pop("InnateCharges", None)
    spec = importlib.util.spec_from_file_location("cipher_runtime", CIPHER / "guiscripts" / "Cipher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, state, applied


def test_runtime():
    runtime, state, applied = load_runtime()
    runtime.cancel_pending()
    assert runtime.maximum_focus(1) == 70
    assert runtime.current_focus(1) == 20
    runtime.set_focus(1, 200)
    assert runtime.current_focus(1) == 70
    assert applied[-1] == (1, "CIFS14", 1)
    runtime.set_focus(1, 25)
    assert applied[-1] == (1, "CIFS5", 1)
    assert runtime.can_manifest(1, "CI2MBND")
    assert runtime.begin_manifest(1, "CI2MBND")
    assert runtime.current_focus(1) == 25
    assert runtime.begin_manifest(1, "CI2MBND")
    assert runtime.current_focus(1) == 10
    assert applied[-1] == (1, "CIFS2", 1)
    assert not runtime.can_manifest(1, "CI2MBND")
    runtime.restore_party()
    assert state[165] == 4
    assert (1, "CIFS4", 1) in applied[-6:]
    assert runtime.current_focus(1) == 20


def test_python_syntax():
    py_compile.compile(str(CIPHER / "guiscripts" / "Cipher.py"), doraise=True)
    py_compile.compile(str(CIPHER / "tools" / "install_guiscripts.py"), doraise=True)
    for path in COMMON.glob("*.py"):
        py_compile.compile(str(path), doraise=True)
    py_compile.compile(str(ROOT / "common" / "tools" / "install_guiscripts.py"), doraise=True)


def test_shared_gui_lifecycle():
    path = ROOT / "common" / "tests" / "validate.py"
    spec = importlib.util.spec_from_file_location("shared_gui_validation_cipher", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.test_gui_lifecycle()


def main():
    test_tables()
    test_sources()
    test_runtime()
    test_python_syntax()
    test_shared_gui_lifecycle()
    print("Cipher validation passed")


if __name__ == "__main__":
    main()
