# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the GemRB Psion mod.

Power points are stored in GemRB's user-defined actor stat 239. Manifestation
uses a two-phase transaction: the first SpellPressed callback reserves a power,
while the second callback commits its cost. Cancelling target selection and
opening the power list again clears the reservation without charging points.
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


def power_info(resref):
    """Load one power's authoritative metadata from PSIONPOWERS.2DA."""
    key = (resref or "").upper()
    if not key.startswith("PS"):
        return None
    table = GemRB.LoadTable("psionpowers", False, True)
    try:
        return {
            "resref": key,
            "level": int(table.GetValue(key, "LEVEL")),
            "discipline": str(table.GetValue(key, "DISCIPLINE")).upper(),
            "cost": int(table.GetValue(key, "BASE_COST")),
            "augment_step": int(table.GetValue(key, "AUGMENT_STEP")),
        }
    except Exception:
        return None


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
    if info["cost"] > manifester_level(actor):
        return False
    return ensure_pool(actor) >= info["cost"]


def begin_manifest(actor, resref):
    """Reserve on the first callback and spend on the matching second callback.

    GemRB's spell action invokes SpellPressed twice for an ordinary cast. This
    avoids charging a power that the player cancels during target selection.
    """
    info = power_info(resref)
    if not info:
        return True

    key = (actor, info["resref"])
    if _pending.get(actor) == key:
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

    _pending[actor] = key
    return True


def cancel_pending(actor=None):
    """Cancel one actor's reservation, or every reservation during rest."""
    if actor is None:
        _pending.clear()
    else:
        _pending.pop(actor, None)


def pool_text(actor):
    return "%d/%d" % (ensure_pool(actor), maximum_pool(actor))
