#!/usr/bin/env python3
"""Static and fake-runtime validation for the experimental GemRB Psion mod."""
from pathlib import Path
import importlib.util
import py_compile
import re
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]

DISCIPLINE_CLABS = {
    "SEER": "clabpsee.2da",
    "SHAPER": "clabpsha.2da",
    "KINETICIST": "clabpkin.2da",
    "EGOIST": "clabpego.2da",
    "NOMAD": "clabpnom.2da",
    "TELEPATH": "clabptel.2da",
}

LEVEL1_REFS = {
    "PS1ERAY", "PS1MTHR", "PS1IARM", "PS1VIGR", "PS1FSCR", "PS1EMND",
    "PS1PREC", "PS1ACON", "PS1EPUS", "PS1TSKN", "PS1BRST", "PS1CHAR",
}
LEVEL2_REFS = {
    "PS2AMOR", "PS2CBLS", "PS2DHIN", "PS2TSHD", "PS2BIOF", "PS2SWCR",
    "PS2CLAI", "PS2RPRD", "PS2EMIS", "PS2AAFF", "PS2DSWP", "PS2BRLK",
}


def table_lines(name):
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name):
    return table_lines(name)[2].split()


def rows(name):
    return [
        line.split()
        for line in table_lines(name)[3:]
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]


def section_for(text, ref, refs):
    marker = f"ps_resref = ~{ref}~"
    start = text.index(marker)
    later = [
        text.find(f"ps_resref = ~{other}~", start + 1)
        for other in refs
        if text.find(f"ps_resref = ~{other}~", start + 1) != -1
    ]
    return text[start:min(later) if later else len(text)]


def validate_2da_schemas():
    expected = {
        "psionpowers.2da": [
            "NAME", "LEVEL", "DISCIPLINE", "BASE_COST", "AUGMENT_STEP", "TEMPLATE",
        ],
        "psionaugment.2da": ["PARENT", "TOTAL_COST", "EFFECT", "VALUE"],
        "ps1eray.2da": ["ResRef", "Type"],
        "ps1mthr.2da": ["ResRef", "Type"],
        "ps1vigr.2da": ["ResRef", "Type"],
        "ps2aaff.2da": ["ResRef", "Type"],
        "psiondisc.2da": ["DISCIPLINE", "SCHOOL", "SPECIAL_SKILL"],
        "psionskills.2da": ["ABILITY", "ACCESS", "COST", "BREAK1", "BREAK2", "BREAK3"],
        "psionfeats.2da": ["MIN_LEVEL", "FOCUS", "PP_SURCHARGE"],
    }
    for filename, columns in expected.items():
        assert header(filename) == columns, (filename, header(filename), columns)
        assert all(len(row) == len(columns) + 1 for row in rows(filename)), filename


def validate_progressions():
    pool = rows("psionpool.2da")
    known = rows("psionknown.2da")
    powers = rows("psionpowers.2da")
    assert len(pool) == 20 and len(known) == 20
    assert len(powers) == 60
    assert {row[0] for row in powers if row[2] == "1"} == LEVEL1_REFS
    assert {row[0] for row in powers if row[2] == "2"} == LEVEL2_REFS

    known_by_level = {int(row[0]): (int(row[1]), int(row[2])) for row in known}
    metadata = {row[0]: {"level": int(row[2]), "discipline": row[3]} for row in powers}

    for discipline, filename in DISCIPLINE_CLABS.items():
        learned = []
        for row in rows(filename):
            level = int(row[0])
            newly_learned = [token[3:] for token in row[1:] if token.startswith("GA_PS")]
            learned.extend(newly_learned)
            assert len(learned) == len(set(learned)), (discipline, "duplicate power")
            assert set(learned) <= set(metadata), (discipline, "unknown power")
            assert all(metadata[ref]["discipline"] in ("GENERAL", discipline) for ref in learned)

            if level <= 9:
                expected_count, maximum_level = known_by_level[level]
                assert len(learned) == expected_count, (discipline, level, len(learned), expected_count)
                if level in (1, 3, 5, 7, 9):
                    exclusive = [ref for ref in newly_learned if metadata[ref]["discipline"] == discipline]
                    assert len(exclusive) == 1
                    assert metadata[exclusive[0]]["level"] == maximum_level


