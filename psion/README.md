# Experimental D&D 3e Psion for GemRB

This mod adds six selectable Psion disciplines to BG1-family conversions and
Enhanced Edition campaigns running through GemRB:

- Seer — Clairsentience
- Shaper — Metacreativity
- Kineticist — Psychokinesis
- Egoist — Psychometabolism
- Nomad — Psychoportation
- Telepath — Telepathy

## Implemented in 0.2.0-alpha

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
- Sixty installer-generated prototype powers across levels 1–5.
- Separate fixed progression for every discipline. Each class knows 19 powers
  by level 9 and gains its exclusive discipline power at levels 1, 3, 5, 7
  and 9.
- Static progression validation and GUI-patcher fixture tests.

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

This is a playable architecture and content prototype, not the final rules
implementation. Power resources currently clone thematically similar Infinity
Engine spells. The table names, costs, levels and discipline metadata are
custom, but exact augmentation choices and every tabletop effect still require
individual SPL implementation.

Power selection is fixed in this alpha. A later level-up interface will allow
players to choose general powers while enforcing one discipline power whenever
a new tier becomes available, plus replacement at levels 4/8/12/16/20.

The cancellation-safe point transaction follows GemRB's documented two-callback
spell flow and is covered by a GUI-script fixture, but it still requires an
in-game test against the exact GemRB build used by the player. No complete
WeiDU/GemRB installation was available during development.

## Installation

1. Run GemRB against the game once so `gemrb_path.txt` exists.
2. Copy the `psion` directory to the game directory.
3. Run `weidu psion/setup-psion.tp2`.
4. Patch GemRB's shared GUI scripts:

   `python psion/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts`

The patcher creates `.psion.bak` backups. Remove hooks with `--uninstall`.

## Supported targets

Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE and EET under GemRB.
Original BG1/TotSC are excluded because they lack native Sorcerer/Monk-era
class data used by this implementation.

## Development priorities

1. Exact SPL effects for the level 1 vertical slice: Energy Ray, Mind Thrust,
   Inertial Armor, Vigor and all six first-tier discipline powers.
2. Per-power augmentation variants and a dedicated cost-selection panel.
3. Choice-based power learning and replacement at levels 4/8/12/16/20.
4. Current/max pool display on the action and character-record interfaces.
5. Psionic focus, feats and skill allocation UI.
6. Psicrystal, psionic items and enemy users.
7. Automated WeiDU installation fixtures and GemRB integration tests.
