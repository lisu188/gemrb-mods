#!/usr/bin/env python3
"""Version-neutral Psion table, progression, builder, and installer checks."""

from pathlib import Path
import py_compile
import re

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "common"

DISCIPLINE_CLABS = {
    "SEER": "clabpsee.2da",
    "SHAPER": "clabpsha.2da",
    "KINETICIST": "clabpkin.2da",
    "EGOIST": "clabpego.2da",
    "NOMAD": "clabpnom.2da",
    "TELEPATH": "clabptel.2da",
}

LEVEL_REFS = {
    1: {"PS1ERAY", "PS1MTHR", "PS1IARM", "PS1VIGR", "PS1FSCR", "PS1EMND", "PS1PREC", "PS1ACON", "PS1MAGI", "PS1TSKN", "PS1BRST", "PS1CHAR"},
    2: {"PS2AMOR", "PS2CBLS", "PS2DHIN", "PS2TSHD", "PS2BIOF", "PS2SWCR", "PS2CLAI", "PS2RPRD", "PS2EMIS", "PS2AAFF", "PS2DSWP", "PS2BRLK", "PS2EPUS"},
    3: {"PS3DPSI", "PS3BADJ", "PS3EBLT", "PS3MBAR", "PS3TSGT", "PS3THOP", "PS3DANG", "PS3COCO", "PS3ECON", "PS3HUST", "PS3SSTP", "PS3CBRE"},
    4: {"PS4EADP", "PS4FOMV", "PS4DDOR", "PS4IFOR", "PS4TKMN", "PS4PLEE", "PS4RVIE", "PS4WECT", "PS4EBAL", "PS4META", "PS4PFLY", "PS4COMP"},
    5: {"PS5ADBD", "PS5CATP", "PS5PRES", "PS5PCRU", "PS5TRUE", "PS5TELE", "PS5SCHN", "PS5HOCR", "PS5ECUR", "PS5PFDB", "PS5BALT", "PS5MPRB"},
    6: {"PS6GPRE", "PS6CRYS", "PS6DBUF", "PS6REST", "PS6BANI", "PS6MSWI"},
    7: {"PS7FATE", "PS7MCOC", "PS7RDOP", "PS7FISS", "PS7EJNT", "PS7CLIF"},
    8: {"PS8HYPC", "PS8ASED", "PS8TKSP", "PS8FUSN", "PS8MTHP", "PS8MSED"},
    9: {"PS9META", "PS9TCRE", "PS9TORN", "PS9GMET", "PS9TCIR", "PS9PCHI"},
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
        "psionpowers.2da": ["NAME", "LEVEL", "DISCIPLINE", "BASE_COST", "TEMPLATE"],
        "psionaugment.2da": ["PARENT", "TOTAL_COST", "EFFECT", "VALUE"],
        "ps1eray.2da": ["ResRef", "Type"],
        "ps1mthr.2da": ["ResRef", "Type"],
        "ps1vigr.2da": ["ResRef", "Type"],
        "ps2aaff.2da": ["ResRef", "Type"],
        "psiondisc.2da": ["DISCIPLINE", "SCHOOL", "SPECIAL_SKILL"],
        "psionskills.2da": ["ABILITY", "ACCESS", "COST", "BREAK1", "BREAK2", "BREAK3"],
        "psionfeats.2da": ["MIN_LEVEL", "FOCUS", "PP_SURCHARGE"],
        "pspick.2da": ["ResRef", "Type"],
    }
    for filename, columns in expected.items():
        assert header(filename) == columns, (filename, header(filename), columns)
        assert all(len(row) == len(columns) + 1 for row in rows(filename)), filename

    powers = rows("psionpowers.2da")
    assert len(powers) == len({row[0] for row in powers}) == 85
    for level, expected_refs in LEVEL_REFS.items():
        actual = {row[0] for row in powers if int(row[2]) == level}
        assert actual == expected_refs, (level, actual ^ expected_refs)
        assert all(int(row[4]) == 2 * level - 1 for row in powers if int(row[2]) == level)
    assert len(rows("psionpool.2da")) == len(rows("psionknown.2da")) == 20


