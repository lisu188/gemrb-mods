# Custom class compatibility and release status

This matrix is the repository-level source of truth for the currently maintained custom classes. Class READMEs contain class-specific rules and installation details; installer `VERSION` values remain authoritative for release numbers.

| Mod | Version | Supported game families under GemRB | Runtime / GUI requirement | Automated validation | Real-engine acceptance |
| --- | --- | --- | --- | --- | --- |
| Cipher | 0.2.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE, EET | matching sibling `common/`; shared `GemRBModCore` GUI hooks | static, fake-GemRB, WeiDU parse/install/uninstall/reinstall and pinned GemRB fixture contracts | pending cross-mod acceptance suite in #50 |
| Psion | 1.3.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BGT, BG2EE, EET | matching sibling `common/`; shared `GemRBModCore` GUI hooks | static, fake-GemRB, generated-resource, WeiDU lifecycle and pinned GemRB fixture contracts | pending cross-mod acceptance suite in #50 |
| Sorcerer/Monk | 2.0 | Tutu, Tutu_TotSC, BGEE, Classic Adventures, BG2/ToB, BGT, BG2EE, EET | matching sibling `common/`; shared custom-class chargen layer | source-contract, table-shape and real-WeiDU lifecycle validation | live campaign qualification pending in #51 |

## What the validation states mean

**Automated validation** proves repository-controlled invariants such as table shapes, generated resources, runtime helper behavior under fake GemRB APIs, WeiDU parser compatibility, install/uninstall restoration and source contracts against a pinned GemRB tree.

**Real-engine acceptance** means the installed mod has been exercised in an actual GemRB process against a legal game fixture, including the relevant gameplay state transitions. Automated validation is intentionally not described as equivalent to this evidence.

Until #50 and #51 complete their live scenarios, release documentation must use the explicit pending language above rather than claiming complete live-engine qualification.

## Shared-runtime rule

Cipher and Psion must use matching `common/` code from the same release/repository revision. They may be installed in either order. Removing one handler must leave the shared GUI layer active for the other, and removing the last handler must restore the original GemRB GUI scripts.

Sorcerer/Monk uses the shared custom-class chargen support but does not use the Cipher/Psion PP/Focus runtime handler dispatch.
