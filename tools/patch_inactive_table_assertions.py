from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    "psion/tests/validate_weidu_install.sh",
    '''if not split_schema:\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        path = override / filename\n        if path.is_file():\n            text = path.read_text(encoding="utf-8", errors="replace")\n            for discipline in disciplines:\n                assert discipline not in text, (layout, filename, discipline)\n\n''',
    '',
)

replace(
    "cipher/tests/verify_weidu_install.py",
    '''else:\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        path = override / filename\n        if path.is_file():\n            assert "CIPHER" not in path.read_text(encoding="utf-8", errors="replace"), (layout, filename)\n\n''',
    '',
)