def validate_progressions() -> None:
    known = {int(row[0]): (int(row[1]), int(row[2])) for row in rows("psionknown.2da")}
    assert known[1] == (3, 1)
    assert known[20] == (36, 9)
    previous_known = previous_max = 0
    for level in range(1, 21):
        current_known, current_max = known[level]
        assert current_known >= previous_known
        assert current_max >= previous_max
        previous_known, previous_max = current_known, current_max

    for discipline, filename in DISCIPLINE_CLABS.items():
        data = rows(filename)
        assert len(data) == 20, (discipline, len(data))
        level1 = next(row for row in data if row[0] == "1")
        utilities = {token for token in level1[1:] if token != "****"}
        assert utilities == {"GA_PXPLRN", "GA_PXCNTR", "GA_PXFSEL", "GA_PXSKILL"}, (discipline, utilities)
        for row in data:
            assert not any(token.startswith("GA_PS") for token in row[1:]), (discipline, row)
            if row[0] != "1":
                assert all(token == "****" for token in row[1:]), (discipline, row)


def validate_learnable_powers() -> None:
    catalogue = [row[0] for row in rows("psionpowers.2da")]
    picks = rows("pspick.2da")
    assert [row[0] for row in picks] == catalogue
    assert len(picks) == len({row[1] for row in picks}) == len(catalogue) == 85
    for index, row in enumerate(picks, 1):
        assert row == [catalogue[index - 1], f"PXL{index:04d}", "3"], row


def validate_weidu_integer_syntax() -> None:
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
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    shared_includes = re.findall(r"INCLUDE ~(common/weidu/[^~]+)~", driver)
    psion_includes = re.findall(r"INCLUDE ~psion/lib/([^~]+)~", driver)
    assert shared_includes == ["common/weidu/spell-functions.tpa"], shared_includes
    for level in range(1, 10):
        assert f"level{level}-powers.tpa" in psion_includes, level

    compatibility = (ROOT / "lib" / "spell-functions.tpa").read_text(encoding="utf-8")
    assert "INCLUDE ~common/weidu/spell-functions.tpa~" in compatibility
    helpers = (COMMON / "weidu" / "spell-functions.tpa").read_text(encoding="utf-8")
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
        "COUNT_2DA_COLS ps_clskills_cols",
        "OUTER_SET ps_seer_id = ps_clskills_rows",
        "ps_telepath_id > 31",
        "INDEX_BUFFER (~NAME_REF~)",
        "INDEX_BUFFER (~CAP_REF~)",
        "ps_detect_classes_cols = 7",
        "ps_detect_classes_cols = 19",
        "INDEX_BUFFER (~BIOGRAPHY~)",
        "INDEX_BUFFER (~FALLEN_NOTICE~)",
        "ps_detect_text_cols = 9",
        "LOOKUP_IDS_SYMBOL_OF_INT",
    ):
        assert fragment in detector, fragment
    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in detector
    assert "COUNT_2DA_COLS ps_classes_cols" not in detector
    assert "COUNT_2DA_COLS ps_text_cols" not in detector

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
        'cp -R "$repo_root/common" "$game/common"',
    ):
        assert fragment in lifecycle, fragment

    runtime = (ROOT / "guiscripts" / "Psionics.py").read_text(encoding="utf-8")
    for fragment in (
        "import Transactions",
        "import InnateCharges",
        "import PersistentState",
        "import Selectors",
        "POOL_STATE_SIGNATURE = 0x50530000",
        "CURRENT_POOL_STAT = 239",
        "def resolve_power_entry(spellbook, actor, raw_spell):",
    ):
        assert fragment in runtime, fragment
    assert "POOL_READY_STAT" not in runtime

    shared_charges = (COMMON / "guiscripts" / "InnateCharges.py").read_text(encoding="utf-8")
    for fragment in (
        "GemRB.GetKnownSpellsCount",
        "GemRB.UnmemorizeSpell",
        "GemRB.MemorizeSpell",
    ):
        assert fragment in shared_charges, fragment

    patcher = (ROOT / "tools" / "install_guiscripts.py").read_text(encoding="utf-8")
    for fragment in (
        'CORE = ROOT / "common" / "tools" / "install_guiscripts.py"',
        'module.main_for_handler("Psionics"',
    ):
        assert fragment in patcher, fragment
    core_patcher = (COMMON / "tools" / "install_guiscripts.py").read_text(encoding="utf-8")
    for fragment in (
        "GemRBModCore.refresh_innate_charges",
        "GemRBModCore.filter_spellinfo",
        "GemRBModCore.begin_spell",
        "_migrate_legacy_runtime_ownership",
    ):
        assert fragment in core_patcher, fragment


