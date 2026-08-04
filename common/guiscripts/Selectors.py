# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared helpers for GemRB temporary selector entries."""
import GemRB


def resolve_temporary(actor, raw_spell, predicate, temporary_type=255):
    encoded_type = raw_spell // 1000
    if encoded_type != temporary_type:
        return None
    index = raw_spell % 1000
    try:
        resrefs = GemRB.GetSpelldata(actor)
        if index < 0 or index >= len(resrefs):
            return None
        resref = str(resrefs[index])
    except Exception:
        return None
    if not predicate(resref):
        return None
    return {"SpellIndex": raw_spell, "SpellResRef": resref}


def filter_resrefs(resrefs, predicate):
    return [resref for resref in resrefs if predicate(resref)]
