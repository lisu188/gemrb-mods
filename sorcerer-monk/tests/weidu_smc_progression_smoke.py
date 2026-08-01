from pathlib import Path
import shutil
import sys
import tempfile

from weidu_smc_layout_smoke import prepare_smc, row, run_smc, snapshot
from weidu_smoke import build_fixture, write_2da


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def column_values(path, column):
    lines = path.read_text(encoding="utf-8").splitlines()
    headers = lines[2].split()
    index = headers.index(column)
    result = {}
    for line in lines[3:]:
        fields = line.split()
        if fields:
            result[fields[0]] = fields[index + 1]
    return result


def exercise_modern_skill_tables(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-progression-modern-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        originals = snapshot(override)

        run_smc(weidu, game, "--force-install-list", "0")
        assert row(override / "profs.2da", "SORCERER_MONK_CLERIC") == ["SORCERER_MONK_CLERIC", "2", "4"]
        assert row(override / "thiefskl.2da", "SORCERER_MONK_CLERIC") == ["SORCERER_MONK_CLERIC", "0", "10"]
        values = column_values(override / "thiefscl.2da", "SORCERER_MONK_CLERIC")
        assert values == {
            "PICK_POCKETS": "0",
            "OPEN_LOCKS": "0",
            "FIND_TRAPS": "1",
            "MOVE_SILENTLY": "1",
            "HIDE_IN_SHADOWS": "1",
            "DETECT_ILLUSION": "0",
            "SET_TRAPS": "0",
        }, values

        run_smc(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "modern progression uninstall")
        print("SMC modern proficiency and Monk skill progression: OK", flush=True)


def exercise_legacy_skill_table(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-progression-legacy-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        (override / "thiefscl.2da").unlink()
        (override / "thiefskl.2da").unlink()
        write_2da(
            override / "skills.2da",
            ["MONK"],
            [
                ("START_POINTS", [10]),
                ("LEVEL_POINTS", [10]),
                ("PICK_POCKETS", [-1]),
                ("OPEN_LOCKS", [-1]),
                ("FIND_TRAPS", [1]),
                ("MOVE_SILENTLY", [1]),
                ("HIDE_IN_SHADOWS", [1]),
                ("DETECT_ILLUSION", [-1]),
                ("SET_TRAPS", [-1]),
            ],
            default="-1",
        )
        originals = snapshot(override)

        run_smc(weidu, game, "--force-install-list", "0")
        assert row(override / "profs.2da", "SORCERER_MONK_CLERIC") == ["SORCERER_MONK_CLERIC", "2", "4"]
        values = column_values(override / "skills.2da", "SORCERER_MONK_CLERIC")
        assert [values[name] for name in (
            "START_POINTS", "LEVEL_POINTS", "PICK_POCKETS", "OPEN_LOCKS",
            "FIND_TRAPS", "MOVE_SILENTLY", "HIDE_IN_SHADOWS", "DETECT_ILLUSION", "SET_TRAPS",
        )] == ["10", "10", "-1", "-1", "1", "1", "1", "-1", "-1"]

        run_smc(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "legacy progression uninstall")
        print("SMC legacy proficiency and Monk skill progression: OK", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_modern_skill_tables(weidu)
    exercise_legacy_skill_table(weidu)


if __name__ == "__main__":
    main()
