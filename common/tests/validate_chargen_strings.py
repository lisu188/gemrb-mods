#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "common"
GUI = COMMON / "guiscripts"
TOOLS = COMMON / "tools"

UNSAFE_CUSTOM_TEXT_REFS = (17242, 9602, 9588, 11973, 11993, 11994, 15416)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bg1_alignment_fixture():
    return '''import GemRB
import GUICommon

def OnLoad():
\tMyChar = GemRB.GetVar ("Slot")
\tKitName = GUICommon.GetClassRowName (MyChar)
\tBackButton.SetText(15416)
\tDoneButton.SetText(11973)
\tTextAreaControl.SetText(9602)
'''


def bg2_alignment_fixture():
    return '''import GemRB
import GUICommon

def OnLoad():
\tglobal MyChar
\tMyChar = GemRB.GetVar ("Slot")
\tKitName = GUICommon.GetKitRowName (MyChar)
\tBackButton.SetText(15416)
\tDoneButton.SetText(11973)
\tTextAreaControl.SetText(9602)
'''


def prof_fixture():
    return '''import GemRB
import GUICommon

def SetupProfsWindow (pc, proftype, window, callback):
\tif proftype:
\t\tProfsTextArea = window.GetControl(68)
\t\tProfsTextArea.SetText (9588)
\treturn

def ProfsJustPress():
\tProfIndex = GemRB.GetVar("Prof")
\tProfsTextArea.SetText(ProfsTable.GetValue(ProfIndex, 2))
'''


def test_source_contract():
    strings = load("chargen_strings", GUI / "GemRBModStrings.py")
    assert strings.is_custom_class("CIPHER")
    assert strings.is_custom_class("psion_seer")
    assert strings.is_custom_class("SORCERER_MONK")
    assert not strings.is_custom_class("FIGHTER")
    assert strings.CHOOSE_CLASS == "Choose a class."
    assert strings.CHOOSE_ALIGNMENT == "Choose an alignment."
    assert strings.CHOOSE_PROFICIENCIES == "Choose weapon proficiencies."

    for name in ("GemRBModClassChoice.py", "GemRBModPsionChoice.py"):
        source = (GUI / name).read_text(encoding="utf-8")
        assert "import GemRBModStrings" in source
        for value in UNSAFE_CUSTOM_TEXT_REFS:
            assert f"SetText({value})" not in source
            assert f"SetText ({value})" not in source

    cipher_class = (ROOT / "cipher" / "lib" / "class.tpa").read_text(encoding="utf-8")
    cipher_tra = (ROOT / "cipher" / "tra" / "english.tra").read_text(encoding="utf-8")
    assert "ci_lower = RESOLVE_STR_REF(@100)" in cipher_class
    assert "ci_title = RESOLVE_STR_REF(@101)" in cipher_class
    assert "ci_desc = RESOLVE_STR_REF(@102)" in cipher_class
    assert "clastext.2da" in cipher_class.lower()
    assert "@100 = ~cipher~" in cipher_tra
    assert "@101 = ~CIPHER:~" in cipher_tra
    assert "@102 = ~Ciphers are weapon-driven psychic combatants" in cipher_tra

    sorcerer_monk = (ROOT / "sorcerer-monk" / "setup-sorcerer-monk.tp2").read_text(encoding="utf-8")
    assert "sm_lower = RESOLVE_STR_REF (@1)" in sorcerer_monk
    assert "sm_desc = RESOLVE_STR_REF (@2)" in sorcerer_monk
    assert "SORCERER_MONK" in sorcerer_monk

    wrapper = (ROOT / "sorcerer-monk" / "tools" / "install_guiscripts.py").read_text(encoding="utf-8")
    assert '"SorcererMonkUI"' in wrapper
    assert "main_for_handler" in wrapper
    assert (ROOT / "sorcerer-monk" / "guiscripts" / "SorcererMonkUI.py").is_file()


def test_renderers():
    installer = load("chargen_string_installer", TOOLS / "install_guiscripts.py")
    for index, source in enumerate((bg1_alignment_fixture(), bg2_alignment_fixture())):
        path = Path(f"bg{index + 1}-GUICG3.py")
        rendered = installer.render_alignment_string_patch(source, path)
        assert "import GemRBModStrings" in rendered
        assert "GemRBModStrings.is_custom_class(GUICommon.GetClassRowName(MyChar))" in rendered
        assert "GemRBModStrings.BACK if _GemRBModSafeStrings else 15416" in rendered
        assert "GemRBModStrings.DONE if _GemRBModSafeStrings else 11973" in rendered
        assert "GemRBModStrings.CHOOSE_ALIGNMENT if _GemRBModSafeStrings else 9602" in rendered
        assert installer.render_alignment_string_patch(rendered, path) is None

    profs = installer.render_proficiency_string_patch(prof_fixture(), Path("LUProfsSelection.py"))
    assert "import GemRBModStrings" in profs
    assert "GemRBModStrings.CHOOSE_PROFICIENCIES" in profs
    assert "GemRBModStrings.is_custom_class(GUICommon.GetClassRowName(pc))" in profs
    assert "else 9588" in profs
    assert "ProfsTable.GetValue(ProfIndex, 2)" in profs
    assert installer.render_proficiency_string_patch(profs, Path("LUProfsSelection.py")) is None


