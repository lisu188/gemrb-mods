from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")


psion_detect = r'''// GemRB uses class IDs as direct indices in several class tables and tracks
// class categories in a 32-bit mask. Allocate Psion IDs from the exact
// CLSKILLS.2DA row positions that the six discipline rows will occupy, rather
// than from the largest numeric ID found elsewhere.
OUTER_SET ps_split = 0
OUTER_SET ps_text_cols = 0
OUTER_SET ps_classes_cols = 0
OUTER_SET ps_clskills_cols = 0
OUTER_SET ps_clskills_rows = 0
OUTER_SET ps_existing_count = 0
OUTER_SET ps_registration_conflict = 0
OUTER_SET ps_seer_row = (0 - 1)
OUTER_SET ps_shaper_row = (0 - 1)
OUTER_SET ps_kineticist_row = (0 - 1)
OUTER_SET ps_egoist_row = (0 - 1)
OUTER_SET ps_nomad_row = (0 - 1)
OUTER_SET ps_telepath_row = (0 - 1)

COPY_EXISTING ~clskills.2da~ ~override~
  COUNT_2DA_COLS ps_clskills_cols
  READ_2DA_ENTRIES_NOW ~ps_clskills~ ps_clskills_cols
  SET ps_clskills_rows = ps_clskills
  FOR (ps_i = 0; ps_i < ps_clskills; ++ps_i) BEGIN
    READ_2DA_ENTRY_FORMER ~ps_clskills~ ps_i 0 ps_class_name
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SEER~ BEGIN SET ps_seer_row = ps_i SET ps_existing_count += 1 END
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SHAPER~ BEGIN SET ps_shaper_row = ps_i SET ps_existing_count += 1 END
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_KINETICIST~ BEGIN SET ps_kineticist_row = ps_i SET ps_existing_count += 1 END
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_EGOIST~ BEGIN SET ps_egoist_row = ps_i SET ps_existing_count += 1 END
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_NOMAD~ BEGIN SET ps_nomad_row = ps_i SET ps_existing_count += 1 END
    PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_TELEPATH~ BEGIN SET ps_telepath_row = ps_i SET ps_existing_count += 1 END
  END
BUT_ONLY

ACTION_IF (ps_clskills_cols != 16) AND (ps_clskills_cols != 17) THEN BEGIN FAIL @5 END
ACTION_IF (ps_existing_count != 0) AND (ps_existing_count != 6) THEN BEGIN
  FAIL ~The Psion mod found a partial or duplicate Psion CLSKILLS registration.~
END

ACTION_IF ps_existing_count = 6 THEN BEGIN
  OUTER_SET ps_seer_id = ps_seer_row
  OUTER_SET ps_shaper_id = ps_shaper_row
  OUTER_SET ps_kineticist_id = ps_kineticist_row
  OUTER_SET ps_egoist_id = ps_egoist_row
  OUTER_SET ps_nomad_id = ps_nomad_row
  OUTER_SET ps_telepath_id = ps_telepath_row
  ACTION_IF (ps_shaper_id != ps_seer_id + 1)
      OR (ps_kineticist_id != ps_seer_id + 2)
      OR (ps_egoist_id != ps_seer_id + 3)
      OR (ps_nomad_id != ps_seer_id + 4)
      OR (ps_telepath_id != ps_seer_id + 5) THEN BEGIN
    FAIL ~The Psion discipline CLSKILLS rows must be consecutive.~
  END
END ELSE BEGIN
  OUTER_SET ps_seer_id = ps_clskills_rows
  OUTER_SET ps_shaper_id = ps_clskills_rows + 1
  OUTER_SET ps_kineticist_id = ps_clskills_rows + 2
  OUTER_SET ps_egoist_id = ps_clskills_rows + 3
  OUTER_SET ps_nomad_id = ps_clskills_rows + 4
  OUTER_SET ps_telepath_id = ps_clskills_rows + 5
END

ACTION_IF (ps_seer_id < 1) OR (ps_telepath_id > 31) THEN BEGIN
  FAIL ~The Psion mod requires six consecutive GemRB class slots below class ID 32.~
END

// Determine the active class-table generation from CLASSES.2DA itself.
// HPCLASS.2DA can exist alongside the released combined CLASSES schema and is
// therefore not a valid layout discriminator.
COPY_EXISTING ~classes.2da~ ~override~
  COUNT_2DA_COLS ps_classes_cols
BUT_ONLY
ACTION_IF ps_classes_cols = 7 THEN BEGIN
  OUTER_SET ps_split = 1
END ELSE BEGIN
  ACTION_IF ps_classes_cols = 19 THEN BEGIN
    OUTER_SET ps_split = 0
  END ELSE BEGIN
    FAIL ~Unsupported CLASSES.2DA layout for the Psion mod.~
  END
END

ACTION_IF ps_split = 1 THEN BEGIN
  COPY_EXISTING ~clastext.2da~ ~override~
    COUNT_2DA_COLS ps_text_cols
    PATCH_IF (ps_text_cols = 6) OR (ps_text_cols = 9) OR (ps_text_cols = 10) BEGIN
      READ_2DA_ENTRIES_NOW ~ps_class_table~ ps_text_cols
      FOR (ps_i = 0; ps_i < ps_class_table; ++ps_i) BEGIN
        READ_2DA_ENTRY_FORMER ~ps_class_table~ ps_i 0 ps_class_name
        READ_2DA_ENTRY_FORMER ~ps_class_table~ ps_i 1 ps_id
        PATCH_IF IS_AN_INT ~%ps_id%~ BEGIN
          SET ps_expected_here = (0 - 1)
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SEER~ BEGIN SET ps_expected_here = ps_seer_id END
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SHAPER~ BEGIN SET ps_expected_here = ps_shaper_id END
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_KINETICIST~ BEGIN SET ps_expected_here = ps_kineticist_id END
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_EGOIST~ BEGIN SET ps_expected_here = ps_egoist_id END
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_NOMAD~ BEGIN SET ps_expected_here = ps_nomad_id END
          PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_TELEPATH~ BEGIN SET ps_expected_here = ps_telepath_id END
          PATCH_IF (ps_expected_here >= 0) AND (ps_id != ps_expected_here) BEGIN SET ps_registration_conflict = 1 END
          PATCH_IF (ps_id >= ps_seer_id) AND (ps_id <= ps_telepath_id) AND (ps_expected_here != ps_id) BEGIN SET ps_registration_conflict = 1 END
        END
      END
    END
  BUT_ONLY
  ACTION_IF (ps_text_cols != 6) AND (ps_text_cols != 9) AND (ps_text_cols != 10) THEN BEGIN FAIL @4 END
END ELSE BEGIN
  COPY_EXISTING ~classes.2da~ ~override~
    READ_2DA_ENTRIES_NOW ~ps_class_table~ ps_classes_cols
    FOR (ps_i = 0; ps_i < ps_class_table; ++ps_i) BEGIN
      READ_2DA_ENTRY_FORMER ~ps_class_table~ ps_i 0 ps_class_name
      READ_2DA_ENTRY_FORMER ~ps_class_table~ ps_i 6 ps_id
      PATCH_IF IS_AN_INT ~%ps_id%~ BEGIN
        SET ps_expected_here = (0 - 1)
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SEER~ BEGIN SET ps_expected_here = ps_seer_id END
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_SHAPER~ BEGIN SET ps_expected_here = ps_shaper_id END
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_KINETICIST~ BEGIN SET ps_expected_here = ps_kineticist_id END
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_EGOIST~ BEGIN SET ps_expected_here = ps_egoist_id END
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_NOMAD~ BEGIN SET ps_expected_here = ps_nomad_id END
        PATCH_IF ~%ps_class_name%~ STRING_EQUAL_CASE ~PSION_TELEPATH~ BEGIN SET ps_expected_here = ps_telepath_id END
        PATCH_IF (ps_expected_here >= 0) AND (ps_id != ps_expected_here) BEGIN SET ps_registration_conflict = 1 END
        PATCH_IF (ps_id >= ps_seer_id) AND (ps_id <= ps_telepath_id) AND (ps_expected_here != ps_id) BEGIN SET ps_registration_conflict = 1 END
      END
    END
  BUT_ONLY
END
ACTION_IF ps_registration_conflict = 1 THEN BEGIN
  FAIL ~The Psion mod found a class-table identity collision in its allocated class slots.~
END

// CLASS.IDS may drift independently of the class tables after manual or partial
// custom-class changes. Validate both symbol-to-ID and ID-to-symbol directions.
DEFINE_ACTION_FUNCTION psion_validate_class_ids
INT_VAR ps_expected = 0
STR_VAR ps_symbol = ~~
BEGIN
  ACTION_IF IDS_OF_SYMBOL (~class~ ~%ps_symbol%~) >= 0 THEN BEGIN
    OUTER_SET ps_existing_ids_value = IDS_OF_SYMBOL (~class~ ~%ps_symbol%~)
    ACTION_IF ps_existing_ids_value != ps_expected THEN BEGIN
      FAIL ~The Psion mod found a conflicting CLASS.IDS symbol registration.~
    END
  END
  OUTER_SPRINT ps_existing_ids_symbol ~~
  OUTER_PATCH ~~ BEGIN
    LOOKUP_IDS_SYMBOL_OF_INT ps_existing_ids_symbol ~class~ ps_expected
  END
  ACTION_IF !(IS_AN_INT ~%ps_existing_ids_symbol%~)
      AND !(~%ps_existing_ids_symbol%~ STRING_EQUAL_CASE ~%ps_symbol%~) THEN BEGIN
    FAIL ~The Psion mod found a conflicting numeric CLASS.IDS registration.~
  END
END

LAF psion_validate_class_ids INT_VAR ps_expected = ps_seer_id STR_VAR ps_symbol = ~PSION_SEER~ END
LAF psion_validate_class_ids INT_VAR ps_expected = ps_shaper_id STR_VAR ps_symbol = ~PSION_SHAPER~ END
LAF psion_validate_class_ids INT_VAR ps_expected = ps_kineticist_id STR_VAR ps_symbol = ~PSION_KINETICIST~ END
LAF psion_validate_class_ids INT_VAR ps_expected = ps_egoist_id STR_VAR ps_symbol = ~PSION_EGOIST~ END
LAF psion_validate_class_ids INT_VAR ps_expected = ps_nomad_id STR_VAR ps_symbol = ~PSION_NOMAD~ END
LAF psion_validate_class_ids INT_VAR ps_expected = ps_telepath_id STR_VAR ps_symbol = ~PSION_TELEPATH~ END
'''
write("psion/lib/class-detect.tpa", psion_detect)


