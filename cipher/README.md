# Cipher for GemRB

A Pillars of Eternity-inspired single class for BG-family games running under GemRB.

## Combat loop

Cipher does not use spell slots or per-rest power charges. It begins each rest cycle with 20 Focus, successful melee or projectile weapon hits add 5 Focus, and psychic powers spend Focus. Maximum Focus is `20 + 5 × Cipher level`, capped by the runtime at level 30.

Soul Whip increases all damage by 10% at level 1, 15% at level 10, and 20% at level 20.

Focus is stored in scripting state stat 165 in five-point units. Weapon abilities trigger an internal spell on successful impact; opcode 326 gates that spell to the Cipher class, and a descending state dispatch advances the Focus state by exactly one unit without cascading multiple increments in the same hit.

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

Install `cipher/setup-cipher.tp2` with WeiDU against a BG-family game configured for GemRB. After the WeiDU component is installed, patch the GemRB GUI scripts:

```bash
python cipher/tools/install_guiscripts.py /path/to/GemRB/gemrb/GUIScripts
```

The GUI hook is required. It makes Cipher innate powers reusable, enforces Focus costs with reserve/commit semantics, restores 20 Focus on rest, and routes Cipher quickslots through the same transaction path.

If the Psion GUI patch is also used, install the Psion GUI patch first and the Cipher GUI patch second. Uninstall them in reverse order so each patcher's byte-for-byte backup restores the expected previous layer.

## Class rules

- d8 hit points through `HPPRS`
- Mage XP progression and saving-throw table
- rogue-rate THAC0 progression
- Intelligence 13 minimum
- two starting weapon proficiency points, one pip maximum in the configured Cipher weapon list
- any alignment and race allowed by the active GemRB class layout
- innate/mental power action-bar integration through `QSLOTS.2DA`

## Deliberate approximations in 0.1

- Critical hits currently generate the same +5 Focus as other successful hits; the proposed +10 critical-hit rule needs a reliable engine-level critical discriminator.
- Reaping Knives grants its ally attack/damage enhancement but does not yet transfer Focus from that ally's attacks.
- Amplified Wave represents knockdown with a one-round hold.
- Detonate implements the direct psychic damage but not the on-death secondary explosion.
- Soul Collapse omits the conditional execute below 20% HP.
- Power choice on level-up, Beguiler, Soul Blade, and Ascendant are not part of this first core implementation.
- Armor/shield usability has not yet been narrowed to the final light-armor/no-shield design; the class table and Focus mechanics are implemented first to avoid global item-usability changes before playtesting.
- Successful attacks against non-hostile creatures can currently generate Focus because the on-hit effect is attached to weapon abilities rather than an allegiance-filtered victim callback.

## Validation

Run:

```bash
python cipher/tests/validate.py
```

The validator checks the tier/cost table against CLAB grants, verifies the Focus opcode chain and installer wiring, exercises reserve/commit Focus spending with a mocked GemRB runtime, compiles both Python modules, and tests GUI patch idempotence.
