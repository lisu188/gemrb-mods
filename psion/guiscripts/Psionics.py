# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the GemRB Psion mod.

Power points are stored in GemRB's user-defined actor stat 239. Manifestation
uses a two-phase transaction: the first SpellPressed callback reserves a power,
while the second callback commits its cost. Selector resources are free; their
chosen child resources carry the authoritative augmented PP cost.
"""
import GemRB

CURRENT_POOL_STAT = 239
POOL_READY_STAT = 188
INT_STAT = 38
LEVEL_STAT = 34

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
    """Return D&D 3e base PP plus the Intelligence bonus PP."""
    level = manifester_level(actor)
    if not level:
        return 0
    intelligence = GemRB.GetPlayerStat(actor, INT_STAT)
    modifier = max(0, (intelligence - 10) // 2)
    table = GemRB.LoadTable("psionpool", False, True)
    base = int(table.GetValue(str(level), "BASE_POOL"))
    return max(0, base + (modifier * level) // 2)


def ensure_pool(actor, refill=False):
    if not is_psion(actor):
        return 0
    cap = maximum_pool(actor)
    ready = GemRB.GetPlayerStat(actor, POOL_READY_STAT)
    current = GemRB.GetPlayerStat(actor, CURRENT_POOL_STAT)
    if refill or not ready:
        current = cap
        GemRB.SetPlayerStat(actor, POOL_READY_STAT, 1)
    current = max(0, min(current, cap))
    GemRB.SetPlayerStat(actor, CURRENT_POOL_STAT, current)
    return current


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
            "augment_step": int(table.GetValue(key, "AUGMENT_STEP")),
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


def can_manifest(actor, resref):
    """Check class, discipline, ability score, level and pool requirements."""
    info = power_info(resref)
    actor_discipline = discipline(actor)
    if not info or not actor_discipline:
        return False
    if info["discipline"] not in ("GENERAL", actor_discipline):
        return False
    if GemRB.GetPlayerStat(actor, INT_STAT) < 10 + info["level"]:
        return False
    if info["selector"]:
        return True
    if info["cost"] > manifester_level(actor):
        return False
    return ensure_pool(actor) >= info["cost"]


def available_variants(actor, parent):
    """Return legal child resrefs for a future dedicated augmentation GUI."""
    table = _augment_table()
    if not table or not can_manifest(actor, parent):
        return []
    available = []
    try:
        for index in range(table.GetRowCount()):
            resref = table.GetRowName(index)
            if str(table.GetValue(resref, "PARENT")).upper() != parent.upper():
                continue
            if can_manifest(actor, resref):
                available.append(resref.upper())
    except Exception:
        return []
    return available


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
        GemRB.SetPlayerStat(actor, CURRENT_POOL_STAT, current - info["cost"])
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
