from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class CombatBonusTests(unittest.TestCase):
    def test_live_monk_row_is_scanned(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_clswpbon~ sm_clswpbon_cols", TP2)
        self.assertIn("STRING_EQUAL_CASE ~MONK~", TP2)
        self.assertIn("SET sm_monk_clswpbon_matches += 1", TP2)

    def test_schema_and_duplicate_rows_are_rejected(self):
        self.assertIn("sm_clswpbon_cols != 4", TP2)
        self.assertIn("sm_monk_clswpbon_matches > 1", TP2)
        self.assertIn("FAIL @28", TP2)

    def test_stock_monk_row_remains_compatibility_fallback(self):
        self.assertIn("OUTER_SPRINT sm_clswpbon_row ~1 3 2~", TP2)

    def test_installed_row_uses_derived_payload(self):
        self.assertIn("APPEND ~clswpbon.2da~ ~SORCERER_MONK %sm_clswpbon_row%~", TP2)
        self.assertNotIn("APPEND ~clswpbon.2da~ ~SORCERER_MONK 1 3 2~", TP2)


if __name__ == "__main__":
    unittest.main()
