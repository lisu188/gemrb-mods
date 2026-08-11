from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "sorcerer-monk"


def write_2da(path, headers, rows, default="*"):
    lines = ["2DA V1.0", default, " ".join(headers)]
    lines.extend(" ".join([name, *map(str, values)]) for name, values in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


HLA_HEADERS = [
    "ABILITY", "TYPE", "ICON", "MIN_LEVEL", "MAX_LEVEL", "NUM_ALLOWED",
    "PREREQUISITE", "EXCLUDED", "ALIGNMENT_RESTRICT",
]


def hla_row(index, ability):
    """LU*.2DA rows are named by index; the ability reference is the first cell."""
    return (str(index), [ability, 1, "ICON", 1, 99, 1, "*", "*", "*"])


def write_qslots(override, class_names):
    """One row per class ID: GemRB reads QSLOTS.2DA by row index, not row name."""
    rows = []
    for name in class_names:
        if name == "UNUSED":
            continue
        if name == "MONK":
            rows.append((name, [18, 14, 22, 0, 8, 9, 11, 12, 13]))
        else:
            rows.append((name, [3, 4, 5, 2, 8, 9, 11, 12, 13]))
    write_2da(override / "qslots.2da", [f"SLOT{i}" for i in range(9)], rows)


def write_hla_tables(override):
    write_2da(
        override / "luabbr.2da",
        ["ABBREV"],
        [("SORCERER", ["SO0"]), ("MONK", ["MO0"])],
    )
    # GA_SPCL900 is deliberately shared so the merge has to deduplicate it, and
    # both tables end with the sentinel row GemRB stops reading at.
    for name, abilities in [
        ("luso0.2da", ["GA_SPCL900", "GA_SPCL920", "GA_SPCL921"]),
        ("lumo0.2da", ["GA_SPCL900", "GA_SPCL930", "GA_SPCL931"]),
    ]:
        rows = [hla_row(i, ability) for i, ability in enumerate(abilities)]
        rows.append((str(len(abilities)), ["*"] * 9))
        write_2da(override / name, HLA_HEADERS, rows)


def build_fixture(game):
    override = game / "override"
    override.mkdir(parents=True)
    (game / "gemrb-data").mkdir()
    shutil.copytree(MOD, game / "sorcerer-monk")

    (game / "chitin.key").write_bytes(b"KEY V1  " + struct.pack("<IIII", 0, 0, 24, 24))
    (game / "dialog.tlk").write_bytes(b"TLK V1  " + struct.pack("<HII", 0, 0, 18))
    (game / "gemrb_path.txt").write_text(
        f"GemRB_Data_Path = {game / 'gemrb-data'}\n", encoding="utf-8"
    )
    (override / "ar0083.are").write_bytes(b"fixture")

    class_headers = [
        "NAME_REF", "DESC_REF", "CAP_REF", "SAVE", "MULTI", "ID", "HP",
        "USABILITY", "MC_WAS_ID", "HUMAN", "ELF", "HALF_ELF", "DWARF",
        "HALFLING", "GNOME", "HALFORC", "STREXTRA", "CONBONLVL",
    ]
    write_2da(
        override / "classes.2da",
        class_headers,
        [
            ("SORCERER", [45849, 45866, 45856, "SAVEWIZ", 0, 19, "HPWIZ", "0x40000", -1, 1, 1, 1, 0, 0, 0, 0, 0, 10]),
            ("MONK", [45851, 45867, 45858, "SAVEMONK", 0, 20, "HPMONK", "0x20000000", -1, 1, 0, 0, 0, 0, 0, 0, 0, 9]),
        ],
    )

    skill_headers = [
        "DRUIDSPELL", "CLERICSPELL", "MAGESPELL", "STARTXP", "BARDSKILL",
        "THIEFSKILL", "LAYHANDS", "TURNLEVEL", "BOOKTYPE", "HATERACE",
        "ABILITIES", "NO_PROF", "STARTXP2", "RANGERSKILL", "SAVEBONUS", "SPONCAST",
    ]
    names = [
        "UNUSED", "MAGE", "FIGHTER", "CLERIC", "THIEF", "BARD", "PALADIN",
        "FIGHTER_MAGE", "FIGHTER_CLERIC", "FIGHTER_THIEF", "FIGHTER_MAGE_THIEF",
        "DRUID", "RANGER", "MAGE_THIEF", "CLERIC_MAGE", "CLERIC_THIEF",
        "FIGHTER_DRUID", "FIGHTER_MAGE_CLERIC", "CLERIC_RANGER", "SORCERER", "MONK",
    ]
    skill_rows = []
    for name in names:
        values = ["*", "*", "*", 89000, "*", "*", "*", 0, 0, "*", "*", -3, 2500000, "*", 0, "*"]
        if name == "UNUSED":
            values[3] = "*"
            values[11] = "*"
            values[12] = "*"
        elif name == "SORCERER":
            values[2] = "MXSPLSRC"
            values[8] = 2
            values[11] = -4
        elif name == "MONK":
            values[5] = "SKILLS"
            values[10] = "CLABMO01"
            values[11] = -3
        skill_rows.append((name, values))
    write_2da(override / "clskills.2da", skill_headers, skill_rows)

    write_2da(override / "xpcap.2da", ["XP_CAP"], [("SORCERER", [8000000]), ("MONK", [8000000])], default="-1")
    write_2da(
        override / "alignmnt.2da",
        ["LG", "LN", "LE", "NG", "TN", "NE", "CG", "CN", "CE"],
        [("SORCERER", [1] * 9), ("MONK", [1, 1, 1, 0, 0, 0, 0, 0, 0])],
    )

    write_2da(
        override / "weapprof.2da",
        ["MAGE"],
        [(f"PROF{i:02d}", [1]) for i in range(50)],
        default="0",
    )
    write_2da(override / "profs.2da", ["FIRST_LEVEL", "RATE"], [("SORCERER", [1, 6]), ("MONK", [2, 4])])
    write_2da(override / "strtgold.2da", ["SIDES", "ROLLS", "MODIFIER", "MULTIPLIER"], [("SORCERER", [4, 1, 1, 10]), ("MONK", [4, 1, 1, 10])])
    write_2da(override / "numwslot.2da", ["SLOTS"], [("SORCERER", [2]), ("MONK", [3])])
    write_2da(override / "avprefc.2da", ["CLASS"], [("SORCERER", [0]), ("MONK", ["0x500"])])

    stock_fists = [
        "MFIST1", "MFIST1", "MFIST2", "MFIST2", "MFIST2", "MFIST3", "MFIST3", "MFIST3",
        "MFIST4", "MFIST4", "MFIST4", "MFIST5", "MFIST5", "MFIST5", "MFIST6", "MFIST6",
        "MFIST6", "MFIST7", "MFIST7", "MFIST7", "MFIST7", "MFIST7", "MFIST7", "MFIST7",
    ] + ["MFIST8"] * 17
    write_2da(override / "fistweap.2da", [str(i) for i in range(41)], [("20", stock_fists)], default="FIST")
    write_qslots(override, names)
    write_hla_tables(override)

    write_2da(
        override / "thiefscl.2da",
        ["MONK"],
        [
            ("PICK_POCKETS", [0]), ("OPEN_LOCKS", [0]), ("FIND_TRAPS", [1]),
            ("MOVE_SILENTLY", [1]), ("HIDE_IN_SHADOWS", [1]),
            ("DETECT_ILLUSION", [0]), ("SET_TRAPS", [0]),
        ],
        default="0",
    )
    write_2da(override / "thiefskl.2da", ["START_POINTS", "LEVEL_POINTS"], [("MONK", [0, 10])], default="0")

    write_2da(override / "abclasrq.2da", ["STR", "DEX", "CON", "INT", "WIS", "CHA"], [("SORCERER", [0, 0, 0, 9, 0, 9]), ("MONK", [0, 9, 9, 0, 9, 0])], default="0")
    write_2da(override / "abclsmod.2da", ["STR", "DEX", "CON", "INT", "WIS", "CHA"], [("SORCERER", [0, 0, 0, 0, 0, 0]), ("MONK", [0, 0, 0, 0, 0, 0])], default="0")
    write_2da(override / "stweapon.2da", ["ITEM"], [("SORCERER", ["STAF01"]), ("MONK", [])], default="STAF01")
    write_2da(override / "clswpbon.2da", ["GETS_PROF_APR", "UNARMED_DIVISOR", "ZERO_SKILL_THAC0"], [("SORCERER", [0, 0, 4]), ("MONK", [1, 3, 2])], default="0")

    (override / "class.ids").write_text("19 SORCERER\n20 MONK\n", encoding="utf-8")


def count_token(path, token):
    return path.read_text(encoding="utf-8").split().count(token)


def data_rows(path):
    """The 2DA rows WeiDU and GemRB see: the three header lines are skipped."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.split()]
    return [line.split() for line in lines[3:]]


def find_row(path, name):
    for cells in data_rows(path):
        if cells[0] == name:
            return cells
    raise AssertionError(f"missing {name} in {path}")


def verify_component_derived_rows(game, class_id, monk_id):
    """Everything the installer copies out of the live component rows."""
    override = game / "override"

    # GemRB looks fists up by the Monk component level, so the multiclass row is
    # the Monk row verbatim under the new class ID.
    assert find_row(override / "fistweap.2da", class_id)[1:] == \
        find_row(override / "fistweap.2da", monk_id)[1:]

    # GemRB reads QSLOTS.2DA by row index: class ID N uses row N - 1.
    qslots = data_rows(override / "qslots.2da")
    assert qslots[int(class_id) - 1] == \
        ["SORCERER_MONK", "3", "2", "22", "0", "8", "9", "11", "12", "13"], qslots[-1]

    assert find_row(override / "strtgold.2da", "SORCERER_MONK")[1:] == \
        find_row(override / "strtgold.2da", "MONK")[1:]
    assert find_row(override / "avprefc.2da", "SORCERER_MONK")[1:] == \
        find_row(override / "avprefc.2da", "MONK")[1:]

    # The merged HLA table keeps both components' abilities, in order, once each.
    assert find_row(override / "luabbr.2da", "SORCERER_MONK")[1] == "SM0"
    merged = data_rows(override / "lusm0.2da")
    assert [cells[0] for cells in merged] == ["0", "1", "2", "3", "4"], merged
    assert [cells[1] for cells in merged] == \
        ["GA_SPCL900", "GA_SPCL920", "GA_SPCL921", "GA_SPCL930", "GA_SPCL931"], merged
    assert all(len(cells) == 10 for cells in merged), merged


def verify_installed(game):
    override = game / "override"
    assert count_token(override / "classes.2da", "SORCERER_MONK") == 1
    assert "SORCERER_MONK" in (override / "classes.2da").read_text(encoding="utf-8")
    assert "21 SORCERER_MONK" in (override / "class.ids").read_text(encoding="utf-8")
    assert count_token(override / "clskills.2da", "SORCERER_MONK") == 1
    assert "SORCERER_MONK 2 4" in (override / "profs.2da").read_text(encoding="utf-8")
    assert "SORCERER_MONK 8000000" in (override / "xpcap.2da").read_text(encoding="utf-8")
    assert "SORCERER_MONK 2" in (override / "numwslot.2da").read_text(encoding="utf-8")
    assert "SORCERER_MONK 0 10" in (override / "thiefskl.2da").read_text(encoding="utf-8")
    assert "SORCERER_MONK 0 9 9 9 9 9" in (override / "abclasrq.2da").read_text(encoding="utf-8")
    assert "SORCERER_MONK 1 3 2" in (override / "clswpbon.2da").read_text(encoding="utf-8")
    assert count_token(override / "weapprof.2da", "SORCERER_MONK") == 1
    assert count_token(override / "thiefscl.2da", "SORCERER_MONK") == 1

    verify_component_derived_rows(game, class_id="21", monk_id="20")

    backup = game / "sorcerer-monk-cleric" / "backup" / "0"
    assert backup.is_dir()
    assert (game / "WeiDU.log").is_file()


def run_weidu(weidu, game, *args):
    command = [
        weidu,
        "sorcerer-monk/setup-sorcerer-monk.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        *args,
    ]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=game, check=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-weidu-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        originals = {p.name: p.read_bytes() for p in (game / "override").iterdir() if p.is_file()}

        run_weidu(weidu, game, "--force-install-list", "0")
        verify_installed(game)
        print("real WeiDU install: OK", flush=True)

        run_weidu(weidu, game, "--reinstall")
        verify_installed(game)
        print("real WeiDU reinstall: OK", flush=True)

        run_weidu(weidu, game, "--force-uninstall", "0")
        for name, original in originals.items():
            assert (game / "override" / name).read_bytes() == original, name
        assert not (game / "override" / "lusm0.2da").exists(), "lusm0.2da left behind"
        print("real WeiDU uninstall restore: OK", flush=True)

    verify_short_qslots_is_rejected(weidu)
    verify_taken_hla_abbreviation_is_rejected(weidu)
    verify_missing_avprefc_uses_gemrb_baseline(weidu)


def install_expecting_failure(weidu, game):
    result = subprocess.run(
        [weidu, "sorcerer-monk/setup-sorcerer-monk.tp2", "--game", str(game),
         "--language", "0", "--noautoupdate", "--force-install-list", "0"],
        cwd=game, capture_output=True, text=True,
        stdin=subprocess.DEVNULL, timeout=120,
    )
    assert result.returncode != 0, result.stdout
    assert "SORCERER_MONK" not in (game / "override" / "classes.2da").read_text(encoding="utf-8")


def verify_taken_hla_abbreviation_is_rejected(weidu):
    """LUSM0.2DA is a new file, so an existing SM0 owner must not be clobbered."""
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-sm0-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        write_2da(
            game / "override" / "luabbr.2da",
            ["ABBREV"],
            [("SORCERER", ["SO0"]), ("MONK", ["MO0"]), ("SOME_OTHER_CLASS", ["SM0"])],
        )
        install_expecting_failure(weidu, game)
        assert not (game / "override" / "lusm0.2da").exists(), "lusm0.2da was written anyway"
        print("real WeiDU taken-SM0 rejection: OK", flush=True)


def verify_short_qslots_is_rejected(weidu):
    """A QSLOTS.2DA that is out of step with CLSKILLS must stop the install.

    GemRB addresses the action bar by row index, so an appended row would land
    on another class instead of the new one.
    """
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-qslots-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        qslots = game / "override" / "qslots.2da"
        lines = qslots.read_text(encoding="utf-8").splitlines()
        qslots.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

        install_expecting_failure(weidu, game)
        print("real WeiDU short-qslots rejection: OK", flush=True)


def verify_missing_avprefc_uses_gemrb_baseline(weidu):
    """Fresh BGEE games rely on GemRB's shared AVPREFC instead of their KEY."""
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-avprefc-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        avprefc = game / "override" / "avprefc.2da"
        avprefc.unlink()

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(avprefc, "MONK")[1:] == ["0x500"]
        assert find_row(avprefc, "SORCERER_MONK")[1:] == ["0x500"]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert not avprefc.exists(), "fallback AVPREFC.2DA left behind"
        print("missing AVPREFC uses GemRB baseline: OK", flush=True)


if __name__ == "__main__":
    main()
