# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the GemRB Psion mod.

Power points, psionic focus, feats, class bonus-feat credits, and Psion skill
state use private non-dispellable actor effects that GemRB serializes with CRE
save data. GemRB user stat 239 remains only a fast PP cache.

Manifestation uses a two-phase SpellPressed transaction: the first callback
reserves an action while target/selector UI is active and the matching callback
performs irreversible PP, feat, or skill changes. Center Mind is special:
confirmation performs the Concentration check, while its SPL writes focus only
when the action resolves, so interruption cannot grant focus.
"""
import GemRB
import Transactions
import InnateCharges
import PersistentState
import Selectors
from ie_spells import LS_MEMO

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
MEDITATION_CENTER_RESOURCE = "PXCMEDI"
CENTER_RESOURCES = (CENTER_RESOURCE, MEDITATION_CENTER_RESOURCE)
FEAT_SELECTOR_RESOURCE = "PXFSEL"
POWER_SELECTOR_RESOURCE = "PXPLRN"
SKILL_SELECTOR_RESOURCE = "PXSKILL"
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
    "PXFMEDI": 0x50534604,
}
FEAT_STATE_RESOURCES = {
    "PXFTALT": "PXTALST",
    "PXFBODY": "PXBODST",
    "PXFSPD": "PXSPDST",
    "PXFMEDI": "PXMEDST",
}
PSIONIC_TALENT = "PXFTALT"
PSIONIC_BODY = "PXFBODY"
SPEED_OF_THOUGHT = "PXFSPD"
PSIONIC_MEDITATION = "PXFMEDI"
BONUS_FEAT_LEVELS = (1, 5, 10, 15, 20)

SKILL_POINTS_MARKER = 0x50535350
SKILL_POINTS_RESOURCE = "PSSKPTS"
SKILL_LEVEL_MARKER = 0x5053534C
SKILL_LEVEL_RESOURCE = "PSSKLVL"
SKILL_EFFECT_SOURCE = "PSSKIL"
SKILL_MARKERS = {
    "CONCENTRATION": 0x50535301,
    "PSICRAFT": 0x50535302,
    "SELF_DISCIPLINE": 0x50535303,
    "PSIONIC_KNOWLEDGE": 0x50535304,
    "DEVICE_LORE": 0x50535305,
    "AWARENESS": 0x50535306,
    "ECTOPLASMIC_CRAFT": 0x50535307,
    "ENERGY_LORE": 0x50535308,
    "HEAL": 0x50535309,
    "SPATIAL_NAVIGATION": 0x5053530A,
    "INFLUENCE": 0x5053530B,
}
SKILL_STATE_RESOURCES = {
    "CONCENTRATION": "PSCNCST",
    "PSICRAFT": "PSPSIST",
    "SELF_DISCIPLINE": "PSSLFST",
    "PSIONIC_KNOWLEDGE": "PSKNWST",
    "DEVICE_LORE": "PSDVCST",
    "AWARENESS": "PSAWRST",
    "ECTOPLASMIC_CRAFT": "PSECTST",
    "ENERGY_LORE": "PSENRST",
    "HEAL": "PSHEAST",
    "SPATIAL_NAVIGATION": "PSSPTST",
    "INFLUENCE": "PSINFST",
}
CONCENTRATION_SKILL = "CONCENTRATION"
SKILL_ABILITY_STATS = {
    "STR": 36,
    "INT": 38,
    "WIS": 39,
    "DEX": 40,
    "CON": 41,
    "CHA": 42,
}

INT_STAT = 38
WIS_STAT = 39
CON_STAT = 41
LEVEL_STAT = 34
INNATE_TYPE = 2
INNATE_LEVEL = 0
TEMPORARY_SPELLINFO_TYPE = 255

# BG-family GemRB games use MaximumAbility=25. Public Psion SPLs are authored
# for the class minimum INT 15 (+2); save-bearing internal clones cover every
# other reachable modifier without changing known-spell or PP state.
DC_BASELINE_MODIFIER = 2
DC_MODIFIER_SUFFIXES = {
    -5: "V", -4: "W", -3: "X", -2: "Y", -1: "Z",
    0: "0", 1: "1", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
}
DC_SUFFIX_MODIFIERS = {suffix: modifier for modifier, suffix in DC_MODIFIER_SUFFIXES.items()}

PSION_CLASSES = {
    "PSION_SEER": "SEER",
    "PSION_SHAPER": "SHAPER",
    "PSION_KINETICIST": "KINETICIST",
    "PSION_EGOIST": "EGOIST",
    "PSION_NOMAD": "NOMAD",
    "PSION_TELEPATH": "TELEPATH",
}

TRANSACTION_NAMESPACE = "Psionics"


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


def _skill_table():
    try:
        return GemRB.LoadTable("psionskills", False, True)
    except Exception:
        return None


def _skill_pick_table():
    try:
        return GemRB.LoadTable("psskill", False, True)
    except Exception:
        return None


def _power_pick_table():
    try:
        return GemRB.LoadTable("pspick", False, True)
    except Exception:
        return None


def _known_power_table():
    try:
        return GemRB.LoadTable("psionknown", False, True)
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
        skill = str(table.GetValue(key, "SKILL")).upper()
        if skill == "****":
            skill = ""
        return {
            "kind": "feat_choice",
            "resref": key,
            "parent": key,
            "feat": str(table.GetValue(key, "FEAT")).upper(),
            "min_level": int(table.GetValue(key, "MIN_LEVEL")),
            "wis": int(table.GetValue(key, "WIS")),
            "repeatable": bool(int(table.GetValue(key, "REPEATABLE"))),
            "skill": skill,
            "rank": int(table.GetValue(key, "RANK")),
        }
    except Exception:
        return None


def skill_rule_info(skill):
    key = (skill or "").upper()
    if key not in SKILL_MARKERS:
        return None
    table = _skill_table()
    if not table:
        return None
    try:
        return {
            "skill": key,
            "ability": str(table.GetValue(key, "ABILITY")).upper(),
            "access": str(table.GetValue(key, "ACCESS")).upper(),
            "cost": int(table.GetValue(key, "COST")),
            "break1": int(table.GetValue(key, "BREAK1")),
            "break2": int(table.GetValue(key, "BREAK2")),
            "break3": int(table.GetValue(key, "BREAK3")),
        }
    except Exception:
        return None


def skill_choice_info(resref):
    key = (resref or "").upper()
    table = _skill_pick_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            skill = str(table.GetRowName(index)).upper()
            if str(table.GetValue(skill, "ResRef")).upper() != key:
                continue
            info = skill_rule_info(skill)
            if not info:
                return None
            info.update({
                "kind": "skill_choice",
                "resref": key,
                "parent": key,
            })
            return info
    except Exception:
        return None
    return None


def power_choice_info(resref):
    key = (resref or "").upper()
    if not key.startswith("PXL"):
        return None
    table = _power_pick_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            power = str(table.GetRowName(index)).upper()
            if str(table.GetValue(power, "ResRef")).upper() != key:
                continue
            base = _base_power_info(power)
            if not base:
                return None
            base.update({
                "kind": "power_choice",
                "resref": key,
                "parent": key,
                "power": power,
            })
            return base
    except Exception:
        return None
    return None


def power_learning_limits(actor):
    if not is_psion(actor):
        return (0, 0)
    table = _known_power_table()
    if not table:
        return (0, 0)
    try:
        level = manifester_level(actor)
        return (
            int(table.GetValue(str(level), "KNOWN")),
            int(table.GetValue(str(level), "MAX_LEVEL")),
        )
    except Exception:
        return (0, 0)


def known_power_refs(actor):
    known = set()
    try:
        count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            key = str(spell.get("SpellResRef", "")).upper()
            if _base_power_info(key):
                known.add(key)
    except Exception as error:
        GemRB.Log(2, "Psionics", "known-power scan failed: %s" % error)
    return known


def power_choices_remaining(actor):
    limit, _ = power_learning_limits(actor)
    return max(0, limit - len(known_power_refs(actor)))


def can_learn_power(actor, resref):
    info = power_choice_info(resref)
    if not info or not is_psion(actor) or power_choices_remaining(actor) <= 0:
        return False
    if info["power"] in known_power_refs(actor):
        return False
    _, maximum_level = power_learning_limits(actor)
    if info["level"] > maximum_level:
        return False
    return info["discipline"] in ("GENERAL", discipline(actor))


def available_power_choices(actor):
    table = _power_pick_table()
    if not table or power_choices_remaining(actor) <= 0:
        return []
    available = []
    try:
        for index in range(table.GetRowCount()):
            power = table.GetRowName(index)
            resref = str(table.GetValue(power, "ResRef")).upper()
            if can_learn_power(actor, resref):
                available.append(resref)
    except Exception:
        return []
    return available


def _ensure_power_selector_known(actor):
    """Grant PXPLRN to migrated Psions that still have legal choices."""
    if not is_psion(actor) or not available_power_choices(actor):
        return False
    try:
        count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            if str(spell.get("SpellResRef", "")).upper() == POWER_SELECTOR_RESOURCE:
                return True
        result = GemRB.LearnSpell(actor, POWER_SELECTOR_RESOURCE, LS_MEMO)
        return result in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Psionics", "power selector migration failed: %s" % error)
        return False


def _learn_power(actor, resref):
    info = power_choice_info(resref)
    if not info or not can_learn_power(actor, resref):
        return False
    try:
        return GemRB.LearnSpell(actor, info["power"], LS_MEMO) in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Psionics", "power learning failed: %s" % error)
        return False


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
            if str(effect.get("Resource1", "")).upper() != state_resource.upper():
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
            actor, STATE_EFFECT_OPCODE, rank, marker, state_resource,
            "", "", FEAT_EFFECT_SOURCE,
        )
    return rank


def _read_private_value(actor, marker, resource):
    return PersistentState.read(actor, STATE_EFFECT_OPCODE, marker, resource)


def _write_private_value(actor, marker, resource, value, source=SKILL_EFFECT_SOURCE):
    return PersistentState.write(
        actor, STATE_EFFECT_OPCODE, marker, resource, value, source,
    )


def skill_rank(actor, skill):
    key = (skill or "").upper()
    marker = SKILL_MARKERS.get(key)
    resource = SKILL_STATE_RESOURCES.get(key)
    if marker is None or resource is None:
        return 0
    found, rank = _read_private_value(actor, marker, resource)
    return rank if found else 0


def _write_skill_rank(actor, skill, rank):
    key = skill.upper()
    return _write_private_value(
        actor, SKILL_MARKERS[key], SKILL_STATE_RESOURCES[key], rank,
    )


def _ability_modifier(actor, ability):
    stat = SKILL_ABILITY_STATS.get((ability or "").upper())
    if stat is None:
        return 0
    return (int(GemRB.GetPlayerStat(actor, stat)) - 10) // 2


def _base_ability_modifier(actor, ability):
    stat = SKILL_ABILITY_STATS.get((ability or "").upper())
    if stat is None:
        return 0
    return (int(GemRB.GetPlayerStat(actor, stat, 1)) - 10) // 2


def skill_rank_cap(actor):
    return manifester_level(actor) + 3 if is_psion(actor) else 0


def _skill_points_per_level(actor):
    return max(1, 2 + _base_ability_modifier(actor, "INT"))


def _spent_skill_points(actor):
    total = 0
    for skill in SKILL_MARKERS:
        info = skill_rule_info(skill)
        if info:
            total += skill_rank(actor, skill) * max(1, info["cost"])
    return total


def sync_skill_points(actor):
    """Initialize/mature the persistent Psion skill-point ledger.

    Progression uses base Intelligence, so temporary buffs/debuffs cannot
    permanently alter newly credited levels. A migrated character with no
    ledger receives the normal level-1 x4 allotment plus one ordinary allotment
    for every existing later Psion level, minus any already serialized ranks.
    Once a level is accounted, later base-Intelligence changes affect only new
    levels and never rewrite already credited levels.
    """
    if not is_psion(actor):
        return 0
    level = manifester_level(actor)
    per_level = _skill_points_per_level(actor)
    have_level, accounted = _read_private_value(
        actor, SKILL_LEVEL_MARKER, SKILL_LEVEL_RESOURCE,
    )
    have_points, points = _read_private_value(
        actor, SKILL_POINTS_MARKER, SKILL_POINTS_RESOURCE,
    )

    if not have_level:
        if not have_points:
            earned = per_level * (level + 3)
            points = max(0, earned - _spent_skill_points(actor))
        _write_private_value(
            actor, SKILL_LEVEL_MARKER, SKILL_LEVEL_RESOURCE, level,
        )
        _write_private_value(
            actor, SKILL_POINTS_MARKER, SKILL_POINTS_RESOURCE, points,
        )
        return points

    if not have_points:
        earned = per_level * (max(1, accounted) + 3)
        points = max(0, earned - _spent_skill_points(actor))

    if level > accounted:
        points += per_level * (level - accounted)
        accounted = level
        _write_private_value(
            actor, SKILL_LEVEL_MARKER, SKILL_LEVEL_RESOURCE, accounted,
        )

    _write_private_value(
        actor, SKILL_POINTS_MARKER, SKILL_POINTS_RESOURCE, points,
    )
    return points


def skill_points_remaining(actor):
    return sync_skill_points(actor)


def _skill_access_allowed(actor, info):
    if not info or not is_psion(actor):
        return False
    return info["access"] in ("CORE", discipline(actor))


def can_train_skill(actor, resref):
    info = skill_choice_info(resref)
    if not _skill_access_allowed(actor, info):
        return False
    if skill_rank(actor, info["skill"]) >= skill_rank_cap(actor):
        return False
    return skill_points_remaining(actor) >= max(1, info["cost"])


def available_skill_choices(actor):
    table = _skill_pick_table()
    if not table or skill_points_remaining(actor) <= 0:
        return []
    available = []
    try:
        for index in range(table.GetRowCount()):
            skill = table.GetRowName(index)
            resref = str(table.GetValue(skill, "ResRef")).upper()
            if can_train_skill(actor, resref):
                available.append(resref)
    except Exception:
        return []
    return available


def _ensure_skill_selector_known(actor):
    """Grant PXSKILL to pre-v1.2 Psions once legal training exists."""
    if not is_psion(actor) or not available_skill_choices(actor):
        return False
    try:
        known_count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(known_count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            if str(spell.get("SpellResRef", "")).upper() == SKILL_SELECTOR_RESOURCE:
                return True
        result = GemRB.LearnSpell(actor, SKILL_SELECTOR_RESOURCE, LS_MEMO)
        return result in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Psionics", "skill selector migration failed: %s" % error)
        return False


def _train_skill(actor, resref):
    info = skill_choice_info(resref)
    if not info or not can_train_skill(actor, resref):
        return False
    points = skill_points_remaining(actor)
    cost = max(1, info["cost"])
    _write_skill_rank(actor, info["skill"], skill_rank(actor, info["skill"]) + 1)
    _write_private_value(
        actor, SKILL_POINTS_MARKER, SKILL_POINTS_RESOURCE, points - cost,
    )
    return True


def skill_check_total(actor, skill, roll=None):
    info = skill_rule_info(skill)
    if not info or not _skill_access_allowed(actor, info):
        return None
    if roll is None:
        roll = int(GemRB.Roll(1, 20, 0))
    return int(roll) + skill_rank(actor, info["skill"]) + _ability_modifier(actor, info["ability"])


def concentration_check(actor, dc=20, roll=None):
    total = skill_check_total(actor, CONCENTRATION_SKILL, roll)
    return total is not None and total >= int(dc)


def psionic_feat_count(actor):
    return sum(feat_rank(actor, resref) for resref in FEAT_MARKERS)


def bonus_feat_spent(actor):
    found, spent = _read_private_value(
        actor, BONUS_FEAT_SPENT_MARKER, BONUS_FEAT_SPENT_RESOURCE,
    )
    return spent if found else 0


def _write_bonus_feat_spent(actor, spent):
    return _write_private_value(
        actor, BONUS_FEAT_SPENT_MARKER, BONUS_FEAT_SPENT_RESOURCE,
        spent, BONUS_FEAT_SPENT_SOURCE,
    )


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
    if info["skill"] and skill_rank(actor, info["skill"]) < info["rank"]:
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
    found, current = _read_private_value(
        actor, POOL_EFFECT_MARKER, POOL_EFFECT_RESOURCE,
    )
    return found, min(current, POOL_VALUE_MASK)


def _write_pool_state(actor, current):
    current = max(0, min(int(current), POOL_VALUE_MASK))
    _write_private_value(
        actor, POOL_EFFECT_MARKER, POOL_EFFECT_RESOURCE,
        current, POOL_EFFECT_SOURCE,
    )
    cached = _write_pool_cache(actor, current)
    # SRD focus requires a nonempty PP reserve. Spending the last point therefore
    # clears focus immediately; raising the reserve later does not auto-refocus.
    if current == 0 and is_psion(actor):
        _write_focus_state(actor, False)
    return cached


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
    found = False
    focused = False
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != FOCUS_EFFECT_MARKER:
                continue
            if str(effect.get("Resource1", "")).upper() != FOCUS_EFFECT_RESOURCE:
                continue
            found = True
            focused = focused or bool(int(effect.get("Param1", 0)))
    except Exception as error:
        GemRB.Log(2, "Psionics", "focus state read failed: %s" % error)
    return found, focused


def _sync_speed_gate(actor, owns_speed=None):
    if not is_psion(actor):
        return
    if owns_speed is None:
        owns_speed = feat_rank(actor, SPEED_OF_THOUGHT) > 0
    try:
        GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, SPEED_BLOCK_MARKER)
        if not owns_speed:
            GemRB.ApplyEffect(
                actor, STATE_EFFECT_OPCODE, 0, SPEED_BLOCK_MARKER,
                SPEED_ON_RESOURCE, "", "", SPEED_BLOCK_SOURCE,
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
    if ensure_pool(actor) <= 0:
        persisted, focused = _read_focus_state(actor)
        if not persisted or focused:
            return _write_focus_state(actor, False)
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


def _center_resource_for_actor(actor):
    if feat_rank(actor, PSIONIC_MEDITATION):
        return MEDITATION_CENTER_RESOURCE
    return CENTER_RESOURCE


def _sync_center_action(actor):
    """Replace ordinary Center Mind with the Meditation version when owned."""
    if not is_psion(actor):
        return False
    wanted = _center_resource_for_actor(actor)
    unwanted = (
        CENTER_RESOURCE if wanted == MEDITATION_CENTER_RESOURCE
        else MEDITATION_CENTER_RESOURCE
    )
    try:
        GemRB.RemoveSpell(actor, unwanted)
        result = GemRB.LearnSpell(actor, wanted, LS_MEMO)
        return result in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Psionics", "Center Mind spellbook sync failed: %s" % error)
        return False


def _apply_body_hp(actor, amount):
    amount = max(0, int(amount))
    if not amount:
        return
    GemRB.ApplyEffect(actor, "MaximumHPModifier", amount, 3, "", "", "", "PXFBODY", 9)
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
    if info["resref"] == PSIONIC_MEDITATION:
        _sync_center_action(actor)
    _sync_focus_passives(actor)
    return True


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            ensure_pool(actor, True)
            ensure_focus(actor, True)
            _ensure_power_selector_known(actor)
            sync_skill_points(actor)
            _ensure_skill_selector_known(actor)
            _sync_center_action(actor)
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


def _dc_modifier(actor):
    intelligence = max(0, min(25, int(GemRB.GetPlayerStat(actor, INT_STAT))))
    return (intelligence - 10) // 2


def _dc_variant_resref(resref, modifier):
    key = (resref or "").upper()
    if modifier == DC_BASELINE_MODIFIER:
        return key
    suffix = DC_MODIFIER_SUFFIXES.get(int(modifier))
    if not suffix or len(key) >= 8:
        return key
    return key + suffix


def _dc_canonical_resref(resref):
    key = (resref or "").upper()
    if len(key) < 2 or key[-1] not in DC_SUFFIX_MODIFIERS:
        return key
    candidate = key[:-1]
    if augment_info(candidate) or _base_power_info(candidate):
        return candidate
    return key


def _dc_resource_exists(resref):
    try:
        return bool(GemRB.GetSpell(resref, 1))
    except Exception:
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
    if base:
        if _has_variants(key):
            base["selector"] = True
            base["cost"] = 0
        return base

    canonical = _dc_canonical_resref(key)
    if canonical == key:
        return None
    info = power_info(canonical)
    if not info:
        return None
    info = dict(info)
    info["internal_resref"] = key
    info["dc_variant"] = True
    return info

def action_info(resref):
    key = (resref or "").upper()
    if key in CENTER_RESOURCES:
        return {"kind": "center", "resref": key, "parent": key, "cost": 0, "selector": False}
    if key == FEAT_SELECTOR_RESOURCE:
        return {"kind": "feat_selector", "resref": key, "parent": key, "cost": 0, "selector": True}
    if key == POWER_SELECTOR_RESOURCE:
        return {"kind": "power_selector", "resref": key, "parent": key, "cost": 0, "selector": True}
    if key == SKILL_SELECTOR_RESOURCE:
        return {"kind": "skill_selector", "resref": key, "parent": key, "cost": 0, "selector": True}
    power_choice = power_choice_info(key)
    if power_choice:
        return power_choice
    feat = feat_choice_info(key)
    if feat:
        return feat
    skill = skill_choice_info(key)
    if skill:
        return skill
    return power_info(key)


def resolve_power_entry(spellbook, actor, raw_spell):
    encoded_type = raw_spell // 1000
    spell_index = raw_spell % 1000
    if encoded_type == TEMPORARY_SPELLINFO_TYPE:
        return Selectors.resolve_temporary(
            actor, raw_spell, lambda resref: bool(action_info(resref)),
            TEMPORARY_SPELLINFO_TYPE,
        )
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


def _memorized_parent_entry(spellbook, actor, parent):
    key = (parent or "").upper()
    try:
        for candidate in spellbook.GetUsableMemorizedSpells(actor, INNATE_TYPE):
            if str(candidate.get("SpellResRef", "")).upper() == key:
                return candidate
    except Exception:
        return None
    return None


def prepare_action_entry(spellbook, actor, entry):
    """Substitute an exact-INT save-DC resource before ActionsWindow casts.

    Normal powers replace themselves. Temporary augmentation choices (type 255)
    replace their memorized parent power, converting the selector result to an
    ordinary innate SpellCast while preserving the selected child for PP cost.
    """
    selected = str(entry.get("SpellResRef", "")).upper()
    canonical = _dc_canonical_resref(selected)
    if canonical != selected:
        return entry
    info = power_info(canonical)
    if not info or info.get("selector", False):
        return entry

    replacement = _dc_variant_resref(canonical, _dc_modifier(actor))
    if replacement == canonical or not _dc_resource_exists(replacement):
        return entry

    source = entry
    if int(entry.get("SpellIndex", 0)) // 1000 == TEMPORARY_SPELLINFO_TYPE:
        source = _memorized_parent_entry(spellbook, actor, info.get("parent"))
        if not source:
            return False

    try:
        source_ref = str(source.get("SpellResRef", "")).upper()
        book_type = int(source["BookType"])
        spell_level = int(source["SpellLevel"])
        spell_index = GemRB.PrepareSpontaneousCast(
            actor, source_ref, book_type, spell_level, replacement
        )
        GemRB.SetVar("Spell", int(spell_index) + 1000 * (1 << book_type))
        return entry
    except Exception as error:
        GemRB.Log(2, "Psionics", "exact save-DC cast preparation failed: %s" % error)
        return False


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
        power_choice = power_choice_info(resref)
        if power_choice:
            if can_learn_power(actor, resref):
                filtered.append(resref)
            continue
        feat = feat_choice_info(resref)
        if feat:
            if can_select_feat(actor, resref):
                filtered.append(resref)
            continue
        skill = skill_choice_info(resref)
        if skill:
            if can_train_skill(actor, resref):
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
    if power_info(key):
        return True
    if key in CENTER_RESOURCES:
        return key == _center_resource_for_actor(actor)
    if key == FEAT_SELECTOR_RESOURCE:
        return bonus_feats_remaining(actor) > 0
    if key == POWER_SELECTOR_RESOURCE:
        return bool(available_power_choices(actor))
    if key == SKILL_SELECTOR_RESOURCE:
        return bool(available_skill_choices(actor))
    return False


def refresh_innate_charges(actor):
    if not is_psion(actor):
        return 0
    _sync_focus_passives(actor)
    _ensure_power_selector_known(actor)
    sync_skill_points(actor)
    _ensure_skill_selector_known(actor)
    _sync_center_action(actor)
    try:
        return InnateCharges.refresh(
            actor,
            lambda resref: _is_reusable_innate(actor, resref),
            INNATE_TYPE,
            INNATE_LEVEL,
        )
    except Exception as error:
        GemRB.Log(2, "Psionics", "charge refresh failed: %s" % error)
        return 0


def _begin_simple_action(actor, transaction, legal, commit):
    return Transactions.begin(
        TRANSACTION_NAMESPACE, actor, transaction, legal, commit,
    )


def begin_manifest(actor, resref):
    info = action_info(resref)
    if not info:
        return True

    if info["kind"] == "center":
        _sync_speed_gate(actor)
        key = info["resref"]
        return _begin_simple_action(
            actor,
            ("CENTER", key),
            lambda: (
                key == _center_resource_for_actor(actor)
                and ensure_pool(actor) > 0
                and not is_focused(actor)
            ),
            lambda: concentration_check(actor, 20),
        )

    if info["kind"] == "power_selector":
        cancel_pending(actor)
        return bool(available_power_choices(actor))

    if info["kind"] == "power_choice":
        key = info["resref"]
        return _begin_simple_action(
            actor,
            ("POWER_LEARN", key),
            lambda: can_learn_power(actor, key),
            lambda: _learn_power(actor, key),
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

    if info["kind"] == "skill_selector":
        cancel_pending(actor)
        return bool(available_skill_choices(actor))

    if info["kind"] == "skill_choice":
        key = info["resref"]
        return _begin_simple_action(
            actor,
            ("SKILL", key),
            lambda: can_train_skill(actor, key),
            lambda: _train_skill(actor, key),
        )

    if info["selector"]:
        cancel_pending(actor)
        return can_manifest(actor, info["resref"])

    transaction = (info["resref"], info["cost"])

    def legal():
        allowed = can_manifest(actor, info["resref"])
        if not allowed:
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return allowed

    def commit():
        current = ensure_pool(actor)
        _write_pool_state(actor, current - info["cost"])
        return True

    return Transactions.begin(
        TRANSACTION_NAMESPACE, actor, transaction, legal, commit,
    )


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)


def pool_text(actor):
    return "%d/%d" % (ensure_pool(actor), maximum_pool(actor))


def focus_text(actor):
    return "Focused" if is_focused(actor) else "Unfocused"


def skill_points_text(actor):
    return "%d skill points" % skill_points_remaining(actor)
