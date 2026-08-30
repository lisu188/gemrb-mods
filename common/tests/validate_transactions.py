#!/usr/bin/env python3
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "common" / "guiscripts" / "Transactions.py"

spec = importlib.util.spec_from_file_location("transactions_regression", PATH)
transactions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transactions)

calls = []
assert transactions.begin("X", 1, ("A", 5), lambda: True)
assert transactions.begin("X", 1, ("A", 5), lambda: True, lambda: calls.append("A") or True)
assert calls == ["A"]
assert transactions.begin("X", 1, ("A", 5), lambda: True, lambda: calls.append("duplicate") or True)
assert calls == ["A"]

assert transactions.begin("X", 1, ("B", 2), lambda: True)
assert transactions.begin("X", 1, ("B", 2), lambda: True, lambda: calls.append("B") or True)
assert calls == ["A", "B"]

transactions.cancel("X", 1)
assert transactions.begin("X", 1, ("A", 5), lambda: True)
assert transactions.begin("X", 1, ("A", 5), lambda: True, lambda: False) is False
assert transactions.begin("X", 1, ("A", 5), lambda: True)

print("Repeated GemRB callback transaction validation passed")
