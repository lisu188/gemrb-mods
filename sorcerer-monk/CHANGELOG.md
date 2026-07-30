# Changelog

## 2.0

- Fixed `BACKUP` pointing at the Sorcerer/Monk/Cleric mod directory.
- Replaced hardcoded class ID 21 with free-ID discovery through the active GemRB class table layout.
- Preserved compatibility with released GemRB versions that use the combined `CLASSES.2DA` format.
- Added support for the split `CLASSTEXT.2DA`, `HPCLASS.2DA` and `CLSRCREQ.2DA` development layout.
- Documented and supported both normalized GemRB and native Enhanced Edition `CLASSTEXT.2DA` columns.
- Added Tutu, Tutu_TotSC, BGEE and Classic Adventures to the supported game list.
- Added compact BG1-style proficiency-table handling.
- Corrected `CLSKILLS.2DA` mapping for compact, released BG2 and newer/EE layouts.
- Inherited `STARTXP`, `STARTXP2` and legacy `NO_PROF` values from the Sorcerer row where applicable.
- Changed saving throws and hit points to multiclass-derived values.
- Changed race restrictions to human-only.
- Combined Sorcerer/Mage and Monk item-usability flags.
- Added `CLASS.IDS` registration using the allocated class ID.
- Limited file-existence checks to genuinely optional game tables and restored explanatory comments.
- Restored the legacy `SKILLS.2DA` fallback for older GemRB versions.
- Removed the stale version number and redundant engine warning from translated component text.
