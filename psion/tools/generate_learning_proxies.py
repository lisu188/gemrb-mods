#!/usr/bin/env python3
"""Build harmless PXL* selector proxies for Psion power learning."""
from __future__ import annotations
from pathlib import Path
import argparse
import shutil
import struct


def rows(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0].strip().upper() != "2DA V1.0":
        raise ValueError(f"not a 2DA table: {path}")
    result = []
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
  continue
        fields = stripped.split()
        if len(fields) < 3:
  raise ValueError(f"malformed PSPICK row: {line}")
        result.append((fields[0].upper(), fields[1].upper()))
    return result


def neutralize(source: bytes) -> bytes:
    data = bytearray(source)
    if len(data) < 0x72 or bytes(data[:8]) != b"SPL V1  ":
        raise ValueError("expected an SPL V1 resource")
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    if header_count < 1 or header_offset + 0x28 > len(data):
        raise ValueError("learning proxy source has no complete ability")
    # Keep the first ability solely for its icon, but make it an immediate
    # self-targeted, zero-effect action. Old headers/effects remain inert
    # trailing bytes because both live counts are reduced to one/zero.
    struct.pack_into("<H", data, 0x68, 1)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 0)
    header = header_offset
    data[header + 0x02] = 4
    data[header + 0x0C] = 5
    data[header + 0x0D] = 0
    struct.pack_into("<H", data, header + 0x0E, 0x7FFF)
    struct.pack_into("<H", data, header + 0x10, 1)
    struct.pack_into("<I", data, header + 0x12, 0)
    struct.pack_into("<H", data, header + 0x1E, 0)
    struct.pack_into("<H", data, header + 0x20, 0)
    struct.pack_into("<H", data, header + 0x26, 1)
    return bytes(data)


def build(override: Path, output: Path, pick: Path) -> int:
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    seen = set()
    count = 0
    for power, proxy in rows(pick):
        if proxy in seen:
  raise ValueError(f"duplicate learning proxy: {proxy}")
        seen.add(proxy)
        source = override / f"{power}.SPL"
        if not source.exists():
  source = override / f"{power}.spl"
        if not source.exists():
  raise FileNotFoundError(f"missing Psion power {power}.SPL")
        (output / f"{proxy}.spl").write_bytes(neutralize(source.read_bytes()))
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--override", type=Path, default=Path("override"))
    parser.add_argument("--output", type=Path, default=Path(".psion-learn-build"))
    parser.add_argument("--pick", type=Path, default=Path("psion/tables/pspick.2da"))
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.cleanup:
        shutil.rmtree(args.output, ignore_errors=True)
        return
    print(f"Generated {build(args.override, args.output, args.pick)} Psion learning proxies")


if __name__ == "__main__":
    main()
