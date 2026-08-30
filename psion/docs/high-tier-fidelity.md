# Psion level 6-9 fidelity matrix

The Infinity Engine can express direct combat effects well, but several high-level 3.5e psionic powers require actor cloning, persistent world objects, arbitrary CRE mutation, cross-area queries, or long-running campaign callbacks. This matrix makes those boundaries explicit.

| Level | Power | Current implementation | Feasibility | Remaining divergence |
| --- | --- | --- | --- | --- |
| 6 | Greater Precognition | one-round +4 attack/AC/saves | Partial | no generic one-roll reroll/insight callback |
| 6 | Crystallize | permanent petrification, save vs death | High | crystallization is represented by petrification |
| 6 | Dispelling Buffer | temporary Dispel Magic immunity | Partial | cannot add +5 to each individual dispel check |
| 6 | Restoration (Psionic) | removes level drain | Partial | broad ability-drain restoration is not portable as one generic effect |
| 6 | Banishment | temporary Maze removal | Partial | outsider-only targeting and planar return are not portable |
| 6 | Mind Switch | temporary domination | Low | safe body/CRE/inventory/protagonist exchange is not available |
| 7 | Fate of One | one-round +6 attack/AC/saves | Partial | no generic failed-roll reroll callback |
| 7 | Ectoplasmic Cocoon, Mass | area helplessness | Partial | shell hardness/HP and shell destruction are not separate actors |
| 7 | Reddopsi | spell-level reflection | Partial | transparency makes magic and psionics indistinguishable to the reflection opcode |
| 7 | Fission | self buffs plus temporary controlled psionic echo | Improved | echo is not a literal PC clone and never copies inventory/scripts/dialog |
| 7 | Ethereal Jaunt | speed, AC, anti-backstab, physical resistance | Partial | collision/wall traversal cannot be made safe on arbitrary maps |
| 7 | Crisis of Life | 7d6 on save, death on failed save | Improved | the tabletop 11-HD cutoff is not enforced |
| 8 | Hypercognition | strong local perception/defense | Low | cannot answer campaign questions or query arbitrary off-map facts |
| 8 | Astral Seed | long defensive preparation | Low | no ten-day death/rebirth lifecycle or persistent replacement body |
| 8 | Telekinetic Sphere | held target plus defensive shell | Partial | shell cannot be dragged around the map as an independent object |
| 8 | Fusion | bounded composite stat/combat form | Low | arbitrary ally CRE/stat/ability merge is unsafe |
| 8 | Time Hop, Mass | area Maze-style temporal removal | Partial | willing-only selection and per-round early-return check are absent |
| 8 | Mind Seed | long domination | Low | permanent identity/progression rewrite is intentionally not attempted |
| 9 | Metafaculty | maximal local perception | Low | cannot locate or inspect arbitrary off-map campaign actors |
| 9 | True Creation | long-lived astral construct | Low | no generic item design/placement UI for permanent mundane matter |
| 9 | Tornado Blast | explicit 17d6/8d6 split plus failed-save knockback | High | random final displacement/direct-hit nuances remain simplified |
| 9 | Greater Metamorphosis | apex mutable combat form | Partial | arbitrary creature/object forms and round-by-round form selection are absent |
| 9 | Teleportation Circle | visible-point relocation in current area | Low | no persistent portal/distant destination placement system |
| 9 | Psychic Chirurgery | level-drain repair, save bonus, mental protections | Partial | teaching a permanent known power to another actor requires progression-state editing |

## Implemented fidelity upgrades

### Fission

The base approximation remains for predictable combat scaling, but the power now also summons a real temporary psionic echo. The echo is deliberately based on the mod's astral construct body instead of copying the selected PC. This provides an actual second acting creature while preventing duplicated inventory, scripts, dialog state, protagonist identity, or plot-local variables.

### Crisis of Life

The failed-save child package now uses the engine Death effect rather than additional damage plus helplessness. The successful branch remains 7d6. The one unresolved rule is the tabletop 11-HD death cutoff; the installed description states that explicitly so the stronger high-HD behavior is never hidden.

## Extension rule

Future upgrades should prefer reusable runtime or resource primitives over one-off campaign scripting. Any implementation that would duplicate a player CRE, mutate permanent plot identity, or depend on a single campaign's area/dialog layout should remain an explicit approximation unless GemRB gains a general safe callback for it.
