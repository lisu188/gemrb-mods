from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, write_2da


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def run_weidu(weidu, game, *args, check=True):
    command = [
        weidu,
        "sorcerer-monk/setup-sorcerer-monk.tp2",
        "--game", str(game),
        "--language", "0",
        "--noautoupdate",
        *args,
    ]
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=game,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode:
        print(result.stdout, flush=True)
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout)
    return result


def assert_rejected(result, message):
    print(result.stdout, flush=True)
    assert message.casefold() in result.stdout.casefold(), result.stdout


def exercise_stale_class_ids(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-stale-class-ids-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        (override / "class.ids").write_text(
            "19 SORCERER\n20 MONK\n30 SORCERER_MONK\n",
            encoding="utf-8",
        )
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "CLASS.IDS already maps SORCERER_MONK to a different numeric class identifier")
        assert_snapshot(override, originals, "stale CLASS.IDS rejection")
        print("stale CLASS.IDS mapping: rejected safely", flush=True)


def exercise_missing_component_xpcap(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-missing-xpcap-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_2da(
            override / "xpcap.2da",
            ["XP_CAP"],
            [("SORCERER", [8000000])],
            default="-1",
        )
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "Could not determine valid Sorcerer and Monk experience caps from XPCAP.2DA")
        assert_snapshot(override, originals, "missing component XPCAP rejection")
        print("missing Monk XPCAP row: rejected safely", flush=True)


def exercise_existing_custom_fist_row(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-custom-fist-row-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        fist_path = override / "fistweap.2da"
        with fist_path.open("a", encoding="utf-8") as handle:
            handle.write("21 " + " ".join(["CUSTOM_FIST"] * 41) + "\n")
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        rows = [
            line.split()
            for line in fist_path.read_text(encoding="utf-8").splitlines()
            if line.split() and line.split()[0] == "21"
        ]
        assert len(rows) == 1, rows
        assert rows[0][1:] == ["CUSTOM_FIST"] * 41, rows[0]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "custom FISTWEAP row uninstall")
        print("existing custom FISTWEAP row: preserved without duplication", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_stale_class_ids(weidu)
    exercise_missing_component_xpcap(weidu)
    exercise_existing_custom_fist_row(weidu)


if __name__ == "__main__":
    main()
