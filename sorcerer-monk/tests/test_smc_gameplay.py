from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TP2 = (ROOT / "sorcerer-monk-cleric" / "setup-sorcerer-monk-cleric.tp2").read_text(encoding="utf-8")


class SorcererMonkClericGameplayTests(unittest.TestCase):
    def test_multiclass_saves_and_hit_points_are_component_derived(self):
        self.assertIn("APPEND ~classes.2da~ ~SORCERER_MONK_CLERIC * 786436", TP2)
        self.assertIn("APPEND ~hpclass.2da~ ~SORCERER_MONK_CLERIC *~", TP2)
        self.assertNotIn("SORCERER_MONK_CLERIC  SAVEPRS 786436", TP2)
        self.assertNotIn("SORCERER_MONK_CLERIC  HPMONK", TP2)

    def test_race_requirements_are_human_only(self):
        self.assertIn("SORCERER_MONK_CLERIC 1 0 0 0 0 0 0", TP2)
        self.assertIn(
            "* 786436 %smc_class_id% * 0x40000 -1 1 0 0 0 0 0 0 0 9",
            TP2,
        )
        self.assertNotIn("SORCERER_MONK_CLERIC  1 1 1 0 0 2 0", TP2)

    def test_xpcap_is_derived_from_all_three_components(self):
        self.assertNotIn("SORCERER_MONK_CLERIC  8000000", TP2)
        self.assertIn("OUTER_SET smc_xpcap = (0 - 2)", TP2)
        self.assertIn("OUTER_SET smc_found_cleric_xpcap = 0", TP2)
        self.assertIn("OUTER_SET smc_found_sorcerer_xpcap = 0", TP2)
        self.assertIn("OUTER_SET smc_found_monk_xpcap = 0", TP2)
        self.assertIn("STRING_EQUAL_CASE ~CLERIC~", TP2)
        self.assertIn("smc_xpcap_value = (0 - 1)", TP2)
        self.assertIn("smc_xpcap_value < smc_xpcap", TP2)
        self.assertIn("SORCERER_MONK_CLERIC %smc_xpcap%", TP2)
        self.assertIn("FAIL @15", TP2)


if __name__ == "__main__":
    unittest.main()
