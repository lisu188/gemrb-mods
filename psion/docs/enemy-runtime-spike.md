# Enemy Psion runtime spike

## Result

Enemy Psion manifestations cannot safely share the player runtime on the currently
pinned engine without an additional non-party accepted-cast hook.

The existing `GemRB.SetSpellCastCheck` contract is intentionally GUI-only.
`GameControl::TryToCast` invokes it after GUI target validation and before
queueing a player spell. Scripted and AI casts instead enter
`GameScript::SpellCore` or `GameScript::SpellPointCore`, so they never pass
through that callback.

The engine execution point suitable for enemy Psions is the first invocation of
`Scriptable::CastSpell` / `CastSpellPoint`, after target, range, line-of-sight
and aura checks have succeeded and before the cast begins. The action's
`int2Parameter` first-pass state makes that point naturally once-per-cast.

## Canonical mod-side contract

`Psionics.manifestation_plan(actor, resref)` is now the non-mutating authority
for a manifestation. It returns:

- canonical save-bearing power resref;
- exact-INT executable resref when the installed DC resource exists;
- PP cost and current actor-local PP snapshot;
- legality and a bounded rejection reason;
- discipline, power level and parent metadata.

The planning path does not initialize, clamp, cache or spend PP. Missing
persistent state is interpreted exactly as the existing runtime would initialize
it: a full level/INT-derived pool.

`Psionics.commit_manifestation(actor, resref)` recomputes the plan and performs
the single PP mutation only when the plan is still legal. GUI
`begin_manifest()` uses the same plan/commit pair through the existing
transaction layer, so player behavior and future enemy behavior cannot drift
into separate PP ledgers.

Exact-INT preparation also consumes the plan's executable resref. Internal DC
variants remain implementation resources and are not learned powers.

## Required engine hook

The follow-up engine change must:

1. run only for non-party/scripted actors so player GUI casts are not
   double-accounted;
2. run once after script target/range/LOS/aura acceptance and immediately before
   the initial `CastSpell` or `CastSpellPoint` call;
3. receive the actor global ID and resolved spell resref;
4. allow the callback to veto the cast or replace the executable resref;
5. fail closed on callback exceptions;
6. leave ordinary enemy spells unchanged when the callback returns the original
   resref;
7. cover both actor-target and point-target script casts;
8. have native tests proving no callback on rejected/out-of-range/retried casts,
   exactly one callback on an accepted cast, veto semantics, and resref
   substitution.

Once that hook is available, `GemRBModCore` can route non-party `PS*`
resources to `manifestation_plan()`, commit PP exactly once, and return the
plan's exact-INT resref. Only then should encounter BCS/CRE resources be added.

## Source evidence

- Engine commit `330f3d827382b9b7505975da8cac2a8236864d9f` introduced
  `SetSpellCastCheck` and documents that AI casts are excluded.
- Current `gemrb/core/GUI/GameControl.cpp` owns that callback and calls it only
  from GUI cast dispatch.
- Current `gemrb/core/GameScript/GSUtils.cpp` implements
  `SpellCore`/`SpellPointCore` and reaches `CastSpell`/`CastSpellPoint`
  without a mod callback.
