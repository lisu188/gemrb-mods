#!/usr/bin/env python3
"""Compatibility entry point for the complete Psion validation suite."""

from validate_core import main as validate_core
from validate_high_tier import main as validate_high_tier
from validate_focus_feats import main as validate_focus_feats
from validate_skills import main as validate_skills
from validate_power_learning import main as validate_power_learning
from validate_psicrystal import main as validate_psicrystal


def main() -> None:
    validate_core()
    validate_high_tier()
    validate_focus_feats()
    validate_skills()
    validate_power_learning()
    validate_psicrystal()


if __name__ == "__main__":
    main()
