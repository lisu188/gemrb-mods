#!/usr/bin/env python3
"""Static, fake-runtime, and GUI-hook checks for the GemRB Psion mod."""
from pathlib import Path
import importlib.util
import py_compile
import re
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
DISCIPLINE_CLABS = {
    "SEER": "clabpsee.2da", "SHAPER": "clabpsha.2da",
    "KINETICIST": "clabpkin.2da", "EGOIST": "clabpego.2da",
    "NOMAD": "clabpnom.2da", "TELEPATH": "clabptel.2da",
}
LEVEL1 = {
    "PS1ERAY", "PS1MTHR", "PS1IARM", "PS1VIGR", "PS1FSCR", "PS1EMND",
    "PS1PREC", "PS1ACON", "PS1EPUS", "PS1TSKN", "PS1BRST", "PS1CHAR",
}
LEVEL2 = {
    "PS2AMOR", "PS2CBLS", "PS2DHIN", "PS2TSHD", "PS2BIOF", "PS2SWCR",
    "PS2CLAI", "PS2RPRD", "PS2EMIS", "PS2AAFF", "PS2DSWP", "PS2BRLK",
}


def lines(name):
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name):
    return lines(name)[2].split()


def rows(name):
    return [line.split() for line in lines(name)[3:]
            if line.strip() and not line.lstrip().startswith(("#", "//"))]


def section(text, ref, refs):
    start = text.index(f"ps_resref = ~{ref}~")
    ends = [text.find(f"ps_resref = ~{other}~", start + 1) for other in refs]
    ends = [value for value in ends if value != -1]
    return text[start:min(ends) if ends else len(text)]


def validate_tables():
    expected = {
        "psionpowers.2da": ["NAME", "LEVEL", "DISCIPLINE", "BASE_COST", "AUGMENT_STEP", "TEMPLATE"],
        "psionaugment.2da": ["PARENT", "TOTAL_COST", "EFFECT", "VALUE"],
        "ps1eray.2da": ["ResRef", "Type"], "ps1mthr.2da": ["ResRef", "Type"],
        "ps1vigr.2da": ["ResRef", "Type"], "ps2aaff.2da": ["ResRef", "Type"],
        "psiondisc.2da": ["DISCIPLINE", "SCHOOL", "SPECIAL_SKILL"],
        "psionskills.2da": ["ABILITY", "ACCESS", "COST", "BREAK1", "BREAK2", "BREAK3"],
        "psionfeats.2da": ["MIN_LEVEL", "FOCUS", "PP_SURCHARGE"],
    }
    for name, columns in expected.items():
        assert header(name) == columns, (name, header(name), columns)
        assert all(len(row) == len(columns) + 1 for row in rows(name)), name

    powers = rows("psionpowers.2da")
    assert len(powers) == 60
    assert {row[0] for row in powers if row[2] == "1"} == LEVEL1
    assert {row[0] for row in powers if row[2] == "2"} == LEVEL2
    assert len(rows("psionpool.2da")) == len(rows("psionknown.2da")) == 20


def validate_progressions():
    known = {int(row[0]): (int(row[1]), int(row[2])) for row in rows("psionknown.2da")}
    powers = {row[0]: {"level": int(row[2]), "discipline": row[3]}
              for row in rows("psionpowers.2da")}
    for discipline, filename in DISCIPLINE_CLABS.items():
        learned = []
        for row in rows(filename):
            level = int(row[0])
            gained = [token[3:] for token in row[1:] if token.startswith("GA_PS")]
            learned.extend(gained)
            assert len(learned) == len(set(learned))
            assert set(learned) <= set(powers)
            assert all(powers[ref]["discipline"] in ("GENERAL", discipline) for ref in learned)
            if level <= 9:
                count, maximum = known[level]
                assert len(learned) == count
                if level in (1, 3, 5, 7, 9):
                    exclusive = [ref for ref in gained if powers[ref]["discipline"] == discipline]
                    assert len(exclusive) == 1 and powers[exclusive[0]]["level"] == maximum


