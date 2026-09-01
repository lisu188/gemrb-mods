from pathlib import Path
import importlib.util
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "sorcerer-monk" / "tools" / "build_live_oracle.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("build_live_oracle", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_2da(path, headers, rows, default="*"):
    lines = ["2DA V1.0", default, " ".join(headers)]
    lines.extend(" ".join([name, *values]) for name, values in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def class_rows():
    rows = [(f"CLASS_{index}", ["*", "0"]) for index in range(18)]
    rows.extend([
        ("SORCERER", ["MXSPLSRC", "2"]),
        ("MONK", ["*", "0"]),
        ("SORCERER_MONK", ["MXSPLSRC", "2"]),
    ])
    return rows


def qslot_rows():
    rows = [(f"CLASS_{index}", ["0", "0", "0"]) for index in range(20)]
    rows.append(("SORCERER_MONK", ["3", "2", "22"]))
    return rows


def make_game(root, custom_id=21, include_hla=True):
    game = root / "game"
    override = game / "override"
    override.mkdir(parents=True)
    package = game / "sorcerer-monk"
    package.mkdir()
    (package / "setup-sorcerer-monk.tp2").write_text("VERSION ~2.0~\n", encoding="utf-8")

    (override / "class.ids").write_text(
        f"19 SORCERER\n20 MONK\n{custom_id} SORCERER_MONK\n",
        encoding="utf-8",
    )
    write_2da(override / "clskills.2da", ["MAGESPELL", "BOOKTYPE"], class_rows())
    write_2da(
        override / "CLASSES.2DA",
        ["ID", "MULTI"],
        [
            ("SORCERER", ["19", "0"]),
            ("MONK", ["20", "0"]),
            ("SORCERER_MONK", [str(custom_id), "786432"]),
        ],
    )
    write_2da(override / "QSLOTS.2DA", ["A", "B", "C"], qslot_rows())
    write_2da(
        override / "FISTWEAP.2DA",
        ["L0", "L1", "L2", "L3"],
        [
            ("20", ["MFIST1", "MFIST1", "MFIST2", "MFIST2"]),
            (str(custom_id), ["MFIST1", "MFIST1", "MFIST2", "MFIST2"]),
        ],
    )
    write_2da(
        override / "PROFS.2DA",
        ["FIRST", "RATE"],
        [
            ("SORCERER", ["2", "6"]),
            ("MONK", ["2", "4"]),
            ("SORCERER_MONK", ["2", "4"]),
        ],
    )
    write_2da(
        override / "CLSWPBON.2DA",
        ["FIRST", "RATE", "BONUS"],
        [
            ("MONK", ["1", "3", "2"]),
            ("SORCERER_MONK", ["1", "3", "2"]),
        ],
    )
    write_2da(
        override / "NUMWSLOT.2DA",
        ["SLOTS"],
        [("MONK", ["3"]), ("SORCERER_MONK", ["2"])],
    )

    write_2da(
        override / "CLASTEXT.2DA",
        ["ID", "LOWER"],
        [("SORCERER_MONK", [str(custom_id), "12345"])],
    )
    write_2da(
        override / "HPCLASS.2DA",
        ["TABLE"],
        [("SORCERER_MONK", ["*"])],
    )
    write_2da(
        override / "XPCAP.2DA",
        ["VALUE"],
        [("SORCERER_MONK", ["8000000"])],
    )
    write_2da(
        override / "ALIGNMNT.2DA",
        ["LG", "LN", "LE", "NG", "TN", "NE", "CG", "CN", "CE"],
        [("SORCERER_MONK", ["1", "1", "1", "0", "0", "0", "0", "0", "0"])],
    )
    write_2da(
        override / "THIEFSKL.2DA",
        ["FIRST", "RATE"],
        [("SORCERER_MONK", ["0", "10"])],
    )
    write_2da(
        override / "THIEFSCL.2DA",
        ["MONK", "SORCERER_MONK"],
        [("STEALTH", ["1", "1"]), ("SEARCH", ["1", "1"])],
    )
    write_2da(
        override / "WEAPPROF.2DA",
        ["MONK", "SORCERER_MONK"],
        [("DAGGER", ["1", "1"]), ("TWOHANDED", ["0", "0"])],
    )

    if include_hla:
        write_2da(
            override / "LUABBR.2DA",
            ["TABLE"],
            [("SORCERER_MONK", ["SM0"])],
        )
        write_2da(
            override / "LUNUMAB.2DA",
            ["FIRST", "RATE"],
            [("SORCERER_MONK", ["1", "1"])],
        )
        write_2da(
            override / "LUSM0.2DA",
            ["ABILITY", "MIN_LEVEL"],
            [
                ("SORCERER_HLA", ["GA_SPIN100", "1"]),
                ("MONK_HLA", ["GA_SPIN200", "1"]),
            ],
        )
    return game


class LiveOracleTests(unittest.TestCase):
    def setUp(self):
        self.tool = load_tool()

    def test_oracle_is_derived_from_installed_resources(self):
        with tempfile.TemporaryDirectory() as folder_name:
            game = make_game(Path(folder_name))
            metadata = {
                "game_type": "bg2ee",
                "fixture_id": "fixture-a",
                "gemrb_commit": "abc123",
                "weidu_version": "251.00",
            }
            oracle = self.tool.build_oracle(game, metadata)

            self.assertEqual(oracle["schema_version"], 1)
            self.assertEqual(oracle["metadata"], metadata)
            self.assertEqual(oracle["mod"]["version"], "2.0")
            self.assertEqual(oracle["identity"]["class_id"], 21)
            self.assertEqual(oracle["identity"]["clskills_position_zero_based"], 20)
            self.assertEqual(oracle["identity"]["clskills_id_offset"], 1)
            self.assertEqual(oracle["identity"]["clskills_derived_id"], 21)
            self.assertEqual(
                oracle["identity"]["component_class_ids"],
                {"sorcerer": 19, "monk": 20},
            )

            installed = oracle["installed"]
            self.assertEqual(installed["qslots"]["position_zero_based"], 20)
            self.assertEqual(installed["qslots"]["row"]["name"], "SORCERER_MONK")
            self.assertEqual(installed["fistweap"]["by_monk_level"]["2"], "MFIST2")
            self.assertEqual(installed["profs"]["mapping"], {"FIRST": "2", "RATE": "4"})
            self.assertEqual(installed["clswpbon"]["values"], ["1", "3", "2"])
            self.assertEqual(installed["numwslot"]["values"], ["2"])
            self.assertEqual(installed["thiefskl"]["values"], ["0", "10"])
            self.assertEqual(installed["thiefscl"]["values"]["STEALTH"], "1")
            self.assertEqual(installed["weapprof"]["values"]["DAGGER"], "1")

            hla = installed["hla"]
            self.assertTrue(hla["enabled"])
            self.assertEqual(hla["abbreviation"], "SM0")
            self.assertEqual(hla["resource"].upper(), "LUSM0.2DA")
            self.assertEqual(hla["usable_row_count"], 2)
            self.assertEqual(len(hla["resource_sha256"]), 64)

            self.assertEqual(oracle["components"]["sorcerer"]["class_id"], 19)
            self.assertEqual(oracle["components"]["monk"]["class_id"], 20)
            self.assertEqual(oracle["components"]["monk"]["fistweap"]["name"], "20")
            self.assertEqual(len(oracle["files"]["CLASS.IDS"]["sha256"]), 64)
            self.assertEqual(oracle["files"]["CLSKILLS.2DA"]["path"], "override/clskills.2da")

    def test_identity_mismatch_fails_before_live_run(self):
        with tempfile.TemporaryDirectory() as folder_name:
            game = make_game(Path(folder_name), custom_id=22)
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                self.tool.build_oracle(game)

    def test_missing_generated_hla_resource_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder_name:
            game = make_game(Path(folder_name))
            (game / "override" / "LUSM0.2DA").unlink()
            with self.assertRaisesRegex(RuntimeError, "LUSM0.2DA"):
                self.tool.build_oracle(game)

    def test_hla_absence_is_recorded_without_faking_support(self):
        with tempfile.TemporaryDirectory() as folder_name:
            game = make_game(Path(folder_name), include_hla=False)
            oracle = self.tool.build_oracle(game)
            self.assertFalse(oracle["installed"]["hla"]["enabled"])
            self.assertIn("LUABBR", oracle["installed"]["hla"]["reason"])


if __name__ == "__main__":
    unittest.main()
