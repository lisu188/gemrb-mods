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


def locate(override: Path, resref: str, extension: str = "SPL") -> Path:
    for suffix in (f".{extension.upper()}", f".{extension.lower()}"):
        path = override / f"{resref}{suffix}"
        if path.exists():
            return path
    raise AssertionError(f"missing {resref}.{extension}")


def splprot_rows(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = {}
    index = 0
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        fields = stripped.split()
        rows[fields[0].upper()] = index
        index += 1
    return rows


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


def verify_reaping_knives(override: Path) -> None:
    rows = splprot_rows(locate(override, "SPLPROT", "2DA"))
    for owner in range(1, 7):
        label = f"CIPHER_RK_OWNER_{owner}"
        assert label in rows

        variant = features(locate(override, f"CI8RK{owner}"))
        marker = [effect for effect in variant if effect["opcode"] == 282]
        assert len(marker) == 1
        assert marker[0]["target"] == 9
        assert marker[0]["parameter1"] == owner
        assert marker[0]["parameter2"] == 26
        assert marker[0]["duration"] == 30

        melee = [effect for effect in variant if effect["opcode"] == 248]
        ranged = [effect for effect in variant if effect["opcode"] == 249]
        assert len(melee) == len(ranged) == 1
        assert melee[0]["target"] == ranged[0]["target"] == 2
        assert melee[0]["resource"] == ranged[0]["resource"] == f"CIRKE{owner}"
        assert melee[0]["duration"] == ranged[0]["duration"] == 30

        gain = features(locate(override, f"CIRKG{owner}"))
        assert len(gain) == 1
        assert gain[0]["opcode"] == 326
        assert gain[0]["target"] == 3
        assert gain[0]["parameter2"] == rows[label]
        assert gain[0]["resource"] == "CIFSTEP"

        eff = locate(override, f"CIRKE{owner}", "EFF").read_bytes()
        assert eff[:8] == b"EFF V2.0"
        assert read_u32(eff, 0x10) == 0x92
        assert read_u32(eff, 0x14) == 2
        assert eff[0x30:0x38].split(b"\0", 1)[0].decode("ascii") == f"CIRKG{owner}"


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
    verify_reaping_knives(override)
    verify_soul_collapse(override)
    print("Cipher high-tier installed-resource validation passed")


if __name__ == "__main__":
    main()
