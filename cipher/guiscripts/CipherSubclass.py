# SPDX-License-Identifier: GPL-2.0-or-later
"""Optional persistent Cipher subclass routing and Soul Blade implementation."""
import GemRB
import InnateCharges
import PersistentState
import Selectors
import Transactions
import Cipher
from ie_spells import LS_MEMO

INNATE_TYPE = 2
INNATE_LEVEL = 0
TEMPORARY_SPELLINFO_TYPE = 255
TRANSACTION_NAMESPACE = "CipherSubclass"
STATE_EFFECT_OPCODE = "Protection:Spell"
SUBCLASS_MARKER = 0x43495342
SUBCLASS_RESOURCE = "CISUBCLS"
SUBCLASS_SOURCE = "CISUB"
SELECTOR_RESOURCE = "CISUBSEL"
SOUL_BLADE_CHOICE = "CISBSBLD"
SOUL_BLADE_ACTION = "CISBANN"
SOUL_BLADE_PASSIVE = "CISBPASS"
SOUL_BLADE_ID = 1
SOUL_BLADE_COST = 20


def subclass_id(actor):
    if not Cipher.is_cipher(actor):
        return 0
    found, value = PersistentState.read(
        actor, STATE_EFFECT_OPCODE, SUBCLASS_MARKER, SUBCLASS_RESOURCE,
    )
    return int(value) if found and int(value) == SOUL_BLADE_ID else 0


def subclass(actor):
    return "SOUL_BLADE" if subclass_id(actor) == SOUL_BLADE_ID else ""


def modify_focus_gain(actor, amount, source=""):
    return max(0, int(amount))


def modify_focus_cap(actor, cap):
    return max(0, int(cap))


def modify_power_cost(actor, resref, cost):
    return max(0, int(cost))


def weapon_effect_resource(actor):
    return SOUL_BLADE_PASSIVE if subclass_id(actor) == SOUL_BLADE_ID else ""


def passive_resource(actor):
    return weapon_effect_resource(actor)


def can_choose(actor):
    return Cipher.is_cipher(actor) and subclass_id(actor) == 0


def _known(actor, resref):
    key = str(resref).upper()
    try:
        count = GemRB.GetKnownSpellsCount(actor, INNATE_TYPE, INNATE_LEVEL)
        for index in range(count):
            spell = GemRB.GetKnownSpell(actor, INNATE_TYPE, INNATE_LEVEL, index)
            if str(spell.get("SpellResRef", "")).upper() == key:
                return True
    except Exception:
        return False
    return False


def _ensure_known(actor, resref):
    if _known(actor, resref):
        return True
    try:
        return GemRB.LearnSpell(actor, resref, LS_MEMO) in (0, 1)
    except Exception as error:
        GemRB.Log(2, "CipherSubclass", "spellbook sync failed: %s" % error)
        return False


def _sync_passive(actor):
    resource = passive_resource(actor)
    if not resource:
        return False
    try:
        GemRB.ApplySpell(actor, resource)
        return True
    except Exception as error:
        GemRB.Log(2, "CipherSubclass", "passive sync failed: %s" % error)
        return False


def _choose_soul_blade(actor):
    if not can_choose(actor):
        return False
    PersistentState.write(
        actor, STATE_EFFECT_OPCODE, SUBCLASS_MARKER, SUBCLASS_RESOURCE,
        SOUL_BLADE_ID, SUBCLASS_SOURCE,
    )
    _ensure_known(actor, SOUL_BLADE_ACTION)
    _sync_passive(actor)
    return True


def action_info(resref):
    key = str(resref or "").upper()
    if key == SELECTOR_RESOURCE:
        return {
            "kind": "subclass_selector", "resref": key, "parent": key,
            "selector": True,
        }
    if key == SOUL_BLADE_CHOICE:
        return {
            "kind": "subclass_choice", "resref": key, "parent": key,
            "selector": False,
        }
    if key == SOUL_BLADE_ACTION:
        return {
            "kind": "soul_annihilation", "resref": key, "parent": key,
            "selector": False, "cost": SOUL_BLADE_COST,
        }
    return None


def resolve_power_entry(spellbook, actor, raw_spell):
    if not Cipher.is_cipher(actor):
        return None
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


def filter_spellinfo(actor, resrefs):
    if not Cipher.is_cipher(actor):
        return list(resrefs)
    result = []
    chosen = subclass_id(actor) != 0
    for resref in resrefs:
        key = str(resref).upper()
        if key in (SELECTOR_RESOURCE, SOUL_BLADE_CHOICE):
            if not chosen:
                result.append(resref)
            continue
        result.append(resref)
    return result


def refresh_innate_charges(actor):
    if not Cipher.is_cipher(actor):
        return 0
    if subclass_id(actor) == SOUL_BLADE_ID:
        _ensure_known(actor, SOUL_BLADE_ACTION)
        _sync_passive(actor)
        predicate = lambda resref: str(resref).upper() == SOUL_BLADE_ACTION
    else:
        _ensure_known(actor, SELECTOR_RESOURCE)
        predicate = lambda resref: str(resref).upper() == SELECTOR_RESOURCE
    try:
        return InnateCharges.refresh(actor, predicate, INNATE_TYPE, INNATE_LEVEL)
    except Exception as error:
        GemRB.Log(2, "CipherSubclass", "charge refresh failed: %s" % error)
        return 0


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            if not Cipher.is_cipher(actor):
                continue
            refresh_innate_charges(actor)
        except Exception:
            pass


def begin_manifest(actor, resref):
    info = action_info(resref)
    if not info:
        return True
    if info["kind"] == "subclass_selector":
        cancel_pending(actor)
        return can_choose(actor)
    if info["kind"] == "subclass_choice":
        return Transactions.begin(
            TRANSACTION_NAMESPACE, actor, ("SUBCLASS", SOUL_BLADE_ID),
            lambda: can_choose(actor), lambda: _choose_soul_blade(actor),
        )
    if info["kind"] == "soul_annihilation":
        def legal():
            return (
                subclass_id(actor) == SOUL_BLADE_ID
                and Cipher.current_focus(actor) >= SOUL_BLADE_COST
            )

        def commit():
            Cipher.set_focus(actor, Cipher.current_focus(actor) - SOUL_BLADE_COST)
            return True

        return Transactions.begin(
            TRANSACTION_NAMESPACE, actor,
            ("SOUL_ANNIHILATION", SOUL_BLADE_COST), legal, commit,
        )
    return True


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)
