# Enemy Psion runtime

## Engine contract

GemRB commit `dc975a69be0f048a9dfe01211fc8a183bccd58b3` provides
`GemRB.SetNonPartySpellCastCheck`. The callback runs once for an accepted
non-party scripted cast after target, range, line-of-sight and aura validation
and immediately before `SpellCore` or `SpellPointCore` begins casting. It
receives the caster global ActorID and resolved spell ResRef, may veto the cast,
or may return a replacement executable ResRef. Python failures are rejected by
the engine.

The GUIScript actor APIs accept a global ActorID, so the callback can use the
same Psion runtime functions as party actors without translating the identifier
or creating an NPC-only state store.

## Mod-side authority

`GemRBModCore.confirm_nonparty_spell(actor, resref)` leaves ordinary scripted
spells and non-Psion actors unchanged. For a recognized Psion power it:

1. calls `Psionics.manifestation_plan()` without mutating state;
2. vetoes requirements, manifester-level and PP failures;
3. calls `Psionics.commit_manifestation()` exactly once at the accepted-cast
   boundary;
4. returns the plan's exact-current-Intelligence executable ResRef to GemRB.

Player GUI casts continue through `SetSpellCastCheck` and the transaction
layer. Enemy casts do not touch player selectors, quickslots, `Spell` GUI
variables or pending player transactions. Both paths share the same PP ledger,
legality rules and save-DC variant generation.

The installed action-window initialization hook registers the nonparty callback
on the current GameControl, including after loading another game. Importing the
shared runtime during the main menu does not access a GameControl. On engines
without the new API it leaves the old behavior intact,
so installation remains compatible while enemy Psion casting requires the
documented engine contract.

## Deterministic AI fixture

`psionai.2da` defines the deliberately small regression policy used to exercise
four tactical roles without exposing the full catalogue to generic random AI:

- OFFENSE: `PS2CBLS`, enemy target;
- DEFENSE: `PS1IARM`, self target;
- CONTROL: `PS3THOP`, enemy target;
- MOBILITY: `PS3SSTP`, point target.

The table records minimum PP and reserve policy and is installed as
`PSIONAI.2DA`. Campaign encounter scripts can select from this bounded set and
cast the canonical power ResRef normally; the accepted-cast callback remains the
authority for affordability, exact-INT substitution and the once-only PP spend.

`psion/tests/validate_enemy_runtime.py` verifies callback registration, global
ActorID routing, native-spell bypass, non-Psion bypass, two exact-INT resource
variants, unaffordable veto, exactly-once commit, and registry coverage for
offensive, defensive, control and mobility roles.

`psion/tests/validate_enemy_psion_native.py` is the real-engine regression. It
spawns a non-party creature in the public GemRB demo, assigns the installed
PSION_NOMAD class, initializes canonical actor-local PP, executes a BCS
`ForceSpellRES` action targeting a separate friendly nonparty dummy by scripting
name, observes the actual nonparty accepted-cast callback with a hostile caster,
requires the INT-18 executable resource `PS3THOP4`, and checks five PP are spent
exactly once. A deterministic failing target save and zero magic resistance let
the fixture require the delivered `PS3THOP4` Maze effect and avatar removal,
so callback acceptance alone cannot pass. After checking delivery, the fixture
removes caster hostility and waits for the action list to empty and the combat
counter to reach zero before an ordinary save. No party actor is targeted by
Time Hop's Maze effect and no save restriction
is bypassed. After load it resolves the persistent nonparty caster through its
saved native owner/resource token and checks its scripting identity and committed
pool, rather than reusing a GlobalID from the previous game instance. The runner
records the actual engine checkout commit in its result. The fixture is
deliberately not placed into a campaign.

The public demo's sparse script dictionary is extended with the probe's native
trigger symbols. Its placeholder INTMOD is given native Maze duration columns,
so the delivered effect lasts six rounds instead of expiring immediately from
missing dice values. These fixture rules do not modify the installed power.

## Save/load semantics

Enemy PP and other Psion state use the same actor-local persistent effects as
player Psions. No pending Python transaction is required for a scripted cast:
state changes happen only at the engine's accepted-cast callback. A save therefore
contains only committed PP. After load, the next accepted scripted cast is
planned from the restored actor state; no quickslot or GUI reconstruction is
required.

This implementation proves non-party runtime support and a bounded encounter
policy. It does not automatically populate campaign areas with Psion enemies or
attempt a general tactical AI over all installed powers.