def psion_split_row(name, ident, lower, desc, title):
    return f'''  OUTER_SPRINT ps_row ~{name} %{ident}% * %{lower}% %{desc}% %{title}%~\n  ACTION_IF ps_text_cols = 9 THEN BEGIN OUTER_SPRINT ps_row ~%ps_row% -1 0 %{title}%~ END\n  ACTION_IF ps_text_cols = 10 THEN BEGIN OUTER_SPRINT ps_row ~%ps_row% -1 0 %{title}% -1~ END\n  APPEND ~clastext.2da~ ~%ps_row%~ UNLESS ~{name}~\n  APPEND ~classes.2da~ ~{name} SAVEPSI 0 0 -1 0 10~ UNLESS ~{name}~\n  APPEND ~clsrcreq.2da~ ~{name} 1 1 1 1 1 1 1~ UNLESS ~{name}~\n  APPEND ~hpclass.2da~ ~{name} HPWIZ~ UNLESS ~{name}~\n'''

rows = [
    ("PSION_SEER", "ps_seer_id", "ps_seer_lower", "ps_seer_desc", "ps_seer_title"),
    ("PSION_SHAPER", "ps_shaper_id", "ps_shaper_lower", "ps_shaper_desc", "ps_shaper_title"),
    ("PSION_KINETICIST", "ps_kineticist_id", "ps_kineticist_lower", "ps_kineticist_desc", "ps_kineticist_title"),
    ("PSION_EGOIST", "ps_egoist_id", "ps_egoist_lower", "ps_egoist_desc", "ps_egoist_title"),
    ("PSION_NOMAD", "ps_nomad_id", "ps_nomad_lower", "ps_nomad_desc", "ps_nomad_title"),
    ("PSION_TELEPATH", "ps_telepath_id", "ps_telepath_lower", "ps_telepath_desc", "ps_telepath_title"),
]
layout = "ACTION_IF ps_split=1 THEN BEGIN\n"
layout += "  ACTION_IF (ps_text_cols != 6) AND (ps_text_cols != 9) AND (ps_text_cols != 10) THEN BEGIN FAIL @4 END\n"
for row in rows:
    layout += psion_split_row(*row)
