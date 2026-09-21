#!/usr/bin/env python3
"""Exercise real rest-handler functions against strict party-slot boundaries."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RestPartyBoundsTests(unittest.TestCase):
    def test_handlers_visit_only_existing_party_members(self):
        for relative in ("psion/guiscripts/Psionics.py", "cipher/guiscripts/Cipher.py"):
            path = ROOT / relative
            tree = ast.parse(path.read_text())
            # Execute the actual definition/alias order, including extension
            # wrappers. Testing only the first definition misses later loops.
            functions = [node for node in tree.body
                         if (isinstance(node, ast.FunctionDef) and node.name in ("restore_party", "sync_psicrystal_party"))
                         or (isinstance(node, ast.Assign)
                             and any(isinstance(target, ast.Name) and target.id == "_base_restore_party"
                                     for target in node.targets))]
            for size in (0, 1, 2, 6, 8):
                with self.subTest(handler=relative, party_size=size):
                    visited, invalid, canceled, restored = [], [], [], []

                    def check(actor, *_):
                        visited.append(actor)
                        if not 1 <= actor <= size:
                            invalid.append(actor)
                            raise RuntimeError("Actor not found")
                        return True

                    def restore(actor, *_):
                        check(actor)
                        restored.append(actor)

                    def companion(actor, mode):
                        check(actor)
                        self.assertEqual(mode, 3, "rest must not create or resurrect a companion")
                        return None

                    def reset_use(actor, used):
                        check(actor)
                        self.assertIs(used, False)

                    namespace = {"GemRB": SimpleNamespace(GetPartySize=lambda: size, ManageCompanion=companion),
                                 "cancel_pending": lambda: canceled.append(True),
                                 "STARTING_FOCUS": 20, "is_cipher": check,
                                 "set_focus": restore, "ensure_pool": restore,
                                 "is_psion": check, "_write_psicrystal_used": reset_use,
                                 "psicrystal_companion": companion, "_scale_psicrystal": check}
                    for name in ("ensure_focus", "_ensure_power_selector_known", "sync_skill_points",
                                 "_ensure_skill_selector_known", "_sync_center_action", "_sync_psicrystal_selector"):
                        namespace[name] = check
                    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
                    namespace["restore_party"]()
                    self.assertEqual(invalid, [], "caught exceptions must not hide missing actor queries")
                    self.assertEqual(set(visited), set(range(1, size + 1)))
                    self.assertEqual(restored, list(range(1, size + 1)))
                    self.assertEqual(canceled, [True])


if __name__ == "__main__":
    unittest.main()
