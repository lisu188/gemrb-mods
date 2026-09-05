from pathlib import Path


def replace(path, old, new):
    path = Path(path)
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: source anchor mismatch: {old!r}")
    path.write_text(text.replace(old, new, 1))


runtime = "cipher/guiscripts/Cipher.py"
replace(runtime, 'REAPING_KNIVES_RESOURCE = "CI8RKNI"', '''REAPING_KNIVES_RESOURCE = "CI8RKNI"
REAPING_OWNER_FIRST = 7
REAPING_OWNER_LAST = 255
REAPING_OWNER_COUNTER = "CIRKNEXT"
REAPING_OWNER_MARKER = 0x43495249
REAPING_OWNER_RESOURCE = "CIRKID"
REAPING_OWNER_OPCODE = "Protection:Spell"''')
replace(runtime, 'def prepare_action_entry(spellbook, actor, entry):', '''def _read_reaping_owner(actor):
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


def prepare_action_entry(spellbook, actor, entry):''')
replace(runtime, '    replacement = "CI8RK%d" % actor\n    try:\n', '    try:\n        replacement = "CI8RK%d" % _reaping_owner_token(actor)\n')

builder = Path("cipher/lib/reaping-knives-focus.tpa")
source = builder.read_text()
old_header = source[:source.index("OUTER_SET ci_rk_owner_state_stat")]
source = source.replace(old_header, '''// Reaping Knives routes ally weapon hits through save-persistent owner tokens.
// Tokens are assigned once per actor by Cipher.py, independently of party order.
// Legacy slot resources 1..6 remain available for existing timed effects; new
// identities use 7..255 and are never reassigned to another actor in the save.

OUTER_SET ci_rk_owner_token_limit = 255
''', 1)
if source.count("ci_rk_slot <= 6;") != 2:
    raise RuntimeError("Unexpected Reaping Knives owner loops")
source = source.replace("ci_rk_slot <= 6;", "ci_rk_slot <= ci_rk_owner_token_limit;")
builder.write_text(source)

checks = "cipher/tests/validate_reaping_knives_runtime.py"
replace(checks, 'import importlib.util\n', 'import importlib.util\nimport subprocess\n')
replace(checks, '    spec.loader.exec_module(module)\n    return module, prepared, variables, logs', '    spec.loader.exec_module(module)\n    module._reaping_owner_token = lambda actor: actor + 6\n    return module, prepared, variables, logs')
replace(checks, '"CI8RK3")]', '"CI8RK9")]')
replace(checks, '    test_installer_source_contract()\n', '    test_installer_source_contract()\n    subprocess.run([sys.executable, str(CIPHER / "tests" / "validate_reaping_identity.py")], check=True)\n')

readme = Path("cipher/README.md")
readme.write_text(readme.read_text().rstrip() + '''

### Reaping Knives owner identity

New casts use an owner token saved on the Cipher, not the actor's current party
slot. The game-global allocation counter and actor effect survive save/reload.
Party reordering, dismissal and rejoining do not transfer an existing token to a
different Cipher. Recasting reuses the same identity, including when older buffs
remain on other allies. Allocation is immediate and validated before preparing
the cast; failures stop casting rather than falling back to a portrait slot.

The generated resource bank supports 249 distinct Reaping Knives owners per
save (tokens 7–255). This is a lifetime-owner limit, not a cast limit. Exhaustion
fails closed, while already registered owners can continue casting. Tokens 1–6
are reserved for pre-upgrade resources and never allocated by the new runtime.
Allow existing pre-upgrade Reaping Knives effects to expire before testing the
new routing. Imported or manually edited character/save combinations require
separate qualification; corrupted or inconsistent identity records are rejected.
''')
print("Applied persistent owner identity, resource bank and regression entrypoint")
