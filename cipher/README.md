# Cipher for GemRB

A Pillars of Eternity-inspired single class for BG-family games running under GemRB.

## Release status

Current release metadata: **0.3.0**.

Automated validation covers the installer, Focus state machine, selectable powers, shared GUI lifecycle, Reaping Knives resource contracts, and the subclass framework. Real BGEE/BG2EE-family gameplay acceptance is handled separately by the repository-level `acceptance/` runner and still requires locally available game assets.

## Combat loop

Cipher begins each rest cycle with 20 Focus. Successful weapon hits against hostile creatures add 5 Focus; critical hits add another 5 Focus for 10 total. Maximum Focus is `20 + 5 × Cipher level`, capped by the runtime at level 30. Powers spend Focus through the shared two-phase transaction layer, so canceling target selection does not intentionally spend Focus.

Soul Whip adds +1 weapon damage at level 1, +2 at level 10, and +3 at level 20. This is the portable BG-family approximation of Pillars-style percentage weapon scaling.

Focus is represented in five-point units by permanent `CIFS<n>` actor effects and scripting state 165, so it survives normal save/load serialization. Weapon hit effects use SPLPROT hostility checks before advancing the Focus state machine.

Critical hits use GemRB's `CastSpellOnCriticalHit` hook and the same hostile-target gate.

## Reaping Knives

Version 0.3 completes the Reaping Knives Focus-transfer loop.

While the power is active, the buffed ally receives temporary `SetMeleeEffect` and `SetRangedEffect` hooks. GemRB copies those effects into the ally's weapon projectile. On a successful hit, the struck actor must pass the normal Cipher hostile-target SPLPROT relation; the resulting credit is then routed to the **original Cipher** and advances that Cipher's canonical Focus state by 5.

The implementation is scoped to the temporary Reaping Knives effect rather than a global item patch. Multiple instances therefore retain their own originating caster identity. Friendly and neutral targets do not generate Focus, Focus cannot exceed the normal cap, and expiry/dispel removes the transfer hook with the buff. A critical hit grants the same 5 Focus from Reaping Knives itself; Reaping Knives does not add a second critical-only transfer on top of that.

## Power progression

| Tier | Character level | Cost | Powers |
| --- | ---: | ---: | --- |
| I | 1 | 10 | Whisper of Treason, Eyestrike |
| II | 3 | 15 | Mental Binding, Psychovampiric Shield |
| III | 5 | 20 | Puppet Master, Soul Ignition |
| IV | 7 | 25 | Pain Block, Silent Scream |
| V | 9 | 30 | Borrowed Instinct, Detonate |
| VI | 11 | 35 | Disintegration, Amplified Wave |
| VII | 13 | 40 | Stasis Shell, Time Parasite |
| VIII | 16 | 50 | Reaping Knives, Soul Cascade |
| IX | 19 | 60 | Absolute Domination, Soul Collapse |

Cipher uses a reusable **Learn Cipher Power** selector. One powers-known credit is earned at levels 1, 3, 5, 7, 9, 11, 13, 16, and 19. Each credit may be spent on any currently unlocked unlearned power.

The selector uses harmless `CIL*` proxy resources that preserve the real power's display metadata while removing live effects and hostile-cast flags. Confirming a proxy learns the real power permanently; it does not manifest the power or spend Focus. Existing saves retain powers they already know.

Detonate installs a short-lived death watcher before its primary damage; a kill triggers an 8d6 soul burst around the corpse. Amplified Wave uses GemRB's prone-capable helpless state for its knockdown approximation. Soul Collapse installs a one-round HP-percentage condition and executes a target below 20 percent maximum hit points during that window.

## Subclass framework

Version 0.3 introduces a persistent optional subclass framework without duplicating the base Cipher runtime.

Subclass identity is stored in a private save-serialized actor effect. A Cipher that never selects a subclass remains behaviorally unchanged. The framework exposes bounded hooks for Focus gain, Focus cap, power cost, weapon effects, and passive resources while the base Cipher remains authoritative for Focus and normal power transactions.

### Soul Blade

The first implemented subclass is **Soul Blade**:

- +2 melee attack modifier while its passive is active;
- 1 worse Armor Class as the tradeoff;
- learns **Soul Annihilation**;
- Soul Annihilation spends 20 Focus through the transaction runtime and grants a one-round 125% melee-damage effect.

The choice is persistent per actor. Multiple Ciphers can therefore hold independent subclass state. The framework is deliberately structured so Beguiler and Ascendant can be added as additional data/runtime hooks rather than copied Cipher handlers.

## Class rules

- d8 hit points through `HPPRS`;
- Mage XP progression and saving throws;
- rogue-rate THAC0 progression (`20, 20, 19, 19, ...`);
- Intelligence 13 minimum;
- two starting weapon proficiency points;
- one-pip maximum in the configured Cipher weapon list;
- any alignment/race permitted by the active GemRB class layout;
- innate/mental power action-bar integration through `QSLOTS.2DA`;
- exact class-ID allocation from `CLSKILLS.2DA`, restricted to GemRB's sub-32 custom-class range.

## Installation

The recommended entry point is the repository/release driver:

```bash
python tools/gemrb_mods.py install cipher \
  --game /path/to/game \
  --guiscripts /path/to/GemRB/gemrb/GUIScripts \
  --weidu /path/to/weidu
```

Install Cipher and Psion together:

```bash
python tools/gemrb_mods.py install cipher psion \
  --game /path/to/game \
  --guiscripts /path/to/GemRB/gemrb/GUIScripts
```

The driver stages matching `common/` and class files, validates a release manifest when present, runs WeiDU, installs the shared GUI core, and installs `CipherSubclass.py` as an owned runtime dependency. Failure after partial installation triggers best-effort reverse rollback.

A self-contained release bundle can be built with:

```bash
python tools/gemrb_mods.py package cipher --output cipher-gemrb.zip
```

Low-level development installation remains supported: run `weidu cipher/setup-cipher.tp2`, then `python cipher/tools/install_guiscripts.py <GUIScripts>`.

Cipher and Psion share `GemRBModCore`. They can be installed in either order; uninstalling one preserves the shared hook while the other handler remains active.

## Deliberate approximations

- Soul Whip uses +1/+2/+3 weapon damage rather than percentage weapon-source scaling.
- The 18-power catalogue grants one powers-known credit per tier unlock rather than Pillars' denser progression.
- Amplified Wave uses GemRB's prone-capable helpless state rather than a dedicated Pillars prone mechanic.
- Soul Blade is the first subclass; Beguiler and Ascendant remain future framework clients rather than separate duplicated class implementations.

Reaping Knives Focus transfer, Detonate death-burst behavior, and Soul Collapse's low-HP execution path are implemented and are not listed as remaining limitations.

## Validation

```bash
python cipher/tests/validate.py
python cipher/tests/validate_extensions.py
bash cipher/tests/validate_weidu.sh
```

CI additionally installs, uninstalls, and reinstalls the component against pinned GemRB fixture layouts, validates shared GUI ownership, and checks the release/documentation invariants. Real-engine campaign acceptance remains a separate reproducible gate under `acceptance/`.
