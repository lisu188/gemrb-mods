#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import struct
import sys


def read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def features(path: Path) -> list[dict[str, int | str]]:
    data = path.read_bytes()
    assert data[:8] == b"SPL V1  ", path
    header_offset = read_u32(data, 0x64)
    header_count = read_u16(data, 0x68)
    effect_offset = read_u32(data, 0x6A)
    assert header_count >= 1, path
    first = read_u16(data, header_offset + 0x20)
    count = read_u16(data, header_offset + 0x1E)
    result = []
    for index in range(first, first + count):
        base = effect_offset + index * 0x30
        result.append({
            "opcode": read_u16(data, base),
            "target": data[base + 0x02],
            "power": data[base + 0x03],
            "parameter1": read_u32(data, base + 0x04),
            "parameter2": read_u32(data, base + 0x08),
            "timing": data[base + 0x0C],
            "duration": read_u32(data, base + 0x0E),
            "resource": data[base + 0x14:base + 0x1C].split(b"\0", 1)[0].decode("ascii").upper(),
            "dice": read_u32(data, base + 0x1C),
            "sides": read_u32(data, base + 0x20),
            "save": read_u32(data, base + 0x24),
            "special": read_u32(data, base + 0x2C),
        })
    return result


def locate(override: Path, resref: str) -> Path:
    for suffix in (".SPL", ".spl"):
        path = override / f"{resref}{suffix}"
        if path.exists():
            return path
    raise AssertionError(f"missing {resref}.SPL")


def verify_detonate(override: Path) -> None:
    effects = features(locate(override, "CI5DETN"))
    watcher = effects[0]
    assert watcher == {
        **watcher,
        "opcode": 232,
        "target": 2,
        "parameter1": 0,
        "parameter2": 16,
        "timing": 0,
        "duration": 1,
        "resource": "CI5DBST",
        "special": 6,
    }
    assert any(effect["opcode"] == 12 and effect["dice"] == 8 and effect["sides"] == 6 for effect in effects[1:])

    burst = features(locate(override, "CI5DBST"))
    assert len(burst) == 1
    assert burst[0]["opcode"] == 12
    assert burst[0]["target"] == 2
    assert burst[0]["dice"] == 8
    assert burst[0]["sides"] == 6


def verify_amplified_wave(override: Path) -> None:
    effects = features(locate(override, "CI6AWAV"))
    assert any(effect["opcode"] == 12 and effect["dice"] == 8 and effect["sides"] == 6 for effect in effects)
    assert not any(effect["opcode"] == 175 for effect in effects)
    prone = [effect for effect in effects if effect["opcode"] == 39]
    assert len(prone) == 1
    assert prone[0]["target"] == 2
    assert prone[0]["parameter1"] == 0
    assert prone[0]["parameter2"] == 1
    assert prone[0]["timing"] == 0
    assert prone[0]["duration"] == 6
    assert prone[0]["save"] == 2
    assert prone[0]["special"] == 1


def verify_soul_collapse(override: Path) -> None:
    effects = features(locate(override, "CI9SCOL"))
    watcher = effects[0]
    assert watcher == {
        **watcher,
        "opcode": 232,
        "target": 2,
        "parameter1": 0,
        "parameter2": 20,
        "timing": 0,
        "duration": 6,
        "resource": "CI9SDEX",
        "special": 20,
    }
    assert any(effect["opcode"] == 12 and effect["dice"] == 12 and effect["sides"] == 6 for effect in effects[1:])

    execute = features(locate(override, "CI9SDEX"))
    assert len(execute) == 1
    assert execute[0]["opcode"] == 13
    assert execute[0]["target"] == 2
    assert execute[0]["parameter1"] == 1
    assert execute[0]["parameter2"] == 4


def main() -> None:
    game = Path(sys.argv[1])
    override = game / "override"
    verify_detonate(override)
    verify_amplified_wave(override)
    verify_soul_collapse(override)
    print("Cipher high-tier installed-resource validation passed")


if __name__ == "__main__":
    main()