def validate_builders() -> None:
    driver = (ROOT / "lib" / "powers.tpa").read_text(encoding="utf-8")
    compatibility = (ROOT / "lib" / "power-build.tpa").read_text(encoding="utf-8")
    assert "COPY_EXISTING" not in compatibility
    assert "ACTION_PHP_EACH" not in compatibility
    augment_modules = {"PS2SWCR": "swarm-augment.tpa"}

    level_text = {}
    for level, expected_refs in LEVEL_REFS.items():
        filename = f"level{level}-powers.tpa"
        assert filename in driver
        text = (ROOT / "lib" / filename).read_text(encoding="utf-8")
        level_text[level] = text
        created = set(re.findall(fr"ps_resref = ~(PS{level}[A-Z0-9]+)~", text))
        for resref, module in augment_modules.items():
            if resref not in expected_refs:
                continue
            assert module in driver, module
            module_text = (ROOT / "lib" / module).read_text(encoding="utf-8")
            assert f"ps_resref = ~{resref}~" in module_text, (resref, module)
            assert resref not in created, (resref, filename)
            created.add(resref)
        assert created == expected_refs, (level, created ^ expected_refs)
        assert f"WRITE_LONG 0x34 {level}" in text
        assert "WRITE_LONG 0x18 ps_flags" in text

    level1 = level_text[1]
    level2 = level_text[2]
    affinity = (ROOT / "lib" / "animal-affinity.tpa").read_text(encoding="utf-8")
    mind_vigor = (ROOT / "lib" / "mind-vigor-augment.tpa").read_text(encoding="utf-8")

    checks = {
        "PS1ERAY": (1, ("opcode = 12", "dicesize = 6")),
        "PS1MTHR": (1, ("dicesize = 10", "savingthrow = BIT0")),
        "PS1VIGR": (1, ("opcode = 18", "opcode = 17")),
        "PS1PREC": (1, ("opcode = 54", "parameter1 = 1", "parameter1 = (0 - 1)")),
        "PS1ACON": (1, ("opcode = 67", "resource = ~PSACON01~")),
        "PS1BRST": (1, ("opcode = 126", "parameter1 = 130", "parameter2 = 2")),
        "PS2AMOR": (2, ("opcode = 65", "parameter1 = (0 - 2)")),
        "PS2BIOF": (2, ("ps_resist_opcode = 86", "ps_resist_opcode <= 89")),
        "PS2AAFF": (2, ("opcode = 214", "resource = ~PS2AAFF~")),
        "PS2DSWP": (2, ("opcode = 124", "parameter2 = 3")),
        "PS6CRYS": (6, ("opcode = 134", "savingthrow = BIT2")),
        "PS6DBUF": (6, ("opcode = 101", "parameter2 = 58")),
        "PS6REST": (6, ("opcode = 224",)),
        "PS6BANI": (6, ("opcode = 213", "duration = 30")),
        "PS6MSWI": (6, ("opcode = 5", "duration = 30")),
        "PS7MCOC": (7, ("opcode = 175", "Fireball_Just_Projectile")),
        "PS7RDOP": (7, ("opcode = 199", "ps_bounce_level <= 9")),
        "PS7FISS": (7, ("opcode = 1", "parameter1 = 1")),
        "PS7EJNT": (7, ("opcode = 126", "parameter1 = 150", "parameter2 = 2")),
        "PS7CLIF": (7, ("opcode = 146", "resource = ~PS7CLIB~", "dicenumber = 7", "savingthrow = BIT2")),
        "PS8HYPC": (8, ("opcode = 91", "parameter1 = 100")),
        "PS8ASED": (8, ("ps_resist_opcode = 86", "parameter1 = 25")),
        "PS8TKSP": (8, ("opcode = 146", "resource = ~PS8TKSB~", "opcode = 175", "parameter1 = 50")),
        "PS8FUSN": (8, ("opcode = 44", "opcode = 15", "opcode = 10", "parameter1 = 6")),
        "PS8MTHP": (8, ("opcode = 213", "Fireball_Just_Projectile")),
        "PS8MSED": (8, ("opcode = 5", "duration = 600")),
        "PS9META": (9, ("opcode = 193", "opcode = 91", "parameter1 = 100")),
        "PS9TCRE": (9, ("opcode = 67", "resource = ~PSACON01~")),
        "PS9TORN": (9, ("Fireball_Just_Projectile", "ps_description = ~A violent vortex deals 17d6")),
        "PS9GMET": (9, ("opcode = 44", "parameter1 = 8", "parameter1 = 40")),
        "PS9TCIR": (9, ("opcode = 124", "parameter2 = 1")),
        "PS9PCHI": (9, ("opcode = 224", "parameter2 = 5", "parameter2 = 128")),
    }
    for resref, (level, fragments) in checks.items():
        body = section(level_text[level], f"psion_create_level{level}_power", resref)
        for fragment in fragments:
            assert fragment in body, (resref, fragment)

    precognition = section(level1, "psion_create_level1_power", "PS1PREC")
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = 1" in precognition
    assert "opcode = 54 target = 1 resist_dispel = BIT1 parameter1 = (0 - 1)" not in precognition

    for resref, opcode in (
        ("PSAASTR", "44"), ("PSAADEX", "15"), ("PSAACON", "10"), ("PSAACHA", "6")
    ):
        assert f"~{resref}~ => {opcode}" in affinity
    assert "resource = ~%ps_resref%~" in affinity
    for resref in ("PSAASTR", "PSAADEX", "PSAACON", "PSAACHA"):
        assert f"resource = ~{resref}~" not in affinity

    assert "savebonus = ps_save_penalty" in mind_vigor
    assert "save_bonus = ps_save_penalty" not in mind_vigor
    assert "dicenumber = ps_cost" in mind_vigor
    assert "ps_save_penalty = (psion_level1_save_penalty - ((ps_cost - 1) / 2))" in mind_vigor