layout += "END ELSE BEGIN\n"
for name, ident, lower, desc, title in rows:
    layout += f"  APPEND ~classes.2da~ ~{name} %{lower}% %{desc}% %{title}% SAVEPSI 0 %{ident}% HPWIZ 0 -1 1 1 1 1 1 1 1 0 10~ UNLESS ~{name}~\n"
layout += "END\n"
write("psion/lib/class-layout.tpa", layout)

replace(
    "psion/lib/class-common.tpa",
    "// Build the Psion proficiency column from WEAPPROF row names instead of a\n",
    "// QSLOTS.2DA is indexed by class ID - 1 rather than by row name. The first\n// Psion row must therefore land exactly at ps_seer_id - 1 and the six rows then\n// remain aligned with the six consecutive discipline IDs.\nOUTER_SET ps_qslots_cols = 0\nOUTER_SET ps_qslots_rows = 0\nCOPY_EXISTING ~qslots.2da~ ~override~\n  COUNT_2DA_COLS ps_qslots_cols\n  COUNT_2DA_ROWS ps_qslots_cols ps_qslots_rows\nBUT_ONLY\nACTION_IF ps_qslots_rows != (ps_seer_id - 1) THEN BEGIN\n  FAIL ~The Psion mod cannot align QSLOTS.2DA with its allocated class IDs.~\nEND\n\n// Build the Psion proficiency column from WEAPPROF row names instead of a\n",
)

