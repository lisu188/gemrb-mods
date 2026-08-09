from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class ModernMonkSkillTests(unittest.TestCase):
    def test_live_monk_availability_column_is_copied(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_thiefscl~ 1", TP2)
        self.assertIn("sm_thiefscl_monk_col = sm_i + 1", TP2)
        self.assertIn("SPRINT sm_thiefscl_column ~$ $ SORCERER_MONK~", TP2)
        self.assertIn("sm_thiefscl_invalid = 1", TP2)

    def test_live_monk_point_progression_is_copied(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_thiefskl~ sm_thiefskl_cols", TP2)
        self.assertIn("SET sm_monk_thiefskl_matches += 1", TP2)
        self.assertIn("SPRINT sm_thiefskl_row ~%sm_thiefskl_start% %sm_thiefskl_level%~", TP2)

    def test_incomplete_modern_tables_are_rejected(self):
        self.assertIn("NOT FILE_EXISTS_IN_GAME ~thiefskl.2da~", TP2)
        self.assertIn("sm_thiefscl_monk_col < 0", TP2)
        self.assertIn("sm_monk_thiefskl_matches != 1", TP2)
        self.assertIn("FAIL @29", TP2)

    def test_modern_rows_use_derived_payloads(self):
        self.assertIn("APPEND_COL ~thiefscl.2da~ ~%sm_thiefscl_column%~", TP2)
        self.assertIn("APPEND ~thiefskl.2da~ ~SORCERER_MONK %sm_thiefskl_row%~", TP2)
        self.assertNotIn("APPEND_COL ~thiefscl.2da~ ~$ $ SORCERER_MONK 0 0 1 1 1 0 0~", TP2)
        self.assertNotIn("APPEND ~thiefskl.2da~ ~SORCERER_MONK 0 10~", TP2)

    def test_legacy_fallback_remains_unchanged(self):
        self.assertIn("APPEND_COL ~skills.2da~ ~$ $ SORCERER_MONK 10 10 -1 -1 1 1 1 -1 -1~", TP2)


if __name__ == "__main__":
    unittest.main()
