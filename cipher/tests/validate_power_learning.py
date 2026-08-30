#!/usr/bin/env python3
"""Validate Cipher selectable-power proxy generation."""
from pathlib import Path
import importlib.util
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cipher_learnproxy", ROOT / "tools/generate_learning_proxies.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_spl():
    data = bytearray(0x72 + 0x28 + 0x30)
    data[:8] = b"SPL V1  "
    struct.pack_into("<I", data, 0x64, 0x72)
    struct.pack_into("<H", data, 0x68, 1)
    struct.pack_into("<I", data, 0x6A, 0x72 + 0x28)
    struct.pack_into("<H", data, 0x70, 1)
    data[0x72 + 0x04:0x72 + 0x0C] = b"SPWI105B"
    struct.pack_into("<H", data, 0x72 + 0x1E, 1)
    return bytes(data)


def main():
    picks = mod.rows(ROOT / "tables/cipick.2da")
    assert len(picks) == 18
    assert len({proxy for _, proxy in picks}) == 18
    assert picks[0] == ("CI1WHSP", "CIL0001")
    assert picks[-1] == ("CI9SCOL", "CIL0018")

    source = fake_spl()
    proxy = mod.neutralize(source)
    assert proxy[:0x64] == source[:0x64]
    assert struct.unpack_from("<H", proxy, 0x68)[0] == 1
    assert struct.unpack_from("<H", proxy, 0x70)[0] == 0
    header = struct.unpack_from("<I", proxy, 0x64)[0]
    assert proxy[header + 0x04:header + 0x0C] == b"SPWI105B"
    assert proxy[header + 0x0C] == 5
    assert struct.unpack_from("<H", proxy, header + 0x1E)[0] == 0

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        override = base / "override"
        output = base / "out"
        override.mkdir()
        (override / "CI1WHSP.spl").write_bytes(source)
        pick = base / "pick.2da"
        pick.write_text(
            "2DA V1.0\n****\n         ResRef Type\nCI1WHSP CIL0001 3\n",
            encoding="utf-8",
        )
        assert mod.build(override, output, pick) == 1
        assert (output / "CIL0001.spl").exists()

    print("Cipher selectable-power proxy validation passed")


if __name__ == "__main__":
    main()
