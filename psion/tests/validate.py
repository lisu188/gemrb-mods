#!/usr/bin/env python3
"""Compatibility entry point for the Psion validation suite."""

from validate_core import main as validate_core
from validate_high_tier import main as validate_high_tier


def main() -> None:
    validate_core()
    validate_high_tier()


if __name__ == "__main__":
    main()
