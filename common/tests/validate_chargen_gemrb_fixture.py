#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "common" / "tools" / "install_guiscripts.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("chargen_fixture_installer", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    assert path.is_file(), path
    return path.read_text(encoding="utf-8")


def verify_alignment(installer, guiscripts, family):
    path = guiscripts / family / "GUICG3.py"
    source = read(path)
    assert "TextAreaControl.SetText(9602)" in source or "TextAreaControl.SetText (9602)" in source
    rendered = installer.render_alignment_string_patch(source, path)
    assert rendered is not None
    assert "GemRBModStrings.is_custom_class(GUICommon.GetClassRowName(MyChar))" in rendered
    assert "GemRBModStrings.CHOOSE_ALIGNMENT if _GemRBModSafeStrings else 9602" in rendered
    assert "GemRBModStrings.BACK if _GemRBModSafeStrings else 15416" in rendered
    assert "GemRBModStrings.DONE if _GemRBModSafeStrings else 11973" in rendered
    assert rendered.count(installer.MARK_BEGIN) == 1
    assert rendered.count(installer.MARK_END) == 1


def verify_proficiencies(installer, guiscripts):
    path = guiscripts / "LUProfsSelection.py"
    source = read(path)
    assert "ProfsTextArea.SetText (9588)" in source or "ProfsTextArea.SetText(9588)" in source
    rendered = installer.render_proficiency_string_patch(source, path)
    assert rendered is not None
    assert "GemRBModStrings.CHOOSE_PROFICIENCIES" in rendered
    assert "GemRBModStrings.is_custom_class(GUICommon.GetClassRowName(pc))" in rendered
    assert "else 9588" in rendered
    assert "ProfsTable.GetValue" in rendered
    assert rendered.count(installer.MARK_BEGIN) == 1
    assert rendered.count(installer.MARK_END) == 1


def verify_class_choice(installer, guiscripts, family):
    path = guiscripts / family / "GUICG2.py"
    source = read(path)
    rendered = installer.render_class_choice_patch(source, path)
    assert rendered is not None
    assert "import GemRBModClassChoice" in rendered
    assert "GemRBModClassChoice.on_load(globals())" in rendered
    assert "def _GemRBModCoreOriginalOnLoad():" in rendered


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_chargen_gemrb_fixture.py GEMRB_ROOT")
    gemrb_root = Path(sys.argv[1]).resolve()
    guiscripts = gemrb_root / "gemrb" / "GUIScripts"
    installer = load_installer()
    for family in ("bg1", "bg2"):
        verify_class_choice(installer, guiscripts, family)
        verify_alignment(installer, guiscripts, family)
    verify_proficiencies(installer, guiscripts)
    print("Real GemRB BGEE/BG2EE-family chargen text patch validation passed")


if __name__ == "__main__":
    main()
