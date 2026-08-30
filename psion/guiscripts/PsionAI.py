# SPDX-License-Identifier: GPL-2.0-or-later
"""Non-player Psion manifestation controller using the canonical Psion runtime."""
import GemRB
import Psionics

OFFENSE_BY_DISCIPLINE = {
    "SEER": ("PS1ERAY", "PS1MTHR", "PS3EBLT", "PS5PCRU", "PS7CLIF", "PS9TORN"),
    "SHAPER": ("PS1ERAY", "PS1ACON", "PS3COCO", "PS5HOCR", "PS7MCOC", "PS9TCRE"),
    "KINETICIST": ("PS1ERAY", "PS3EBLT", "PS4EBAL", "PS5PCRU", "PS7CLIF", "PS9TORN"),
    "EGOIST": ("PS1ERAY", "PS2BIOF", "PS3HUST", "PS5ADBD", "PS7FISS", "PS9GMET"),
    "NOMAD": ("PS1ERAY", "PS3THOP", "PS4DDOR", "PS5TELE", "PS7EJNT", "PS9TCIR"),
    "TELEPATH": ("PS1MTHR", "PS1EMND", "PS3MBAR", "PS5SCHN", "PS7CLIF", "PS9PCHI"),
}
DEFENSE = ("PS1IARM", "PS1FSCR", "PS2TSHD", "PS3DANG", "PS4IFOR", "PS6DBUF", "PS7RDOP")
MOBILITY = ("PS1BRST", "PS3HUST", "PS4DDOR", "PS5TELE", "PS7EJNT", "PS9TCIR")
SELF_TARGET = frozenset(DEFENSE + MOBILITY + (
    "PS1ACON", "PS9TCRE",
    "PS2BIOF", "PS5ADBD", "PS7FISS", "PS9GMET",
))


def initialize(actor, refill=True):
    if not Psionics.is_psion(actor):
        return False
    Psionics.ensure_pool(actor, bool(refill))
    Psionics.ensure_focus(actor, bool(refill))
    return True


def current_pp(actor):
    return Psionics.ensure_pool(actor) if Psionics.is_psion(actor) else 0


def exact_dc_resource(actor, resref):
    key = str(resref or "").upper()
    info = Psionics.power_info(key)
    if not info or info.get("selector", False):
        return key
    canonical = Psionics._dc_canonical_resref(key)
    replacement = Psionics._dc_variant_resref(canonical, Psionics._dc_modifier(actor))
    return replacement if Psionics._dc_resource_exists(replacement) else canonical


def legal_power(actor, resref):
    return Psionics.can_manifest(actor, str(resref or "").upper())


def _best_legal(actor, candidates):
    legal = []
    for resref in candidates:
        info = Psionics.power_info(resref)
        if info and not info.get("selector", False) and legal_power(actor, resref):
            legal.append((int(info["cost"]), int(info["level"]), resref))
    if not legal:
        return ""
    legal.sort(reverse=True)
    return legal[0][2]


def choose_power(actor, role="offense"):
    if not Psionics.is_psion(actor):
        return ""
    role = str(role or "offense").lower()
    if role == "defense":
        return _best_legal(actor, DEFENSE)
    if role == "mobility":
        return _best_legal(actor, MOBILITY)
    return _best_legal(actor, OFFENSE_BY_DISCIPLINE.get(Psionics.discipline(actor), ()))


def target_for_power(actor, resref, target=None):
    key = str(resref or "").upper()
    if key in SELF_TARGET or target is None:
        return actor
    return target


def manifest(actor, resref, target=None):
    key = str(resref or "").upper()
    info = Psionics.power_info(key)
    if not info or info.get("selector", False) or not legal_power(actor, key):
        return False
    recipient = target_for_power(actor, key, target)
    resource = exact_dc_resource(actor, key)
    current = Psionics.ensure_pool(actor)
    try:
        GemRB.ApplySpell(recipient, resource, actor)
    except Exception as error:
        GemRB.Log(2, "PsionAI", "manifestation failed: %s" % error)
        return False
    Psionics._write_pool_state(actor, current - int(info["cost"]))
    return True


def act(actor, target=None, role="offense"):
    if not Psionics.is_psion(actor):
        return ""
    power = choose_power(actor, role)
    if not power:
        return ""
    return power if manifest(actor, power, target) else ""
