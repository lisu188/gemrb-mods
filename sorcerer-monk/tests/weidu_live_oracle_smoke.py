from pathlib import Path
import importlib.util
import shutil
import sys
import tempfile

from weidu_smoke import build_fixture, run_weidu, write_2da


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "sorcerer-monk" / "tools" / "build_live_oracle.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("build_live_oracle", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")
    tool = load_tool()

    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-live-oracle-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        write_2da(
            game / "override" / "lunumab.2da",
            ["FIRST_LEVEL", "STEP", "MAX_LEVEL", "RATE"],
            [("SORCERER", [14, 1, 99, 1]), ("MONK", [14, 1, 99, 1])],
        )
        run_weidu(weidu, game, "--force-install-list", "0")

        oracle = tool.build_oracle(
            game,
            {
                "game_type": "synthetic-bg2",
                "fixture_id": "weidu-live-oracle-smoke",
                "gemrb_commit": "not-launched",
                "weidu_version": "251.00",
            },
        )
        assert oracle["mod"]["version"] == "2.0", oracle["mod"]
        assert oracle["identity"]["class_id"] == 21, oracle["identity"]
        assert oracle["identity"]["clskills_derived_id"] == 21, oracle["identity"]
        assert oracle["identity"]["component_class_ids"] == {"sorcerer": 19, "monk": 20}

        installed = oracle["installed"]
        assert installed["qslots"]["position_zero_based"] == 20, installed["qslots"]
        assert installed["qslots"]["row"]["name"] == "SORCERER_MONK", installed["qslots"]
        assert installed["fistweap"]["by_monk_level"]["2"] == "MFIST2", installed["fistweap"]
        assert installed["profs"]["values"] == ["2", "4"], installed["profs"]
        assert installed["clswpbon"]["values"] == ["1", "3", "2"], installed["clswpbon"]
        assert installed["numwslot"]["values"] == ["2"], installed["numwslot"]
        assert installed["thiefskl"]["values"] == ["0", "10"], installed["thiefskl"]
        assert installed["thiefscl"]["values"]["FIND_TRAPS"] == "1", installed["thiefscl"]
        assert installed["weapprof"] is not None, installed["weapprof"]

        hla = installed["hla"]
        assert hla["enabled"] is True, hla
        assert hla["abbreviation"] == "SM0", hla
        assert hla["resource"].casefold() == "lusm0.2da", hla
        assert hla["usable_row_count"] == 5, hla
        abilities = [row["values"][0] for row in hla["rows"]]
        assert abilities == [
            "GA_SPCL900", "GA_SPCL920", "GA_SPCL921", "GA_SPCL930", "GA_SPCL931"
        ], abilities
        assert hla["lunumab"] is not None, hla

        assert all(len(entry["sha256"]) == 64 for entry in oracle["files"].values())
        print("real WeiDU installed-data live oracle: OK", flush=True)


if __name__ == "__main__":
    main()
