# SPDX-License-Identifier: GPL-2.0-or-later
"""GemRB runtime support for the Pillars-inspired Cipher class."""
import GemRB
import Transactions
import InnateCharges
import PersistentState
import Selectors
from ie_spells import LS_MEMO

FOCUS_STAT = 165
FOCUS_UNIT = 5
STARTING_FOCUS = 20
LEVEL_STAT = 34
INNATE_TYPE = 2
INNATE_LEVEL = 0
CIPHER_CLASS = "CIPHER"
POWER_SELECTOR_RESOURCE = "CILRN"
SUBCLASS_SELECTOR_RESOURCE = "CISUB"
SUBCLASS_STAT = 166
SUBCLASS_STATE_OPCODE = "Protection:Spell"
SUBCLASS_STATE_MARKER = 0x43495355
SUBCLASS_STATE_RESOURCE = "CISUBCLS"
SUBCLASS_STATE_SOURCE = "CISUBMOD"
BASE_SUBCLASS = "BASE"
SOUL_BLADE_SUBCLASS = "SOUL_BLADE"
REAPING_KNIVES_RESOURCE = "CI8RKNI"
REAPING_OWNER_FIRST = 7
REAPING_OWNER_LAST = 255
REAPING_OWNER_COUNTER = "CIRKNEXT"
REAPING_OWNER_MARKER = 0x43495249
REAPING_OWNER_RESOURCE = "CIRKID"
REAPING_OWNER_OPCODE = "Protection:Spell"
TEMPORARY_SPELLINFO_TYPE = 255
TRANSACTION_NAMESPACE = "Cipher"


def _class_row(actor):
    try:
        import GUICommon
        return GUICommon.GetClassRowName(actor)
    except Exception:
        return ""


def is_cipher(actor):
    return _class_row(actor) == CIPHER_CLASS


def cipher_level(actor):
    if not is_cipher(actor):
        return 0
    return max(1, min(30, int(GemRB.GetPlayerStat(actor, LEVEL_STAT))))


def maximum_focus(actor):
    level = cipher_level(actor)
    base = 0 if not level else 20 + 5 * level
    return subclass_focus_cap(actor, base)


def _focus_units(actor):
    return max(0, int(GemRB.GetPlayerStat(actor, FOCUS_STAT)))


def set_focus(actor, amount):
    if not is_cipher(actor):
        return 0
    cap = maximum_focus(actor)
    amount = max(0, min(int(amount), cap))
    amount -= amount % FOCUS_UNIT
    units = amount // FOCUS_UNIT
    GemRB.ApplySpell(actor, "CIFS%d" % units, actor)
    return amount


def current_focus(actor):
    if not is_cipher(actor):
        return 0
    current = _focus_units(actor) * FOCUS_UNIT
    cap = maximum_focus(actor)
    if current > cap:
        return set_focus(actor, cap)
    return current


def _subclass_table():
    try:
        return GemRB.LoadTable("cisub", False, True)
    except Exception:
        return None


def _subclass_info_by_id(value):
    table = _subclass_table()
    if not table:
        return {
            "key": BASE_SUBCLASS,
            "id": 0,
            "resref": "",
            "focus_cap_mod": 0,
            "power_cost_mod": 0,
            "weapon_focus_units": 1,
            "enabled": True,
        } if int(value) == 0 else None
    try:
        for index in range(table.GetRowCount()):
            key = str(table.GetRowName(index)).upper()
            if int(table.GetValue(key, "ID")) != int(value):
                continue
            resref = str(table.GetValue(key, "RESREF")).upper()
            if resref == "****":
                resref = ""
            return {
                "key": key,
                "id": int(value),
                "resref": resref,
                "focus_cap_mod": int(table.GetValue(key, "FOCUS_CAP_MOD")),
                "power_cost_mod": int(table.GetValue(key, "POWER_COST_MOD")),
                "weapon_focus_units": max(1, int(table.GetValue(key, "WEAPON_FOCUS_UNITS"))),
                "enabled": bool(int(table.GetValue(key, "ENABLED"))),
            }
    except Exception:
        return None
    return None


