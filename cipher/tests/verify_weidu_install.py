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


class_ids = {}
for line in (override / "class.ids").read_text(encoding="utf-8").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1] == "CIPHER":
        class_ids[fields[1]] = int(fields[0], 0)
assert set(class_ids) == {"CIPHER"}, (layout, class_ids)
assert 0 <= class_ids["CIPHER"] <= 255

for filename in ("classes.2da", "alignmnt.2da", "abclasrq.2da", "profs.2da", "xplevel.2da", "thac0.2da", "lore.2da", "xpcap.2da", "clskills.2da"):
    assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)

if layout != "legacy":
    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):
        assert "CIPHER" in (override / filename).read_text(encoding="utf-8", errors="replace"), (layout, filename)
    _, hpclass = rows(override / "hpclass.2da")
    assert hpclass["CIPHER"] == ["HPPRS"], (layout, hpclass["CIPHER"])

_, clskills = rows(override / "clskills.2da")
assert clskills["CIPHER"][2] == "MXCIPHER", (layout, clskills["CIPHER"])

_, ability = rows(override / "abclasrq.2da")
assert ability["CIPHER"] == ["0", "0", "0", "13", "0", "0"], (layout, ability["CIPHER"])

_, profs = rows(override / "profs.2da")
assert profs["CIPHER"] == ["2", "4"], (layout, profs["CIPHER"])

_, xp = rows(override / "xplevel.2da")
assert xp["CIPHER"] == xp["MAGE"], (layout, xp["CIPHER"], xp["MAGE"])

for resref in ("CIFCORE", "CIFSW15", "CIFSW20", "CI1WHSP", "CI9SCOL", "CIFGAIN", "CIFSTEP", "CIFS34"):
    assert (override / f"{resref}.SPL").is_file(), (layout, resref)


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
        effect_count = struct.unpack_from("<H", data, header + 0x1E)[0]
        first_effect = struct.unpack_from("<H", data, header + 0x20)[0]
        effects = []
        for effect_index in range(effect_count):
            offset = effect_offset + (first_effect + effect_index) * 0x30
            effects.append((
                struct.unpack_from("<H", data, offset)[0],
                data[offset + 0x02],
                struct.unpack_from("<I", data, offset + 0x08)[0],
                data[offset + 0x0C],
                data[offset + 0x14:offset + 0x1C].split(b"\0", 1)[0].decode("ascii"),
            ))
        result.append((attack_type, effects))
    return result


hit = header_effects(override / "CIFHIT.ITM")
assert len(hit) == 2, (layout, hit)
for attack_type, effects in hit:
    assert attack_type in (1, 2)
    assert effects == [(146, 9, 1, 1, "CIFGAIN")], (layout, attack_type, effects)

assert header_effects(override / "CIFMAGIC.ITM") == [(3, [])]