cipher_path = ROOT / "cipher/lib/class.tpa"
cipher = cipher_path.read_text(encoding="utf-8")
start = cipher.index("OUTER_SET ci_max_id")
end = cipher.index("COPY_EXISTING ~savewiz.2da~")
cipher_prelude = r'''// GemRB class IDs are table indices and participate in a 32-bit class mask.
// Allocate Cipher from the row it will occupy in CLSKILLS rather than from the
// largest arbitrary numeric class ID.
OUTER_SET ci_split = 0
OUTER_SET ci_text_cols = 0
OUTER_SET ci_classes_cols = 0
OUTER_SET ci_skill_pre_cols = 0
OUTER_SET ci_skill_pre_rows = 0
OUTER_SET ci_existing_clskills = 0
OUTER_SET ci_existing_clskills_id = (0 - 1)
OUTER_SET ci_registration_conflict = 0

COPY_EXISTING ~clskills.2da~ ~override~
  COUNT_2DA_COLS ci_skill_pre_cols
  READ_2DA_ENTRIES_NOW ~ci_skill_pre~ ci_skill_pre_cols
  SET ci_skill_pre_rows = ci_skill_pre
  FOR (ci_i = 0; ci_i < ci_skill_pre; ++ci_i) BEGIN
    READ_2DA_ENTRY_FORMER ~ci_skill_pre~ ci_i 0 ci_name
    PATCH_IF ~%ci_name%~ STRING_EQUAL_CASE ~CIPHER~ BEGIN
      SET ci_existing_clskills += 1
      SET ci_existing_clskills_id = ci_i
    END
  END
BUT_ONLY
ACTION_IF (ci_skill_pre_cols != 16) AND (ci_skill_pre_cols != 17) THEN BEGIN FAIL @5 END
ACTION_IF ci_existing_clskills > 1 THEN BEGIN
  FAIL ~Cipher found duplicate CIPHER rows in CLSKILLS.2DA.~
END
ACTION_IF ci_existing_clskills = 1 THEN BEGIN
  OUTER_SET ci_class_id = ci_existing_clskills_id
END ELSE BEGIN
  OUTER_SET ci_class_id = ci_skill_pre_rows
END
ACTION_IF (ci_class_id < 1) OR (ci_class_id > 31) THEN BEGIN
  FAIL ~Cipher requires an available GemRB class slot below class ID 32.~
END

// Detect split vs combined tables from CLASSES.2DA itself. HPCLASS can coexist
// with the released nineteen-column combined schema and is not a safe signal.
COPY_EXISTING ~classes.2da~ ~override~
  COUNT_2DA_COLS ci_classes_cols
BUT_ONLY
ACTION_IF ci_classes_cols = 7 THEN BEGIN
  OUTER_SET ci_split = 1
END ELSE BEGIN
  ACTION_IF ci_classes_cols = 19 THEN BEGIN
    OUTER_SET ci_split = 0
  END ELSE BEGIN
    FAIL ~Cipher does not support this CLASSES.2DA layout.~
  END
END

ACTION_IF ci_split = 1 THEN BEGIN
  COPY_EXISTING ~clastext.2da~ ~override~
    COUNT_2DA_COLS ci_text_cols
    PATCH_IF (ci_text_cols = 6) OR (ci_text_cols = 9) OR (ci_text_cols = 10) BEGIN
      READ_2DA_ENTRIES_NOW ~ci_active_classes~ ci_text_cols
      FOR (ci_i = 0; ci_i < ci_active_classes; ++ci_i) BEGIN
        READ_2DA_ENTRY_FORMER ~ci_active_classes~ ci_i 0 ci_name
        READ_2DA_ENTRY_FORMER ~ci_active_classes~ ci_i 1 ci_id
        PATCH_IF IS_AN_INT ~%ci_id%~ BEGIN
          PATCH_IF (~%ci_name%~ STRING_EQUAL_CASE ~CIPHER~) AND (ci_id != ci_class_id) BEGIN SET ci_registration_conflict = 1 END
          PATCH_IF (ci_id = ci_class_id) AND !(~%ci_name%~ STRING_EQUAL_CASE ~CIPHER~) BEGIN SET ci_registration_conflict = 1 END
        END
      END
    END
  BUT_ONLY
  ACTION_IF (ci_text_cols != 6) AND (ci_text_cols != 9) AND (ci_text_cols != 10) THEN BEGIN FAIL @4 END
END ELSE BEGIN
  COPY_EXISTING ~classes.2da~ ~override~
    READ_2DA_ENTRIES_NOW ~ci_active_classes~ ci_classes_cols
    FOR (ci_i = 0; ci_i < ci_active_classes; ++ci_i) BEGIN
      READ_2DA_ENTRY_FORMER ~ci_active_classes~ ci_i 0 ci_name
      READ_2DA_ENTRY_FORMER ~ci_active_classes~ ci_i 6 ci_id
      PATCH_IF IS_AN_INT ~%ci_id%~ BEGIN
        PATCH_IF (~%ci_name%~ STRING_EQUAL_CASE ~CIPHER~) AND (ci_id != ci_class_id) BEGIN SET ci_registration_conflict = 1 END
        PATCH_IF (ci_id = ci_class_id) AND !(~%ci_name%~ STRING_EQUAL_CASE ~CIPHER~) BEGIN SET ci_registration_conflict = 1 END
      END
    END
  BUT_ONLY
END
ACTION_IF ci_registration_conflict = 1 THEN BEGIN
  FAIL ~Cipher found a class-table identity collision in its allocated class slot.~
END

OUTER_SET ci_ids_class_id = IDS_OF_SYMBOL (~class~ ~CIPHER~)
ACTION_IF (ci_ids_class_id >= 0) AND (ci_ids_class_id != ci_class_id) THEN BEGIN
  FAIL ~Cipher found a conflicting CIPHER symbol in CLASS.IDS.~
END
OUTER_SPRINT ci_ids_class_symbol ~~
OUTER_PATCH ~~ BEGIN
  LOOKUP_IDS_SYMBOL_OF_INT ci_ids_class_symbol ~class~ ci_class_id
END
ACTION_IF !(IS_AN_INT ~%ci_ids_class_symbol%~)
    AND !(~%ci_ids_class_symbol%~ STRING_EQUAL_CASE ~CIPHER~) THEN BEGIN
  FAIL ~Cipher found a conflicting numeric class slot in CLASS.IDS.~
END

// GemRB indexes QSLOTS by class ID - 1. Refuse an install that would append the
// Cipher action bar at a different class's positional slot.
OUTER_SET ci_qslots_cols = 0
OUTER_SET ci_qslots_rows = 0
COPY_EXISTING ~qslots.2da~ ~override~
  COUNT_2DA_COLS ci_qslots_cols
  COUNT_2DA_ROWS ci_qslots_cols ci_qslots_rows
BUT_ONLY
ACTION_IF ci_qslots_rows != (ci_class_id - 1) THEN BEGIN
  FAIL ~Cipher cannot align QSLOTS.2DA with its allocated class ID.~
END

'''
cipher = cipher[:start] + cipher_prelude + cipher[end:]
old_layout = '''ACTION_IF ci_split = 1 THEN BEGIN
  ACTION_IF (ci_text_cols != 6) AND (ci_text_cols != 10) THEN BEGIN FAIL @4 END
  OUTER_SPRINT ci_row ~CIPHER %ci_class_id% * %ci_lower% %ci_desc% %ci_title%~
  ACTION_IF ci_text_cols = 10 THEN BEGIN
    OUTER_SPRINT ci_row ~%ci_row% -1 0 %ci_title% -1~
  END
  APPEND ~clastext.2da~ ~%ci_row%~ UNLESS ~CIPHER~
  APPEND ~classes.2da~ ~CIPHER SAVECIPH 0 0 -1 0 10~ UNLESS ~CIPHER~
  APPEND ~clsrcreq.2da~ ~CIPHER 1 1 1 1 1 1 1~ UNLESS ~CIPHER~
  APPEND ~hpclass.2da~ ~CIPHER HPPRS~ UNLESS ~CIPHER~
END ELSE BEGIN
  APPEND ~classes.2da~ ~CIPHER %ci_lower% %ci_desc% %ci_title% SAVECIPH 0 %ci_class_id% HPPRS 0 -1 1 1 1 1 1 1 1 0 10~ UNLESS ~CIPHER~
END
'''
new_layout = '''ACTION_IF ci_split = 1 THEN BEGIN
  ACTION_IF (ci_text_cols != 6) AND (ci_text_cols != 9) AND (ci_text_cols != 10) THEN BEGIN FAIL @4 END
  OUTER_SPRINT ci_row ~CIPHER %ci_class_id% * %ci_lower% %ci_desc% %ci_title%~
  ACTION_IF ci_text_cols = 9 THEN BEGIN
    OUTER_SPRINT ci_row ~%ci_row% -1 0 %ci_title%~
  END
  ACTION_IF ci_text_cols = 10 THEN BEGIN
    OUTER_SPRINT ci_row ~%ci_row% -1 0 %ci_title% -1~
  END
  APPEND ~clastext.2da~ ~%ci_row%~ UNLESS ~CIPHER~
  APPEND ~classes.2da~ ~CIPHER SAVECIPH 0 0 -1 0 10~ UNLESS ~CIPHER~
  APPEND ~clsrcreq.2da~ ~CIPHER 1 1 1 1 1 1 1~ UNLESS ~CIPHER~
  APPEND ~hpclass.2da~ ~CIPHER HPPRS~ UNLESS ~CIPHER~
END ELSE BEGIN
  APPEND ~classes.2da~ ~CIPHER %ci_lower% %ci_desc% %ci_title% SAVECIPH 0 %ci_class_id% HPPRS 0 -1 1 1 1 1 1 1 1 0 10~ UNLESS ~CIPHER~
END
'''
if old_layout not in cipher:
    raise RuntimeError("Cipher split layout block changed unexpectedly")
