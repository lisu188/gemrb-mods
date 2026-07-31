#!/usr/bin/env python3
"""Version-neutral table, runtime, installer, and GUI-hook checks."""

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

LEVEL_REFS = {
    1: {
        "PS1ERAY", "PS1MTHR", "PS1IARM", "PS1VIGR", "PS1FSCR", "PS1EMND",
        "PS1PREC", "PS1ACON", "PS1EPUS", "PS1TSKN", "PS1BRST", "PS1CHAR",
    },
    2: {
        "PS2AMOR", "PS2CBLS", "PS2DHIN", "PS2TSHD", "PS2BIOF", "PS2SWCR",
        "PS2CLAI", "PS2RPRD", "PS2EMIS", "PS2AAFF", "PS2DSWP", "PS2BRLK",
    },
    3: {
        "PS3DPSI", "PS3BADJ", "PS3EBLT", "PS3MBAR", "PS3TSGT", "PS3THOP",
        "PS3DANG", "PS3COCO", "PS3ECON", "PS3HUST", "PS3SSTP", "PS3MSTL",
    },
    4: {
        "PS4EADP", "PS4FOMV", "PS4DDOR", "PS4IFOR", "PS4TKMN", "PS4PLEE",
        "PS4RVIE", "PS4WECT", "PS4EBAL", "PS4META", "PS4PFLY", "PS4COMP",
    },
    5: {
        "PS5ADBD", "PS5CATP", "PS5PRES", "PS5COGL", "PS5TRUE", "PS5TELE",
        "PS5SCHN", "PS5HOCR", "PS5ECUR", "PS5PFDB", "PS5BALT", "PS5MPRB",
    },
}


def table_lines(name: str) -> list[str]:
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name: str) -> list[str]:
    return table_lines(name)[2].split()


def rows(name: str) -> list[list[str]]:
    return [
        line.split()
        for line in table_lines(name)[3:]
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]


