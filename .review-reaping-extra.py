from pathlib import Path


def replace(path, old, new):
    path = Path(path)
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: source anchor mismatch")
    path.write_text(text.replace(old, new, 1))


replace("cipher/tests/validate_reaping_knives_runtime.py",
        '    assert "SetMeleeEffect" in source\n    assert "SetRangedEffect" in source',
        '    assert "OUTER_SET ci_rk_set_melee = 248" in source\n    assert "OUTER_SET ci_rk_set_ranged = 249" in source')
replace("cipher/tests/verify_high_tier_weidu.py",
        '    for slot in range(1, 7):',
        '    for slot in range(1, 256):')
print("Strengthened opcode contracts and binary validation for all 255 owner resource sets")
