# SPDX-License-Identifier: GPL-2.0-or-later
"""GemRB runtime support for the Pillars-inspired Cipher class."""
import GemRB
import Transactions
import InnateCharges

FOCUS_STAT = 165
FOCUS_UNIT = 5
STARTING_FOCUS = 20
LEVEL_STAT = 34
INNATE_TYPE = 2
INNATE_LEVEL = 0
CIPHER_CLASS = "CIPHER"
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


def restore_party():
    cancel_pending()
    for actor in range(1, 7):
        try:
            if is_cipher(actor):
                set_focus(actor, STARTING_FOCUS)
        except Exception:
            pass


def power_info(resref):
    key = str(resref or "").upper()
    if not key.startswith("CI"):
        return None
    try:
        table = GemRB.LoadTable("cipherpowers", False, True)
        return {
            "resref": key,
            "tier": int(table.GetValue(key, "TIER")),
            "unlock": int(table.GetValue(key, "UNLOCK")),
            "cost": int(table.GetValue(key, "COST")),
        }
    except Exception:
        return None


def can_manifest(actor, resref):
    info = power_info(resref)
    return bool(
        info
        and is_cipher(actor)
        and cipher_level(actor) >= info["unlock"]
        and current_focus(actor) >= info["cost"]
    )


def resolve_power_entry(spellbook, actor, raw_spell):
    encoded_type = raw_spell // 1000
    spell_index = raw_spell % 1000
    book_types = [i for i in range(16) if encoded_type & (1 << i)]
    if not book_types:
        book_types = range(16)
    for book_type in book_types:
        for candidate in spellbook.GetUsableMemorizedSpells(actor, book_type):
            if candidate.get("SpellIndex", -1) % 1000 != spell_index:
                continue
            if power_info(candidate.get("SpellResRef", "")):
                return candidate
    return None


def refresh_innate_charges(actor):
    if not is_cipher(actor):
        return 0
    try:
        return InnateCharges.refresh(
            actor,
            lambda resref: bool(power_info(resref)),
            INNATE_TYPE,
            INNATE_LEVEL,
        )
    except Exception as error:
        GemRB.Log(2, "Cipher", "charge refresh failed: %s" % error)
        return 0


def begin_manifest(actor, resref):
    info = power_info(resref)
    if not info:
        return True

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
