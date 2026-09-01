#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "common" / "tools" / "patch_soundset_diagnostic.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("patch_soundset_diagnostic", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(family):
    position = "\tCharGenCommon.PositionCharGenWin(CharSoundWindow)\n" if family == "bg2" else ""
    return (
        "import GemRB\n"
        "import GUICommon\n"
        "from GUIDefines import *\n"
        "from ie_stats import IE_SEX\n\n"
        "def OnLoad():\n"
        "\tCharSoundWindow=GemRB.LoadWindow(19, \"GUICG\")\n"
        + position
        + "\tVoiceList = CharSoundWindow.GetControl (45)\n"
        + "\tVoices = VoiceList.ListResources (CHR_SOUNDS)\n"
        + "\tGUICommon.AddDefaultVoiceSet (VoiceList, Voices)\n"
    )


def main():
    tool = load_tool()
    with tempfile.TemporaryDirectory() as folder_name:
        root = Path(folder_name)
        originals = {}
        for family in ("bg1", "bg2"):
            directory = root / family
            directory.mkdir(parents=True)
            path = directory / "GUICG19.py"
            text = source(family)
            path.write_text(text, encoding="utf-8")
            originals[family] = text

        changed = tool.patch_root(root)
        assert sorted(changed) == ["bg1/GUICG19.py", "bg2/GUICG19.py"]
        for family in ("bg1", "bg2"):
            path = root / family / "GUICG19.py"
            text = path.read_text(encoding="utf-8")
            assert tool.MARK_BEGIN in text
            assert text.count("VoiceList.ListResources (CHR_SOUNDS)") == 1
            assert f"GEMRB_MODS_SOUNDSET|family={family}|count=%d" in text
            assert "GUICommon.GetClassRowName (_GemRBModsSlot)" in text
            backup = tool.backup_path(path)
            assert backup.read_text(encoding="utf-8") == originals[family]

        assert tool.patch_root(root) == []
        restored = tool.patch_root(root, uninstall=True)
        assert sorted(restored) == ["bg1/GUICG19.py", "bg2/GUICG19.py"]
        for family in ("bg1", "bg2"):
            path = root / family / "GUICG19.py"
            assert path.read_text(encoding="utf-8") == originals[family]
            assert not tool.backup_path(path).exists()

        broken = root / "bg1" / "GUICG19.py"
        broken.write_text("import GemRB\n", encoding="utf-8")
        try:
            tool.patch_file(broken, "bg1")
        except RuntimeError as error:
            assert "enumeration layout not recognized" in str(error)
        else:
            raise AssertionError("unsupported GUICG19 layout was accepted")

    print("Soundset diagnostic patch validation passed")


if __name__ == "__main__":
    main()
