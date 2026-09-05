# Cipher for GemRB

A Pillars of Eternity-inspired single class for BG-family games running under GemRB.

**Current version: `0.2.0`**

Repository-level support status is tracked in [the compatibility matrix](../docs/compatibility.md).

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

Cipher 0.2 replaces the fixed pair of powers at each tier with a reusable **Learn Cipher Power** selector. A new powers-known credit is earned whenever a new tier unlocks (levels 1, 3, 5, 7, 9, 11, 13, 16, and 19), for nine chosen powers by level 19. Each credit may be spent on any currently unlocked power rather than being forced into the newest tier. This reduced cadence is intentional: the current catalogue contains only two powers per tier, so the much denser original Pillars progression would exhaust the available catalogue too quickly.

The selector uses harmless `CIL*` proxy resources that preserve the chosen power's name, description, and icon but contain no live effects. The runtime converts the confirmed proxy into a permanently learned real `CI*` power. Canceling the selector does not consume a choice and learning never spends Focus or manifests the selected power. Existing saves from Cipher 0.1 keep all powers they already know; migration never removes powers, and an old character only receives the selector if its number of known powers is below the new level-based allowance.

Detonate installs a short-lived death watcher before its primary damage. If that damage kills the target, the original Cipher fires an 8d6 crushing soul burst around the corpse. Amplified Wave uses GemRB's prone-capable helpless state to play the knockdown/get-up sequence for one round after a failed save. Soul Collapse installs a one-round GemRB HP-percentage condition and executes a target that is below 20 percent of maximum hit points during that window.

Reaping Knives routes each cast through an internal owner-specific variant. Successful melee or ranged hits by a non-Cipher ally against hostile creatures grant 5 Focus to the originating Cipher. Critical hits grant the same single 5-Focus transfer rather than a second Reaping Knives critical bonus. The owner marker and ally attack hooks are ordinary timed actor effects, so multiple Ciphers do not cross-credit one another and the relationship survives normal save/load serialization. Casting Reaping Knives on a Cipher still grants the attack/damage buff but suppresses the transfer hook because that attacker already receives normal Soul Whip Focus.

## Installation

Cipher uses the repository's shared GemRB runtime infrastructure. A distributable/install tree must therefore contain both `cipher/` and its sibling `common/` directory:

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

The GUI hook is required. It makes Cipher innate powers reusable, enforces Focus costs with reserve/commit semantics, restores 20 Focus on rest, filters the power-learning selector, and routes Cipher quickslots through the same transaction path.

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

## Deliberate approximations in 0.2

- Soul Whip uses +1/+2/+3 weapon damage rather than PoE-style percentage weapon scaling because the supported BG-family effect model does not expose a portable weapon-source-only percentage modifier.
- The reduced 18-power catalogue grants one powers-known credit per tier unlock rather than reproducing Pillars' denser level-by-level power acquisition.
- Amplified Wave uses GemRB's prone-capable helpless state (including the knockdown/get-up animation) because BG-family data does not expose a separate portable PoE-style prone effect.
- Beguiler, Soul Blade, and Ascendant are not implemented.

## Validation

Static/runtime checks:

```bash
python cipher/tests/validate.py
python cipher/tests/validate_reaping_knives_runtime.py
```

WeiDU parser checks, with WeiDU in `PATH`:

```bash
bash cipher/tests/validate_weidu.sh
```

CI additionally installs, uninstalls, and reinstalls the component against the repository's pinned GemRB fixture in normalized, native, and legacy class-table layouts. The fixture checks class registration, THAC0, persistent Focus setters, corrected attack modifiers, hostile-only normal/critical/Reaping-Knives Focus injection, shared GUI lifecycle behavior, selectable-power proxy generation and rollback, Detonate/Amplified Wave/Soul Collapse high-tier resources, item restrictions, and WeiDU rollback of patched items and IDS resources.

These automated checks are the current release evidence; the real-engine cross-mod acceptance suite is tracked separately in #50.

### Reaping Knives owner identity

New casts use an owner token saved on the Cipher, not the actor's current party
slot. The game-global allocation counter and actor effect survive save/reload.
Party reordering, dismissal and rejoining do not transfer an existing token to a
different Cipher. Recasting reuses the same identity, including when older buffs
remain on other allies. Allocation is immediate and validated before preparing
the cast; failures stop casting rather than falling back to a portrait slot.

The generated resource bank supports 249 distinct Reaping Knives owners per
save (tokens 7–255). This is a lifetime-owner limit, not a cast limit. Exhaustion
fails closed, while already registered owners can continue casting. Tokens 1–6
are reserved for pre-upgrade resources and never allocated by the new runtime.
Allow existing pre-upgrade Reaping Knives effects to expire before testing the
new routing. Imported or manually edited character/save combinations require
separate qualification; corrupted or inconsistent identity records are rejected.
