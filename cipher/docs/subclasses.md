# Cipher subclasses

Cipher subclasses share the single `cipher/guiscripts/Cipher.py` runtime. Subclass identity is stored actor-locally through `PersistentState`; stat 166 is only a synchronized mirror used by installed resource routing.

## Base Cipher

Characters with no stored subclass ID remain base Ciphers. Their Focus cap, power costs, weapon Focus gain, known powers and selector behavior are unchanged.

## Soul Blade

Soul Blade is subclass ID 1.

- Weapon hits generate two Focus units (10 Focus) instead of one unit (5 Focus).
- Cipher powers cost 5 additional Focus.
- Power learning is unchanged.
- Focus spending still goes through the normal Cipher transaction and setter path.
- Weapon Focus gain still terminates in the shared `CIFS<n>` setter family.

Existing saves remain base Ciphers and are not forced into a subclass choice. New Ciphers receive the subclass selector from the class ability table.
