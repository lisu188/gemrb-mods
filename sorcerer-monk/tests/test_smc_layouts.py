from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TP2 = (ROOT / "sorcerer-monk-cleric" / "setup-sorcerer-monk-cleric.tp2").read_text(encoding="utf-8")


class SorcererMonkClericLayoutTests(unittest.TestCase):
    def test_layout_detection_uses_classes_schema(self):
        self.assertIn("COUNT_2DA_COLS smc_classes_cols", TP2)
        self.assertIn("ACTION_IF smc_classes_cols = 7", TP2)
        self.assertIn("ACTION_IF smc_classes_cols = 19", TP2)
        self.assertNotIn("ACTION_IF FILE_EXISTS_IN_GAME ~hpclass.2da~", TP2)

    def test_split_clastext_supports_normalized_and_native_ee_shapes(self):
        self.assertIn("ACTION_IF smc_clastext_cols = 6", TP2)
        self.assertIn("ACTION_IF smc_clastext_cols = 9", TP2)
        self.assertIn(
            "SORCERER_MONK_CLERIC 22 * %smc_lower% %smc_desc% %smc_mixed%",
            TP2,
        )
        self.assertIn(
            "SORCERER_MONK_CLERIC 22 16384 %smc_lower% %smc_desc% %smc_mixed% -1 0 %smc_brief%",
            TP2,
        )
        self.assertIn(
            "SORCERER_MONK_CLERIC 22 16384 %smc_lower% %smc_desc% %smc_mixed% -1 0 %smc_brief% -1",
            TP2,
        )
        self.assertNotIn("22 * SORCERER_MONK_CLERIC PLACEHOLDER_1", TP2)

    def test_clskills_rows_match_both_supported_widths(self):
        self.assertIn("ACTION_IF smc_clskills_cols = 17", TP2)
        self.assertIn("smc_clskills_cols != 16", TP2)
        self.assertIn(
            "SORCERER_MONK_CLERIC * MXSPLPRS MXSPLSRC 89000 * SKILLS * 0 2 * CLABMO01 -4 2500000 * 0 *",
            TP2,
        )
        self.assertIn(
            "SORCERER_MONK_CLERIC * MXSPLPRS MXSPLSRC 89000 * SKILLS * 0 2 * CLABMO01 2500000 * 0 *",
            TP2,
        )

    def test_schema_checks_precede_string_resolution(self):
        self.assertLess(TP2.index("COUNT_2DA_COLS smc_classes_cols"), TP2.index("RESOLVE_STR_REF (@1)"))
        self.assertLess(TP2.index("COUNT_2DA_COLS smc_clskills_cols"), TP2.index("RESOLVE_STR_REF (@1)"))


if __name__ == "__main__":
    unittest.main()
