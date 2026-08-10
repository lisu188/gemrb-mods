from pathlib import Path

path = Path(__file__).resolve().parents[1] / "psion/tests/validate_core.py"
text = path.read_text(encoding="utf-8")
old = '''    detector = (ROOT / "lib" / "class-detect.tpa").read_text(encoding="utf-8")
    for fragment in (
        "INDEX_BUFFER (~BIOGRAPHY~)",
        "SET ps_detect_cols = 10",
        "SET ps_detect_cols = 19",
        "READ_2DA_ENTRY ps_i 6 ps_detect_cols ps_id",
    ):
        assert fragment in detector, fragment
'''
new = '''    detector = (ROOT / "lib" / "class-detect.tpa").read_text(encoding="utf-8")
    for fragment in (
        "COUNT_2DA_COLS ps_clskills_cols",
        "OUTER_SET ps_seer_id = ps_clskills_rows",
        "ps_telepath_id > 31",
        "COUNT_2DA_COLS ps_classes_cols",
        "ps_classes_cols = 7",
        "ps_classes_cols = 19",
        "ps_text_cols = 9",
        "LOOKUP_IDS_SYMBOL_OF_INT",
    ):
        assert fragment in detector, fragment
    assert "FILE_EXISTS_IN_GAME ~hpclass.2da~" not in detector
'''
if old not in text:
    raise RuntimeError("validate_core registration expectations changed unexpectedly")
path.write_text(text.replace(old, new), encoding="utf-8")
