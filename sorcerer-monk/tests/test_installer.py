from pathlib import Path
import re
import unittest


TP2 = (Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")


def payloads(directive, table):
    pattern = rf"{directive}\s+~{re.escape(table)}~\s+~([^~]*)~"
    return re.findall(pattern, TP2, flags=re.IGNORECASE)


class InstallerTests(unittest.TestCase):
    def test_backup_path_preserves_v19_upgrades(self):
        self.assertTrue(TP2.startswith("BACKUP ~sorcerer-monk-cleric/backup~"))
        self.assertNotIn("BACKUP ~sorcerer-monk/backup~", TP2)

    def test_split_class_metadata(self):
        class_rows = payloads("APPEND", "classes.2da")
        self.assertIn("SORCERER_MONK * 786432 0x20040000 -1 0 9", class_rows)
        self.assertIn("SORCERER_MONK 1 0 0 0 0 0 0", payloads("APPEND", "clsrcreq.2da"))
        self.assertIn("SORCERER_MONK *", payloads("APPEND", "hpclass.2da"))

    def test_native_ee_clastext_variants(self):
        self.assertIn("ACTION_IF sm_clastext_cols = 9", TP2)
        self.assertIn("ACTION_IF sm_clastext_cols = 10", TP2)
        self.assertIn(
            "SORCERER_MONK %sm_class_id% 16384 %sm_lower% %sm_desc% %sm_mixed% -1 0 %sm_brief%",
            TP2,
        )
        self.assertIn(
            "SORCERER_MONK %sm_class_id% 16384 %sm_lower% %sm_desc% %sm_mixed% -1 0 %sm_brief% -1",
            TP2,
        )

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
        self.assertEqual(fist_rows[0], "%sm_class_id%%sm_fist_row%")

    def test_class_id_is_never_hardcoded(self):
        # The allocated ID itself is checked end-to-end by the WeiDU smoke tests;
        # this only guards against a literal creeping back into the tables.
        self.assertNotIn("sm_candidate_id", TP2)
        self.assertIn("sm_expected_class_id > 31", TP2)
        for table in ("class.ids", "fistweap.2da"):
            for row in payloads("APPEND", table):
                self.assertIn("%sm_class_id%", row)

    def test_exact_class_token_guards_do_not_match_triple_class(self):
        self.assertNotIn("UNLESS ~SORCERER_MONK~", TP2)
        guard = r"UNLESS ~\(^\|[ %TAB%]\)SORCERER_MONK\([ %TAB%]\|$\)~"
        self.assertGreaterEqual(TP2.count(guard), 20)
        token = re.compile(r"(^|[ \t])SORCERER_MONK([ \t]|$)", re.MULTILINE)
        self.assertIsNotNone(token.search("SORCERER_MONK 1 2 3"))
        self.assertIsNotNone(token.search("21 SORCERER_MONK"))
        self.assertIsNotNone(token.search("  SORCERER_MONK\t"))
        self.assertIsNone(token.search("SORCERER_MONK_CLERIC 1 2 3"))

    def test_legacy_nonproficiency_penalty_follows_monk(self):
        self.assertIn("OUTER_SPRINT sm_no_prof ~-3~", TP2)
        self.assertNotIn("OUTER_SPRINT sm_no_prof ~-4~", TP2)

    def test_sorcerer_and_monk_features_are_combined(self):
        clskills_rows = payloads("APPEND", "clskills.2da")
        self.assertEqual(len(clskills_rows), 2)
        for row in clskills_rows:
            self.assertIn("%sm_magespell%", row)
            self.assertIn("%sm_booktype%", row)
            self.assertIn("SKILLS", row)
            self.assertIn("CLABMO01", row)
        self.assertIn("%sm_thiefscl_column%", payloads("APPEND_COL", "thiefscl.2da"))

    def test_combined_ability_prerequisites(self):
        self.assertIn("SORCERER_MONK %sm_abclasrq_row%", payloads("APPEND", "abclasrq.2da"))
        self.assertIn("SORCERER_MONK 0 0 0 0 0 0", payloads("APPEND", "abclsmod.2da"))
        self.assertIn("sm_found_sorcerer_abclasrq != 1", TP2)
        self.assertIn("sm_found_monk_abclasrq != 1", TP2)

    def test_modern_monk_skill_progression(self):
        self.assertIn("SORCERER_MONK %sm_thiefskl_row%", payloads("APPEND", "thiefskl.2da"))
        self.assertIn("OUTER_SPRINT sm_thiefskl_row ~0 10~", TP2)
        self.assertNotIn("SORCERER_MONK 10 5", payloads("APPEND", "thiefskl.2da"))

    def test_legacy_monk_skill_progression(self):
        legacy_rows = payloads("APPEND_COL", "skills.2da")
        expected = "$ $ SORCERER_MONK 10 10 -1 -1 1 1 1 -1 -1"
        self.assertIn(expected, legacy_rows)
        self.assertNotIn("$ $ SORCERER_MONK 10 10 -1 -1 -1 1 1 -1 -1", legacy_rows)
        values = expected.split()[3:]
        self.assertEqual(values, ["10", "10", "-1", "-1", "1", "1", "1", "-1", "-1"])

    def test_gameplay_restrictions(self):
        self.assertIn("SORCERER_MONK %sm_alignmnt_row%", payloads("APPEND", "alignmnt.2da"))
        self.assertIn("sm_found_sorcerer_alignmnt != 1", TP2)
        self.assertIn("sm_found_monk_alignmnt != 1", TP2)

    def test_proficiency_progression_uses_fastest_component(self):
        prof_rows = payloads("APPEND", "profs.2da")
        self.assertIn("SORCERER_MONK %sm_profs_row%", prof_rows)
        self.assertIn("sm_monk_prof_rate < sm_prof_rate", TP2)
        self.assertIn("sm_monk_prof_first > sm_prof_first", TP2)
        self.assertNotIn("SORCERER_MONK 2 4", prof_rows)

    def test_xp_cap_is_inherited_from_components(self):
        self.assertNotIn("SORCERER_MONK 8000000", TP2)
        self.assertIn("OUTER_SET sm_xpcap = (0 - 2)", TP2)
        self.assertIn("STRING_EQUAL_CASE ~SORCERER~", TP2)
        self.assertIn("STRING_EQUAL_CASE ~MONK~", TP2)
        self.assertIn("sm_xpcap_value = (0 - 1)", TP2)
        self.assertIn("SET sm_xpcap = (0 - 1)", TP2)
        self.assertIn("sm_xpcap_value < sm_xpcap", TP2)
        self.assertIn("SORCERER_MONK %sm_xpcap%", payloads("APPEND", "xpcap.2da"))
        self.assertIn("sm_found_sorcerer_xpcap != 1", TP2)
        self.assertIn("sm_found_monk_xpcap != 1", TP2)
        self.assertIn("sm_xpcap < (0 - 1)", TP2)
        self.assertIn("FAIL @14", TP2)

    def test_component_derived_rows_are_not_hardcoded(self):
        self.assertIn("SORCERER_MONK%sm_gold_row%", payloads("APPEND", "strtgold.2da"))
        self.assertIn("SORCERER_MONK%sm_avatar%", payloads("APPEND", "avprefc.2da"))

    def test_bgee_starts_unarmed(self):
        self.assertIn("SORCERER_MONK", payloads("APPEND", "stweapon.2da"))

    def test_quick_weapon_slots_use_restrictive_component(self):
        self.assertIn("SORCERER_MONK 2", payloads("APPEND", "numwslot.2da"))

    def test_monk_combat_progression_is_preserved(self):
        combat_rows = payloads("APPEND", "clswpbon.2da")
        self.assertIn("SORCERER_MONK %sm_clswpbon_row%", combat_rows)
        self.assertIn("OUTER_SPRINT sm_clswpbon_row ~1 3 2~", TP2)
        self.assertNotIn("SORCERER_MONK 1 3 2", combat_rows)

    def test_fist_progression_falls_back_to_the_stock_monk_table(self):
        # GemRB indexes FISTWEAP by the Monk component level (Actor::SetupFist),
        # so no average-level compensation is applied. The installed row is
        # copied from the game's Monk row; this is only the fallback literal.
        fallback = re.search(r"OUTER_SPRINT sm_fist_row ~([^~]*)~", TP2).group(1).split()
        self.assertEqual(len(fallback), 41)
        expected_ranges = [
            (0, 1, "MFIST1"),
            (2, 4, "MFIST2"),
            (5, 7, "MFIST3"),
            (8, 10, "MFIST4"),
            (11, 13, "MFIST5"),
            (14, 16, "MFIST6"),
            (17, 23, "MFIST7"),
            (24, 40, "MFIST8"),
        ]
        for start, end, fist in expected_ranges:
            self.assertEqual(fallback[start : end + 1], [fist] * (end - start + 1))

    def test_merged_action_bar_carries_both_components(self):
        # QSPELL1 and CAST from Sorcerer, SEARCH and STEALTH from Monk, then the
        # shared use/quick-item/innate buttons. The Monk's third quick-weapon
        # button is excluded because NUMWSLOT restricts the class to two slots.
        self.assertIn("SORCERER_MONK 3 2 22 0 8 9 11 12 13", payloads("APPEND", "qslots.2da"))

    def test_index_addressed_tables_are_preflighted(self):
        self.assertIn("COUNT_2DA_ROWS sm_qslots_cols sm_qslots_rows", TP2)
        self.assertIn("ACTION_IF sm_qslots_rows != (sm_class_id - 1)", TP2)

    def test_fist_row_is_copied_from_the_monk_class_id(self):
        # A missing Monk row is already rejected by the Sorcerer 19 / Monk 20
        # identity guard, so the copy only has to key off that row index.
        self.assertIn("STRING_EQUAL_CASE ~%sm_monk_clskills_id%~", TP2)

    def test_hla_abbreviation_collision_is_rejected(self):
        self.assertIn("SET sm_sm0_taken = 1", TP2)
        self.assertIn("ACTION_IF sm_sm0_taken = 1", TP2)
        self.assertLess(TP2.index("ACTION_IF sm_sm0_taken = 1"),
                        TP2.index("APPEND ~lusm0.2da~"))

    def test_hla_table_is_generated_rather_than_referenced(self):
        # The LUABBR row may only be added together with the table it names.
        abbrev = TP2.index("APPEND ~luabbr.2da~ ~SORCERER_MONK SM0~")
        merge = TP2.index("APPEND ~lusm0.2da~")
        self.assertLess(merge, abbrev)
        self.assertIn("LAUNCH_ACTION_MACRO sm_collect_hlas", TP2)


if __name__ == "__main__":
    unittest.main()
