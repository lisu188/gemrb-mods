from pathlib import Path
import re
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


def clskills_payloads():
    return re.findall(r"APPEND\s+~clskills\.2da~\s+~([^~]*)~", TP2, flags=re.IGNORECASE)


class SorcererSpellMetadataInvariantTests(unittest.TestCase):
    def test_combined_rows_keep_hybrid_monk_metadata(self):
        rows = clskills_payloads()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("%sm_magespell%", row)
            self.assertIn("%sm_booktype%", row)
            self.assertIn("SKILLS", row)
            self.assertIn("CLABMO01", row)

    def test_spontaneous_conversion_remains_disabled(self):
        for row in clskills_payloads():
            self.assertEqual(row.split()[-1], "*")


if __name__ == "__main__":
    unittest.main()
