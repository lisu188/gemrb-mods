from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / "psion" / "guiscripts" / "Psionics.py"
text = path.read_text(encoding="utf-8")

old = "import GemRB\nfrom ie_spells import LS_MEMO\n"
new = "import GemRB\nimport Transactions\nimport InnateCharges\nimport PersistentState\nimport Selectors\nfrom ie_spells import LS_MEMO\n"
assert old in text
text = text.replace(old, new, 1)
text = text.replace("\n_pending = {}\n", "\nTRANSACTION_NAMESPACE = \"Psionics\"\n", 1)

old = '''def _read_private_value(actor, marker, resource):
    try:
        for effect in GemRB.GetEffects(actor, STATE_EFFECT_OPCODE):
            if int(effect.get("Param2", -1)) != marker:
                continue
            if str(effect.get("Resource1", "")).upper() != resource.upper():
                continue
            return True, max(0, int(effect.get("Param1", 0)))
    except Exception as error:
        GemRB.Log(2, "Psionics", "private state read failed: %s" % error)
    return False, 0


def _write_private_value(actor, marker, resource, value, source=SKILL_EFFECT_SOURCE):
    value = max(0, int(value))
    GemRB.DispelEffect(actor, STATE_EFFECT_OPCODE, marker)
    GemRB.ApplyEffect(
        actor, STATE_EFFECT_OPCODE, value, marker, resource,
        "", "", source,
    )
    return value
'''
new = '''def _read_private_value(actor, marker, resource):
    return PersistentState.read(actor, STATE_EFFECT_OPCODE, marker, resource)


def _write_private_value(actor, marker, resource, value, source=SKILL_EFFECT_SOURCE):
    return PersistentState.write(
        actor, STATE_EFFECT_OPCODE, marker, resource, value, source,
    )
'''
assert old in text
text = text.replace(old, new, 1)

old = '''    if encoded_type == TEMPORARY_SPELLINFO_TYPE:
        try:
            spell_resrefs = GemRB.GetSpelldata(actor)
            if spell_index < 0 or spell_index >= len(spell_resrefs):
                return None
            resref = spell_resrefs[spell_index]
        except Exception:
            return None
        if action_info(resref):
            return {"SpellIndex": raw_spell, "SpellResRef": resref}
        return None
'''
new = '''    if encoded_type == TEMPORARY_SPELLINFO_TYPE:
        return Selectors.resolve_temporary(
            actor, raw_spell, lambda resref: bool(action_info(resref)),
            TEMPORARY_SPELLINFO_TYPE,
        )
'''
assert old in text
text = text.replace(old, new, 1)

start = text.index("def refresh_innate_charges(actor):")
end = text.index("\n\ndef _begin_simple_action", start)
new_refresh = '''def refresh_innate_charges(actor):
    if not is_psion(actor):
        return 0
    _sync_focus_passives(actor)
    sync_skill_points(actor)
    _ensure_skill_selector_known(actor)
    _sync_center_action(actor)
    try:
        return InnateCharges.refresh(
            actor,
            lambda resref: _is_reusable_innate(actor, resref),
            INNATE_TYPE,
            INNATE_LEVEL,
        )
    except Exception as error:
        GemRB.Log(2, "Psionics", "charge refresh failed: %s" % error)
        return 0
'''
text = text[:start] + new_refresh + text[end:]

old = '''def _begin_simple_action(actor, transaction, legal, commit):
    pending = _pending.get(actor)
    if pending == transaction:
        if not legal():
            _pending.pop(actor, None)
            return False
        _pending.pop(actor, None)
        return bool(commit())
    if not legal():
        return False
    _pending[actor] = transaction
    return True
'''
new = '''def _begin_simple_action(actor, transaction, legal, commit):
    return Transactions.begin(
        TRANSACTION_NAMESPACE, actor, transaction, legal, commit,
    )
'''
assert old in text
text = text.replace(old, new, 1)

old = '''    pending = _pending.get(actor)
    transaction = (info["resref"], info["cost"])
    if pending == transaction:
        if not can_manifest(actor, info["resref"]):
            _pending.pop(actor, None)
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
            return False
        current = ensure_pool(actor)
        _write_pool_state(actor, current - info["cost"])
        _pending.pop(actor, None)
        return True
    if not can_manifest(actor, info["resref"]):
        GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return False
    _pending[actor] = transaction
    return True


def cancel_pending(actor=None):
    if actor is None:
        _pending.clear()
    else:
        _pending.pop(actor, None)
'''
new = '''    transaction = (info["resref"], info["cost"])

    def legal():
        allowed = can_manifest(actor, info["resref"])
        if not allowed:
            GemRB.DisplayString(10417, 0xFFFFFF, actor)
        return allowed

    def commit():
        current = ensure_pool(actor)
        _write_pool_state(actor, current - info["cost"])
        return True

    return Transactions.begin(
        TRANSACTION_NAMESPACE, actor, transaction, legal, commit,
    )


def cancel_pending(actor=None):
    Transactions.cancel(TRANSACTION_NAMESPACE, actor)
'''
assert old in text
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

# Make the fake GemRB contract model the optional base-stat flag and make shared
# runtime modules importable when the runtime is loaded directly from source.
test = root / "psion" / "tests" / "validate_runtime.py"
t = test.read_text(encoding="utf-8")
old = 'ROOT = Path(__file__).resolve().parents[1]\n'
new = 'ROOT = Path(__file__).resolve().parents[1]\nCOMMON = ROOT.parent / "common" / "guiscripts"\nsys.path.insert(0, str(COMMON))\n'
assert old in t
t = t.replace(old, new, 1)
old = '    effects = {1: []}\n'
new = '    base_stats = dict(stats)\n    effects = {1: []}\n'
assert old in t
t = t.replace(old, new, 1)
old = '    gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)\n'
new = '''    def get_player_stat(actor, stat, base=0):
        source = base_stats if base else stats
        return source.get((actor, stat), 0)

    gemrb.GetPlayerStat = get_player_stat
'''
assert old in t
t = t.replace(old, new, 1)
test.write_text(t, encoding="utf-8")

Path(__file__).unlink()
(root / ".github" / "workflows" / "shared-runtime-refactor.yml").unlink()
