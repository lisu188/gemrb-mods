# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared reusable-innate charge normalization."""
import GemRB


def refresh(actor, predicate, spell_type=2, spell_level=0):
    known = {}
    for index in range(GemRB.GetKnownSpellsCount(actor, spell_type, spell_level)):
        spell = GemRB.GetKnownSpell(actor, spell_type, spell_level, index)
        resref = str(spell.get("SpellResRef", "")).upper()
        if predicate(resref):
            known[resref] = index

    charged = set()
    depleted = []
    count = GemRB.GetMemorizedSpellsCount(actor, spell_type, spell_level, False)
    for index in range(count):
        spell = GemRB.GetMemorizedSpell(actor, spell_type, spell_level, index)
        resref = str(spell.get("SpellResRef", "")).upper()
        if resref not in known:
            continue
        if spell.get("Flags", 0):
            charged.add(resref)
        else:
            depleted.append((index, resref))

    needed = []
    for index, resref in reversed(depleted):
        if GemRB.UnmemorizeSpell(actor, spell_type, spell_level, index):
            if resref not in charged and resref not in needed:
                needed.append(resref)

    restored = 0
    for resref in reversed(needed):
        if GemRB.MemorizeSpell(actor, spell_type, spell_level, known[resref], 1):
            restored += 1
    return restored