def resource_section(text: str, function: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind(f"LAF {function}", 0, marker_pos)
    assert start >= 0, (resref, "missing builder call")
    next_start = text.find(f"LAF {function}", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def validate_tables() -> None:
    expected = {
        "psionpowers.2da": [
            "NAME", "LEVEL", "DISCIPLINE", "BASE_COST", "AUGMENT_STEP", "TEMPLATE"
        ],
        "psionaugment.2da": ["PARENT", "TOTAL_COST", "EFFECT", "VALUE"],
        "ps1eray.2da": ["ResRef", "Type"],
        "ps1mthr.2da": ["ResRef", "Type"],
        "ps1vigr.2da": ["ResRef", "Type"],
        "ps2aaff.2da": ["ResRef", "Type"],
        "psiondisc.2da": ["DISCIPLINE", "SCHOOL", "SPECIAL_SKILL"],
        "psionskills.2da": [
            "ABILITY", "ACCESS", "COST", "BREAK1", "BREAK2", "BREAK3"
        ],
        "psionfeats.2da": ["MIN_LEVEL", "FOCUS", "PP_SURCHARGE"],
    }
    for filename, columns in expected.items():
        assert header(filename) == columns, (filename, header(filename), columns)
        assert all(len(row) == len(columns) + 1 for row in rows(filename)), filename

    powers = rows("psionpowers.2da")
    assert len(powers) == 60
    assert len({row[0] for row in powers}) == 60
    for level, expected_refs in LEVEL_REFS.items():
        actual = {row[0] for row in powers if int(row[2]) == level}
        assert actual == expected_refs, (level, actual ^ expected_refs)
        assert all(int(row[4]) == 2 * level - 1 for row in powers if int(row[2]) == level)
    assert len(rows("psionpool.2da")) == len(rows("psionknown.2da")) == 20


def validate_progressions() -> None:
    known = {
        int(row[0]): (int(row[1]), int(row[2]))
        for row in rows("psionknown.2da")
    }
    powers = {
        row[0]: {"level": int(row[2]), "discipline": row[3]}
        for row in rows("psionpowers.2da")
    }

    for discipline, filename in DISCIPLINE_CLABS.items():
        learned: list[str] = []
        for row in rows(filename):
            level = int(row[0])
            gained = [token[3:] for token in row[1:] if token.startswith("GA_PS")]
            learned.extend(gained)
            assert len(learned) == len(set(learned)), (discipline, "duplicate power")
            assert set(learned) <= set(powers), (discipline, "unknown power")
            assert all(
                powers[ref]["discipline"] in ("GENERAL", discipline)
                for ref in learned
            ), (discipline, "off-discipline power")

            if level <= 9:
                expected_count, maximum_level = known[level]
                assert len(learned) == expected_count, (
                    discipline, level, len(learned), expected_count
                )
                if level in (1, 3, 5, 7, 9):
                    exclusive = [
                        ref for ref in gained
                        if powers[ref]["discipline"] == discipline
                    ]
                    assert len(exclusive) == 1
                    assert powers[exclusive[0]]["level"] == maximum_level


def validate_builders() -> None:
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    prototype = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")
    for level in range(1, 6):
        assert f"level{level}-powers.tpa" in driver
    for include in (
        "energy-ray-augment.tpa", "mind-vigor-augment.tpa", "animal-affinity.tpa"
    ):
        assert include in driver
    assert "COPY_EXISTING" not in prototype
    assert "ACTION_PHP_EACH" not in prototype

    for level, expected_refs in LEVEL_REFS.items():
        text = (ROOT / "lib" / f"level{level}-powers.tpa").read_text(encoding="utf-8")
        created = set(re.findall(fr"ps_resref = ~(PS{level}[A-Z0-9]+)~", text))
        assert created == expected_refs, (level, created ^ expected_refs)
        assert f"WRITE_LONG 0x34 {level}" in text
        assert "WRITE_LONG 0x18 ps_flags" in text

    level1 = (ROOT / "lib" / "level1-powers.tpa").read_text(encoding="utf-8")
    level2 = (ROOT / "lib" / "level2-powers.tpa").read_text(encoding="utf-8")
    affinity = (ROOT / "lib" / "animal-affinity.tpa").read_text(encoding="utf-8")

    required1 = {
        "PS1ERAY": ("opcode = 12", "dicesize = 6"),
        "PS1MTHR": ("dicesize = 10", "savingthrow = BIT0"),
        "PS1IARM": ("parameter1 = -4", "duration = 3600"),
        "PS1VIGR": ("opcode = 18", "opcode = 17"),
        "PS1FSCR": ("opcode = 206", "resource = ~SPWI112~"),
        "PS1ACON": ("opcode = 67", "resource = ~PSACON01~"),
        "PS1EPUS": ("opcode = 238", "savingthrow = BIT1"),
    }
    for resref, fragments in required1.items():
        body = resource_section(level1, "psion_create_level1_power", resref)
        for fragment in fragments:
            assert fragment in body, (resref, fragment)

    required2 = {
        "PS2AMOR": ("opcode = 65", "parameter1 = -2"),
        "PS2CBLS": ("dicenumber = 2", "dicesize = 6"),
        "PS2DHIN": ("opcode = 193", "opcode = 292"),
        "PS2TSHD": ("opcode = 31", "parameter1 = 20"),
        "PS2BIOF": ("ps_resist_opcode = 86", "ps_resist_opcode <= 89"),
        "PS2AAFF": ("opcode = 214", "resource = ~PS2AAFF~"),
        "PS2DSWP": ("opcode = 124", "parameter2 = 3"),
        "PS2BRLK": ("opcode = 175", "duration = 18"),
    }
    for resref, fragments in required2.items():
        body = resource_section(level2, "psion_create_level2_power", resref)
        for fragment in fragments:
            assert fragment in body, (resref, fragment)

    for resref, opcode in (("PSAASTR", "15"), ("PSAADEX", "44"), ("PSAACON", "10")):
        assert f"~{resref}~ => {opcode}" in affinity
        assert f"resource = ~{resref}~" in affinity


def validate_augmentation() -> None:
    augment = rows("psionaugment.2da")
    assert len(augment) == len({row[0] for row in augment}) == 57
    selectors = {
        "PS1ERAY": ("ps1eray.2da", 36),
        "PS1MTHR": ("ps1mthr.2da", 9),
        "PS1VIGR": ("ps1vigr.2da", 9),
        "PS2AAFF": ("ps2aaff.2da", 3),
    }
    all_children: set[str] = set()
    for parent, (filename, count) in selectors.items():
        data = rows(filename)
        assert len(data) == count
        children = {row[1] for row in data}
        assert children == {row[0] for row in augment if row[1] == parent}
        all_children |= children
    assert all_children == {row[0] for row in augment}


def validate_installer() -> None:
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert re.search(r"VERSION ~0\.[0-9]+\.0-alpha~", setup)
    for name in (
        "psionpool", "psionknown", "psiondisc", "psionskills", "psionfeats",
        "psionpowers", "psionaugment", "ps1eray", "ps1mthr", "ps1vigr",
        "ps2aaff", "mxpsion", "clabpsee", "clabpsha", "clabpkin",
        "clabpego", "clabpnom", "clabptel",
    ):
        assert name in setup
    for include in (
        "class-detect.tpa", "class-strings.tpa", "class-layout.tpa",
        "class-common.tpa", "class-skills.tpa",
    ):
        assert include in setup


def fake_table(name: str):
    columns, data = header(name), rows(name)

    class Table:
        names = [row[0] for row in data]
        values = {row[0]: dict(zip(columns, row[1:])) for row in data}

        def GetValue(self, row, column):
            return self.values[str(row)][column]

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

    return Table()


def validate_runtime() -> None:
    gemrb = types.ModuleType("GemRB")
    gui = types.ModuleType("GUICommon")
    stats = {(1, 38): 18, (1, 34): 3, (1, 188): 0, (1, 239): 0}
    tables = {
        name: fake_table(name + ".2da")
        for name in ("psionpool", "psionpowers", "psionaugment")
    }
    gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""
    gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)
    gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    gemrb.LoadTable = lambda name, *_: tables[name.lower()]
    gemrb.DisplayString = lambda *_: None

    old_gemrb, old_gui = sys.modules.get("GemRB"), sys.modules.get("GUICommon")
    sys.modules["GemRB"], sys.modules["GUICommon"] = gemrb, gui
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psion_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.ensure_pool(1) == 17
        assert module.can_manifest(1, "PS1ERAY")
        assert module.power_info("PSAADEX")["cost"] == 3
        assert module.filter_spellinfo(
            1, ["SPWI112", "PSRF01", "PSRF04", "PSAADEX"]
        ) == ["SPWI112", "PSRF01", "PSAADEX"]
        before = module.ensure_pool(1)
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before - 3
        stats[(1, 188)], stats[(1, 239)] = 1, 0
        assert not module.can_manifest(1, "PS2AAFF")
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_gui is None:
            sys.modules.pop("GUICommon", None)
        else:
            sys.modules["GUICommon"] = old_gui


def validate_patcher() -> None:
    path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_patcher_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions_text = '''import GemRB\nimport Spellbook\n\ndef ActionCastPressed ():\n\tif GemRB.GetVar ("SettingButtons"):\n\t\treturn\n\ndef ActionInnatePressed ():\n\tif GemRB.GetVar ("SettingButtons"):\n\t\treturn\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tSpell = GemRB.GetVar ("Spell")\n'''
    spellbook_text = '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\treturn memorizedSpells\n'''
    rest_text = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        actions = folder / "ActionsWindow.py"
        spellbook = folder / "Spellbook.py"
        menu = folder / "MenuWindow.py"
        store = folder / "GUISTORE.py"
        actions.write_text(actions_text, encoding="utf-8")
        spellbook.write_text(spellbook_text, encoding="utf-8")
        menu.write_text(rest_text, encoding="utf-8")
        store.write_text(rest_text, encoding="utf-8")

        assert module.patch(actions, "actions")
        assert module.patch(spellbook, "spellbook")
        assert module.patch(menu, "rest")
        assert module.patch(store, "rest")
        assert "Psionics.begin_manifest" in actions.read_text(encoding="utf-8")
        assert "Psionics.filter_spellinfo" in spellbook.read_text(encoding="utf-8")
        assert not module.patch(actions, "actions")
        assert module.remove(actions)
        assert module.remove(spellbook)
        assert actions.read_text(encoding="utf-8") == actions_text
        assert spellbook.read_text(encoding="utf-8") == spellbook_text


def main() -> None:
    validate_tables()
    validate_progressions()
    validate_builders()
    validate_augmentation()
    validate_installer()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    validate_runtime()
    validate_patcher()
    print("Psion core table, builder, runtime, and GUI-hook validation passed.")


if __name__ == "__main__":
    main()
