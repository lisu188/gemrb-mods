# Development engine prerequisite and cast accounting

This development revision of Psion/Cipher requires the companion GemRB
`SetSpellCastCheck` API. A version string such as `0.9.5-git` is not enough to
establish that capability. The companion engine changes are being delivered
to the user-maintained fork in [GemRB PR #3](https://github.com/lisu188/gemrb/pull/3).
The separate [upstream proposal](https://github.com/gemrb/gemrb/pull/2525)
does not establish that an upstream release contains this API; do not interpret
this branch as qualification of an unmodified released GemRB build.

Without the API, class-power selection fails closed with an explicit
`SetSpellCastCheck` requirement in the engine log. Ordinary native spells and
standalone Sorcerer/Monk do not require this class-power callback.

## Event boundary

The shared hook reserves a class action on the actual spell-button selection.
It commits only when the engine calls the check for that actor and the exact
prepared spell resource. Merely opening the selector, configuring a quickslot,
or canceling the targeting cursor does not commit. A later selection replaces
the old reservation; it is never treated as an imaginary second callback.

The reservation binds the canonical selected power, its exact internal cast
resource, and the selected actor's global ID as well as its party slot. The
commit rechecks legality and is idempotent for multiple accepted targets.
Wrong resources/actors, failed commits and callback exceptions are rejected.

The engine check currently marks acceptance of a GUI command: it runs before
the spell action is queued, or immediately before an untargeted instant spell
is applied. It is **not** evidence that a later projectile/effect succeeded.
For targeted casts, later movement/range/line-of-sight checks, aura delay,
interruption, or stopping an already queued action can prevent execution after
resource commitment. No automatic refund for that later cancellation is
implemented. Live acceptance must report that boundary explicitly rather than
claiming that every form of canceled casting is free.

## Internal resource substitution

Psion save-DC/augmentation variants and Cipher Reaping Knives owner variants
are installed resources, not separately learned powers. Preparation records
their `CastResRef` without modifying memorized charges. Only these substitutions
use `GemRB.SpellCast(actor, -3, 0, resref)`; native/ordinary calls and the `-1`
spell-list reset retain their original arguments. The accepted-cast check still
commits against the canonical choice and its PP/Focus cost.

`GemRB.PrepareSpontaneousCast()` is deliberately not used for these private
variants: its native implementation depletes the original spell and searches
the known-spell list, where the internal variant is absent. A fake API that
always returns a successful index does not validate that native contract.

## Evidence boundary

The focused regression is `common/tests/validate_cast_confirmation.py`.
It tests dispatcher/event behavior with controlled engine boundaries. Native
engine callback tests and actual learning, target cancellation, spending,
quickslot, substitution and persistence runs are separate requirements. Until
those runs are complete, the gameplay acceptance gates remain pending even
though the infrastructure issues #50 and #51 are closed. The required campaign
matrix is documented in [real-engine acceptance](../common/acceptance/README.md).

Existing saves are not rewritten by the corrected CLAB orientation. Missing
old Psion startup utilities and incorrectly persisted old Cipher Soul Whip
effects require a separate migration policy; fresh-character acceptance does
not establish that upgrade behavior.
