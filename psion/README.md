# D&D 3.5e Psion for GemRB

This mod adds a point-based D&D 3.5e Psion class to BG-family campaigns running through GemRB.

The six discipline classes are:

- **Seer** — Clairsentience
- **Shaper** — Metacreativity
- **Kineticist** — Psychokinesis
- **Egoist** — Psychometabolism
- **Nomad** — Psychoportation
- **Telepath** — Telepathy

## Development status

Version 1.0.0 is the first merged release. Current post-1.0 development extends the fixed class progression through character level 20 and power level 9 while retaining the 1.0 installer version until the next release is cut.

The current catalogue contains **85 powers**:

- 61 powers at levels 1–5;
- 24 discipline powers at levels 6–9;
- one new discipline power for every specialization whenever tiers 6, 7, 8 and 9 unlock.

Every catalogue power has at least one progression route. The sixteen level-1–5 resources that were installed but unreachable in 1.0 development are now assigned across CLAB rows 10–20.

## Core rules

- D&D 3.5 power-point progression through Psion level 20.
- Intelligence is the manifesting ability; character creation requires Intelligence 15.
- Maximum PP spent on one manifestation equals manifester level.
- Base power costs are 1, 3, 5, 7, 9, 11, 13, 15 and 17 PP for power levels 1–9.
- Full PP restoration after ordinary or temple rest.
- Persistent PP authority is stored in a private permanent actor effect that survives save/load; GemRB stat 239 is only a runtime cache.
- Runtime validation covers discipline, Intelligence, manifester level, PP reserve and augmentation cost.
- Cancellation-safe reserve/commit accounting prevents target-selection cancellation from spending PP.
- Quickslot configuration never reserves or spends PP; Psion quickspells route through the same PP transaction as action-bar manifestations.
- Silence and ordinary arcane spell failure do not define Psion resource use; powers are implemented as innate resources under GemRB runtime control.

## Powers known

`psionknown.2da` is authoritative. The fixed progression is:

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

At every new tier—class levels 1, 3, 5, 7, 9, 11, 13, 15 and 17—the newly gained set contains exactly one power from the character's chosen discipline at the newly unlocked maximum power level.

## Power catalogue

### Level 1 — 1 PP

Energy Ray, Mind Thrust, Inertial Armor, Vigor, Force Screen, Empty Mind, Precognition, Astral Construct, Matter Agitation, Thicken Skin, Burst and Psionic Charm.

### Level 2 — 3 PP

Concealing Amorpha, Concussion Blast, Detect Hostile Intent, Thought Shield, Biofeedback, Swarm of Crystals, Clairvoyant Sense, Psionic Repair Damage, Energy Missile, Animal Affinity, Dimension Swap, Brain Lock and Energy Push.

### Level 3 — 5 PP

Dispel Psionics, Body Adjustment, Energy Bolt, Mental Barrier, Touchsight, Time Hop, Danger Sense, Ectoplasmic Cocoon, Energy Cone, Hustle, Dimension Slide and Crisis of Breath.

### Level 4 — 7 PP

Energy Adaptation, Freedom of Movement, Dimension Door, Intellect Fortress, Telekinetic Maneuver, Power Leech, Remote Viewing, Wall of Ectoplasm, Energy Ball, Metamorphosis, Fly (Psionic) and Dominate (Psionic).

### Level 5 — 9 PP

Adapt Body, Catapsi, Power Resistance, Psychic Crush, True Seeing, Teleport, Second Chance, Hail of Crystals, Energy Current, Psychofeedback, Baleful Teleport and Mind Probe.

### Level 6 — 11 PP

- Seer: Greater Precognition
- Shaper: Crystallize
- Kineticist: Dispelling Buffer
- Egoist: Restoration (Psionic)
- Nomad: Banishment (Psionic)
- Telepath: Mind Switch

### Level 7 — 13 PP

- Seer: Fate of One
- Shaper: Ectoplasmic Cocoon, Mass
- Kineticist: Reddopsi
- Egoist: Fission
- Nomad: Ethereal Jaunt (Psionic)
- Telepath: Crisis of Life

