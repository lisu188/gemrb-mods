from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_layout_smoke import make_current_split_layout, make_released_ee_layout, row
from weidu_native_clastext_smoke import make_native_ee9_layout, make_native_ee10_layout
from weidu_smoke import ROOT, build_fixture, count_token, write_2da


SMC = ROOT / "sorcerer-monk-cleric"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def has_row(path, name):
    return any(line.split() and line.split()[0] == name for line in path.read_text(encoding="utf-8").splitlines())


def row_index(path, name):
    rows = path.read_text(encoding="utf-8").splitlines()[3:]
    for index, line in enumerate(rows):
        cells = line.split()
        if cells and cells[0] == name:
            return index
    raise AssertionError(f"missing {name} in {path}")


def add_cleric_identity(override):
    classes = override / "classes.2da"
    class_headers = classes.read_text(encoding="utf-8").splitlines()[2].split()
    if not has_row(classes, "CLERIC"):
        if len(class_headers) == 18:
            with classes.open("a", encoding="utf-8") as handle:
                handle.write("CLERIC 1 2 3 SAVEPRS 0 3 HPPRS 0x4000 -1 1 1 1 1 1 1 1 0 9\n")
        elif len(class_headers) == 6:
            with classes.open("a", encoding="utf-8") as handle:
                handle.write("CLERIC SAVEPRS 0 0x4000 -1 0 9\n")
        else:
            raise AssertionError(class_headers)

    clastext = override / "clastext.2da"
    if clastext.exists() and not has_row(clastext, "CLERIC"):
        width = len(clastext.read_text(encoding="utf-8").splitlines()[2].split()) + 1
        if width == 6:
            values = "3 * 1 2 3"
        elif width == 9:
            values = "3 16384 1 2 3 -1 0 4"
        elif width == 10:
            values = "3 16384 1 2 3 -1 0 4 -1"
        else:
            raise AssertionError(width)
        with clastext.open("a", encoding="utf-8") as handle:
            handle.write(f"CLERIC {values}\n")

    hpclass = override / "hpclass.2da"
    if hpclass.exists() and not has_row(hpclass, "CLERIC"):
        with hpclass.open("a", encoding="utf-8") as handle:
            handle.write("CLERIC HPPRS\n")

    clsrcreq = override / "clsrcreq.2da"
    if clsrcreq.exists() and not has_row(clsrcreq, "CLERIC"):
        with clsrcreq.open("a", encoding="utf-8") as handle:
            handle.write("CLERIC 1 1 1 1 1 1 1\n")

    class_ids = override / "class.ids"
    text = class_ids.read_text(encoding="utf-8")
    if "3 CLERIC" not in text:
        class_ids.write_text("3 CLERIC\n" + text, encoding="utf-8")


def prepare_smc(game, builder):
    builder(game)
    shutil.copytree(SMC, game / "sorcerer-monk-cleric")
    override = game / "override"
    add_cleric_identity(override)

    write_2da(
        override / "weapprof.2da",
        ["MAGE"],
        [(f"PROF{i:02d}", [1]) for i in range(51)],
        default="0",
    )
    write_2da(
        override / "25stweap.2da",
        ["MAGE"],
        [(f"SLOT{i}", ["*"]) for i in range(20)],
    )
    write_2da(
        override / "luabbr.2da",
        ["ABBREV"],
        [("SORCERER", ["SOR"]), ("MONK", ["MON"]), ("CLERIC", ["CLR"])],
    )
    write_2da(
        override / "lunumab.2da",
        ["FIRST_LEVEL", "RATE", "MAX_LEVEL", "NUM_ALLOWED"],
        [
            ("SORCERER", [14, 1, 99, 1]),
            ("MONK", [14, 1, 99, 1]),
            ("CLERIC", [14, 1, 99, 1]),
            ("MULTI2SORCERER", [14, 1, 99, 1]),
            ("MULTI2MONK", [14, 1, 99, 1]),
            ("MULTI2CLERIC", [14, 1, 99, 1]),
        ],
    )


