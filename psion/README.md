# Experimental D&D 3e Psion for GemRB

This mod adds six selectable Psion disciplines to BG1-family conversions and
Enhanced Edition campaigns running through GemRB:

- Seer — Clairsentience
- Shaper — Metacreativity
- Kineticist — Psychokinesis
- Egoist — Psychometabolism
- Nomad — Psychoportation
- Telepath — Telepathy

## Implemented in 0.1.0-alpha

- Six dynamically allocated custom class rows.
- Released combined and newer split GemRB class-table layouts.
- D&D 3e base pool progression through level 20.
- Intelligence bonus pool: `floor(Int modifier × level / 2)`.
- Persistent current pool in GemRB actor stat 239.
- Full restoration after normal or temple rest.
- Spontaneous manifestation through the spell action bar.
- Base costs 1/3/5/7/9 for power levels 1–5.
- Manifester-level, discipline, skill, feat and augmentation metadata tables.
- Sixty installer-generated prototype powers across levels 1–5.
- A level-1-to-9 known-power progression matching 3e totals.
- Static Python/table validation.

## Important alpha limitations

This is a playable architecture and content prototype, not the final rules
implementation. Power resources currently clone thematically similar Infinity
Engine spells. The table names, costs, levels and discipline metadata are
custom, but exact augmentation choices and every tabletop effect still require
individual SPL implementation. All six disciplines currently share the first
19-power CLAB sequence; discipline-exclusive learning UI is planned next.

Pool cost is deducted when targeting begins. Cancelling targeting does not yet
refund it. No real WeiDU/GemRB installation was available during development,
so the source has static validation but still needs an in-game test pass.

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
class data used by this first implementation.

## Development priorities

1. Exact SPL effects and per-power augmentation variants.
2. Discipline-exclusive power selection and replacement at levels 4/8/12/16/20.
3. A dedicated manifestation/augmentation panel and current-pool display.
4. Psionic focus, feats and skill allocation UI.
5. Psicrystal, psionic items and enemy users.
6. Automated WeiDU installation fixtures and GemRB integration tests.
