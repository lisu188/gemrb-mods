# Experimental D&D 3e Psion for GemRB

This mod adds six selectable Psion disciplines to BG1-family conversions and
Enhanced Edition campaigns running through GemRB:

- Seer — Clairsentience
- Shaper — Metacreativity
- Kineticist — Psychokinesis
- Egoist — Psychometabolism
- Nomad — Psychoportation
- Telepath — Telepathy

## Implemented in 0.5.0-alpha

- Six dynamically allocated custom class rows.
- Released combined and newer split GemRB class-table layouts.
- D&D 3e base power-point progression through level 20.
- Intelligence bonus pool: `floor(Int modifier × level / 2)`.
- Persistent current pool in GemRB actor stat 239.
- Full restoration after normal or temple rest.
- Two-phase manifestation accounting: reserve before targeting and charge only
  after GemRB confirms the casting flow.
- Runtime validation of discipline, Intelligence, manifester level and current
  power points.
- Separate fixed progression for every discipline, reaching 19 powers known at
  BG1 level 9.
- Purpose-built resources for all twelve level-1 and all twelve level-2 powers.
- Point-scaled augmentation for Energy Ray, Mind Thrust and Vigor.
- Choice-based Animal Affinity with Strength, Dexterity and Constitution forms.
- Fifty-seven selector children with authoritative PP costs.
- Runtime filtering of opcode-214 lists so only currently legal variants are
  shown, while unrelated base-game and third-party selectors remain unchanged.
- Backup-safe GUI hooks with uninstall support.
- Static progression, 2DA schema, SPL-builder, fake-runtime transaction and
  GUI-patcher fixture tests.

## Power-point rules

The base costs are 1, 3, 5, 7 and 9 PP for power levels 1–5. A manifestation
cannot spend more PP than the character's Psion level. Selectors cost nothing;
the selected child resource carries the full cost and is validated twice:
when the choice list is built and again when the child is manifested.

PP are reserved on the first GemRB casting callback and deducted on the matching
second callback. Cancelling target selection does not intentionally consume PP,
and a duplicate callback cannot intentionally charge the same manifestation
twice.

## Purpose-built level-1 powers

- **Energy Ray:** energy and cost selector, 1–9 PP.
- **Mind Thrust:** 1d10 per PP; save vs spell negates.
- **Inertial Armor:** +4 Armor Class for one hour.
- **Vigor:** 5 temporary-HP-equivalent points per PP.
- **Force Screen:** +2 Armor Class and Magic Missile protection.
- **Empty Mind:** +2 to all saves for one round.
- **Precognition:** +1 attack, Armor Class and saves for three rounds.
- **Astral Construct:** summons the current construct prototype.
- **Energy Push:** electrical damage plus save-negated knockback.
- **Thicken Skin:** +1 Armor Class for one turn.
- **Burst:** +30 percent movement for one round.
- **Psionic Charm:** one-turn charm, save negates.

## Purpose-built level-2 powers

- **Concealing Amorpha:** Blur, +2 Armor Class and +1 saves for one turn.
- **Concussion Blast:** 2d6 magical force damage, no save.
- **Detect Hostile Intent:** detects invisibility, prevents backstab and grants
  +2 Armor Class for one turn.
- **Thought Shield:** +4 saves and 20 percent magical-damage resistance for
  three rounds.
- **Biofeedback:** 10 percent resistance to all four physical damage types for
  one turn.
- **Swarm of Crystals:** 3d4 slashing damage in a cone, save vs breath for half.
- **Clairvoyant Sense:** detects invisibility and grants +20 Find Traps for five
  rounds; quest scripts may add remote information.
- **Psionic Repair Damage:** heals 3d8+3. Construct-only target filtering remains
  a runtime task, so the alpha can target any ally.
- **Energy Missile:** 3d6 electrical damage with a save for half. The current
  area projectile approximates three discrete tabletop targets.
- **Animal Affinity:** choose +4 Strength, Dexterity or Constitution for one
  turn. Changing the choice refreshes the power rather than stacking forms.
- **Dimension Swap:** exchanges the manifester and target positions using
  GemRB's extended teleport opcode behavior.
- **Brain Lock:** holds one target for three rounds, save negates.

## Engine approximations

The Infinity Engine does not directly expose every D&D 3e mechanic. These
approximations are deliberate and documented in the in-game descriptions:

- Will saves use save vs spell or all five BG saving throws.
- Vigor uses timed current/maximum HP effects instead of native temporary HP.
- Concealment uses Blur plus AC and save bonuses instead of a generic miss
  chance percentage.
- Biofeedback uses percentage resistance rather than flat damage reduction.
- Repair Construct is not yet restricted to construct creatures.
- Energy Missile currently uses an area burst rather than three individually
  selected creatures.
- Astral Construct still uses a temporary wolf-derived body.

## Filtered choice lists

GemRB stores opcode-214 choices in a temporary spellinfo list. The installed
`Spellbook.py` hook passes that list through `Psionics.filter_spellinfo` before
buttons are created. Only rows registered in `PSIONAUGMENT.2DA` are filtered.

For a level-3 Psion with 2 PP remaining, Energy Ray, Mind Thrust and Vigor show
only their 1- and 2-PP children. Animal Affinity requires 3 PP, so it is hidden
or rejected when fewer than 3 PP remain. At zero PP an augmented parent does
not open an empty selector.

## Current level 1–9 progression

All disciplines share a conservative fixed alpha progression:

- Level 1: Energy Ray, Inertial Armor, first discipline power
- Level 2: Mind Thrust, Vigor
- Level 3: Concealing Amorpha, second discipline power
- Level 4: Force Screen, Detect Hostile Intent
- Level 5: Dispel Psionics, third discipline power
- Level 6: Body Adjustment, Energy Bolt
- Level 7: Energy Adaptation, fourth discipline power
- Level 8: Freedom of Movement, Intellect Fortress
- Level 9: Power Resistance, fifth discipline power

This matches the D&D 3e cumulative totals of 3, 5, 7, 9, 11, 13, 15, 17 and 19
powers known while preventing access to another specialist's discipline list.

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

## Important alpha limitations

Powers of levels 3–5 still clone thematically similar game spells. Power
selection is fixed rather than choice-based. The GUI hooks, extended teleport
behavior and generated resources still require a complete WeiDU installation
and in-game test against the intended GemRB build.

## Development priorities

1. Automated WeiDU installation fixture and real GemRB smoke test.
2. Exact level-3 power resources and augmentation.
3. Construct-only targeting and a dedicated Astral Construct CRE/AI.
4. Choice-based power learning and replacement at levels 4/8/12/16/20.
5. Current/max PP display on action and character-record interfaces.
6. Psionic focus, feats and skill allocation UI.
7. Psicrystal, psionic items and enemy users.
