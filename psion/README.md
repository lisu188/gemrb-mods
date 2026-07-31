# D&D 3e Psion for GemRB

This mod adds a point-based D&D 3e Psion class to BG1-family conversions and
Enhanced Edition campaigns running through GemRB.

The six selectable discipline classes are:

- **Seer** — Clairsentience
- **Shaper** — Metacreativity
- **Kineticist** — Psychokinesis
- **Egoist** — Psychometabolism
- **Nomad** — Psychoportation
- **Telepath** — Telepathy

## Release status: 1.0.0

Version 1.0.0 is the first installable release. It includes class registration,
level progression, persistent power points, filtered augmentation selectors and
all sixty level 1–5 powers. Every power is built from an empty SPL resource; the
installer has no wizard/priest template-spell dependency and no undeclared WeiDU
helper-library dependency.

The release is validated with official WeiDU 251 through complete install,
uninstall and reinstall lifecycles against generated fixtures for all supported
class-table formats:

- released GemRB's normalized six-field split layout;
- native Enhanced Edition's ten-field split layout;
- older GemRB's nineteen-field combined layout.

These automated fixtures verify installer behavior and generated resource
structure without distributing proprietary game data. They are not a substitute
for a manual full-campaign playthrough on every supported game configuration.

## Implemented systems

- Six dynamically allocated custom class identifiers.
- Normalized split, native EE split and legacy combined class-table support.
- D&D 3e base power-point progression through level 20.
- Intelligence bonus pool:

  `floor(Intelligence modifier × Psion level / 2)`

- Persistent current PP stored in GemRB actor stat 239.
- Full PP restoration after ordinary and temple resting.
- Base costs of 1, 3, 5, 7 and 9 PP for power levels 1–5.
- Maximum PP expenditure per manifestation equal to Psion level.
- Discipline, Intelligence, manifester-level and current-pool validation.
- Cancellation-safe two-phase PP transactions.
- Runtime-filtered augmentation and choice lists.
- Separate fixed level 1–9 progression for every discipline.
- Nineteen known powers at level 9, including one exclusive discipline power
  whenever a new power tier becomes available.
- Purpose-built resources for all sixty powers at levels 1–5.
- Fifty-seven registered augmentation or choice child resources.
- Backup-safe GemRB GUI-script installation and removal.
- Ownership-aware installation of the standalone `Psionics.py` runtime module.

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

## Power catalogue

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

Adapt Body, Catapsi, Power Resistance, Cognitive Overload, True Seeing,
Teleport, Second Chance, Hail of Crystals, Energy Current, Psychofeedback,
Spatial Disruption and Mind Probe.

## Deliberate engine approximations

The Infinity Engine does not expose every D&D 3e psionic mechanism. The
following portable approximations are intentional and documented in source
comments and in-game descriptions:

- Will saves use save vs spell or broad BG saving-throw modifiers.
- Vigor uses timed HP effects instead of native temporary HP.
- Concealment uses Blur, AC and saving-throw bonuses.
- Biofeedback uses percentage rather than flat damage reduction.
- Energy Missile uses a small area burst instead of three discrete targets.
- Psionic Repair Damage is not yet restricted to construct targets.
- Dispel Psionics uses a fixed effective level rather than Psicraft.
- Time Hop uses Maze.
- Ectoplasmic Cocoon is not a destructible hit-point shell.
- Energy Adaptation protects against four energies rather than selecting one
  stronger resistance.
- Intellect Fortress is self-only rather than a maintained party aura.
- Telekinetic Maneuver implements push and trip, but not pull or disarm.
- Power Leech applies casting failure but does not transfer PP.
- Wall of Ectoplasm creates one construct node instead of a segmented wall.
- Metamorphosis provides one bear-like form.
- Psionic Flight cannot cross arbitrary unwalkable map geometry.
- Adapt Body does not provide portable fatigue immunity.
- Catapsi is stationary rather than following the manifester.
- Teleport relocates within the current area only.
- Second Chance uses an insight bonus instead of a true reroll callback.
- Energy Current does not stop when concentration is broken.
- Psychofeedback does not select exact ability transfers.
- Mind Probe does not display full statistics or scripted memories.
- Astral Construct uses a temporary wolf-derived creature body.
- Power learning is fixed by discipline rather than player-selected.

These are gameplay-scope limitations, not silent installer fallbacks.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory into the game directory.
3. Install the WeiDU component:

   `weidu psion/setup-psion.tp2`

4. Patch GemRB's shared GUI scripts and install the runtime module:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

The patcher copies `psion/guiscripts/Psionics.py` into the selected GemRB
`GUIScripts` directory and updates `ActionsWindow.py`, `Spellbook.py`,
`MenuWindow.py` and `GUISTORE.py`.

For each shared script it creates a byte-for-byte `.psion.bak` backup. If a
pre-existing `Psionics.py` is present, that module is also backed up and restored
on uninstall. If the Psion mod created the runtime file, ownership is recorded
and uninstall removes it. Repeating the installation with identical files is
idempotent and does not replace the original backups.

To remove the GUI hooks and runtime module:

`python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts --uninstall`

Uninstall the WeiDU component through WeiDU in the normal way. WeiDU restores
patched game resources; as with other WeiDU mods, unused appended TLK slots may
remain after uninstall while all original strings remain unchanged.

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE and EET under GemRB.
Original BG1/TotSC are excluded because the implementation depends on
Sorcerer/Monk-era class data.

## Automated validation

GitHub Actions runs:

- table, progression, augmentation and installer-source checks;
- parser-safety checks for unsupported WeiDU integer forms;
- fake-GemRB PP, selector and transaction tests;
- GUI patch install, idempotence, backup and uninstall fixtures;
- runtime-module replacement, restoration, creation and removal fixtures;
- dedicated level-3, level-4 and level-5 resource regression suites;
- Python compilation checks;
- official WeiDU 251 parsing of the TP2 and every TPA module;
- real WeiDU install, verification, uninstall and reinstall for normalized,
  native EE and legacy combined class-table layouts;
- binary validation of every generated Psion SPL header and effect range;
- byte-for-byte restoration checks for every patched table;
- semantic preservation checks for all original TLK entries.

## Post-1.0 development

Future work can improve fidelity without changing the 1.0 installer contract:
choice-based power learning, dedicated Astral Construct assets and AI, exact
construct targeting, PP transfer, reroll and concentration callbacks, a travel
interface, psionic focus/feats/skills, psicrystals, items and enemy Psions.