def validate_builders():
    l1 = (ROOT / "lib" / "level1-powers.tpa").read_text(encoding="utf-8")
    l2 = (ROOT / "lib" / "level2-powers.tpa").read_text(encoding="utf-8")
    animal = (ROOT / "lib" / "animal-affinity.tpa").read_text(encoding="utf-8")
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    prototype = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")

    for include in ("level1-powers.tpa", "level2-powers.tpa", "energy-ray-augment.tpa",
                    "mind-vigor-augment.tpa", "animal-affinity.tpa"):
        assert include in driver
    assert "psion_level > 2" in prototype and "psion_level > 1" not in prototype
    assert "WRITE_LONG 0x34 psion_level" in prototype
    assert set(re.findall(r"ps_resref = ~(PS1[A-Z0-9]+)~", l1)) == LEVEL1
    assert set(re.findall(r"ps_resref = ~(PS2[A-Z0-9]+)~", l2)) == LEVEL2
    assert "WRITE_LONG 0x34 1" in l1 and "WRITE_LONG 0x34 2" in l2

    required = {
        "PS2AMOR": ("opcode = 65", "parameter1 = -2"),
        "PS2CBLS": ("dicenumber = 2", "dicesize = 6"),
        "PS2DHIN": ("opcode = 193", "opcode = 292"),
        "PS2TSHD": ("opcode = 31", "parameter1 = 20"),
        "PS2BIOF": ("ps_resist_opcode = 86", "ps_resist_opcode <= 89"),
        "PS2SWCR": ("dicenumber = 3", "special = BIT8"),
        "PS2CLAI": ("opcode = 193", "opcode = 91"),
        "PS2RPRD": ("opcode = 17", "dicesize = 8"),
        "PS2EMIS": ("ELECTRICITY", "special = BIT8"),
        "PS2AAFF": ("opcode = 214", "resource = ~PS2AAFF~"),
        "PS2DSWP": ("opcode = 124", "parameter2 = 3"),
        "PS2BRLK": ("opcode = 175", "duration = 18"),
    }
    for ref, fragments in required.items():
        body = section(l2, ref, LEVEL2)
        for fragment in fragments:
            assert fragment in body, (ref, fragment)

    # IESDP mapping: opcode 15 modifies Strength, 44 Dexterity, and 10 Constitution.
    for ref, opcode in (("PSAASTR", "15"), ("PSAADEX", "44"), ("PSAACON", "10")):
        assert f"~{ref}~ => {opcode}" in animal
        assert f"resource = ~{ref}~" in animal
    assert "parameter1 = 4" in animal and "duration = 60" in animal


def validate_augmentation():
    augment = rows("psionaugment.2da")
    assert len(augment) == len({row[0] for row in augment}) == 57
    selectors = {
        "PS1ERAY": ("ps1eray.2da", 36), "PS1MTHR": ("ps1mthr.2da", 9),
        "PS1VIGR": ("ps1vigr.2da", 9), "PS2AAFF": ("ps2aaff.2da", 3),
    }
    all_children = set()
    for parent, (filename, count) in selectors.items():
        data = rows(filename)
        assert len(data) == count and all(row[2] == "3" for row in data)
        children = {row[1] for row in data}
        assert children == {row[0] for row in augment if row[1] == parent}
        all_children |= children
    assert all_children == {row[0] for row in augment}
    affinity = [row for row in augment if row[1] == "PS2AAFF"]
    assert {row[0] for row in affinity} == {"PSAASTR", "PSAADEX", "PSAACON"}
    assert all(row[2] == "3" and row[3] == "ABILITY" for row in affinity)


def validate_installer():
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "VERSION ~0.5.0-alpha~" in setup
    for name in ("psionpool", "psionknown", "psiondisc", "psionskills", "psionfeats",
                 "psionpowers", "psionaugment", "ps1eray", "ps1mthr", "ps1vigr",
                 "ps2aaff", "mxpsion", "clabpsee", "clabpsha", "clabpkin",
                 "clabpego", "clabpnom", "clabptel"):
        assert name in setup


