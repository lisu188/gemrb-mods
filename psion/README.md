# D&D 3.5e Psion for GemRB

This mod adds a point-based D&D 3.5e Psion class to BG1-family conversions and
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
all sixty-one level 1–5 powers. Every power is built from an empty SPL resource;
the installer has no wizard/priest template-spell dependency and no undeclared
WeiDU helper-library dependency.

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
- D&D 3.5e base power-point progression through level 20.
- Intelligence bonus pool:

  `floor(Intelligence modifier × Psion level / 2)`

- Save-safe PP state stored in a private permanent `Protection:Spell` actor
  effect. GemRB serializes ordinary actor effects in CRE saves, including when
  using original game CRE formats. The record targets a private nonexistent
  resource, carries current PP in `Param1`, and uses resistance mode 0, so it is
  neither resistible nor dispellable and has no effect on real game resources.
- GemRB user stat 239 is retained only as a fast runtime PP cache. A Psion
  signature occupies the high word and current PP the low word; after save/load,
  a missing cache is reconstructed from the serialized actor effect.
- No ordinary Infinity Engine gameplay stat is repurposed as Psion state.
- Full PP restoration after ordinary and temple resting.
- Base costs of 1, 3, 5, 7 and 9 PP for power levels 1–5.
- Maximum PP expenditure per manifestation equal to Psion level.
- Power-level scaled saving-throw difficulty. The tabletop DC of
  `10 + power level + Intelligence modifier` has no Infinity Engine equivalent,
  so each generated effect carries a `savebonus` combining a power-level term
  of `-(level - 1)` with the `+2` key-ability modifier guaranteed by the
  Intelligence 15 chargen minimum. Intelligence above 15 does not further
  improve save difficulty; see below.
- Discipline, Intelligence, manifester-level and current-pool validation.
- Cancellation-safe two-phase PP transactions.
- Quickslot/action-bar configuration is excluded from PP transactions, so
  assigning a Psion power cannot reserve or spend points.
- Registered Psion quickspells are routed back through `SpellPressed` instead of
  GemRB's direct `SpellCast(-2, slot)` path. Each fresh quickslot attempt clears
  that actor's stale reservation first, so canceling target selection and trying
  again cannot make the retry commit PP on its first callback. Non-Psion
  quickspells retain the stock GemRB path.
- Runtime-filtered augmentation and choice lists.
- Collision-safe temporary selector resolution: GemRB's synthetic spellinfo
  type 255 is resolved exclusively from the temporary spell list before any
  ordinary memorized-spell lookup.
- Selector filtering happens after GemRB assigns synthetic `SpellIndex` values,
  so hidden choices leave index gaps instead of renumbering later legal choices.
- Separate fixed level 1–9 progression for every discipline.
- Nineteen known powers at level 9, including one exclusive discipline power
  whenever a new power tier becomes available.
- Complete custom-class progression support: the installed game's Mage XP row
  is inherited dynamically, THAC0 follows `20 - floor(level / 2)`, Lore gains 5
  per level, and the class receives two starting proficiency points plus one
  every four levels.
- Dedicated `SAVEPSI` saving-throw progression cloned from the active game's
  Mage table, with a +2 class bonus to saves against wands and spells while
  death, polymorph and breath saves remain unchanged.
- Character creation enforces Intelligence 15 while allowing every race and
  alignment supported by the game.
- One-pip weapon proficiency maximum for dagger, club, spear, quarterstaff,
  crossbow, dart and sling; all other weapon/style rows are disabled.
- Exact item usability through item-local opcode 319 restrictions: legal Psion
  weapons and their ammunition remain usable, while armor, shields, illegal
  weapons and inherited Mage-blocked nonweapons are rejected for all six
  Psion discipline classes.
- BG2-family starting-gold rows inherit the active game's Mage values rather
  than embedding campaign-specific constants.
- Throne of Bhaal starts receive Mage-equivalent `25STWEAP` starter equipment,
  with the standard twenty-slot table shape validated before mutation.
- ToB `LUNUMAB` rows keep HLA arithmetic valid while postponing HLA eligibility;
  version 1.0 intentionally does not implement epic Psion powers.
- Purpose-built resources for all sixty-one powers at levels 1–5.
- 142 registered augmentation or choice child resources, generated from the
  `psion_max_augment_cost` ceiling rather than hand-written.