def validate_power_builders():
    level1 = (ROOT / "lib" / "level1-powers.tpa").read_text(encoding="utf-8")
    level2 = (ROOT / "lib" / "level2-powers.tpa").read_text(encoding="utf-8")
    animal = (ROOT / "lib" / "animal-affinity.tpa").read_text(encoding="utf-8")
    energy = (ROOT / "lib" / "energy-ray-augment.tpa").read_text(encoding="utf-8")
    mind_vigor = (ROOT / "lib" / "mind-vigor-augment.tpa").read_text(encoding="utf-8")
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    prototype = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")

    for include in (
        "level1-powers.tpa", "level2-powers.tpa", "energy-ray-augment.tpa",
        "mind-vigor-augment.tpa", "animal-affinity.tpa",
    ):
        assert include in driver

    # Exact levels must not be overwritten by the remaining template builder.
    assert "psion_level > 2" in prototype
    assert "psion_level > 1" not in prototype
    assert "WRITE_LONG 0x34 psion_level" in prototype
    assert "WRITE_LONG 0x18 (THIS | BIT25)" in prototype

    assert set(re.findall(r"ps_resref = ~(PS1[A-Z0-9]+)~", level1)) == LEVEL1_REFS
    assert set(re.findall(r"ps_resref = ~(PS2[A-Z0-9]+)~", level2)) == LEVEL2_REFS
    assert "WRITE_LONG 0x34 1" in level1
    assert "WRITE_LONG 0x34 2" in level2

    level1_required = {
        "PS1ERAY": ("opcode = 12", "dicesize = 6"),
        "PS1MTHR": ("dicesize = 10", "savingthrow = BIT0"),
        "PS1IARM": ("parameter1 = -4", "duration = 3600"),
        "PS1VIGR": ("opcode = 18", "opcode = 17"),
        "PS1FSCR": ("opcode = 206", "resource = ~SPWI112~"),
        "PS1EMND": ("opcode = 37", "parameter1 = -2"),
        "PS1PREC": ("opcode = 54", "duration = 18"),
        "PS1ACON": ("opcode = 67", "resource = ~PSACON01~"),
        "PS1EPUS": ("opcode = 238", "savingthrow = BIT1"),
        "PS1TSKN": ("parameter1 = -1", "duration = 60"),
        "PS1BRST": ("opcode = 126", "parameter1 = 130"),
        "PS1CHAR": ("opcode = 5", "duration = 60"),
    }
    for ref, fragments in level1_required.items():
        section = section_for(level1, ref, LEVEL1_REFS)
        for fragment in fragments:
            assert fragment in section, (ref, fragment)

    level2_required = {
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
    for ref, fragments in level2_required.items():
        section = section_for(level2, ref, LEVEL2_REFS)
        for fragment in fragments:
            assert fragment in section, (ref, fragment)

    assert "DELETE ~override/PS1ERAY.spl~" in energy
    assert "dicenumber = ps_cost" in energy
    assert "DELETE ~override/PS1MTHR.spl~" in mind_vigor
    assert "DELETE ~override/PS1VIGR.spl~" in mind_vigor
    assert "ps_vigor_hp = (ps_cost * 5)" in mind_vigor

    for ref, opcode in (("PSAASTR", "44"), ("PSAADEX", "15"), ("PSAACON", "10")):
        assert f"~{ref}~ => {opcode}" in animal
        assert f"resource = ~{ref}~" in animal
    assert "parameter1 = 4" in animal and "duration = 60" in animal


def validate_augmentation_tables():
    augment = rows("psionaugment.2da")
    assert len(augment) == 57
    assert len({row[0] for row in augment}) == 57

    selector_files = {
        "PS1ERAY": ("ps1eray.2da", 36),
        "PS1MTHR": ("ps1mthr.2da", 9),
        "PS1VIGR": ("ps1vigr.2da", 9),
        "PS2AAFF": ("ps2aaff.2da", 3),
    }
    all_selector_refs = set()
    for parent, (filename, expected_count) in selector_files.items():
        selector = rows(filename)
        assert len(selector) == expected_count
        assert all(row[2] == "3" for row in selector)
        selector_refs = {row[1] for row in selector}
        parent_refs = {row[0] for row in augment if row[1] == parent}
        assert selector_refs == parent_refs
        all_selector_refs |= selector_refs

    assert all_selector_refs == {row[0] for row in augment}
    animal = [row for row in augment if row[1] == "PS2AAFF"]
    assert {row[0] for row in animal} == {"PSAASTR", "PSAADEX", "PSAACON"}
    assert all(row[2:] == ["3", "ABILITY", row[4]] for row in animal)


def validate_installer_references():
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "VERSION ~0.5.0-alpha~" in setup
    for table in (
        "psionpool", "psionknown", "psiondisc", "psionskills", "psionfeats",
        "psionpowers", "psionaugment", "ps1eray", "ps1mthr", "ps1vigr",
        "ps2aaff", "mxpsion", "clabpsee", "clabpsha", "clabpkin",
        "clabpego", "clabpnom", "clabptel",
    ):
        assert table in setup

    for include in (
        "class-detect.tpa", "class-strings.tpa", "class-layout.tpa",
        "class-common.tpa", "class-skills.tpa",
    ):
        assert include in setup

    power_data = (ROOT / "lib" / "power-data.tpa").read_text(encoding="utf-8")
    generated = set(re.findall(r"~(PS[0-9A-Z]+)~ =>", power_data))
    defined = {row[0] for row in rows("psionpowers.2da")}
    assert defined <= generated


def fake_table(name):
    columns = header(name)
    data = rows(name)

    class Table:
        def __init__(self):
            self.names = [row[0] for row in data]
            self.values = {row[0]: dict(zip(columns, row[1:])) for row in data}

        def GetValue(self, row, column):
            return self.values[str(row)][column]

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

    return Table()


def validate_runtime_transactions():
    fake_gemrb = types.ModuleType("GemRB")
    fake_gui = types.ModuleType("GUICommon")
    stats = {(1, 38): 18, (1, 34): 3, (1, 188): 0, (1, 239): 0}
    messages = []
    tables = {
        "psionpool": fake_table("psionpool.2da"),
        "psionpowers": fake_table("psionpowers.2da"),
        "psionaugment": fake_table("psionaugment.2da"),
    }

    fake_gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""
    fake_gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)
    fake_gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    fake_gemrb.LoadTable = lambda name, *_args: tables[name.lower()]
    fake_gemrb.DisplayString = lambda *args: messages.append(args)

    old_gemrb = sys.modules.get("GemRB")
    old_gui = sys.modules.get("GUICommon")
    sys.modules["GemRB"] = fake_gemrb
    sys.modules["GUICommon"] = fake_gui
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psion_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        starting_pool = module.ensure_pool(1)
        assert starting_pool == 17
        for parent in ("PS1ERAY", "PS1MTHR", "PS1VIGR", "PS2AAFF"):
            info = module.power_info(parent)
            assert info["selector"] and info["cost"] == 0
            assert module.can_manifest(1, parent)

        affinity = module.power_info("PSAADEX")
        assert affinity["parent"] == "PS2AAFF" and affinity["cost"] == 3
        assert affinity["value"] == "DEXTERITY"

        mixed = ["SPWI112", "PSRF01", "PSRF04", "PSMT03", "PSVG09", "PSAADEX"]
        assert module.filter_spellinfo(1, mixed) == ["SPWI112", "PSRF01", "PSMT03", "PSAADEX"]

        before = module.ensure_pool(1)
        assert module.begin_manifest(1, "PS2AAFF")
        assert module.ensure_pool(1) == before
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before - 3

        assert not module.can_manifest(1, "PSRF04")
        assert "PSRF03" in module.available_variants(1, "PS1ERAY")
        assert "PSRF04" not in module.available_variants(1, "PS1ERAY")
        assert set(module.available_variants(1, "PS2AAFF")) == {"PSAASTR", "PSAADEX", "PSAACON"}

        stats[(1, 188)] = 1
        stats[(1, 239)] = 0
        assert not module.can_manifest(1, "PS2AAFF")
        assert module.available_variants(1, "PS2AAFF") == []
        assert module.filter_spellinfo(1, ["SPWI112", "PSAASTR"]) == ["SPWI112"]
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_gui is None:
            sys.modules.pop("GUICommon", None)
        else:
            sys.modules["GUICommon"] = old_gui


