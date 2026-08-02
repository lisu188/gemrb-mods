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


def exercise_duplicate_clskills_rows(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-duplicate-clskills-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        clskills_path = override / "clskills.2da"
        duplicate = "SORCERER_MONK * * MXSPLSRC 89000 * SKILLS * 0 2 * CLABMO01 -3 2500000 * 0 *\n"
        with clskills_path.open("a", encoding="utf-8") as handle:
            handle.write(duplicate)
            handle.write(duplicate)
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "Multiple SORCERER_MONK identity rows already exist")
        assert_snapshot(override, originals, "duplicate CLSKILLS rejection")
        print("duplicate CLSKILLS identity rows: rejected safely", flush=True)


def exercise_duplicate_class_table_rows(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-duplicate-classes-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        with (override / "clskills.2da").open("a", encoding="utf-8") as handle:
            handle.write("SORCERER_MONK * * MXSPLSRC 89000 * SKILLS * 0 2 * CLABMO01 -3 2500000 * 0 *\n")
        duplicate = "SORCERER_MONK 1 2 3 * 786432 21 * 0x20040000 -1 1 0 0 0 0 0 0 0 9\n"
        with (override / "classes.2da").open("a", encoding="utf-8") as handle:
            handle.write(duplicate)
            handle.write(duplicate)
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "Multiple SORCERER_MONK identity rows already exist")
        assert_snapshot(override, originals, "duplicate CLASSES rejection")
        print("duplicate active class-table identity rows: rejected safely", flush=True)


def exercise_stale_class_ids_symbol(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-stale-class-ids-symbol-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        (override / "class.ids").write_text(
            "19 SORCERER\n20 MONK\n30 SORCERER_MONK\n",
            encoding="utf-8",
        )
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "CLASS.IDS conflicts with the numeric class identifier required for Sorcerer/Monk")
        assert_snapshot(override, originals, "stale CLASS.IDS symbol rejection")
        print("stale CLASS.IDS symbol mapping: rejected safely", flush=True)


def exercise_class_ids_numeric_collision(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-class-ids-id-collision-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        (override / "class.ids").write_text(
            "19 SORCERER\n20 MONK\n21 OTHER_CLASS\n",
            encoding="utf-8",
        )
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "CLASS.IDS conflicts with the numeric class identifier required for Sorcerer/Monk")
        assert_snapshot(override, originals, "CLASS.IDS numeric collision rejection")
        print("allocated CLASS.IDS numeric ID owned by another symbol: rejected safely", flush=True)


def exercise_noncanonical_component_class_id(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-component-id-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        classes_path = override / "classes.2da"
        lines = classes_path.read_text(encoding="utf-8").splitlines()
        found = False
        for index, line in enumerate(lines):
            fields = line.split()
            if fields and fields[0] == "MONK":
                assert fields[6] == "20", fields
                fields[6] = "18"
                lines[index] = " ".join(fields)
                found = True
                break
        assert found
        classes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        originals = snapshot(override)

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "Sorcerer and Monk must retain GemRB class IDs 19 and 20")
        assert_snapshot(override, originals, "component class ID rejection")
        print("noncanonical Monk class ID: rejected safely", flush=True)


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

        result = run_weidu(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "FISTWEAP.2DA already contains a row for the numeric class identifier allocated to Sorcerer/Monk")
        assert_snapshot(override, originals, "custom FISTWEAP collision rejection")
        print("existing custom FISTWEAP numeric row: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_duplicate_clskills_rows(weidu)
    exercise_duplicate_class_table_rows(weidu)
    exercise_stale_class_ids_symbol(weidu)
    exercise_class_ids_numeric_collision(weidu)
    exercise_noncanonical_component_class_id(weidu)
    exercise_missing_component_xpcap(weidu)
    exercise_existing_custom_fist_row(weidu)


if __name__ == "__main__":
    main()
