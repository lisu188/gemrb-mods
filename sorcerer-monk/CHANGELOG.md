# Changelog

## 2.0

- Fixed `BACKUP` pointing at the Sorcerer/Monk/Cleric mod directory.
- Replaced hardcoded class ID 21 with free-ID discovery through the active GemRB class table.
- Preserved compatibility with released GemRB versions that use combined `CLASSES.2DA` rows.
- Added support for development GemRB versions that split class data across `CLASSTEXT.2DA`, `HPCLASS.2DA` and `CLSRCREQ.2DA`.
- Added explicit handling for the normalized GemRB and native Enhanced Edition `CLASSTEXT.2DA` formats.
- Added Tutu, Tutu_TotSC, BGEE and Classic Adventures to the supported game list.
- Corrected `CLSKILLS.2DA` mapping for the released and development layouts.
- Inherited `STARTXP`, `STARTXP2` and legacy `NO_PROF` values from the Sorcerer row where applicable.
- Changed saving throws and hit points to multiclass-derived values.
- Changed race restrictions to human-only.
- Combined Sorcerer/Mage and Monk item-usability flags.
- Added `CLASS.IDS` registration using the allocated class ID.
- Limited file-existence checks to genuinely optional or version-dependent tables.
- Restored explanatory comments and the legacy `SKILLS.2DA` fallback.
- Corrected newer split `THIEFSKL.2DA` Monk skill progression to 0 starting points and 10 points per Monk level.
- Corrected legacy `SKILLS.2DA` Monk skill progression to 10 starting points and 10 points per Monk level instead of the previous half-rate progression.
- Added regression tests for class registration, multiclass metadata, combined class features and gameplay restrictions.
- Removed the stale version number and redundant engine warning from translated component text.