from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    "psion/lib/class-detect.tpa",
    '''// Determine the active class-table generation from CLASSES.2DA itself.\n// HPCLASS.2DA can exist alongside the released combined CLASSES schema and is\n// therefore not a valid layout discriminator.\nCOPY_EXISTING ~classes.2da~ ~override~\n  COUNT_2DA_COLS ps_classes_cols\nBUT_ONLY\nACTION_IF ps_classes_cols = 7 THEN BEGIN\n  OUTER_SET ps_split = 1\nEND ELSE BEGIN\n  ACTION_IF ps_classes_cols = 19 THEN BEGIN\n    OUTER_SET ps_split = 0\n  END ELSE BEGIN\n    FAIL ~Unsupported CLASSES.2DA layout for the Psion mod.~\n  END\nEND\n\nACTION_IF ps_split = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    COUNT_2DA_COLS ps_text_cols\n    PATCH_IF (ps_text_cols = 6) OR (ps_text_cols = 9) OR (ps_text_cols = 10) BEGIN\n      READ_2DA_ENTRIES_NOW ~ps_class_table~ ps_text_cols\n''',
    '''// Determine the active class-table generation from the real CLASSES.2DA\n// header. COUNT_2DA_COLS is unsafe here because GemRB tables can end with\n// explanatory comment lines containing more tokens than the actual header.\n// HPCLASS.2DA can also coexist with the combined schema.\nCOPY_EXISTING ~classes.2da~ ~override~\n  SET ps_detect_classes_cols = 7\n  SET ps_detect_split = 1\n  PATCH_IF (INDEX_BUFFER (~SAVE~) < 0) OR (INDEX_BUFFER (~USABILITY~) < 0) BEGIN\n    SET ps_detect_classes_cols = 0\n  END ELSE PATCH_IF (INDEX_BUFFER (~NAME_REF~) >= 0) AND (INDEX_BUFFER (~CAP_REF~) >= 0) BEGIN\n    SET ps_detect_classes_cols = 19\n    SET ps_detect_split = 0\n  END\n  INNER_ACTION BEGIN\n    OUTER_SET ps_classes_cols = %ps_detect_classes_cols%\n    OUTER_SET ps_split = %ps_detect_split%\n  END\nBUT_ONLY\nACTION_IF (ps_classes_cols != 7) AND (ps_classes_cols != 19) THEN BEGIN\n  FAIL ~Unsupported CLASSES.2DA layout for the Psion mod.~\nEND\n\nACTION_IF ps_split = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    SET ps_detect_text_cols = 6\n    PATCH_IF INDEX_BUFFER (~CLASSID~) < 0 BEGIN\n      SET ps_detect_text_cols = 0\n    END ELSE BEGIN\n      PATCH_IF INDEX_BUFFER (~BIOGRAPHY~) >= 0 BEGIN\n        SET ps_detect_text_cols = 9\n      END\n      PATCH_IF INDEX_BUFFER (~FALLEN_NOTICE~) >= 0 BEGIN\n        SET ps_detect_text_cols = 10\n      END\n    END\n    INNER_ACTION BEGIN\n      OUTER_SET ps_text_cols = %ps_detect_text_cols%\n    END\n    PATCH_IF (ps_detect_text_cols = 6) OR (ps_detect_text_cols = 9) OR (ps_detect_text_cols = 10) BEGIN\n      READ_2DA_ENTRIES_NOW ~ps_class_table~ ps_detect_text_cols\n''',
)