def fake_table(name):
    columns, data = header(name), rows(name)
    class Table:
        names = [row[0] for row in data]
        values = {row[0]: dict(zip(columns, row[1:])) for row in data}
        def GetValue(self, row, column): return self.values[str(row)][column]
        def GetRowCount(self): return len(self.names)
        def GetRowName(self, index): return self.names[index]
    return Table()


def validate_runtime():
    gemrb, gui = types.ModuleType("GemRB"), types.ModuleType("GUICommon")
    stats = {(1, 38): 18, (1, 34): 3, (1, 188): 0, (1, 239): 0}
    tables = {name: fake_table(name + ".2da") for name in
              ("psionpool", "psionpowers", "psionaugment")}
    gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""
    gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)
    gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    gemrb.LoadTable = lambda name, *_: tables[name.lower()]
    gemrb.DisplayString = lambda *_: None
    old_gemrb, old_gui = sys.modules.get("GemRB"), sys.modules.get("GUICommon")
    sys.modules["GemRB"], sys.modules["GUICommon"] = gemrb, gui
    try:
        spec = importlib.util.spec_from_file_location("psion_runtime_test", ROOT / "guiscripts" / "Psionics.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        assert module.ensure_pool(1) == 17
        for parent in ("PS1ERAY", "PS1MTHR", "PS1VIGR", "PS2AAFF"):
            assert module.power_info(parent)["selector"] and module.can_manifest(1, parent)
        assert module.power_info("PSAADEX")["cost"] == 3
        mixed = ["SPWI112", "PSRF01", "PSRF04", "PSAADEX"]
        assert module.filter_spellinfo(1, mixed) == ["SPWI112", "PSRF01", "PSAADEX"]
        before = module.ensure_pool(1)
        assert module.begin_manifest(1, "PSAADEX") and module.ensure_pool(1) == before
        assert module.begin_manifest(1, "PSAADEX") and module.ensure_pool(1) == before - 3
        assert set(module.available_variants(1, "PS2AAFF")) == {"PSAASTR", "PSAADEX", "PSAACON"}
        stats[(1, 188)], stats[(1, 239)] = 1, 0
        assert not module.can_manifest(1, "PS2AAFF")
        assert module.filter_spellinfo(1, ["SPWI112", "PSAASTR"]) == ["SPWI112"]
    finally:
        if old_gemrb is None: sys.modules.pop("GemRB", None)
        else: sys.modules["GemRB"] = old_gemrb
        if old_gui is None: sys.modules.pop("GUICommon", None)
        else: sys.modules["GUICommon"] = old_gui


def validate_patcher():
    path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_patcher_test", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    actions_text = '''import GemRB\nimport Spellbook\n\ndef ActionCastPressed ():\n\t"""Opens the spell choice scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_CAST)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\t"""Opens the innate spell scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_INNATE)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")\n'''
    spellbook_text = '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\ti = 0\n\treturn memorizedSpells\n'''
    rest_text = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        actions, spellbook = folder / "ActionsWindow.py", folder / "Spellbook.py"
        menu, store = folder / "MenuWindow.py", folder / "GUISTORE.py"
        actions.write_text(actions_text); spellbook.write_text(spellbook_text)
        menu.write_text(rest_text); store.write_text(rest_text)
        assert module.patch(actions, "actions") and module.patch(spellbook, "spellbook")
        assert module.patch(menu, "rest") and module.patch(store, "rest")
        assert "Psionics.begin_manifest" in actions.read_text()
        assert "Psionics.filter_spellinfo" in spellbook.read_text()
        assert not module.patch(actions, "actions")
        assert module.remove(actions) and module.remove(spellbook)
        assert actions.read_text() == actions_text and spellbook.read_text() == spellbook_text


def main():
    validate_tables(); validate_progressions(); validate_builders()
    validate_augmentation(); validate_installer()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    validate_runtime(); validate_patcher()
    print("Psion 0.5 level-2, 57-variant, runtime, and GUI-hook validation passed.")


if __name__ == "__main__":
    main()
