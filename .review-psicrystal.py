from pathlib import Path


def replace(path, old, new):
    path = Path(path)
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: source anchor mismatch")
    path.write_text(text.replace(old, new, 1))


replace("psion/guiscripts/Psionics.py", '''def can_choose_psicrystal(actor, resref):
    return bool(
        is_psion(actor)
        and not has_psicrystal_choice(actor)
        and psicrystal_choice_info(resref)
    )
''', '''def can_choose_psicrystal(actor, resref):
    info = psicrystal_choice_info(resref)
    return bool(
        info
        and is_psion(actor)
        and not has_psicrystal_choice(actor)
        and _skill_access_allowed(actor, skill_rule_info(info["skill"]))
    )
''')
replace("psion/tests/validate_psicrystal.py", '''        assert set(module.available_psicrystal_choices(1)) == {
            value[1] for value in EXPECTED.values()
        }
''', '''        assert set(module.available_psicrystal_choices(1)) == {
            "PXCART", "PXCSAGE", "PXCSING"
        }
''')
replace("psion/tests/validate_psicrystal.py", '        assert module.psicrystal_personality(1) == 0\n        assert set(module.available_psicrystal_choices(1))', '''        combinations = 0
        for class_row, discipline in module.PSION_CLASSES.items():
            for personality_id, resref, skill, bonus in EXPECTED.values():
                class_rows[4] = class_row
                effects[4] = []
                known[4] = []
                memorized[4] = []
                module.cancel_pending(4)
                for stat in (34, 36, 38, 39, 40, 41, 42):
                    stats[(4, stat)] = 5 if stat == 34 else 18
                access = module.skill_rule_info(skill)["access"]
                allowed = access in ("CORE", discipline)
                assert module.can_choose_psicrystal(4, resref) == allowed, (class_row, resref)
                assert (resref in module.available_psicrystal_choices(4)) == allowed
                assert (resref in module.filter_spellinfo(4, [resref])) == allowed
                assert module._ensure_psicrystal_selector_known(4)
                assert module.begin_manifest(4, resref) == allowed
                assert module.psicrystal_personality(4) == 0
                if allowed:
                    baseline = module.skill_check_total(4, skill, roll=10)
                    assert baseline is not None
                    assert module.begin_manifest(4, resref)
                    assert module.psicrystal_personality(4) == personality_id
                    assert module.skill_check_total(4, skill, roll=10) == baseline + bonus
                    effects[4] = [dict(effect) for effect in effects[4]]
                    assert module.psicrystal_personality(4) == personality_id
                    assert not module.can_choose_psicrystal(4, resref)
                    assert "PXCRYST" not in {spell["SpellResRef"] for spell in known[4]}
                else:
                    assert not module._choose_psicrystal(4, resref)
                    assert module.psicrystal_personality(4) == 0
                    assert "PXCRYST" in {spell["SpellResRef"] for spell in known[4]}
                combinations += 1
        assert combinations == 30

        effects[4] = []
        module.cancel_pending(4)
        class_rows[4] = "PSION_SHAPER"
        assert module.begin_manifest(4, "PXCART")
        class_rows[4] = "PSION_EGOIST"
        assert not module.begin_manifest(4, "PXCART")
        assert module.psicrystal_personality(4) == 0
        module.cancel_pending(4)
        class_rows.pop(4)

        assert module.psicrystal_personality(1) == 0
        assert set(module.available_psicrystal_choices(1))''')
readme = Path("psion/README.md")
readme.write_text(readme.read_text().rstrip() + '''

### Psicrystal personality availability

Personality selection only offers bonuses for skills available to the Psion's
current discipline. All disciplines may choose Sage or Single-Minded. Artiste
requires Shaper, Friendly requires Telepath, and Observant requires Seer.
The same rule is checked again when the choice commits; a blocked choice does
not consume the selector or grant cross-discipline skill access. The personality
and owner benefit are the current slice, not a completed summoned-psicrystal
lifecycle.
''')
print("Applied personality skill-access gate and all 30 discipline/personality cases")
