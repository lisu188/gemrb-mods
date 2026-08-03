from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu, write_2da


HEADERS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
SORCERER = [1, 2, 3, 11, 5, 13]
MONK = [4, 10, 12, 7, 14, 6]
EXPECTED = [4, 10, 12, 11, 14, 13]


def install(weidu, game):
    return subprocess.run(
        [weidu, "sorcerer-monk/setup-sorcerer-monk.tp2", "--game", str(game),
         "--language", "0", "--noautoupdate", "--force-install-list", "0"],
        cwd=game, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120,
    )


def exercise_live_requirements(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-abclasrq-live-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "abclasrq.2da",
            HEADERS,
            [("SORCERER", SORCERER), ("MONK", MONK)],
            default="0",
        )
        original = (override / "abclasrq.2da").read_bytes()

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "abclasrq.2da", "SORCERER_MONK")[1:] == [str(v) for v in EXPECTED]
        print("live ABCLASRQ maximum install: OK", flush=True)

        run_weidu(weidu, game, "--reinstall")
        assert find_row(override / "abclasrq.2da", "SORCERER_MONK")[1:] == [str(v) for v in EXPECTED]
        print("live ABCLASRQ maximum reinstall: OK", flush=True)

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert (override / "abclasrq.2da").read_bytes() == original
        print("live ABCLASRQ uninstall restore: OK", flush=True)


def exercise_missing_component(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-abclasrq-missing-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(override / "abclasrq.2da", HEADERS, [("SORCERER", SORCERER)], default="0")
        originals = {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}

        result = install(weidu, game)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Could not derive Sorcerer/Monk ability requirements from ABCLASRQ.2DA" in output, output
        for name, original in originals.items():
            assert (override / name).read_bytes() == original, name
        print("missing Monk ABCLASRQ row: rejected safely", flush=True)


def exercise_bad_value(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-abclasrq-invalid-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        bad_monk = MONK.copy()
        bad_monk[2] = "BAD"
        write_2da(
            override / "abclasrq.2da",
            HEADERS,
            [("SORCERER", SORCERER), ("MONK", bad_monk)],
            default="0",
        )
        originals = {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}

        result = install(weidu, game)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Could not derive Sorcerer/Monk ability requirements from ABCLASRQ.2DA" in output, output
        for name, original in originals.items():
            assert (override / name).read_bytes() == original, name
        print("invalid Monk ABCLASRQ value: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_live_requirements(weidu)
    exercise_missing_component(weidu)
    exercise_bad_value(weidu)


if __name__ == "__main__":
    main()
