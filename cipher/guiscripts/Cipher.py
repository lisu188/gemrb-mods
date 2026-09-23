# SPDX-License-Identifier: GPL-2.0-or-later
"""GemRB runtime support for the Pillars-inspired Cipher class."""
import GemRB
import Transactions
import InnateCharges
import Selectors
import PersistentState
from ie_spells import LS_MEMO

FOCUS_STAT = 165
FOCUS_UNIT = 5
STARTING_FOCUS = 20
LEVEL_STAT = 34
INNATE_TYPE = 2
INNATE_LEVEL = 0
CIPHER_CLASS = "CIPHER"
POWER_SELECTOR_RESOURCE = "CILRN"
SUBCLASS_SELECTOR_RESOURCE = "CISUBCL"
SUBCLASS_STATE_OPCODE = "Protection:Spell"
SUBCLASS_STATE_MARKER = 0x43495342
SUBCLASS_STATE_RESOURCE = "CISUBCLS"
SUBCLASS_STATE_SOURCE = "CISUBMOD"
SUBCLASS_MIRROR_STAT = 164
BASE_SUBCLASS_ID = 0
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


def _subclass_table():
    try:
        return GemRB.LoadTable("cisub", False, True)
    except Exception:
        return None


def _subclass_info_by_id(identifier):
    table = _subclass_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            key = str(table.GetRowName(index)).upper()
            value = int(table.GetValue(key, "ID"))
            if value != int(identifier):
                continue
            return {
                "key": key,
                "id": value,
                "choice": str(table.GetValue(key, "CHOICE")).upper(),
                "cap_mod": int(table.GetValue(key, "CAP_MOD")),
                "cost_delta": int(table.GetValue(key, "COST_DELTA")),
                "gain_units": int(table.GetValue(key, "GAIN_UNITS")),
                "passive": str(table.GetValue(key, "PASSIVE")).upper(),
                "weapon": str(table.GetValue(key, "WEAPON")).upper(),
                "enabled": int(table.GetValue(key, "ENABLED")) != 0,
            }
    except Exception as error:
        raise RuntimeError("Cipher subclass registry read failed") from error
    return None


def subclass_id(actor):
    if not is_cipher(actor):
        return BASE_SUBCLASS_ID
    found, value = PersistentState.read(
        actor, SUBCLASS_STATE_OPCODE, SUBCLASS_STATE_MARKER, SUBCLASS_STATE_RESOURCE,
    )
    if not found:
        return BASE_SUBCLASS_ID
    info = _subclass_info_by_id(value)
    if not info or not info["enabled"]:
        raise RuntimeError("Unsupported Cipher subclass ID %s" % value)
    return value


def subclass_info(actor):
    info = _subclass_info_by_id(subclass_id(actor))
    if info and info["enabled"]:
        return info
    raise RuntimeError("BASE Cipher subclass policy is unavailable")


def has_subclass(actor):
    return subclass_id(actor) != BASE_SUBCLASS_ID


def is_subclass(actor, key):
    return subclass_info(actor)["key"] == str(key or "").upper()


def focus_cap(actor, base_cap):
    return max(0, int(base_cap) + subclass_info(actor)["cap_mod"])


def power_cost(actor, info, base_cost=None):
    if not info:
        return 0
    cost = int(info["cost"] if base_cost is None else base_cost)
    return max(FOCUS_UNIT, cost + subclass_info(actor)["cost_delta"])


def can_gain_focus(actor, source_kind):
    return bool(is_cipher(actor) and str(source_kind or "").lower() == "weapon")


def focus_gain_units(actor, source_kind, base_units=1):
    if not can_gain_focus(actor, source_kind):
        return max(0, int(base_units))
    return max(0, min(8, int(subclass_info(actor)["gain_units"])))


def passive_resource(actor):
    value = subclass_info(actor)["passive"]
    return "" if value in ("", "*") else value


def weapon_policy(actor):
    return subclass_info(actor)["weapon"]


def maximum_focus(actor):
    level = cipher_level(actor)
    if not level:
        return 0
    return focus_cap(actor, 20 + 5 * level)


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