replace(
    "cipher/lib/class.tpa",
    '''// Detect split vs combined tables from CLASSES.2DA itself. HPCLASS can coexist\n// with the released nineteen-column combined schema and is not a safe signal.\nCOPY_EXISTING ~classes.2da~ ~override~\n  COUNT_2DA_COLS ci_classes_cols\nBUT_ONLY\nACTION_IF ci_classes_cols = 7 THEN BEGIN\n  OUTER_SET ci_split = 1\nEND ELSE BEGIN\n  ACTION_IF ci_classes_cols = 19 THEN BEGIN\n    OUTER_SET ci_split = 0\n  END ELSE BEGIN\n    FAIL ~Cipher does not support this CLASSES.2DA layout.~\n  END\nEND\n\nACTION_IF ci_split = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    COUNT_2DA_COLS ci_text_cols\n    PATCH_IF (ci_text_cols = 6) OR (ci_text_cols = 9) OR (ci_text_cols = 10) BEGIN\n      READ_2DA_ENTRIES_NOW ~ci_active_classes~ ci_text_cols\n''',
    '''// Detect split vs combined tables from the actual CLASSES.2DA header.\n// COUNT_2DA_COLS is unsafe because trailing explanatory comments in GemRB's\n// real tables can contain more tokens than the header; HPCLASS presence is also\n// not a schema discriminator.\nCOPY_EXISTING ~classes.2da~ ~override~\n  SET ci_detect_classes_cols = 7\n  SET ci_detect_split = 1\n  PATCH_IF (INDEX_BUFFER (~SAVE~) < 0) OR (INDEX_BUFFER (~USABILITY~) < 0) BEGIN\n    SET ci_detect_classes_cols = 0\n  END ELSE PATCH_IF (INDEX_BUFFER (~NAME_REF~) >= 0) AND (INDEX_BUFFER (~CAP_REF~) >= 0) BEGIN\n    SET ci_detect_classes_cols = 19\n    SET ci_detect_split = 0\n  END\n  INNER_ACTION BEGIN\n    OUTER_SET ci_classes_cols = %ci_detect_classes_cols%\n    OUTER_SET ci_split = %ci_detect_split%\n  END\nBUT_ONLY\nACTION_IF (ci_classes_cols != 7) AND (ci_classes_cols != 19) THEN BEGIN\n  FAIL ~Cipher does not support this CLASSES.2DA layout.~\nEND\n\nACTION_IF ci_split = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    SET ci_detect_text_cols = 6\n    PATCH_IF INDEX_BUFFER (~CLASSID~) < 0 BEGIN\n      SET ci_detect_text_cols = 0\n    END ELSE BEGIN\n      PATCH_IF INDEX_BUFFER (~BIOGRAPHY~) >= 0 BEGIN\n        SET ci_detect_text_cols = 9\n      END\n      PATCH_IF INDEX_BUFFER (~FALLEN_NOTICE~) >= 0 BEGIN\n        SET ci_detect_text_cols = 10\n      END\n    END\n    INNER_ACTION BEGIN\n      OUTER_SET ci_text_cols = %ci_detect_text_cols%\n    END\n    PATCH_IF (ci_detect_text_cols = 6) OR (ci_detect_text_cols = 9) OR (ci_detect_text_cols = 10) BEGIN\n      READ_2DA_ENTRIES_NOW ~ci_active_classes~ ci_detect_text_cols\n''',
)

