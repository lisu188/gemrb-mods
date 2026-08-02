#!/usr/bin/env python3
"""Version-neutral Psion table, progression, builder, and installer checks."""

from pathlib import Path
import py_compile
import re

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
    1: {"PS1ERAY", "PS1MTHR", "PS1IARM", "PS1VIGR", "PS1FSCR", "PS1EMND", "PS1PREC", "PS1ACON", "PS1EPUS", "PS1TSKN", "PS1BRST", "PS1CHAR"},
    2: {"PS2AMOR", "PS2CBLS", "PS2DHIN", "PS2TSHD", "PS2BIOF", "PS2SWCR", "PS2CLAI", "PS2RPRD", "PS2EMIS", "PS2AAFF", "PS2DSWP", "PS2BRLK"},
    3: {"PS3DPSI", "PS3BADJ", "PS3EBLT", "PS3MBAR", "PS3TSGT", "PS3THOP", "PS3DANG", "PS3COCO", "PS3ECON", "PS3HUST", "PS3SSTP", "PS3MSTL"},
    4: {"PS4EADP", "PS4FOMV", "PS4DDOR", "PS4IFOR", "PS4TKMN", "PS4PLEE", "PS4RVIE", "PS4WECT", "PS4EBAL", "PS4META", "PS4PFLY", "PS4COMP"},
    5: {"PS5ADBD", "PS5CATP", "PS5PRES", "PS5COGL", "PS5TRUE", "PS5TELE", "PS5SCHN", "PS5HOCR", "PS5ECUR", "PS5PFDB", "PS5BALT", "PS5MPRB"},
}


def lines(name: str) -> list[str]:
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name: str) -> list[str]:
    return lines(name)[2].split()


def rows(name: str) -> list[list[str]]:
    return [
        line.split()
        for line in lines(name)[3:]
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]


def section(text: str, function: str, resref: str) -> str:
    marker = f"ps_resref = ~{resref}~"
    marker_pos = text.index(marker)
    start = text.rfind(f"LAF {function}", 0, marker_pos)
    assert start >= 0, (resref, "missing builder call")
    next_start = text.find(f"LAF {function}", marker_pos + len(marker))
    return text[start : next_start if next_start >= 0 else len(text)]


