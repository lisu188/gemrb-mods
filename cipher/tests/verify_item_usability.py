#!/usr/bin/env python3
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
override = root / "override"

class_id = None
for line in (override / "class.ids").read_text(encoding="utf-8", errors="replace").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1] == "CIPHER":
        class_id = int(fields[0], 0)
        break
assert class_id is not None


def restrictions(path):
    data = path.read_bytes()
    assert data[:8] == b"ITM V1  ", path
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    first = struct.unpack_from("<H", data, 0x6E)[0]
    count = struct.unpack_from("<H", data, 0x70)[0]
    result = []
    for index in range(count):
        offset = effect_offset + (first + index) * 0x30
        opcode = struct.unpack_from("<H", data, offset)[0]
        target = data[offset + 0x02]
        parameter1 = struct.unpack_from("<I", data, offset + 0x04)[0]
        parameter2 = struct.unpack_from("<I", data, offset + 0x08)[0]
        timing = data[offset + 0x0C]
        if (opcode, target, parameter1, parameter2, timing) == (319, 2, class_id, 5, 2):
            result.append(index)
    return result


assert restrictions(override / "CIFLEATH.ITM") == []
assert restrictions(override / "CIFROBE.ITM") == []
assert restrictions(override / "CIFCHAIN.ITM") == [0]
assert restrictions(override / "CIFSHLD.ITM") == [0]

print("Cipher light-armor/no-shield usability validation passed")
