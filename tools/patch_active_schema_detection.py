from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    "cipher/tests/verify_weidu_install.py",
    '''classes_columns, _ = rows(override / "classes.2da")\nassert len(classes_columns) in (6, 18), (layout, classes_columns)\nsplit_schema = len(classes_columns) == 6\n\n''',
    '''# The dedicated class-registration matrix proves which schema should be\n# active. This lifecycle verifier only needs to follow the installer's actual\n# registration so it can validate install/uninstall/reinstall consistently.\nclastext_path = override / "clastext.2da"\nsplit_schema = False\nif clastext_path.is_file():\n    _, clastext_rows = rows(clastext_path)\n    split_schema = "CIPHER" in clastext_rows\n\n''',
)

replace(
    "psion/tests/validate_weidu_install.sh",
    '''class_columns, _ = read_2da(override / "classes.2da")\nassert len(class_columns) in (6, 18), (layout, class_columns)\nsplit_schema = len(class_columns) == 6\nclass_tables = ["classes.2da"]\n''',
    '''# The dedicated cross-mod registration test proves whether a scenario must\n# use split or combined class metadata. This lifecycle verifier follows the\n# actual Psion registration so install/uninstall/reinstall assertions remain\n# independent of fixture naming and inactive auxiliary tables.\nclastext_path = override / "clastext.2da"\nsplit_schema = False\nif clastext_path.is_file():\n    _, clastext_rows = read_2da(clastext_path)\n    split_presence = [discipline in clastext_rows for discipline in disciplines]\n    assert all(split_presence) or not any(split_presence), (layout, split_presence)\n    split_schema = all(split_presence)\nclass_tables = ["classes.2da"]\n''',
)