def fixture_texts():
    return {
        "ActionsWindow.py": '''import GemRB
import Spellbook

def UpdateActionsWindow ():
\tpass

def ActionQSpellPressed (which):
\tpc = GemRB.GameGetFirstSelectedActor ()
\tGemRB.SpellCast (pc, -2, which)
\tUpdateActionsWindow ()
\treturn

def ActionCastPressed ():
\tGemRB.SetVar ("QSpell", None)

def ActionInnatePressed ():
\tGemRB.SetVar ("QSpell", None)

def SpellPressed ():
\tpc = GemRB.GameGetFirstSelectedActor ()
\tSpell = GemRB.GetVar ("Spell")
''',
        "Spellbook.py": '''import GemRB

def GetSpellinfoSpells(actor, BookType):
\tmemorizedSpells = []
\treturn memorizedSpells
''',
        "MenuWindow.py": 'import GemRB\n\ndef Rest():\n\tinfo = GemRB.RestParty (15, 0, 0)\n\treturn info\n',
        "GUISTORE.py": 'import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n',
        "LUSpellSelection.py": '''import GameCheck

def OpenSpellsWindow():
\tif True:
\t\tSpellsTextArea = SpellsWindow.GetControl (41 if GameCheck.IsAnyEE() else 27)
\tif GameCheck.IsBG2OrEE ():
\t\tGemRB.SetNextScript("GUICG6")

def SpellsCancelPress():
\tif GameCheck.IsBG2OrEE ():
\t\tGemRB.SetNextScript("CharGen6")
''',
        "LUProfsSelection.py": prof_fixture(),
        "bg1/GUICG2.py": 'import GemRB\n\ndef OnLoad():\n\tpass\n',
        "bg2/GUICG2.py": 'import GemRB\n\ndef OnLoad():\n\tpass\n',
        "bg1/GUICG3.py": bg1_alignment_fixture(),
        "bg2/GUICG3.py": bg2_alignment_fixture(),
        "bg2/GUICG7.py": 'import GemRB\n\ndef OnLoad():\n\tpass\n',
    }


def write_fixture(folder, originals):
    for name, text in originals.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def runtime_paths():
    return {
        "Psionics": ROOT / "psion" / "guiscripts" / "Psionics.py",
        "Cipher": ROOT / "cipher" / "guiscripts" / "Cipher.py",
        "SorcererMonkUI": ROOT / "sorcerer-monk" / "guiscripts" / "SorcererMonkUI.py",
    }


def marker(folder, handler):
    return folder / (".gemrbmodcore.%s.active" % handler.lower())


def exercise_lifecycle(first, second):
    installer = load(f"chargen_lifecycle_{first}_{second}", TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    runtime = runtime_paths()
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        installer.install_handler(folder, first, runtime[first])
        installer.install_handler(folder, second, runtime[second])

        for game_type in ("bg1", "bg2"):
            alignment = (folder / game_type / "GUICG3.py").read_text(encoding="utf-8")
            assert "GemRBModStrings.CHOOSE_ALIGNMENT" in alignment
            assert alignment.count(installer.MARK_BEGIN) == 1
        profs = (folder / "LUProfsSelection.py").read_text(encoding="utf-8")
        assert "GemRBModStrings.CHOOSE_PROFICIENCIES" in profs
        assert profs.count(installer.MARK_BEGIN) == 1
        assert (folder / "GemRBModStrings.py").exists()
        assert marker(folder, first).exists()
        assert marker(folder, second).exists()

        installer.uninstall_handler(folder, first)
        assert installer.MARK_BEGIN in (folder / "bg1" / "GUICG3.py").read_text(encoding="utf-8")
        assert marker(folder, second).exists()
        installer.uninstall_handler(folder, second)
        for name, text in originals.items():
            assert (folder / name).read_text(encoding="utf-8") == text
        assert not (folder / "GemRBModStrings.py").exists()


def exercise_single_sorcerer_monk():
    installer = load("chargen_lifecycle_sorcerer_monk", TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        runtime = runtime_paths()["SorcererMonkUI"]
        installer.install_handler(folder, "SorcererMonkUI", runtime)
        assert marker(folder, "SorcererMonkUI").exists()
        assert "GemRBModClassChoice.on_load(globals())" in (folder / "bg1" / "GUICG2.py").read_text(encoding="utf-8")
        assert "GemRBModStrings.CHOOSE_ALIGNMENT" in (folder / "bg1" / "GUICG3.py").read_text(encoding="utf-8")
        assert "GemRBModStrings.CHOOSE_PROFICIENCIES" in (folder / "LUProfsSelection.py").read_text(encoding="utf-8")
        installer.uninstall_handler(folder, "SorcererMonkUI")
        for name, text in originals.items():
            assert (folder / name).read_text(encoding="utf-8") == text


def test_lifecycle():
    exercise_lifecycle("Psionics", "Cipher")
    exercise_lifecycle("Cipher", "Psionics")
    exercise_lifecycle("SorcererMonkUI", "Cipher")
    exercise_lifecycle("Psionics", "SorcererMonkUI")
    exercise_single_sorcerer_monk()


def main():
    test_source_contract()
    test_renderers()
    test_lifecycle()
    print("Game-family-safe chargen string validation passed")


if __name__ == "__main__":
    main()
