from pathlib import Path
import re
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class WeaponProficiencyTests(unittest.TestCase):
    def test_live_monk_column_is_detected_and_copied(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_weapprof~ 1", TP2)
        self.assertIn("STRING_EQUAL_CASE ~MONK~", TP2)
        self.assertIn("SET sm_weapprof_monk_col = sm_i + 1", TP2)
        self.assertIn(
            "SPRINT sm_weapprof_column ~%sm_weapprof_column% %sm_weapprof_value%~",
            TP2,
        )

    def test_append_col_uses_derived_payload(self):
        match = re.search(r"APPEND_COL ~weapprof\.2da~ ~([^~]*)~", TP2)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "%sm_weapprof_column%")

    def test_stock_monk_column_remains_only_as_fallback(self):
        self.assertIn("OUTER_SPRINT sm_weapprof_column ~$ $ SORCERER_MONK", TP2)
        self.assertNotIn(
            "APPEND_COL ~weapprof.2da~ ~$ $ SORCERER_MONK 0 1 0 0 1",
            TP2,
        )


if __name__ == "__main__":
    unittest.main()
