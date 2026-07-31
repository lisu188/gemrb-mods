# Changelog

## 0.2.0-alpha

- Added separate level 1–9 power progressions for all six disciplines.
- Added one exclusive discipline power whenever a new power tier unlocks.
- Matched cumulative powers-known totals at every BG1-accessible level.
- Added runtime checks for discipline ownership, Intelligence and manifester
  level before manifestation.
- Replaced immediate PP deduction with a two-phase reserve/commit transaction.
- Cancelled target selection no longer intentionally consumes PP, and repeated
  GemRB callbacks no longer intentionally double-charge the same power.
- Added GUI-patcher fixture tests and stronger table/progression validation.
- Expanded implementation and limitation documentation.

## 0.1.0-alpha

- Added six Psion discipline classes with dynamic class identifiers.
- Added D&D 3e pool and powers-known progressions.
- Added persistent Intelligence-based point accounting and rest restoration.
- Added 60 level 1–5 prototype power definitions.
- Added documented discipline, skill, feat and augmentation metadata.
- Added cross-platform GemRB GUI hook installer with backups and uninstall.
- Added static validation and documented current alpha limitations.
