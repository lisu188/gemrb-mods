#!/usr/bin/env python3
"""Validate GemRB runtime routing for owner-aware Reaping Knives."""
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "common" / "guiscripts" / "GemRBModCore.py"
REAPING = ROOT / "cipher" / "lib" / "reaping-knives.tpa"


def load_core():
    calls = []
    gemrb = types.ModuleType("GemRB")

    def prepare(actor, source, book_type, spell_level, replacement):
        calls.append(("prepare", actor, source, book_type, spell_level, replacement))
        return 17

    gemrb.PrepareSpontaneousCast = prepare
    gemrb.SetVar = lambda name, value: calls.append(("setvar", name, value))
    gemrb.Log = lambda *args: calls.append(("log",) + args)
    sys.modules["GemRB"] = gemrb
    spec = importlib.util.spec_from_file_location("reaping_mod_core", CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, calls


def test_runtime_substitution():
    core, calls = load_core()
    handler = types.SimpleNamespace(__name__="Cipher")
    entry = {
        "SpellResRef": "CI8RKNI",
        "BookType": 2,
        "SpellLevel": 0,
        "SpellIndex": 9,
    }
    assert core._prepare_cipher_reaping_knives(handler, 3, entry) is entry
    assert calls == [
        ("prepare", 3, "CI8RKNI", 2, 0, "CI8RK3"),
        ("setvar", "Spell", 4017),
    ]

    calls.clear()
    assert core._prepare_cipher_reaping_knives(handler, 7, entry) is None
    assert calls == []
    assert core._prepare_cipher_reaping_knives(types.SimpleNamespace(__name__="Psionics"), 3, entry) is None
    assert calls == []


def test_installer_contract():
    text = REAPING.read_text(encoding="utf-8")
    assert "ci_rk_scripting_stat = 182" in text
    assert "ci_rk_scripting_index = 26" in text
    for owner in range(1, 7):
        assert f"CIPHER_RK_OWNER_{owner} 182 {owner} 1" in text
        assert f"override/CI8RK{owner}.spl" in text
        assert f"CIRKE{owner}" in text
        assert f"CIRKG{owner}" in text
    assert "opcode = 248" in text
    assert "opcode = 249" in text
    assert "opcode = 326 target = 3" in text
    assert "resource = ~CIFSTEP~" in text


def main():
    test_runtime_substitution()
    test_installer_contract()
    print("Cipher Reaping Knives runtime validation passed")


if __name__ == "__main__":
    main()