def augment_ceiling() -> int:
    text = (ROOT / "lib" / "power-data.tpa").read_text(encoding="utf-8")
    match = re.search(r"OUTER_SET psion_max_augment_cost = (\d+)", text)
    assert match, "power-data.tpa must define psion_max_augment_cost"
    return int(match.group(1))


def validate_augmentation() -> None:
    ceiling = augment_ceiling()
    generator = (ROOT / "tools" / "generate_augment_tables.py").read_text(encoding="utf-8")
    match = re.search(r"^MAX_AUGMENT_COST = (\d+)$", generator, re.MULTILINE)
    assert match, "the generator must define MAX_AUGMENT_COST"
    assert int(match.group(1)) == ceiling

    augment = rows("psionaugment.2da")
    expected = {
        "PS1ERAY": ("ps1eray.2da", 4 * ceiling),
        "PS1MTHR": ("ps1mthr.2da", ceiling),
        "PS1VIGR": ("ps1vigr.2da", ceiling),
        "PS2SWCR": ("ps2swcr.2da", ceiling - 2),
        "PS2AAFF": ("ps2aaff.2da", 4),
    }
    total = sum(count for _, count in expected.values())
    assert len(augment) == len({row[0] for row in augment}) == total
    for row in augment:
        assert 1 <= int(row[2]) <= ceiling, row

    all_children: set[str] = set()
    for parent, (filename, count) in expected.items():
        data = rows(filename)
        assert len(data) == count
        children = {row[1] for row in data}
        assert children == {row[0] for row in augment if row[1] == parent}
        all_children |= children
    assert all_children == {row[0] for row in augment}


