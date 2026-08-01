from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class MetadataGuardTests(unittest.TestCase):
    def test_existing_class_ids_symbol_must_match_allocated_id(self):
        self.assertIn("OUTER_SET sm_ids_class_id = IDS_OF_SYMBOL (~class~ ~SORCERER_MONK~)", TP2)
        self.assertIn("sm_ids_class_id != sm_class_id", TP2)
        self.assertIn("FAIL @17", TP2)

    def test_allocated_class_id_must_not_belong_to_another_symbol(self):
        self.assertIn("LOOKUP_IDS_SYMBOL_OF_INT sm_ids_class_symbol ~class~ sm_class_id", TP2)
        self.assertIn("OUTER_SET sm_ids_numeric_conflict = 1", TP2)
        self.assertIn("sm_ids_numeric_conflict = 1", TP2)
        self.assertIn("FAIL @17", TP2)

    def test_component_class_ids_match_fixed_multiclass_mask(self):
        self.assertIn("OUTER_SET sm_sorcerer_clskills_id = (0 - 1)", TP2)
        self.assertIn("OUTER_SET sm_monk_clskills_id = (0 - 1)", TP2)
        self.assertIn("OUTER_SET sm_sorcerer_class_id = (0 - 1)", TP2)
        self.assertIn("OUTER_SET sm_monk_class_id = (0 - 1)", TP2)
        self.assertIn("sm_sorcerer_clskills_id != 19", TP2)
        self.assertIn("sm_monk_clskills_id != 20", TP2)
        self.assertIn("sm_sorcerer_class_id != 19", TP2)
        self.assertIn("sm_monk_class_id != 20", TP2)
        self.assertIn("FAIL @18", TP2)

    def test_xpcap_requires_both_component_rows(self):
        self.assertIn("OUTER_SET sm_found_sorcerer_xpcap = 0", TP2)
        self.assertIn("OUTER_SET sm_found_monk_xpcap = 0", TP2)
        self.assertIn("SET sm_found_sorcerer_xpcap = 1", TP2)
        self.assertIn("SET sm_found_monk_xpcap = 1", TP2)
        self.assertIn("sm_found_sorcerer_xpcap != 1", TP2)
        self.assertIn("sm_found_monk_xpcap != 1", TP2)

    def test_fistweap_numeric_row_collision_is_rejected(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_fistweap~ sm_fistweap_cols", TP2)
        self.assertIn("sm_fistweap_class_id = sm_class_id", TP2)
        self.assertIn("SET sm_fistweap_id_conflict = 1", TP2)
        self.assertIn("FAIL @19", TP2)
        self.assertIn(
            "UNLESS ~^[ %TAB%]*%sm_class_id%\\([ %TAB%]\\|$\\)~",
            TP2,
        )


if __name__ == "__main__":
    unittest.main()
