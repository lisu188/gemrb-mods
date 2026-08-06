from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class AlignmentTests(unittest.TestCase):
    def test_component_alignment_rows_are_preflighted(self):
        self.assertIn("READ_2DA_ENTRIES_NOW ~sm_alignmnt~ sm_alignmnt_cols", TP2)
        self.assertIn("SET sm_found_sorcerer_alignmnt += 1", TP2)
        self.assertIn("SET sm_found_monk_alignmnt += 1", TP2)
        self.assertIn("sm_alignmnt_cols != 10", TP2)
        self.assertIn("sm_found_sorcerer_alignmnt != 1", TP2)
        self.assertIn("sm_found_monk_alignmnt != 1", TP2)
        self.assertIn("FAIL @26", TP2)

    def test_combined_alignment_is_component_intersection(self):
        for name in ("lg", "ln", "le", "ng", "tn", "ne", "cg", "cn", "ce"):
            self.assertIn(
                f"OUTER_SET sm_align_{name} = sm_sorcerer_align_{name} * sm_monk_align_{name}",
                TP2,
            )

    def test_derived_alignment_row_is_appended(self):
        self.assertIn("APPEND ~alignmnt.2da~ ~SORCERER_MONK %sm_alignmnt_row%~", TP2)
        self.assertNotIn("APPEND ~alignmnt.2da~ ~SORCERER_MONK 1 1 1 0 0 0 0 0 0~", TP2)


if __name__ == "__main__":
    unittest.main()