cipher = cipher.replace(old_layout, new_layout)
cipher_path.write_text(cipher, encoding="utf-8")

replace(
    ".github/workflows/psion-static.yml",
    '      - "psion/**"\n      - ".github/workflows/psion-static.yml"',
    '      - "psion/**"\n      - "common/**"\n      - ".github/workflows/psion-static.yml"',
)
replace(
    ".github/workflows/cipher-static.yml",
    "      - 'psion/lib/spell-functions.tpa'\n",
    "      - 'common/**'\n",
)

static_test = r'''#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ps_detect = (ROOT / "psion/lib/class-detect.tpa").read_text(encoding="utf-8")
    ps_layout = (ROOT / "psion/lib/class-layout.tpa").read_text(encoding="utf-8")
    ps_common = (ROOT / "psion/lib/class-common.tpa").read_text(encoding="utf-8")
    cipher = (ROOT / "cipher/lib/class.tpa").read_text(encoding="utf-8")
    sm = (ROOT / "sorcerer-monk/setup-sorcerer-monk.tp2").read_text(encoding="utf-8")
    ps_workflow = (ROOT / ".github/workflows/psion-static.yml").read_text(encoding="utf-8")
    ci_workflow = (ROOT / ".github/workflows/cipher-static.yml").read_text(encoding="utf-8")

    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in ps_detect
    assert "COUNT_2DA_COLS ps_classes_cols" in ps_detect
    assert "ps_telepath_id > 31" in ps_detect
    assert "ps_seer_id = ps_clskills_rows" in ps_detect
    assert "ps_text_cols = 9" in ps_detect
    assert "ps_text_cols = 9" in ps_layout
    assert "ps_qslots_rows != (ps_seer_id - 1)" in ps_common
    assert "LOOKUP_IDS_SYMBOL_OF_INT" in ps_detect

    registration_prefix = cipher.split("COPY_EXISTING ~savewiz.2da~", 1)[0]
    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in registration_prefix
    assert "COUNT_2DA_COLS ci_classes_cols" in registration_prefix
    assert "ci_class_id = ci_skill_pre_rows" in registration_prefix
    assert "ci_class_id > 31" in registration_prefix
    assert "ci_text_cols = 9" in cipher
    assert "ci_qslots_rows != (ci_class_id - 1)" in registration_prefix
    assert "LOOKUP_IDS_SYMBOL_OF_INT" in registration_prefix

    assert "sm_expected_class_id > 31" in sm
    assert "COUNT_2DA_COLS sm_classes_cols" in sm
    assert "sm_clastext_cols = 9" in sm
    assert "sm_qslots_rows != (sm_class_id - 1)" in sm

    assert ps_workflow.count('"common/**"') == 2
    assert ci_workflow.count("'common/**'") == 2
    assert "psion/lib/spell-functions.tpa" not in ci_workflow
    print("Custom class registration invariants are aligned across Psion, Cipher and Sorcerer/Monk.")


if __name__ == "__main__":
    main()
'''
write("common/tests/validate_class_registration.py", static_test)