def subclass_id(actor):
    if not is_cipher(actor):
        return 0
    try:
        found, value = PersistentState.read(
            actor, SUBCLASS_STATE_OPCODE, SUBCLASS_STATE_MARKER, SUBCLASS_STATE_RESOURCE,
        )
    except Exception as error:
        GemRB.Log(2, "Cipher", "subclass state read failed: %s" % error)
        return 0
    return max(0, int(value)) if found else 0


def subclass_info(actor):
    return _subclass_info_by_id(subclass_id(actor)) or _subclass_info_by_id(0)


def has_subclass(actor):
    return subclass_id(actor) != 0


def is_subclass(actor, key):
    info = subclass_info(actor)
    return bool(info and info["key"] == str(key or "").upper())


def _sync_subclass_mirror(actor):
    if not is_cipher(actor):
        return
    GemRB.SetPlayerStat(actor, SUBCLASS_STAT, subclass_id(actor))


def _write_subclass(actor, value):
    info = _subclass_info_by_id(value)
    if not is_cipher(actor) or not info or not info["enabled"]:
        return False
    PersistentState.write(
        actor, SUBCLASS_STATE_OPCODE, SUBCLASS_STATE_MARKER, SUBCLASS_STATE_RESOURCE,
        info["id"], SUBCLASS_STATE_SOURCE,
    )
    _sync_subclass_mirror(actor)
    return subclass_id(actor) == info["id"]


def subclass_choice_info(resref):
    key = str(resref or "").upper()
    table = _subclass_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            row = str(table.GetRowName(index)).upper()
            value = int(table.GetValue(row, "ID"))
            if value == 0:
                continue
            candidate = str(table.GetValue(row, "RESREF")).upper()
            if candidate != key:
                continue
            info = _subclass_info_by_id(value)
            if not info:
                return None
            return {
                "kind": "subclass_choice",
                "resref": key,
                "parent": key,
                "subclass": row,
                "subclass_id": value,
                "cost": 0,
                "selector": False,
            }
    except Exception:
        return None
    return None


def available_subclass_choices(actor):
    if not is_cipher(actor) or has_subclass(actor):
        return []
    table = _subclass_table()
    if not table:
        return []
    result = []
    try:
        for index in range(table.GetRowCount()):
            row = str(table.GetRowName(index)).upper()
            value = int(table.GetValue(row, "ID"))
            if value == 0 or not int(table.GetValue(row, "ENABLED")):
                continue
            resref = str(table.GetValue(row, "RESREF")).upper()
            if resref and resref != "****":
                result.append(resref)
    except Exception:
        return []
    return result


def _choose_subclass(actor, resref):
    info = subclass_choice_info(resref)
    if not info or has_subclass(actor) or resref not in available_subclass_choices(actor):
        return False
    return _write_subclass(actor, info["subclass_id"])


def subclass_focus_cap(actor, base_cap):
    info = subclass_info(actor)
    return max(0, int(base_cap) + (int(info["focus_cap_mod"]) if info else 0))


def effective_power_cost(actor, info):
    base = max(0, int(info.get("cost", 0)))
    subclass = subclass_info(actor)
    return max(0, base + (int(subclass["power_cost_mod"]) if subclass else 0))


def focus_gain_units(actor, source_kind="weapon"):
    subclass = subclass_info(actor)
    if source_kind == "weapon" and subclass:
        return max(1, int(subclass["weapon_focus_units"]))
    return 1


def _power_pick_table():
    try:
        return GemRB.LoadTable("cipick", False, True)
    except Exception:
        return None


def _known_power_table():
    try:
        return GemRB.LoadTable("ciknown", False, True)
    except Exception:
        return None


def power_info(resref):
    key = str(resref or "").upper()
    if not key.startswith("CI"):
        return None
    try:
        table = GemRB.LoadTable("cipowers", False, True)
        return {
            "kind": "power",
            "resref": key,
            "parent": key,
            "tier": int(table.GetValue(key, "TIER")),
            "unlock": int(table.GetValue(key, "UNLOCK")),
            "cost": int(table.GetValue(key, "COST")),
            "selector": False,
        }
    except Exception:
        return None


def power_choice_info(resref):
    key = str(resref or "").upper()
    if not key.startswith("CIL") or key == POWER_SELECTOR_RESOURCE:
        return None
    table = _power_pick_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            power = str(table.GetRowName(index)).upper()
            if str(table.GetValue(power, "ResRef")).upper() != key:
                continue
            base = power_info(power)
            if not base:
                return None
            base.update({
                "kind": "power_choice",
                "resref": key,
                "parent": key,
                "power": power,
                "cost": 0,
            })
            return base
    except Exception:
        return None
    return None


