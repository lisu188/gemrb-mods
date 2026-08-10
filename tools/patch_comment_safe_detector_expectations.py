from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    "common/tests/validate_class_registration.py",
    '    assert "ps_text_cols = 9" in ps_detect\n',
    '    assert "ps_detect_text_cols = 9" in ps_detect\n',
)
replace(
    "psion/tests/validate_core.py",
    '        "ps_text_cols = 9",\n',
    '        "ps_detect_text_cols = 9",\n',
)