weidu_test = r'''#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISCIPLINES = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)


def read_rows(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line.split() for line in lines[3:] if line.split()]


def write_native9(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[2].split()
    if len(header) != 5:
        raise AssertionError((path, header))
    out = [lines[0], lines[1], "        CLASSID KITID LOWER DESCSTR MIXED BIOGRAPHY FALLEN BRIEFDESC"]
    for row in read_rows(path):
        if len(row) < 6:
            continue
        out.append(" ".join(row[:6] + ["-1", "0", row[5]]))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def add_combined_hp(path: Path):
    path.write_text("2DA V1.0\n*\n        HP\nMAGE HPWIZ\nSORCERER HPWIZ\nMONK HPMONK\n", encoding="ascii")


def class_ids(path: Path):
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) >= 2:
            try:
                result[fields[1]] = int(fields[0], 0)
            except ValueError:
                pass
    return result


def install(weidu: str, gemrb: Path, mod: str, scenario: str):
    with tempfile.TemporaryDirectory(prefix=f"{mod}-{scenario}-") as tmp:
        game = Path(tmp) / "game"
        base_layout = "legacy" if scenario == "combined_hp" else "normalized"
        subprocess.run([
            sys.executable, str(ROOT / "psion/tests/make_weidu_fixture.py"),
            "--gemrb-root", str(gemrb), "--output", str(game), "--layout", base_layout,
        ], check=True)
        override = game / "override"
        if scenario == "combined_hp":
            add_combined_hp(override / "hpclass.2da")
        else:
            write_native9(override / "clastext.2da")
        shutil.copytree(ROOT / "common", game / "common")
        shutil.copytree(ROOT / mod, game / mod)
        if mod == "cipher":
            subprocess.run([sys.executable, str(ROOT / "cipher/tests/seed_weidu_fixture.py"), str(game)], check=True)
        tp2 = f"{mod}/setup-{mod}.tp2" if mod != "sorcerer-monk" else "sorcerer-monk/setup-sorcerer-monk.tp2"
        subprocess.run([
            weidu, tp2, "--use-lang", "en_US", "--force-install", "0", "--no-exit-pause",
        ], cwd=game, check=True)

        ids = class_ids(override / "class.ids")
        clskills = read_rows(override / "clskills.2da")
        qslots = read_rows(override / "qslots.2da")
        names = DISCIPLINES if mod == "psion" else ("CIPHER",)
        for name in names:
            cl_index = next(index for index, row in enumerate(clskills) if row[0] == name)
            assert ids[name] == cl_index, (mod, scenario, name, ids[name], cl_index)
            assert ids[name] <= 31, (mod, scenario, name, ids[name])
            qs_index = next(index for index, row in enumerate(qslots) if row[0] == name)
            assert qs_index == ids[name] - 1, (mod, scenario, name, qs_index, ids[name])

        if scenario == "combined_hp":
            classes = read_rows(override / "classes.2da")
            for name in names:
                row = next(row for row in classes if row[0] == name)
                assert int(row[6], 0) == ids[name], (mod, scenario, row)
            hp_names = {row[0] for row in read_rows(override / "hpclass.2da")}
            assert not (set(names) & hp_names), (mod, scenario, hp_names)
        else:
            clastext = read_rows(override / "clastext.2da")
            for name in names:
                row = next(row for row in clastext if row[0] == name)
                assert len(row) == 9, (mod, scenario, row)
                assert int(row[1], 0) == ids[name], (mod, scenario, row)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_class_registration_weidu.py WEIDU GEMRB_ROOT")
    weidu = sys.argv[1]
    gemrb = Path(sys.argv[2]).resolve()
    for mod in ("psion", "cipher"):
        for scenario in ("combined_hp", "native9"):
            install(weidu, gemrb, mod, scenario)
    print("Psion and Cipher registration passed combined+HPCLASS and native 9-column CLASTEXT smoke tests.")


if __name__ == "__main__":
    main()
'''
write("common/tests/validate_class_registration_weidu.py", weidu_test)

