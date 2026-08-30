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

    known_header, known = read_2da(CIPHER / "tables" / "cipherknown.2da")
    assert known_header == ["KNOWN", "MAX_TIER"]
    assert len(known) == 30
    assert known["1"] == ["1", "1"]
    assert known["10"] == ["5", "5"]
    assert known["19"] == ["9", "9"]
    assert known["30"] == ["9", "9"]
    previous_known = previous_tier = 0
    for level in range(1, 31):
        current_known, current_tier = map(int, known[str(level)])
        assert current_known >= previous_known
        assert current_tier >= previous_tier
        previous_known, previous_tier = current_known, current_tier

    pick_header, picks = read_2da(CIPHER / "tables" / "cipick.2da")
    assert pick_header == ["ResRef", "Type"]
    assert list(picks) == list(powers)
    assert len({values[0] for values in picks.values()}) == 18
    for index, (power, values) in enumerate(picks.items(), 1):
        assert values == [f"CIL{index:04d}", "3"], (power, values)

    metadata_header, metadata = read_2da(CIPHER / "tables" / "cipherfocus.2da")
    assert metadata_header == ["VALUE"]
    assert metadata == {"HOSTILE": ["0"]}

    clab = (CIPHER / "tables" / "clabciph.2da").read_text(encoding="utf-8")
    for resref in powers:
        assert f"GA_{resref}" not in clab
    assert clab.count("GA_CILRN") == 1
    assert "AP_CIFCORE" in clab
    assert "AP_CIFSW15" in clab
    assert "AP_CIFSW20" in clab