### Level 8 — 15 PP

- Seer: Hypercognition
- Shaper: Astral Seed
- Kineticist: Telekinetic Sphere (Psionic)
- Egoist: Fusion
- Nomad: Time Hop, Mass
- Telepath: Mind Seed

### Level 9 — 17 PP

- Seer: Metafaculty
- Shaper: True Creation
- Kineticist: Tornado Blast
- Egoist: Greater Metamorphosis
- Nomad: Teleportation Circle (Psionic)
- Telepath: Psychic Chirurgery

These tier-6–9 names and discipline assignments follow the D&D 3.5 SRD. Engine-inexpressible mechanics use documented portable approximations in the SPL source and in-game description rather than hidden substitutions.

## Augmentation

The current selector subsystem supports:

- **Energy Ray:** fire, cold, electricity and sonic ladders through 20 PP.
- **Mind Thrust:** damage through 20 PP with save difficulty improving every 2 additional PP.
- **Vigor:** 5 temporary-HP-equivalent points per PP through 20 PP.
- **Swarm of Crystals:** damage ladder from its 3 PP base through 20 PP.
- **Animal Affinity:** Strength, Dexterity, Constitution or Charisma forms.

`psion_max_augment_cost` and the generated selector tables share the same 20-PP ceiling. Runtime legality still caps a selected child at the actor's manifester level.

## Character progression

- XP progression inherits the active game's complete Mage row.
- The campaign XP cap inherits the active game's Mage cap.
- THAC0 follows `max(0, 20 - floor(level / 2))`.
- Saving throws use a dedicated `SAVEPSI.2DA`: death, polymorph and breath remain Mage-identical while wand and spell saves are 2 better.
- Lore gains 5 points per level.
- Two starting proficiency points; one additional point every four levels.
- One pip maximum in dagger, club, spear, quarterstaff, crossbow, dart and sling; other weapons and styles are disabled.
- BG2-family starting gold inherits Mage values.
- ToB starter equipment uses the Mage package after table-shape validation.
- ToB HLA arithmetic receives safe rows, but epic Psion abilities are not implemented yet.

## Save difficulty

D&D 3.5 uses `10 + power level + Intelligence modifier`. The Infinity Engine does not expose a runtime caster-stat DC field for an installed SPL. This mod therefore preserves the power-level spread in each effect's `savebonus` and bakes in the +2 modifier guaranteed by the Intelligence 15 character-creation minimum.

Intelligence above 15 currently increases bonus PP but does **not** further increase power save difficulty. Implementing exact runtime Intelligence scaling would require a dedicated GemRB substitution/effect mechanism or a large family of per-Intelligence resources.

## High-level portable approximations

Some level-6–9 tabletop mechanics cannot be represented safely by portable Infinity Engine resources:

- Greater Precognition and Fate of One use short insight windows instead of one-roll reroll callbacks.
- Crystallize uses the engine's petrification state with save vs death as the Fortitude analogue.
- Dispelling Buffer blocks ordinary Dispel Magic effects during its duration instead of adding +5 to individual dispel checks.
- Psionic Restoration directly removes level drain but does not generically repair every form of ability-score drain.
- Psionic Banishment uses temporary Maze removal and does not enforce extraplanar-only targeting.
- Mind Switch uses temporary domination instead of swapping CRE bodies, inventories and plot identity.
- Mass Ectoplasmic Cocoon uses an area hold rather than destructible shells.
- Reddopsi uses broad spell/power reflection under psionics-magic transparency.
- Fission expresses the duplicate's contribution as temporary combat bonuses rather than cloning a player CRE.
- Ethereal Jaunt models mobility and defense but does not cross arbitrary unwalkable map geometry.
- Crisis of Life deals severe damage plus brief helplessness rather than a single-save instant kill.
- Hypercognition and Metafaculty provide strong local perception; SPL resources cannot invent campaign knowledge about arbitrary off-map actors.
- Astral Seed currently grants a long defensive preparation; persistent death-to-seed transfer and ten-day body regrowth require runtime resurrection callbacks.
- Telekinetic Sphere immobilizes and protects its subject but cannot be dragged around the map.
- Fusion and Greater Metamorphosis use bounded composite forms instead of arbitrary CRE merging/replacement.
- Mass Time Hop uses area Maze and lacks the tabletop early-return Wisdom check.
- Mind Seed uses long domination instead of permanently rewriting actor identity and progression.
- True Creation summons a durable astral construct because a generic permanent-item construction UI does not exist.
- Tornado Blast implements the 17d6 area blast and forced movement but not a separate direct-hit packet or random relocation distance.
- Teleportation Circle currently relocates within the current area; persistent portal placement and distant destination selection need a dedicated interface.
- Psychic Chirurgery performs restoration and temporary mental protection but cannot yet teach another actor a permanent known power.