replace(
    "sorcerer-monk/setup-sorcerer-monk.tp2",
    '''// Determine the GemRB class-table generation from CLASSES.2DA itself. Enhanced\n// Edition games can provide a native HPCLASS.2DA even when the active GemRB\n// data still uses the released combined CLASSES.2DA schema, so HPCLASS presence\n// is not a safe layout discriminator.\nCOPY_EXISTING ~classes.2da~ ~override~\n  COUNT_2DA_COLS sm_classes_cols\nBUT_ONLY\n\nACTION_IF sm_classes_cols = 7 THEN BEGIN\n  OUTER_SET sm_split_class_tables = 1\nEND ELSE BEGIN\n  ACTION_IF sm_classes_cols = 19 THEN BEGIN\n    OUTER_SET sm_split_class_tables = 0\n  END ELSE BEGIN\n    FAIL @15\n  END\nEND\n\n// Released GemRB versions keep class text, IDs, hit points and race rules in\n// one combined CLASSES.2DA row. Development versions split these fields into\n// CLASTEXT.2DA, HPCLASS.2DA and CLSRCREQ.2DA.\nACTION_IF sm_split_class_tables = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    COUNT_2DA_COLS sm_clastext_cols\n    READ_2DA_ENTRIES_NOW ~sm_clastext~ sm_clastext_cols\n''',
    '''// Determine the GemRB class-table generation from the real CLASSES.2DA\n// header. COUNT_2DA_COLS is unsafe here because GemRB tables can end with long\n// explanatory comment lines. HPCLASS presence is likewise not a discriminator.\nCOPY_EXISTING ~classes.2da~ ~override~\n  SET sm_detect_classes_cols = 7\n  SET sm_detect_split = 1\n  PATCH_IF (INDEX_BUFFER (~SAVE~) < 0) OR (INDEX_BUFFER (~USABILITY~) < 0) BEGIN\n    SET sm_detect_classes_cols = 0\n  END ELSE PATCH_IF (INDEX_BUFFER (~NAME_REF~) >= 0) AND (INDEX_BUFFER (~CAP_REF~) >= 0) BEGIN\n    SET sm_detect_classes_cols = 19\n    SET sm_detect_split = 0\n  END\n  INNER_ACTION BEGIN\n    OUTER_SET sm_classes_cols = %sm_detect_classes_cols%\n    OUTER_SET sm_split_class_tables = %sm_detect_split%\n  END\nBUT_ONLY\n\nACTION_IF (sm_classes_cols != 7) AND (sm_classes_cols != 19) THEN BEGIN\n  FAIL @15\nEND\n\n// Released GemRB versions keep class text, IDs, hit points and race rules in\n// one combined CLASSES.2DA row. Development versions split these fields into\n// CLASTEXT.2DA, HPCLASS.2DA and CLSRCREQ.2DA. Determine CLASTEXT width from\n// header markers for the same comment-safety reason.\nACTION_IF sm_split_class_tables = 1 THEN BEGIN\n  COPY_EXISTING ~clastext.2da~ ~override~\n    SET sm_detect_clastext_cols = 6\n    PATCH_IF INDEX_BUFFER (~CLASSID~) < 0 BEGIN\n      SET sm_detect_clastext_cols = 0\n    END ELSE BEGIN\n      PATCH_IF INDEX_BUFFER (~BIOGRAPHY~) >= 0 BEGIN\n        SET sm_detect_clastext_cols = 9\n      END\n      PATCH_IF INDEX_BUFFER (~FALLEN_NOTICE~) >= 0 BEGIN\n        SET sm_detect_clastext_cols = 10\n      END\n    END\n    INNER_ACTION BEGIN\n      OUTER_SET sm_clastext_cols = %sm_detect_clastext_cols%\n    END\n    PATCH_IF (sm_detect_clastext_cols = 6) OR (sm_detect_clastext_cols = 9) OR (sm_detect_clastext_cols = 10) BEGIN\n      READ_2DA_ENTRIES_NOW ~sm_clastext~ sm_detect_clastext_cols\n''',
)

# Close the new PATCH_IF wrapper around the Sorcerer/Monk CLASTEXT scan before BUT_ONLY.
replace(
    "sorcerer-monk/setup-sorcerer-monk.tp2",
    '''        END\n      END\n    END\n  BUT_ONLY\nEND ELSE BEGIN\n  COPY_EXISTING ~classes.2da~ ~override~\n''',
    '''        END\n      END\n    END\n    END\n  BUT_ONLY\n  ACTION_IF (sm_clastext_cols != 6) AND (sm_clastext_cols != 9) AND (sm_clastext_cols != 10) THEN BEGIN\n    FAIL @15\n  END\nEND ELSE BEGIN\n  COPY_EXISTING ~classes.2da~ ~override~\n''',
)

replace(
    "psion/tests/validate_core.py",
    '''        "COUNT_2DA_COLS ps_classes_cols",\n        "ps_classes_cols = 7",\n        "ps_classes_cols = 19",\n        "ps_text_cols = 9",\n''',
    '''        "INDEX_BUFFER (~NAME_REF~)",\n        "INDEX_BUFFER (~CAP_REF~)",\n        "ps_detect_classes_cols = 7",\n        "ps_detect_classes_cols = 19",\n        "INDEX_BUFFER (~BIOGRAPHY~)",\n        "INDEX_BUFFER (~FALLEN_NOTICE~)",\n        "ps_text_cols = 9",\n''',
)
replace(
    "psion/tests/validate_core.py",
    '''    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in detector\n''',
    '''    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in detector\n    assert "COUNT_2DA_COLS ps_classes_cols" not in detector\n    assert "COUNT_2DA_COLS ps_text_cols" not in detector\n''',
)

