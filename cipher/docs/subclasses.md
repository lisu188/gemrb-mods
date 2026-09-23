# Cipher subclasses

Cipher subclass identity is a stable actor-local numeric ID. The serialized private effect is authoritative; ScriptingState9/stat 164 is only a derived mirror used by installed SPLPROT resource logic. Focus remains on ScriptingState10/stat 165.

`BASE` is ID 0 and preserves the existing Cipher rules: normal Focus cap, normal power costs, 5 Focus from a successful hostile weapon hit, and the existing Soul Whip progression. Existing saves read as BASE until the player explicitly uses the subclass selector.

## Soul Blade

Soul Blade is ID 1. It is deliberately implemented as policy data plus shared resources rather than a second runtime handler.

- Maximum Focus: base cap + 10.
- Weapon Focus gain: 10 per eligible hostile weapon hit instead of 5.
- Power cost: base cost + 5 Focus.
- Power learning: unchanged.
- Soul Whip progression: unchanged.
- Selection: permanent during normal play; test/migration helpers can reset it to BASE.

This trade favors the weapon-to-Focus combat loop while making direct power use more expensive. The policy surface is bounded to cap, effective power cost, hit-gain units, passive/mirror resource and weapon policy, so later subclasses do not need a copy of `Cipher.py` or `begin_manifest()`.
