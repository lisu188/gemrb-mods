"""Expose appended single classes in BG1 character generation."""
import GemRB
import CharGenCommon
import CommonTables
import GUICommon
import GemRBModStrings
from GUIDefines import *
from ie_stats import IE_CLASS


BG1_BUTTON_IDS = tuple(range(2, 10)) + tuple(range(20, 24))
BG2_BUTTON_IDS = tuple(range(2, 10)) + tuple(range(15, 19))
TOP_INDEX_VAR = "GemRBModClassTopIndex"
SCROLLBAR_ID = 1000
DIRECT_MULTI_CLASSES = ("SORCERER_MONK",)
PSION_CLASSES = (
	"PSION_SEER",
	"PSION_SHAPER",
	"PSION_KINETICIST",
	"PSION_EGOIST",
	"PSION_NOMAD",
	"PSION_TELEPATH",
)
NO_PICK_SPELL_CLASSES = PSION_CLASSES + ("CIPHER",)

_class_rows = []
_button_ids = []
_script = None
_bg2_style = False
_last_offset = None


def _available_buttons(window, candidates):
	return [control_id for control_id in candidates if window.GetControl(control_id)]


def _create_scrollbar(window, button_ids, maximum):
	frames = [window.GetControl(control_id).GetFrame() for control_id in button_ids]
	top = min(frame["y"] for frame in frames)
	bottom = max(frame["y"] + frame["h"] for frame in frames)
	right = max(frame["x"] + frame["w"] for frame in frames)
	width = 16
	gap = 4
	for control_id in button_ids:
		button = window.GetControl(control_id)
		frame = button.GetFrame()
		button.SetSize(frame["w"] - width - gap, frame["h"])
	x = right - width
	scrollbar = window.CreateScrollBar(
		SCROLLBAR_ID,
		{"x": x, "y": top, "w": width, "h": bottom - top},
		"GUISCRCW",
	)
	scrollbar.SetVarAssoc(TOP_INDEX_VAR, maximum, 0, maximum)
	GemRB.SetVar(TOP_INDEX_VAR, maximum)
	scrollbar.OnChange(redraw)
	window.SetEventProxy(scrollbar)
	return scrollbar


def redraw():
	global _last_offset
	offset = GemRB.GetVar(TOP_INDEX_VAR) or 0
	page_changed = _last_offset is not None and offset != _last_offset
	selected_class = 0 if page_changed else GemRB.GetVar("Class") or 0
	_last_offset = offset
	for slot, control_id in enumerate(_button_ids):
		button = _script["ClassWindow"].GetControl(control_id)
		row_offset = offset + slot
		button.SetFlags(IE_GUI_BUTTON_RADIOBUTTON, OP_OR)
		button.OnPress(None)
		if row_offset >= len(_class_rows):
			button.SetText("")
			button.SetState(IE_GUI_BUTTON_DISABLED)
			continue

		row_index, class_name, allowed = _class_rows[row_offset]
		button.SetText("PSION" if class_name == PSION_CLASSES[0] else CommonTables.ClassText.GetValue(class_name, "LOWER"))
		button.SetState(IE_GUI_BUTTON_DISABLED)
		if allowed == 0 or (not _bg2_style and allowed != 1):
			continue
		button.SetState(IE_GUI_BUTTON_ENABLED)
		button.OnPress(_psion_press if class_name == PSION_CLASSES[0] else _script["ClassPress"])
		button.SetVarAssoc("Class", row_index + 1)
	GemRB.SetVar("Class", selected_class)
	if page_changed:
		done_button = _script.get("DoneButton")
		if done_button:
			done_button.SetState(IE_GUI_BUTTON_DISABLED)
		text_area = _script.get("TextAreaControl")
		if text_area:
			text_area.SetText(GemRBModStrings.CHOOSE_CLASS)


def _psion_press():
	GemRB.SetVar("Class", 0)
	if _script["ClassWindow"]:
		_script["ClassWindow"].Close()
	GemRB.SetNextScript("GemRBModPsionChoice")


