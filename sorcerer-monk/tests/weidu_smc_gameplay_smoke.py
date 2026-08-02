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


def assert_rejected(result, message):
    print(result.stdout, flush=True)
    assert result.returncode != 0, result.stdout
    assert message.casefold() in result.stdout.casefold(), result.stdout


def exercise_restrictive_component_xpcap(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-xpcap-restrictive-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        write_2da(
            override / "xpcap.2da",
            ["XP_CAP"],
            [("CLERIC", [2500000]), ("SORCERER", [8000000]), ("MONK", [-1])],
            default="-1",
        )
        originals = snapshot(override)

        run_smc(weidu, game, "--force-install-list", "0")
        assert row(override / "xpcap.2da", "SORCERER_MONK_CLERIC") == ["SORCERER_MONK_CLERIC", "2500000"]
        run_smc(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "restrictive XPCAP uninstall")
        print("SMC restrictive component XPCAP: OK", flush=True)


def exercise_all_components_uncapped(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-xpcap-uncapped-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        write_2da(
            override / "xpcap.2da",
            ["XP_CAP"],
            [("CLERIC", [-1]), ("SORCERER", [-1]), ("MONK", [-1])],
            default="-1",
        )
        originals = snapshot(override)

        run_smc(weidu, game, "--force-install-list", "0")
        assert row(override / "xpcap.2da", "SORCERER_MONK_CLERIC") == ["SORCERER_MONK_CLERIC", "-1"]
        run_smc(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "uncapped XPCAP uninstall")
        print("SMC all-component uncapped XPCAP: OK", flush=True)


def exercise_missing_component_xpcap(weidu):
    with tempfile.TemporaryDirectory(prefix="smc-xpcap-missing-") as tmp:
        game = Path(tmp)
        prepare_smc(game, build_fixture)
        override = game / "override"
        write_2da(
            override / "xpcap.2da",
            ["XP_CAP"],
            [("SORCERER", [8000000]), ("MONK", [8000000])],
            default="-1",
        )
        originals = snapshot(override)

        result = run_smc(weidu, game, "--force-install-list", "0", check=False)
        assert_rejected(result, "Could not determine valid Cleric, Sorcerer and Monk experience caps from XPCAP.2DA")
        assert_snapshot(override, originals, "missing Cleric XPCAP rejection")
        print("SMC missing component XPCAP: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_restrictive_component_xpcap(weidu)
    exercise_all_components_uncapped(weidu)
    exercise_missing_component_xpcap(weidu)


if __name__ == "__main__":
    main()
