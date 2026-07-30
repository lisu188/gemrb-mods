# Sorcerer/Monk multiclass for GemRB

This mod adds a true Sorcerer/Monk multiclass to Baldur's Gate II-family installations running through GemRB.

It does not work with the original Infinity Engine executable. Install it before creating the character and do not uninstall it while a save still contains Sorcerer/Monk characters.

## Supported games

- Baldur's Gate II: Shadows of Amn
- Throne of Bhaal
- BGT
- Baldur's Gate II: Enhanced Edition
- EET

All supported games must be launched through a current GemRB build.

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
- Adds the class to `CLASS.IDS` when available.
- Writes the current `CLASSTEXT.2DA` row layout.
- Corrects the shifted `CLSKILLS.2DA` fields.
- Uses multiclass save and hit-point handling instead of priest saves and full Monk hit points.
- Restricts the class to humans, matching the intersection of Sorcerer and Monk race rules.
- Combines Mage/Sorcerer and Monk item-usability restrictions.
- Protects optional table changes and repeated row additions.
- Rejects unsupported games and installations where GemRB metadata is unavailable.

## Gameplay model

- Sorcerer spontaneous arcane spell progression
- Monk fists and class abilities
- Lawful alignments only
- Human only
- Combined Sorcerer/Mage and Monk equipment restrictions
- No dual-classing
- Custom merged action bar

## Compatibility

Install this after GemRB has generated `gemrb_path.txt`. Install custom-class mods before starting a new game. Existing saves created without the class tables are not guaranteed to remain compatible after installing or uninstalling the mod.
