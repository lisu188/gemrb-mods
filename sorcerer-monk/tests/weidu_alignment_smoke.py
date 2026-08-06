from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu, write_2da


HEADERS = ["L_G", "L_N", "L_E", "N_G", "N_N", "N_E", "C_G", "C_N", "C_E"]
SORCERER = [1, 1, 0, 1, 0, 1, 1, 0, 1]
MONK = [1, 0, 1, 1, 1, 0, 0, 1, 1]
EXPECTED = [1, 0, 0, 1, 0, 0, 0, 0, 1]


def install(weidu, game):
    return subprocess.run(
        [weidu, "sorcerer-monk/setup-sorcerer-monk.tp2", "--game", str(game),
         "--language", "0", "--noautoupdate", "--force-install-list", "0"],
        cwd=game, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120,
    )


def exercise_live_intersection(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-align-live-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "alignmnt.2da",
            HEADERS,
            [("SORCERER", SORCERER), ("MONK", MONK)],
            default="0",
        )
        original = (override / "alignmnt.2da").read_bytes()

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "alignmnt.2da", "SORCERER_MONK")[1:] == [str(v) for v in EXPECTED]
        print("live ALIGNMNT intersection install: OK", flush=True)

        run_weidu(weidu, game, "--reinstall")
        assert find_row(override / "alignmnt.2da", "SORCERER_MONK")[1:] == [str(v) for v in EXPECTED]
        print("live ALIGNMNT intersection reinstall: OK", flush=True)

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert (override / "alignmnt.2da").read_bytes() == original
        print("live ALIGNMNT uninstall restore: OK", flush=True)


def exercise_invalid_component(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-align-invalid-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        bad_monk = MONK.copy()
        bad_monk[4] = 2
        write_2da(
            override / "alignmnt.2da",
            HEADERS,
            [("SORCERER", SORCERER), ("MONK", bad_monk)],
            default="0",
        )
        originals = {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}

        result = install(weidu, game)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Could not derive Sorcerer/Monk alignment restrictions from ALIGNMNT.2DA" in output, output
        for name, original in originals.items():
            assert (override / name).read_bytes() == original, name
        print("invalid Monk ALIGNMNT value: rejected safely", flush=True)


def exercise_missing_component(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-align-missing-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(override / "alignmnt.2da", HEADERS, [("SORCERER", SORCERER)], default="0")
        originals = {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}

        result = install(weidu, game)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "Could not derive Sorcerer/Monk alignment restrictions from ALIGNMNT.2DA" in output, output
        for name, original in originals.items():
            assert (override / name).read_bytes() == original, name
        print("missing Monk ALIGNMNT row: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_live_intersection(weidu)
    exercise_invalid_component(weidu)
    exercise_missing_component(weidu)


if __name__ == "__main__":
    main()
