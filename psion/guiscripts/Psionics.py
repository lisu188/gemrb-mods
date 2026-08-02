# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the GemRB Psion mod.

Power-point state is persisted in a private, non-dispellable actor effect that
GemRB serializes with normal CRE effect blocks. GemRB user stat 239 is only a
fast runtime cache: its high word carries a Psion signature and its low word the
current PP value. This avoids depending on arbitrary user-stat serialization
across save/load while still keeping PP reads cheap during selector filtering.

Manifestation uses a two-phase transaction: the first SpellPressed callback
reserves a power, while the second callback commits its cost. Selector resources
are free; their chosen child resources carry the authoritative augmented PP cost.

Opcode 214 places selector children in GemRB's temporary spellinfo list. The
``filter_spellinfo`` hook removes Psion variants that the selected actor cannot
currently afford or legally augment to, while leaving unrelated temporary
spell selectors untouched. Cast-time type-255 resolution uses the raw GemRB
spellinfo array, so confirmation can still identify and reject a child even if
its affordability changed after the selector UI was built.
"""
import GemRB

CURRENT_POOL_STAT = 239
POOL_STATE_SIGNATURE = 0x50530000  # ASCII-ish "PS" in the high word.
POOL_STATE_SIGNATURE_MASK = 0xFFFF0000
POOL_VALUE_MASK = 0x0000FFFF

# Save-safe PP storage. Protection:Spell ignores Param1/Param2; a private,
# nonexistent resource therefore acts only as an inert serialized state carrier.
# GemRB.ApplyEffect defaults to resistance 0 (not resistible and not dispellable).
POOL_EFFECT_OPCODE = "Protection:Spell"
POOL_EFFECT_MARKER = 0x50535050  # ASCII-ish "PSPP", positive signed 32-bit.
POOL_EFFECT_RESOURCE = "PSPPSTAT"
POOL_EFFECT_SOURCE = "PSPPMOD"

INT_STAT = 38
LEVEL_STAT = 34
INNATE_TYPE = 2
INNATE_LEVEL = 0
TEMPORARY_SPELLINFO_TYPE = 255

PSION_CLASSES = {
    "PSION_SEER": "SEER",
    "PSION_SHAPER": "SHAPER",
    "PSION_KINETICIST": "KINETICIST",
    "PSION_EGOIST": "EGOIST",
    "PSION_NOMAD": "NOMAD",
    "PSION_TELEPATH": "TELEPATH",
}

_pending = {}


def _class_row(actor):
    try:
        import GUICommon
        return GUICommon.GetClassRowName(actor)
    except Exception:
        return ""


def discipline(actor):
    return PSION_CLASSES.get(_class_row(actor), "")


def is_psion(actor):
    return bool(discipline(actor))


def manifester_level(actor):
    if not is_psion(actor):
        return 0
    return max(1, min(20, GemRB.GetPlayerStat(actor, LEVEL_STAT)))


def maximum_pool(actor):
    """Return D&D 3.5e base PP plus the Intelligence bonus PP."""
    level = manifester_level(actor)
    if not level:
        return 0
    intelligence = GemRB.GetPlayerStat(actor, INT_STAT)
    modifier = max(0, (intelligence - 10) // 2)
    table = GemRB.LoadTable("psionpool", False, True)
    base = int(table.GetValue(str(level), "BASE_POOL"))
    return max(0, base + (modifier * level) // 2)


def _decode_pool_state(actor):
    """Decode the fast stat-239 cache; it is not the save authority."""
    raw = int(GemRB.GetPlayerStat(actor, CURRENT_POOL_STAT))
    initialized = (
        raw & POOL_STATE_SIGNATURE_MASK
    ) == POOL_STATE_SIGNATURE
    return initialized, raw & POOL_VALUE_MASK


def _write_pool_cache(actor, current):
    current = max(0, min(int(current), POOL_VALUE_MASK))
    GemRB.SetPlayerStat(
        actor,
        CURRENT_POOL_STAT,
        POOL_STATE_SIGNATURE | current,
    )
    return current


def _read_persistent_pool_state(actor):
    """Read PP from the private serialized actor effect after save/load."""
    try:
        for effect in GemRB.GetEffects(actor, POOL_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != POOL_EFFECT_MARKER:
                continue
            if str(effect.get("Resource1", "")).upper() != POOL_EFFECT_RESOURCE:
                continue
            current = max(0, min(int(effect.get("Param1", 0)), POOL_VALUE_MASK))
            return True, current
    except Exception as error:
        GemRB.Log(2, "Psionics", "persistent PP read failed: %s" % error)
    return False, 0


def _write_pool_state(actor, current):
    """Persist PP in the actor effect queue and mirror it into stat 239."""
    current = max(0, min(int(current), POOL_VALUE_MASK))
    # Remove only our marker. The deliberately large Param2 value makes a
    # collision with an unrelated Protection:Spell effect extremely unlikely.
    GemRB.DispelEffect(actor, POOL_EFFECT_OPCODE, POOL_EFFECT_MARKER)
    GemRB.ApplyEffect(
        actor,
        POOL_EFFECT_OPCODE,
        current,
        POOL_EFFECT_MARKER,
        POOL_EFFECT_RESOURCE,
        "",
        "",
        POOL_EFFECT_SOURCE,
    )
    return _write_pool_cache(actor, current)


def ensure_pool(actor, refill=False):
    if not is_psion(actor):
        return 0
    cap = min(maximum_pool(actor), POOL_VALUE_MASK)

    # Normal runtime path: stat 239 is a cheap cache, avoiding effect scans for
    # every affordability check in a large augmentation selector.
    initialized, current = _decode_pool_state(actor)
    if initialized and not refill:
        clamped = max(0, min(current, cap))
        if clamped != current:
            return _write_pool_state(actor, clamped)
        return clamped

    if refill:
        return _write_pool_state(actor, cap)

    # A cache miss is the expected post-load path on BG-family CRE formats.
    # Recover the authoritative serialized effect and rebuild the fast cache.
    persisted, current = _read_persistent_pool_state(actor)
    if persisted:
        clamped = max(0, min(current, cap))
        if clamped != current:
            return _write_pool_state(actor, clamped)
        return _write_pool_cache(actor, clamped)

    # First use on a Psion: initialize a full pool and immediately create the
    # save-safe effect, including for a genuine zero-cap edge case.
    return _write_pool_state(actor, cap)


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            ensure_pool(actor, True)
        except Exception:
            pass


def _base_power_info(key):
    table = GemRB.LoadTable("psionpowers", False, True)
    try:
        return {
            "resref": key,
            "parent": key,
            "level": int(table.GetValue(key, "LEVEL")),
            "discipline": str(table.GetValue(key, "DISCIPLINE")).upper(),
            "cost": int(table.GetValue(key, "BASE_COST")),
            "selector": False,
            "variant": False,
        }
    except Exception:
        return None


def _augment_table():
    try:
        return GemRB.LoadTable("psionaugment", False, True)
    except Exception:
        return None


def augment_info(resref):
    """Return child-resource augmentation metadata, if present."""
    key = (resref or "").upper()
    table = _augment_table()
    if not table:
        return None
    try:
        return {
            "resref": key,
            "parent": str(table.GetValue(key, "PARENT")).upper(),
            "cost": int(table.GetValue(key, "TOTAL_COST")),
            "effect": str(table.GetValue(key, "EFFECT")).upper(),
            "value": str(table.GetValue(key, "VALUE")).upper(),
        }
    except Exception:
        return None


def _has_variants(parent):
    table = _augment_table()
    if not table:
        return False
    key = parent.upper()
    try:
        for index in range(table.GetRowCount()):
            row = table.GetRowName(index)
            if str(table.GetValue(row, "PARENT")).upper() == key:
                return True
    except Exception:
        return False
    return False


def power_info(resref):
    """Load base or augmented power metadata from the authoritative 2DAs."""
    key = (resref or "").upper()
    if not key.startswith("PS"):
        return None

    augmented = augment_info(key)
    if augmented:
        base = _base_power_info(augmented["parent"])
        if not base:
            return None
        base.update(augmented)
        base["selector"] = False
        base["variant"] = True
        return base

    base = _base_power_info(key)
    if not base:
        return None
    if _has_variants(key):
        # The parent only opens an opcode-214 choice list. Spending happens on
        # the selected child resource, never on the selector itself.
        base["selector"] = True
        base["cost"] = 0
    return base


def resolve_power_entry(spellbook, actor, raw_spell):
    """Resolve a GemRB spell token to a registered Psion resource.

    Opcode-214 selector children use GemRB's synthetic spellinfo type 255. Their
    small list indices overlap ordinary spellbook indices, so type 255 is
    resolved directly against GemRB's raw spellinfo array. This deliberately
    bypasses the affordability-filtered UI list: confirmation must still find a
    selected child so ``begin_manifest`` can reject it if PP changed meanwhile.
    """
    encoded_type = raw_spell // 1000
    spell_index = raw_spell % 1000

    if encoded_type == TEMPORARY_SPELLINFO_TYPE:
        try:
            spell_resrefs = GemRB.GetSpelldata(actor)
            if spell_index < 0 or spell_index >= len(spell_resrefs):
                return None
            resref = spell_resrefs[spell_index]
        except Exception:
            return None
        if power_info(resref):
            return {"SpellIndex": raw_spell, "SpellResRef": resref}
        return None

    book_types = [i for i in range(16) if encoded_type & (1 << i)]
    if not book_types:
        book_types = range(16)
    for book_type in book_types:
        for candidate in spellbook.GetUsableMemorizedSpells(actor, book_type):
            if candidate.get("SpellIndex", -1) % 1000 != spell_index:
                continue
            resref = candidate.get("SpellResRef", "")
            if power_info(resref):
                return candidate
    return None


def _meets_base_requirements(actor, info):
    """Check restrictions shared by a selector and all of its child variants."""
    actor_discipline = discipline(actor)
    if not info or not actor_discipline:
        return False
    if info["discipline"] not in ("GENERAL", actor_discipline):
        return False
    return GemRB.GetPlayerStat(actor, INT_STAT) >= 10 + info["level"]


def _variant_is_affordable(actor, info):
    """Check the D&D 3.5e spending cap and the actor's current PP reserve."""
    return (
        info["cost"] <= manifester_level(actor)
        and ensure_pool(actor) >= info["cost"]
    )


