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

## Status: 0.7.0-alpha

The architecture, class registration, power-point pool and all level 1–4 power
resources are implemented. Level-5 powers remain prototypes, and the mod still
requires a complete WeiDU installation and in-game GemRB smoke test before it
should be considered ready for normal play.

## Implemented systems

- Six dynamically allocated custom class rows.
- Support for released combined and newer split GemRB class-table layouts.
- D&D 3e base power-point progression through level 20.
- Intelligence bonus pool:

  `floor(Intelligence modifier × Psion level / 2)`

- Persistent current power points stored in GemRB actor stat 239.
- Full PP restoration after ordinary and temple resting.
- Base power costs of 1, 3, 5, 7 and 9 PP for power levels 1–5.
- Maximum PP expenditure per manifestation equal to Psion level.
- Discipline, Intelligence, level and current-pool validation.
- Cancellation-safe two-phase PP transactions.
- Runtime-filtered augmentation and choice lists.
- Separate fixed level 1–9 progression for each discipline.
- Nineteen known powers at level 9, including one exclusive discipline power
  whenever a new power tier becomes available.
- Purpose-built resources for all 48 powers at levels 1–4.
- Fifty-seven registered augmentation or choice child resources.
- Backup-safe GemRB GUI-script installation and removal.

## Power-point transaction

GemRB invokes the spell-selection flow more than once while a target is being
chosen. The Psion runtime therefore treats manifestation as a transaction:

1. The first matching callback validates and reserves the manifestation.
2. A matching confirmation callback deducts the PP exactly once.
3. Cancelling the targeting interface clears the pending transaction.
4. Repeated callbacks cannot intentionally charge the same manifestation twice.

The runtime revalidates the selected child resource at confirmation time. A
power cannot overspend merely because the character lost PP after opening a
selector.

## Filtered selectors

Opcode-214 choice lists are filtered through the installed `Spellbook.py` hook.
Only choices registered in `PSIONAUGMENT.2DA` are modified; base-game and
third-party selectors are preserved in their original order.

The current selectors are:

- **Energy Ray:** fire, cold, electricity and sonic variants costing 1–9 PP.
- **Mind Thrust:** 1d10–9d10 variants costing 1–9 PP.
- **Vigor:** 5–45 temporary-HP-equivalent variants costing 1–9 PP.
- **Animal Affinity:** +4 Strength, Dexterity or Constitution for 3 PP.

A selector displays only children legal for the selected actor's current PP,
manifester level, discipline and Intelligence.

## Purpose-built level-1 powers

- Energy Ray
- Mind Thrust
- Inertial Armor
- Vigor
- Force Screen
- Empty Mind
- Precognition
- Astral Construct
- Energy Push
- Thicken Skin
- Burst
- Psionic Charm

## Purpose-built level-2 powers

- Concealing Amorpha
- Concussion Blast
- Detect Hostile Intent
- Thought Shield
- Biofeedback
- Swarm of Crystals
- Clairvoyant Sense
- Psionic Repair Damage
- Energy Missile
- Animal Affinity
- Dimension Swap
- Brain Lock

## Purpose-built level-3 powers

- Dispel Psionics
- Body Adjustment
- Energy Bolt
- Mental Barrier
- Touchsight
- Time Hop
- Danger Sense
- Ectoplasmic Cocoon
- Energy Cone
- Hustle
- Spatial Step
- Mental Stasis

## Purpose-built level-4 powers

- **Energy Adaptation:** 25% resistance to acid, cold, electricity and fire for
  seven turns.
- **Freedom of Movement:** removes hold and movement penalties, then protects
  against common hold, slow, entangle, web and grease opcodes.
- **Dimension Door:** teleports the manifester to a visible point.
- **Intellect Fortress:** +2 saves and 50% magical-damage resistance for three
  rounds.
- **Telekinetic Maneuver:** pushes and knocks down one target on a failed save.
- **Power Leech:** imposes 20% mage, priest and innate casting failure for five
  rounds.
- **Remote Viewing:** detects invisibility and grants +30 Lore and Find Traps.
- **Wall of Ectoplasm:** creates one temporary construct obstruction.
- **Energy Ball:** 7d6 electrical area damage, save for half.
- **Metamorphosis:** bear-like combat form with physical statistics, AC, APR and
  resistance bonuses.
- **Psionic Flight:** movement, AC, backstab and ground-restraint protection.
- **Compulsion:** dominates one target for five rounds, save negates.

## Deliberate engine approximations

The Infinity Engine does not expose every D&D 3e psionic mechanic. The current
portable approximations are explicit in source comments and in-game power
text:

- Will saves use save vs spell or broad BG saving-throw modifiers.
- Vigor uses timed current and maximum HP effects rather than native temporary
  hit points.
- Concealment uses Blur, AC and saving-throw bonuses.
- Biofeedback uses percentage resistance instead of flat damage reduction.
- Energy Missile uses a small area burst rather than three discrete targets.
- Dispel Psionics uses a fixed effective level rather than Psicraft.
- Time Hop uses the engine's Maze effect.
- Ectoplasmic Cocoon is not yet a destructible hit-point shell.
- Energy Adaptation currently gives 25% to four energies instead of selecting
  50% resistance to one energy.
- Intellect Fortress is self-only rather than a maintained party aura.
- Telekinetic Maneuver currently implements push and trip, not pull or disarm.
- Power Leech applies casting failure but does not yet transfer PP.
- Remote Viewing provides enhanced perception unless a quest script supplies a
  remote scene.
- Wall of Ectoplasm currently creates one construct node rather than a segmented
  wall.
- Metamorphosis currently provides one bear-like form.
- Psionic Flight cannot cross arbitrary unwalkable map geometry.
- Astral Construct still uses a temporary wolf-derived creature body.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory into the game directory.
3. Run:

   `weidu psion/setup-psion.tp2`

4. Patch GemRB's shared GUI scripts:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

The patcher updates:

- `ActionsWindow.py`
- `Spellbook.py`
- `MenuWindow.py`
- `GUISTORE.py`

A `.psion.bak` backup is created for each modified file. Remove the hooks with:

`python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts --uninstall`

## Supported targets

- Tutu
- Tutu_TotSC
- BGEE
- Classic Adventures
- BGT
- BG2EE
- EET

Original BG1/TotSC are excluded because this implementation depends on
Sorcerer/Monk-era class data.

## Automated validation

GitHub Actions currently runs:

- core table and progression validation;
- level-1 and level-2 resource checks;
- augmentation-table and filtered-selector tests;
- fake-GemRB PP transaction tests;
- GUI patch, idempotence, backup and uninstall fixtures;
- dedicated level-3 resource regression checks;
- dedicated level-4 resource regression checks;
- Python compilation checks.

## Remaining development priorities

1. Automated WeiDU parsing and installation fixture.
2. Real GemRB in-game smoke test.
3. Purpose-built level-5 power resources.
4. Construct-only targeting for Psionic Repair Damage.
5. Dedicated Astral Construct creature and AI.
6. Choice-based power learning and replacement.
7. Current/maximum PP display in the action and record interfaces.
8. Psionic focus, feats and skill allocation.
9. Psicrystal, psionic items and enemy Psions.
