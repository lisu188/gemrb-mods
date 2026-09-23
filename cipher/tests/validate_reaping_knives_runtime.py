#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
CIPHER = ROOT / "cipher"


def load_runtime():
    prepared = []
    variables = {}
    logs = []

    gemrb = types.ModuleType("GemRB")
    gemrb.PrepareSpontaneousCast = lambda actor, source, book, level, replacement: prepared.append(
        (actor, source, book, level, replacement)
    ) or 12
    gemrb.SetVar = lambda key, value: variables.__setitem__(key, value)
    gemrb.Log = lambda *args: logs.append(args)
    sys.modules["GemRB"] = gemrb

    transactions = types.ModuleType("Transactions")
    transactions.begin = lambda *args, **kwargs: True
    transactions.cancel = lambda *args, **kwargs: None
    sys.modules["Transactions"] = transactions

    innate = types.ModuleType("InnateCharges")
    innate.refresh = lambda *args, **kwargs: 0
    sys.modules["InnateCharges"] = innate

    persistent = types.ModuleType("PersistentState")
    persistent.read = lambda *args, **kwargs: (False, 0)
    persistent.write = lambda *args, **kwargs: args[4] if len(args) > 4 else 0
    sys.modules["PersistentState"] = persistent

    selectors = types.ModuleType("Selectors")
    selectors.resolve_temporary = lambda *args, **kwargs: None
    sys.modules["Selectors"] = selectors

    ie_spells = types.ModuleType("ie_spells")
    ie_spells.LS_MEMO = 8
    sys.modules["ie_spells"] = ie_spells

    spec = importlib.util.spec_from_file_location("cipher_reaping_runtime", CIPHER / "guiscripts" / "Cipher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._reaping_owner_token = lambda actor: actor + 6
    return module, prepared, variables, logs


def test_prepare_reaping_knives():
    runtime, prepared, variables, logs = load_runtime()
    entry = {
        "SpellResRef": "CI8RKNI",
        "BookType": 2,
        "SpellLevel": 0,
        "SpellIndex": 17,
    }
    assert runtime.prepare_action_entry(None, 3, entry) is entry
    assert not prepared
    assert entry["CastResRef"] == "CI8RK9"
    assert not variables
    assert not logs


def test_non_reaping_spell_is_unchanged():
    runtime, prepared, variables, _ = load_runtime()
    entry = {
        "SpellResRef": "CI7TPAR",
        "BookType": 2,
        "SpellLevel": 0,
        "SpellIndex": 4,
    }
    assert runtime.prepare_action_entry(None, 2, entry) is entry
    assert not prepared
    assert not variables


def test_internal_owner_variants_remain_managed():
    runtime, _, _, _ = load_runtime()
    runtime.power_info = lambda name: {"resref": name} if name == "CI8RKNI" else None
    for token in (1, 6, 7, 9, 99, 100, 255):
        info = runtime.action_info("CI8RK%d" % token)
        assert info["resref"] == "CI8RKNI"
        assert info["internal_resref"] == "CI8RK%d" % token
    runtime.power_choice_info = lambda name: None
    for name in ("CI8RK0", "CI8RK256", "CI8RK01", "CI8RKX"):
        assert runtime.action_info(name) is None


def test_invalid_owner_slot_fails_closed():
    runtime, prepared, variables, logs = load_runtime()
    entry = {
        "SpellResRef": "CI8RKNI",
        "BookType": 2,
        "SpellLevel": 0,
        "SpellIndex": 17,
    }
    assert runtime.prepare_action_entry(None, 7, entry) is False
    assert not prepared
    assert not variables
    assert logs


def test_installer_source_contract():
    setup = (CIPHER / "setup-cipher.tp2").read_text(encoding="utf-8")
    source = (CIPHER / "lib" / "reaping-knives-focus.tpa").read_text(encoding="utf-8")
    runtime_source = (CIPHER / "guiscripts" / "Cipher.py").read_text(encoding="utf-8")
    assert "cipher/lib/reaping-knives-focus.tpa" in setup
    assert setup.index("cipher/lib/focus.tpa") < setup.index("cipher/lib/reaping-knives-focus.tpa")
    assert "CIPHER_RK_OWNER_" in source
    assert "OUTER_SET ci_rk_set_melee = 248" in source
    assert "OUTER_SET ci_rk_set_ranged = 249" in source
    assert "CREATE ~eff~" in source
    assert "CIRKSTEP" in source
    assert "target = 3" in source
    assert "ci_hostile_splprot" in source
    assert "ci_class_splprot" in source
    assert "REAPING_KNIVES_RESOURCE = \"CI8RKNI\"" in runtime_source
    assert 'entry["CastResRef"]' in runtime_source


def main():
    test_prepare_reaping_knives()
    test_non_reaping_spell_is_unchanged()
    test_internal_owner_variants_remain_managed()
    test_invalid_owner_slot_fails_closed()
    test_installer_source_contract()
    subprocess.run([sys.executable, str(CIPHER / "tests" / "validate_reaping_identity.py")], check=True)
    print("Cipher Reaping Knives runtime validation passed")


if __name__ == "__main__":
    main()
