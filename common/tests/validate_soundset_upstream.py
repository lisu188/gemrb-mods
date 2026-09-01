#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ENUMERATION = "VoiceList.ListResources (CHR_SOUNDS)"
DEFAULT_SET = "GUICommon.AddDefaultVoiceSet (VoiceList, Voices)"


def validate_family(gemrb_root, family):
    path = Path(gemrb_root) / "gemrb" / "GUIScripts" / family / "GUICG19.py"
    text = path.read_text(encoding="utf-8")
    assert text.count(ENUMERATION) == 1, f"{family}: CHR_SOUNDS enumeration contract changed"
    assert text.count(DEFAULT_SET) == 1, f"{family}: default voice-set contract changed"
    enumeration_at = text.index(ENUMERATION)
    default_at = text.index(DEFAULT_SET)
    assert enumeration_at < default_at, f"{family}: default voice-set call moved before enumeration"
    segment = text[enumeration_at:default_at]
    for token in ("IE_CLASS", "GetClassRowName", "ClassSkills"):
        assert token not in segment, f"{family}: class-dependent soundset filter appeared: {token}"
    assert "GemRB.SetPlayerSound" in text, f"{family}: soundset persistence call missing"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: validate_soundset_upstream.py GEMRB_ROOT")
    gemrb_root = Path(args[0]).resolve()
    validate_family(gemrb_root, "bg1")
    validate_family(gemrb_root, "bg2")
    installer = (ROOT / "common" / "tools" / "install_guiscripts.py").read_text(encoding="utf-8")
    assert "GUICG19.py" not in installer, "production GUI installer must not patch the soundset screen"
    print("GemRB soundset upstream contract validation passed")


if __name__ == "__main__":
    main()
