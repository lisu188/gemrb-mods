from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu, write_2da


ERROR = "Unsupported CLSWPBON.2DA layout or duplicate Monk combat rows"


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


def exercise_live_monk_row(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clswpbon-live-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "clswpbon.2da",
            ["GETS_PROF_APR", "UNARMED_DIVISOR", "ZERO_SKILL_THAC0"],
            [("SORCERER", [0, 0, 4]), ("MONK", [0, 5, 7])],
            default="0",
        )
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "clswpbon.2da", "SORCERER_MONK")[1:] == ["0", "5", "7"]

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "clswpbon.2da", "SORCERER_MONK")[1:] == ["0", "5", "7"]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "live CLSWPBON uninstall")
        print("live Monk CLSWPBON row: OK", flush=True)


def exercise_missing_monk_fallback(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clswpbon-fallback-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "clswpbon.2da",
            ["GETS_PROF_APR", "UNARMED_DIVISOR", "ZERO_SKILL_THAC0"],
            [("SORCERER", [0, 0, 4])],
            default="0",
        )
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        assert find_row(override / "clswpbon.2da", "SORCERER_MONK")[1:] == ["1", "3", "2"]
        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "CLSWPBON fallback uninstall")
        print("missing Monk CLSWPBON row uses stock fallback: OK", flush=True)


def exercise_duplicate_monk_rows(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clswpbon-duplicate-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "clswpbon.2da",
            ["GETS_PROF_APR", "UNARMED_DIVISOR", "ZERO_SKILL_THAC0"],
            [("MONK", [1, 3, 2]), ("MONK", [1, 4, 2])],
            default="0",
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "duplicate Monk CLSWPBON rejection")


def exercise_wrong_schema(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clswpbon-schema-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "clswpbon.2da",
            ["GETS_PROF_APR", "UNARMED_DIVISOR"],
            [("MONK", [1, 3])],
            default="0",
        )
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "CLSWPBON schema rejection")


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_live_monk_row(weidu)
    exercise_missing_monk_fallback(weidu)
    exercise_duplicate_monk_rows(weidu)
    exercise_wrong_schema(weidu)


if __name__ == "__main__":
    main()