registration_workflow = r'''name: Custom class registration

on:
  push:
    paths:
      - 'psion/**'
      - 'cipher/**'
      - 'common/**'
      - '.github/workflows/class-registration.yml'
  pull_request:
    paths:
      - 'psion/**'
      - 'cipher/**'
      - 'common/**'
      - '.github/workflows/class-registration.yml'

env:
  WEIDU_VERSION: '251.00'
  GEMRB_FIXTURE_COMMIT: '8c853a764ab489eee7e990a713eeb24dc8cc2d53'

jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Validate shared registration invariants
        run: python common/tests/validate_class_registration.py
      - name: Install official WeiDU release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          gh release download "v${WEIDU_VERSION}" --repo WeiDUorg/weidu --pattern '*Linux*' --dir "$RUNNER_TEMP"
          mkdir -p "$RUNNER_TEMP/weidu"
          unzip -q "$(find "$RUNNER_TEMP" -maxdepth 1 -type f -iname '*linux*' -print -quit)" -d "$RUNNER_TEMP/weidu"
          executable="$(find "$RUNNER_TEMP/weidu" -type f -iname weidu -print -quit)"
          chmod +x "$executable"
          echo "$(dirname "$executable")" >> "$GITHUB_PATH"
      - name: Check out pinned GemRB fixture data
        uses: actions/checkout@v4
        with:
          repository: gemrb/gemrb
          ref: ${{ env.GEMRB_FIXTURE_COMMIT }}
          path: vendor/gemrb
          fetch-depth: 1
      - name: Seed missing Mage saving throw fixture
        run: python psion/tests/seed_savewiz_fixture.py vendor/gemrb
      - name: Validate native-9 and combined-plus-HPCLASS registration
        run: python common/tests/validate_class_registration_weidu.py weidu vendor/gemrb
'''
write(".github/workflows/class-registration.yml", registration_workflow)

