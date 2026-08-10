# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared two-phase action transactions for GemRB class runtimes."""

_pending = {}


def begin(namespace, actor, transaction, legal, commit=lambda: True):
    key = (str(namespace), actor)
    if _pending.get(key) == transaction:
        if not legal():
            _pending.pop(key, None)
            return False
        _pending.pop(key, None)
        return bool(commit())
    if not legal():
        return False
    _pending[key] = transaction
    return True


def cancel(namespace, actor=None):
    namespace = str(namespace)
    if actor is not None:
        _pending.pop((namespace, actor), None)
        return
    for key in [key for key in _pending if key[0] == namespace]:
        _pending.pop(key, None)


def clear():
    _pending.clear()
