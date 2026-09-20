# Actor-state read failures

## Failure boundary

Missing saved state and unreadable saved state are different conditions.
A successful effect scan with no matching marker may initialize an old or new
character according to the existing migration rules. A failed scan must not
initialize that character again.

`PersistentState.read` now raises `RuntimeError`, preserving the original
exception as its cause, when the engine cannot enumerate effects or a matching
value cannot be decoded. It no longer converts those failures to `(False, 0)`.
Psion feat and focus readers follow the same failure rule. Successfully read
zero PP, zero skill credits and unfocused state remain valid saved values.

The Psion and Cipher known-power readers also reject failed or interrupted
spellbook enumeration instead of returning a partial set. A partial scan must
not make a character appear to have unused power-learning credits.

This closes paths that could refill Psion PP, grant psionic focus, reset feat
ranks or skill credits, authorize a second psicrystal personality, or grant an
extra power-learning choice after an engine read error.

## Casting and recovery

An exception during `GemRBModCore.confirm_spell` clears the actor's pending
reservation and propagates to the engine's `SetSpellCastCheck` boundary. The
required engine rejects the accepted-cast command on an exception; it does not
queue the spell. Native Sorcerer/Monk spells do not consult Psion saved state.

The failed read does not itself erase or replace the saved effect. After a
transient read problem is resolved, the next successful access recovers the
stored value rather than granting a refill. There is no automatic repair of a
corrupt save and no guessing of lost values.

## Regression coverage

Run `python common/tests/validate_actor_state_failures.py` from the repository
root. Thirteen tests use the actual runtime modules and repository rule tables
with fault-injected GemRB API boundaries. They cover absent versus zero state,
engine read exceptions, malformed matching values, PP/cache protection, focus,
feats, skills, psicrystal choices, accepted-cast cancellation, complete versus
partial known-power scans, and unaffected native Sorcerer/Monk casting.

The suite reproduced 14 assertion/subtest failures against the preceding
runtime and passes after the correction. It runs in class-registration CI.

These are read-failure and Python/engine-boundary regressions, not real
BGEE/BG2EE/ToB campaign save/reload qualification. They do not make multi-effect
writes atomic, implement summoned psicrystal lifecycle, or migrate old CLAB
grants. Those remain separate work.
