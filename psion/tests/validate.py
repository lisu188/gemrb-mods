#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import py_compile
import re
import tempfile

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
    "PS1ERAY",
    "PS1MTHR",
    "PS1IARM",
    "PS1VIGR",
    "PS1FSCR",
    "PS1EMND",
    "PS1PREC",
    "PS1ACON",
    "PS1EPUS",
    "PS1TSKN",
    "PS1BRST",
    "PS1CHAR",
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


def validate_2da_schemas():
    expected = {
        "psionpowers.2da": [
            "NAME",
            "LEVEL",
            "DISCIPLINE",
            "BASE_COST",
            "AUGMENT_STEP",
            "TEMPLATE",
        ],
        "psiondisc.2da": ["DISCIPLINE", "SCHOOL", "SPECIAL_SKILL"],
        "psionskills.2da": [
            "ABILITY",
            "ACCESS",
            "COST",
            "BREAK1",
            "BREAK2",
            "BREAK3",
        ],
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
    assert [int(row[2]) for row in powers].count(1) == 12

    known_by_level = {int(row[0]): (int(row[1]), int(row[2])) for row in known}
    metadata = {
        row[0]: {"level": int(row[2]), "discipline": row[3]} for row in powers
    }

    for discipline, filename in DISCIPLINE_CLABS.items():
        learned = []
        for row in rows(filename):
            level = int(row[0])
            newly_learned = [token[3:] for token in row[1:] if token.startswith("GA_PS")]
            learned.extend(newly_learned)
            assert len(learned) == len(set(learned)), (discipline, "duplicate power")
            assert set(learned) <= set(metadata), (discipline, "unknown power")
            assert all(
                metadata[ref]["discipline"] in ("GENERAL", discipline)
                for ref in learned
            ), (discipline, "off-discipline power")

            if level <= 9:
                expected_count, maximum_level = known_by_level[level]
                assert len(learned) == expected_count, (
                    discipline,
                    level,
                    len(learned),
                    expected_count,
                )
                if level in (1, 3, 5, 7, 9):
                    exclusive = [
                        ref
                        for ref in newly_learned
                        if metadata[ref]["discipline"] == discipline
                    ]
                    assert len(exclusive) == 1
                    assert metadata[exclusive[0]]["level"] == maximum_level


def validate_level1_builders():
    exact_path = ROOT / "lib" / "level1-powers.tpa"
    exact = exact_path.read_text(encoding="utf-8")
    powers_driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    prototype = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")

    assert "level1-powers.tpa" in powers_driver
    assert "psion_level > 1" in prototype

    # SPL V1 correctness: level and flags must use 0x34 and 0x18. The old alpha
    # accidentally wrote them to 0x24 and 0x14.
    assert "WRITE_LONG 0x34 psion_level" in prototype
    assert "WRITE_LONG 0x18 (THIS | BIT25)" in prototype
    assert "WRITE_SHORT 0x24" not in prototype
    assert "WRITE_LONG 0x14" not in prototype
    assert "WRITE_LONG 0x34 1" in exact
    assert "WRITE_LONG 0x18 ps_flags" in exact

    created = set(re.findall(r"ps_resref = ~(PS1[A-Z0-9]+)~", exact))
    assert created == LEVEL1_REFS, (created, LEVEL1_REFS)

    # Guard the intended implementation primitives for every major behavior.
    required_fragments = {
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
    for index, ref in enumerate(sorted(LEVEL1_REFS)):
        start = exact.index(f"ps_resref = ~{ref}~")
        later = [
            exact.find(f"ps_resref = ~{other}~", start + 1)
            for other in LEVEL1_REFS
            if exact.find(f"ps_resref = ~{other}~", start + 1) != -1
        ]
        end = min(later) if later else len(exact)
        section = exact[start:end]
        for fragment in required_fragments[ref]:
            assert fragment in section, (ref, fragment)


def validate_installer_references():
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    for table in (
        "psionpool",
        "psionknown",
        "psiondisc",
        "psionskills",
        "psionfeats",
        "psionpowers",
        "mxpsion",
        "clabpsee",
        "clabpsha",
        "clabpkin",
        "clabpego",
        "clabpnom",
        "clabptel",
    ):
        assert table in setup

    for include in (
        "class-detect.tpa",
        "class-strings.tpa",
        "class-layout.tpa",
        "class-common.tpa",
        "class-skills.tpa",
    ):
        assert include in setup

    skills = (ROOT / "lib" / "class-skills.tpa").read_text(encoding="utf-8")
    for clab in ("CLABPSEE", "CLABPSHA", "CLABPKIN", "CLABPEGO", "CLABPNOM", "CLABPTEL"):
        assert clab in skills

    power_data = (ROOT / "lib" / "power-data.tpa").read_text(encoding="utf-8")
    generated = set(re.findall(r"~(PS[0-9A-Z]+)~ =>", power_data))
    defined = {row[0] for row in rows("psionpowers.2da")}
    assert defined <= generated


def validate_gui_patcher():
    patcher_path = ROOT / "tools" / "install_guiscripts.py"
    spec = importlib.util.spec_from_file_location("psion_gui_patcher", patcher_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    actions_fixture = '''import GemRB\nimport Spellbook\n\ndef ActionCastPressed ():\n\t"""Opens the spell choice scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_CAST)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\t"""Opens the innate spell scrollbar."""\n\n\tif GemRB.GetVar ("SettingButtons"):\n\t\tSaveActionButton (ACT_INNATE)\n\t\treturn\n\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\n\tSpell = GemRB.GetVar ("Spell")\n'''
    rest_fixture = '''import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n'''

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        actions = directory / "ActionsWindow.py"
        menu = directory / "MenuWindow.py"
        store = directory / "GUISTORE.py"
        actions.write_text(actions_fixture, encoding="utf-8")
        menu.write_text(rest_fixture, encoding="utf-8")
        store.write_text(rest_fixture, encoding="utf-8")

        assert module.patch(actions, "actions")
        assert module.patch(menu, "rest")
        assert module.patch(store, "rest")
        patched = actions.read_text(encoding="utf-8")
        assert "Psionics.begin_manifest" in patched
        assert patched.count("Psionics.cancel_pending") == 2
        assert "import Psionics" in patched
        assert not module.patch(actions, "actions")

        assert module.remove(actions)
        assert actions.read_text(encoding="utf-8") == actions_fixture


def main():
    validate_2da_schemas()
    validate_progressions()
    validate_level1_builders()
    validate_installer_references()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    validate_gui_patcher()
    print("Psion 0.3 static, level-1 resource, and GUI-hook validation passed.")


if __name__ == "__main__":
    main()
