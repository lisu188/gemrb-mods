# Psion level 6-9 fidelity matrix

The Infinity Engine can express direct combat effects well, but several high-level 3.5e psionic powers require actor cloning, persistent world objects, arbitrary CRE mutation, cross-area queries, or long-running campaign callbacks. This matrix makes those boundaries explicit and ranks future work using three separate dimensions:

- **Gameplay value:** expected player-visible improvement from closing the remaining gap.
- **Engine feasibility:** how safely the behavior can be expressed through portable GemRB/Infinity Engine primitives.
- **Runtime complexity:** amount of persistent state, UI, callbacks, or cross-actor coordination required.

`Priority` is the current implementation order after considering all three dimensions; it is not a promise that low-feasibility work will be forced into unsafe engine hacks.

| Level | Power | Current implementation | Gameplay value | Engine feasibility | Runtime complexity | Priority | Remaining divergence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Greater Precognition | one-round +4 attack/AC/saves | Medium | Partial | High | P3 | no generic one-roll reroll/insight callback |
| 6 | Crystallize | permanent petrification, save vs death | Low | High | Low | P4 | crystallization is represented by petrification |
| 6 | Dispelling Buffer | temporary Dispel Magic immunity | Medium | Partial | Medium | P3 | cannot add +5 to each individual dispel check |
| 6 | Restoration (Psionic) | removes level drain | Medium | Partial | Medium | P3 | broad ability-drain restoration is not portable as one generic effect |
| 6 | Banishment | temporary Maze removal | Medium | Partial | Medium | P3 | outsider-only targeting and planar return are not portable |
| 6 | Mind Switch | temporary domination | High | Low | Very high | P4 | safe body/CRE/inventory/protagonist exchange is not available |
| 7 | Fate of One | one-round +6 attack/AC/saves | Medium | Partial | High | P3 | no generic failed-roll reroll callback |
| 7 | Ectoplasmic Cocoon, Mass | area helplessness | Medium | Partial | High | P3 | shell hardness/HP and shell destruction are not separate actors |
| 7 | Reddopsi | spell-level reflection | Low | Partial | Low | P4 | transparency makes magic and psionics indistinguishable to the reflection opcode |
| 7 | Fission | self buffs plus temporary controlled psionic echo | High | High | Medium | Done | echo is not a literal PC clone and never copies inventory/scripts/dialog |
| 7 | Ethereal Jaunt | speed, AC, anti-backstab, physical resistance | Medium | Partial | High | P3 | collision/wall traversal cannot be made safe on arbitrary maps |
| 7 | Crisis of Life | 7d6 on save, death on failed save | High | High | Low | Done | the tabletop 11-HD cutoff is not enforced |
| 8 | Hypercognition | strong local perception/defense | Low | Low | Very high | P4 | cannot answer campaign questions or query arbitrary off-map facts |
| 8 | Astral Seed | long defensive preparation | High | Low | Very high | P4 | no ten-day death/rebirth lifecycle or persistent replacement body |
| 8 | Telekinetic Sphere | held target plus defensive shell | Medium | Partial | High | P3 | shell cannot be dragged around the map as an independent object |
| 8 | Fusion | bounded composite stat/combat form | High | Low | Very high | P4 | arbitrary ally CRE/stat/ability merge is unsafe |
| 8 | Time Hop, Mass | area Maze-style temporal removal | High | Partial | High | P1 | willing-only selection and per-round early-return check are absent |
| 8 | Mind Seed | long domination | Medium | Low | Very high | P4 | permanent identity/progression rewrite is intentionally not attempted |
| 9 | Metafaculty | maximal local perception | Low | Low | Very high | P4 | cannot locate or inspect arbitrary off-map campaign actors |
| 9 | True Creation | long-lived astral construct | Low | Low | Very high | P4 | no generic item design/placement UI for permanent mundane matter |
| 9 | Tornado Blast | explicit 17d6/8d6 split plus failed-save knockback | Medium | High | Low | P3 | random final displacement/direct-hit nuances remain simplified |
| 9 | Greater Metamorphosis | apex mutable combat form | High | Partial | High | P2 | arbitrary creature/object forms and round-by-round form selection are absent |
| 9 | Teleportation Circle | visible-point relocation in current area | High | Low | Very high | P2 | no persistent portal/distant destination placement system |
| 9 | Psychic Chirurgery | level-drain repair, save bonus, mental protections | High | Partial | Medium | P1 | teaching a permanent known power to another actor requires progression-state editing |

## Implemented fidelity upgrades

### Fission

The base approximation remains for predictable combat scaling, but the power now also summons a real temporary psionic echo. The echo is deliberately based on the mod's astral construct body instead of copying the selected PC. This provides an actual second acting creature while preventing duplicated inventory, scripts, dialog state, protagonist identity, or plot-local variables.

### Crisis of Life

The failed-save child package now uses the engine Death effect rather than additional damage plus helplessness. The successful branch remains 7d6. The one unresolved rule is the tabletop 11-HD death cutoff; the installed description states that explicitly so the stronger high-HD behavior is never hidden.

## Resource-growth budget

The two implemented upgrades are deliberately bounded:

- Fission adds one derived CRE resource (`PSFISS01`) and one extra summon effect to the existing power.
- Crisis of Life rewrites the existing failed-save child effect package and adds no family of per-level or per-stat resources.

Future high-tier augmentation work should remain table/generated and must declare its resource multiplier before implementation. A proposal that requires an unbounded Cartesian product of Intelligence, augmentation, target state, or campaign destination is rejected in favor of runtime substitution or an explicit approximation.

## Next ranked slices

1. **Mass Time Hop early return** — high gameplay value, partial feasibility, but requires a reusable periodic state check rather than one-off scripting.
2. **Psychic Chirurgery power teaching** — high value and moderate complexity if it can reuse the existing known-power registry and transaction primitives without bypassing powers-known accounting.
3. **Greater Metamorphosis bounded forms** — useful but should remain a curated form set rather than arbitrary CRE replacement.
4. **Teleportation Circle** — high value but deliberately deferred until GemRB exposes a safe persistent-destination/portal UI primitive.

## Extension rule

Future upgrades should prefer reusable runtime or resource primitives over one-off campaign scripting. Any implementation that would duplicate a player CRE, mutate permanent plot identity, or depend on a single campaign's area/dialog layout should remain an explicit approximation unless GemRB gains a general safe callback for it.
