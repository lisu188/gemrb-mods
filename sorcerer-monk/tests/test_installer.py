from pathlib import Path
import re
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


def payloads(directive, table):
    pattern = rf"{directive}\s+~{re.escape(table)}~\s+~([^~]*)~"
    return re.findall(pattern, TP2, flags=re.IGNORECASE)


class InstallerTests(unittest.TestCase):
    def test_split_class_metadata(self):
        class_rows = payloads("APPEND", "classes.2da")
        self.assertIn("SORCERER_MONK * 786432 0x20040000 -1 0 9", class_rows)
        self.assertIn("SORCERER_MONK 1 0 0 0 0 0 0", payloads("APPEND", "clsrcreq.2da"))
        self.assertIn("SORCERER_MONK *", payloads("APPEND", "hpclass.2da"))

    def test_released_class_metadata(self):
        class_rows = payloads("APPEND", "classes.2da")
        self.assertIn(
            "SORCERER_MONK %sm_lower% %sm_desc% %sm_mixed% * 786432 %sm_class_id% * 0x20040000 -1 1 0 0 0 0 0 0 0 9",
            class_rows,
        )

    def test_class_registration_uses_allocated_id(self):
        self.assertIn("%sm_class_id% SORCERER_MONK", payloads("APPEND", "class.ids"))
        fist_rows = payloads("APPEND", "fistweap.2da")
        self.assertEqual(len(fist_rows), 1)
        self.assertTrue(fist_rows[0].startswith("%sm_class_id% MFIST1 MFIST1 MFIST2"))

    def test_class_id_allocator_reuses_free_slots(self):
        self.assertNotIn("sm_max_class_id + 1", TP2)
        self.assertEqual(TP2.count("SET sm_candidate_id = 21"), 2)
        self.assertEqual(TP2.count("WHILE (sm_candidate_id <= 255) AND (sm_class_id < 0)"), 2)
        self.assertEqual(TP2.count("sm_existing_id = sm_candidate_id"), 2)
        self.assertIn("ACTION_IF (sm_class_id < 0) OR (sm_class_id > 255)", TP2)

    def test_sorcerer_and_monk_features_are_combined(self):
        clskills_rows = payloads("APPEND", "clskills.2da")
        self.assertEqual(len(clskills_rows), 2)
        for row in clskills_rows:
            self.assertIn("MXSPLSRC", row)
            self.assertIn("SKILLS", row)
            self.assertIn("CLABMO01", row)
        self.assertIn("$ $ SORCERER_MONK 0 0 1 1 1 0 0", payloads("APPEND_COL", "thiefscl.2da"))

    def test_modern_monk_skill_progression(self):
        self.assertIn("SORCERER_MONK 0 10", payloads("APPEND", "thiefskl.2da"))
        self.assertNotIn("SORCERER_MONK 10 5", payloads("APPEND", "thiefskl.2da"))

    def test_legacy_monk_skill_progression(self):
        legacy_rows = payloads("APPEND_COL", "skills.2da")
        self.assertIn("$ $ SORCERER_MONK 10 10 -1 -1 -1 1 1 -1 -1", legacy_rows)
        self.assertNotIn("$ $ SORCERER_MONK 10 5 -1 -1 -1 1 1 -1 -1", legacy_rows)

    def test_gameplay_restrictions(self):
        self.assertIn("SORCERER_MONK 1 1 1 0 0 0 0 0 0", payloads("APPEND", "alignmnt.2da"))
        self.assertIn("SORCERER_MONK 2 5", payloads("APPEND", "profs.2da"))

    def test_merged_action_bar(self):
        self.assertIn("SORCERER_MONK 0 3 4 2 8 9 11 12 13", payloads("APPEND", "qslots.2da"))


if __name__ == "__main__":
    unittest.main()
