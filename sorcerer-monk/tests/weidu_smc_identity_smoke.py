from pathlib import Path
import shutil
import sys
import tempfile

from weidu_smc_layout_smoke import prepare_smc, run_smc, snapshot
from weidu_smoke import build_fixture


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def assert_rejected(result, message):
    print(result.stdout, flush=True)
    assert result.returncode != 0, result.stdout
    assert message.casefold() in result.stdout.casefold(), result.stdout


def exercise_class_ids_numeric_collision(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-class-ids-collision-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        with (override / "class.ids").open("a", encoding="utf-8") as handle:
            handle.write("21 OTHER_CLASS\n")
        originals = snapshot(override)

        result = run_smc(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "CLASS.IDS conflicts with the numeric class identifier required for Sorcerer/Monk/Cleric")
        assert_snapshot(override, originals, "CLASS.IDS numeric collision rejection")
        print("SMC CLASS.IDS numeric collision: rejected safely", flush=True)


def exercise_active_class_id_collision(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-class-table-collision-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        with (override / "classes.2da").open("a", encoding="utf-8") as handle:
            handle.write("OTHER_CLASS 1 2 3 SAVEWIZ 0 21 HPWIZ 0x1 -1 1 0 0 0 0 0 0 0 9\n")
        originals = snapshot(override)

        result = run_smc(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "The GemRB class tables and CLSKILLS.2DA disagree about the numeric class identifier required for Sorcerer/Monk/Cleric")
        assert_snapshot(override, originals, "active class ID collision rejection")
        print("SMC active class ID collision: rejected safely", flush=True)


def exercise_fistweap_numeric_collision(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-fistweap-collision-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        with (override / "fistweap.2da").open("a", encoding="utf-8") as handle:
            handle.write("21 " + " ".join(["CUSTOM_FIST"] * 41) + "\n")
        originals = snapshot(override)

        result = run_smc(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "FISTWEAP.2DA already contains a row for the numeric class identifier allocated to Sorcerer/Monk/Cleric")
        assert_snapshot(override, originals, "FISTWEAP numeric collision rejection")
        print("SMC FISTWEAP numeric collision: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_class_ids_numeric_collision(weidu)
    exercise_active_class_id_collision(weidu)
    exercise_fistweap_numeric_collision(weidu)


if __name__ == "__main__":
    main()
