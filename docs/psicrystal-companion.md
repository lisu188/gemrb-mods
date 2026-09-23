# Psicrystal companion lifecycle

## Implemented contract

Personality selection and the existing owner skill bonus are unchanged. A chosen
personality grants PXCRSUM (Manifest Psicrystal) and PXCRDIS (Dismiss Psicrystal).
These are TARGET_NONE instant innates accepted through SetSpellCastCheck, not
queued creature-target casts. Creation occurs synchronously inside the accepted
transaction. Cancellation does not create a creature or spend PP. Repeated
confirmation for the same transaction does not create another body.

The runtime uses GemRB.ManageCompanion as the ownership authority. Querying,
creation, synchronization and dismissal are performed against the owning Psion;
no party-global token table, user stat, familiar slot or Python-only actor ID is
used as persistent ownership state. Actor IDs are treated as load-local and may
change after save/reload.

A living existing companion is reused rather than duplicated. Dismissal removes
the current companion. A dead companion consumes the manifestation use until
rest; restore_party resets that per-owner rest-use state but does not silently
create a new body. Area transitions preserve the engine-owned companion relation,
and requesting manifestation while the living companion already exists is
idempotent.

Stats are sampled from Psion level when a fresh companion is created and resynced
through the public companion contract: HP is half the owner's base maximum,
rounded down and clamped to 1–32767; saves copy the owner's base values. AC and
Intelligence scale from pscrlvl.2da. The body has zero base attacks and remains
separate from the normal familiar subsystem.

## Persistent ownership and cleanup

The selected personality and rest-use flag are actor-local persistent Psion
effects. The companion itself is engine-owned state managed by ManageCompanion.
The runtime asks the engine for the companion associated with a particular Psion
instead of reconstructing ownership from CRE names, script globals, party slots,
or private statistics.

Save/load validation therefore checks behavioral invariants: both owners recover
distinct living companions, damaged HP survives, no duplicate is created, and
dismiss/resummon/death operations continue to address the correct owner. It does
not require a pre-save global actor ID or an implementation-specific engine stat
to retain a particular numeric value.

If creation or scaling fails, the operation fails rather than recording a
successful manifestation without a usable companion. Owner death and companion
death are handled by the engine companion relation; subsequent synchronization
must not return a live companion for a dead owner.

## Installer boundaries

The installer owns the PSCRBODY creature, PXCRSUM/PXCRDIS actions, animation,
tables and supporting resources. Validation uses the same generated resources
that WeiDU installs and checks an install -> uninstall -> reinstall -> uninstall
cycle for exact restoration of the original override bytes.

The validation intentionally consumes the public ManageCompanion API rather than
depending on removed token-era private helpers. This keeps the mod-side contract
aligned with the engine API that is actually serialized and supported.

## Validation and limits

Run the Python lifecycle suite and real WeiDU lifecycle test:

```sh
python psion/tests/validate_psicrystal_companion.py
python psion/tests/validate_psicrystal_install.py /path/to/weidu /path/to/gemrb-source
```

The native runner uses the actual pinned engine, actual installed class tables,
actual Spellbook/GemRBModCore and native accepted casting, companion management,
map transitions and save/load APIs. The public demo fixture supplies two Psion
actors, installed TLK data and the minimal demo resources needed by the scenario.

```sh
python psion/tests/validate_psicrystal_native.py --engine-source /path/to/gemrb-source --runtime /path/to/installed-gemrb --installed /path/to/weidu-fixture --output /path/to/new-output-directory
```

CI builds lisu188/gemrb commit 5e5f45da0d801674174a118aad9d5c49ec224542.
It checks accepted creation and cancellation, two independent owners, party
reorder, saved injury and zero APR, load without duplication, post-load dismissal,
area transitions without duplication, creature death/rest-gated resummon and
owner-death cleanup.

This does not claim every tabletop psicrystal ability or full campaign-wide
acceptance. Telepathy, shared powers, remote vision and other mechanics requiring
additional engine contracts remain outside this subsystem. No proprietary game
assets are committed or required by these tests.
