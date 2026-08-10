#!/usr/bin/env python3
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
layout = sys.argv[2]
override = root / "override"


def rows(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    result = {}
    for line in lines[3:]:
        fields = line.split()
        if fields:
            result[fields[0]] = fields[1:]
    return lines[2].split(), result


def row_index(path, name):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines[3:]):
        fields = line.split()
        if fields and fields[0] == name:
            return index
    raise AssertionError((layout, path.name, name))


def spl_path(resref):
    return override / f"{resref}.spl"


class_ids = {}
for line in (override / "class.ids").read_text(encoding="utf-8").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1] == "CIPHER":
        class_ids[fields[1]] = int(fields[0], 0)
assert set(class_ids) == {"CIPHER"}, (layout, class_ids)
assert 1 <= class_ids["CIPHER"] <= 31, (layout, class_ids)

classes_columns, _ = rows(override / "classes.2da")
assert len(classes_columns) in (6, 18), (layout, classes_columns)
split_schema = len(classes_columns) == 6

for filename in ("classes.2da", "alignmnt.2da", "abclasrq.2da", "profs.2da", "xplevel.2da", "thac0.2da", "lore.2da", "xpcap.2da", "clskills.2da"):
    assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)

if split_schema:
    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):
        assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)
    _, hpclass = rows(override / "hpclass.2da")
    assert hpclass["CIPHER"] == ["HPPRS"], (layout, hpclass["CIPHER"])
else:
    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):
        path = override / filename
        if path.is_file():
            assert "CIPHER" not in path.read_text(encoding="utf-8", errors="replace"), (layout, filename)

_, clskills = rows(override / "clskills.2da")
assert clskills["CIPHER"][2] == "MXCIPHER", (layout, clskills["CIPHER"])
assert row_index(override / "clskills.2da", "CIPHER") == class_ids["CIPHER"], (layout, class_ids)
assert row_index(override / "qslots.2da", "CIPHER") == class_ids["CIPHER"] - 1, (layout, class_ids)

_, ability = rows(override / "abclasrq.2da")
assert ability["CIPHER"] == ["0", "0", "0", "13", "0", "0"], (layout, ability["CIPHER"])

_, profs = rows(override / "profs.2da")
assert profs["CIPHER"] == ["2", "4"], (layout, profs["CIPHER"])

_, xp = rows(override / "xplevel.2da")
assert xp["CIPHER"] == xp["MAGE"], (layout, xp["CIPHER"], xp["MAGE"])

_, thac0 = rows(override / "thac0.2da")
assert thac0["CIPHER"][:8] == ["20", "20", "19", "19", "18", "18", "17", "17"], (layout, thac0["CIPHER"][:8])

_, splprot = rows(override / "splprot.2da")
assert splprot["CIPHER_HOSTILE"] == ["0x108", "2", "1"], (layout, splprot["CIPHER_HOSTILE"])
hostile_row = row_index(override / "splprot.2da", "CIPHER_HOSTILE")

effects_ids = (override / "effects.ids").read_text(encoding="utf-8", errors="replace")
assert "0x155 CastSpellOnCriticalHit" in effects_ids, layout

for resref in ("CIFCORE", "CIFSW15", "CIFSW20", "CIFCRIT", "CI1WHSP", "CI9SCOL", "CIFGAIN", "CIFSTEP", "CIFS0", "CIFS34"):
    assert spl_path(resref).is_file(), (layout, resref)


def resource(data, offset):
    return data[offset:offset + 8].split(b"\0", 1)[0].decode("ascii")


def spell_effects(path):
    data = path.read_bytes()
    assert data[:8] == b"SPL V1  "
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    result = []
    for header_index in range(header_count):
        header = header_offset + 0x28 * header_index
        effect_count = struct.unpack_from("<H", data, header + 0x1E)[0]
        first_effect = struct.unpack_from("<H", data, header + 0x20)[0]
        for effect_index in range(effect_count):
            offset = effect_offset + (first_effect + effect_index) * 0x30
            result.append((
                struct.unpack_from("<H", data, offset)[0],
                data[offset + 0x02],
                struct.unpack_from("<I", data, offset + 0x04)[0],
                struct.unpack_from("<I", data, offset + 0x08)[0],
                data[offset + 0x0C],
                resource(data, offset + 0x14),
            ))
    return result


