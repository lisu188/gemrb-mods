#!/usr/bin/env python3
"""Build internal Psion SPL variants with exact Intelligence-based save DCs.

Psion powers are authored against the guaranteed INT 15 minimum (+2 modifier).
For BG-family GemRB games MaximumAbility is 25, so the complete runtime range is
INT 0..25 (modifiers -5..+7).  The +2 baseline keeps its public resref; every
other modifier gets an internal one-character-suffix clone when the source SPL
contains at least one real saving-throw effect.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import shutil
import struct

# Public power resrefs are at most seven characters; augmentation children are
# shorter. These suffixes therefore remain valid IE resrefs while being easy to
# reverse in the GemRB runtime.
MODIFIER_SUFFIXES = {
    -5: "V",
    -4: "W",
    -3: "X",
    -2: "Y",
    -1: "Z",
    0: "0",
    1: "1",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
}
BASELINE_MODIFIER = 2
EFFECT_SIZE = 0x30
EXTENDED_HEADER_SIZE = 0x28


def variant_resref(source: str, modifier: int) -> str:
    source = source.upper()
    if modifier == BASELINE_MODIFIER:
        return source
    suffix = MODIFIER_SUFFIXES[modifier]
    if len(source) >= 8:
        raise ValueError(f"Psion DC source resref is too long for a suffix: {source}")
    return source + suffix


def _u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _effect_indices(data: bytes | bytearray) -> list[int]:
    if len(data) < 0x72 or bytes(data[:8]) != b"SPL V1  ":
        raise ValueError("expected an SPL V1 resource")

    header_offset = _u32(data, 0x64)
    header_count = _u16(data, 0x68)
    indices: set[int] = set()

    casting_first = _u16(data, 0x6E)
    casting_count = _u16(data, 0x70)
    indices.update(range(casting_first, casting_first + casting_count))

    for index in range(header_count):
        header = header_offset + index * EXTENDED_HEADER_SIZE
        if header + EXTENDED_HEADER_SIZE > len(data):
            raise ValueError("truncated SPL extended header")
        effect_count = _u16(data, header + 0x1E)
        first_effect = _u16(data, header + 0x20)
        indices.update(range(first_effect, first_effect + effect_count))
    return sorted(indices)


def save_effect_offsets(data: bytes | bytearray) -> list[int]:
    table_offset = _u32(data, 0x6A)
    offsets = []
    for index in _effect_indices(data):
        effect = table_offset + index * EFFECT_SIZE
        if effect + EFFECT_SIZE > len(data):
            raise ValueError("truncated SPL feature block")
        save_type = _u32(data, effect + 0x24)
        # Bits 0..4 are the actual save categories. Higher bits are targeting /
        # EE flags and must not turn a no-save effect into a DC-adjusted one.
        if save_type & 0x1F:
            offsets.append(effect)
    return offsets


def adjusted_variant(source_data: bytes, modifier: int) -> bytes:
    delta = modifier - BASELINE_MODIFIER
    data = bytearray(source_data)
    for effect in save_effect_offsets(data):
        old_bonus = _i32(data, effect + 0x28)
        struct.pack_into("<i", data, effect + 0x28, old_bonus - delta)
    return bytes(data)


def table_resrefs(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or not lines[0].strip().upper().startswith("2DA V1.0"):
        raise ValueError(f"not a 2DA table: {path}")
    refs = []
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue
        row = stripped.split()[0].upper()
        if row not in ("*", "****"):
            refs.append(row)
    return refs


def build(override: Path, output: Path, powers: Path, augments: Path) -> tuple[int, int]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    sources = []
    seen = set()
    for ref in table_resrefs(powers) + table_resrefs(augments):
        if ref not in seen:
            seen.add(ref)
            sources.append(ref)

    variant_names = set()
    source_count = 0
    variant_count = 0
    for source in sources:
        path = override / f"{source}.SPL"
        if not path.exists():
            path = override / f"{source}.spl"
        if not path.exists():
            raise FileNotFoundError(f"missing generated Psion power {source}.SPL")
        source_data = path.read_bytes()
        if not save_effect_offsets(source_data):
            continue
        source_count += 1
        for modifier in MODIFIER_SUFFIXES:
            ref = variant_resref(source, modifier)
            if ref in variant_names or ref in seen:
                raise ValueError(f"Psion DC variant resref collision: {ref}")
            variant_names.add(ref)
            (output / f"{ref}.spl").write_bytes(adjusted_variant(source_data, modifier))
            variant_count += 1
    return source_count, variant_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--override", type=Path, default=Path("override"))
    parser.add_argument("--output", type=Path, default=Path(".psion-dc-build"))
    parser.add_argument("--powers", type=Path, default=Path("psion/tables/psionpowers.2da"))
    parser.add_argument("--augments", type=Path, default=Path("psion/tables/psionaugment.2da"))
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    if args.cleanup:
        shutil.rmtree(args.output, ignore_errors=True)
        return

    sources, variants = build(args.override, args.output, args.powers, args.augments)
    print(f"Generated {variants} exact-DC SPL variants from {sources} save-bearing Psion powers")


if __name__ == "__main__":
    main()
