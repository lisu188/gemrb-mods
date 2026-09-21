#!/usr/bin/env python3
"""Build original, self-contained psicrystal animation and creature resources."""
from pathlib import Path
import argparse
import struct
import shutil

FILES = ("PSCRANI.BAM", "PSCRBODY.CRE", "avatars.2da")
COLUMNS = ("AT_1", "AT_2", "AT_3", "AT_4", "TYPE", "SPACE", "PALETTE", "SIZE")


def avatar_table(text):
    rows = [line.split("//", 1)[0].split() for line in text.splitlines()]
    rows = [row for row in rows if row and not row[0].startswith("#")]
    if len(rows) < 3 or rows[0] != ["2DA", "V1.0"] or tuple(rows[2]) != COLUMNS:
        raise ValueError("Unsupported AVATARS.2DA schema")
    used = set()
    own = []
    for row in rows[3:]:
        if len(row) != 9:
            raise ValueError("Malformed AVATARS.2DA row")
        number = int(row[0], 0)
        if number in used:
            raise ValueError("Duplicate animation ID")
        used.add(number)
        if any(value.upper() == "PSCRANI" for value in row[1:5]):
            if [v.upper() for v in row[1:]] != ["PSCRANI"] * 4 + ["1", "1", "1", "*"]:
                raise ValueError("PSCRANI is already owned by another animation")
            own.append(number)
    if len(own) > 1:
        raise ValueError("Multiple psicrystal animation IDs")
    if own:
        return own[0], text
    animation = next((value for value in range(0xF000, 0xFFFF) if value not in used), None)
    if animation is None:
        raise ValueError("No free psicrystal animation ID")
    return animation, text.rstrip("\r\n") + f"\n0x{animation:04x} PSCRANI PSCRANI PSCRANI PSCRANI 1 1 1 *\n"


def crystal_frame(index):
    width, height = 32, 40
    pixels = bytearray(width * height)
    bob = (0, -1, -2, -1)[index % 4]
    for y in range(height):
        for x in range(width):
            if ((x - 16) / 10) ** 2 + ((y - 34) / 3) ** 2 <= 1:
                pixels[y * width + x] = 1
            cy = y - (17 + bob)
            dx = x - 16
            if abs(dx) / 10 + abs(cy) / 15 <= 1:
                color = 2 if dx < 0 else 3
                if cy < -abs(dx):
                    color = 4
                if abs(dx) / 10 + abs(cy) / 15 > 0.86:
                    color = 5
                if abs(dx) < 1.1:
                    color = 6
                pixels[y * width + x] = color
    if index == 4:
        pixels = bytearray(width * height)
        for y in range(28, 35):
            for x in range(7, 26):
                if abs(x - 16) + 2 * abs(y - 31) < 11:
                    pixels[y * width + x] = 2 + ((x + y) % 4)
    return pixels


def animation_bytes():
    frames, cycles, width, height = 5, 80, 32, 40
    frame_offset = 0x18
    cycle_offset = frame_offset + frames * 12
    palette_offset = cycle_offset + cycles * 4
    lookup_offset = palette_offset + 1024
    lookup = []
    cycle_rows = []
    for cycle in range(cycles):
        sequence = [4] if cycle >= 64 else [0, 1, 2, 3]
        cycle_rows.append((len(sequence), len(lookup)))
        lookup.extend(sequence)
    pixel_offset = lookup_offset + len(lookup) * 2
    data = bytearray(pixel_offset + frames * width * height)
    data[:8] = b"BAM V1  "
    struct.pack_into("<HBBIII", data, 8, frames, cycles, 0, frame_offset, palette_offset, lookup_offset)
    palette = ((0, 255, 0), (24, 24, 35), (35, 110, 170), (40, 185, 215),
               (125, 225, 245), (15, 65, 120), (205, 250, 255))
    for i, (red, green, blue) in enumerate(palette):
        data[palette_offset + i * 4:palette_offset + i * 4 + 4] = bytes((blue, green, red, 0))
    for i, row in enumerate(cycle_rows):
        struct.pack_into("<HH", data, cycle_offset + 4 * i, *row)
    struct.pack_into(f"<{len(lookup)}H", data, lookup_offset, *lookup)
    for i in range(frames):
        offset = pixel_offset + i * width * height
        struct.pack_into("<HHhhI", data, frame_offset + i * 12, width, height, 16, 34, offset | 0x80000000)
        data[offset:offset + width * height] = crystal_frame(i)
    return data


def creature_bytes(animation):
    header, slots = 0x2D4, 40
    data = bytearray(header + slots * 2)
    data[:8] = b"CRE V1.0"
    struct.pack_into("<II", data, 8, 0xFFFFFFFF, 0xFFFFFFFF)
    struct.pack_into("<HHI", data, 0x24, 1, 1, animation)
    struct.pack_into("<hh", data, 0x46, 4, 4)
    data[0x52] = 20
    data[0x54:0x59] = bytes([14] * 5)
    for offset in range(0xA4, 0x234, 4):
        struct.pack_into("<I", data, offset, 0xFFFFFFFF)
    data[0x234:0x243] = bytes((1, 0, 0, 0, 1, 0, 6, 10, 15, 10, 6, 10, 0, 0, 0))
    data[0x248:0x250] = b"PSCRAI\x00\x00"
    data[0x270:0x27C] = bytes((5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x22))
    data[0x280:0x288] = b"PSCRBODY"
    for offset in (0x2A0, 0x2A8, 0x2B0, 0x2B8, 0x2BC, 0x2C4):
        struct.pack_into("<I", data, offset, header)
    data[header:] = b"\xff\xff" * slots
    struct.pack_into("<H", data, header + 78, 0)
    return data


def generate(avatars, output):
    animation, text = avatar_table(Path(avatars).read_text(encoding="ascii"))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(path.name not in FILES for path in output.iterdir()):
        raise ValueError("Psicrystal build directory contains unrelated files")
    (output / "avatars.2da").write_text(text, encoding="ascii")
    (output / "PSCRANI.BAM").write_bytes(animation_bytes())
    (output / "PSCRBODY.CRE").write_bytes(creature_bytes(animation))
    return animation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatars", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.cleanup:
        if args.output.is_dir():
            if any(path.name not in FILES or not path.is_file() for path in args.output.iterdir()):
                raise SystemExit("Refusing to remove unrelated build files")
            shutil.rmtree(args.output)
    elif args.avatars:
        print(f"Psicrystal animation: 0x{generate(args.avatars, args.output):04x}")
    else:
        parser.error("--avatars is required when building")


if __name__ == "__main__":
    main()
