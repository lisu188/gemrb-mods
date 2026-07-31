# Changelog

## 0.6.0-alpha

- Replaced all twelve level-3 template clones with purpose-built SPL resources.
- Implemented Dispel Psionics, Body Adjustment, Energy Bolt, Mental Barrier,
  Touchsight, Time Hop, Danger Sense, Ectoplasmic Cocoon, Energy Cone, Hustle,
  Spatial Step and Mental Stasis.
- Added documented Infinity Engine approximations for fixed-level dispelling,
  Maze-based temporary removal, manual reaction defenses and a non-destructible
  cocoon shell.
- Added portable line and cone projectile handling with a classic projectile-ID
  fallback for Lightning Bolt layouts.
- Added non-stacking refresh protection to Mental Barrier, Touchsight, Danger
  Sense and Hustle.
- Restricted template spell cloning to powers of levels 4 and 5.
- Added a dedicated level-3 regression suite covering all twelve resources,
  hostile flags, durations, teleport mode, line/cone damage and non-stacking
  protections.
- Updated the core validator and installer version to 0.6.0-alpha.

## 0.5.0-alpha

- Replaced all twelve level-2 template clones with purpose-built SPL resources.
- Implemented Concealing Amorpha, Concussion Blast, Detect Hostile Intent,
  Thought Shield, Biofeedback, Swarm of Crystals, Clairvoyant Sense, Psionic
  Repair Damage, Energy Missile, Animal Affinity, Dimension Swap and Brain Lock.
- Added documented Infinity Engine approximations for miss chance, flat damage
  reduction, construct-only healing and discrete multi-target selection.
- Added Animal Affinity's Strength, Dexterity and Constitution selector forms.
- Registered three new 3-PP child resources, increasing the augmentation set
  from 54 to 57 resources.
- Reused the filtered selector and two-phase PP transaction for Animal Affinity.
- Prevented Strength, Dexterity and Constitution forms from stacking with one
  another.
- Corrected an audit-discovered Strength/Dexterity opcode inversion and added a
  regression check for the correct opcode mapping.
- Restricted template spell cloning to powers of level 3 and above.
- Expanded validation to cover every level-2 power, selector-table consistency,
  exact resource ownership and the new runtime choices.

## 0.4.0-alpha

- Added a backup-safe `Spellbook.py` GUI hook for temporary spell selectors.
- Filtered Psion augmentation children by current PP, manifester level,
  discipline and Intelligence before selector buttons are displayed.
- Preserved all non-Psion opcode-214 choices and their original order.
- Disabled augmented parent powers when no legal child can be manifested,
  preventing empty selectors at zero PP.
- Retained final validation when a child is selected, preventing overspending
  when PP changes after the selector was opened.
- Expanded fake-GemRB tests for mixed third-party/Psion spellinfo lists,
  zero-pool behavior and filtered selector ordering.
- Expanded GUI patcher fixtures to cover install, idempotence, backup and
  uninstall behavior for `Spellbook.py`.
- Documented all four patched GemRB GUI scripts and the selector data flow.

## 0.3.0-alpha

- Replaced all twelve level-1 template clones with purpose-built SPL resources.
- Implemented base effects for Energy Ray, Mind Thrust, Inertial Armor, Vigor,
  Force Screen, Empty Mind, Precognition, Astral Construct, Energy Push,
  Thicken Skin, Burst and Psionic Charm.
- Added non-stacking refresh protection to level-1 defensive powers.
- Added a temporary custom Astral Construct creature resource.
- Corrected two SPL-header bugs from earlier alpha versions: spell level now
  uses offset `0x34`, and cast-while-silenced flags use offset `0x18`.
- Added opcode-214 selectors for Energy Ray, Mind Thrust and Vigor.
- Added 54 point-scaled child resources and augmentation metadata:
  - 36 Energy Ray energy/cost variants;
  - 9 Mind Thrust damage/save variants;
  - 9 Vigor temporary-HP-equivalent variants.
- Mind Thrust now deals 1d10 per PP and improves its save penalty every 2 PP
  beyond the first.
- Vigor now grants 5 points per PP and removes every previous Vigor variant
  before applying the selected value.
- Extended the GUI hook to resolve powers from GemRB temporary spellinfo lists.
- Added fake-GemRB runtime tests for selector cost, reserve/commit accounting,
  manifester-level limits and legal variant filtering.
- Kept higher-level prototype cloning isolated from exact level-1 generation.
- Added static checks for level-1 resource coverage, required opcodes and the
  corrected SPL header fields.

## 0.2.0-alpha

- Added separate level 1–9 power progressions for all six disciplines.
- Added one exclusive discipline power whenever a new power tier unlocks.
- Matched cumulative powers-known totals at every BG1-accessible level.
- Added runtime checks for discipline ownership, Intelligence and manifester
  level before manifestation.
- Replaced immediate PP deduction with a two-phase reserve/commit transaction.
- Cancelled target selection no longer intentionally consumes PP, and repeated
  GemRB callbacks no longer intentionally double-charge the same power.
- Added GUI-patcher fixture tests and stronger table/progression validation.
- Expanded implementation and limitation documentation.

## 0.1.0-alpha

- Added six Psion discipline classes with dynamic class identifiers.
- Added D&D 3e pool and powers-known progressions.
- Added persistent Intelligence-based point accounting and rest restoration.
- Added 60 level 1–5 prototype power definitions.
- Added documented discipline, skill, feat and augmentation metadata.
- Added cross-platform GemRB GUI hook installer with backups and uninstall.
- Added static validation and documented current alpha limitations.
