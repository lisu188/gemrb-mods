# Psicrystal companion lifecycle

## Implemented contract

Personality selection and the existing owner skill bonus are unchanged. A chosen
personality grants PXCRSUM (Manifest Psicrystal) and PXCRDIS (Dismiss Psicrystal).
These are TARGET_NONE instant innates accepted through SetSpellCastCheck, not
queued creature-target casts. Creation occurs synchronously inside the accepted
transaction. Cancellation does not allocate an owner, create a creature or spend
PP. Repeated confirmation for the same transaction does not create another body.

Only living party Psions in the current area can manifest, and only outside party
combat. A same-area existing body blocks another manifestation. Dismissal revokes
the current generation even in combat and removes the body on its next script
update. Neither action spends PP. Explicit out-of-combat remanifestation restores
the body's freshly sampled stats; UI refresh and rest do not respawn or heal it.

Stats are sampled from Psion level at manifestation: HP is half the owner's base
maximum, rounded down and clamped to 1–32767; saves copy the owner's base values.
AC is 10 - floor((level - 1) / 2), Intelligence 6 + floor((level - 1) / 2),
Dexterity 15 and movement 9, through level 20. The body has no player class and
zero base attacks; giving it Fighter class would make native RefreshPCStats reset
its APR. MC_NO_NIGHTMARE_MODS prevents automatic HP/XP boosts. It grants no XP,
has no loot, and does not use familiar ownership, summon slots or bonus familiar HP.

## Persistent ownership and cleanup

PSCRNEXT is a monotonic game-global high-water mark. One private actor effect
(PSCRID, marker 0x50534349) records an owner token in 1–255. A matching permanent
ScriptingState effect exposes that token in slot 7/stat 163 for native scripts.
The slot must have zero base value and no foreign effect. Broken state, exhausted
counters and duplicate imported party identities fail closed. Tokens are never
recycled. Cross-save imported characters are not automatically renumbered.

The corresponding game global PSCRnnn records a manifestation generation. Each
body stores the same generation in its native PSCREP local. PSREADY is set last,
after stats and generation are initialized. Incomplete bodies remove themselves.
Post-creation exceptions attempt native UnsummonCreature cleanup and veto the cast.
No transient Python existence flag or engine global actor ID is the save authority.

Generated PSCR001–PSCR255 CRE/BCS pairs scan the available Player selectors for
the owner token, not a fixed party slot. They destroy the body if initialization
is incomplete, its generation is revoked, its owner is absent/dead or no longer
in the same area. Otherwise an idle body follows its owner. On area travel there
is no automatic teleport: explicitly manifest again; stale bodies in inactive
areas are destroyed when their scripts next run. Multiple Psions are independent.
Native save/load preserves local variables, effects, generations and damaged HP.

## Installer and compiler boundaries

The generator creates one original four-frame/five-direction BAM, 255 CRE/BAF
pairs and small metadata tables. It allocates a free private animation row and
free GemRB trigger indices below MAX_TRIGGERS (300), respecting both TRIGGER.IDS
and the effective GEMTRIG.IDS overrides. Installation fails if required capacity
or supported schemas are absent.

WeiDU 251 does not merge four string operands for newly allocated native
GlobalLTGlobal/GlobalGTGlobal IDs: its output loses the second variable. The
postcompile step validates both comparisons in every owned BCS and writes the
fully qualified LOCALSPSCREP/GLOBALPSCRnnn operands. Unknown encodings, missing or
duplicate comparisons abort installation. This edits only generated PSCR scripts;
WeiDU owns the final resources and backups normally. Install/uninstall/reinstall
is tested for exact restoration of all original override bytes.

## Validation and limits

Run the Python lifecycle suite and real WeiDU lifecycle test:

```sh
python psion/tests/validate_psicrystal_companion.py
python psion/tests/validate_psicrystal_install.py /path/to/weidu /path/to/gemrb-source
```

The native runner uses the actual pinned engine, actual installed class tables,
actual Spellbook/GemRBModCore and native accepted casting, CRE/effect/local-variable
serialization, BCS execution and map/save APIs. It observes CreateCreature results
without substituting their implementation. The public demo fixture supplies two
Psion actors, zero-bonus missing rule tables, installed TLK, and a reused demo
stance for the demo's otherwise missing human death animation. It uses the normal
save-dialog API with an explicit screenshot preview, not the engine's currently
unsafe omitted-preview quicksave path. Owner death is tested under the engine's
all-party-dead protagonist mode to avoid the demo's missing death-dialog window.
These are disclosed fixture adaptations, not mocked companion behavior.

```sh
python psion/tests/validate_psicrystal_native.py --engine-source /path/to/gemrb-source --runtime /path/to/installed-gemrb --installed /path/to/weidu-fixture --output /path/to/new-output-directory
```

CI builds lisu188/gemrb commit 5e5f45da0d801674174a118aad9d5c49ec224542 and runs
that scenario. It checks accepted creation, cancellation, two owners, party
reorder, saved injury/zero APR, load without duplication, post-load dismissal,
area remanifestation/stale cleanup, creature death and owner death.

This does not establish full BGEE/BG2EE/ToB campaign acceptance or all tabletop
psicrystal abilities. Telepathy, shared powers, remote vision and distance-gating
the pre-existing personality skill bonus remain outside this implementation.
An inactive-area stale body can exist until the next script tick after activation.
No arbitrary save repair, automatic old-CLAB migration or new epic class abilities
are provided. No proprietary game assets are committed or required by the tests.
