from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu, write_2da


ERROR = "Could not derive Sorcerer/Monk modern Monk-skill metadata"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def column_values(path, column):
    lines = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.split()]
    headers = lines[2]
    index = headers.index(column) + 1
    return [row[index] for row in lines[3:]]


def run_rejected(weidu, game):
    command = [
        weidu,
        "sorcerer-monk/setup-sorcerer-monk.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        "--force-install-list", "0",
    ]
    return subprocess.run(
        command,
        cwd=game,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def exercise_live_modern_skills(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-modern-skills-live-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        skills = [
            ("PICK_POCKETS", 1), ("OPEN_LOCKS", 0), ("FIND_TRAPS", 1),
            ("MOVE_SILENTLY", 0), ("HIDE_IN_SHADOWS", 1),
            ("DETECT_ILLUSION", 1), ("SET_TRAPS", 0),
            ("MOD_SKILL_A", 1), ("MOD_SKILL_B", 1),
        ]
        write_2da(
            override / "thiefscl.2da",
            ["MONK"],
            [(name, [value]) for name, value in skills],
            default="0",
        )
        write_2da(
            override / "thiefskl.2da",
            ["START_POINTS", "LEVEL_POINTS"],
            [("MONK", [7, 13])],
            default="0",
        )
        originals = snapshot(override)
        expected = [str(value) for _, value in skills]

        run_weidu(weidu, game, "--force-install-list", "0")
        assert column_values(override / "thiefscl.2da", "SORCERER_MONK") == expected
        assert find_row(override / "thiefskl.2da", "SORCERER_MONK")[1:] == ["7", "13"]

        run_weidu(weidu, game, "--force-install-list", "0")
        assert column_values(override / "thiefscl.2da", "SORCERER_MONK") == expected
        assert find_row(override / "thiefskl.2da", "SORCERER_MONK")[1:] == ["7", "13"]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "modern Monk skill uninstall")
        print("live modern Monk skill metadata: OK", flush=True)


def exercise_missing_monk_column(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-modern-skills-column-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "thiefscl.2da",
            ["THIEF"],
            [("PICK_POCKETS", [1]), ("OPEN_LOCKS", [1])],
            default="0",
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "missing Monk THIEFSCL rejection")


def exercise_invalid_availability(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-modern-skills-invalid-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "thiefscl.2da",
            ["MONK"],
            [("PICK_POCKETS", [0]), ("OPEN_LOCKS", [2])],
            default="0",
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "non-binary THIEFSCL rejection")


def exercise_missing_monk_points(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-modern-skills-points-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "thiefskl.2da",
            ["START_POINTS", "LEVEL_POINTS"],
            [("THIEF", [40, 25])],
            default="0",
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "missing Monk THIEFSKL rejection")


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_live_modern_skills(weidu)
    exercise_missing_monk_column(weidu)
    exercise_invalid_availability(weidu)
    exercise_missing_monk_points(weidu)


if __name__ == "__main__":
    main()
