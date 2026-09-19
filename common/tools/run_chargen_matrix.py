#!/usr/bin/env python3
"""Drive one real BGEE/BG2EE chargen flow with observed controls and mouse input.

Start on the character-generation overview in a disposable session instrumented
by live_console.py. This controller never invokes gameplay callbacks or changes
actor/GUI stats through the mailbox. Engine-log classification and the wider
gameplay acceptance scenarios remain separate gates.
"""

from contextlib import redirect_stdout
from pathlib import Path
import argparse
import io
import json
import math
import os
import subprocess
import time
import uuid

import live_console

CLASSES = {"fighter": "FIGHTER", "cipher": "CIPHER", "sorcerer-monk": "SORCERER_MONK"}
DISCIPLINES = ("seer", "shaper", "kineticist", "egoist", "nomad", "telepath")
CLASSES.update({"psion-" + name: "PSION_" + name.upper() for name in DISCIPLINES})
WINDOW_CONTROLS = {
    0: list(range(17)), 1: [0, 2, 3, 6], 2: [0, *range(2, 19), 1000],
    3: [0, *range(2, 11)], 4: [0, 2, *range(16, 28)], 5: [0, 2, 3],
    6: [0, 11, 13, 15, 17, 27, 29, 26], 7: [0, *range(2, 27), 30, 43],
    8: [0, *range(2, 9)], 9: [0, *range(11, 27), 78], 11: [0, 1, 2, 3],
    13: [0, 2, 3, 4, 5], 19: [0, 45], 22: [1, 2, 3, 4, 7, 9, 10],
}
VIEW_DISABLED = 1 << 29


class Stalled(RuntimeError):
    pass


def usable(control):
    return bool(control and control.get("visible") and not control["flags"] & VIEW_DISABLED
                and control["frame"]["w"] > 0 and control["frame"]["h"] > 0)


def focused_window(snapshot):
    visible = [(int(key), value) for key, value in snapshot["windows"].items() if value["visible"]]
    focused = [(key, value) for key, value in visible if value["focused"]]
    if len(focused) == 1:
        return focused[0]
    dialogs = [(key, value) for key, value in visible if key != 0]
    if len(dialogs) == 1:
        return dialogs[0]
    if len(visible) == 1:
        return visible[0]
    raise Stalled("No unambiguous focused chargen window; inspect the screenshot and mailbox snapshot")


