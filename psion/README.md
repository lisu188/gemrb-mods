# Experimental D&D 3e Psion for GemRB

This mod adds six selectable Psion disciplines to BG1-family conversions and
Enhanced Edition campaigns running through GemRB:

- Seer — Clairsentience
- Shaper — Metacreativity
- Kineticist — Psychokinesis
- Egoist — Psychometabolism
- Nomad — Psychoportation
- Telepath — Telepathy

## Implemented in 0.4.0-alpha

- Six dynamically allocated custom class rows.
- Released combined and newer split GemRB class-table layouts.
- D&D 3e base power-point progression through level 20.
- Intelligence bonus pool: `floor(Int modifier × level / 2)`.
- Persistent current pool in GemRB actor stat 239.
- Full restoration after normal or temple rest.
- Two-phase manifestation accounting: reserve before targeting and charge only
  after GemRB confirms the casting flow, avoiding cancelled-target costs and
  duplicate callback charges.
- Runtime validation of class, discipline, Intelligence, manifester level and
  available power points.
- Base costs 1/3/5/7/9 for power levels 1–5.
- Manifester-level, discipline, skill, feat and augmentation metadata tables.
- Separate fixed progression for every discipline. Each class knows 19 powers
  by level 9 and gains its exclusive discipline power at levels 1, 3, 5, 7
  and 9.
- Purpose-built level-1 resources for all twelve first-tier powers.
- Point-scaled augmentation for Energy Ray, Mind Thrust and Vigor.
- Fifty-four augmentation child resources with runtime cost enforcement.
- Runtime filtering of opcode-214 choice lists so unaffordable Psion variants
  are hidden without changing unrelated selectors from the base game or other
  mods.
- Static progression, 2DA schema, SPL-builder, fake-runtime transaction and
  GUI-patcher fixture tests.

## Exact level-1 vertical slice

The following powers no longer inherit unrelated effects from existing wizard
or priest spells:

- **Energy Ray:** opens an energy/cost selector described below.
- **Mind Thrust:** opens a 1–9 PP damage and save-DC selector.
- **Inertial Armor:** +4 Armor Class for one hour, non-stacking.
- **Vigor:** opens a 1–9 PP temporary-HP-equivalent selector.
- **Force Screen:** +2 Armor Class and Magic Missile protection for one turn.
- **Empty Mind:** +2 to all saves for one round.
- **Precognition:** +1 attack, Armor Class and saves for three rounds.
- **Astral Construct:** summons a temporary controlled construct prototype.
- **Energy Push:** 1d6 electrical damage plus save-negated knockback.
- **Thicken Skin:** +1 Armor Class for one turn.
- **Burst:** +30% movement speed for one round.
- **Psionic Charm:** charms one humanoid for one turn, save vs spell negates.

Several effects are deliberate Infinity Engine approximations. BG has no
separate Will save, no native temporary-hit-point pool, and no fully generic
D&D 3e construct body. Empty Mind therefore modifies all five saves, Vigor
uses timed maximum/current HP effects, and Astral Construct currently uses a
renamed wolf-derived creature that will be replaced by a dedicated CRE.

## Implemented augmentation

Every augmented parent is a free opcode-214 selector. The chosen child resource
reserves its total cost on the first casting callback and spends it on the
matching second callback. Total cost cannot exceed manifester level and must be
available in the current PP pool.

### Energy Ray

Energy Ray offers four energy types at total costs from 1 through 9 PP:

- **Fire:** one d6 per PP, plus 1 damage per die.
- **Cold:** one d6 per PP.
- **Electricity:** one d6 per PP.
- **Sonic:** one d4 per PP, represented as magical damage by the engine.

### Mind Thrust

Mind Thrust deals one d10 per PP. A save vs spell negates all damage. The save
penalty improves by 1 for every 2 PP spent beyond the first, approximating the
D&D 3e augmentation that raises the power's save DC.

### Vigor

Vigor grants 5 temporary-hit-point-equivalent points per PP for one turn. Every
variant removes the effects of all nine other Vigor variants before applying
its own value, so changing the amount refreshes the power instead of stacking
multiple pools.

### Filtered choice lists

GemRB stores opcode-214 choices in a temporary spellinfo list. The installed
`Spellbook.py` hook passes that list through `Psionics.filter_spellinfo` before
buttons are created. Only resources registered as children in
`PSIONAUGMENT.2DA` are filtered. Ordinary temporary spell selectors remain in
their original order and are not modified.

For a level-3 Psion with 2 PP remaining, the selector therefore displays only
1- and 2-PP children. At zero PP the augmented parent is rejected instead of
opening an empty choice list. The final child resource is still validated again
when selected, so a pool change between opening the list and choosing a power
cannot overspend points.

## Current level 1–9 progression

All disciplines share a deliberately conservative set of general powers:

- Level 1: Energy Ray, Inertial Armor, first discipline power
- Level 2: Mind Thrust, Vigor
- Level 3: Concealing Amorpha, second discipline power
- Level 4: Force Screen, Detect Hostile Intent
- Level 5: Dispel Psionics, third discipline power
- Level 6: Body Adjustment, Energy Bolt
- Level 7: Energy Adaptation, fourth discipline power
- Level 8: Freedom of Movement, Intellect Fortress
- Level 9: Power Resistance, fifth discipline power

This reaches the D&D 3e totals of 3, 5, 7, 9, 11, 13, 15, 17 and 19 powers
known while keeping every specialist isolated from the other five discipline
lists.

## Important alpha limitations

Level-1 powers now have dedicated resources, but powers of levels 2–5 still
clone thematically similar Infinity Engine spells. Most powers still lack
augmentation variants and several tabletop secondary effects require engine
approximations.

Power selection is fixed in this alpha. A later level-up interface will allow
players to choose general powers while enforcing one discipline power whenever
a new tier becomes available, plus replacement at levels 4/8/12/16/20.

The cancellation-safe point transaction and filtered selector are covered by
GUI-script and fake-runtime fixtures, but both still require an in-game test
against the exact GemRB build used by the player. No complete WeiDU/GemRB
installation was available during development.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory to the game directory.
3. Run `weidu psion/setup-psion.tp2`.
4. Patch GemRB's shared GUI scripts:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

The patcher updates `ActionsWindow.py`, `Spellbook.py`, `MenuWindow.py` and
`GUISTORE.py`, creating a `.psion.bak` backup for each. Remove all hooks with
`--uninstall`.

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE and EET under GemRB.
Original BG1/TotSC are excluded because they lack native Sorcerer/Monk-era
class data used by this implementation.

## Development priorities

1. Exact level-2 power resources and their legal augmentation paths.
2. Add augmentation variants to discipline powers and remaining general powers.
3. Replace the temporary Astral Construct body with a dedicated CRE and AI.
4. Choice-based power learning and replacement at levels 4/8/12/16/20.
5. Current/max pool display on the action and character-record interfaces.
6. Psionic focus, feats and skill allocation UI.
7. Psicrystal, psionic items and enemy users.
8. Automated WeiDU installation fixtures and GemRB integration tests.