- Backup-safe GemRB GUI-script installation and removal.
- Ownership-aware installation of the standalone `Psionics.py` runtime module.
- Read-only GUI compatibility preflight before the installer writes any file.

## Power-point transaction

GemRB invokes the spell-selection flow more than once while a target is being
chosen. Manifestation therefore uses a transaction:

1. The first matching callback validates and reserves the manifestation.
2. A matching confirmation callback deducts PP exactly once.
3. Cancelling target selection clears the pending transaction when a fresh
   spell/innate/quickslot attempt begins.
4. Repeated callbacks cannot intentionally charge the same manifestation twice.

The runtime revalidates selected child resources at confirmation time, so a
power cannot overspend merely because PP changed after opening a selector.
Temporary opcode-214 children are re-resolved from GemRB's raw spellinfo array at
confirmation, so a child that becomes unaffordable before commit is rejected
rather than being cast without its PP cost.

## Filtered selectors

Opcode-214 choice lists pass through the installed `Spellbook.py` hook. Only
choices registered in `PSIONAUGMENT.2DA` are filtered; base-game and third-party
selectors retain their order and behavior.

GemRB encodes temporary opcode-214 entries with synthetic spell type 255. Those
small selector indices can numerically overlap ordinary spellbook indices. The
Psion runtime therefore resolves type 255 exclusively from GemRB's temporary
spellinfo list, preventing an augmented child from being mistaken for a base
Psion power with the same index.

Affordability filtering is applied only after GemRB has constructed the full
temporary spellinfo list and assigned each entry its original synthetic index.
An unavailable earlier choice can therefore disappear from the UI without
changing the `SpellIndex` of any later legal choice; the resource charged by the
PP runtime remains the same resource GemRB casts.

Current selectors:

- **Energy Ray:** fire, cold, electricity and sonic variants costing 1–20 PP.
- **Mind Thrust:** 1d10–20d10 variants costing 1–20 PP.
- **Vigor:** 5–100 temporary-HP-equivalent variants costing 1–20 PP.
- **Swarm of Crystals:** 3d4–20d4 cone variants costing 3–20 PP.
- **Animal Affinity:** +4 Strength, Dexterity, Constitution or Charisma for
  3 PP each. Manifesting again for a different ability adds that bonus
  alongside the first, which is how the tabletop augment line is reached.

Ladders run to 20 PP because D&D 3.5 caps a single manifestation at the
manifester's level in power points. The ceiling is `psion_max_augment_cost` in
`psion/lib/power-data.tpa`; `psion/tools/generate_augment_tables.py` produces
`PSIONAUGMENT.2DA` and the selector tables from the same number, and CI checks
they agree.

## Power catalogue

### Level 1

Energy Ray, Mind Thrust, Inertial Armor, Vigor, Force Screen, Empty Mind,
Precognition, Astral Construct, Matter Agitation, Thicken Skin, Burst and
Psionic Charm.

### Level 2

Concealing Amorpha, Concussion Blast, Detect Hostile Intent, Thought Shield,
Biofeedback, Swarm of Crystals, Clairvoyant Sense, Psionic Repair Damage,
Energy Missile, Animal Affinity, Dimension Swap, Brain Lock and Energy Push.

### Level 3

Dispel Psionics, Body Adjustment, Energy Bolt, Mental Barrier, Touchsight, Time
Hop, Danger Sense, Ectoplasmic Cocoon, Energy Cone, Hustle, Dimension Slide and
Crisis of Breath.

### Level 4

Energy Adaptation, Freedom of Movement, Dimension Door, Intellect Fortress,
Telekinetic Maneuver, Power Leech, Remote Viewing, Wall of Ectoplasm, Energy
Ball, Metamorphosis, Fly (Psionic) and Dominate (Psionic).

### Level 5

Adapt Body, Catapsi, Power Resistance, Psychic Crush, True Seeing, Teleport,
Second Chance, Hail of Crystals, Energy Current, Psychofeedback, Baleful
Teleport and Mind Probe.

## Deliberate engine approximations

The Infinity Engine does not expose every D&D 3.5e psionic mechanism. The
following portable approximations are intentional and documented in source
comments and in-game descriptions:

