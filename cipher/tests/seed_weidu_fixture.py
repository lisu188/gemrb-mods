#!/usr/bin/env python3
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
override = root / "override"

dmgtype = override / "dmgtype.ids"
text = dmgtype.read_text(encoding="ascii")
for value, symbol in ((3, "FIRE"), (4, "CRUSHING")):
    if symbol not in text:
        text += f"0x{value:04x} {symbol}\n"
dmgtype.write_text(text, encoding="ascii")


def write_item(path, abilities):
    header_offset = 0x72
    effect_offset = header_offset + 0x38 * len(abilities)
    data = bytearray(effect_offset)
    data[:8] = b"ITM V1  "
    struct.pack_into("<H", data, 0x1C, 19)
    struct.pack_into("<I", data, 0x64, header_offset)
    struct.pack_into("<H", data, 0x68, len(abilities))
    struct.pack_into("<I", data, 0x6A, effect_offset)
    for index, (attack_type, location) in enumerate(abilities):
        header = header_offset + 0x38 * index
        data[header] = attack_type
        data[header + 0x02] = location
    path.write_bytes(data)


write_item(override / "CIFHIT.ITM", ((1, 1), (2, 1)))
write_item(override / "CIFMWEAP.ITM", ((3, 1),))
write_item(override / "CIFMAGIC.ITM", ((3, 3),))