def can_manifest(actor, resref):
    """Check class, discipline, ability score, level and pool requirements."""
    info = power_info(resref)
    if not _meets_base_requirements(actor, info):
        return False
    if info["selector"]:
        # A selector is useful only when at least one child can actually be
        # manifested. This prevents an empty choice list at zero PP.
        return bool(available_variants(actor, info["resref"], check_parent=False))
    return _variant_is_affordable(actor, info)


def available_variants(actor, parent, check_parent=True):
    """Return legal child resrefs for the selected actor, preserving 2DA order."""
    parent_info = power_info(parent)
    table = _augment_table()
    if not table or not _meets_base_requirements(actor, parent_info):
        return []
    if check_parent and not parent_info.get("selector", False):
        return []

    available = []
    try:
        for index in range(table.GetRowCount()):
            resref = table.GetRowName(index)
            if str(table.GetValue(resref, "PARENT")).upper() != parent.upper():
                continue
            info = power_info(resref)
            if info and _meets_base_requirements(actor, info) and _variant_is_affordable(actor, info):
                available.append(resref.upper())
    except Exception:
        return []
    return available


def filter_spellinfo(actor, resrefs):
    """Filter temporary opcode-214 choices without affecting other mods.

    Non-Psion resources and ordinary Psion powers are returned unchanged. Only
    entries registered as children in PSIONAUGMENT.2DA are subject to the
    current PP, manifester-level, discipline and Intelligence checks.
    """
    filtered = []
    for resref in resrefs:
        info = power_info(resref)
        if not info or not info.get("variant", False):
            filtered.append(resref)
        elif can_manifest(actor, resref):
            filtered.append(resref)
    return filtered


