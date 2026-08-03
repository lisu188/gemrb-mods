from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class AbilityRequirementTests(unittest.TestCase):
    def test_component_rows_are_read_before_append(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_abclasrq~ sm_abclasrq_cols", TP2)
        self.assertIn("STRING_EQUAL_CASE ~SORCERER~", TP2)
        self.assertIn("STRING_EQUAL_CASE ~MONK~", TP2)
        self.assertIn("SET sm_found_sorcerer_abclasrq = 1", TP2)
        self.assertIn("SET sm_found_monk_abclasrq = 1", TP2)

    def test_each_requirement_uses_component_maximum(self):
        for stat in ("str", "dex", "con", "int", "wis", "cha"):
            self.assertIn(f"sm_req_{stat} > sm_abclasrq_{stat}", TP2)
            self.assertIn(f"SET sm_abclasrq_{stat} = sm_req_{stat}", TP2)

    def test_derived_row_is_appended(self):
        self.assertIn(
            "APPEND ~abclasrq.2da~ ~SORCERER_MONK %sm_abclasrq_row%~",
            TP2,
        )
        self.assertNotIn(
            "APPEND ~abclasrq.2da~ ~SORCERER_MONK 0 9 9 9 9 9~",
            TP2,
        )

    def test_malformed_component_data_fails_preflight(self):
        self.assertIn("sm_abclasrq_cols != 7", TP2)
        self.assertIn("sm_found_sorcerer_abclasrq != 1", TP2)
        self.assertIn("sm_found_monk_abclasrq != 1", TP2)
        self.assertIn("FAIL @24", TP2)


if __name__ == "__main__":
    unittest.main()
