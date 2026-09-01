"""Choose a Psion discipline while retaining distinct runtime class rows."""
import GemRB
import CharGenCommon
import CommonTables
import GUICG2
import GemRBModStrings
from GUIDefines import *
from ie_stats import IE_KIT


PSION_CLASSES = (
	"PSION_SEER",
	"PSION_SHAPER",
	"PSION_KINETICIST",
	"PSION_EGOIST",
	"PSION_NOMAD",
	"PSION_TELEPATH",
)
BUTTON_IDS = (1, 2, 3, 4, 9, 10)
CHOICE_VAR = "GemRBModPsionDiscipline"

DisciplineWindow = None
TextAreaControl = None
DoneButton = None
MyChar = 0
_rows = []


def _class_rows():
	rows = []
	for class_name in PSION_CLASSES:
		row_index = CommonTables.Classes.GetRowIndex(class_name)
		if row_index is not None and row_index >= 0:
			rows.append((row_index, class_name))
	return rows


def OnLoad():
	global DisciplineWindow, TextAreaControl, DoneButton, MyChar, _rows
	MyChar = GemRB.GetVar("Slot")
	_rows = _class_rows()
	if not _rows:
		raise RuntimeError("No Psion discipline classes are installed")

	DisciplineWindow = GemRB.LoadWindow(22, "GUICG")
	CharGenCommon.PositionCharGenWin(DisciplineWindow)
	title = DisciplineWindow.GetControl(0xfffffff)
	if title:
		title.SetText(GemRBModStrings.PSION_DISCIPLINE)

	for slot, control_id in enumerate(BUTTON_IDS):
		button = DisciplineWindow.GetControl(control_id)
		button.SetFlags(IE_GUI_BUTTON_RADIOBUTTON, OP_OR)
		button.SetState(IE_GUI_BUTTON_DISABLED)
		if slot >= len(_rows):
			button.SetText("")
			continue
		row_index, class_name = _rows[slot]
		button.SetText(CommonTables.ClassText.GetValue(class_name, "LOWER"))
		button.SetState(IE_GUI_BUTTON_ENABLED)
		button.SetVarAssoc(CHOICE_VAR, slot)
		button.OnPress(DisciplinePress)

	back_button = DisciplineWindow.GetControl(8)
	back_button.SetText(GemRBModStrings.BACK)
	back_button.MakeEscape()
	back_button.OnPress(BackPress)
	DoneButton = DisciplineWindow.GetControl(7)
	DoneButton.SetText(GemRBModStrings.DONE)
	DoneButton.MakeDefault()
	DoneButton.SetState(IE_GUI_BUTTON_DISABLED)
	DoneButton.OnPress(NextPress)
	TextAreaControl = DisciplineWindow.GetControl(5)
	TextAreaControl.SetText(GemRBModStrings.CHOOSE_PSION_DISCIPLINE)
	GemRB.SetVar(CHOICE_VAR, -1)
	DisciplineWindow.Focus()


def DisciplinePress():
	choice = GemRB.GetVar(CHOICE_VAR)
	if choice is None or choice < 0 or choice >= len(_rows):
		return
	row_index, class_name = _rows[choice]
	GemRB.SetVar("Class", row_index + 1)
	TextAreaControl.SetText(CommonTables.ClassText.GetValue(class_name, "DESCSTR"))
	DoneButton.SetState(IE_GUI_BUTTON_ENABLED)


def BackPress():
	GemRB.SetVar("Class", 0)
	GemRB.SetVar("Class Kit", 0)
	if DisciplineWindow:
		DisciplineWindow.Close()
	GemRB.SetNextScript("GUICG2")


def NextPress():
	if not GemRB.GetVar("Class"):
		return
	GemRB.SetVar("Class Kit", 0)
	GemRB.SetVar("MAGESCHOOL", 0)
	GUICG2.MyChar = MyChar
	GUICG2.SetClass()
	GemRB.SetPlayerStat(MyChar, IE_KIT, 0)
	if DisciplineWindow:
		DisciplineWindow.Close()
	GemRB.SetNextScript("CharGen4")
