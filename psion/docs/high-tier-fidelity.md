# High-tier Psion fidelity matrix

Every level 6–9 power is represented here because `psion/README.md` documents a portable approximation for each high-tier family. Scores are planning data; installed behavior remains defined by the SPL/runtime sources.

| Power | ResRef | Current approximation | Missing tabletop behavior | Impact | Feasibility | Risk | Growth | Recommended action |
|---|---|---|---|---:|---|---|---|---|
| Greater Precognition | PS6GPRE | Strong short insight window | One-roll reroll callback | 3 | Runtime callback | Medium | 0 | Retain until generic reroll callback exists |
| Crystallize | PS6CRYS | Petrification state + death-save analogue | Exact Fortitude/material semantics | 3 | Native SPL | Low | 0–1 | Keep; only refine if engine exposes closer state |
| Dispelling Buffer | PS6DBUF | Blocks ordinary Dispel Magic | +5 to individual dispel checks | 3 | Upstream dispel hook | Medium | 0 | Retain until per-dispel modifier exists |
| Restoration (Psionic) | PS6REST | Removes level drain | Generic ability-score drain repair | 3 | Native SPL, bounded stats | Low | 0 | Add only explicitly safe drain repairs |
| Banishment (Psionic) | PS6BANI | Temporary Maze removal | Extraplanar-only targeting | 3 | SPLPROT/native SPL | Medium | 0–1 | Spike reliable extraplanar discriminator |
| Mind Switch | PS6MSWI | Temporary domination | Body/inventory/plot identity swap | 5 | Upstream actor-identity API | Very high | Low | Retain approximation |
| Fate of One | PS7FATE | Strong short insight window | One-roll reroll callback | 3 | Runtime callback | Medium | 0 | Share future reroll primitive with PS6GPRE |
| Ectoplasmic Cocoon, Mass | PS7MCOC | Area hold | Destructible shells with HP/hardness | 3 | Summoned world objects | High | High | Retain area hold |
| Reddopsi | PS7RDOP | Broad spell/power reflection | Psionics-only reflection | 3 | Engine effect typing | Medium | 0 | Retain under transparency |
| Fission | PS7FISS | Temporary combat bonuses | Independent duplicate body | 4 | Persistent state / clone API | High | Low or very high | Retain bounded form |
| Ethereal Jaunt (Psionic) | PS7EJNT | Mobility + defensive effects | Arbitrary wall traversal/ethereal plane | 4 | Navigation/engine mode | High | 0 | Retain approximation |
| Crisis of Life | PS7CLIF | 7d6 save; 10d6 + helpless on fail | Eligible low-HD instant death | 4 | Native SPL if safe HD/story gate exists | Medium | +1–2 SPL | Spike protected-actor + HD gating |
| Hypercognition | PS8HYPC | Strong local perception | Narrative deduction/campaign knowledge | 2 | Campaign scripting | High | 0 | Retain local perception |
| Astral Seed | PS8ASED | Long defensive preparation | Death-to-seed transfer/body regrowth | 5 | Upstream resurrection lifecycle | Very high | Low | Retain until resurrection callback exists |
| Telekinetic Sphere (Psionic) | PS8TKSP | Immobilizing protective shell | Movable sphere | 3 | Runtime movement controller | High | Low | Retain immobile form |
| Fusion | PS8FUSN | Bounded composite self-buff | Merge with willing target | 4 | Runtime/state | High | Low–medium | Improve only safe transferable stats |
| Time Hop, Mass | PS8MTHP | Fixed-duration area Maze | Willing-only + per-round early return | 3 | Callback while removed | High | Low | Retain until removal-state callback proven |
| Mind Seed | PS8MSED | Long domination | Permanent identity/progression rewrite | 5 | Actor identity API | Very high | 0 | Retain approximation |
| Metafaculty | PS9META | Strong local perception | Off-map creature facts/location | 2 | Campaign/world query API | High | 0 | Retain local perception |
| True Creation | PS9TCRE | Durable astral construct | Permanent chosen mundane object | 3 | Item construction UI | High | Medium | Retain construct |
| Tornado Blast | PS9TORN | 17d6/8d6 area + fixed knockback | Separate direct-hit packet/random distance | 3 | Native SPL/projectile | Medium | +1–4 SPL | Consider bounded displacement variants |
| Greater Metamorphosis | PS9GMET | One apex mutable form | Broad form choice/repeated changes | 4 | Bounded selector + SPL packages | Medium | Capped medium | Consider small form selector |
| Teleportation Circle (Psionic) | PS9TCIR | Current-area point teleport | Persistent portal + distant destination | 5 | World object + destination UI | Very high | Low resources | Split portal infrastructure prerequisite |
| Psychic Chirurgery | PS9PCHI | Restoration + mental protection | Permanently impart known power | 5 | Targeted runtime selector | Medium–high | Low | Preferred runtime fidelity slice |

## Prioritization

Psychic Chirurgery is the preferred runtime slice because it can reuse the existing known-power registry. Crisis of Life is the preferred resource-only spike if one-save/one-PR semantics, HD eligibility, and story-actor safety can all be represented without a second defense gate.

Mass Time Hop, Astral Seed, Mind Switch, Mind Seed, and Teleportation Circle require engine/runtime interfaces that should not be faked with Python-only state. Fission, Fusion, and Greater Metamorphosis remain bounded until actor identity and transformation semantics can be represented safely.

## Resource-growth budget

Each behavior slice must report generated-resource growth. A single power should normally stay below 16 newly generated SPL resources. Designs that multiply exact-INT DC variants by an unbounded selector space must be redesigned.