def run_smc(weidu, game, *args, check=True):
    command = [
        weidu,
        "sorcerer-monk-cleric/setup-sorcerer-monk-cleric.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        *args,
    ]
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=game,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode:
        print(result.stdout, flush=True)
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout)
    return result


def verify_common(game, expected_clskills_width, expected_id):
    override = game / "override"
    skill_row = row(override / "clskills.2da", "SORCERER_MONK_CLERIC")
    assert len(skill_row) == expected_clskills_width, skill_row
    assert row_index(override / "clskills.2da", "SORCERER_MONK_CLERIC") == expected_id
    assert skill_row[2] == "MXSPLPRS", skill_row
    assert skill_row[3] == "MXSPLSRC", skill_row
    assert skill_row[11] == "CLABMO01", skill_row
    assert f"{expected_id} SORCERER_MONK_CLERIC" in (override / "class.ids").read_text(encoding="utf-8")
    fist_rows = [
        line.split()
        for line in (override / "fistweap.2da").read_text(encoding="utf-8").splitlines()
        if line.split() and line.split()[0] == str(expected_id)
    ]
    assert len(fist_rows) == 1, fist_rows
    assert count_token(override / "lunumab.2da", "MULTI3SORCERER") == 1
    assert count_token(override / "lunumab.2da", "MULTI3MONK") == 1
    assert count_token(override / "lunumab.2da", "MULTI3CLERIC") == 1


def verify_released_combined(game, expected_id):
    override = game / "override"
    verify_common(game, 17, expected_id)
    class_row = row(override / "classes.2da", "SORCERER_MONK_CLERIC")
    assert len(class_row) == 19, class_row
    assert class_row[6] == str(expected_id), class_row
    if (override / "hpclass.2da").exists():
        assert count_token(override / "hpclass.2da", "SORCERER_MONK_CLERIC") == 0
    assert not (override / "clastext.2da").exists()
    assert not (override / "clsrcreq.2da").exists()


def verify_split(game, expected_clastext_width, expected_id):
    override = game / "override"
    verify_common(game, 16, expected_id)
    class_row = row(override / "classes.2da", "SORCERER_MONK_CLERIC")
    assert len(class_row) == 7, class_row
    assert class_row[2] == "786436", class_row
    class_text = row(override / "clastext.2da", "SORCERER_MONK_CLERIC")
    assert len(class_text) == expected_clastext_width, class_text
    assert class_text[1] == str(expected_id), class_text
    if expected_clastext_width == 6:
        assert class_text[2] == "*", class_text
    else:
        assert class_text[2] == "16384", class_text
    assert "PLACEHOLDER" not in " ".join(class_text)
    assert count_token(override / "hpclass.2da", "SORCERER_MONK_CLERIC") == 1
    assert count_token(override / "clsrcreq.2da", "SORCERER_MONK_CLERIC") == 1


def exercise(weidu, builder, verifier, label):
    with tempfile.TemporaryDirectory(prefix=f"smc-{label}-") as tmp:
        game = Path(tmp)
        prepare_smc(game, builder)
        override = game / "override"
        originals = snapshot(override)

        run_smc(weidu, game, "--force-install-list", "0")
        verifier(game)
        run_smc(weidu, game, "--reinstall")
        verifier(game)
        run_smc(weidu, game, "--force-uninstall", "0")

        actual = snapshot(override)
        assert actual.keys() == originals.keys(), f"{label}: override file set changed"
        for name, original in originals.items():
            assert actual[name] == original, f"{label}: {name} not restored"
        print(f"{label}: OK", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise(weidu, build_fixture, lambda game: verify_released_combined(game, 21), "classic-combined-id21")
    exercise(weidu, make_released_ee_layout, lambda game: verify_released_combined(game, 22), "released-ee-id22")
    exercise(weidu, make_current_split_layout, lambda game: verify_split(game, 6, 22), "current-split-id22")
    exercise(weidu, make_native_ee9_layout, lambda game: verify_split(game, 9, 22), "native-ee9-id22")
    exercise(weidu, make_native_ee10_layout, lambda game: verify_split(game, 10, 22), "native-ee10-id22")


if __name__ == "__main__":
    main()
