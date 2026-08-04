from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_layout_smoke import make_released_clskills
from weidu_smoke import build_fixture, find_row, run_weidu


ERROR = "Could not derive Sorcerer/Monk Sorcerer spell metadata from CLSKILLS.2DA"


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def rewrite_sorcerer_fields(override, magespell, booktype):
    path = override / "clskills.2da"
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        cells = line.split()
        if cells and cells[0] == "SORCERER":
            cells[3] = str(magespell)
            cells[9] = str(booktype)
            lines[index] = " ".join(cells)
            break
    else:
        raise AssertionError("missing Sorcerer CLSKILLS row")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def exercise_layout(weidu, legacy):
    label = "legacy" if legacy else "current"
    with tempfile.TemporaryDirectory(prefix=f"sorcerer-monk-clskills-spells-{label}-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        if legacy:
            make_released_clskills(override)
        rewrite_sorcerer_fields(override, "MODSRC99", 7)
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        row = find_row(override / "clskills.2da", "SORCERER_MONK")
        assert row[3] == "MODSRC99", row
        assert row[9] == "7", row

        run_weidu(weidu, game, "--force-install-list", "0")
        row = find_row(override / "clskills.2da", "SORCERER_MONK")
        assert row[3] == "MODSRC99", row
        assert row[9] == "7", row

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, f"{label} CLSKILLS spell metadata uninstall")
        print(f"{label} CLSKILLS Sorcerer spell metadata: OK", flush=True)


def exercise_invalid_magespell(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clskills-spells-missing-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        rewrite_sorcerer_fields(override, "*", 2)
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "invalid Sorcerer MAGESPELL rejection")


def exercise_invalid_booktype(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clskills-booktype-invalid-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        rewrite_sorcerer_fields(override, "MXSPLSRC", -1)
        originals = snapshot(override)
        result = run_rejected(weidu, game)
        print(result.stdout, flush=True)
        assert ERROR.casefold() in result.stdout.casefold(), result.stdout
        assert_snapshot(override, originals, "invalid Sorcerer BOOKTYPE rejection")


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_layout(weidu, False)
    exercise_layout(weidu, True)
    exercise_invalid_magespell(weidu)
    exercise_invalid_booktype(weidu)


if __name__ == "__main__":
    main()
