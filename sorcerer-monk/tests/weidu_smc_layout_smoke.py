from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_layout_smoke import make_current_split_layout, make_released_ee_layout, row
from weidu_native_clastext_smoke import make_native_ee9_layout, make_native_ee10_layout
from weidu_smoke import ROOT, count_token, write_2da


SMC = ROOT / "sorcerer-monk-cleric"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def prepare_smc(game, builder):
    builder(game)
    shutil.copytree(SMC, game / "sorcerer-monk-cleric")
    override = game / "override"

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


def run_smc(weidu, game, *args):
    command = [
        weidu,
        "sorcerer-monk-cleric/setup-sorcerer-monk-cleric.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        *args,
    ]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=game, check=True)


def verify_common(game, expected_clskills_width):
    override = game / "override"
    skill_row = row(override / "clskills.2da", "SORCERER_MONK_CLERIC")
    assert len(skill_row) == expected_clskills_width, skill_row
    assert skill_row[2] == "MXSPLPRS", skill_row
    assert skill_row[3] == "MXSPLSRC", skill_row
    assert skill_row[11] == "CLABMO01", skill_row
    assert count_token(override / "lunumab.2da", "MULTI3SORCERER") == 1
    assert count_token(override / "lunumab.2da", "MULTI3MONK") == 1
    assert count_token(override / "lunumab.2da", "MULTI3CLERIC") == 1


def verify_released_combined(game):
    override = game / "override"
    verify_common(game, 17)
    class_row = row(override / "classes.2da", "SORCERER_MONK_CLERIC")
    assert len(class_row) == 19, class_row
    assert class_row[6] == "22", class_row
    assert count_token(override / "hpclass.2da", "SORCERER_MONK_CLERIC") == 0
    assert not (override / "clastext.2da").exists()
    assert not (override / "clsrcreq.2da").exists()


def verify_split(game, expected_clastext_width):
    override = game / "override"
    verify_common(game, 16)
    class_row = row(override / "classes.2da", "SORCERER_MONK_CLERIC")
    assert len(class_row) == 7, class_row
    assert class_row[2] == "786436", class_row
    class_text = row(override / "clastext.2da", "SORCERER_MONK_CLERIC")
    assert len(class_text) == expected_clastext_width, class_text
    assert class_text[1] == "22", class_text
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

    exercise(weidu, make_released_ee_layout, verify_released_combined, "released-combined-with-hpclass")
    exercise(weidu, make_current_split_layout, lambda game: verify_split(game, 6), "current-split")
    exercise(weidu, make_native_ee9_layout, lambda game: verify_split(game, 9), "native-ee9")
    exercise(weidu, make_native_ee10_layout, lambda game: verify_split(game, 10), "native-ee10")


if __name__ == "__main__":
    main()
