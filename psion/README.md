# D&D 3.5e Psion for GemRB

This mod adds a point-based D&D 3.5e Psion class to BG-family campaigns running through GemRB.

## Release status

Current release metadata: **1.4.0**.

The six discipline classes are Seer, Shaper, Kineticist, Egoist, Nomad, and Telepath. The current catalogue contains 85 powers through power level 9.

Automated validation covers installer parsing, class-table layouts, power resources, power-point accounting, selectable powers, exact Intelligence save-DC substitution, shared GUI ownership, save-safe state, and install/uninstall lifecycles. Real BGEE and BG2EE-family campaign acceptance is scripted under `acceptance/` but still requires locally available game assets and an interactive GemRB run; automated coverage is not presented as a substitute for that live acceptance.

## Core rules

- D&D 3.5e power-point progression through Psion level 20.
- Intelligence is the manifesting ability; character creation requires Intelligence 15.
- Maximum PP spent on one manifestation equals manifester level.
- Base power costs are 1, 3, 5, 7, 9, 11, 13, 15, and 17 PP for power levels 1–9.
- Full PP restoration after ordinary or temple rest.
- Persistent PP authority is stored in a private save-serialized actor effect; GemRB stat 239 is only a cache.
- Manifestation validates discipline, Intelligence, manifester level, PP reserve, and augmentation cost.
- Target cancellation does not spend PP, and repeated callbacks do not intentionally double-charge a manifestation.
- Quickslot configuration does not reserve or spend PP.
- Psionic focus and Psion skill/feat state also use private save-serialized effects.

## Player-selected powers

`psionknown.2da` defines the number of powers known and highest legal power level at each Psion level. **Powers are selected by the player** rather than granted as a fixed CLAB sequence.

The reusable **Learn Psion Power** selector filters the catalogue by:

- current `PSIONKNOWN` allowance;
- maximum legal power level;
- chosen discipline;
- already-known powers.

The selector uses harmless `PXL*` proxy spells. Confirming a proxy permanently learns the corresponding real `PS*` power but does not manifest it or spend PP. Canceling the selector does not consume a powers-known choice. Existing saves retain already-known powers and receive additional selector access only when their current known count is below the allowance.

| Psion level | Powers known | Maximum power level |
| ---: | ---: | ---: |
| 1 | 3 | 1 |
| 2 | 5 | 1 |
| 3 | 7 | 2 |
| 4 | 9 | 2 |
| 5 | 11 | 3 |
| 6 | 13 | 3 |
| 7 | 15 | 4 |
| 8 | 17 | 4 |
| 9 | 19 | 5 |
| 10 | 21 | 5 |
| 11 | 22 | 6 |
| 12 | 24 | 6 |
| 13 | 25 | 7 |
| 14 | 27 | 7 |
| 15 | 28 | 8 |
| 16 | 30 | 8 |
| 17 | 31 | 9 |
| 18 | 33 | 9 |
| 19 | 34 | 9 |
| 20 | 36 | 9 |

## Exact Intelligence save difficulty

D&D 3.5e uses `10 + power level + Intelligence modifier`.

Public Psion resources are authored against the class minimum Intelligence 15. During installation, the mod generates internal save-bearing variants for the other reachable BG-family Intelligence modifiers. Immediately before a manifestation, `Psionics.py` reads the actor's **current Intelligence** and substitutes the appropriate internal resource through GemRB's spontaneous-cast path.

This means temporary Intelligence changes alter save difficulty at cast time without changing the known-power registry or PP cost. The runtime falls back to the canonical resource if a variant is unavailable instead of mutating installed SPL files during play.

## Augmentation

The current selector subsystem supports:

- Energy Ray: fire, cold, electricity, and sonic ladders through 20 PP.
- Mind Thrust: damage through 20 PP with improved save difficulty on higher augment steps.
- Vigor: 5 temporary-HP-equivalent points per PP through 20 PP.
- Swarm of Crystals: damage ladder from its 3 PP base through 20 PP.
- Animal Affinity: Strength, Dexterity, Constitution, or Charisma forms.

Runtime legality still limits the total selected cost to manifester level and current PP.

## Psicrystals

Version 1.4 adds a persistent psicrystal subsystem without using or modifying the ordinary familiar infrastructure.

A Psion can make exactly one persistent personality selection:

- Heroic: level-scaled attack insight.
- Nimble: level-scaled Armor Class bonus.
- Observant: level-scaled trap-detection/awareness bonus.
- Resolute: level-scaled saving-throw bonus.

The personality is stored on that Psion in a private serialized effect, so multiple Psions do not share state. Passive scaling is derived from Psion level, with stronger resonance tiers at levels 8 and 15. Existing saves are not forced to pick a personality during load.

After choosing, the Psion learns **Manifest Psicrystal**. Its summon charge is restored on rest rather than whenever the innate menu is opened. The summoned creature uses a dedicated Psion resource and does not consume familiar tables or familiar ownership state.

## Enemy Psions

