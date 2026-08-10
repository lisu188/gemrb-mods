#!/usr/bin/env python3
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
