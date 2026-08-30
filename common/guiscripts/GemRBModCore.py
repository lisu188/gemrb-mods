# SPDX-License-Identifier: GPL-2.0-or-later
"""Dispatcher for optional GemRB class runtime modules."""
import importlib

_HANDLER_NAMES = ("Psionics", "Cipher")


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
    for handler in _handlers():
        function = getattr(handler, "cancel_pending", None)
        if function:
            function(actor)


def restore_party():
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
    handler, entry = resolve_action_entry(spellbook, actor, raw_spell)
    if not entry:
        return True
    # Handlers may replace the selected resource through GemRB's own
    # PrepareSpontaneousCast mechanism before ActionsWindow reads the Spell var.
    # The transaction still receives the canonical selected resref, so resource
    # substitutions cannot change PP/Focus cost or selector ownership.
    prepare = getattr(handler, "prepare_action_entry", None)
    if prepare:
        prepared = prepare(spellbook, actor, entry)
        if prepared is False:
            return False
        if prepared:
            entry = prepared
    return bool(handler.begin_manifest(actor, entry["SpellResRef"]))


def action_info(resref):
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
