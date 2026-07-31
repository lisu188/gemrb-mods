# Experimental D&D 3e Psion for GemRB

This mod adds a point-based Psion class to BG1-family conversions and Enhanced
Edition campaigns running through GemRB.

The six selectable discipline classes are:

- **Seer** — Clairsentience
- **Shaper** — Metacreativity
- **Kineticist** — Psychokinesis
- **Egoist** — Psychometabolism
- **Nomad** — Psychoportation
- **Telepath** — Telepathy

## Status: 0.9.0-alpha

Class registration, progression, persistent power points, filtered augmentation
selectors and all sixty level 1–5 powers are implemented. Every power is built
from an empty SPL resource; the mod no longer clones or depends on wizard and
priest spells for its power catalogue.

The complete TP2 and every included TPA module are parsed in CI with the
official Linux build of WeiDU 251. This uncovered and fixed invalid negative
integer syntax that the earlier source-text tests could not detect.

The project remains an alpha until it completes an installation against actual
BG-family game data and an in-game GemRB smoke test.

## Implemented systems

- Six dynamically allocated custom class rows.
- Released combined and newer split GemRB class-table layouts.
- D&D 3e base power-point progression through level 20.
- Intelligence bonus pool:

  `floor(Intelligence modifier × Psion level / 2)`

- Persistent current PP stored in GemRB actor stat 239.
- Full PP restoration after ordinary and temple resting.
- Base costs of 1, 3, 5, 7 and 9 PP for power levels 1–5.
- Maximum PP expenditure per manifestation equal to Psion level.
- Discipline, Intelligence, level and current-pool validation.
- Cancellation-safe two-phase PP transactions.
- Runtime-filtered augmentation and choice lists.
- Separate fixed level 1–9 progression for every discipline.
- Nineteen known powers at level 9, including one exclusive discipline power
  whenever a new power tier becomes available.
- Purpose-built resources for all sixty powers at levels 1–5.
- Fifty-seven registered augmentation or choice child resources.
- Backup-safe GemRB GUI-script installation and removal.

## Power-point transaction

GemRB invokes the spell-selection flow more than once while a target is being
chosen. Manifestation therefore uses a transaction:

1. The first matching callback validates and reserves the manifestation.
2. A matching confirmation callback deducts PP exactly once.
3. Cancelling target selection clears the pending transaction.
4. Repeated callbacks cannot intentionally charge the same manifestation twice.

The runtime revalidates selected child resources at confirmation time, so a
power cannot overspend merely because PP changed after opening a selector.

## Filtered selectors

Opcode-214 choice lists pass through the installed `Spellbook.py` hook. Only
choices registered in `PSIONAUGMENT.2DA` are filtered; base-game and third-party
selectors retain their order and behavior.

Current selectors:

- **Energy Ray:** fire, cold, electricity and sonic variants costing 1–9 PP.
- **Mind Thrust:** 1d10–9d10 variants costing 1–9 PP.
- **Vigor:** 5–45 temporary-HP-equivalent variants costing 1–9 PP.
- **Animal Affinity:** +4 Strength, Dexterity or Constitution for 3 PP.

## Purpose-built powers

### Level 1

Energy Ray, Mind Thrust, Inertial Armor, Vigor, Force Screen, Empty Mind,
Precognition, Astral Construct, Energy Push, Thicken Skin, Burst and Psionic
Charm.

### Level 2

Concealing Amorpha, Concussion Blast, Detect Hostile Intent, Thought Shield,
Biofeedback, Swarm of Crystals, Clairvoyant Sense, Psionic Repair Damage,
Energy Missile, Animal Affinity, Dimension Swap and Brain Lock.

### Level 3

Dispel Psionics, Body Adjustment, Energy Bolt, Mental Barrier, Touchsight, Time
Hop, Danger Sense, Ectoplasmic Cocoon, Energy Cone, Hustle, Spatial Step and
Mental Stasis.

### Level 4

Energy Adaptation, Freedom of Movement, Dimension Door, Intellect Fortress,
Telekinetic Maneuver, Power Leech, Remote Viewing, Wall of Ectoplasm, Energy
Ball, Metamorphosis, Psionic Flight and Compulsion.

### Level 5

