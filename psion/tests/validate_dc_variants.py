#!/usr/bin/env python3
"""Validate exact-Intelligence Psion save-DC variant generation."""
from pathlib import Path
import importlib.util
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "generate_dc_variants", ROOT / "psion/tools/generate_dc_variants.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def make_spl(save_bonus=-2, save_type=1):
    # One extended header and one feature block.
    data = bytearray(0x72 + 0x28 + 0x30)
    data[:8] = b"SPL V1  "
    struct.pack_into("<I", data, 0x64, 0x72)
    struct.pack_into("<H", data, 0x68, 1)
    struct.pack_into("<I", data, 0x6A, 0x72 + 0x28)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 0)
    struct.pack_into("<H", data, 0x72 + 0x1E, 1)
    struct.pack_into("<H", data, 0x72 + 0x20, 0)
    effect = 0x72 + 0x28
    struct.pack_into("<H", data, effect, 12)
    struct.pack_into("<I", data, effect + 0x24, save_type)
    struct.pack_into("<i", data, effect + 0x28, save_bonus)
    return bytes(data)


def save_bonus(data):
    return struct.unpack_from("<i", data, 0x72 + 0x28 + 0x28)[0]


def main():
    baseline = make_spl(-2, 1)
    assert MOD.save_effect_offsets(baseline) == [0x72 + 0x28]
    # Authored +2 baseline: INT 10 (modifier 0) is two DC lower, represented by
    # a save bonus two points less favorable to the caster (-2 -> 0).
    assert save_bonus(MOD.adjusted_variant(baseline, 0)) == 0
    # INT 20 (modifier +5) is three DC higher (-2 -> -5).
    assert save_bonus(MOD.adjusted_variant(baseline, 5)) == -5

    flag_only = make_spl(-2, 1 << 10)
    assert MOD.save_effect_offsets(flag_only) == []

    assert MOD.variant_resref("PS1MTHR", -5) == "PS1MTHRV"
    assert MOD.variant_resref("PSMT20", 7) == "PSMT207"
    assert MOD.variant_resref("PS1MTHR", 2) == "PS1MTHR"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        override = root / "override"
        output = root / "generated"
        override.mkdir()
        (override / "PS1MTHR.spl").write_bytes(baseline)
        (override / "PSNOSEV.spl").write_bytes(make_spl(-2, 0))
        powers = root / "powers.2da"
        powers.write_text(
            "2DA V1.0\n*\n NAME LEVEL\nPS1MTHR MIND 1\nPSNOSEV NONE 1\n",
            encoding="utf-8",
        )
        augments = root / "augment.2da"
        augments.write_text("2DA V1.0\n*\n PARENT\n", encoding="utf-8")
        sources, variants = MOD.build(override, output, powers, augments)
        assert sources == 1
        assert variants == len(MOD.MODIFIER_SUFFIXES)
        assert (output / "PS1MTHR5.spl").exists()
        assert not (output / "PSNOSEV5.spl").exists()

    print("Psion exact Intelligence save-DC variants validated")


if __name__ == "__main__":
    main()