def validate_tables() -> None:
    expected = {
        "psionpowers.2da": ["NAME", "LEVEL", "DISCIPLINE", "BASE_COST", "AUGMENT_STEP", "TEMPLATE"],
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

    powers = rows("psionpowers.2da")
    assert len(powers) == len({row[0] for row in powers}) == 60
    for level, expected_refs in LEVEL_REFS.items():
        actual = {row[0] for row in powers if int(row[2]) == level}
        assert actual == expected_refs, (level, actual ^ expected_refs)
        assert all(int(row[4]) == 2 * level - 1 for row in powers if int(row[2]) == level)
    assert len(rows("psionpool.2da")) == len(rows("psionknown.2da")) == 20


def validate_progressions() -> None:
    known = {int(row[0]): (int(row[1]), int(row[2])) for row in rows("psionknown.2da")}
    powers = {row[0]: {"level": int(row[2]), "discipline": row[3]} for row in rows("psionpowers.2da")}

    for discipline, filename in DISCIPLINE_CLABS.items():
        learned: list[str] = []
        for row in rows(filename):
            level = int(row[0])
            gained = [token[3:] for token in row[1:] if token.startswith("GA_PS")]
            learned.extend(gained)
            assert len(learned) == len(set(learned)), (discipline, "duplicate power")
            assert set(learned) <= set(powers), (discipline, "unknown power")
            assert all(powers[ref]["discipline"] in ("GENERAL", discipline) for ref in learned)
            if level <= 9:
                expected_count, maximum = known[level]
                assert len(learned) == expected_count, (discipline, level)
                if level in (1, 3, 5, 7, 9):
                    exclusive = [ref for ref in gained if powers[ref]["discipline"] == discipline]
                    assert len(exclusive) == 1
                    assert powers[exclusive[0]]["level"] == maximum


def validate_weidu_integer_syntax() -> None:
    """Reject forms that WeiDU 251 does not accept in INT_VAR expressions."""
    bare_negative = re.compile(
        r"\b(?:parameter1|parameter2|duration|timing|target|range|speed|"
        r"projectile|opcode|resist_dispel|dicenumber|dicesize|savingthrow|special)"
        r"\s*=\s*-\d+"
    )
    negative_long = re.compile(r"\bWRITE_(?:S?LONG)\s+\S+\s+-\d+")

    for path in sorted((ROOT / "lib").glob("*.tpa")):
        text = path.read_text(encoding="utf-8")
        match = bare_negative.search(text)
        assert not match, (path.name, match.group(0) if match else "")
        match = negative_long.search(text)
        assert not match, (path.name, match.group(0) if match else "")


def validate_release_infrastructure() -> None:
    """Lock the self-contained installer and all 1.0 lifecycle fixtures."""
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    includes = re.findall(r"INCLUDE ~psion/lib/([^~]+)~", driver)
    assert includes[0] == "spell-functions.tpa", includes

    helpers = (ROOT / "lib" / "spell-functions.tpa").read_text(encoding="utf-8")
    for fragment in (
        "DEFINE_PATCH_FUNCTION ~ADD_SPELL_HEADER~",
        "DEFINE_PATCH_FUNCTION ~ADD_SPELL_EFFECT~",
        "INSERT_BYTES ps_new_header 0x28",
        "INSERT_BYTES ps_new_effect 0x30",
        "WRITE_SHORT 0x68 (ps_header_count + 1)",
    ):
        assert fragment in helpers, fragment

    detector = (ROOT / "lib" / "class-detect.tpa").read_text(encoding="utf-8")
    for fragment in (
        "INDEX_BUFFER (~BIOGRAPHY~)",
        "SET ps_detect_cols = 10",
        "SET ps_detect_cols = 19",
        "READ_2DA_ENTRY ps_i 6 ps_detect_cols ps_id",
    ):
        assert fragment in detector, fragment

    fixture = (ROOT / "tests" / "make_weidu_fixture.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "tests" / "validate_weidu_install.sh").read_text(encoding="utf-8")
    for layout in ("normalized", "native", "legacy"):
        assert layout in fixture, layout
        assert layout in lifecycle, layout
    for fragment in (
        "SPL V1  ",
        "header_offset + header_count * 0x28",
        "effect_offset + maximum_effect * 0x30",
        "verify_uninstalled",
        "install\nverify_installed\nuninstall\nverify_uninstalled\ninstall\nverify_installed",
    ):
        assert fragment in lifecycle, fragment

    runtime = (ROOT / "guiscripts" / "Psionics.py").read_text(encoding="utf-8")
    patcher = (ROOT / "tools" / "install_guiscripts.py").read_text(encoding="utf-8")
    for fragment in (
        "def refresh_innate_charges(actor):",
        "GemRB.GetKnownSpellsCount",
        "GemRB.UnmemorizeSpell",
        "GemRB.MemorizeSpell",
        "POOL_STATE_SIGNATURE = 0x50530000",
        "CURRENT_POOL_STAT = 239",
        "def resolve_power_entry(spellbook, actor, raw_spell):",
    ):
        assert fragment in runtime, fragment
    assert "POOL_READY_STAT" not in runtime
    assert "Psionics.refresh_innate_charges" in patcher
    assert "spellResRefs = Psionics.filter_spellinfo" not in patcher
    assert "memorizedSpells = [entry for entry in memorizedSpells if entry[\"SpellResRef\"] in psionAllowedResRefs]" in patcher


def validate_builders() -> None:
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    compatibility = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")
    assert "COPY_EXISTING" not in compatibility
    assert "ACTION_PHP_EACH" not in compatibility

    for level, expected_refs in LEVEL_REFS.items():
        filename = f"level{level}-powers.tpa"
        assert filename in driver
        text = (ROOT / "lib" / filename).read_text(encoding="utf-8")
        created = set(re.findall(fr"ps_resref = ~(PS{level}[A-Z0-9]+)~", text))
        assert created == expected_refs, (level, created ^ expected_refs)
        assert f"WRITE_LONG 0x34 {level}" in text
        assert "WRITE_LONG 0x18 ps_flags" in text

    level1 = (ROOT / "lib" / "level1-powers.tpa").read_text(encoding="utf-8")
    level2 = (ROOT / "lib" / "level2-powers.tpa").read_text(encoding="utf-8")
    affinity = (ROOT / "lib" / "animal-affinity.tpa").read_text(encoding="utf-8")
    mind_vigor = (ROOT / "lib" / "mind-vigor-augment.tpa").read_text(encoding="utf-8")

    checks = {
        "PS1ERAY": (level1, "psion_create_level1_power", ("opcode = 12", "dicesize = 6")),
        "PS1MTHR": (level1, "psion_create_level1_power", ("dicesize = 10", "savingthrow = BIT0")),
        "PS1VIGR": (level1, "psion_create_level1_power", ("opcode = 18", "opcode = 17")),
        "PS1FSCR": (level1, "psion_create_level1_power", ("opcode = 0", "parameter1 = (0 - 4)", "opcode = 206")),
        "PS1PREC": (level1, "psion_create_level1_power", ("opcode = 54", "parameter1 = 1", "parameter1 = (0 - 1)")),
        "PS1ACON": (level1, "psion_create_level1_power", ("opcode = 67", "resource = ~PSACON01~")),
        "PS1BRST": (level1, "psion_create_level1_power", ("opcode = 126", "parameter1 = 130", "parameter2 = 2")),
        "PS2AMOR": (level2, "psion_create_level2_power", ("opcode = 65", "parameter1 = (0 - 2)")),
        "PS2BIOF": (level2, "psion_create_level2_power", ("ps_resist_opcode = 86", "ps_resist_opcode <= 89")),
        "PS2AAFF": (level2, "psion_create_level2_power", ("opcode = 214", "resource = ~PS2AAFF~")),
        "PS2DSWP": (level2, "psion_create_level2_power", ("opcode = 124", "parameter2 = 3")),
    }
    for resref, (text, function, fragments) in checks.items():
        body = section(text, function, resref)
        for fragment in fragments:
            assert fragment in body, (resref, fragment)

    precognition = section(level1, "psion_create_level1_power", "PS1PREC")
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = 1" in precognition
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = (0 - 1)" not in precognition

    for resref, opcode in (("PSAASTR", "44"), ("PSAADEX", "15"), ("PSAACON", "10")):
        assert f"~{resref}~ => {opcode}" in affinity
        assert f"resource = ~{resref}~" in affinity

    assert "savebonus = ps_save_penalty" in mind_vigor
    assert "save_bonus = ps_save_penalty" not in mind_vigor

    # Mind Thrust augments damage by 1d10 per additional power point, and the
    # save DC by 1 for each extra 2d10, so the penalty is floor((cost - 1) / 2).
    assert "dicenumber = ps_cost" in mind_vigor
    assert (
        "ps_save_penalty = (psion_level1_save_penalty - ((ps_cost - 1) / 2))"
        in mind_vigor
    )


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


def validate_save_dc_scheme() -> None:
    """Every save-bearing effect carries its power level's save penalty.

    D&D 3.5 sets a power's save DC at 10 + power level + key ability modifier.
    The engine has no DC, so the translation splits into a power-level term of
    -(N - 1) and the guaranteed key-ability term from the Intelligence 15
    chargen minimum. This check pins both constants and the fact that no
    save-bearing effect is left without one, which is the shape of regression
    that silently reverts the scheme.
    """
    shared = (ROOT / "lib" / "power-data.tpa").read_text(encoding="utf-8")
    assert "OUTER_SET psion_key_ability_save_penalty = (0 - 2)" in shared

    for level in range(1, 6):
        text = (ROOT / "lib" / f"level{level}-powers.tpa").read_text(encoding="utf-8")
        constant = f"psion_level{level}_save_penalty"
        expected = (
            "psion_key_ability_save_penalty"
            if level == 1
            else f"(psion_key_ability_save_penalty - {level - 1})"
        )
        assert f"OUTER_SET {constant} = {expected}" in text, (level, expected)

    # Walk every module, not just the level builders. The augment modules
    # delete and rebuild some level-1 resources, so a check scoped to
    # level*-powers.tpa would pass while the resources players actually
    # manifest carry no penalty at all.
    for path in sorted((ROOT / "lib").glob("*.tpa")):
        body = path.read_text(encoding="utf-8")
        rendered = body.splitlines()
        for number, line in enumerate(rendered, start=1):
            if "savingthrow = BIT" not in line:
                continue
            # The multi-line INT_VAR form puts savebonus on its own line.
            following = rendered[number] if number < len(rendered) else ""
            if "save_penalty" in line or "save_penalty" in following:
                continue
            raise AssertionError(
                f"{path.name}:{number} sets a saving throw without a save penalty"
            )


def validate_installer() -> None:
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "VERSION ~1.0.0~" in setup
    for name in (
        "psionpool", "psionknown", "psiondisc", "psionskills", "psionfeats",
        "psionpowers", "psionaugment", "ps1eray", "ps1mthr", "ps1vigr",
        "ps2aaff", "mxpsion", "clabpsee", "clabpsha", "clabpkin",
        "clabpego", "clabpnom", "clabptel",
    ):
        assert name in setup
    for include in ("class-detect.tpa", "class-strings.tpa", "class-layout.tpa", "class-common.tpa", "class-skills.tpa"):
        assert include in setup


def main() -> None:
    validate_tables()
    validate_progressions()
    validate_weidu_integer_syntax()
    validate_release_infrastructure()
    validate_builders()
    validate_augmentation()
    validate_save_dc_scheme()
    validate_installer()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    print("Psion core table, progression, builder, and installer validation passed.")


if __name__ == "__main__":
    main()
