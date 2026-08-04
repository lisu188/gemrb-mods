# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the GemRB Psion mod.

Power points, psionic focus, implemented feat ownership, and consumed class
bonus-feat credits use private, non-dispellable actor effects that GemRB
serializes with normal CRE effect blocks. GemRB user stat 239 remains only a
fast PP cache.

Manifestation uses the existing two-phase SpellPressed transaction: the first
callback reserves an action while target/selector UI is active, and the matching
confirmation callback performs irreversible PP or feat changes. Center Mind is
special: confirmation only authorizes its cast; PXCNTR writes focus when the
speed-9 spell actually resolves, so interruption cannot grant focus early.
"""
import GemRB

CURRENT_POOL_STAT = 239
POOL_STATE_SIGNATURE = 0x50530000
POOL_STATE_SIGNATURE_MASK = 0xFFFF0000
POOL_VALUE_MASK = 0x0000FFFF

STATE_EFFECT_OPCODE = "Protection:Spell"
POOL_EFFECT_MARKER = 0x50535050
POOL_EFFECT_RESOURCE = "PSPPSTAT"
POOL_EFFECT_SOURCE = "PSPPMOD"

FOCUS_EFFECT_MARKER = 0x50534643
FOCUS_EFFECT_RESOURCE = "PSFOCUS"
FOCUS_EFFECT_SOURCE = "PSFMOD"
CENTER_RESOURCE = "PXCNTR"
FEAT_SELECTOR_RESOURCE = "PXFSEL"
SPEED_ON_RESOURCE = "PXFSPED"
SPEED_OFF_RESOURCE = "PXFSPOF"
SPEED_BLOCK_MARKER = 0x50534642
SPEED_BLOCK_SOURCE = "PSFMOD"

BONUS_FEAT_SPENT_MARKER = 0x50534653
BONUS_FEAT_SPENT_RESOURCE = "PSFSPENT"
BONUS_FEAT_SPENT_SOURCE = "PSFMOD"
FEAT_EFFECT_SOURCE = "PSFEAT"
FEAT_MARKERS = {
    "PXFTALT": 0x50534601,
    "PXFBODY": 0x50534602,
    "PXFSPD": 0x50534603,
}
# Protection:Spell is used only as a serialized private-effect carrier. Keep its
# Resource1 values away from real selector child SPLs so state cannot grant
# accidental immunity to the live feat resources themselves.
FEAT_STATE_RESOURCES = {
    "PXFTALT": "PXTALST",
    "PXFBODY": "PXBODST",
    "PXFSPD": "PXSPDST",
}
PSIONIC_TALENT = "PXFTALT"
PSIONIC_BODY = "PXFBODY"
SPEED_OF_THOUGHT = "PXFSPD"
BONUS_FEAT_LEVELS = (1, 5, 10, 15, 20)

INT_STAT = 38
WIS_STAT = 39
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


def _feat_table():
    try:
        return GemRB.LoadTable("psionfeatpick", False, True)
    except Exception:
        return None


def feat_choice_info(resref):
    key = (resref or "").upper()
    if key not in FEAT_MARKERS:
        return None
    table = _feat_table()
    if not table:
        return None
    try:
        return {
            "kind": "feat_choice",
            "resref": key,
            "parent": key,
            "feat": str(table.GetValue(key, "FEAT")).upper(),
            "min_level": int(table.GetValue(key, "MIN_LEVEL")),
            "wis": int(table.GetValue(key, "WIS")),
            "repeatable": bool(int(table.GetValue(key, "REPEATABLE"))),
        }
    except Exception:
        return None


def feat_rank(actor, resref):
    key = (resref or "").upper()
    marker = FEAT_MARKERS.get(key)
    state_resource = FEAT_STATE_RESOURCES.get(key)
    if marker is None or state_resource is None:
        return 0
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != marker:
                continue
            if str(effect.get("Resource1", "")).upper() != state_resource:
                continue
            return max(0, int(effect.get("Param1", 0)))
    except Exception as error:
        GemRB.Log(2, "Psionics", "feat state read failed: %s" % error)
    return 0


def _write_feat_rank(actor, resref, rank):
    key = resref.upper()
    marker = FEAT_MARKERS[key]
    state_resource = FEAT_STATE_RESOURCES[key]
    rank = max(0, int(rank))
    GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, marker)
    if rank:
        GemRB.ApplyEffect(
            actor,
            STATE_EFFECT_OPCODE,
            rank,
            marker,
            state_resource,
            "",
            "",
            FEAT_EFFECT_SOURCE,
        )
    return rank


def psionic_feat_count(actor):
    """Count owned psionic feat selections for Psionic Body scaling."""
    return sum(feat_rank(actor, resref) for resref in FEAT_MARKERS)


def bonus_feat_spent(actor):
    """Return how many Psion class bonus-feat credits were consumed."""
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != BONUS_FEAT_SPENT_MARKER:
                continue
            if str(effect.get("Resource1", "")).upper() != BONUS_FEAT_SPENT_RESOURCE:
                continue
            return max(0, int(effect.get("Param1", 0)))
    except Exception as error:
        GemRB.Log(2, "Psionics", "bonus feat credit read failed: %s" % error)
    return 0


def _write_bonus_feat_spent(actor, spent):
    spent = max(0, int(spent))
    GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, BONUS_FEAT_SPENT_MARKER)
    if spent:
        GemRB.ApplyEffect(
            actor,
            STATE_EFFECT_OPCODE,
            spent,
            BONUS_FEAT_SPENT_MARKER,
            BONUS_FEAT_SPENT_RESOURCE,
            "",
            "",
            BONUS_FEAT_SPENT_SOURCE,
        )
    return spent


def bonus_feat_slots(actor):
    level = manifester_level(actor)
    return sum(1 for threshold in BONUS_FEAT_LEVELS if level >= threshold)


def bonus_feats_remaining(actor):
    return max(0, bonus_feat_slots(actor) - bonus_feat_spent(actor))


def psionic_talent_bonus(actor):
    rank = feat_rank(actor, PSIONIC_TALENT)
    return rank * (rank + 3) // 2


def can_select_feat(actor, resref):
    info = feat_choice_info(resref)
    if not info or not is_psion(actor) or bonus_feats_remaining(actor) <= 0:
        return False
    if manifester_level(actor) < info["min_level"]:
        return False
    if GemRB.GetPlayerStat(actor, WIS_STAT) < info["wis"]:
        return False
    if not info["repeatable"] and feat_rank(actor, info["resref"]):
        return False
    return True


def available_feat_choices(actor):
    table = _feat_table()
    if not table or bonus_feats_remaining(actor) <= 0:
        return []
    available = []
    try:
        for index in range(table.GetRowCount()):
            resref = table.GetRowName(index)
            if can_select_feat(actor, resref):
                available.append(resref.upper())
    except Exception:
        return []
    return available


def maximum_pool(actor):
    """Return D&D 3.5e base PP, Intelligence bonus PP, and Psionic Talent."""
    level = manifester_level(actor)
    if not level:
        return 0
    intelligence = GemRB.GetPlayerStat(actor, INT_STAT)
    modifier = max(0, (intelligence - 10) // 2)
    table = GemRB.LoadTable("psionpool", False, True)
    base = int(table.GetValue(str(level), "BASE_POOL"))
    return max(0, base + (modifier * level) // 2 + psionic_talent_bonus(actor))


def _decode_pool_state(actor):
    raw = int(GemRB.GetPlayerStat(actor, CURRENT_POOL_STAT))
    initialized = (raw & POOL_STATE_SIGNATURE_MASK) == POOL_STATE_SIGNATURE
    return initialized, raw & POOL_VALUE_MASK


def _write_pool_cache(actor, current):
    current = max(0, min(int(current), POOL_VALUE_MASK))
    GemRB.SetPlayerStat(actor, CURRENT_POOL_STAT, POOL_STATE_SIGNATURE | current)
    return current


def _read_persistent_pool_state(actor):
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
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
    current = max(0, min(int(current), POOL_VALUE_MASK))
    GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, POOL_EFFECT_MARKER)
    GemRB.ApplyEffect(
        actor, STATE_EFFECT_OPCODE, current, POOL_EFFECT_MARKER,
        POOL_EFFECT_RESOURCE, "", "", POOL_EFFECT_SOURCE,
    )
    return _write_pool_cache(actor, current)


def ensure_pool(actor, refill=False):
    if not is_psion(actor):
        return 0
    cap = min(maximum_pool(actor), POOL_VALUE_MASK)
    initialized, current = _decode_pool_state(actor)
    if initialized and not refill:
        clamped = max(0, min(current, cap))
        if clamped != current:
            return _write_pool_state(actor, clamped)
        return clamped
    if refill:
        return _write_pool_state(actor, cap)
    persisted, current = _read_persistent_pool_state(actor)
    if persisted:
        clamped = max(0, min(current, cap))
        if clamped != current:
            return _write_pool_state(actor, clamped)
        return _write_pool_cache(actor, clamped)
    return _write_pool_state(actor, cap)


def _read_focus_state(actor):
    """Read focus, accepting a resolved PXCNTR marker alongside old state."""
    found = False
    focused = False
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != FOCUS_EFFECT_MARKER:
                continue
            if str(effect.get("Resource1", "")).upper() != FOCUS_EFFECT_RESOURCE:
                continue
            found = True
            # Runtime may have written an unfocused 0 record before PXCNTR later
            # resolves with a focused 1 record. Any resolved focused marker wins;
            # the next explicit state write compacts them back to one effect.
            focused = focused or bool(int(effect.get("Param1", 0)))
    except Exception as error:
        GemRB.Log(2, "Psionics", "focus state read failed: %s" % error)
    return found, focused


def _sync_speed_gate(actor, owns_speed=None):
    """Allow PXFSPED only for characters who own Speed of Thought."""
    if not is_psion(actor):
        return
    if owns_speed is None:
        owns_speed = feat_rank(actor, SPEED_OF_THOUGHT) > 0
    try:
        GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, SPEED_BLOCK_MARKER)
        if not owns_speed:
            GemRB.ApplyEffect(
                actor,
                STATE_EFFECT_OPCODE,
                0,
                SPEED_BLOCK_MARKER,
                SPEED_ON_RESOURCE,
                "",
                "",
                SPEED_BLOCK_SOURCE,
            )
    except Exception as error:
        GemRB.Log(2, "Psionics", "speed helper gate sync failed: %s" % error)


def _sync_focus_passives(actor, focused=None):
    if not is_psion(actor):
        return
    if focused is None:
        persisted, focused = _read_focus_state(actor)
        if not persisted:
            focused = True
    owns_speed = feat_rank(actor, SPEED_OF_THOUGHT) > 0
    _sync_speed_gate(actor, owns_speed)
    try:
        if owns_speed and focused:
            GemRB.ApplySpell(actor, SPEED_ON_RESOURCE)
        else:
            GemRB.ApplySpell(actor, SPEED_OFF_RESOURCE)
    except Exception as error:
        GemRB.Log(2, "Psionics", "focus passive sync failed: %s" % error)


def _write_focus_state(actor, focused):
    focused = bool(focused)
    GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, FOCUS_EFFECT_MARKER)
    GemRB.ApplyEffect(
        actor, STATE_EFFECT_OPCODE, 1 if focused else 0, FOCUS_EFFECT_MARKER,
        FOCUS_EFFECT_RESOURCE, "", "", FOCUS_EFFECT_SOURCE,
    )
    _sync_focus_passives(actor, focused)
    return focused


def ensure_focus(actor, refill=False):
    if not is_psion(actor):
        return False
    if refill:
        return _write_focus_state(actor, True)
    persisted, focused = _read_focus_state(actor)
    if persisted:
        return focused
    return _write_focus_state(actor, True)


def is_focused(actor):
    return ensure_focus(actor)


def expend_focus(actor):
    if not is_psion(actor):
        return False
    _write_focus_state(actor, False)
    return True


def _apply_body_hp(actor, amount):
    amount = max(0, int(amount))
    if not amount:
        return
    GemRB.ApplyEffect(actor, "MaximumHPModifier", amount, 0, "", "", "", "PXFBODY", 9)
    GemRB.ApplyEffect(actor, "CurrentHPModifier", amount, 0, "", "", "", "PXFBODY", 9)


def _grant_feat(actor, resref):
    info = feat_choice_info(resref)
    if not info or not can_select_feat(actor, resref):
        return False

    current_pp = ensure_pool(actor)
    old_cap = maximum_pool(actor)
    had_body = feat_rank(actor, PSIONIC_BODY) > 0
    old_rank = feat_rank(actor, info["resref"])
    spent = bonus_feat_spent(actor)
    _write_feat_rank(actor, info["resref"], old_rank + 1)
    _write_bonus_feat_spent(actor, spent + 1)

    new_cap = maximum_pool(actor)
    if new_cap > old_cap:
        _write_pool_state(actor, min(new_cap, current_pp + (new_cap - old_cap)))

    if info["resref"] == PSIONIC_BODY:
        _apply_body_hp(actor, 2 * psionic_feat_count(actor))
    elif had_body:
        _apply_body_hp(actor, 2)

    _sync_focus_passives(actor)
    return True


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            ensure_pool(actor, True)
            ensure_focus(actor, True)
        except Exception:
            pass


def _base_power_info(key):
    table = GemRB.LoadTable("psionpowers", False, True)
    try:
        return {
            "kind": "power",
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
        base["selector"] = True
        base["cost"] = 0
    return base


def action_info(resref):
    key = (resref or "").upper()
    if key == CENTER_RESOURCE:
        return {"kind": "center", "resref": key, "parent": key, "cost": 0, "selector": False}
    if key == FEAT_SELECTOR_RESOURCE:
        return {"kind": "feat_selector", "resref": key, "parent": key, "cost": 0, "selector": True}
    feat = feat_choice_info(key)
    if feat:
        return feat
    return power_info(key)


def resolve_power_entry(spellbook, actor, raw_spell):
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
        if action_info(resref):
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
            if action_info(resref):
                return candidate
    return None


def _meets_base_requirements(actor, info):
    actor_discipline = discipline(actor)
    if not info or not actor_discipline:
        return False
    if info["discipline"] not in ("GENERAL", actor_discipline):
        return False
    return GemRB.GetPlayerStat(actor, INT_STAT) >= 10 + info["level"]


def _variant_is_affordable(actor, info):
    return info["cost"] <= manifester_level(actor) and ensure_pool(actor) >= info["cost"]


def can_manifest(actor, resref):
    info = power_info(resref)
    if not _meets_base_requirements(actor, info):
        return False
    if info["selector"]:
        return bool(available_variants(actor, info["resref"], check_parent=False))
    return _variant_is_affordable(actor, info)


def available_variants(actor, parent, check_parent=True):
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
    filtered = []
    for resref in resrefs:
        feat = feat_choice_info(resref)
        if feat:
            if can_select_feat(actor, resref):
                filtered.append(resref)
            continue
        info = power_info(resref)
        if not info or not info.get("variant", False):
            filtered.append(resref)
        elif can_manifest(actor, resref):
            filtered.append(resref)
    return filtered


def _is_reusable_innate(actor, resref):
    key = (resref or "").upper()
    if power_info(key) or key == CENTER_RESOURCE:
        return True
    if key == FEAT_SELECTOR_RESOURCE:
        return bonus_feats_remaining(actor) > 0
    return False


def refresh_innate_charges(actor):
    if not is_psion(actor):
        return 0
    # A successfully resolved PXCNTR may have added a focused marker after the
    # pre-cast GUI callback. Reconcile focus-dependent passives whenever the
    # Psion bar is reopened, without converting an unresolved reservation.
    _sync_focus_passives(actor)
    try:
        known = {}
        known_count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(known_count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            resref = str(spell.get("SpellResRef", "")).upper()
            if _is_reusable_innate(actor, resref):
                known[resref] = index

        charged = set()
        depleted = []
        memorized_count = GemRB.GetMemorizedSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL, False)
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
            if GemRB.MemorizeSpell(actor, INNATE_TYPE, INNATE_LEVEL, known[resref], 1):
                restored += 1
        return restored
    except Exception as error:
        GemRB.Log(2, "Psionics", "charge refresh failed: %s" % error)
        return 0


def _begin_simple_action(actor, transaction, legal, commit):
    pending = _pending.get(actor)
    if pending == transaction:
        if not legal():
            _pending.pop(actor, None)
            return False
        _pending.pop(actor, None)
        return bool(commit())
    if not legal():
        return False
    _pending[actor] = transaction
    return True


def begin_manifest(actor, resref):
    info = action_info(resref)
    if not info:
        return True

    if info["kind"] == "center":
        # Guarantee the ownership gate before the resolution SPL fires, even
        # for an unfocused save created by an earlier development build.
        _sync_speed_gate(actor)
        return _begin_simple_action(
            actor,
            ("CENTER", CENTER_RESOURCE),
            lambda: not is_focused(actor),
            # PXCNTR.spl itself writes the focus marker and casts PXFSPED after
            # successful resolution. Confirmation must not grant focus early.
            lambda: True,
        )

    if info["kind"] == "feat_selector":
        cancel_pending(actor)
        return bool(available_feat_choices(actor))

    if info["kind"] == "feat_choice":
        key = info["resref"]
        return _begin_simple_action(
            actor,
            ("FEAT", key),
            lambda: can_select_feat(actor, key),
            lambda: _grant_feat(actor, key),
        )

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
    if actor is None:
        _pending.clear()
    else:
        _pending.pop(actor, None)


def pool_text(actor):
    return "%d/%d" % (ensure_pool(actor), maximum_pool(actor))


def focus_text(actor):
    return "Focused" if is_focused(actor) else "Unfocused"
