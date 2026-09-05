#!/usr/bin/env python3
"""Synthetic safety tests for the optional local acceptance console."""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"GemRB": SimpleNamespace()}):
        spec.loader.exec_module(module)
    return module


HOST = load("live_console_test", ROOT / "tools" / "live_console.py")
ENGINE = load("LiveControl_test", ROOT / "acceptance" / "LiveControl.py")


@unittest.skipUnless(hasattr(os, "getuid"), "local X11 acceptance console requires POSIX ownership")
class PrivateSessionTests(unittest.TestCase):
    def test_both_ends_require_private_owned_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = root / "session"
            session.mkdir(mode=0o700)
            link = root / "link"
            link.symlink_to(session, target_is_directory=True)
            ordinary_file = root / "file"
            ordinary_file.touch(mode=0o600)
            for module in (HOST, ENGINE):
                with self.subTest(module=module.__name__):
                    self.assertEqual(module.private_session(session), session.resolve())
                    for invalid in (link, ordinary_file):
                        with self.assertRaises(RuntimeError):
                            module.private_session(invalid)
                    for mode in (0o755, 0o770, 0o777):
                        session.chmod(mode)
                        with self.assertRaises(RuntimeError):
                            module.private_session(session)
                    session.chmod(0o700)
                    with patch.object(module.os, "getuid", return_value=os.getuid() + 1):
                        with self.assertRaises(RuntimeError):
                            module.private_session(session)

    def test_prepare_rejects_existing_shared_directory_before_gui_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = root / "session"
            session.mkdir(mode=0o755)
            with self.assertRaises(RuntimeError):
                HOST.prepare(root / "nonexistent-gui", session)
            self.assertEqual(list(session.iterdir()), [])

    def test_request_rejects_shared_directory_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Path(folder)
            session.chmod(0o777)
            with self.assertRaises(RuntimeError):
                HOST.request(session, "None", 0.1)
            self.assertEqual(list(session.iterdir()), [])

    def test_engine_does_not_start_timer_for_shared_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Path(folder)
            session.chmod(0o755)
            timer_calls = []
            with patch.dict(os.environ, {"GEMRB_ACCEPTANCE_SESSION": folder}), \
                    patch.object(ENGINE, "_session", None), \
                    patch.object(ENGINE, "GemRB", SimpleNamespace(SetTimer=lambda *args: timer_calls.append(args))):
                with self.assertRaises(RuntimeError):
                    ENGINE.start()
            self.assertEqual(timer_calls, [])


if __name__ == "__main__":
    unittest.main()
