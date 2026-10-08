# Cipher subclasses

Cipher subclasses share the single `cipher/guiscripts/Cipher.py` runtime. Subclass identity is stored actor-locally through `PersistentState`; scripting state 8 (stat 163) is a synchronized mirror used by installed resource routing. A permanent actor effect preserves Soul Blade routing across save/load, including before its owner is selected. Melee attack bonuses are independent of subclass identity.

## Base Cipher

Characters with no stored subclass ID remain base Ciphers. Their Focus cap, power costs, weapon Focus gain, known powers and selector behavior are unchanged.

## Soul Blade

Soul Blade is subclass ID 1.

- Weapon hits generate two Focus units (10 Focus) instead of one unit (5 Focus).
- Hostile critical hits add another 10 Focus, for 20 total. Misses and attacks
  against friendly or neutral targets grant none.
- Cipher powers cost 5 additional Focus.
- Power learning is unchanged.
- Focus spending still goes through the normal Cipher transaction and setter path.
- Weapon Focus gain still terminates in the shared `CIFS<n>` setter family.
- Each gain is capped immediately at `20 + 5 × Cipher level` (maximum 170 at
  level 30), including when the Cipher is not selected. Reaping Knives transfers
  remain 5 Focus per ally hit, regardless of the owner's subclass.

Existing saves remain base Ciphers and are not forced into a subclass choice. New Ciphers receive the subclass selector from the class ability table.
