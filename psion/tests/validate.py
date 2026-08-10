#!/usr/bin/env python3
"""Compatibility entry point for Psion core, focus/feat, and skill validation."""

from validate_core import main as validate_core
from validate_focus_feats import main as validate_focus_feats
from validate_skills import main as validate_skills


if __name__ == "__main__":
    validate_core()
    validate_focus_feats()
    validate_skills()
