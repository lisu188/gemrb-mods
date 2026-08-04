from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class ProficiencyProgressionTests(unittest.TestCase):
    def test_component_rows_are_preflighted(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_profs~ sm_profs_cols", TP2)
        self.assertIn("SET sm_found_sorcerer_profs += 1", TP2)
        self.assertIn("SET sm_found_monk_profs += 1", TP2)
        self.assertIn("sm_profs_cols != 3", TP2)
        self.assertIn("FAIL @27", TP2)

    def test_starting_points_use_component_maximum(self):
        self.assertIn("OUTER_SET sm_prof_first = sm_sorcerer_prof_first", TP2)
        self.assertIn("sm_monk_prof_first > sm_prof_first", TP2)
        self.assertIn("OUTER_SET sm_prof_first = sm_monk_prof_first", TP2)

    def test_rate_uses_fastest_component(self):
        self.assertIn("OUTER_SET sm_prof_rate = sm_sorcerer_prof_rate", TP2)
        self.assertIn("sm_monk_prof_rate < sm_prof_rate", TP2)
        self.assertIn("OUTER_SET sm_prof_rate = sm_monk_prof_rate", TP2)

    def test_derived_row_is_appended(self):
        self.assertIn("APPEND ~profs.2da~ ~SORCERER_MONK %sm_profs_row%~", TP2)
        self.assertNotIn("APPEND ~profs.2da~ ~SORCERER_MONK 2 4~", TP2)


if __name__ == "__main__":
    unittest.main()
