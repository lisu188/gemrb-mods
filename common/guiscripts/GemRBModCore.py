# SPDX-License-Identifier: GPL-2.0-or-later
"""Dispatcher for optional GemRB class runtime modules."""
import importlib

_HANDLER_NAMES = ("Psionics", "Cipher")
_pending_casts = {}


def _handlers():
    result = []
    for name in _HANDLER_NAMES:
        try:
            result.append(importlib.import_module(name))
        except ImportError as exc:
            # A handler that is not installed is optional. Import failures raised
            # *by* an installed handler are configuration/runtime errors and must
            # remain visible instead of silently disabling that class runtime.
            if getattr(exc, "name", None) == name:
                continue
            raise
    return result


def cancel_pending(actor=None):
    if actor is None:
        _pending_casts.clear()
    else:
        _pending_casts.pop(actor, None)
    for handler in _handlers():
        function = getattr(handler, "cancel_pending", None)
        if function:
            function(actor)


def restore_party():
    cancel_pending()
    for handler in _handlers():
        function = getattr(handler, "restore_party", None)
        if function:
            function()


def refresh_innate_charges(actor):
    restored = 0
    for handler in _handlers():
        function = getattr(handler, "refresh_innate_charges", None)
        if function:
            restored += int(function(actor) or 0)
    return restored


def filter_spellinfo(actor, resrefs):
    filtered = list(resrefs)
    for handler in _handlers():
        function = getattr(handler, "filter_spellinfo", None)
        if function:
            filtered = list(function(actor, filtered))
    return filtered


def resolve_action_entry(spellbook, actor, raw_spell):
    for handler in _handlers():
        function = getattr(handler, "resolve_power_entry", None)
        if not function:
            continue
        entry = function(spellbook, actor, raw_spell)
        if entry:
            return handler, entry
    return None, None


def begin_spell(spellbook, actor, raw_spell):
    # Each real button selection starts a new reservation. SpellPressed is not
    # a completion event: current GemRB can call it only once, and target-mode
    # cancellation must never commit a previous reservation on the next click.
    cancel_pending(actor)
    handler, entry = resolve_action_entry(spellbook, actor, raw_spell)
    if not entry:
        return _native_spell_selection(spellbook, actor, raw_spell)
    import GemRB
    if not hasattr(GemRB, "SetSpellCastCheck"):
        GemRB.Log(1, "GemRBModCore", "Class powers require GemRB SetSpellCastCheck support")
        return False
    selected_actors = GemRB.GetSelectedActors()
    if not selected_actors:
        return False
    GemRB.SetSpellCastCheck(confirm_spell)
    # Internal resource substitutions are metadata only here. The canonical
    # selection remains the PP/Focus authority; targeting must not deplete a
    # memorized parent or require learning private DC/owner-specific variants.
    prepare = getattr(handler, "prepare_action_entry", None)
    if prepare:
        prepared = prepare(spellbook, actor, entry)
        if prepared is False:
            return False
        if prepared:
            entry = prepared
    selected = str(entry["SpellResRef"]).upper()
    if not handler.begin_manifest(actor, selected):
        cancel_pending(actor)
        return False
    _pending_casts[actor] = {
        "handler": handler,
        "selected": selected,
        "cast": str(entry.get("CastResRef", selected)).upper(),
        # GameGetFirstSelectedActor supplies the party slot, but party slots
        # can be reordered. Bind its corresponding stable selected global ID.
        "global_id": selected_actors[0],
    }
    return True


def cast_spell(actor, spell_type, spell_index):
    """Route internal variants through the engine's installed-resource path."""
    import GemRB
    pending = _pending_casts.get(actor)
    if spell_type != -1 and pending and pending["cast"] != pending["selected"]:
        return GemRB.SpellCast(actor, -3, 0, pending["cast"])
    return GemRB.SpellCast(actor, spell_type, spell_index)


def confirm_spell(actor, resref):
    """Commit only when the engine accepts this actor's prepared GUI cast.

    The engine calls this after target validation, immediately before queuing
    the cast (or applying an instant, untargeted selector). Escape/cursor resets
    do not call it. Returning False vetoes an unprepared or now-illegal power.
    Native spells remain unaffected; no scripted/AI casting is intercepted.
    """
    import GemRB
    actual = str(resref).upper()
    pending = _pending_casts.get(actor)
    if pending:
        selected_actors = GemRB.GetSelectedActors()
        if not selected_actors or selected_actors[0] != pending["global_id"]:
            cancel_pending(actor)
            GemRB.Log(1, "GemRBModCore", "Prepared class power actor changed; cast rejected")
            return False
    if pending and pending["cast"] == actual:
        try:
            accepted = bool(pending["handler"].begin_manifest(actor, pending["selected"]))
        except Exception:
            cancel_pending(actor)
            raise
        if not accepted:
            cancel_pending(actor)
        return accepted
    cancel_pending(actor)
    if pending or is_managed_action(actual):
        GemRB.Log(1, "GemRBModCore", "Unprepared class power cast rejected: %s" % actual)
        return False
    return True


def action_info(resref):
    if not is_managed_action(resref):
        return None
    for handler in _handlers():
        function = getattr(handler, "action_info", None) or getattr(handler, "power_info", None)
        if not function:
            continue
        info = function(resref)
        if not info:
            continue
        result = dict(info)
        result["handler"] = handler.__name__
        result["parent"] = result.get("parent") or result.get("resref") or str(resref).upper()
        result["innate_type"] = int(getattr(handler, "INNATE_TYPE", 2))
        return result
    return None


def is_managed_action(resref):
    return str(resref or "").upper().startswith(("PS", "PX", "CI"))


def abort_action(actor, error):
    import GemRB
    import Transactions
    _pending_casts.pop(actor, None)
    for namespace in _HANDLER_NAMES:
        Transactions.cancel(namespace, actor)
    try:
        GemRB.Log(2, "GemRBModCore", "Casting cancelled; check the custom-class runtime installation: %s" % error)
    except Exception:
        pass


def _native_spell_selection(spellbook, actor, raw_spell):
    try:
        import GemRB
        encoded_type, index = divmod(int(raw_spell), 1000)
        if encoded_type == 255:
            resrefs = [GemRB.GetSpelldata(actor)[index]]
        else:
            books = [i for i in range(16) if encoded_type & (1 << i)] or range(16)
            resrefs = [
                entry.get("SpellResRef", "")
                for book in books
                for entry in spellbook.GetUsableMemorizedSpells(actor, book)
                if entry.get("SpellIndex", -1) % 1000 == index
            ]
        return bool(resrefs) and all(resref and not is_managed_action(resref) for resref in resrefs)
    except Exception:
        return False


def spell_error(spellbook, actor, raw_spell, error):
    abort_action(actor, error)
    return _native_spell_selection(spellbook, actor, raw_spell)
