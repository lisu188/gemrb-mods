# Changelog

## 0.3.0

- Completed Reaping Knives Focus transfer using temporary melee/ranged weapon-effect hooks that retain the originating Cipher.
- Defined Reaping Knives critical behavior as one 5-Focus transfer per qualifying hit, with no additional critical-only Reaping Knives credit.
- Added persistent optional Cipher subclass identity and the first subclass, Soul Blade.
- Added Soul Blade passive tradeoffs and the Focus-paid Soul Annihilation action while keeping base Cipher Focus authority in the existing runtime.
- Added subclass hook points for Focus gain, Focus cap, power cost, weapon behavior, and passives.
- Added the unified repository-level install/uninstall/package driver and owned `CipherSubclass.py` runtime dependency.
- Added release-manifest validation and real-GemRB acceptance runner integration.
- Updated documentation to distinguish automated validation from outstanding live campaign acceptance.

## 0.2.0

- Added player-selected Cipher power learning through level-based `CIPHERKNOWN` limits and harmless `CIL*` selector proxies.
- Completed high-tier Detonate and Soul Collapse mechanics.
- Hardened Focus persistence, hostile-only weapon-hit Focus generation, critical-hit Focus, class-table validation, item restrictions, and shared GUI ownership.

## 0.1.0

- Initial installable Cipher implementation with Soul Whip, Focus generation/spending, the 18-power catalogue, class registration, and GemRB GUI integration.
