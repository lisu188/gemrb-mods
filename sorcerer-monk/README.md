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

Sorcerer/Monk and the legacy Sorcerer/Monk/Cleric mod are intentionally mutually exclusive. Uninstall one before installing the other.

## Version 2.0 corrections

Version 2.0 is a correctness pass over the 1.9 installer. The user-visible results:

- The class ID is derived from the live `CLSKILLS.2DA` row instead of being hardcoded, and the
  installer refuses to build a class whose metadata GemRB would misread at runtime.
- Ambiguous class metadata is rejected rather than worked around: duplicate `SORCERER_MONK` rows,
  `CLASS.IDS` conflicts in either direction, a `FISTWEAP.2DA` row already claiming the allocated
  numeric ID, Sorcerer or Monk moved off GemRB IDs 19 and 20, a `QSLOTS.2DA` out of step with the
  class tables, and partial `XPCAP.2DA` component entries all stop the install before any table is
  modified.
- Released, development and native Enhanced Edition class-table layouts are all supported, and an
  unrecognised layout stops the install instead of producing a broken class.
- Campaign-specific values are inherited from the live Sorcerer and Monk rows rather than assumed:
  experience cap (including the conventional uncapped `-1`), starting experience, starting gold,
  avatar prefix, non-proficiency penalty and the Monk fist progression.
- Multiclass saving throws and hit points, human-only race rules, lawful alignments, combined
  ability prerequisites (DEX/CON/INT/WIS/CHA 9, no STR minimum) and combined Sorcerer/Mage plus
  Monk item restrictions.
- Monk skill and proficiency progression in both the legacy `SKILLS.2DA` and the current
  `THIEFSCL.2DA`/`THIEFSKL.2DA` layouts.
- Two quick-weapon slots, an unarmed start in BGEE, and Monk fist APR through `CLSWPBON.2DA`.
- A combined high-level-ability table generated from the game's own Sorcerer and Monk HLA lists.
- Simultaneous installation with Sorcerer/Monk/Cleric is rejected, while the historical
  `sorcerer-monk-cleric/backup` location is kept so 1.9 installations stay reinstallable.

See `CHANGELOG.md` for the itemised list.

## Gameplay model

- Sorcerer spontaneous arcane spell progression
- Monk fists and class abilities
- Lawful alignments only
- Human only
- Minimum DEX 9, CON 9, INT 9, WIS 9 and CHA 9
- Combined Sorcerer/Mage and Monk equipment restrictions
- No dual-classing
- Merged action bar: spellbook and a quick spell from Sorcerer, Search and Stealth from Monk

## Compatibility notes

The installer has two documented class-table branches: the combined format used by released GemRB versions and the split format used by development builds. Split `CLASTEXT.2DA` is accepted in GemRB's normalized six-column form and in native EE nine- or ten-column forms.

GemRB uses class IDs as indices into several class tables and tracks class categories with 32-bit masks. For that reason, custom-class table order is significant: the Sorcerer/Monk ID must equal its `CLSKILLS.2DA` row index and must remain below 32. `CLSKILLS.2DA` and the active class table must each contain at most one `SORCERER_MONK` identity row; duplicates are rejected before installation can depend on lookup order. The Sorcerer/Monk component mask is built for Sorcerer ID 19 and Monk ID 20, so the installer also verifies those base-class IDs and their `CLSKILLS.2DA` row positions before making changes. `CLASS.IDS` must agree in both directions: `SORCERER_MONK` must resolve to the allocated ID, and the allocated ID must not already resolve to another class symbol.

GemRB resolves `FISTWEAP.2DA` by the Monk component level rather than by the rounded average multiclass level, so the multiclass can use the Monk progression unchanged. The installer copies the game's own Monk row under the new class ID: fists improve at exactly the Monk levels a single-class Monk would see. Lower-cap campaigns naturally stop at lower fist tiers. Because `FISTWEAP.2DA` identifies rows only by numeric class ID, an existing row for the ID allocated to Sorcerer/Monk is treated as a collision and installation stops before modifying game tables.

GemRB's high-level-ability screen resolves an unkitted multiclass through its own `LUABBR.2DA` row rather than through the component rows, so both halves of the class end up loading one table. On games without `LUNUMAB.2DA`, HLA metadata is absent and the installer leaves `LUABBR.2DA` untouched. On HLA-capable games where `LUNUMAB.2DA` exists, the HLA metadata is atomic: `LUABBR.2DA` must exist, both Sorcerer and Monk abbreviations must resolve to source LU tables, the source tables must have compatible layouts, and the merge must produce at least one usable HLA row. Any incomplete or ambiguous source set aborts installation before table mutation rather than silently installing a class with broken HLA metadata.

`QSLOTS.2DA` is the one class table GemRB addresses by row index rather than by row name: class ID N uses row N-1. The installer therefore checks that the table holds one row per existing class before appending, and fails rather than writing an action bar that would be applied to a different class.

The apparently misplaced backup directory is intentional in version 2.0. Version 1.9 stored its uninstall data under `sorcerer-monk-cleric/backup`; changing the `BACKUP` directive after users have already installed 1.9 would prevent WeiDU from finding those restoration files during an upgrade. A future backup-path migration requires an explicit transition strategy rather than a direct path rename.

Sorcerer/Monk and Sorcerer/Monk/Cleric cannot be installed together. They historically use the same WeiDU backup directory and component number, so simultaneous installation would make uninstall restoration order-dependent. The old triple-class installer also hardcodes class ID 22, which can collide with Sorcerer/Monk on EE layouts with Shaman present. Both installers now reject the second installation before modifying game files.

Install custom-class mods before starting a new game. Existing saves created without the class tables are not guaranteed to remain compatible after installing or uninstalling the mod.
