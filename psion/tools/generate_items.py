#!/usr/bin/env python3
"""Generate small Psion equipment ITM resources with runtime marker effects."""
from pathlib import Path
import argparse
import shutil
import struct

ITEMS = {
    "PSIMIND": ("PSIPP10", 2200),
    "PSICNTR": ("PSICNC2", 1200),
    "PSIFOC": ("PSIFOC2", 1800),
    "PSISHP": ("PSISHP3", 2000),
    "PSIDC1": ("PSIDC1", 4500),
}
EFFECT_SIZE = 0x30
HEADER_SIZE = 0x72
MARKER_OPCODE = 206


def item_bytes(tag: str, price: int) -> bytes:
    data = bytearray(HEADER_SIZE + EFFECT_SIZE)
    data[:8] = b"ITM V1  "
    struct.pack_into("<H", data, 0x1C, 10)
    struct.pack_into("<I", data, 0x34, price)
    struct.pack_into("<H", data, 0x38, 1)
    for offset in (0x3A, 0x44, 0x58):
        data[offset:offset + 8] = b"PSCRANI\0"
    struct.pack_into("<I", data, 0x64, HEADER_SIZE)
    struct.pack_into("<H", data, 0x68, 0)
    struct.pack_into("<I", data, 0x6A, HEADER_SIZE)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 1)

    effect = HEADER_SIZE
    struct.pack_into("<H", data, effect, MARKER_OPCODE)
    data[effect + 0x02] = 2
    data[effect + 0x03] = 0
    struct.pack_into("<I", data, effect + 0x04, 0)
    struct.pack_into("<I", data, effect + 0x08, 0)
    data[effect + 0x0C] = 2
    data[effect + 0x14:effect + 0x1C] = tag.encode("ascii").ljust(8, b"\0")
    data[effect + 0x12] = 100
    return bytes(data)


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for resref, (tag, price) in ITEMS.items():
        (output / (resref + ".itm")).write_bytes(item_bytes(tag, price))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".psion-item-build"))
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.cleanup:
        shutil.rmtree(args.output, ignore_errors=True)
        return
    build(args.output)
    print("Generated %d Psion equipment resources" % len(ITEMS))


if __name__ == "__main__":
    main()