- **Adapt Body:** poison and disease protection plus 25% resistance to acid,
  cold, electricity and fire.
- **Catapsi:** stationary field imposing 30% wizard, priest and innate failure.
- **Power Resistance:** grants 29% magic and power resistance at the first legal
  manifestation level.
- **Cognitive Overload:** 6d6 magical damage plus slow and 50% casting failure
  on a failed save.
- **True Seeing:** detects invisibility, prevents backstab and blocks blindness.
- **Teleport:** unrestricted current-area relocation.
- **Second Chance:** short +2 attack, Armor Class and saving-throw insight bonus.
- **Hail of Crystals:** 9d4 slashing area damage, save for half.
- **Energy Current:** 5d6 initial electrical damage followed by four delayed 2d6
  pulses.
- **Psychofeedback:** +4 Strength, Dexterity and Constitution with a saving-throw
  penalty.
- **Spatial Disruption:** 9d6 magical damage and save-negated slow.
- **Mind Probe:** worsens all target saving throws by 2 for five rounds.

## Deliberate engine approximations

The Infinity Engine does not expose every D&D 3e psionic mechanism. Current
portable approximations are explicit in source comments and in-game text:

- Will saves use save vs spell or broad BG saving-throw modifiers.
- Vigor uses timed HP effects instead of native temporary HP.
- Concealment uses Blur, AC and saving-throw bonuses.
- Biofeedback uses percentage rather than flat damage reduction.
- Energy Missile uses a small area burst instead of three discrete targets.
- Dispel Psionics uses a fixed effective level rather than Psicraft.
- Time Hop uses Maze.
- Ectoplasmic Cocoon is not a destructible hit-point shell.
- Energy Adaptation currently protects against four energies rather than
  selecting one stronger resistance.
- Intellect Fortress is self-only rather than a maintained party aura.
- Telekinetic Maneuver currently implements push and trip only.
- Power Leech applies casting failure but does not transfer PP.
- Wall of Ectoplasm creates one construct node instead of a segmented wall.
- Metamorphosis currently provides one bear-like form.
- Psionic Flight cannot cross arbitrary unwalkable map geometry.
- Adapt Body does not yet implement portable fatigue immunity.
- Catapsi is stationary rather than following the manifester.
- Teleport remains current-area only until a safe destination GUI exists.
- Second Chance uses a broad insight bonus instead of a true reroll callback.
- Energy Current does not yet stop when concentration is broken.
- Psychofeedback does not yet select exact ability transfers.
- Mind Probe does not yet display full statistics or scripted memories.
- Astral Construct still uses a temporary wolf-derived creature body.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory into the game directory.
3. Run `weidu psion/setup-psion.tp2`.
4. Patch GemRB's shared GUI scripts:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

The patcher updates `ActionsWindow.py`, `Spellbook.py`, `MenuWindow.py` and
`GUISTORE.py`, creating a `.psion.bak` backup for each. Remove the hooks with:

`python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts --uninstall`

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE and EET under GemRB.
Original BG1/TotSC are excluded because the implementation depends on
Sorcerer/Monk-era class data.

## Automated validation

GitHub Actions runs:

- version-neutral table, progression, builder and installer checks;
- a parser-safety guard rejecting bare negative WeiDU argument values and
  negative long-write sentinels;
- fake-GemRB PP, selector and transaction tests;
- GUI patch, idempotence, backup and uninstall fixtures;
- dedicated level-3, level-4 and level-5 resource regression suites;
- Python compilation checks;
- official WeiDU 251 component parsing for `setup-psion.tp2`;
- independent WeiDU 251 parsing of every `psion/lib/*.tpa` module.

The WeiDU stage validates grammar and module structure. It does not yet prove
that every resource and table mutation succeeds against a real game install.

## Remaining development priorities

1. Automated WeiDU installation against a representative BG-family fixture or
   test installation.
2. Real GemRB in-game smoke test.
3. Construct-only targeting for Psionic Repair Damage.
4. Dedicated Astral Construct creature and AI.
5. Choice-based power learning and replacement.
6. Current/maximum PP display in action and record interfaces.
7. Psionic focus, feats and skill allocation.
8. Psicrystal, psionic items and enemy Psions.
9. Runtime implementations for PP transfer, rerolls, concentration and travel.
