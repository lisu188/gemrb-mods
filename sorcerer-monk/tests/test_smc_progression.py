from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TP2 = (ROOT / "sorcerer-monk-cleric" / "setup-sorcerer-monk-cleric.tp2").read_text(encoding="utf-8")


class SorcererMonkClericProgressionTests(unittest.TestCase):
    def test_proficiency_rate_matches_fastest_component(self):
        self.assertIn("SORCERER_MONK_CLERIC 2 4", TP2)
        self.assertNotIn("SORCERER_MONK_CLERIC  2 5", TP2)

    def test_modern_monk_skill_progression(self):
        self.assertIn("$ $ SORCERER_MONK_CLERIC 0 0 1 1 1 0 0", TP2)
        self.assertIn("SORCERER_MONK_CLERIC 0 10", TP2)
        self.assertNotIn("SORCERER_MONK_CLERIC 10 5", TP2)

    def test_legacy_monk_skill_progression_and_availability(self):
        self.assertIn(
            "$ $ SORCERER_MONK_CLERIC 10 10 -1 -1 1 1 1 -1 -1",
            TP2,
        )
        self.assertNotIn(
            "$ $ SORCERER_MONK_CLERIC 10 5 -1 -1 -1 1 1 -1 -1",
            TP2,
        )


if __name__ == "__main__":
    unittest.main()
