#!/usr/bin/env python3
"""Verify installed/uninstalled Cipher power-learning resources in a WeiDU fixture."""
from pathlib import Path
import argparse
import struct

SELECTOR_SAFE_FLAGS = (1 << 14) | (1 << 25)


def casefold_path(folder: Path, name: str) -> Path | None:
    exact = folder / name
    if exact.exists():
        return exact
    matches = [path for path in folder.iterdir() if path.name.lower() == name.lower()]
    return matches[0] if len(matches) == 1 else None


def read_2da(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(lines) >= 3 and lines[0].strip().upper() == "2DA V1.0", path
    header = lines[2].split()
    rows = []
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        rows.append(stripped.split())
    return header, rows


def verify_proxy(real: Path, proxy: Path):
    source = real.read_bytes()
    data = proxy.read_bytes()
    assert data[:8] == b"SPL V1  ", proxy
    assert data[:0x18] == source[:0x18], proxy
    assert data[0x1C:0x64] == source[0x1C:0x64], proxy
    assert struct.unpack_from("<I", data, 0x18)[0] == SELECTOR_SAFE_FLAGS, proxy
    header = struct.unpack_from("<I", data, 0x64)[0]
    assert struct.unpack_from("<H", data, 0x68)[0] == 1, proxy
    assert struct.unpack_from("<H", data, 0x70)[0] == 0, proxy
    assert data[header + 0x0C] == 5, proxy
    assert struct.unpack_from("<H", data, header + 0x1E)[0] == 0, proxy
    source_header = struct.unpack_from("<I", source, 0x64)[0]
    assert data[header + 0x04:header + 0x0C] == source[source_header + 0x04:source_header + 0x0C], proxy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    parser.add_argument("--uninstalled", action="store_true")
    args = parser.parse_args()
    override = args.game / "override"

    names = ["CILRN.spl"] + [f"CIL{index:04d}.spl" for index in range(1, 19)]
    if args.uninstalled:
        for name in names:
            assert casefold_path(override, name) is None, name
        assert casefold_path(override, "cipherknown.2da") is None
        assert casefold_path(override, "cipick.2da") is None
        print("Cipher power-learning resources removed cleanly")
        return

    known_path = casefold_path(override, "cipherknown.2da")
    pick_path = casefold_path(override, "cipick.2da")
    selector = casefold_path(override, "CILRN.spl")
    assert known_path and pick_path and selector
    known_header, known_rows = read_2da(known_path)
    assert known_header == ["KNOWN", "MAX_TIER"]
    assert len(known_rows) == 30
    assert known_rows[0] == ["1", "1", "1"]
    assert known_rows[18] == ["19", "9", "9"]

    pick_header, picks = read_2da(pick_path)
    assert pick_header == ["ResRef", "Type"]
    assert len(picks) == 18
    for power, proxy, kind in picks:
        assert kind == "3"
        real = casefold_path(override, f"{power}.spl")
        generated = casefold_path(override, f"{proxy}.spl")
        assert real and generated, (power, proxy)
        verify_proxy(real, generated)

    print("Cipher installed power-learning resources validated")


if __name__ == "__main__":
    main()
