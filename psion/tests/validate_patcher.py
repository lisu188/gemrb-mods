#!/usr/bin/env python3
"""Compatibility entry point for shared GemRB GUI lifecycle validation."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "common" / "tests" / "validate.py"


def main():
    spec = importlib.util.spec_from_file_location("shared_gui_validation", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.test_gui_lifecycle()
    print("Psion shared GUI lifecycle validation passed")


if __name__ == "__main__":
    main()
