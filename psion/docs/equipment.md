# Psion discipline equipment

WeiDU component **200 — Psion discipline equipment** installs a deliberately small six-item set, one item for each Psion discipline. The component is optional and does not modify stores, areas, creatures, or encounter scripts.

## Availability model

All six items are installed as item resources in `override/` and are **unplaced by design**. They are therefore not obtainable in an unmodified campaign merely by installing component 200. Campaign, store, or encounter integration may place `PSIITM01` through `PSIITM06` explicitly without requiring a second item-definition path.

This is intentional: guessing campaign-specific store or creature resrefs would make the component brittle across Tutu, BGEE, BGT, BG2EE, and EET. Resource-only installation is deterministic, idempotent, and safe to combine with a later placement mod.

| Resource | Item | Discipline | Target tier | Psion mechanic | Balance rationale | Availability |
| --- | --- | --- | --- | --- | --- | --- |
| `PSIITM01` | Seer's Lens | Seer | early/mid | Intelligence; therefore bonus PP and current-INT save DC | +1 INT is meaningful to the manifesting stat without granting free manifestations or bypassing PP accounting | installed resource only; unplaced |
| `PSIITM02` | Ectoplasmic Bracers | Shaper | mid | defense | +1 AC is a compact defensive benefit that does not multiply construct output or create summon-state bookkeeping | installed resource only; unplaced |
| `PSIITM03` | Conductive Ring | Kineticist | mid | energy defense | 20% electrical resistance reinforces the energy theme while remaining narrower than a general resistance item | installed resource only; unplaced |
| `PSIITM04` | Mutable Girdle | Egoist | mid | physical self-modification | +1 CON improves durability without modifying the Psion PP cache, focus state, or power registry | installed resource only; unplaced |
| `PSIITM05` | Nomad's Striders | Nomad | mid/high | mobility | +15% movement is useful for repositioning but avoids teleport callbacks, destination state, or action-economy changes | installed resource only; unplaced |
| `PSIITM06` | Whispering Circlet | Telepath | high | Intelligence/save pressure | +1 INT plus +1 save vs spell is deliberately placed at a later tier because it combines offensive manifesting value with a defensive save bonus | installed resource only; unplaced |

## Usability

Each item carries an opcode 319 allow-only restriction for exactly one Psion discipline class ID. The class IDs are recovered from the already-installed main Psion component rather than hardcoded. All six disciplines therefore use the same deterministic mechanism, and the optional component fails if the main component is absent.

## PP and psionic focus safety

The first equipment slice deliberately contains no direct PP restoration, PP-cap mutation, or psionic-focus grant. Intelligence bonuses are ordinary actor-stat effects; the existing Psion runtime observes current Intelligence and derives bonus PP/save-DC behavior through its canonical paths.

Any future item that directly changes PP or psionic focus must call the canonical runtime state setters. Writing GemRB stat 239 or private focus/cache state from an item effect is not an accepted implementation path.

## Placement extension contract

A future store/encounter placement component should:

1. treat placement as optional and separate from item creation;
2. check for an existing identical placement before appending inventory;
3. use campaign-specific resource detection rather than assuming BG2 store names on every target;
4. leave component 200's resource-only behavior unchanged;
5. prove uninstall restoration for every modified store/CRE/area resource.
