# Changelog

## Unreleased

- Made Mage-progression extraction tolerant of stock BGEE's CRLF-formatted
  `XPLEVEL.2DA`, which WeiDU 251 otherwise miscounts as a single data row.
- Extended the fixed Psion progression from the BG1-accessible level-1–9 class
  rows to the complete class-level 1–20 powers-known table, ending at 36 unique
  known powers per discipline.
- Added 24 D&D 3.5e discipline powers at power levels 6–9: one Seer, Shaper,
  Kineticist, Egoist, Nomad and Telepath power at each new tier.
- Expanded `psionpowers.2da` to 85 catalogue powers with the complete base-cost
  ladder of 1, 3, 5, 7, 9, 11, 13, 15 and 17 PP.
- Filled all six CLAB tables through level 20. Each newly unlocked tier still
  grants exactly one matching discipline power at class levels 1, 3, 5, 7, 9,
  11, 13, 15 and 17.
- Assigned the previously installed-but-unreachable lower-tier resources across
  levels 10–20. CI now requires zero catalogue powers without a progression
  route instead of pinning a known stranded set.
- Added explicit portable Infinity Engine approximations for high-tier mechanics
  that require body swaps, persistent rebirth, movable force spheres, actor
  identity rewriting, arbitrary CRE merging, off-map information queries or
  persistent teleport destinations.
- Reworked Telekinetic Sphere, Crisis of Life and Tornado Blast so each coupled
  outcome is controlled by exactly one saving throw. Failed-save child SPLs
  contain the dependent control/protection/damage effects with no secondary
  saves.
- Added `validate_high_tier.py` to assert those parent/child contracts directly:
  one save on the parent, zero saves in the child, correct resource routing and
  exact 5+5 and 8+9 damage splits for Crisis of Life and Tornado Blast.
- Extended core validation through power level 9: exact catalogue membership,
  base PP costs, per-level powers-known totals, discipline unlocks, zero
  unreachable powers, builder ownership, save penalties and display-name/table
  consistency.
- Rewrote the README around the current 85-power catalogue and complete 1–20
  progression, including the high-tier power list and every documented engine
  approximation.

- Renamed four lower-tier powers to their Expanded Psionics Handbook names:
  Spatial Step to Dimension Slide, Spatial Disruption to Baleful Teleport,
  Compulsion to Dominate (Psionic) and Psionic Flight to Fly (Psionic).
- Settled `PS2RPRD` on the single name Psionic Repair Damage and removed obsolete
  prototype name/template/level arrays that duplicated `psionpowers.2da`.
- Moved Energy Push to its correct 2nd level as `PS2EPUS`, added Matter Agitation
  (`PS1MAGI`) as the Kineticist level-1 exclusive, replaced Mental Stasis with
  Crisis of Breath (`PS3CBRE`) and replaced Cognitive Overload with Psychic
  Crush (`PS5PCRU`).
- Corrected those SRD powers: Psychic Crush uses 3d6 rather than invented 8d6;
  Matter Agitation has no save and ramps 1 point/1d4/1d6; Crisis of Breath is
  Will-negates; Energy Push uses Reflex-half damage with separately approximated
  knockback semantics.

- Extended augmentation ladders to the manifester-level ceiling of 20 PP:
  Energy Ray runs 1–20 PP per energy type, Mind Thrust and Vigor 1–20, and Swarm
  of Crystals 3–20.
- Added Swarm of Crystals augmentation, added Charisma to Animal Affinity, fixed
  Animal Affinity sibling cancellation, and extended Vigor refresh stripping to
  the entire ladder.
- Replaced hand-written augmentation arrays with loops bounded by one
  `psion_max_augment_cost` constant plus `generate_augment_tables.py`; CI checks
  generated tables for drift.
- Removed the unused `AUGMENT_STEP` metadata from `psionpowers.2da` and runtime
  dictionaries.

