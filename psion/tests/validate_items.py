#!/usr/bin/env python3
"""Validate generated Psion equipment registry and marker ownership."""
from pathlib import Path
import importlib.util
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[2].split()
    return [dict(zip(["ROW"] + header, line.split())) for line in lines[3:] if line.strip()]


def main():
    registry = rows(ROOT / "tables/psionitems.2da")
    assert len(registry) == 5
    assert {row["MECHANIC"] for row in registry} == {
        "PP_CAPACITY", "SKILL", "FOCUS_SKILL", "SAVE_DC"
    }
    assert all(len(row["RESREF"]) <= 8 and len(row["TAG"]) <= 8 for row in registry)
    assert [row["DISCIPLINE"] for row in registry].count("SHAPER") == 1

    spec = importlib.util.spec_from_file_location(
        "generate_psion_items", ROOT / "tools/generate_items.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="psion-items-") as folder:
        output = Path(folder)
        module.build(output)
        for row in registry:
            data = (output / (row["RESREF"] + ".itm")).read_bytes()
            assert data[:8] == b"ITM V1  "
            assert struct.unpack_from("<H", data, 0x1C)[0] == 10
            offset = struct.unpack_from("<I", data, 0x6A)[0]
            assert struct.unpack_from("<H", data, 0x70)[0] == 1
            assert struct.unpack_from("<H", data, offset)[0] == module.MARKER_OPCODE
            assert data[offset + 0x02] == 2
            assert data[offset + 0x0C] == 2
            tag = data[offset + 0x14:offset + 0x1C].rstrip(b"\0").decode("ascii")
            assert tag == row["TAG"]

    setup = (ROOT / "setup-psion.tp2").read_text(encoding="utf-8")
    assert "psionitems.2da" in setup
    assert "generate_items.py" in setup
    assert "psion/lib/equipment.tpa" in setup
    runtime = (ROOT / "guiscripts/Psionics.py").read_text(encoding="utf-8")
    for row in registry:
        assert row["TAG"] in runtime
    print("5 Psion equipment resources, registry rows and runtime markers validated")


if __name__ == "__main__":
    main()