`psion/guiscripts/PsionAI.py` provides a non-player Psion controller that reuses the canonical Psion runtime rather than implementing a second PP/DC system. It can initialize enemy PP/focus state, choose offensive/defensive/mobility powers, enforce affordability, substitute the enemy's current-Intelligence DC resource, and deduct PP exactly once after manifestation.

This is an encounter integration primitive and deterministic regression target; version 1.4 does not place enemy Psions throughout existing campaigns automatically.

## Optional discipline equipment

WeiDU component **200 — Psion discipline equipment** installs six small, discipline-specific items:

| Item | Discipline | Effect | Intended tier |
| --- | --- | --- | --- |
| Seer's Lens (`PSIITM01`) | Seer | +1 Intelligence | early/mid |
| Ectoplasmic Bracers (`PSIITM02`) | Shaper | +1 Armor Class | mid |
| Conductive Ring (`PSIITM03`) | Kineticist | +20% electrical resistance | mid |
| Mutable Girdle (`PSIITM04`) | Egoist | +1 Constitution | mid |
| Nomad's Striders (`PSIITM05`) | Nomad | +15% movement | mid/high |
| Whispering Circlet (`PSIITM06`) | Telepath | +1 Intelligence, +1 save vs spell | high |

Each item uses opcode 319 in allow-only CLASS.IDS mode, so all six discipline classes receive deterministic usability behavior. Intelligence bonuses naturally feed the canonical PP/DC calculations; the items do not write the PP cache or psionic-focus state directly.

The component installs item resources only and intentionally does not alter campaign stores or encounters. This keeps campaign placement optional and prevents guessed store-resource dependencies. Encounter/store mods can place the documented `PSIITM01`–`PSIITM06` resources explicitly.

## High-tier fidelity

`psion/docs/high-tier-fidelity.md` tracks every documented level 6–9 approximation by gameplay value, engine feasibility, and implementation complexity.

Version 1.4 implements two high-impact upgrades:

- **Fission** now creates a real temporary psionic echo while retaining bounded combat bonuses. It does not clone player inventory, scripts, dialogue, or protagonist identity.
- **Crisis of Life** now has a lethal failed-save branch. The remaining divergence is that the portable implementation cannot enforce the tabletop 11-HD death cutoff.

Other high-tier deviations remain explicitly documented rather than hidden behind approximate descriptions.

## Character progression

- XP progression and campaign XP cap inherit the active game's Mage data.
- THAC0 follows `max(0, 20 - floor(level / 2))`.
- Saving throws use `SAVEPSI.2DA`; wand and spell saves are two points better than the inherited Mage row.
- Lore gains 5 points per level.
- Two starting proficiency points and one additional point every four levels.
- One pip maximum in dagger, club, spear, quarterstaff, crossbow, dart, and sling.
- BG2-family starting gold and ToB starter equipment inherit validated Mage data.
- HLA safety rows prevent invalid arithmetic, but a dedicated epic Psion HLA system is not implemented.

## Installation

The recommended entry point is the repository/release-level driver. It stages matching `common/` and class files, validates a release manifest when present, runs WeiDU, then installs the shared GUI runtime with the correct dependency set.

```bash
python tools/gemrb_mods.py install psion \
  --game /path/to/game \
  --guiscripts /path/to/GemRB/gemrb/GUIScripts \
  --weidu /path/to/weidu
```

Install Cipher and Psion together through the same entry point:

```bash
python tools/gemrb_mods.py install cipher psion \
  --game /path/to/game \
  --guiscripts /path/to/GemRB/gemrb/GUIScripts
```

Package a self-contained release bundle:

```bash
python tools/gemrb_mods.py package cipher psion --output gemrb-classes.zip
```

The generated bundle contains matching shared runtime files and `gemrb-mods-release.json` SHA-256 metadata. Manifest mismatches fail before target mutation.

Low-level installation remains supported for development: run `weidu psion/setup-psion.tp2`, then `python psion/tools/install_guiscripts.py <GUIScripts>`. When Cipher is also installed, removing one handler leaves the shared GUI core active until the last handler is removed.

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE, and EET under GemRB. Original BG1/TotSC are excluded because the implementation depends on later class-table infrastructure.

See the repository-level `COMPATIBILITY.md` and `acceptance/README.md` for automated-versus-live validation status.

## Validation

The repository validates:

- table shapes, complete 85-power catalogue membership, and powers-known limits;
- generated augmentation tables and resource bounds;
- exact current-Intelligence save-DC substitution;
- PP/focus/feat/skill persistence and transaction behavior;
- selectable-power proxy safety;
- psicrystal persistence/resource ownership contracts;
- enemy Psion controller contracts;
- optional equipment usability contracts;
- high-tier fidelity patches;
- shared GUI install/idempotence/uninstall ownership;
- official WeiDU parsing;
- install/uninstall/reinstall across supported class-table fixture layouts.

Real-engine BGEE/BG2EE-family acceptance remains a separate gate because proprietary game data is not committed to this repository.
