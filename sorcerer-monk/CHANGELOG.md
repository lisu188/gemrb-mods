# Changelog

## 2.0

- Fixed `BACKUP` pointing at the Sorcerer/Monk/Cleric mod directory.
- Replaced hardcoded class ID 21 with an ID derived from the Sorcerer/Monk `CLSKILLS.2DA` row index.
- Added explicit checks for conflicting class IDs and GemRB's below-32 class-mask limit.
- Preserved compatibility with released GemRB versions that use combined `CLASSES.2DA` rows.
- Added support for development GemRB versions that split class data across `CLASSTEXT.2DA`, `HPCLASS.2DA` and `CLSRCREQ.2DA`.
- Added explicit handling for the normalized GemRB and native Enhanced Edition `CLASSTEXT.2DA` formats.
- Added Tutu, Tutu_TotSC, BGEE and Classic Adventures to the supported game list.
- Corrected `CLSKILLS.2DA` mapping for the released and development layouts.
- Inherited `STARTXP` and `STARTXP2` values from the Sorcerer row.
- Corrected the legacy non-proficiency penalty to follow Monk instead of Sorcerer.
- Changed saving throws and hit points to multiclass-derived values.
- Changed race restrictions to human-only.
- Combined Sorcerer/Mage and Monk item-usability flags.
- Added `CLASS.IDS` registration using the runtime-safe class ID.
- Limited file-existence checks to genuinely optional or version-dependent tables.
- Restored explanatory comments and the legacy `SKILLS.2DA` fallback.
- Corrected newer split `THIEFSKL.2DA` Monk skill progression to 0 starting points and 10 points per Monk level.
- Corrected legacy `SKILLS.2DA` Monk skill progression to 10 starting points and 10 points per Monk level instead of the previous half-rate progression.
- Corrected proficiency progression to the Monk/fastest-component rate of one point every four levels.
- Added the component-compatible starting-gold row.
- Added a two-slot `NUMWSLOT.2DA` row instead of falling through to the table default.
- Preserved Monk fist APR and combat proficiency behavior through `CLSWPBON.2DA` where available.
- Prevented BGEE character generation from giving the multiclass the default quarterstaff.
- Reworked the custom `FISTWEAP.2DA` row around GemRB's rounded multiclass-level lookup so it never grants a tier before the Monk component reaches it and still reaches the top fist under the normal XP cap.
- Added regression tests for class registration, multiclass metadata, combined class features, progression and character-generation defaults.
- Added WeiDU syntax validation to CI.
- Removed the stale version number and redundant engine warning from translated component text.
