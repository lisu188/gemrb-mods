# Sorcerer/Monk multiclass for GemRB

This mod adds a true Sorcerer/Monk multiclass to Infinity Engine games running through GemRB.

Install it before creating the character and do not uninstall it while a save still contains Sorcerer/Monk characters.

## Supported games

- Tutu and Tutu_TotSC
- Baldur's Gate: Enhanced Edition
- Classic Adventures
- Baldur's Gate II: Shadows of Amn
- Throne of Bhaal
- BGT
- Baldur's Gate II: Enhanced Edition
- EET

Original BG1 and TotSC are not included because they do not provide the Sorcerer and Monk base classes. All supported games must be launched through GemRB.

## Installation

1. Run GemRB once against the target game installation.
2. Copy the `sorcerer-monk` directory into the game directory.
3. Run:

```text
weidu sorcerer-monk/setup-sorcerer-monk.tp2
```

Use WeiDU 247 or newer.

## Version 2.0 corrections

- Corrects the backup directory.
- Allocates a free class identifier instead of hardcoding class ID 21.
- Supports the combined class table used by released GemRB versions and the split class tables used by development builds.
- Handles both normalized GemRB and native Enhanced Edition `CLASSTEXT.2DA` layouts when the split tables are present.
- Handles the released and development `CLSKILLS.2DA` layouts and inherits campaign-specific starting experience from the Sorcerer row.
- Uses multiclass save and hit-point handling instead of priest saves and full Monk hit points.
- Restricts the class to humans, matching the intersection of Sorcerer and Monk race rules.
- Combines Mage/Sorcerer and Monk item-usability restrictions.
- Adds the allocated class identifier to `CLASS.IDS`.
- Avoids modifying ToB starting-equipment and HLA tables in games where those tables are absent.
- Supports both the older `SKILLS.2DA` layout and the newer `THIEFSCL.2DA`/`THIEFSKL.2DA` pair.
- Matches Monk skill-point progression in both skill-table layouts: legacy `10/10` and current split `0/10`.

## Gameplay model

- Sorcerer spontaneous arcane spell progression
- Monk fists and class abilities
- Lawful alignments only
- Human only
- Combined Sorcerer/Mage and Monk equipment restrictions
- No dual-classing
- Custom merged action bar

## Compatibility notes

The installer has two documented class-table branches: the combined format used by released GemRB versions and the split format used by development builds. Split `CLASSTEXT.2DA` is accepted in either its normalized six-column form or the native EE ten-column form.

Install custom-class mods before starting a new game. Existing saves created without the class tables are not guaranteed to remain compatible after installing or uninstalling the mod.
