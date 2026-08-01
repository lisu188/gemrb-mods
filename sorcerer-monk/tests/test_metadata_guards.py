from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class MetadataGuardTests(unittest.TestCase):
    def test_existing_class_ids_symbol_must_match_allocated_id(self):
        self.assertIn("OUTER_SET sm_ids_class_id = IDS_OF_SYMBOL (~class~ ~SORCERER_MONK~)", TP2)
        self.assertIn("sm_ids_class_id != sm_class_id", TP2)
        self.assertIn("FAIL @17", TP2)

    def test_xpcap_requires_both_component_rows(self):
        self.assertIn("OUTER_SET sm_found_sorcerer_xpcap = 0", TP2)
        self.assertIn("OUTER_SET sm_found_monk_xpcap = 0", TP2)
        self.assertIn("SET sm_found_sorcerer_xpcap = 1", TP2)
        self.assertIn("SET sm_found_monk_xpcap = 1", TP2)
        self.assertIn("sm_found_sorcerer_xpcap != 1", TP2)
        self.assertIn("sm_found_monk_xpcap != 1", TP2)

    def test_fistweap_guard_reserves_numeric_class_row(self):
        self.assertIn(
            "UNLESS ~^[ %TAB%]*%sm_class_id%\\([ %TAB%]\\|$\\)~",
            TP2,
        )
        self.assertNotIn(
            "UNLESS ~^[ %TAB%]*%sm_class_id%[ %TAB%]+MFIST1~",
            TP2,
        )


if __name__ == "__main__":
    unittest.main()
