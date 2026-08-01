from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TP2 = (ROOT / "sorcerer-monk-cleric" / "setup-sorcerer-monk-cleric.tp2").read_text(encoding="utf-8")


class SorcererMonkClericIdentityTests(unittest.TestCase):
    def test_class_id_follows_clskills_row(self):
        self.assertIn("OUTER_SET smc_expected_class_id = smc_clskills_id", TP2)
        self.assertIn("OUTER_SET smc_expected_class_id = smc_clskills_rows", TP2)
        self.assertIn("smc_expected_class_id > 31", TP2)
        self.assertIn("OUTER_SET smc_class_id = smc_expected_class_id", TP2)
        self.assertNotIn("SORCERER_MONK_CLERIC 22 * %smc_lower%", TP2)
        self.assertNotIn("786436 22 *", TP2)
        self.assertNotIn("APPEND ~fistweap.2da~ ~22", TP2)

    def test_component_ids_match_multiclass_mask(self):
        self.assertIn("smc_cleric_clskills_id != 3", TP2)
        self.assertIn("smc_sorcerer_clskills_id != 19", TP2)
        self.assertIn("smc_monk_clskills_id != 20", TP2)
        self.assertIn("smc_cleric_class_id != 3", TP2)
        self.assertIn("smc_sorcerer_class_id != 19", TP2)
        self.assertIn("smc_monk_class_id != 20", TP2)
        self.assertGreaterEqual(TP2.count("FAIL @10"), 2)

    def test_class_ids_registration_uses_allocated_id(self):
        self.assertIn("IDS_OF_SYMBOL (~class~ ~SORCERER_MONK_CLERIC~)", TP2)
        self.assertIn("LOOKUP_IDS_SYMBOL_OF_INT smc_ids_class_symbol ~class~ smc_class_id", TP2)
        self.assertIn("%smc_class_id% SORCERER_MONK_CLERIC", TP2)
        self.assertIn("FAIL @12", TP2)

    def test_fistweap_uses_allocated_id_and_checks_collision(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~smc_fistweap~ smc_fistweap_cols", TP2)
        self.assertIn("smc_fistweap_class_id = smc_class_id", TP2)
        self.assertIn("FAIL @13", TP2)
        self.assertIn("APPEND ~fistweap.2da~ ~%smc_class_id% MFIST1", TP2)

    def test_duplicate_smc_identity_rows_are_rejected(self):
        self.assertIn("ACTION_IF smc_clskills_matches > 1", TP2)
        self.assertIn("ACTION_IF smc_class_table_matches > 1", TP2)
        self.assertGreaterEqual(TP2.count("FAIL @14"), 2)


if __name__ == "__main__":
    unittest.main()