core = spell_effects(spl_path("CIFCORE"))
assert any(effect[0] == 146 and effect[3] == 1 and effect[4] == 1 and effect[5] == "CIFS4" for effect in core), (layout, core)
assert not any(effect[0] == 282 and effect[3] == 9 for effect in core), (layout, core)

soul_whip = {
    "CIFCORE": 1,
    "CIFSW15": 2,
    "CIFSW20": 3,
}
for resref, bonus in soul_whip.items():
    effects = spell_effects(spl_path(resref))
    damage_effects = [effect for effect in effects if effect[0] == 332 and effect[3] == 0]
    assert any(effect[2] == bonus for effect in damage_effects), (layout, resref, damage_effects)
    critical_effects = [effect for effect in effects if effect[0] == 341]
    assert critical_effects == [(341, 1, 0, 0, 9, "CIFCRIT")], (layout, resref, critical_effects)

critical = spell_effects(spl_path("CIFCRIT"))
assert critical == [(326, 2, 0, hostile_row, 1, "CIFGAIN")], (layout, critical)

setter = spell_effects(spl_path("CIFS4"))
removals = [effect for effect in setter if effect[0] == 321]
state = [effect for effect in setter if effect[0] == 282]
assert len(removals) == 35, (layout, len(removals))
assert {effect[5] for effect in removals} == {f"CIFS{index}" for index in range(35)}, (layout, removals)
assert state == [(282, 1, 4, 9, 9, "CIFOCUS")], (layout, state)

borrowed = [effect for effect in spell_effects(spl_path("CI5BINS")) if effect[0] == 54]
assert any(effect[1] == 2 and effect[2] == 3 for effect in borrowed), (layout, borrowed)
assert any(effect[1] == 9 and effect[2] == 0xFFFFFFFD for effect in borrowed), (layout, borrowed)

time_parasite = [effect for effect in spell_effects(spl_path("CI7TPAR")) if effect[0] == 54]
assert any(effect[1] == 9 and effect[2] == 0xFFFFFFFC for effect in time_parasite), (layout, time_parasite)

reaping_effects = spell_effects(spl_path("CI8RKNI"))
reaping_thac0 = [effect for effect in reaping_effects if effect[0] == 54]
assert any(effect[1] == 2 and effect[2] == 0xFFFFFFFE for effect in reaping_thac0), (layout, reaping_thac0)
reaping_damage = [effect for effect in reaping_effects if effect[0] == 332 and effect[3] == 0]
assert any(effect[1] == 2 and effect[2] == 3 for effect in reaping_damage), (layout, reaping_damage)


def header_effects(path):
    data = path.read_bytes()
    assert data[:8] == b"ITM V1  "
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    result = []
    for header_index in range(header_count):
        header = header_offset + 0x38 * header_index
        attack_type = data[header]
        location = data[header + 0x02]
        effect_count = struct.unpack_from("<H", data, header + 0x1E)[0]
        first_effect = struct.unpack_from("<H", data, header + 0x20)[0]
        effects = []
        for effect_index in range(effect_count):
            offset = effect_offset + (first_effect + effect_index) * 0x30
            effects.append((
                struct.unpack_from("<H", data, offset)[0],
                data[offset + 0x02],
                struct.unpack_from("<I", data, offset + 0x04)[0],
                struct.unpack_from("<I", data, offset + 0x08)[0],
                data[offset + 0x0C],
                resource(data, offset + 0x14),
            ))
        result.append((attack_type, location, effects))
    return result


hit = header_effects(override / "CIFHIT.ITM")
assert len(hit) == 2, (layout, hit)
for attack_type, location, effects in hit:
    assert attack_type in (1, 2)
    assert location == 1
    assert effects == [(326, 2, 0, hostile_row, 1, "CIFGAIN")], (layout, attack_type, effects)

assert header_effects(override / "CIFBOW.ITM") == [(4, 1, [])], layout
assert header_effects(override / "CIFMWEAP.ITM") == [(3, 1, [(326, 2, 0, hostile_row, 1, "CIFGAIN")])]
assert header_effects(override / "CIFMAGIC.ITM") == [(3, 3, [])]
