#!/usr/bin/env python3
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
CIPHER = ROOT / "cipher"
COMMON = ROOT / "common"


def main():
    setup = (CIPHER / "setup-cipher.tp2").read_text(encoding="utf-8")
    assert "VERSION ~0.3.0~" in setup
    assert "cipher/tables/cisubpck.2da" in setup
    assert "cipher/lib/reaping-knives.tpa" in setup
    assert "cipher/lib/subclasses.tpa" in setup
    assert "AT_NOW ~python \"cipher/tools/generate_learning_proxies.py\"" in setup
    assert "AT_NOW ~python3" not in setup

    wrapper = (CIPHER / "tools/install_guiscripts.py").read_text(encoding="utf-8")
    assert "CipherSubclass.py" in wrapper

    dispatcher = (COMMON / "guiscripts/GemRBModCore.py").read_text(encoding="utf-8")
    assert '"CipherSubclass"' in dispatcher
    assert '"Cipher"' in dispatcher

    runtime = (CIPHER / "guiscripts/Cipher.py").read_text(encoding="utf-8")
    subclass = (CIPHER / "guiscripts/CipherSubclass.py").read_text(encoding="utf-8")
    ast.parse(runtime)
    ast.parse(subclass)
    for fragment in (
        "modify_focus_gain",
        "modify_focus_cap",
        "modify_power_cost",
        "weapon_effect_resource",
        "PersistentState.read",
        "PersistentState.write",
        "SOUL_BLADE_ACTION",
        "SOUL_BLADE_COST",
    ):
        assert fragment in subclass
    assert "modify_focus_cap(actor, cap)" in runtime
    assert "modify_power_cost(actor, info[\"resref\"], cost)" in runtime

    subclass_rules = (CIPHER / "lib/subclasses.tpa").read_text(encoding="utf-8")
    for resref in ("CISUBSEL", "CISBSBLD", "CISBPASS", "CISBANN"):
        assert resref in subclass_rules
    assert "opcode = 284" in subclass_rules
    assert "opcode = 285" in subclass_rules

    reaping = (CIPHER / "lib/reaping-knives.tpa").read_text(encoding="utf-8")
    assert "CREATE EFF VERSION ~V2.0~ ~CIRKHIT~" in reaping
    assert "WRITE_LONG 0x10 326" in reaping
    assert "WRITE_LONG 0x14 2" in reaping
    assert "WRITE_LONG 0x20 ci_hostile_splprot" in reaping
    assert "WRITE_ASCII 0x30 ~CIRKGAIN~ #8" in reaping
    assert "WRITE_LONG 0x5c 2" in reaping
    assert "opcode = 326 target = 9" in reaping
    assert "resource = ~CIFSTEP~" in reaping
    assert "opcode = 248" in reaping
    assert "opcode = 249" in reaping
    assert "critical hit transfers the same 5 Focus" in reaping

    print("Cipher extension validation passed")


if __name__ == "__main__":
    main()
