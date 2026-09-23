# High-tier Psion fidelity matrix

This matrix tracks every level 6–9 approximation called out in the authoritative `psion/README.md` high-level approximation list. Scores are descriptive planning data, not runtime behavior.

| Power | ResRef | Current approximation | Missing tabletop behavior | Gameplay impact | Engine feasibility | Risk | Resource growth | Recommended action |
|---|---|---|---|---:|---|---|---|---|
| Fission | PS7FISS | Temporary combat bonuses model a duplicate | Independent duplicate body with shared/limited resources | 4 | Persistent state / upstream-safe clone API | High | Low if runtime; high if CRE variants | Retain bounded form until clone identity/inventory semantics are safe |
| Crisis of Life | PS7CLIF | 7d6 on save; 10d6 + brief helplessness on failure | Failed-save instant death for eligible low-HD targets | 4 | Native SPL if protected-actor and HD gating are proven | Medium | +1–2 child SPLs | Spike HD/story-protection gating; preserve one PR/save gate |
| Fusion | PS8FUSN | Bounded composite self-buff | Merge with willing target and combine statistics/abilities | 4 | Runtime/state with bounded stat package | High | Low–medium | Improve only explicitly safe transferable stats; never merge CRE identity |
| Time Hop, Mass | PS8MTHP | Area Maze for fixed duration | Willing-only targets and per-round Wisdom early return | 3 | Upstream/runtime callback needed while removed | High | Low | Retain until actor-in-removal periodic callback is proven |
| Greater Metamorphosis | PS9GMET | One apex mutable combat form | Broad form choice and repeatable form changes | 4 | Native SPL with bounded form packages + selector | Medium | Medium, capped per form | Add a small bounded form selector only if variant count stays capped |
| Teleportation Circle (Psionic) | PS9TCIR | Current-area point teleport | Persistent portal and distant destination selection | 5 | Upstream/world-object + destination UI | Very high | Low resources, high runtime state | Split portal infrastructure into a prerequisite if pursued |
| Psychic Chirurgery | PS9PCHI | Restoration + temporary mental protection | Permanently impart one known power | 5 | Runtime selector/target transfer | Medium–high | Low | Reuse canonical power-learning registry after recipient/target callback is proven |

## Prioritization

Psychic Chirurgery is the preferred runtime slice because it can reuse the existing known-power registry and learning legality. Crisis of Life is the preferred resource-only spike if one-save/one-PR semantics, HD eligibility, and story-actor safety can all be represented without a second defense gate.

Mass Time Hop and Teleportation Circle remain upstream/runtime-interface problems. Fission, Fusion, and Greater Metamorphosis remain deliberately bounded until actor identity, inventory, and transformation semantics can be represented without copying arbitrary CRE state.

## Resource-growth budget

New high-tier augmentation or fidelity work must state generated resource growth in its PR. A single power should normally stay below 16 newly generated SPL resources; designs that multiply exact-INT DC variants by an unbounded selector space must be rejected or redesigned.
