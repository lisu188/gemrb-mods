from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class SorcererSpellMetadataTests(unittest.TestCase):
    def test_live_sorcerer_spell_fields_are_read(self):
        self.assertIn("READ_2DA_ENTRY_FORMER ~sm_clskills~ sm_i 3 sm_magespell_candidate", TP2)
        self.assertIn("READ_2DA_ENTRY_FORMER ~sm_clskills~ sm_i 9 sm_booktype_candidate", TP2)
        self.assertIn("SET sm_found_sorcerer_spell_metadata = 1", TP2)

    def test_invalid_spell_metadata_is_rejected(self):
        self.assertIn("sm_found_sorcerer_spell_metadata != 1", TP2)
        self.assertIn("FAIL @30", TP2)
        self.assertIn("sm_booktype_candidate >= 0", TP2)

    def test_both_clskills_layouts_use_live_fields(self):
        self.assertGreaterEqual(TP2.count("%sm_magespell%"), 2)
        self.assertGreaterEqual(TP2.count("%sm_booktype%"), 2)
        self.assertNotIn("SORCERER_MONK * * MXSPLSRC %sm_startxp%", TP2)


if __name__ == "__main__":
    unittest.main()
