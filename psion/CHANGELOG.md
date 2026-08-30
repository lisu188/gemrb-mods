# Changelog

## 1.4.0

- Added player-selected power learning through `PSIONKNOWN.2DA` limits and harmless `PXL*` selector proxies.
- Added exact current-Intelligence save-DC substitution. Installation generates internal save-bearing variants and the runtime selects the correct resource immediately before manifestation.
- Added persistent psionic focus, bonus-feat, and skill state through private save-serialized actor effects.
- Added the persistent psicrystal subsystem with four personality choices, Psion-level-scaled passive resonance, one rest-restored summon action, and no dependency on familiar infrastructure.
- Added the reusable non-player `PsionAI.py` controller. Enemy Psions reuse canonical discipline, PP, affordability, and exact-INT DC functions rather than a parallel rules implementation.
- Added optional WeiDU component 200 with six discipline-specific Psion equipment resources using opcode-319 allow-only class restrictions.
- Added a tracked level-6–9 fidelity matrix.
- Improved Fission with a real temporary psionic echo that does not clone player identity/inventory/scripts.
- Improved Crisis of Life with a lethal failed-save branch; the remaining documented divergence is the unavailable tabletop 11-HD cutoff.
- Added a unified repository-level install/uninstall/package driver with shared-runtime dependency ownership, SHA-256 release manifests, pre-mutation bundle validation, and best-effort rollback.
- Added a real-GemRB acceptance runner and documented BGEE/BG2EE-family scenario matrix. Live campaign results remain a separate gate requiring local game assets.
- Updated release documentation and compatibility metadata to distinguish automated validation from live-engine acceptance.

## 1.3.0

- Expanded the Psion catalogue to 85 powers through power level 9 and class level 20.
- Added complete 1–20 powers-known limits and made all catalogue powers reachable through the selectable-power registry.
- Added high-tier D&D 3.5e discipline powers and explicit portable approximations where Infinity Engine mechanics cannot safely represent the tabletop behavior.
- Extended Energy Ray, Mind Thrust, Vigor, and Swarm of Crystals augmentation through the manifester-level ceiling of 20 PP.
- Added Charisma to Animal Affinity and corrected augmentation refresh/cancellation behavior.
- Added generated-table validation and expanded source/resource consistency checks through power level 9.
- Corrected multiple SRD mappings, names, saving throws, hostile flags, and power descriptions.

## 1.0.0

- First installable Psion release.
- Added six dynamically registered Psion discipline classes with class IDs derived from the active GemRB class tables.
- Added D&D 3.5e PP progression, Intelligence 15 minimum, Mage-derived XP/cap data, Psion saving throws, proficiencies, Lore, item usability, startup gold, and ToB safety metadata.
- Added purpose-built power resources, augmentation selectors, two-phase PP transactions, reusable innate manifestations, and shared GemRB GUI hooks.
- Added generated non-proprietary BG-family fixtures and real-WeiDU install/uninstall/reinstall validation across supported class-table layouts.
- Added byte-for-byte restoration checks for patched tables/resources and ownership-safe runtime-module installation.

## 0.x development

The pre-1.0 alpha series incrementally introduced discipline registration, PP state, levels 1–5 power resources, augmentation, GUI selectors, item restrictions, and fixture validation. Those versions are superseded by the release behavior documented above.
