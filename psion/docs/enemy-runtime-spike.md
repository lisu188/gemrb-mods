# Enemy Psion runtime

## Engine contract

GemRB commit `5e5f45da0d801674174a118aad9d5c49ec224542` provides
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

`GemRBModCore` installs the non-party callback when the shared runtime module
is imported. On engines without the new API it leaves the old behavior intact,
so installation remains compatible while enemy Psion casting requires the
documented engine contract.

## Deterministic AI fixture

`psionai.2da` defines the deliberately small regression policy used to exercise
four tactical roles without exposing the full catalogue to generic random AI:

- OFFENSE: `PS1ERAY`, enemy target;
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
PSION_SEER class, initializes canonical actor-local PP, executes a BCS
`Spell(Player1,PS1ERAY)` action, observes the actual non-party accepted-cast
callback, requires the INT-18 executable resource `PS1ERAY4`, checks one PP is
spent exactly once, then saves and reloads the area and verifies the committed
pool and Psion identity survive. The fixture is deliberately not placed into a
campaign.

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
