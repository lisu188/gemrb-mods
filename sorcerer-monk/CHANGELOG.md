# Changelog

## 2.0

- Fixed `BACKUP` pointing at the Sorcerer/Monk/Cleric mod directory.
- Replaced hardcoded class ID 21 with free-ID discovery through `CLASSTEXT.2DA`.
- Corrected `CLASSTEXT.2DA` row order and optional Enhanced Edition fields.
- Corrected the modern `CLSKILLS.2DA` column mapping.
- Changed `CLASSES.2DA` saving throw table from `SAVEPRS` to multiclass-derived `*`.
- Changed `HPCLASS.2DA` from `HPMONK` to multiclass-derived `*`.
- Changed race restrictions to human-only.
- Combined Sorcerer/Mage and Monk item usability flags.
- Added `CLASS.IDS` registration.
- Added game, GemRB and required-table guards.
- Added duplicate protection and optional-file checks.
- Updated documentation and removed the stale version number from translated component text.