- Added power-level save-difficulty scaling. Save-bearing effects encode the
  tier term plus the +2 key-ability modifier guaranteed by the Intelligence 15
  chargen minimum.
- Documented the remaining save-DC limitation: Intelligence above 15 increases
  PP but cannot yet dynamically alter an installed SPL's save bonus without a
  dedicated GemRB substitution/effect mechanism.
- Added validation requiring every save-bearing effect to carry the expected
  save penalty.

- Relabelled the implementation as D&D 3.5e, matching the Expanded Psionics
  Handbook tables it has always used.
- Corrected Force Screen to +4 AC, Power Resistance to `12 + manifester level`,
  Body Adjustment to flat 1d12 healing, and removed victim resistance from
  Ectoplasmic Cocoon.
- Removed the extra attack from Hustle, normalized energy-area saving throws to
  save vs breath, changed Baleful Teleport to save vs death, and added the
  missing hostile flags to Dispel Psionics.
- Extended validation with negative assertions against the corrected old values.

## 1.0.0

- Promoted the Psion component from alpha to the first installable release.
- Added self-contained `ADD_SPELL_HEADER` and `ADD_SPELL_EFFECT` implementations,
  removing undeclared community-library dependencies from stock WeiDU installs.
- Added official WeiDU 251 parsing for the complete TP2 and every included TPA.
- Corrected every parser-invalid bare negative integer and encoded absent string
  references with the explicit `0xffffffff` sentinel.
- Replaced the undeclared `game_is_iwdee` variable with WeiDU's `GAME_IS`
  predicate for cone-projectile selection.
- Corrected class-ID discovery to count and scan actual 2DA rows, export values
  across patch/action scope, and ignore long trailing GemRB comment lines.
- Added format-aware handling for normalized six-field, native EE ten-field and
  legacy nineteen-field class tables.
- Added explicit Psion class progression: dynamic inheritance of the installed
  Mage XP row, half-rate THAC0 progression, Lore 5/level, Intelligence 15
  chargen minimum, two starting proficiency points and one every four levels.
- Added a dedicated `SAVEPSI` table cloned from the installed game's Mage saving
  throws, preserving death/polymorph/breath progression while improving wand
  and spell saves by 2 across every available level column.
- Added exact one-pip weapon proficiency columns for dagger, club, spear,
  quarterstaff, crossbow, dart and sling, while disabling other weapon/style
  rows.
- Added item-local opcode-319 class restrictions so legal Psion weapons and
  ammunition remain usable while armor, shields, illegal weapons and inherited
  Mage-blocked nonweapons are rejected for all six discipline classes.
- Added BG2-family starting-gold rows cloned from the active game's Mage data.
- Added guarded Throne of Bhaal `25STWEAP` columns using the Mage starter package
  after validating GemRB's twenty-slot table shape.
- Added ToB `LUNUMAB` safety rows with nonzero rates and deferred HLA eligibility;
  version 1.0 intentionally does not borrow another class's HLA progression.
- Added generated, non-proprietary BG-family fixtures based on pinned GemRB demo
  data and GemRB's official CHITIN.KEY generator.
- Added full install, verification, uninstall and reinstall lifecycles for all
  three class-table layouts.
- Added a dedicated real-WeiDU saving-throw lifecycle across 20-, 41- and
  40-column tables, including `SAVEWIZ` preservation, `SAVEPSI` removal on
  uninstall and clean reinstall.
- Added a dedicated real-WeiDU BG2/ToB startup lifecycle covering starting gold,
  starter equipment, HLA safety rows and byte-for-byte uninstall restoration.
- Added semantic ITM fixtures proving exact item-usability restrictions and
  case-insensitive resource verification after WeiDU canonicalizes filenames.
- Added binary validation of every generated Psion SPL header, ability range and
  effect range.
- Added byte-for-byte uninstall restoration checks for patched tables and
  semantic preservation checks for every original TLK entry.
- Added case-insensitive fixture resource handling matching Infinity Engine
  lookup behavior on Linux.
