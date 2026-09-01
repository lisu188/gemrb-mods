#!/usr/bin/env python3
"""Install/uninstall Sorcerer/Monk through the shared GemRB mod-core GUI layer."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "common" / "tools" / "install_guiscripts.py"
spec = importlib.util.spec_from_file_location("gemrb_mod_core_installer", CORE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == "__main__":
    module.main_for_handler(
        "SorcererMonkUI",
        ROOT / "sorcerer-monk" / "guiscripts" / "SorcererMonkUI.py",
    )
