# Changelog

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
