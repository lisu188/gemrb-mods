#!/usr/bin/env python3
"""Shared runtime primitive, dispatcher, and GUI lifecycle validation."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "common"
GUI = COMMON / "guiscripts"
TOOLS = COMMON / "tools"
sys.path.insert(0, str(GUI))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_transactions():
    transactions = load("transactions_test", GUI / "Transactions.py")
    calls = []
    assert transactions.begin("X", 1, ("A", 5), lambda: True)
    assert not calls
    assert transactions.begin("X", 1, ("A", 5), lambda: True, lambda: calls.append("commit") or True)
    assert calls == ["commit"]
    assert not transactions.begin("X", 1, ("B", 2), lambda: True)
    transactions.cancel("X", 1)
    assert transactions.begin("X", 1, ("B", 2), lambda: True)
    transactions.cancel("X")
    transactions.clear()


def test_state_and_charges():
    gemrb = types.ModuleType("GemRB")
    effects = []
    known = [{"SpellResRef": "MODA"}, {"SpellResRef": "OTHER"}]
    memorized = [
        {"SpellResRef": "MODA", "Flags": 0},
        {"SpellResRef": "OTHER", "Flags": 0},
    ]

    gemrb.GetEffects = lambda actor, opcode: [dict(e) for e in effects if e["Opcode"] == opcode]
    gemrb.DispelEffect = lambda actor, opcode, marker: effects.__setitem__(slice(None), [e for e in effects if not (e["Opcode"] == opcode and e["Param2"] == marker)])

    def apply_effect(actor, opcode, p1, p2, r1="", r2="", r3="", source=""):
        effects.append({"Opcode": opcode, "Param1": p1, "Param2": p2, "Resource1": r1})

    gemrb.ApplyEffect = apply_effect
    gemrb.GetKnownSpellsCount = lambda *args: len(known)
    gemrb.GetKnownSpell = lambda actor, st, sl, index: dict(known[index])
    gemrb.GetMemorizedSpellsCount = lambda *args: len(memorized)
    gemrb.GetMemorizedSpell = lambda actor, st, sl, index: dict(memorized[index])
    gemrb.UnmemorizeSpell = lambda actor, st, sl, index: memorized.pop(index) is not None

    def memorize(actor, st, sl, known_index, usable):
        memorized.append({"SpellResRef": known[known_index]["SpellResRef"], "Flags": usable})
        return True

    gemrb.MemorizeSpell = memorize
    previous = sys.modules.get("GemRB")
    sys.modules["GemRB"] = gemrb
    try:
        state = load("persistent_state_test", GUI / "PersistentState.py")
        charges = load("innate_charges_test", GUI / "InnateCharges.py")
        assert not state.read(1, "Protection:Spell", 7, "STATE")[0]
        assert state.write(1, "Protection:Spell", 7, "STATE", 9, "SRC") == 9
        assert state.read(1, "Protection:Spell", 7, "STATE") == (True, 9)
        assert charges.refresh(1, lambda resref: resref == "MODA") == 1
        assert any(row["SpellResRef"] == "MODA" and row["Flags"] for row in memorized)
        assert any(row["SpellResRef"] == "OTHER" and not row["Flags"] for row in memorized)
    finally:
        if previous is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = previous


def test_dispatcher():
    psion = types.ModuleType("Psionics")
    cipher = types.ModuleType("Cipher")
    psion.INNATE_TYPE = 2
    cipher.INNATE_TYPE = 2
    calls = []
    psion.action_info = lambda r: {"resref": r, "parent": r} if r == "PSX" else None
    cipher.power_info = lambda r: {"resref": r} if r == "CIX" else None
    psion.resolve_power_entry = lambda sb, actor, raw: {"SpellResRef": "PSX"} if raw == 1 else None
    cipher.resolve_power_entry = lambda sb, actor, raw: {"SpellResRef": "CIX"} if raw == 2 else None
    psion.begin_manifest = lambda actor, r: calls.append(("psion", actor, r)) or True
    cipher.begin_manifest = lambda actor, r: calls.append(("cipher", actor, r)) or True
    psion.cancel_pending = lambda actor=None: calls.append(("cancel-psion", actor))
    cipher.cancel_pending = lambda actor=None: calls.append(("cancel-cipher", actor))
    psion.restore_party = lambda: calls.append(("rest-psion",))
    cipher.restore_party = lambda: calls.append(("rest-cipher",))
    psion.refresh_innate_charges = lambda actor: 2
    cipher.refresh_innate_charges = lambda actor: 3
    psion.filter_spellinfo = lambda actor, refs: [r for r in refs if r != "BAD"]

    old = {name: sys.modules.get(name) for name in ("Psionics", "Cipher")}
    sys.modules["Psionics"] = psion
    sys.modules["Cipher"] = cipher
    try:
        core = load("core_dispatch_test", GUI / "GemRBModCore.py")
        assert core.begin_spell(None, 4, 1)
        assert core.begin_spell(None, 4, 2)
        assert calls[:2] == [("psion", 4, "PSX"), ("cipher", 4, "CIX")]
        assert core.action_info("PSX")["handler"] == "Psionics"
        assert core.action_info("CIX")["handler"] == "Cipher"
        assert core.refresh_innate_charges(4) == 5
        assert core.filter_spellinfo(4, ["OK", "BAD"]) == ["OK"]
        core.cancel_pending(4)
        core.restore_party()
    finally:
        for name, previous in old.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def test_dispatcher_import_errors():
    core = load("core_import_test", GUI / "GemRBModCore.py")
    original_names = core._HANDLER_NAMES
    original_import = core.importlib.import_module
    try:
        core._HANDLER_NAMES = ("MissingHandler",)

        def missing_handler(name):
            raise ImportError("handler is not installed", name=name)

        core.importlib.import_module = missing_handler
        assert core._handlers() == []

        def broken_handler(name):
            raise ImportError("installed handler dependency is missing", name="SharedDependency")

        core.importlib.import_module = broken_handler
        try:
            core._handlers()
        except ImportError as exc:
            assert exc.name == "SharedDependency"
        else:
            raise AssertionError("dependency ImportError from an installed handler was swallowed")
    finally:
        core._HANDLER_NAMES = original_names
        core.importlib.import_module = original_import


def test_class_choice_pagination():
    variables = {}
    class_name = {"value": "PSION_SEER"}
    next_script = {"value": None}

    class Control:
        def __init__(self, control_id):
            self.control_id = control_id
            self.text = None
            self.state = None
            self.callback = None
            self.assoc = None
            self.frame = {"x": 10, "y": control_id * 10, "w": 100, "h": 9}

        def GetFrame(self):
            return self.frame

        def SetFlags(self, *args):
            pass

        def SetState(self, state):
            self.state = state

        def SetText(self, text):
            self.text = text

        def SetSize(self, width, height):
            self.frame["w"] = width
            self.frame["h"] = height

        def OnPress(self, callback):
            self.callback = callback

        def SetVarAssoc(self, name, value, *bounds):
            self.assoc = (name, value, bounds)
            variables[name] = value

        def OnChange(self, callback):
            self.callback = callback

        def MakeDefault(self):
            pass

    class Window:
        def __init__(self):
            ids = set(range(2, 10)) | set(range(20, 24)) | {0, 10, 11, 13, 14}
            self.controls = {control_id: Control(control_id) for control_id in ids}
            self.modal = None

        def GetControl(self, control_id):
            return self.controls.get(control_id)

        def GetFrame(self):
            return {"x": 0, "y": 0, "w": 640, "h": 480}

        def CreateScrollBar(self, control_id, frame, sprites):
            control = self.controls[control_id] = Control(control_id)
            control.frame = frame
            return control

        def SetEventProxy(self, control):
            self.proxy = control

        def ShowModal(self, mode):
            self.modal = mode
            variables["GemRBModClassTopIndex"] = 0

    class Table:
        def __init__(self, names):
            self.names = names

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

        def GetValue(self, row, column, *args):
            if column == "MULTI":
                return int(row.startswith("MULTI_") or row == "SORCERER_MONK")
            if column == "LOWER":
                return row.title()
            return 1

    names = [f"CLASS_{index}" for index in range(20)] + ["SORCERER_MONK", "MULTI_CLASS"]
    window = Window()
    gemrb = types.ModuleType("GemRB")
    gemrb.GetVar = lambda name: variables.get(name)
    gemrb.SetVar = lambda name, value: variables.__setitem__(name, value)
    gemrb.GetPlayerStat = lambda actor, stat: 23
    gemrb.SetNextScript = lambda name: next_script.__setitem__("value", name)
    gemrb.LoadWindow = lambda *args: window
    gemrb.LoadTable = lambda *args: Table(names)
    gemrb.Log = lambda *args: None

    common_tables = types.ModuleType("CommonTables")
    common_tables.Classes = Table(names)
    common_tables.ClassText = Table(names)
    gui_common = types.ModuleType("GUICommon")
    gui_common.GetRaceRowName = lambda actor: "HUMAN"
    gui_common.GetClassRowName = lambda class_id, mode: class_name["value"]
    chargen = types.ModuleType("CharGenCommon")
    chargen.back = lambda window: None
    defines = types.ModuleType("GUIDefines")
    for name, value in {
        "IE_GUI_BUTTON_RADIOBUTTON": 1,
        "IE_GUI_BUTTON_DISABLED": 2,
        "IE_GUI_BUTTON_ENABLED": 3,
        "OP_OR": 4,
        "GTV_INT": 5,
        "MODAL_SHADOW_GRAY": 6,
    }.items():
        setattr(defines, name, value)
    ie_stats = types.ModuleType("ie_stats")
    ie_stats.IE_CLASS = 7

    replacements = {
        "GemRB": gemrb,
        "CommonTables": common_tables,
        "GUICommon": gui_common,
        "CharGenCommon": chargen,
        "GUIDefines": defines,
        "ie_stats": ie_stats,
    }
    old = {name: sys.modules.get(name) for name in replacements}
    sys.modules.update(replacements)
    try:
        choices = load("class_choice_test", GUI / "GemRBModClassChoice.py")
        script = {
            "ClassPress": lambda: None,
            "MultiClassPress": lambda: None,
            "SpecialistPress": lambda: None,
            "NextPress": lambda: None,
        }
        choices.on_load(script)
        scrollbar = window.GetControl(choices.SCROLLBAR_ID)
        assert scrollbar.assoc == (choices.TOP_INDEX_VAR, 9, (0, 9))
        assert [window.GetControl(control_id).text for control_id in choices.BG1_BUTTON_IDS] == [
            name.title() for name in names[9:21]
        ]
        assert window.GetControl(choices.BG1_BUTTON_IDS[-1]).text == "Sorcerer_Monk"
        assert variables["Class"] == 0

        variables["Class"] = names.index("SORCERER_MONK") + 1
        window.GetControl(0).SetState(defines.IE_GUI_BUTTON_ENABLED)
        window.GetControl(13).SetText("selected class description")
        variables[choices.TOP_INDEX_VAR] = 0
        scrollbar.callback()
        assert variables["Class"] == 0
        assert window.GetControl(0).state == defines.IE_GUI_BUTTON_DISABLED
        assert window.GetControl(13).text == choices.GemRBModStrings.CHOOSE_CLASS
        assert [window.GetControl(control_id).text for control_id in choices.BG1_BUTTON_IDS] == [
            name.title() for name in names[:12]
        ]
        assert window.GetControl(choices.BG1_BUTTON_IDS[-1]).assoc[:2] == ("Class", 12)

        variables["Class"] = 1
        window.GetControl(0).SetState(defines.IE_GUI_BUTTON_ENABLED)
        window.GetControl(13).SetText("visible class description")
        choices.redraw()
        assert variables["Class"] == 1
        assert window.GetControl(0).state == defines.IE_GUI_BUTTON_ENABLED
        assert window.GetControl(13).text == "visible class description"

        variables["Slot"] = 1
        assert choices.skip_spell_selection()
        assert next_script["value"] == "GUICG6"
        class_name["value"] = "CIPHER"
        assert choices.skip_spell_selection()
        class_name["value"] = "SORCERER_MONK"
        assert not choices.skip_spell_selection()
    finally:
        for name, previous in old.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def fixture_texts():
    alignment = '''import GemRB
import GUICommon

def OnLoad():
\tMyChar = GemRB.GetVar ("Slot")
\tKitName = GUICommon.GetClassRowName (MyChar)
\tBackButton.SetText(15416)
\tDoneButton.SetText(11973)
\tTextAreaControl.SetText(9602)
'''
    proficiencies = '''import GemRB
import GUICommon

def SetupProfsWindow (pc, proftype, window, callback):
\tif proftype:
\t\tProfsTextArea = window.GetControl(68)
\t\tProfsTextArea.SetText (9588)
\treturn
'''
    return {
        "ActionsWindow.py": '''import GemRB\nimport Spellbook\n\ndef UpdateActionsWindow ():\n\tpass\n\ndef ActionQSpellPressed (which):\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tGemRB.SpellCast (pc, -2, which)\n\tUpdateActionsWindow ()\n\treturn\n\ndef ActionCastPressed ():\n\tGemRB.SetVar ("QSpell", None)\n\ndef ActionInnatePressed ():\n\tGemRB.SetVar ("QSpell", None)\n\ndef SpellPressed ():\n\tpc = GemRB.GameGetFirstSelectedActor ()\n\tSpell = GemRB.GetVar ("Spell")\n''',
        "Spellbook.py": '''import GemRB\n\ndef GetSpellinfoSpells(actor, BookType):\n\tmemorizedSpells = []\n\tspellResRefs = GemRB.GetSpelldata (actor)\n\tfor i, resRef in enumerate(spellResRefs):\n\t\tmemorizedSpells.append({"SpellIndex": i + 255000, "SpellResRef": resRef})\n\treturn memorizedSpells\n''',
        "MenuWindow.py": 'import GemRB\n\ndef Rest():\n\tinfo = GemRB.RestParty (15, 0, 0)\n\treturn info\n',
        "GUISTORE.py": "import GemRB\n\ndef Rest():\n\tGemRB.RestParty(0, 0)\n",
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
        "LUProfsSelection.py": proficiencies,
        "bg1/GUICG2.py": "import GemRB\n\ndef OnLoad():\n\tpass\n",
        "bg2/GUICG2.py": "import GemRB\n\ndef OnLoad():\n\tpass\n",
        "bg1/GUICG3.py": alignment,
        "bg2/GUICG3.py": alignment,
        "bg2/GUICG7.py": "import GemRB\n\ndef OnLoad():\n\tpass\n",
    }


def write_fixture(folder, originals):
    for name, text in originals.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def exercise_order(first, second):
    installer = load("core_installer_%s_%s" % (first, second), TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    runtime = {
        "Psionics": ROOT / "psion" / "guiscripts" / "Psionics.py",
        "Cipher": ROOT / "cipher" / "guiscripts" / "Cipher.py",
    }
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)

        installer.install_handler(folder, first, runtime[first])
        installer.install_handler(folder, second, runtime[second])
        actions = (folder / "ActionsWindow.py").read_text(encoding="utf-8")
        spellbook = (folder / "Spellbook.py").read_text(encoding="utf-8")
        menu = (folder / "MenuWindow.py").read_text(encoding="utf-8")
        store = (folder / "GUISTORE.py").read_text(encoding="utf-8")
        class_scripts = [
            (folder / game_type / "GUICG2.py").read_text(encoding="utf-8")
            for game_type in ("bg1", "bg2")
        ]
        alignment_scripts = [
            (folder / game_type / "GUICG3.py").read_text(encoding="utf-8")
            for game_type in ("bg1", "bg2")
        ]
        profs = (folder / "LUProfsSelection.py").read_text(encoding="utf-8")
        spell_selection = (folder / "bg2" / "GUICG7.py").read_text(encoding="utf-8")
        spell_window = (folder / "LUSpellSelection.py").read_text(encoding="utf-8")
        assert actions.count(installer.MARK_BEGIN) == 4
        assert spellbook.count(installer.MARK_BEGIN) == 1
        assert 'if not info["Error"]:' in menu
        assert "\t\tGemRBModCore.restore_party()" in menu
        assert "\tGemRBModCore.restore_party()" in store
        assert all("import GemRBModClassChoice" in classes for classes in class_scripts)
        assert all("GemRBModClassChoice.on_load(globals())" in classes for classes in class_scripts)
        assert all("GemRBModStrings.CHOOSE_ALIGNMENT" in script for script in alignment_scripts)
        assert "GemRBModStrings.CHOOSE_PROFICIENCIES" in profs
        assert "import GemRBModClassChoice" in spell_selection
        assert "GemRBModClassChoice.skip_spell_selection()" in spell_selection
        assert "if not SpellsTextArea and GameCheck.IsBGEE():" in spell_window
        assert "SpellsTextArea = SpellsWindow.GetControl (27)" in spell_window
        assert spell_window.count(
            "(GameCheck.IsBG2OrEE () or GameCheck.IsBGEE ())"
        ) == 2
        assert "import GemRBModCore" in actions
        assert "GemRBModCore.begin_spell" in actions
        assert "GemRBModCore.action_info" in actions
        assert (folder / ".gemrbmodcore.psionics.active").exists()
        assert (folder / ".gemrbmodcore.cipher.active").exists()
        for name in installer.COMMON_MODULES:
            assert (folder / name).exists()

        installer.uninstall_handler(folder, first)
        assert installer.MARK_BEGIN in (folder / "ActionsWindow.py").read_text(encoding="utf-8")
        assert (folder / (second + ".py")).exists()
        installer.uninstall_handler(folder, second)
        for name, text in originals.items():
            assert (folder / name).read_text(encoding="utf-8") == text
        for name in installer.COMMON_MODULES:
            assert not (folder / name).exists()


def exercise_legacy_runtime_upgrade(handler, legacy_tag):
    installer = load("legacy_installer_%s" % handler, TOOLS / "install_guiscripts.py")
    originals = fixture_texts()
    runtime_source = ROOT / ("psion" if handler == "Psionics" else "cipher") / "guiscripts" / (handler + ".py")

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        runtime_target = folder / (handler + ".py")
        runtime_target.write_text("legacy installed runtime\n", encoding="utf-8")
        legacy_backup = runtime_target.with_suffix(runtime_target.suffix + f".{legacy_tag}.bak")
        legacy_backup.write_text("original user runtime\n", encoding="utf-8")

        installer.install_handler(folder, handler, runtime_source)
        backup, created = installer._owned_paths(runtime_target, handler)
        assert not legacy_backup.exists()
        assert backup.read_text(encoding="utf-8") == "original user runtime\n"
        assert not created.exists()
        assert runtime_target.read_bytes() == runtime_source.read_bytes()

        installer.uninstall_handler(folder, handler)
        assert runtime_target.read_text(encoding="utf-8") == "original user runtime\n"
        assert not backup.exists()

    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        write_fixture(folder, originals)
        runtime_target = folder / (handler + ".py")
        runtime_target.write_text("legacy installed runtime\n", encoding="utf-8")
        legacy_created = runtime_target.with_suffix(runtime_target.suffix + f".{legacy_tag}.created")
        legacy_created.write_text("legacy owner\n", encoding="utf-8")

        installer.install_handler(folder, handler, runtime_source)
        backup, created = installer._owned_paths(runtime_target, handler)
        assert not legacy_created.exists()
        assert not backup.exists()
        assert created.exists()
        assert runtime_target.read_bytes() == runtime_source.read_bytes()

        installer.uninstall_handler(folder, handler)
        assert not runtime_target.exists()
        assert not created.exists()


def test_gui_lifecycle():
    exercise_order("Psionics", "Cipher")
    exercise_order("Cipher", "Psionics")
    exercise_legacy_runtime_upgrade("Psionics", "psion")
    exercise_legacy_runtime_upgrade("Cipher", "cipher")


def main():
    test_transactions()
    test_state_and_charges()
    test_dispatcher()
    test_dispatcher_import_errors()
    test_class_choice_pagination()
    test_gui_lifecycle()
    print("Shared GemRB runtime and GUI lifecycle validation passed")


if __name__ == "__main__":
    main()