- Installed the standalone `Psionics.py` runtime module ownership-safely: an
  existing module is backed up and restored, while a mod-created module is
  removed on uninstall.
- Added reusable PP-backed innate manifestations without touching unrelated
  innate abilities.
- Added read-only GUI-script preflight, missing-import detection and exact
  nested `RestParty` indentation preservation before any installation mutation.
- Moved PP initialization state out of engine stat 188 (`SUMMON_DISABLE_ACTION`)
  and encoded both the Psion signature and current PP solely in user stat 239.
- Made temporary opcode-214 type-255 token resolution exclusive to GemRB's
  spellinfo list, avoiding collisions with ordinary memorized spell indices.
- Preserved original synthetic type-255 `SpellIndex` values when hiding illegal
  selector children, so the resource charged for PP is the resource GemRB casts.
- Re-resolved temporary selector children from raw spellinfo at confirmation,
  preventing a child that becomes unaffordable from slipping through without
  its PP cost.
- Excluded quickslot/action-bar configuration from PP transactions and clear
  stale reservations during configuration instead of reserving or spending PP.
- Corrected review-discovered gameplay mappings: Mind Thrust save penalties,
  Animal Affinity ability opcodes, Burst/Hustle movement modes, Metamorphosis
  Strength, and positive THAC0 bonuses for Precognition and Second Chance.
- Added behavioral and static regressions for every review fix, including
  selector index gaps, single-stat zero-PP state and GUI installation rollback.
- Locked the release infrastructure, helper ordering and compatibility layouts
  into the version-neutral core validator.
- Updated installation, compatibility, validation and known-limitation
  documentation for the 1.0.0 release.

## 0.8.0-alpha

- Replaced all twelve level-5 template clones with purpose-built SPL resources.
- Implemented Adapt Body, Catapsi, Power Resistance, Cognitive Overload, True
  Seeing, Teleport, Second Chance, Hail of Crystals, Energy Current,
  Psychofeedback, Spatial Disruption and Mind Probe.
- Removed template-spell cloning completely; all sixty level 1–5 powers are now
  generated from empty SPL resources.
- Added documented portable approximations for world-map travel, true rerolls,
  maintained concentration, exact ability transfer, moving Catapsi fields and
  full Mind Probe inspection.
- Added delayed Energy Current pulses and non-stacking protection to applicable
  level-5 buffs.
- Replaced the accumulated monolithic validator with version-neutral core,
  fake-runtime and GUI-patcher test modules.
- Added a dedicated level-5 regression suite covering resource ownership,
  critical opcodes, delays, damage, saving throws, hostile flags and durations.
- Updated GitHub Actions to run six independent validation stages.

## 0.7.0-alpha

- Replaced all twelve level-4 template clones with purpose-built SPL resources.
- Implemented Energy Adaptation, Freedom of Movement, Dimension Door, Intellect
  Fortress, Telekinetic Maneuver, Power Leech, Remote Viewing, Wall of
  Ectoplasm, Energy Ball, Metamorphosis, Psionic Flight and Compulsion.
- Added explicit portable approximations for broad energy resistance, self-only
  fortress protection, casting-failure Power Leech, a single-node ectoplasmic
  wall, one-form Metamorphosis and two-dimensional flight.
- Corrected resource-patch iteration to use `PATCH_FOR_EACH`.
- Restricted prototype spell cloning to level 5 only.
- Added a dedicated level-4 regression suite and consolidated stale validator
  assertions.

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
- Restricted template spell cloning to power level 3 and above.
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
- Added D&D 3.5e pool and powers-known progressions.
- Added persistent Intelligence-based point accounting and rest restoration.
- Added 60 level 1–5 prototype power definitions.
- Added documented discipline, skill, feat and augmentation metadata.
- Added cross-platform GemRB GUI hook installer with backups and uninstall.
- Added static validation and documented current alpha limitations.
