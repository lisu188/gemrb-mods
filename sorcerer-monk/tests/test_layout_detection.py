from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class LayoutDetectionTests(unittest.TestCase):
    def test_classes_schema_selects_layout(self):
        self.assertIn("INDEX_BUFFER (~NAME_REF~)", TP2)
        self.assertIn("INDEX_BUFFER (~CAP_REF~)", TP2)
        self.assertIn("SET sm_detect_classes_cols = 7", TP2)
        self.assertIn("SET sm_detect_classes_cols = 19", TP2)
        self.assertNotIn("COUNT_2DA_COLS sm_classes_cols", TP2)
        self.assertIn("FAIL @15", TP2)

    def test_clastext_schema_is_comment_safe(self):
        self.assertIn("INDEX_BUFFER (~CLASSID~)", TP2)
        self.assertIn("INDEX_BUFFER (~BIOGRAPHY~)", TP2)
        self.assertIn("INDEX_BUFFER (~FALLEN_NOTICE~)", TP2)
        self.assertNotIn("COUNT_2DA_COLS sm_clastext_cols", TP2)

    def test_hpclass_presence_does_not_select_layout(self):
        self.assertNotIn("ACTION_IF FILE_EXISTS_IN_GAME ~hpclass.2da~ THEN BEGIN", TP2)
        self.assertIn("APPEND ~hpclass.2da~ ~SORCERER_MONK *~", TP2)


if __name__ == "__main__":
    unittest.main()
