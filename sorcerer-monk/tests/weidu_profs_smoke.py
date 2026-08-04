from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu, write_2da


ERROR = "Could not derive Sorcerer/Monk proficiency progression from PROFS.2DA"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


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


def exercise_live_progression(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-profs-live-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "profs.2da",
            ["FIRST_LEVEL", "RATE"],
            [("SORCERER", [5, 3]), ("MONK", [2, 4])],
        )
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "profs.2da", "SORCERER_MONK")[1:] == ["5", "3"]

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "profs.2da", "SORCERER_MONK")[1:] == ["5", "3"]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "live PROFS uninstall")
        print("live component PROFS progression: OK", flush=True)


def exercise_missing_component(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-profs-missing-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(override / "profs.2da", ["FIRST_LEVEL", "RATE"], [("SORCERER", [1, 6])])
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "missing Monk PROFS rejection")


def exercise_invalid_rate(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-profs-invalid-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "profs.2da",
            ["FIRST_LEVEL", "RATE"],
            [("SORCERER", [1, 6]), ("MONK", [2, 0])],
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "invalid Monk PROFS rate rejection")


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_live_progression(weidu)
    exercise_missing_component(weidu)
    exercise_invalid_rate(weidu)


if __name__ == "__main__":
    main()
