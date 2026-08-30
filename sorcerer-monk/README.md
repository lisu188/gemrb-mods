# Sorcerer/Monk multiclass for GemRB

This mod adds a true Sorcerer/Monk multiclass to Infinity Engine games running through GemRB.

Current release metadata: **2.0**.

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

Original BG1 and TotSC are excluded because they do not provide both Sorcerer and Monk base classes. Supported games must be launched through GemRB.

## Version 2.0 behavior

Version 2.0 is a correctness pass over the historical 1.9 installer:

- the class ID is derived from the live `CLSKILLS.2DA` row instead of being hardcoded;
- class-table, `CLASS.IDS`, `FISTWEAP.2DA`, and positional `QSLOTS.2DA` identity conflicts fail before mutation;
- combined, normalized split, and native Enhanced Edition class-table layouts are recognized explicitly;
- XP cap, starting XP/gold, avatar, non-proficiency penalty, and Monk fist progression inherit live campaign data;
- saving throws, hit points, human-only race rules, lawful alignment rules, and Sorcerer/Monk equipment restrictions are combined as a true multiclass;
- Monk skill/proficiency progression is installed for both legacy and current table layouts;
- Sorcerer spontaneous casting and Monk action-bar entries are merged;
- HLA-capable games receive a combined HLA table generated from the installed Sorcerer and Monk sources;
- simultaneous installation with the legacy Sorcerer/Monk/Cleric package is rejected before mutation.

See `CHANGELOG.md` for the detailed installer history.

## Gameplay model

- Sorcerer spontaneous arcane spell progression
- Monk fists and class abilities
- lawful alignments only
- human only
- minimum DEX 9, CON 9, INT 9, WIS 9, and CHA 9
- combined Sorcerer/Mage and Monk equipment restrictions
- no dual-classing
- merged action bar with Sorcerer spellbook/quickspell plus Monk Search and Stealth

GemRB resolves `FISTWEAP.2DA` from the Monk component level. The installer therefore copies the active game's Monk row under the custom class ID instead of inventing a second fist progression.

## Automated validation versus live acceptance

The 2.0 installer is extensively **automatically validated**, including:

- real WeiDU parsing and install/uninstall/reinstall fixture lifecycles;
- supported class-table layouts;
- custom class identity and collision guards;
- inherited campaign metadata;
- Monk fist, skill, proficiency, and APR table contracts;
- Sorcerer spellbook/action-bar metadata;
- HLA table generation and safety checks where HLA data exists;
- byte-for-byte restoration of modified fixture resources.

That automated coverage does **not** prove the entire custom multiclass behavior in a live campaign. The remaining release gate is the real-engine acceptance matrix in `acceptance/README.md`:

- BGEE low-level character creation and gameplay;
- BG2EE mid-level spellcasting/Monk combat/level-up;
- ToB or BG2EE high-level HLA resolution;
- explicit Monk level-2 fist-tier check;
- save/reload preservation of class identity and spellbook state.

`acceptance/run.py` creates a reproducible GemRB config, captures engine logs, records GemRB revision metadata, and writes a machine-readable result file. Actual acceptance must be performed against legally available local game assets; the repository does not claim those checks passed merely because the runner exists.

## Installation

The repository-level driver is the preferred entry point:

```bash
python tools/gemrb_mods.py install sorcerer-monk \
  --game /path/to/game \
  --weidu /path/to/weidu
```

Sorcerer/Monk has no shared GUIScript handler, so `--guiscripts` is not required when it is installed alone.

Low-level installation remains supported:

```text
weidu sorcerer-monk/setup-sorcerer-monk.tp2
```

Use WeiDU 247 or newer. The main repository CI currently validates against WeiDU 251.

Sorcerer/Monk and the legacy Sorcerer/Monk/Cleric mod are intentionally mutually exclusive. Uninstall one before installing the other.

## Compatibility notes

GemRB uses class IDs as indexes into several class tables and tracks class categories with 32-bit masks. The Sorcerer/Monk ID must therefore match its `CLSKILLS.2DA` row position and remain below 32.

`QSLOTS.2DA` is addressed positionally: class ID N uses row N-1. The installer validates this relationship before append.

On HLA-capable games, `LUABBR.2DA` and `LUNUMAB.2DA` metadata are treated atomically. Both Sorcerer and Monk source HLA tables must resolve and have compatible layouts before a merged table is installed.

The historical backup location `sorcerer-monk-cleric/backup` is intentionally retained so existing 1.9 installations remain uninstallable/reinstallable. Changing that path without migration would orphan WeiDU restoration data.

Install custom-class mods before starting a new game. Existing saves created without the relevant class tables are not guaranteed to remain compatible after later installation or removal.

See repository-level `COMPATIBILITY.md` for the cross-mod support matrix.