def subclass_choice_info(resref):
    key = str(resref or "").upper()
    if not key or key == SUBCLASS_SELECTOR_RESOURCE:
        return None
    table = _subclass_table()
    if not table:
        return None
    try:
        for index in range(table.GetRowCount()):
            row = str(table.GetRowName(index)).upper()
            identifier = int(table.GetValue(row, "ID"))
            choice = str(table.GetValue(row, "CHOICE")).upper()
            enabled = int(table.GetValue(row, "ENABLED")) != 0
            if identifier == BASE_SUBCLASS_ID or not enabled or choice != key:
                continue
            return {
                "kind": "subclass_choice",
                "resref": key,
                "parent": key,
                "subclass": row,
                "subclass_id": identifier,
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
    choices = []
    for index in range(table.GetRowCount()):
        row = str(table.GetRowName(index)).upper()
        identifier = int(table.GetValue(row, "ID"))
        choice = str(table.GetValue(row, "CHOICE")).upper()
        enabled = int(table.GetValue(row, "ENABLED")) != 0
        if identifier != BASE_SUBCLASS_ID and enabled and choice not in ("", "*"):
            choices.append(choice)
    return choices


def _sync_subclass_passive(actor):
    if not is_cipher(actor):
        return False
    GemRB.ApplySpell(actor, "CISB0", actor)
    resource = passive_resource(actor)
    if resource:
        GemRB.ApplySpell(actor, resource, actor)
    return True


def _remove_subclass_selector(actor):
    try:
        GemRB.RemoveSpell(actor, SUBCLASS_SELECTOR_RESOURCE)
    except Exception:
        pass


def _write_subclass(actor, identifier):
    info = _subclass_info_by_id(identifier)
    if not is_cipher(actor) or not info or not info["enabled"]:
        return False
    PersistentState.write(
        actor, SUBCLASS_STATE_OPCODE, SUBCLASS_STATE_MARKER,
        SUBCLASS_STATE_RESOURCE, identifier, SUBCLASS_STATE_SOURCE,
    )
    _sync_subclass_passive(actor)
    if int(identifier) != BASE_SUBCLASS_ID:
        _remove_subclass_selector(actor)
    return subclass_id(actor) == int(identifier)


def _select_subclass(actor, resref):
    info = subclass_choice_info(resref)
    if not info or has_subclass(actor):
        return False
    return _write_subclass(actor, info["subclass_id"])


def _ensure_subclass_selector_known(actor):
    if not is_cipher(actor) or not available_subclass_choices(actor):
        return False
    try:
        count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            if str(spell.get("SpellResRef", "")).upper() == SUBCLASS_SELECTOR_RESOURCE:
                return True
        result = GemRB.LearnSpell(actor, SUBCLASS_SELECTOR_RESOURCE, LS_MEMO)
        return result in (0, 1)
    except Exception as error:
        GemRB.Log(2, "Cipher", "subclass selector migration failed: %s" % error)
        return False


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
                set_focus(actor, STARTING_FOCUS)
                _ensure_power_selector_known(actor)
                _ensure_subclass_selector_known(actor)
                _sync_subclass_passive(actor)
        except Exception:
            pass


def can_manifest(actor, resref):
    info = power_info(resref)
    return bool(
        info
        and is_cipher(actor)
        and cipher_level(actor) >= info["unlock"]
        and current_focus(actor) >= power_cost(actor, info)
    )


def action_info(resref):
    key = str(resref or "").upper()
    owner_suffix = key[5:] if key.startswith("CI8RK") else ""
    if owner_suffix.isdecimal() and owner_suffix == str(int(owner_suffix)) and 1 <= int(owner_suffix) <= REAPING_OWNER_LAST:
        info = power_info(REAPING_KNIVES_RESOURCE)
        if info:
            info["internal_resref"] = key
        return info
    if key == POWER_SELECTOR_RESOURCE:
        return {
            "kind": "power_selector",
            "resref": key,
            "parent": key,
            "cost": 0,
            "selector": True,
        }
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
            if not has_subclass(actor):
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
    if key == POWER_SELECTOR_RESOURCE:
        return bool(available_power_choices(actor))
    if key == SUBCLASS_SELECTOR_RESOURCE:
        return bool(available_subclass_choices(actor))
    return False


def refresh_innate_charges(actor):
    if not is_cipher(actor):
        return 0
    _ensure_power_selector_known(actor)
    _ensure_subclass_selector_known(actor)
    _sync_subclass_passive(actor)
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

    if info["kind"] == "power_selector":
        cancel_pending(actor)
        return bool(available_power_choices(actor))

    if info["kind"] == "subclass_selector":
        cancel_pending(actor)
        return bool(available_subclass_choices(actor))

    if info["kind"] == "subclass_choice":
        key = info["resref"]
        return Transactions.begin(
            TRANSACTION_NAMESPACE,
            actor,
            ("SUBCLASS", key),
            lambda: bool(subclass_choice_info(key)) and not has_subclass(actor),
            lambda: _select_subclass(actor, key),
        )

    if info["kind"] == "power_choice":
        key = info["resref"]
        return Transactions.begin(
            TRANSACTION_NAMESPACE,
            actor,
            ("POWER_LEARN", key),
            lambda: can_learn_power(actor, key),
            lambda: _learn_power(actor, key),
        )

    effective_cost = power_cost(actor, info)
    transaction = (info["resref"], effective_cost)

    def legal():
        allowed = can_manifest(actor, info["resref"])
        if not allowed:
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return allowed

    def commit():
        set_focus(actor, current_focus(actor) - effective_cost)
        return True

    return Transactions.begin(TRANSACTION_NAMESPACE, actor, transaction, legal, commit)


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)


def focus_text(actor):
    return "%d/%d" % (current_focus(actor), maximum_focus(actor))
