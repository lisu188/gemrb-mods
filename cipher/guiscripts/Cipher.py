# SPDX-License-Identifier: GPL-2.0-or-later
"""GemRB runtime support for the Pillars-inspired Cipher class."""
import GemRB
import Transactions
import InnateCharges
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
REAPING_KNIVES_RESOURCE = "CI8RKNI"
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
    return 0 if not level else 20 + 5 * level


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
        return GemRB.LoadTable("cipherknown", False, True)
    except Exception:
        return None


def power_info(resref):
    key = str(resref or "").upper()
    if not key.startswith("CI"):
        return None
    try:
        table = GemRB.LoadTable("cipherpowers", False, True)
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
        GemRB.Log(2, "Cipher", "known-power scan failed: %s" % error)
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
    for actor in range(1, 7):
        try:
            if is_cipher(actor):
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
        and current_focus(actor) >= info["cost"]
    )


def action_info(resref):
    key = str(resref or "").upper()
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


def prepare_action_entry(spellbook, actor, entry):
    selected = str(entry.get("SpellResRef", "")).upper()
    if selected != REAPING_KNIVES_RESOURCE:
        return entry
    if actor < 1 or actor > 6:
        GemRB.Log(2, "Cipher", "Reaping Knives owner is outside party slots: %s" % actor)
        return False
    replacement = "CI8RK%d" % actor
    try:
        source_ref = str(entry.get("SpellResRef", "")).upper()
        book_type = int(entry["BookType"])
        spell_level = int(entry["SpellLevel"])
        spell_index = GemRB.PrepareSpontaneousCast(
            actor, source_ref, book_type, spell_level, replacement
        )
        GemRB.SetVar("Spell", int(spell_index) + 1000 * (1 << book_type))
        return entry
    except Exception as error:
        GemRB.Log(2, "Cipher", "Reaping Knives cast preparation failed: %s" % error)
        return False


def filter_spellinfo(actor, resrefs):
    filtered = []
    for resref in resrefs:
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
    return False


def refresh_innate_charges(actor):
    if not is_cipher(actor):
        return 0
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

    transaction = (info["resref"], info["cost"])

    def legal():
        allowed = can_manifest(actor, info["resref"])
        if not allowed:
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return allowed

    def commit():
        set_focus(actor, current_focus(actor) - info["cost"])
        return True

    return Transactions.begin(TRANSACTION_NAMESPACE, actor, transaction, legal, commit)


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)


def focus_text(actor):
    return "%d/%d" % (current_focus(actor), maximum_focus(actor))