def refresh_innate_charges(actor):
    """Replace depleted Psion innate entries with one usable copy.

    CLAB ``GA_`` grants create ordinary one-charge innate entries. Psion powers
    are limited by PP instead, so the next time the innate bar opens we remove
    depleted Psion entries and memorize their known spell again. Other innate
    abilities are never touched, and an already usable duplicate is preserved.
    """
    if not is_psion(actor):
        return 0

    try:
        known = {}
        known_count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(known_count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            resref = str(spell.get("SpellResRef", "")).upper()
            if power_info(resref):
                known[resref] = index

        charged = set()
        depleted = []
        memorized_count = GemRB.GetMemorizedSpellsCount(
            actor, INNATE_TYPE, INNATE_LEVEL, False
        )
        for index in range(memorized_count):
            spell = GemRB.GetMemorizedSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            resref = str(spell.get("SpellResRef", "")).upper()
            if resref not in known:
                continue
            if spell.get("Flags", 0):
                charged.add(resref)
            else:
                depleted.append((index, resref))

        needed = []
        for index, resref in reversed(depleted):
            if GemRB.UnmemorizeSpell(actor, INNATE_TYPE, INNATE_LEVEL, index):
                if resref not in charged and resref not in needed:
                    needed.append(resref)

        restored = 0
        for resref in reversed(needed):
            if GemRB.MemorizeSpell(
                actor, INNATE_TYPE, INNATE_LEVEL, known[resref], 1
            ):
                restored += 1
        return restored
    except Exception as error:
        GemRB.Log(2, "Psionics", "charge refresh failed: %s" % error)
        return 0


def begin_manifest(actor, resref):
    """Reserve on the first callback and spend on the matching second callback.

    GemRB's spell action invokes SpellPressed twice for an ordinary cast. This
    avoids charging a power that the player cancels during target selection.
    Selector resources do not reserve PP; their chosen variants do.
    """
    info = power_info(resref)
    if not info:
        return True
    if info["selector"]:
        cancel_pending(actor)
        return can_manifest(actor, info["resref"])

    pending = _pending.get(actor)
    transaction = (info["resref"], info["cost"])
    if pending == transaction:
        if not can_manifest(actor, info["resref"]):
            _pending.pop(actor, None)
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
            return False
        current = ensure_pool(actor)
        _write_pool_state(actor, current - info["cost"])
        _pending.pop(actor, None)
        return True

    if not can_manifest(actor, info["resref"]):
        GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return False

    _pending[actor] = transaction
    return True


def cancel_pending(actor=None):
    """Cancel one actor's reservation, or every reservation during rest."""
    if actor is None:
        _pending.clear()
    else:
        _pending.pop(actor, None)


def pool_text(actor):
    return "%d/%d" % (ensure_pool(actor), maximum_pool(actor))