replace(
    "psion/README.md",
    "- Legacy Psion GUI/runtime ownership markers are migrated so upgrades preserve the true pre-mod files for uninstall.\n",
    "- Legacy Psion GUI/runtime ownership markers are migrated so upgrades preserve the true pre-mod files for uninstall.\n- Discipline class IDs are allocated from their exact `CLSKILLS.2DA` row indexes, must remain below 32, and are cross-checked against the active class table, `CLASS.IDS`, and positional `QSLOTS.2DA` data. Split class tables support normalized 6-column and native EE 9/10-column `CLASTEXT.2DA`; combined `CLASSES.2DA` is detected from its schema even when `HPCLASS.2DA` is also present.\n",
)
replace(
    "cipher/README.md",
    "- innate/mental power action-bar integration through `QSLOTS.2DA`\n",
    "- innate/mental power action-bar integration through `QSLOTS.2DA`\n- class ID allocation follows the exact `CLSKILLS.2DA` row index and is restricted to GemRB's sub-32 custom-class range; the installer validates class-table, `CLASS.IDS`, and positional `QSLOTS.2DA` identity before mutation\n- combined versus split class tables are detected from `CLASSES.2DA`, including native EE 9/10-column `CLASTEXT.2DA` layouts even when `HPCLASS.2DA` is present\n",
)
