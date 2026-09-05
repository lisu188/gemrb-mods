#!/usr/bin/env python3
"""Controller safety/progress checks; these are not real-engine acceptance."""

from contextlib import redirect_stdout
from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_chargen_matrix as chargen


def control(*, disabled=False):
    return {"visible": True, "flags": chargen.VIEW_DISABLED if disabled else 0,
            "frame": {"x": 1, "y": 2, "w": 20, "h": 10},
            "center": [121, 207], "text": "Observed label"}


def snapshot(window_id=2, controls=None):
    return {"windows": {str(window_id): {"visible": True, "focused": True,
            "controls": controls or {"2": control()}}}, "area": "AR2600",
            "step": 3, "slot": 1, "game_type": "bgee"}


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.args = chargen.parse_args([
            "--session", self.directory.name, "--display", ":99",
            "--output", self.directory.name, "--class", "fighter", "--delay", "0"])
        self.controller = chargen.Controller(self.args)

    def test_click_uses_fresh_live_coordinates_without_shell_or_sync(self):
        self.controller.snapshot = Mock(return_value=snapshot())
        with patch.object(chargen.subprocess, "run") as run:
            self.controller.click(2, 2)
        self.assertEqual(run.call_args.args[0], ["xdotool", "mousemove", "121", "207", "click", "1"])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(self.controller.events[-1]["text"], "Observed label")

    def test_disabled_and_wrong_focus_never_click(self):
        for observed in (snapshot(2, {"2": control(disabled=True)}), snapshot(3)):
            self.controller.snapshot = Mock(return_value=observed)
            with patch.object(chargen.subprocess, "run") as run:
                with self.assertRaises(chargen.Stalled):
                    self.controller.click(2, 2)
                run.assert_not_called()

    def test_ambiguous_focus_is_rejected(self):
        observed = snapshot()
        observed["windows"]["3"] = observed["windows"]["2"]
        with self.assertRaises(chargen.Stalled):
            chargen.focused_window(observed)

    def test_class_scroll_uses_observed_rows_and_button_mapping(self):
        self.controller.query = Mock(return_value={
            "rows": [[0, "FIGHTER", 1], [1, "CIPHER", 1]], "buttons": [17], "offset": 1})
        self.controller.click = Mock()
        self.controller.choose_class()
        self.controller.click.assert_called_once_with(2, 1000, 4)

    def test_class_selection_does_not_click_old_window_after_transition(self):
        self.controller.query = Mock(return_value={
            "rows": [[0, "FIGHTER", 1]], "buttons": [17], "offset": 0})
        self.controller.snapshot = Mock(return_value=snapshot(22))
        self.controller.click = Mock()
        self.controller.choose_class()
        self.controller.click.assert_called_once_with(2, 17)

    def test_class_selection_confirms_if_done_is_required(self):
        self.controller.query = Mock(return_value={
            "rows": [[0, "FIGHTER", 1]], "buttons": [17], "offset": 0})
        self.controller.snapshot = Mock(return_value=snapshot(2, {"0": control()}))
        self.controller.click = Mock()
        self.controller.choose_class()
        self.assertEqual([call.args for call in self.controller.click.call_args_list], [(2, 17), (2, 0)])

    def test_disallowed_class_does_not_click(self):
        self.controller.query = Mock(return_value={
            "rows": [[0, "FIGHTER", 0]], "buttons": [17], "offset": 0})
        self.controller.click = Mock()
        with self.assertRaises(chargen.Stalled):
            self.controller.choose_class()
        self.controller.click.assert_not_called()

    def test_stuck_allocation_cannot_claim_success(self):
        self.controller.variable = Mock(return_value=2)
        self.controller.snapshot = Mock(return_value=snapshot(9, {"11": control()}))
        self.controller.click = Mock()
        for _ in range(24):
            self.controller.allocate(9, "ProfsPointsLeft", [11], 78)
        with self.assertRaisesRegex(chargen.Stalled, "Unable to allocate"):
            self.controller.allocate(9, "ProfsPointsLeft", [11], 78)
        self.assertNotIn((9, 0), [call.args for call in self.controller.click.call_args_list])

    def test_identity_mismatch_stops_before_save(self):
        self.controller.completed_steps.add(8)
        self.controller.expected = {"class": 2}
        self.controller.query = Mock(side_effect=[{"class": 19}, None])
        self.controller.screenshot = Mock(return_value="observed.png")
        self.controller.key = Mock()
        with self.assertRaisesRegex(chargen.Stalled, "identity mismatch"):
            self.controller.finish()
        self.controller.key.assert_not_called()

    def test_chapter_uses_observed_done_without_callback(self):
        chapter = {"id": 62, "focused": True, "controls": {"0": control()}}
        self.controller.query = Mock(return_value=chapter)
        self.controller.screenshot = Mock()
        with patch.object(chargen.subprocess, "run") as run:
            self.assertTrue(self.controller.dismiss_chapter())
        self.assertEqual(run.call_args.args[0], ["xdotool", "mousemove", "121", "207", "click", "1"])
        self.assertEqual(self.controller.events[-1]["group"], "GUICHAP")
        self.assertNotIn("EndTextScreen", self.controller.query.call_args.args[0])

    def test_late_chapter_is_dismissed_and_only_quicksave_slot_counts(self):
        self.controller.completed_steps.add(8)
        self.controller.expected = {"class": 2}
        self.controller.query = Mock(side_effect=[{"class": 2}, None, 1, [], [], [[1, "Quick-Save", "new"]]])
        self.controller.snapshot = Mock()
        self.controller.dismiss_chapter = Mock(side_effect=[True, False])
        self.controller.screenshot = Mock(return_value="observed.png")
        self.controller.key = Mock()
        with patch.object(chargen.time, "sleep"):
            self.controller.finish()
        self.assertEqual(self.controller.key.call_count, 2)
        save_queries = [call.args[0] for call in self.controller.query.call_args_list if "GetSaveGames" in call.args[0]]
        self.assertEqual(len(save_queries), 3)
        self.assertTrue(all("if s.GetSaveID() == 1" in query for query in save_queries))

    def test_tob_observes_slot_four_without_accepting_other_saves(self):
        self.controller.completed_steps.add(8)
        self.controller.expected = {"class": 2}
        self.controller.query = Mock(side_effect=[{"class": 2}, None, 4, [], [[4, "Quick-Save-TOB", "new"]]])
        self.controller.snapshot = Mock()
        self.controller.dismiss_chapter = Mock(return_value=False)
        self.controller.screenshot = Mock(return_value="observed.png")
        self.controller.key = Mock()
        self.controller.finish()
        expressions = [call.args[0] for call in self.controller.query.call_args_list]
        self.assertIn("4 if __import__('GameCheck').IsTOB() else 1", expressions)
        self.assertTrue(all("if s.GetSaveID() == 4" in query for query in expressions if "GetSaveGames" in query))

    def test_preexisting_gameplay_cannot_be_reported_complete(self):
        with self.assertRaisesRegex(chargen.Stalled, "already active"):
            self.controller.finish()

    def test_staged_run_is_not_complete_and_preserves_prior_output(self):
        self.controller.initialize = Mock(return_value=snapshot())
        self.controller.advance = Mock()
        with redirect_stdout(io.StringIO()):
            self.controller.run()
        first_report = self.controller.output / "controller-report.json"
        self.assertEqual(json.loads(first_report.read_text())["status"], "staged")
        second = chargen.Controller(self.args)
        self.assertNotEqual(second.output, self.controller.output)
        self.assertTrue(first_report.exists())

    def test_mailbox_query_records_error_and_stops(self):
        def request(*args):
            print(json.dumps({"error": "engine observation failed"}))
            return 1
        with patch.object(chargen.live_console, "request", side_effect=request):
            with self.assertRaisesRegex(chargen.Stalled, "engine observation failed"):
                self.controller.query("GemRB.GetVar('Slot')")
        self.assertEqual(self.controller.events[-1]["result"]["error"], "engine observation failed")

    def test_nonfinite_time_limit_is_rejected(self):
        with redirect_stdout(io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                chargen.parse_args(["--session", self.directory.name, "--display", ":99",
                                    "--output", self.directory.name, "--class", "fighter", "--timeout", "nan"])

    def test_bare_engine_runtime_error_stops_before_mailbox(self):
        self.args.engine_log = Path(self.directory.name) / "engine.log"
        self.args.engine_log.write_text("[GUIScript/ERROR]: Runtime Error: no table")
        self.controller.query = Mock()
        with self.assertRaisesRegex(chargen.Stalled, "GUI runtime error"):
            self.controller.snapshot()
        self.controller.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