def power_learning_limits(actor):
    if not is_cipher(actor):
        return (0, 0)
    table = _known_power_table()
    if not table:
        return (0, 0)
    try:
        level = cipher_level(actor)
        return (
            int(table.GetValue(str(level), "KNOWN")),
            int(table.GetValue(str(level), "MAX_TIER")),
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
            if power_info(key):
                known.add(key)
    except Exception as error:
        raise RuntimeError("Cipher known-power scan failed for actor %s" % actor) from error
    return known


def power_choices_remaining(actor):
    limit, _ = power_learning_limits(actor)
    return max(0, limit - len(known_power_refs(actor)))


def can_learn_power(actor, resref):
    info = power_choice_info(resref)
    if not info or not is_cipher(actor) or power_choices_remaining(actor) <= 0:
        return False
    if info["power"] in known_power_refs(actor):
        return False
    _, maximum_tier = power_learning_limits(actor)
    return info["tier"] <= maximum_tier


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
    """Grant CILRN to migrated Ciphers when an earned choice remains."""
    if not is_cipher(actor) or not available_power_choices(actor):
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
        GemRB.Log(2, "Cipher", "power selector migration failed: %s" % error)
        return False


def _learn_power(actor, resref):
    info = power_choice_info(resref)
    if not info or not can_learn_power(actor, resref):
        return False
    try:
        return GemRB.LearnSpell(actor, info["power"], LS_MEMO) in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Cipher", "power learning failed: %s" % error)
        return False


def restore_party():
    cancel_pending()
    for actor in range(1, GemRB.GetPartySize() + 1):
        try:
            if is_cipher(actor):
                _sync_subclass_mirror(actor)
                set_focus(actor, STARTING_FOCUS)
                _ensure_power_selector_known(actor)
        except Exception:
            pass


def can_manifest(actor, resref):
    info = power_info(resref)
    return bool(
        info
        and is_cipher(actor)
        and cipher_level(actor) >= info["unlock"]
        and current_focus(actor) >= effective_power_cost(actor, info)
    )


def action_info(resref):
    key = str(resref or "").upper()
    owner_suffix = key[5:] if key.startswith("CI8RK") else ""
    if owner_suffix.isdecimal() and owner_suffix == str(int(owner_suffix)) and 1 <= int(owner_suffix) <= REAPING_OWNER_LAST:
        info = power_info(REAPING_KNIVES_RESOURCE)
        if info:
            info["internal_resref"] = key
        return info
    if key == SUBCLASS_SELECTOR_RESOURCE:
        return {
            "kind": "subclass_selector",
            "resref": key,
            "parent": key,
            "cost": 0,
            "selector": True,
        }
    subclass_choice = subclass_choice_info(key)
    if subclass_choice:
        return subclass_choice
    if key == POWER_SELECTOR_RESOURCE:
        return {
            "kind": "power_selector",
            "resref": key,
            "parent": key,
            "cost": 0,
            "selector": True,
        }
    choice = power_choice_info(key)
    if choice:
        return choice
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
            if action_info(candidate.get("SpellResRef", "")):
                return candidate
    return None


def _read_reaping_owner(actor):
    identities = [
        int(effect.get("Param1", 0))
        for effect in GemRB.GetEffects(actor, REAPING_OWNER_OPCODE)
        if int(effect.get("Param2", -1)) == REAPING_OWNER_MARKER
        and str(effect.get("Resource1", "")).upper() == REAPING_OWNER_RESOURCE
    ]
    if len(identities) > 1:
        raise RuntimeError("duplicate Reaping Knives owner identity")
    return identities[0] if identities else None


def _reaping_owner_token(actor):
    last = int(GemRB.GetGameVar(REAPING_OWNER_COUNTER))
    if not 0 <= last <= REAPING_OWNER_LAST:
        raise RuntimeError("invalid Reaping Knives owner registry")
    token = _read_reaping_owner(actor)
    if token is not None:
        if not REAPING_OWNER_FIRST <= token <= last:
            raise RuntimeError("Reaping Knives owner identity does not match this save")
        return token
    token = max(last + 1, REAPING_OWNER_FIRST)
    if token > REAPING_OWNER_LAST:
        raise RuntimeError("Reaping Knives owner registry is full; refusing to reuse an identity")
    GemRB.SetGlobal(REAPING_OWNER_COUNTER, "GLOBAL", token)
    if int(GemRB.GetGameVar(REAPING_OWNER_COUNTER)) != token:
        raise RuntimeError("Reaping Knives owner registry was not saved")
    GemRB.ApplyEffect(
        actor, REAPING_OWNER_OPCODE, token, REAPING_OWNER_MARKER,
        REAPING_OWNER_RESOURCE, "", "", "CIRKMOD", 9,
    )
    if _read_reaping_owner(actor) != token:
        raise RuntimeError("Reaping Knives owner identity was not saved")
    return token


def prepare_action_entry(spellbook, actor, entry):
    selected = str(entry.get("SpellResRef", "")).upper()
    if selected != REAPING_KNIVES_RESOURCE:
        return entry
    if actor < 1 or actor > 6:
        GemRB.Log(2, "Cipher", "Reaping Knives owner is outside party slots: %s" % actor)
        return False
    try:
        # Persist the save-owned identity, not a mutable party slot. Internal
        # resources are not learned: the shared explicit-resource path avoids
        # depleting the parent while merely choosing a target.
        entry["CastResRef"] = "CI8RK%d" % _reaping_owner_token(actor)
        return entry
    except Exception as error:
        GemRB.Log(2, "Cipher", "Reaping Knives cast preparation failed: %s" % error)
        return False


def filter_spellinfo(actor, resrefs):
    filtered = []
    for resref in resrefs:
        subclass_choice = subclass_choice_info(resref)
        if subclass_choice:
            if resref in available_subclass_choices(actor):
                filtered.append(resref)
            continue
        choice = power_choice_info(resref)
        if choice:
            if can_learn_power(actor, resref):
                filtered.append(resref)
            continue
        filtered.append(resref)
    return filtered


def _is_reusable_innate(actor, resref):
    key = str(resref or "").upper()
    if power_info(key):
        return True
    if key == SUBCLASS_SELECTOR_RESOURCE:
        return bool(available_subclass_choices(actor))
    if key == POWER_SELECTOR_RESOURCE:
        return bool(available_power_choices(actor))
    return False


def refresh_innate_charges(actor):
    if not is_cipher(actor):
        return 0
    _sync_subclass_mirror(actor)
    _ensure_power_selector_known(actor)
    try:
        return InnateCharges.refresh(
            actor,
            lambda resref: _is_reusable_innate(actor, resref),
            INNATE_TYPE,
            INNATE_LEVEL,
        )
    except Exception as error:
        GemRB.Log(2, "Cipher", "charge refresh failed: %s" % error)
        return 0


def begin_manifest(actor, resref):
    info = action_info(resref)
    if not info:
        return True

    if info["kind"] == "subclass_selector":
        cancel_pending(actor)
        return bool(available_subclass_choices(actor))

    if info["kind"] == "subclass_choice":
        key = info["resref"]
        return Transactions.begin(
            TRANSACTION_NAMESPACE,
            actor,
            ("SUBCLASS", key),
            lambda: key in available_subclass_choices(actor),
            lambda: _choose_subclass(actor, key),
        )

    if info["kind"] == "power_selector":
        cancel_pending(actor)
        return bool(available_power_choices(actor))

    if info["kind"] == "power_choice":
        key = info["resref"]
        return Transactions.begin(
            TRANSACTION_NAMESPACE,
            actor,
            ("POWER_LEARN", key),
            lambda: can_learn_power(actor, key),
            lambda: _learn_power(actor, key),
        )

    cost = effective_power_cost(actor, info)
    transaction = (info["resref"], cost)

    def legal():
        allowed = can_manifest(actor, info["resref"])
        if not allowed:
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return allowed

    def commit():
        set_focus(actor, current_focus(actor) - effective_power_cost(actor, info))
        return True

    return Transactions.begin(TRANSACTION_NAMESPACE, actor, transaction, legal, commit)


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)


def focus_text(actor):
    return "%d/%d" % (current_focus(actor), maximum_focus(actor))