- Will saves use save vs spell or broad BG saving-throw modifiers.
- Saving-throw difficulty scales with power level but not with the manifester's
  Intelligence. GemRB exposes no way to vary an installed SPL's `savebonus` by
  the caster's runtime stats: `ModifyEffect` only moves an effect's target
  coordinates, and `PrepareSpontaneousCast`, the one substitution hook, would
  need a separate resource per Intelligence bracket for all sixty-one powers.
  The guaranteed `+2` from the Intelligence 15 chargen minimum is baked in
  instead.
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
- Fly (Psionic) cannot cross arbitrary unwalkable map geometry.
- Psychic Crush deals heavy damage plus a brief hold rather than reducing the
  target to -1 hit points, which would be a save-or-die at the level it is
  reachable.
- Crisis of Breath approximates suffocation with damage, silence and slow;
  the engine has no suffocation mechanic.
- Matter Agitation is an Infinity Engine approximation on the level-1 damage
  budget rather than a transcription of the tabletop entry.
- Adapt Body does not provide portable fatigue immunity.
- Catapsi is stationary rather than following the manifester.
- Teleport relocates within the current area only.
- Second Chance uses an insight bonus instead of a true reroll callback.
- Energy Current does not stop when concentration is broken.
- Psychofeedback does not select exact ability transfers.
- Mind Probe does not display full statistics or scripted memories.
- Astral Construct uses a temporary wolf-derived creature body.
- Power learning is fixed by discipline rather than player-selected.
- Epic/high-level abilities are not implemented in 1.0; ToB safety rows defer
  HLA selection rather than borrowing another class's HLA table.

These are gameplay-scope limitations, not silent installer fallbacks.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory into the game directory.
3. Install the WeiDU component:

   `weidu psion/setup-psion.tp2`

4. Patch GemRB's shared GUI scripts and install the runtime module:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

Before modifying anything, the patcher renders all four shared-script changes in
memory. If a supported hook location or the required `import GemRB` insertion
point cannot be found, installation aborts without copying the runtime, creating
backups or partially modifying the GemRB installation. Rest hooks preserve the
exact indentation of the matched `GemRB.RestParty(...)` call.

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
- class XP, THAC0, saving throws, Lore, proficiency, ability-requirement and
  item-usability regression checks;
- parser-safety checks for unsupported WeiDU integer forms;
- fake-GemRB PP, selector and transaction tests;
- save/load PP-persistence tests that clear stat 239 while retaining the private
  serialized actor effect, including a true zero-PP state and rest refill;
- temporary type-255 selector-index collision tests;
- selector filtering tests that hide an earlier choice and verify later entries
  retain their original non-compacted `SpellIndex` values;
- confirmation-time raw-spellinfo revalidation when PP changes after selection;
- quickslot/action-bar configuration tests proving PP is not reserved or spent;
- Psion quickslot cancel/retry routing tests proving a canceled first phase
  cannot cause the next quickslot attempt to commit on its first callback;
- positive THAC0-bonus regression checks for Precognition and Second Chance;
- GUI patch install, idempotence, backup and uninstall fixtures;
- nested-rest indentation and rendered-Python compilation checks;
- read-only preflight failure tests that verify no partial files or backups are
  created;
- runtime-module replacement, restoration, creation and removal fixtures;
- dedicated level-3, level-4 and level-5 resource regression suites;
- Python compilation checks;
- official WeiDU 251 parsing of the TP2 and every TPA module;
- real WeiDU install, verification, uninstall and reinstall for normalized,
  native EE and legacy combined class-table layouts;
- a dedicated 20/41/40-column saving-throw lifecycle proving `SAVEPSI` preserves
  Mage death/polymorph/breath saves, improves wand/spell saves by 2, is removed
  on uninstall, leaves `SAVEWIZ` unchanged and reinstalls cleanly;
- semantic ITM fixtures proving legal Psion weapons remain usable while armor,
  shields and illegal items receive six class-targeted opcode-319 restrictions;
- a dedicated BG2/ToB startup lifecycle proving Mage-equivalent starting gold,
  twenty-slot starter equipment and nonzero no-HLA safety rows;
- binary validation of every generated Psion SPL header and effect range;
- byte-for-byte restoration checks for patched tables and semantic ITM fixtures;
- semantic preservation checks for all original TLK entries.

## Post-1.0 development

Future work can improve fidelity without changing the 1.0 installer contract:
choice-based power learning, dedicated Astral Construct assets and AI, exact
construct targeting, PP transfer, reroll and concentration callbacks, a travel
interface, psionic focus/feats/skills, psicrystals, dedicated psionic items,
enemy Psions and a true epic/HLA progression.