def skip_spell_selection():
	"""Skip BGEE's stock wizard spell picker for innate-powered classes."""
	my_char = GemRB.GetVar("Slot")
	class_id = GemRB.GetPlayerStat(my_char, IE_CLASS)
	class_name = GUICommon.GetClassRowName(class_id, "class")
	if class_name not in NO_PICK_SPELL_CLASSES:
		return False
	GemRB.SetNextScript("GUICG6")
	return True


def on_load(script):
	global _class_rows, _button_ids, _script, _bg2_style, _last_offset
	_script = script
	_bg2_style = "BackPress" in script
	_last_offset = None
	my_char = GemRB.GetVar("Slot")

	GemRB.SetVar("Class", 0)
	GemRB.SetVar("Multi Class", 0)
	GemRB.SetVar("Specialist", 0)
	GemRB.SetVar("Class Kit", 0)
	GemRB.SetVar("MAGESCHOOL", 0)
	GemRB.SetVar(TOP_INDEX_VAR, 0)

	class_window = GemRB.LoadWindow(2, "GUICG")
	script["ClassWindow"] = class_window
	if _bg2_style:
		CharGenCommon.PositionCharGenWin(class_window)
		script["MyChar"] = my_char
	_button_ids = _available_buttons(
		class_window,
		BG2_BUTTON_IDS if _bg2_style else BG1_BUTTON_IDS,
	)
	if not _button_ids:
		raise RuntimeError("BG1 class window has no reusable class buttons")

	races = GemRB.LoadTable("clsrcreq")
	race_name = GUICommon.GetRaceRowName(my_char)
	has_multi = False
	psion_added = False
	_class_rows = []
	for row_index in range(CommonTables.Classes.GetRowCount()):
		class_name = CommonTables.Classes.GetRowName(row_index)
		allowed = races.GetValue(class_name, race_name, GTV_INT)
		if CommonTables.Classes.GetValue(class_name, "MULTI"):
			has_multi = has_multi or allowed != 0
			if class_name not in DIRECT_MULTI_CLASSES:
				continue
		if class_name in PSION_CLASSES:
			if psion_added:
				continue
			psion_added = True
		if allowed == 2:
			GemRB.SetVar("MAGESCHOOL", 5)
		_class_rows.append((row_index, class_name, allowed))

	maximum = max(0, len(_class_rows) - len(_button_ids))
	if maximum:
		_create_scrollbar(class_window, _button_ids, maximum)
	GemRB.Log(
		2,
		"GemRBModClassChoice",
		"class rows=%d buttons=%d top=%d" % (
			len(_class_rows),
			len(_button_ids),
			GemRB.GetVar(TOP_INDEX_VAR) or 0,
		),
	)
	redraw()

	multi_button = class_window.GetControl(10)
	multi_button.SetText(GemRBModStrings.MULTI_CLASS)
	if not has_multi:
		multi_button.SetState(IE_GUI_BUTTON_DISABLED)

	if "SpecialistPress" in script:
		specialist_button = class_window.GetControl(11)
		specialist_button.SetText(GemRBModStrings.SPECIALIST_MAGE)
		if races.GetValue("MAGE", race_name, GTV_INT) == 0:
			specialist_button.SetState(IE_GUI_BUTTON_DISABLED)
		specialist_button.OnPress(script["SpecialistPress"])

	back_button = class_window.GetControl(14)
	back_button.SetText(GemRBModStrings.BACK)
	done_button = class_window.GetControl(0)
	done_button.SetText(GemRBModStrings.DONE)
	done_button.MakeDefault()
	done_button.SetState(IE_GUI_BUTTON_DISABLED)
	text_area = class_window.GetControl(13)
	text_area.SetText(GemRBModStrings.CHOOSE_CLASS)
	script["DoneButton"] = done_button
	script["TextAreaControl"] = text_area

	multi_button.OnPress(script["MultiClassPress"])
	done_button.OnPress(script["NextPress"])
	if _bg2_style:
		back_button.MakeEscape()
		back_button.OnPress(script["BackPress"])
		class_window.Focus()
	else:
		back_button.OnPress(lambda: CharGenCommon.back(class_window))
		class_window.ShowModal(MODAL_SHADOW_GRAY)
	if maximum:
		GemRB.SetVar(TOP_INDEX_VAR, maximum)
		redraw()