Lower-tier documented approximations remain in their respective source files, including temporary-HP Vigor, Maze-based Time Hop, fixed Dispel Psionics, simplified Astral Construct, current-area Teleport and non-reroll Second Chance.

## Item and UI integration

- Item-local opcode 319 restrictions provide exact class usability without inheriting Mage's narrower legacy mask.
- Legal Psion weapons and ammunition remain usable; armor, shields and illegal weapons are rejected.
- The canonical Mage/Sorcerer-style action bar provides three quickspells, Cast, Use, three quick items and Innate.
- Psion and Cipher use one shared `GemRBModCore` GUI hook layer with independent runtime handlers.
- Shared GUI ownership is install-order independent and remains active until the last handler is removed.
- Legacy Psion GUI/runtime ownership markers are migrated so upgrades preserve the true pre-mod files for uninstall.
- Discipline class IDs are allocated from their exact `CLSKILLS.2DA` row indexes, must remain below 32, and are cross-checked against the active class table, `CLASS.IDS`, and positional `QSLOTS.2DA` data. Split class tables support normalized 6-column and native EE 9/10-column `CLASTEXT.2DA`; combined `CLASSES.2DA` is detected from its schema even when `HPCLASS.2DA` is also present.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy both the `psion` directory and its sibling `common` directory from the same release/repository revision into the game directory. The layout must remain:

   ```text
   game/
   ├── common/
   └── psion/
   ```

   Installing only `psion/` is not supported because WeiDU spell constructors and the GUI installer are shared from `common/`.
3. Install the WeiDU component:

   `weidu psion/setup-psion.tp2`

4. Patch GemRB's shared GUI scripts and install the runtime module:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

To remove the Psion handler:

`python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts --uninstall`

If Cipher is still installed, the shared `GemRBModCore` hooks stay active for Cipher. The original GemRB GUI files and common runtime modules are restored only after the final active handler is removed. Uninstall the WeiDU component through WeiDU normally.

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE and EET under GemRB.

Original BG1/TotSC are excluded because the implementation depends on later class-table infrastructure.

## Automated validation

GitHub Actions validates:

- all table shapes and exact 85-resource catalogue membership;
- exact powers-known totals at every character level from 1 through 20;
- one matching discipline power at every newly unlocked tier;
- zero globally unreachable catalogue powers;
- base PP costs through power level 9;
- purpose-built SPL ownership and key high-tier opcodes;
- power-level save penalties through level 9 and save-bearing effect coverage;
- display-name/table-name consistency across every catalogue power;
- generated augmentation tables and the 20-PP ceiling;
- XP, THAC0, saving throws, Lore, proficiencies, ability requirements and item usability;
- fake-GemRB PP persistence, selectors, quickslots, transactions and reusable innate charges;
- shared GUI patch install, idempotence, ownership migration, uninstall, indentation and failure preflight;
- official WeiDU parsing of the complete installer and every included TPA;
- install, verification, uninstall and reinstall across normalized, native EE and legacy class-table layouts;
- BG2/ToB startup-table lifecycles and semantic item restoration;
- binary SPL bounds and preservation of original TLK/table data after uninstall.

## Next work

The main remaining design systems are player-selected power learning, psicrystals, psionic items, enemy Psions, deeper augmentation for high-tier powers, and higher-fidelity runtime support for the approximations listed above.
