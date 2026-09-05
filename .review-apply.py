from pathlib import Path


def replace(path, old, new):
    path = Path(path)
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one source anchor, found {count}: {old!r}")
    path.write_text(text.replace(old, new, 1))


core = Path("common/guiscripts/GemRBModCore.py")
addition = '''

def is_managed_action(resref):
    return str(resref or "").upper().startswith(("PS", "PX", "CI"))


def abort_action(actor, error):
    import GemRB
    import Transactions
    for namespace in _HANDLER_NAMES:
        Transactions.cancel(namespace, actor)
    try:
        GemRB.Log(2, "GemRBModCore", "Casting cancelled; check the custom-class runtime installation: %s" % error)
    except Exception:
        pass


def spell_error(spellbook, actor, raw_spell, error):
    abort_action(actor, error)
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
'''
text = core.read_text()
if "def abort_action(" in text:
    raise RuntimeError("Review helpers already exist")
core.write_text(text.rstrip() + "\n" + addition)
replace(core, 'def action_info(resref):\n    for handler in _handlers():', 'def action_info(resref):\n    if not is_managed_action(resref):\n        return None\n    for handler in _handlers():')

installer = "common/tools/install_guiscripts.py"
replace(installer,
    '        "\\telse:\\n"\n        "\\t\\ttry:\\n"',
    '        "\\telse:\\n"\n        "\\t\\traw_spell = None\\n"\n        "\\t\\ttry:\\n"')
replace(installer,
    '        "\\t\\t\\tGemRB.Log(2, \\"GemRBModCore\\", str(error))\\n"',
    '        "\\t\\t\\tif not GemRBModCore.spell_error(Spellbook, pc, raw_spell, error):\\n"\n        "\\t\\t\\t\\treturn\\n"')
replace(installer,
    '        "\\ttry:\\n"\n        "\\t\\tpcStats = GemRB.GetPCStats(pc)\\n"\n        "\\t\\tquickResRef = \\"\\"\\n"',
    '        "\\tquickResRef = \\"\\"\\n"\n        "\\ttry:\\n"\n        "\\t\\tpcStats = GemRB.GetPCStats(pc)\\n"')
replace(installer,
    '        "\\t\\tGemRB.Log(2, \\"GemRBModCore\\", \\"quickspell routing failed: %s\\" % error)\\n"',
    '        "\\t\\tGemRBModCore.abort_action(pc, error)\\n"\n        "\\t\\tif not quickResRef or GemRBModCore.is_managed_action(quickResRef):\\n"\n        "\\t\\t\\treturn\\n"')
replace(installer,
    'def render_patch(text, kind, path):\n    if MARK_BEGIN in text:\n        return None\n',
    '''def render_patch(text, kind, path):
    if MARK_BEGIN in text:
        if kind != "actions" or "GemRBModCore.spell_error(" in text:
            return None
        pattern = r"(?ms)^\\t" + re.escape(MARK_BEGIN) + r"\\n.*?^\\t" + re.escape(MARK_END) + r"\\n"
        text, count = re.subn(pattern, "", text)
        if count < 3:
            raise RuntimeError(f"{path.name} legacy action hooks not recognized")
''')
replace("psion/lib/mind-vigor-augment.tpa",
    "opcode = 18 target = 1 resist_dispel = BIT1 parameter1 = ps_vigor_hp timing = 0 duration = 60",
    "opcode = 18 target = 1 resist_dispel = BIT1 parameter1 = ps_vigor_hp parameter2 = 3 timing = 0 duration = 60")
replace("psion/guiscripts/Psionics.py",
    'GemRB.ApplyEffect(actor, "MaximumHPModifier", amount, 0, "", "", "", "PXFBODY", 9)',
    'GemRB.ApplyEffect(actor, "MaximumHPModifier", amount, 3, "", "", "", "PXFBODY", 9)')
replace(".github/workflows/class-registration.yml",
    '      - name: Validate shared GUI lifecycle\n        run: python common/tests/validate.py\n',
    '      - name: Validate shared GUI lifecycle\n        run: python common/tests/validate.py\n      - name: Validate casting and HP review regressions\n        run: python common/tests/validate_review_regressions.py\n')
print("Applied casting, upgrade, Vigor and Psionic Body corrections")