def test_sources():
    setup = (CIPHER / "setup-cipher.tp2").read_text(encoding="utf-8")
    for required in (
        "common/weidu/spell-functions.tpa",
        "common/weidu/class-item-usability.tpa",
        "cipher/lib/focus-item-patch.tpa",
        "cipher/lib/class.tpa",
        "cipher/lib/class-skills-fix.tpa",
        "cipher/lib/class-thac0-fix.tpa",
        "cipher/lib/powers.tpa",
        "cipher/lib/power-learning.tpa",
        "cipher/lib/power-thac0-fix.tpa",
        "cipher/lib/soul-whip-fix.tpa",
        "cipher/lib/focus.tpa",
        "cipher/lib/focus-core.tpa",
        "cipher/lib/critical-focus.tpa",
        "cipher/lib/item-usability.tpa",
    ):
        assert required in setup
    assert "psion/lib/spell-functions.tpa" not in setup
    assert "override/mxcipher.2da" in setup
    assert "override/mxpsion.2da" not in setup
    assert "cipherknown.2da" in setup
    assert "cipick.2da" in setup
    assert "generate_learning_proxies.py" in setup
    assert "VERSION ~0.3.0~" in setup

    class_rules = (CIPHER / "lib" / "class.tpa").read_text(encoding="utf-8")
    assert "SET ci_mage_start = INDEX_BUFFER (~^MAGE[ %TAB%]+~)" in class_rules
    assert "READ_ASCII ci_mage_start ci_mage_row" in class_rules
    assert "OUTER_SPRINT ci_xp_values ~ %ci_values%~" in class_rules

    runtime = (CIPHER / "guiscripts" / "Cipher.py").read_text(encoding="utf-8")
    for fragment in (
        "import Transactions",
        "import InnateCharges",
        "import Selectors",
        "from ie_spells import LS_MEMO",
        'POWER_SELECTOR_RESOURCE = "CILRN"',
        "def power_learning_limits(actor):",
        "def available_power_choices(actor):",
        "def filter_spellinfo(actor, resrefs):",
        "Selectors.resolve_temporary",
        "Transactions.begin",
        "InnateCharges.refresh",
    ):
        assert fragment in runtime, fragment

    learning = (CIPHER / "lib" / "power-learning.tpa").read_text(encoding="utf-8")
    assert "ci_resref = ~CILRN~" in learning
    assert "opcode = 214" in learning
    assert "resource = ~CIPICK~" in learning

    focus = (CIPHER / "lib" / "focus.tpa").read_text(encoding="utf-8")
    focus_item_patch = (CIPHER / "lib" / "focus-item-patch.tpa").read_text(encoding="utf-8")
    late_focus = (CIPHER / "lib" / "focus-items-late.tpa").read_text(encoding="utf-8")
    assert "CIPHER_HOSTILE 0x108 2 1" in focus
    assert "ci_hostile_splprot" in focus
    assert "INSERT_BYTES ci_splprot_offset ci_splprot_length" in focus
    assert "WRITE_ASCIIE ci_splprot_offset" in focus
    assert "APPEND ~splprot.2da~" not in focus
    assert "COPY ~cipher/tables/cipherfocus.2da~ ~override/cipherfocus.2da~" in focus
    assert "REPLACE_TEXTUALLY ~HOSTILE[ %TAB%]+0~ ~HOSTILE %ci_hostile_splprot%~" in focus
    assert "WRITE_SHORT ci_new_effect 326" in focus_item_patch
    assert "WRITE_BYTE (ci_new_effect + 0x02) 2" in focus_item_patch
    assert "WRITE_LONG (ci_new_effect + 0x08) ci_hostile_splprot" in focus_item_patch
    assert "READ_ASCII (ci_effect + 0x14) ci_resource (8)" in focus_item_patch
    assert "STRING_EQUAL_CASE ~CIFGAIN~" in focus_item_patch
    assert "CIPHER_ADD_FOCUS_HIT_EFFECT" in focus_item_patch
    assert "CIPHER_ADD_FOCUS_HIT_EFFECT" in late_focus
    assert "COPY_EXISTING ~cipherfocus.2da~" in late_focus
    assert "READ_2DA_ENTRY 1 1 2 ci_focus_metadata_value" in late_focus
    assert "OUTER_SET ci_hostile_splprot = EVALUATE_BUFFER ~%ci_focus_metadata_value%~" in late_focus
    assert "ci_hostile_splprot <= 0" in late_focus
    assert "opcode = 282" in focus
    assert "opcode = 321" in focus
    assert "opcode = 326" in focus
    assert "timing = 9 parameter1 = ci_unit parameter2 = 9" in focus
    assert "ci_unit = 33; ci_unit >= 0; --ci_unit" in focus
    assert "ci_location = 1" in focus_item_patch
    assert "ci_attack_type = 1" in focus_item_patch
    assert "ci_attack_type = 2" in focus_item_patch
    assert "ci_attack_type = 3" in focus_item_patch
    assert "ci_equipping_index" in focus_item_patch

    shared_usability = (ROOT / "common" / "weidu" / "class-item-usability.tpa").read_text(encoding="utf-8")
    assert "GEMRB_ADD_CLASS_ITEM_RESTRICTION" in shared_usability
    assert "opcode = 319" in shared_usability
    assert "parameter1 = class_id" in shared_usability
    assert "parameter2 = 5" in shared_usability

    item_usability = (CIPHER / "lib" / "item-usability.tpa").read_text(encoding="utf-8")
    assert "ci_item_type = 0x02" in item_usability
    assert "STRING_EQUAL_CASE ~2A~" in item_usability
    assert "ci_item_type = 0x0c" in item_usability
    assert "GEMRB_ADD_CLASS_ITEM_RESTRICTION" in item_usability

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

    lifecycle_verifier = (CIPHER / "tests" / "verify_weidu_install.py").read_text(encoding="utf-8")
    assert 'if layout == "live":' in lifecycle_verifier
    assert 'path.suffix.lower() == ".itm"' in lifecycle_verifier
    assert "sum(verify_item_focus(path) for path in item_paths) > 0" in lifecycle_verifier

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
    known_innates = [
        {"SpellResRef": "CI1WHSP"},
        {"SpellResRef": "CI2MBND"},
        {"SpellResRef": "CI3PUPP"},
        {"SpellResRef": "CI4PBLK"},
    ]
    memorized_innates = [dict(spell, Flags=1) for spell in known_innates]

    table_files = {
        "cipherpowers": "cipherpowers.2da",
        "cipherknown": "cipherknown.2da",
        "cipick": "cipick.2da",
    }

    class Table:
        def __init__(self, name):
            self.header, self.data = read_2da(CIPHER / "tables" / table_files[name])
            self.names = list(self.data)

        def GetValue(self, row, column):
            return self.data[str(row)][self.header.index(column)]

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

    def apply_spell(actor, resref, caster=None):
        applied.append((actor, resref, caster))
        if resref.startswith("CIFS"):
            state[165] = int(resref[4:])

    def learn_spell(actor, resref, flags=0, *args):
        key = str(resref).upper()
        if any(str(spell["SpellResRef"]).upper() == key for spell in known_innates):
            return 1
        known_innates.append({"SpellResRef": key})
        if int(flags) & 8:
            memorized_innates.append({"SpellResRef": key, "Flags": 1})
        return 0

    def unmemorize(actor, spell_type, level, index):
        memorized_innates.pop(index)
        return True

    def memorize(actor, spell_type, level, known_index, usable):
        memorized_innates.append({
            "SpellResRef": known_innates[known_index]["SpellResRef"],
            "Flags": 1 if usable else 0,
        })
        return True

    gemrb = types.ModuleType("GemRB")
    gemrb.GetPlayerStat = lambda actor, stat, *args: state.get(stat, 0)
    gemrb.ApplySpell = apply_spell
    gemrb.LoadTable = lambda name, *args: Table(str(name).lower())
    gemrb.DisplayString = lambda *args: None
    gemrb.Log = lambda *args: None
    gemrb.GetKnownSpellsCount = lambda actor, spell_type, level: len(known_innates)
    gemrb.GetKnownSpell = lambda actor, spell_type, level, index: dict(known_innates[index])
    gemrb.GetMemorizedSpellsCount = lambda actor, spell_type, level, real: len(memorized_innates)
    gemrb.GetMemorizedSpell = lambda actor, spell_type, level, index: dict(memorized_innates[index])
    gemrb.LearnSpell = learn_spell
    gemrb.UnmemorizeSpell = unmemorize
    gemrb.MemorizeSpell = memorize
    gemrb.GetSpelldata = lambda actor: []
    sys.modules["GemRB"] = gemrb

    gui_common = types.ModuleType("GUICommon")
    gui_common.GetClassRowName = lambda actor: "CIPHER"
    sys.modules["GUICommon"] = gui_common

    ie_spells = types.ModuleType("ie_spells")
    ie_spells.LS_MEMO = 8
    sys.modules["ie_spells"] = ie_spells

    sys.modules.pop("InnateCharges", None)
    sys.modules.pop("Selectors", None)
    spec = importlib.util.spec_from_file_location("cipher_runtime", CIPHER / "guiscripts" / "Cipher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, state, applied, known_innates, memorized_innates


def test_runtime():
    runtime, state, applied, known_innates, _ = load_runtime()
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

    # A migrated level-10 Cipher with four old fixed powers has one choice under
    # the new five-power cap. Restore grants the selector without revoking old powers.
    runtime.restore_party()
    assert state[165] == 4
    assert (1, "CIFS4", 1) in applied[-6:]
    assert runtime.current_focus(1) == 20
    known_refs = {str(spell["SpellResRef"]).upper() for spell in known_innates}
    assert runtime.POWER_SELECTOR_RESOURCE in known_refs
    assert runtime.power_learning_limits(1) == (5, 5)
    assert runtime.power_choices_remaining(1) == 1

    _, picks = read_2da(CIPHER / "tables" / "cipick.2da")
    tier5_proxy = picks["CI5BINS"][0]
    tier6_proxy = picks["CI6DSIN"][0]
    assert tier5_proxy in runtime.available_power_choices(1)
    assert tier6_proxy not in runtime.available_power_choices(1)
    assert runtime.action_info(runtime.POWER_SELECTOR_RESOURCE)["kind"] == "power_selector"
    assert runtime.action_info(tier5_proxy)["kind"] == "power_choice"
    assert runtime.begin_manifest(1, runtime.POWER_SELECTOR_RESOURCE)
    assert runtime.begin_manifest(1, tier5_proxy)
    assert "CI5BINS" not in {str(spell["SpellResRef"]).upper() for spell in known_innates}
    assert runtime.begin_manifest(1, tier5_proxy)
    assert "CI5BINS" in {str(spell["SpellResRef"]).upper() for spell in known_innates}
    assert runtime.power_choices_remaining(1) == 0
    assert not runtime.begin_manifest(1, runtime.POWER_SELECTOR_RESOURCE)

    state[34] = 11
    assert runtime.power_learning_limits(1) == (6, 6)
    assert runtime.power_choices_remaining(1) == 1
    assert tier6_proxy in runtime.available_power_choices(1)


def test_power_learning_proxy():
    path = CIPHER / "tests" / "validate_power_learning.py"
    spec = importlib.util.spec_from_file_location("cipher_power_learning_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def test_python_syntax():
    py_compile.compile(str(CIPHER / "guiscripts" / "Cipher.py"), doraise=True)
    py_compile.compile(str(CIPHER / "tools" / "install_guiscripts.py"), doraise=True)
    py_compile.compile(str(CIPHER / "tools" / "generate_learning_proxies.py"), doraise=True)
    py_compile.compile(str(CIPHER / "tests" / "verify_power_learning.py"), doraise=True)
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
    test_power_learning_proxy()
    test_python_syntax()
    test_shared_gui_lifecycle()
    print("Cipher validation passed")


if __name__ == "__main__":
    main()