replace(
    "common/tests/validate_class_registration.py",
    '''    assert "COUNT_2DA_COLS ps_classes_cols" in ps_detect\n''',
    '''    assert "INDEX_BUFFER (~NAME_REF~)" in ps_detect\n    assert "INDEX_BUFFER (~BIOGRAPHY~)" in ps_detect\n    assert "COUNT_2DA_COLS ps_classes_cols" not in ps_detect\n    assert "COUNT_2DA_COLS ps_text_cols" not in ps_detect\n''',
)
replace(
    "common/tests/validate_class_registration.py",
    '''    assert "COUNT_2DA_COLS ci_classes_cols" in registration_prefix\n''',
    '''    assert "INDEX_BUFFER (~NAME_REF~)" in registration_prefix\n    assert "INDEX_BUFFER (~BIOGRAPHY~)" in registration_prefix\n    assert "COUNT_2DA_COLS ci_classes_cols" not in registration_prefix\n    assert "COUNT_2DA_COLS ci_text_cols" not in registration_prefix\n''',
)
replace(
    "common/tests/validate_class_registration.py",
    '''    assert "COUNT_2DA_COLS sm_classes_cols" in sm\n''',
    '''    assert "INDEX_BUFFER (~NAME_REF~)" in sm\n    assert "INDEX_BUFFER (~BIOGRAPHY~)" in sm\n    assert "COUNT_2DA_COLS sm_classes_cols" not in sm\n    assert "COUNT_2DA_COLS sm_clastext_cols" not in sm\n''',
)

replace(
    "sorcerer-monk/tests/test_installer.py",
    '''    def test_native_ee_clastext_variants(self):\n        self.assertIn("ACTION_IF sm_clastext_cols = 9", TP2)\n''',
    '''    def test_native_ee_clastext_variants(self):\n        self.assertIn("ACTION_IF sm_clastext_cols = 9", TP2)\n        self.assertIn("INDEX_BUFFER (~BIOGRAPHY~)", TP2)\n        self.assertIn("INDEX_BUFFER (~FALLEN_NOTICE~)", TP2)\n        self.assertNotIn("COUNT_2DA_COLS sm_classes_cols", TP2)\n        self.assertNotIn("COUNT_2DA_COLS sm_clastext_cols", TP2)\n''',
)

replace(
    "common/tests/validate_class_registration_weidu.py",
    '''        if scenario == "combined_hp":\n            add_combined_hp(override / "hpclass.2da")\n        else:\n            write_split_classes(override / "classes.2da")\n            write_native9(override / "clastext.2da")\n''',
    '''        if scenario == "combined_hp":\n            add_combined_hp(override / "hpclass.2da")\n        elif scenario == "native9":\n            write_split_classes(override / "classes.2da")\n            write_native9(override / "clastext.2da")\n        elif scenario != "commented_split":\n            raise AssertionError(scenario)\n''',
)
replace(
    "common/tests/validate_class_registration_weidu.py",
    '''        if scenario == "combined_hp":\n            classes = read_rows(override / "classes.2da")\n            for name in names:\n                row = next(row for row in classes if row[0] == name)\n                assert int(row[6], 0) == ids[name], (mod, scenario, row)\n            hp_names = {row[0] for row in read_rows(override / "hpclass.2da")}\n            assert not (set(names) & hp_names), (mod, scenario, hp_names)\n        else:\n            clastext = read_rows(override / "clastext.2da")\n            for name in names:\n                row = next(row for row in clastext if row[0] == name)\n                assert len(row) == 9, (mod, scenario, row)\n                assert int(row[1], 0) == ids[name], (mod, scenario, row)\n''',
    '''        if scenario == "combined_hp":\n            classes = read_rows(override / "classes.2da")\n            for name in names:\n                row = next(row for row in classes if row[0] == name)\n                assert int(row[6], 0) == ids[name], (mod, scenario, row)\n            hp_names = {row[0] for row in read_rows(override / "hpclass.2da")}\n            assert not (set(names) & hp_names), (mod, scenario, hp_names)\n        else:\n            clastext = read_rows(override / "clastext.2da")\n            expected_len = 9 if scenario == "native9" else 6\n            for name in names:\n                row = next(row for row in clastext if row[0] == name)\n                assert len(row) == expected_len, (mod, scenario, row)\n                assert int(row[1], 0) == ids[name], (mod, scenario, row)\n''',
)
replace(
    "common/tests/validate_class_registration_weidu.py",
    '''        for scenario in ("combined_hp", "native9"):\n            install(weidu, gemrb, mod, scenario)\n    print("Psion and Cipher registration passed combined+HPCLASS and native 9-column CLASTEXT smoke tests.")\n''',
    '''        for scenario in ("commented_split", "combined_hp", "native9"):\n            install(weidu, gemrb, mod, scenario)\n    print("Psion and Cipher registration passed commented split, combined+HPCLASS and native 9-column CLASTEXT smoke tests.")\n''',
)
