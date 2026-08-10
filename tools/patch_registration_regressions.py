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
    '''assert set(class_ids) == {"CIPHER"}, (layout, class_ids)\nassert 0 <= class_ids["CIPHER"] <= 255\n\nfor filename in ("classes.2da", "alignmnt.2da", "abclasrq.2da", "profs.2da", "xplevel.2da", "thac0.2da", "lore.2da", "xpcap.2da", "clskills.2da"):\n    assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)\n\nif layout != "legacy":\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)\n    _, hpclass = rows(override / "hpclass.2da")\n    assert hpclass["CIPHER"] == ["HPPRS"], (layout, hpclass["CIPHER"])\n\n_, clskills = rows(override / "clskills.2da")\nassert clskills["CIPHER"][2] == "MXCIPHER", (layout, clskills["CIPHER"])\n''',
    '''assert set(class_ids) == {"CIPHER"}, (layout, class_ids)\nassert 1 <= class_ids["CIPHER"] <= 31, (layout, class_ids)\n\nclasses_columns, _ = rows(override / "classes.2da")\nassert len(classes_columns) in (6, 18), (layout, classes_columns)\nsplit_schema = len(classes_columns) == 6\n\nfor filename in ("classes.2da", "alignmnt.2da", "abclasrq.2da", "profs.2da", "xplevel.2da", "thac0.2da", "lore.2da", "xpcap.2da", "clskills.2da"):\n    assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)\n\nif split_schema:\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)\n    _, hpclass = rows(override / "hpclass.2da")\n    assert hpclass["CIPHER"] == ["HPPRS"], (layout, hpclass["CIPHER"])\nelse:\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        path = override / filename\n        if path.is_file():\n            assert "CIPHER" not in path.read_text(encoding="utf-8", errors="replace"), (layout, filename)\n\n_, clskills = rows(override / "clskills.2da")\nassert clskills["CIPHER"][2] == "MXCIPHER", (layout, clskills["CIPHER"])\nassert row_index(override / "clskills.2da", "CIPHER") == class_ids["CIPHER"], (layout, class_ids)\nassert row_index(override / "qslots.2da", "CIPHER") == class_ids["CIPHER"] - 1, (layout, class_ids)\n''',
)

replace(
    "psion/tests/validate_weidu_install.sh",
    '''class_tables = ["classes.2da"]\nif layout != "legacy":\n    class_tables.extend(("clastext.2da", "clsrcreq.2da", "hpclass.2da"))\nfor filename in (\n    *class_tables,\n    "class.ids", "alignmnt.2da", "abclasrq.2da", "weapprof.2da",\n    "profs.2da", "xpcap.2da", "avprefc.2da", "qslots.2da", "clskills.2da",\n):\n    text = (override / filename).read_text(encoding="utf-8", errors="replace")\n    for discipline in disciplines:\n        assert discipline in text, (layout, filename, discipline)\n''',
    '''class_columns, _ = read_2da(override / "classes.2da")\nassert len(class_columns) in (6, 18), (layout, class_columns)\nsplit_schema = len(class_columns) == 6\nclass_tables = ["classes.2da"]\nif split_schema:\n    class_tables.extend(("clastext.2da", "clsrcreq.2da", "hpclass.2da"))\nfor filename in (\n    *class_tables,\n    "class.ids", "alignmnt.2da", "abclasrq.2da", "weapprof.2da",\n    "profs.2da", "xpcap.2da", "avprefc.2da", "qslots.2da", "clskills.2da",\n):\n    text = (override / filename).read_text(encoding="utf-8", errors="replace")\n    for discipline in disciplines:\n        assert discipline in text, (layout, filename, discipline)\nif not split_schema:\n    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):\n        path = override / filename\n        if path.is_file():\n            text = path.read_text(encoding="utf-8", errors="replace")\n            for discipline in disciplines:\n                assert discipline not in text, (layout, filename, discipline)\n''',
)

replace(
    "psion/tests/validate_weidu_install.sh",
    '''class_ids = read_class_ids(override / "class.ids")\nassert set(class_ids) == set(disciplines), (layout, class_ids)\npsion_ids = set(class_ids.values())\n''',
    '''class_ids = read_class_ids(override / "class.ids")\nassert set(class_ids) == set(disciplines), (layout, class_ids)\n_, clskills_list = read_2da_list(override / "clskills.2da")\n_, qslots_list = read_2da_list(override / "qslots.2da")\nfor discipline in disciplines:\n    cl_index = next(index for index, row in enumerate(clskills_list) if row[0] == discipline)\n    qs_index = next(index for index, row in enumerate(qslots_list) if row[0] == discipline)\n    assert class_ids[discipline] == cl_index, (layout, discipline, class_ids[discipline], cl_index)\n    assert class_ids[discipline] <= 31, (layout, discipline, class_ids[discipline])\n    assert qs_index == class_ids[discipline] - 1, (layout, discipline, qs_index, class_ids[discipline])\npsion_ids = set(class_ids.values())\n''',
)

replace(
    "common/tests/validate_class_registration_weidu.py",
    '''def write_native9(path: Path):\n    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()\n    header = lines[2].split()\n    if len(header) != 5:\n        raise AssertionError((path, header))\n    out = [lines[0], lines[1], "        CLASSID KITID LOWER DESCSTR MIXED BIOGRAPHY FALLEN BRIEFDESC"]\n    for row in read_rows(path):\n        if len(row) < 6:\n            continue\n        out.append(" ".join(row[:6] + ["-1", "0", row[5]]))\n    path.write_text("\\n".join(out) + "\\n", encoding="utf-8")\n\n\ndef add_combined_hp(path: Path):\n''',
    '''def write_native9(path: Path):\n    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()\n    header = lines[2].split()\n    if len(header) != 5:\n        raise AssertionError((path, header))\n    out = [lines[0], lines[1], "        CLASSID KITID LOWER DESCSTR MIXED BIOGRAPHY FALLEN BRIEFDESC"]\n    for row in read_rows(path):\n        if len(row) < 6:\n            continue\n        out.append(" ".join(row[:6] + ["-1", "0", row[5]]))\n    path.write_text("\\n".join(out) + "\\n", encoding="utf-8")\n\n\ndef write_split_classes(path: Path):\n    path.write_text(\n        "2DA V1.0\\n*\\n        SAVE MULTI USABILITY MC_WAS_ID STREXTRA CONBONLVL\\n"\n        "SORCERER SAVEWIZ 0 0x40000 -1 0 10\\n"\n        "MONK SAVEMONK 0 0x20000000 -1 0 9\\n"\n        "SHAMAN SAVEPRS 0 0x40000000 -1 1 9\\n",\n        encoding="ascii",\n    )\n\n\ndef add_combined_hp(path: Path):\n''',
)

replace(
    "common/tests/validate_class_registration_weidu.py",
    '''        if scenario == "combined_hp":\n            add_combined_hp(override / "hpclass.2da")\n        else:\n            write_native9(override / "clastext.2da")\n''',
    '''        if scenario == "combined_hp":\n            add_combined_hp(override / "hpclass.2da")\n        else:\n            write_split_classes(override / "classes.2da")\n            write_native9(override / "clastext.2da")\n''',
)