def validate_gui_patcher():
    patcher_path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_gui_patcher", patcher_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions_fixture = '''import GemRB\nimport Spellbook\n\ndef ActionCastPressed ():\n\t"""Opens the spell choice scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_CAST)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\t"""Opens the innate spell scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_INNATE)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")\n'''
    spellbook_fixture = '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\ti = 0\n\treturn memorizedSpells\n'''
    rest_fixture = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        actions = directory / "ActionsWindow.py"
        spellbook = directory / "Spellbook.py"
        menu = directory / "MenuWindow.py"
        store = directory / "GUISTORE.py"
        actions.write_text(actions_fixture, encoding="utf-8")
        spellbook.write_text(spellbook_fixture, encoding="utf-8")
        menu.write_text(rest_fixture, encoding="utf-8")
        store.write_text(rest_fixture, encoding="utf-8")

        assert module.patch(actions, "actions")
        assert module.patch(spellbook, "spellbook")
        assert module.patch(menu, "rest")
        assert module.patch(store, "rest")
        assert "Psionics.begin_manifest" in actions.read_text(encoding="utf-8")
        assert "Psionics.filter_spellinfo(actor, spellResRefs)" in spellbook.read_text(encoding="utf-8")
        assert not module.patch(actions, "actions")
        assert not module.patch(spellbook, "spellbook")
        assert module.remove(actions) and module.remove(spellbook)
        assert actions.read_text(encoding="utf-8") == actions_fixture
        assert spellbook.read_text(encoding="utf-8") == spellbook_fixture


def main():
    validate_2da_schemas()
    validate_progressions()
    validate_power_builders()
    validate_augmentation_tables()
    validate_installer_references()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    validate_runtime_transactions()
    validate_gui_patcher()
    print("Psion 0.5 level-2, 57-variant, runtime, and GUI-hook validation passed.")


if __name__ == "__main__":
    main()
