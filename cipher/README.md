# Cipher for GemRB

A Pillars of Eternity-inspired single class for BG-family games running under GemRB.

## Combat loop

Cipher does not use spell slots or per-rest power charges. It begins each rest cycle with 20 Focus, successful weapon hits against hostile creatures add 5 Focus, critical hits add another 5 Focus for 10 total, and psychic powers spend Focus. Maximum Focus is `20 + 5 × Cipher level`, capped by the runtime at level 30.

Soul Whip adds +1 weapon damage at level 1, +2 at level 10, and +3 at level 20. This is the portable BG-family approximation of PoE's percentage weapon-damage scaling: GemRB's common weapon damage bonus is applied only during weapon damage calculation, while percentage damage opcodes are damage-type based rather than weapon-source based.

Focus is stored in scripting state stat 165 in five-point units. Each Focus value is represented by one permanent `CIFS<n>` actor effect so it survives normal save/load serialization. Weapon abilities carry an `ApplyEffectsList` hit effect that evaluates the struck creature against the weapon user through SPLPROT's caster↔target EA relation (`0x108`). Only hostile targets pass that gate. `CIFGAIN` is then applied with the weapon user preserved as caster; its self-targeted class gate and descending state dispatch advance Focus on the Cipher by exactly one unit without cascading multiple increments in the same hit.

Critical hits use GemRB's `CastSpellOnCriticalHit` actor hook. The installer exposes that hook through opcode `0x155` for both EE and classic GemRB profiles, and all three Soul Whip tiers attach `CIFCRIT`. `CIFCRIT` runs the same hostile-target gate before adding the second +5 Focus. Normal hit and critical bonus transitions are independently capped by the same Focus state machine. Rest and power spending use the same state-transition spells.

## Power progression

| Tier | Character level | Cost | Powers |
|---|---:|---:|---|
| I | 1 | 10 | Whisper of Treason, Eyestrike |
| II | 3 | 15 | Mental Binding, Psychovampiric Shield |
| III | 5 | 20 | Puppet Master, Soul Ignition |
| IV | 7 | 25 | Pain Block, Silent Scream |
| V | 9 | 30 | Borrowed Instinct, Detonate |
| VI | 11 | 35 | Disintegration, Amplified Wave |
| VII | 13 | 40 | Stasis Shell, Time Parasite |
| VIII | 16 | 50 | Reaping Knives, Soul Cascade |
| IX | 19 | 60 | Absolute Domination, Soul Collapse |

The initial implementation grants a fixed pair of powers at each tier. A power-selection UI is intentionally deferred until the core resource loop is stable.

## Installation

Cipher now uses the repository's shared GemRB runtime infrastructure. A distributable/install tree must therefore contain both `cipher/` and its sibling `common/` directory:

```text
game/
├── common/
└── cipher/
```

Copy both directories from the same release/repository revision into the game directory. Installing only `cipher/` is not supported because the WeiDU helper and GUI installer are shared from `common/`.

Install the WeiDU component:

```bash
weidu cipher/setup-cipher.tp2
```

Then patch the GemRB GUI scripts:

```bash
python cipher/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts
```

The GUI hook is required. It makes Cipher innate powers reusable, enforces Focus costs with reserve/commit semantics, restores 20 Focus on rest, and routes Cipher quickslots through the same transaction path.

Psion and Cipher share one `GemRBModCore` GUI layer. They may be installed in either order. Removing one handler leaves the shared GUI layer active for the other; the original GemRB scripts and shared runtime files are restored only after the last active handler is removed.

## Class rules

- d8 hit points through `HPPRS`
- Mage XP progression and saving-throw table
- rogue-rate THAC0 progression (`20, 20, 19, 19, ...`)
- Intelligence 13 minimum
- two starting weapon proficiency points, one pip maximum in the configured Cipher weapon list
- any alignment and race allowed by the active GemRB class layout
- innate/mental power action-bar integration through `QSLOTS.2DA`
- class ID allocation follows the exact `CLSKILLS.2DA` row index and is restricted to GemRB's sub-32 custom-class range; the installer validates class-table, `CLASS.IDS`, and positional `QSLOTS.2DA` identity before mutation
- combined versus split class tables are detected from `CLASSES.2DA`, including native EE 9/10-column `CLASTEXT.2DA` layouts even when `HPCLASS.2DA` is present

## Deliberate approximations in 0.1

- Soul Whip uses +1/+2/+3 weapon damage rather than PoE-style percentage weapon scaling because the supported BG-family effect model does not expose a portable weapon-source-only percentage modifier.
- Reaping Knives grants its ally attack/damage enhancement but does not yet transfer Focus from that ally's attacks.
- Amplified Wave represents knockdown with a one-round hold.
- Detonate implements the direct psychic damage but not the on-death secondary explosion.
- Soul Collapse omits the conditional execute below 20% HP.
- Power choice on level-up, Beguiler, Soul Blade, and Ascendant are not part of this first core implementation.
- Armor/shield usability has not yet been narrowed to the final light-armor/no-shield design; the class table and Focus mechanics are implemented first to avoid global item-usability changes before playtesting.

## Validation

Static/runtime checks:

```bash
python cipher/tests/validate.py
```

WeiDU parser checks, with WeiDU in `PATH`:

```bash
bash cipher/tests/validate_weidu.sh
```

CI additionally installs, uninstalls, and reinstalls the component against the repository's pinned GemRB fixture in normalized, native, and legacy class-table layouts. The fixture checks class registration, THAC0, persistent Focus setters, corrected attack modifiers, hostile-only normal and critical Focus injection, shared GUI lifecycle behavior, and WeiDU rollback of patched items and IDS resources.
