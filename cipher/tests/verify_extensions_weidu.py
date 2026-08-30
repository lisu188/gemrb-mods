#!/usr/bin/env python3
from pathlib import Path
import argparse
import struct


def casefold_path(folder: Path, name: str) -> Path | None:
    exact = folder / name
    if exact.exists():
        return exact
    matches = [path for path in folder.iterdir() if path.name.lower() == name.lower()]
    return matches[0] if len(matches) == 1 else None


def spl_effects(path: Path):
    data = path.read_bytes()
    assert data[:8] == b"SPL V1  ", path
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    effects = []
    seen = set()
    for header_index in range(header_count):
        header = header_offset + header_index * 0x28
        count = struct.unpack_from("<H", data, header + 0x1E)[0]
        first = struct.unpack_from("<H", data, header + 0x20)[0]
        for index in range(first, first + count):
            if index in seen:
                continue
            seen.add(index)
            offset = effect_offset + index * 0x30
            effects.append({
                "opcode": struct.unpack_from("<H", data, offset)[0],
                "target": data[offset + 0x02],
                "power": data[offset + 0x03],
                "parameter1": struct.unpack_from("<I", data, offset + 0x04)[0],
                "parameter2": struct.unpack_from("<I", data, offset + 0x08)[0],
                "timing": data[offset + 0x0C],
                "resist": data[offset + 0x0D],
                "duration": struct.unpack_from("<I", data, offset + 0x0E)[0],
                "resource": data[offset + 0x14:offset + 0x1C].rstrip(b"\0").decode("ascii").upper(),
            })
    return effects


def verify_installed(override: Path):
    hit = casefold_path(override, "CIRKHIT.EFF")
    assert hit, "CIRKHIT.EFF"
    data = hit.read_bytes()
    assert data[:8] == b"EFF V2.0", data[:8]
    assert struct.unpack_from("<I", data, 0x10)[0] == 326
    assert struct.unpack_from("<I", data, 0x14)[0] == 2
    hostile_row = struct.unpack_from("<I", data, 0x20)[0]
    assert hostile_row > 0
    assert struct.unpack_from("<H", data, 0x24)[0] == 1
    assert struct.unpack_from("<H", data, 0x2C)[0] == 100
    assert data[0x30:0x38].rstrip(b"\0").decode("ascii").upper() == "CIRKGAIN"
    assert struct.unpack_from("<I", data, 0x5C)[0] == 2

    gain = casefold_path(override, "CIRKGAIN.SPL")
    assert gain
    gain_effects = spl_effects(gain)
    assert any(
        effect["opcode"] == 326
        and effect["target"] == 9
        and effect["resource"] == "CIFSTEP"
        for effect in gain_effects
    ), gain_effects

    knives = casefold_path(override, "CI8RKNI.SPL")
    assert knives
    knife_effects = spl_effects(knives)
    for opcode in (248, 249):
        assert any(
            effect["opcode"] == opcode
            and effect["target"] == 2
            and effect["timing"] == 0
            and effect["duration"] == 30
            and effect["resource"] == "CIRKHIT"
            for effect in knife_effects
        ), (opcode, knife_effects)

    for name in ("CISUBSEL.SPL", "CISBSBLD.SPL", "CISBPASS.SPL", "CISBANN.SPL", "cisubpck.2da"):
        assert casefold_path(override, name), name

    passive = spl_effects(casefold_path(override, "CISBPASS.SPL"))
    assert any(effect["opcode"] == 284 for effect in passive), passive
    assert any(effect["opcode"] == 0 and effect["parameter1"] == 1 for effect in passive), passive
    annihilation = spl_effects(casefold_path(override, "CISBANN.SPL"))
    assert any(
        effect["opcode"] == 285
        and effect["parameter1"] == 125
        and effect["parameter2"] == 2
        and effect["duration"] == 6
        for effect in annihilation
    ), annihilation


def verify_uninstalled(override: Path):
    for name in (
        "CIRKHIT.EFF",
        "CIRKGAIN.SPL",
        "CISUBSEL.SPL",
        "CISBSBLD.SPL",
        "CISBPASS.SPL",
        "CISBANN.SPL",
        "cisubpck.2da",
    ):
        assert casefold_path(override, name) is None, name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    parser.add_argument("--uninstalled", action="store_true")
    args = parser.parse_args()
    override = args.game / "override"
    if args.uninstalled:
        verify_uninstalled(override)
        print("Cipher extension resources removed cleanly")
    else:
        verify_installed(override)
        print("Cipher Reaping Knives and subclass resources validated")


if __name__ == "__main__":
    main()