def validate_save_dc_scheme() -> None:
    shared = (ROOT / "lib" / "power-data.tpa").read_text(encoding="utf-8")
    assert "OUTER_SET psion_key_ability_save_penalty = (0 - 2)" in shared

    for level in range(1, 10):
        text = (ROOT / "lib" / f"level{level}-powers.tpa").read_text(encoding="utf-8")
        constant = f"psion_level{level}_save_penalty"
        expected = (
            "psion_key_ability_save_penalty"
            if level == 1
            else f"(psion_key_ability_save_penalty - {level - 1})"
        )
        assert f"OUTER_SET {constant} = {expected}" in text, (level, expected)

    for path in sorted((ROOT / "lib").glob("*.tpa")):
        rendered = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(rendered, start=1):
            if "savingthrow = BIT" not in line:
                continue
            following = rendered[number] if number < len(rendered) else ""
            if "save_penalty" in line or "save_penalty" in following:
                continue
            raise AssertionError(
                f"{path.name}:{number} sets a saving throw without a save penalty"
            )


def normalise_power_name(name: str) -> str:
    return "_".join(re.findall(r"[A-Za-z0-9]+", name)).upper()


def validate_power_names() -> None:
    table = {row[0]: row[1] for row in rows("psionpowers.2da")}
    pattern = re.compile(
        r"ps_resref\s*=\s*~([A-Z0-9]+)~(?:(?!ps_resref).)*?ps_name\s*=\s*~([^~]+)~",
        re.DOTALL,
    )
    inspected = set()
    for path in sorted((ROOT / "lib").glob("*.tpa")):
        for resref, display in pattern.findall(path.read_text(encoding="utf-8")):
            if resref not in table:
                continue
            expected = normalise_power_name(display)
            assert table[resref] == expected, (path.name, resref, table[resref], expected)
            inspected.add(resref)
    missing = sorted(set(table) - inspected)
    assert not missing, ("no builder ps_name found for", missing)


def validate_installer() -> None:
    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert re.search(r"(?m)^VERSION ~\d+\.\d+\.\d+~$", setup), "missing semantic VERSION"
    for name in (
        "psionpool", "psionknown", "psiondisc", "psionskills", "psionfeats",
        "psionpowers", "psionaugment", "ps1eray", "ps1mthr", "ps1vigr",
        "ps2aaff", "pspick", "mxpsion", "clabpsee", "clabpsha", "clabpkin",
        "clabpego", "clabpnom", "clabptel",
    ):
        assert name in setup
    for include in (
        "class-detect.tpa", "class-strings.tpa", "class-layout.tpa",
        "class-common.tpa", "class-skills.tpa",
    ):
        assert include in setup


def main() -> None:
    validate_tables()
    validate_progressions()
    validate_learnable_powers()
    validate_weidu_integer_syntax()
    validate_release_infrastructure()
    validate_builders()
    validate_augmentation()
    validate_save_dc_scheme()
    validate_power_names()
    validate_installer()
    py_compile.compile(str(ROOT / "guiscripts" / "Psionics.py"), doraise=True)
    py_compile.compile(str(ROOT / "tools" / "install_guiscripts.py"), doraise=True)
    print("Psion core table, progression, builder, and installer validation passed.")


if __name__ == "__main__":
    main()
