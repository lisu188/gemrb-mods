# Changelog

## Unreleased

- Renamed four powers to their Expanded Psionics Handbook names: Spatial Step
  to Dimension Slide, Spatial Disruption to Baleful Teleport, Compulsion to
  Dominate (Psionic) and Psionic Flight to Fly (Psionic). Resrefs are
  unchanged; `PS5BALT` already read as Baleful Teleport.
- Settled Psionic Repair Damage on one name. `PS2RPRD` was called
  `REPAIR_CONSTRUCT` in `psionpowers.2da`, `Repair Construct` in
  `power-data.tpa` and `Psionic Repair Damage` in its builder.
- Deleted the `psion_power_name`, `psion_power_template` and
  `psion_power_level` arrays from `power-data.tpa`. Nothing in the repository
  read them; they were prototype scaffolding duplicating `psionpowers.2da`, and
  that duplication is how the `PS2RPRD` naming drifted unnoticed.
- Added a `validate_core.py` invariant that pins `psionpowers.2da`'s `NAME`
  column to the builders' `ps_name`. The column is never read at runtime, so it
  could previously drift without symptom. The walk covers every module under
  `lib/`, which is what catches the three augment parents that are built twice.
- Moved Energy Push to its correct 2nd level as `PS2EPUS`, at 3 PP and 2d6.
- Added Matter Agitation (`PS1MAGI`) as the Kineticist's level-1 exclusive.
  Energy Push held that slot, and the progression invariant requires exactly
  one discipline exclusive per odd character level at the tier maximum, so
  moving Energy Push had to be paired with a replacement rather than a reslot.
- Replaced Mental Stasis with Crisis of Breath (`PS3CBRE`) and Cognitive
  Overload with Psychic Crush (`PS5PCRU`). Neither replaced power was an EPH
  power; Mental Stasis's own comment admitted its name came from the prototype
  catalogue, and no CLAB table granted Cognitive Overload, so no character
  could learn it.
- The power catalogue grows from 60 to 61 entries.
- Kept Energy Push learnable after its level change. It moved out of the
  Kineticist's level-1 row, and levels 1-9 are count-pinned and full, so it
  takes the Kineticist's level-4 slot from Detect Hostile Intent, which five
  other disciplines still grant.
- Added a `validate_core.py` invariant pinning the set of powers no CLAB table
  grants. Sixteen powers are built but unreachable while CLAB rows 10-20 stay
  empty; pinning the set means stranding a further power fails CI instead of
  shipping unnoticed, and the README now lists them.
- Corrected all four new powers against the SRD, which turned out to be
  readable from a GitHub mirror after every conventional mirror was refused by
  this environment's network policy. Each had been written from search snippets
  and each was wrong:
  - Psychic Crush dealt an invented 8d6; the tabletop figure is 3d6, and it
    lands regardless of the save rather than being halved by it.
  - Matter Agitation allows no saving throw and ramps 1 point, then 1d4, then
    1d6 over three rounds. It had a save for half, a flat 1d6 and an Armor
    Class penalty with no basis in the power at all.
  - Crisis of Breath is "Will negates", so its save negates outright rather
    than halving.
  - Energy Push is "Reflex half" on the damage with the knockback gated on a
    Strength check. The build had the saves the other way round: damage
    unavoidable, knockback avoidable.
- Added assertions pinning the corrected figures, so the invented 8d6 and a
  halving save on Crisis of Breath both fail CI if reintroduced.

- Extended every augmentation ladder to the manifester-level cap of 20 power
  points. The cap was already enforced correctly, but each ladder stopped at
  9 PP, so a Psion above level 9 could never reach it. Energy Ray now runs
  1-20 PP per energy type, Mind Thrust and Vigor 1-20, and Swarm of Crystals
  3-20. Generated augment children go from 57 to 142.
- Added the missing Swarm of Crystals augmentation (+1d4 per additional power
  point). It is now an opcode-214 selector built by `swarm-augment.tpa`, and
  the dead direct build has been removed from `level2-powers.tpa` rather than
  left to be deleted and rebuilt during install.
- Fixed Animal Affinity so its augment line is reachable. Each child now strips
  only its own resource instead of all its siblings, so boosting a second
  ability no longer cancels the first, and Charisma joins Strength, Dexterity
  and Constitution as a legal choice.
- Extended the Vigor refresh strip to the whole ladder. It covered only the
  first nine tiers, so a 10 PP or higher Vigor would have stacked on top of a
  lower one instead of replacing it.
- Replaced the hand-written augmentation arrays with loops bounded by a single
  `psion_max_augment_cost` constant in `power-data.tpa`, and added
  `psion/tools/generate_augment_tables.py` as the sole producer of the checked-in
  table data. The ladder was previously written out three times -- the augment
  table, the selector tables and the WeiDU arrays -- which does not scale to 142
  rows. CI now runs the generator's `--check` mode so the committed tables
  cannot drift from the constant.
- Removed the `AUGMENT_STEP` column from `psionpowers.2da` and `Psionics.py`.
  It was read into the runtime dictionary and never used.

- Added saving-throw difficulty scaled by power level. Previously every
  generated effect left `savebonus = 0`, so neither a power's level nor the
  manifester's Intelligence had any bearing on whether it landed — Intelligence
  bought power points and nothing else. Each save-bearing effect now carries a
  `savebonus` combining a power-level term of `-(level - 1)` with the `+2`
  key-ability modifier guaranteed by the Intelligence 15 chargen minimum.
- Documented why Intelligence above 15 cannot improve save difficulty: GemRB
  exposes no way to vary an installed SPL's `savebonus` by the caster's runtime
  stats. `ModifyEffect` only moves an effect's target coordinates, and
  `PrepareSpontaneousCast`, the one substitution hook, would require a separate
  resource per Intelligence bracket across all sixty-one powers.
- Added a `validate_core.py` invariant that pins the per-level constants and
  fails if any save-bearing effect is left without its penalty.

Rules-fidelity corrections from a review against the D&D 3.5 Expanded Psionics
Handbook. The core economy (power-point table, powers known, `(2 x level) - 1`
base costs, the manifester-level spending cap and the `Int >= 10 + power level`
requirement) was already correct and is unchanged.

- Relabelled the component, README, changelog and source comments as D&D 3.5e.
  The implemented tables were always the 3.5 Expanded Psionics Handbook ones;
  only the label said 3e.
- Corrected Force Screen to the tabletop +4 shield bonus, up from +2.
- Corrected Power Resistance to `12 + manifester level` (21 at the first legal
  manifestation level), down from an incorrect `20 + manifester level`.
- Corrected Body Adjustment to heal a flat 1d12, removing a +5 rider that the
  tabletop power does not have.
- Removed the damage resistance Ectoplasmic Cocoon granted to its own victim.
  The shell's hardness belongs to the cocoon, not the trapped creature, so the
  power was making held targets harder to kill.
- Removed the extra attack from Hustle. The tabletop power grants an extra move
  action, which the existing doubled movement already approximates.
- Normalised energy-area saving throws to save vs breath, the mod's Reflex
  proxy: Energy Missile, Energy Ball and Energy Current now match Swarm of
  Crystals, Energy Bolt and Energy Cone.
- Changed Baleful Teleport (`PS5BALT`) to save vs death, the mod's Fortitude
  proxy, matching the tabletop power's Fortitude save.
- Added the missing hostile spell flags to Dispel Psionics, which every other
  offensive level-3 power already set.
- Extended the validation suites to lock in each correction, including negative
  assertions against the previous values.

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