class Controller:
    def __init__(self, args):
        self.args = args
        self.output = args.output.resolve() / (str(time.time_ns()) + "-" + uuid.uuid4().hex[:8])
        self.output.mkdir(parents=True, exist_ok=True)
        self.environment = dict(os.environ, DISPLAY=args.display)
        if args.xauthority:
            self.environment["XAUTHORITY"] = str(args.xauthority.resolve())
        self.events = []
        self.last_window = None
        self.completed_steps = set()
        self.scrolls = {}
        self.rerolls = 0
        self.expected = None

    def record(self, kind, **details):
        self.events.append(dict(kind=kind, time=time.time(), **details))
        (self.output / "actions.json").write_text(json.dumps(self.events, indent=2) + "\n")

    def query(self, expression):
        captured = io.StringIO()
        with redirect_stdout(captured):
            status = live_console.request(self.args.session, expression, self.args.timeout)
        result = json.loads(captured.getvalue())
        self.record("observation", expression=expression, result=result)
        if status or "error" in result:
            raise Stalled(result.get("error", "mailbox request failed"))
        return result["value"]

    def snapshot(self):
        if self.args.engine_log and self.args.engine_log.exists():
            log = self.args.engine_log.read_text(errors="replace")
            if any(marker in log for marker in ("Traceback (most recent call last):", "[GUIScript/ERROR]: Runtime Error:")):
                raise Stalled("Engine log contains a traceback or GUI runtime error; resolve the failure before advancing")
        return self.query(
            "{'game_type': GemRB.GameType, 'step': GemRB.GetVar('Step'), "
            "'slot': GemRB.GetVar('Slot'), 'area': GemRB.GetCurrentArea(), 'windows': {"
            "i: dict(__import__('LiveControl').controls('GUICG', i, ids), focused=w.HasFocus) "
            f"for i, ids in {WINDOW_CONTROLS!r}.items() "
            "if (w := GemRB.GetView('GUICG', i)) and w.IsVisible()}}"
        )

    def screenshot(self, label):
        path = self.output / f"{len(self.events):04d}-{label}.png"
        subprocess.run(["import", "-display", self.args.display, "-window", "root", str(path)],
                       env=self.environment, check=True, timeout=20)
        self.record("screenshot", path=str(path))
        return str(path)

    def click(self, window_id, control_id, button=1):
        snapshot = self.snapshot()
        active_id, window = focused_window(snapshot)
        if active_id != window_id:
            raise Stalled(f"Expected focused window {window_id}, found {active_id}")
        control = window["controls"].get(str(control_id))
        if not usable(control):
            raise Stalled(f"Control {window_id}/{control_id} is missing, hidden or disabled")
        self.mouse_control("GUICG", window_id, control_id, control, button)

    def mouse_control(self, group, window_id, control_id, control, button=1):
        x, y = control["center"]
        # --sync can wait forever when scrolling the same stationary control.
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", str(button)],
                       env=self.environment, check=True, timeout=10)
        self.record("mouse", group=group, window=window_id, control=control_id, button=button,
                    text=control["text"], center=[x, y])
        time.sleep(self.args.delay)

    def dismiss_chapter(self):
        chapter = self.query(
            "(lambda w: dict(__import__('LiveControl').controls('GUICHAP', w.ID, [0]), "
            "id=w.ID, focused=w.HasFocus) if w and w.IsVisible() else None)"
            "(__import__('TextScreen').TextScreen)"
        )
        if not chapter:
            return False
        if not chapter["focused"] or not usable(chapter["controls"].get("0")):
            raise Stalled("Chapter screen is not ready for its actual Done button")
        self.screenshot("chapter-screen")
        self.mouse_control("GUICHAP", chapter["id"], 0, chapter["controls"]["0"])
        return True

    def key(self, *keys):
        subprocess.run(["xdotool", "key", "--clearmodifiers", *keys],
                       env=self.environment, check=True, timeout=10)
        self.record("keyboard", keys=list(keys))
        time.sleep(self.args.delay)

    def variable(self, name):
        return self.query(f"GemRB.GetVar({name!r})")

    def initialize(self):
        snapshot = self.snapshot()
        if snapshot["game_type"] not in ("bgee", "bg2ee"):
            raise Stalled("This staged controller supports the actual BGEE/BG2EE bg2 GUI flow only")
        row = CLASSES[self.args.class_name]
        self.expected = self.query(
            "{'row': " + repr(row) + ", 'class': __import__('CommonTables').ClassText.GetValue("
            + repr(row) + ", 'CLASSID'), 'kit': 0, 'race': 1, 'alignment': 18, 'sex': 1}"
        )
        if not isinstance(self.expected["class"], int) or self.expected["class"] < 1:
            raise Stalled(f"Installed class table does not define {row}")
        self.record("independent_identity_oracle", expected=self.expected)
        return snapshot

    def choose_class(self):
        rows = self.query(
            "{'rows': __import__('GemRBModClassChoice')._class_rows, "
            "'buttons': __import__('GemRBModClassChoice')._button_ids, "
            "'offset': GemRB.GetVar('GemRBModClassTopIndex')}"
        )
        wanted = "PSION_SEER" if self.args.class_name.startswith("psion-") else CLASSES[self.args.class_name]
        matches = [index for index, row in enumerate(rows["rows"]) if row[1] == wanted]
        if len(matches) != 1 or rows["rows"][matches[0]][2] == 0:
            raise Stalled(f"Class chooser does not expose an allowed {wanted}")
        index, offset = matches[0], rows["offset"] or 0
        if not offset <= index < offset + len(rows["buttons"]):
            self.scrolls[2] = self.scrolls.get(2, 0) + 1
            if self.scrolls[2] > len(rows["rows"]) + 2:
                raise Stalled("Class chooser did not scroll to the requested row")
            self.click(2, 1000, 4 if index < offset else 5)
        else:
            self.click(2, rows["buttons"][index - offset])
            # Some installed chooser variants select first, then require Done.
            active_id, window = focused_window(self.snapshot())
            if active_id == 2 and usable(window["controls"].get("0")):
                self.click(2, 0)

    def allocate(self, window_id, variable, buttons, scrollbar):
        before = self.variable(variable)
        if before == 0:
            self.click(window_id, 0)
            return
        _, window = focused_window(self.snapshot())
        for button in buttons:
            if usable(window["controls"].get(str(button))):
                self.click(window_id, button)
                after = self.variable(variable)
                if isinstance(after, int) and after < before:
                    return
        self.scrolls[window_id] = self.scrolls.get(window_id, 0) + 1
        if self.scrolls[window_id] > 24:
            raise Stalled(f"Unable to allocate remaining {variable} through enabled controls")
        self.click(window_id, scrollbar, 5)

    def abilities(self):
        values = self.query("[GemRB.GetVar('Ability ' + str(i)) for i in range(6)]")
        if sum(values) < self.args.minimum_roll:
            self.rerolls += 1
            if self.rerolls > 100:
                raise Stalled("Minimum requested roll was not reached after 100 real rerolls")
            self.click(4, 2)
            return
        if self.args.min_intelligence and values[3] < self.args.min_intelligence:
            if self.variable("Ability -1"):
                self.click(4, 22)
                if self.variable("Ability 3") <= values[3]:
                    raise Stalled("Installed rules disallow the requested Intelligence score")
                return
            for donor in (5, 4, 0, 1, 2):
                if values[donor] <= 8:
                    continue
                self.click(4, donor * 2 + 17)
                if self.variable("Ability -1"):
                    return
            raise Stalled("No legal ability points can be reassigned to Intelligence")
        if self.variable("Ability -1") != 0:
            raise Stalled("Unassigned ability points remain; use the real plus/minus controls")
        self.record("rolled_abilities", values=values)
        self.click(4, 0)

    def spells(self):
        selection = self.query(
            "(lambda m: {'level': m.SpellLevel, 'points': m.SpellsSelectPointsLeft[m.SpellLevel], "
            "'row': m.RowIndex(), 'start': m.SpellStart, 'count': m.ButtonCount + m.ExtraSpellButtons(), "
            "'spells': m.Spells[m.SpellLevel], 'selected': m.MemoBook if m.Memorization else m.SpellBook})"
            "(__import__('LUSpellSelection'))"
        )
        if selection["points"] == 0:
            self.click(7, 0)
            return
        for slot in range(selection["count"]):
            index = selection["row"] + slot
            if index >= len(selection["spells"]):
                break
            if selection["spells"][index][1] and not selection["selected"][index]:
                self.click(7, selection["start"] + slot)
                return
        raise Stalled("No unselected legal spell is visible; inspect or scroll the actual spell selector")

    def advance(self, snapshot):
        window_id, window = focused_window(snapshot)
        if window_id != self.last_window:
            self.screenshot(f"window-{window_id}")
            self.last_window = window_id
        if window_id == 0:
            enabled = [i for i in range(9) if usable(window["controls"].get(str(i)))]
            if len(enabled) != 1:
                raise Stalled(f"Overview has ambiguous enabled steps: {enabled}")
            self.completed_steps.add(enabled[0])
            self.click(0, enabled[0])
        elif window_id == 1:
            self.click(1, 2)
            self.click(1, 0)
        elif window_id == 8:
            row = self.query("__import__('CommonTables').Races.GetRowIndex('HUMAN')")
            self.click(8, row + 2)
            self.click(8, 0)
        elif window_id == 2:
            self.choose_class()
        elif window_id == 22:
            button = (1, 2, 3, 4, 9, 10)[DISCIPLINES.index(self.args.class_name[6:])] if self.args.class_name.startswith("psion-") else 1
            self.click(22, button)
            self.screenshot("selected-" + self.args.class_name)
            self.click(22, 7)
        elif window_id == 3:
            row = self.query("__import__('CommonTables').Aligns.GetRowIndex('LAWFUL_NEUTRAL')")
            if not isinstance(row, int) or row < 0:
                raise Stalled("Installed alignment table has no lawful-neutral choice")
            self.click(3, row + 2)
            self.click(3, 0)
        elif window_id == 4:
            self.abilities()
        elif window_id == 6:
            self.allocate(6, "SkillPointsLeft", [11, 13, 15, 17, 27, 29], 26)
        elif window_id == 7:
            self.spells()
        elif window_id == 9:
            self.allocate(9, "ProfsPointsLeft", list(range(11, 27, 2)), 78)
        elif window_id == 5:
            self.click(5, 2)
            self.key("ctrl+a")
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", "20", "--", self.args.name],
                           env=self.environment, check=True, timeout=20)
            self.record("name", value=self.args.name)
            time.sleep(self.args.delay)
            self.click(5, 0)
        elif window_id in (11, 13, 19):
            self.click(window_id, 0)  # current portrait, colours and default soundset
        else:
            raise Stalled(f"Window {window_id} requires manual inspection")

    def finish(self):
        if 8 not in self.completed_steps:
            raise Stalled("Gameplay was already active; this invocation did not complete chargen")
        actual = self.query(
            "(lambda pc, s: {'row': __import__('GUICommon').GetClassRowName(pc), "
            "'class': GemRB.GetPlayerStat(pc, s.IE_CLASS), 'kit': GemRB.GetPlayerStat(pc, s.IE_KIT), "
            "'race': GemRB.GetPlayerStat(pc, s.IE_RACE), 'alignment': GemRB.GetPlayerStat(pc, s.IE_ALIGNMENT), "
            "'sex': GemRB.GetPlayerStat(pc, s.IE_SEX)})"
            "(GemRB.GetVar('Slot'), __import__('ie_stats'))"
        )
        screenshot = self.screenshot("gameplay-identity")
        checkpoint_id = "chargen." + self.args.class_name.replace("psion-", "psion.") + ".identity"
        self.query("__import__('GemRBAcceptance').checkpoint(" + repr(checkpoint_id) + ", "
                   + repr(actual) + ", " + repr(self.expected) + ", "
                   + repr({"oracle": "installed class table before UI selection; human lawful-neutral male", "screenshot": screenshot}) + ")")
        if actual != self.expected:
            raise Stalled(f"Character identity mismatch: {actual!r} != {self.expected!r}")
        # Autosaves can finish asynchronously after chargen. Only the native
        # campaign's native quicksave slot is evidence for the key we send.
        # This matches GUISAVE.QuickSavePressed (ToB uses slot 4).
        save_id = self.query("4 if __import__('GameCheck').IsTOB() else 1")
        if save_id not in (1, 4):
            raise Stalled("Unexpected native quicksave slot")
        saves_query = f"[(s.GetSaveID(), s.GetName(), s.GetDate()) for s in GemRB.GetSaveGames() if s.GetSaveID() == {save_id}]"
        before = self.query(saves_query)
        self.key(self.args.quicksave_key)
        deadline = time.monotonic() + self.args.timeout
        while time.monotonic() < deadline:
            self.snapshot()  # re-check engine errors during asynchronous entry
            if self.dismiss_chapter():
                self.key(self.args.quicksave_key)
            after = self.query(saves_query)
            if after != before:
                self.record("save_observed", before=before, after=after)
                self.screenshot("after-quicksave")
                return
            time.sleep(0.5)
        raise Stalled("Quicksave key produced no observable new/updated save; inspect cutscene/dialog/save restrictions")

    def run(self):
        status = "blocked"
        detail = None
        try:
            snapshot = self.initialize()
            if self.args.mode == "inspect":
                self.screenshot("inspection")
                print(json.dumps(snapshot, indent=2))
                status = "inspected"
                return
            if self.args.mode == "next" and not snapshot["windows"]:
                raise Stalled("Staged mode cannot certify gameplay; run --mode all from chargen")
            for _ in range(self.args.max_actions):
                if not snapshot["windows"] and snapshot["area"]:
                    if self.dismiss_chapter():
                        snapshot = self.snapshot()
                        continue
                    self.finish()
                    status = "ui-complete"
                    return
                self.advance(snapshot)
                if self.args.mode == "next":
                    status = "staged"
                    return
                snapshot = self.snapshot()
            raise Stalled("Action limit reached before completing character creation")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            detail = str(error)
            try:
                self.screenshot("blocked")
            except (OSError, subprocess.SubprocessError):
                pass
            raise
        finally:
            report = {"status": status, "detail": detail, "class": self.args.class_name,
                      "completed_overview_steps": sorted(self.completed_steps), "expected_identity": self.expected,
                      "scope": "UI progression, final identity and observed quicksave; separate engine-log/gameplay acceptance required"}
            (self.output / "controller-report.json").write_text(json.dumps(report, indent=2) + "\n")
            print("Controller evidence: " + str(self.output))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--display", required=True)
    parser.add_argument("--xauthority", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--class", dest="class_name", choices=tuple(CLASSES), required=True)
    parser.add_argument("--name", default="Acceptance")
    parser.add_argument("--mode", choices=("all", "next", "inspect"), default="next")
    parser.add_argument("--engine-log", type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--max-actions", type=int, default=500)
    parser.add_argument("--minimum-roll", type=int, default=0)
    parser.add_argument("--min-intelligence", type=int, choices=range(3, 19))
    parser.add_argument("--quicksave-key", default="q")
    args = parser.parse_args(argv)
    if (not math.isfinite(args.timeout) or not math.isfinite(args.delay)
            or args.timeout <= 0 or args.delay < 0 or args.max_actions < 1
            or not 0 <= args.minimum_roll <= 108):
        parser.error("timeout/actions must be positive; delay nonnegative; minimum roll between 0 and 108")
    return args


if __name__ == "__main__":
    try:
        Controller(parse_args()).run()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error))
        raise SystemExit(1)
