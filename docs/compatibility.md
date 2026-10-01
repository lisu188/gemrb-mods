# Custom class compatibility and release status

This matrix is the repository-level source of truth for the currently maintained custom classes. Class READMEs contain class-specific rules and installation details; installer `VERSION` values remain authoritative for release numbers.

Development-branch prerequisite: Psion/Cipher class powers require the companion
GemRB `SetSpellCastCheck` API, and Psicrystals require `ManageCompanion`, not
merely a matching version string. The current companion engine repairs are in
[engine PR #7](https://github.com/lisu188/gemrb/pull/7). See
[cast accounting and its current limitations](cast-runtime.md). The released
engine and full gameplay qualification must not be inferred from installer or
startup checks.

| Mod | Version | Supported game families under GemRB | Runtime / GUI requirement | Automated validation | Real-engine acceptance |
| --- | --- | --- | --- | --- | --- |
| Cipher | 0.2.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE, EET | matching sibling `common/`; shared `GemRBModCore` GUI hooks | static, fake-GemRB, installed Focus effects, WeiDU lifecycle and pinned GemRB fixture contracts | current campaign coverage in completion PR #93 |
| Psion | 1.4.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE, EET | matching sibling `common/`; shared `GemRBModCore` GUI hooks | static, fake-GemRB, generated resources, native Psicrystal lifecycle and WeiDU lifecycle | current campaign coverage in completion PR #93 |
| Sorcerer/Monk | 2.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BG2/ToB, BGT, BG2EE, EET | matching sibling `common/`; shared custom-class chargen layer | source-contract, table-shape, component progression, HLA selection and real-WeiDU lifecycle | current campaign coverage in completion PR #93 |

## What the validation states mean

**Automated validation** proves repository-controlled invariants such as table shapes, generated resources, runtime helper behavior under fake GemRB APIs, WeiDU parser compatibility, install/uninstall restoration and source contracts against a pinned GemRB tree.

**Real-engine acceptance** means the installed mod has been exercised in an actual GemRB process against a legal game fixture, including the relevant gameplay state transitions. Automated validation is intentionally not described as equivalent to this evidence.

The game-family column describes installer support. The current qualification
scope is fresh characters in BGEE and BG2EE/ToB, including Soul Blade, all five
Psion equipment items, and owned Psicrystals. It does not qualify EET, enemy
Psions, older-character migration, or additional tabletop behavior.

[Completion PR #93](https://github.com/lisu188/gemrb-mods/pull/93) records the
current exact delivery revisions, CI results and campaign coverage. Closed
infrastructure issues #50/#51 and partial runs do not establish qualification.
The [required matrix](../common/acceptance/matrices/three-class-acceptance.json)
requires 11 complete campaign runs and both lifecycle matrices, including
Sorcerer/Monk first/last-owner and standalone checks. Qualification remains open
for any missing, failed or stale entry.

Focused validation has exercised installed Cipher hit probabilities, class
gating, Soul Blade's capped 10/20 Focus gains and 165-to-170 transition, plus
native Psicrystal personality selection and companion save/reload. These
regressions supplement the complete campaign matrix; they do not replace it.

Supported limitations remain explicit: accepted targeted commands can spend
PP/Focus before later interruption or range failure, with no automatic refund;
Psion skills and other documented tabletop approximations retain their
existing consumers; BGEE progression respects the installed XP cap. High-tier
powers and combined HLA selection are checked in BG2EE/ToB. See
[cast accounting](cast-runtime.md) and the class READMEs for the rules.

## Shared-runtime rule

Cipher and Psion must use matching `common/` code from the same release/repository revision. They may be installed in either order. Removing one handler must leave the shared GUI layer active for the other, and removing the last handler must restore the original GemRB GUI scripts.

Sorcerer/Monk uses the shared custom-class chargen support but does not use the Cipher/Psion PP/Focus runtime handler dispatch.
