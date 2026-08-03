from pathlib import Path
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


class StarterEquipmentLayoutTests(unittest.TestCase):
    def test_25stweap_schema_is_preflighted(self):
        self.assertIn("COUNT_2DA_ROWS sm_25stweap_cols sm_25stweap_rows", TP2)
        self.assertIn("READ_2DA_ENTRY sm_i 0 sm_25stweap_cols sm_25stweap_slot", TP2)
        self.assertIn("sm_25stweap_rows != 20", TP2)
        self.assertIn("FAIL @23", TP2)

    def test_expected_slot_order_matches_gemrb_fixed_map(self):
        self.assertIn(
            "ARMOR SHIELD HELM BAG RING1 RING2 CLOAK BOOTS AMULET BRACERS BELT "
            "AMMO1 AMMO2 AMMO3 MISC1 MISC2 MISC3 MISC4 MISC5 WEAPON1",
            TP2,
        )


if __name__ == "__main__":
    unittest.main()
