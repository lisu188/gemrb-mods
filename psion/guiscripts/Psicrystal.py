# SPDX-License-Identifier: GPL-2.0-or-later
"""Persistent one-per-Psion psicrystal state and action routing."""
import GemRB
import InnateCharges
import PersistentState
import Selectors
import Transactions
import Psionics
from ie_spells import LS_MEMO

INNATE_TYPE = 2
INNATE_LEVEL = 0
TEMPORARY_SPELLINFO_TYPE = 255
TRANSACTION_NAMESPACE = "Psicrystal"
STATE_EFFECT_OPCODE = "Protection:Spell"
PERSONALITY_MARKER = 0x50534352
PERSONALITY_RESOURCE = "PSCRYSTL"
PERSONALITY_SOURCE = "PSCRYST"
SELECTOR_RESOURCE = "PXCRYS"
SUMMON_RESOURCE = "PXCRSM"
PERSONALITIES = {
    "PXCRHERO": (1, "HEROIC"),
    "PXCRNIMB": (2, "NIMBLE"),
    "PXCROBSV": (3, "OBSERVANT"),
    "PXCRRESO": (4, "RESOLUTE"),
}
PERSONALITY_BY_ID = {value[0]: key for key, value in PERSONALITIES.items()}


def personality_id(actor):
    if not Psionics.is_psion(actor):
        return 0
    found, value = PersistentState.read(
        actor, STATE_EFFECT_OPCODE, PERSONALITY_MARKER, PERSONALITY_RESOURCE,
    )
    return int(value) if found and int(value) in PERSONALITY_BY_ID else 0


def personality(actor):
    choice = PERSONALITY_BY_ID.get(personality_id(actor))
    return PERSONALITIES.get(choice, (0, ""))[1]


def can_choose(actor):
    return Psionics.is_psion(actor) and personality_id(actor) == 0


def available_choices(actor):
    return list(PERSONALITIES) if can_choose(actor) else []


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
        GemRB.Log(2, "Psicrystal", "spellbook sync failed: %s" % error)
        return False


def _tier(actor):
    level = Psionics.manifester_level(actor)
    if level >= 15:
        return 3
    if level >= 8:
        return 2
    return 1


def _passive_resource(actor):
    value = personality_id(actor)
    return "PXCRP%d%d" % (value, _tier(actor)) if value else ""


def _sync_passive(actor):
    resource = _passive_resource(actor)
    if not resource:
        return False
    try:
        GemRB.ApplySpell(actor, resource)
        return True
    except Exception as error:
        GemRB.Log(2, "Psicrystal", "passive sync failed: %s" % error)
        return False


def _commit_choice(actor, resref):
    key = str(resref).upper()
    value = PERSONALITIES.get(key, (0, ""))[0]
    if not value or not can_choose(actor):
        return False
    PersistentState.write(
        actor, STATE_EFFECT_OPCODE, PERSONALITY_MARKER, PERSONALITY_RESOURCE,
        value, PERSONALITY_SOURCE,
    )
    _ensure_known(actor, SUMMON_RESOURCE)
    _sync_passive(actor)
    return True


def action_info(resref):
    key = str(resref or "").upper()
    if key == SELECTOR_RESOURCE:
        return {
            "kind": "psicrystal_selector", "resref": key, "parent": key,
            "selector": True,
        }
    if key == SUMMON_RESOURCE:
        return {
            "kind": "psicrystal_summon", "resref": key, "parent": key,
            "selector": False,
        }
    if key in PERSONALITIES:
        return {
            "kind": "psicrystal_choice", "resref": key, "parent": key,
            "selector": False,
        }
    return None


def resolve_power_entry(spellbook, actor, raw_spell):
    if not Psionics.is_psion(actor):
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
    if not Psionics.is_psion(actor):
        return list(resrefs)
    result = []
    chosen = personality_id(actor) != 0
    for resref in resrefs:
        key = str(resref).upper()
        if key == SELECTOR_RESOURCE:
            if not chosen:
                result.append(resref)
            continue
        if key in PERSONALITIES:
            if not chosen:
                result.append(resref)
            continue
        result.append(resref)
    return result


def refresh_innate_charges(actor):
    if not Psionics.is_psion(actor):
        return 0
    if personality_id(actor):
        _ensure_known(actor, SUMMON_RESOURCE)
        _sync_passive(actor)
        return 0
    _ensure_known(actor, SELECTOR_RESOURCE)
    try:
        return InnateCharges.refresh(
            actor, lambda resref: str(resref).upper() == SELECTOR_RESOURCE,
            INNATE_TYPE, INNATE_LEVEL,
        )
    except Exception as error:
        GemRB.Log(2, "Psicrystal", "selector recharge failed: %s" % error)
        return 0


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            if not Psionics.is_psion(actor):
                continue
            if personality_id(actor):
                _ensure_known(actor, SUMMON_RESOURCE)
                _sync_passive(actor)
                InnateCharges.refresh(
                    actor, lambda resref: str(resref).upper() == SUMMON_RESOURCE,
                    INNATE_TYPE, INNATE_LEVEL,
                )
            else:
                _ensure_known(actor, SELECTOR_RESOURCE)
                InnateCharges.refresh(
                    actor, lambda resref: str(resref).upper() == SELECTOR_RESOURCE,
                    INNATE_TYPE, INNATE_LEVEL,
                )
        except Exception:
            pass


def begin_manifest(actor, resref):
    info = action_info(resref)
    if not info:
        return True
    if info["kind"] == "psicrystal_selector":
        cancel_pending(actor)
        return bool(available_choices(actor))
    if info["kind"] == "psicrystal_choice":
        key = info["resref"]
        return Transactions.begin(
            TRANSACTION_NAMESPACE, actor, ("PERSONALITY", key),
            lambda: can_choose(actor) and key in available_choices(actor),
            lambda: _commit_choice(actor, key),
        )
    if info["kind"] == "psicrystal_summon":
        return Transactions.begin(
            TRANSACTION_NAMESPACE, actor, ("SUMMON", personality_id(actor)),
            lambda: Psionics.is_psion(actor) and personality_id(actor) != 0,
            lambda: True,
        )
    return True


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)
