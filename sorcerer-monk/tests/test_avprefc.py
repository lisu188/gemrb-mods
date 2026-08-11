from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TP2 = (ROOT / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")
FALLBACK = (ROOT / "tables" / "avprefc.2da").read_text(encoding="utf-8")


class AvatarPrefixTests(unittest.TestCase):
    def test_missing_table_fallback_is_complete_at_copy_time(self):
        self.assertIn("SORCERER_MONK\t0x500", FALLBACK)

    def test_live_table_is_extended_inside_copy_patch(self):
        self.assertIn("INSERT_BYTES sm_avprefc_offset sm_avprefc_length", TP2)
        self.assertIn("WRITE_ASCIIE sm_avprefc_offset", TP2)
        self.assertNotIn("APPEND ~avprefc.2da~", TP2)


if __name__ == "__main__":
    unittest.main()
