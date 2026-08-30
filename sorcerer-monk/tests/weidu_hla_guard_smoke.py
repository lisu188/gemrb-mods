from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import HLA_HEADERS, build_fixture, write_2da


ERROR = "Could not build a complete Sorcerer/Monk high-level-ability table"
AMBIGUOUS_ERROR = "same ability with different eligibility metadata"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def run_weidu(weidu, game):
    command = [
        weidu,
        "sorcerer-monk/setup-sorcerer-monk.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        "--force-install-list", "0",
    ]
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        cwd=game,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def write_lunumab(override):
    write_2da(
        override / "lunumab.2da",
        ["FIRST_LEVEL", "STEP", "MAX_LEVEL", "RATE"],
        [("SORCERER", [14, 1, 99, 1]), ("MONK", [14, 1, 99, 1])],
    )


def assert_rejected(weidu, game, label, error=ERROR):
    override = game / "override"
    originals = snapshot(override)
    result = run_weidu(weidu, game)
    print(result.stdout, flush=True)
    assert error.casefold() in result.stdout.casefold(), result.stdout
    assert_snapshot(override, originals, label)


def exercise_missing_luabbr(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-missing-luabbr-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)
        (override / "luabbr.2da").unlink()
        assert_rejected(weidu, game, "missing LUABBR rejection")
        print("LUNUMAB without LUABBR: rejected safely", flush=True)


def exercise_missing_component_abbreviation(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-missing-abbr-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)
        write_2da(override / "luabbr.2da", ["ABBREV"], [("SORCERER", ["SO0"])])
        assert_rejected(weidu, game, "missing component abbreviation rejection")
        print("missing Monk LUABBR entry: rejected safely", flush=True)


def exercise_missing_component_table(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-missing-table-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)
        (override / "lumo0.2da").unlink()
        assert_rejected(weidu, game, "missing component HLA table rejection")
        print("missing Monk HLA source table: rejected safely", flush=True)


def exercise_mismatched_component_tables(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-width-mismatch-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)
        write_2da(
            override / "lumo0.2da",
            HLA_HEADERS[:-1],
            [("0", ["GA_SPCL930", 1, "ICON", 1, 99, 1, "*", "*"])],
        )
        assert_rejected(weidu, game, "HLA source width mismatch rejection")
        print("incompatible Sorcerer/Monk HLA source widths: rejected safely", flush=True)


def exercise_empty_component_tables(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-empty-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)
        for name in ("luso0.2da", "lumo0.2da"):
            write_2da(override / name, HLA_HEADERS, [("0", ["*"] * len(HLA_HEADERS))])
        assert_rejected(weidu, game, "empty HLA sources rejection")
        print("empty Sorcerer/Monk HLA sources: rejected safely", flush=True)


def exercise_conflicting_duplicate_ability(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-hla-conflicting-duplicate-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_lunumab(override)

        # GA_SPCL900 is deliberately shared by the normal fixture. Change only
        # Monk's repeat limit: the old merge would silently keep Sorcerer's row
        # and discard this different policy for the same ability.
        write_2da(
            override / "lumo0.2da",
            HLA_HEADERS,
            [
                ("0", ["GA_SPCL900", 1, "ICON", 1, 99, 2, "*", "*", "*"]),
                ("1", ["GA_SPCL930", 1, "ICON", 1, 99, 1, "*", "*", "*"]),
                ("2", ["GA_SPCL931", 1, "ICON", 1, 99, 1, "*", "*", "*"]),
                ("3", ["*"] * len(HLA_HEADERS)),
            ],
        )
        assert_rejected(
            weidu,
            game,
            "conflicting duplicate HLA rejection",
            AMBIGUOUS_ERROR,
        )
        print("same HLA with conflicting policy: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_missing_luabbr(weidu)
    exercise_missing_component_abbreviation(weidu)
    exercise_missing_component_table(weidu)
    exercise_mismatched_component_tables(weidu)
    exercise_empty_component_tables(weidu)
    exercise_conflicting_duplicate_ability(weidu)


if __name__ == "__main__":
    main()
