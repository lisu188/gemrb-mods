#!/usr/bin/env python3
"""Real WeiDU icon resolution and failure gates using original synthetic assets."""
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def spell(book, memorized):
    data = bytearray(0x9a)
    data[:8] = b"SPL V1  "
    data[0x3a:0x42] = book.encode().ljust(8, b"\0")
    struct.pack_into("<IHI", data, 0x64, 0x72, 1, 0x9a)
    data[0x76:0x7e] = memorized.encode().ljust(8, b"\0")
    return data


def icons(path):
    data = path.read_bytes()
    offset = struct.unpack_from("<I", data, 0x64)[0]
    return tuple(data[start:start + 8].split(b"\0", 1)[0].decode().lower()
                 for start in (0x3a, offset + 4))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_spell_icons_weidu.py WEIDU GEMRB_ROOT")
    spec = importlib.util.spec_from_file_location("icon_fixture", ROOT / "psion/tests/make_weidu_fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix="gemrb-spell-icons-") as temporary:
        game = Path(temporary) / "game"
        fixture.build_fixture(Path(sys.argv[2]).resolve(), game, "normalized")
        shutil.copytree(ROOT / "common", game / "common")
        override = game / "override"
        for name in ("directb", "directc", "actualb", "actualc"):
            fixture.write_icon_fixture(override / (name + ".bam"))
        # Exact native failure shape: SPPR115 does not own SPPR115B/C BAMs.
        native = override / "sppr115.spl"
        native.write_bytes(spell("actualc", "actualb"))
        native_before = native.read_bytes()
        (override / "broken.spl").write_bytes(spell("missingc", "missingb"))
        cases = {"ZZIC1": "direct", "ZZIC2": "sppr115", "ZZIC3": "absent", "ZZIC4": "broken"}
        tp2 = ["BACKUP ~icon-backup~", "AUTHOR ~acceptance~", "AUTO_EVAL_STRINGS", "BEGIN ~Synthetic icon regression~",
               "INCLUDE ~common/weidu/spell-functions.tpa~"]
        for name, base in cases.items():
            tp2.append(f"""CREATE ~spl~ ~{name}~
COPY_EXISTING ~{name}.spl~ ~override~
  WRITE_ASCII 0x3a ~{base}c~ #8
  LPF ADD_SPELL_HEADER STR_VAR icon = ~{base}b~ END
  LPF ADD_SPELL_EFFECT INT_VAR opcode = 10 target = 1 parameter1 = 7 END
BUT_ONLY""")
        tp2.append("""CREATE ~spl~ ~ZZIC5~
COPY_EXISTING ~ZZIC5.spl~ ~override~
  LPF ADD_SPELL_HEADER END
BUT_ONLY""")
        (game / "icons.tp2").write_text("\n".join(tp2) + "\n")

        def run(operation, success=True):
            result = subprocess.run([sys.argv[1], "icons.tp2", "--use-lang", "en_US", operation, "0", "--no-exit-pause"],
                                    cwd=game, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if success and result.returncode:
                raise AssertionError(result.stdout)
            if not success:
                assert result.returncode, result.stdout
                assert "Missing spell icon" in result.stdout, result.stdout
            return result.stdout

        installed_log = run("--force-install")
        expected = {"ZZIC1": ("directc", "directb"), "ZZIC2": ("actualc", "actualb"),
                    "ZZIC3": ("spwi112c", "spwi112b"), "ZZIC4": ("spwi112c", "spwi112b"),
                    "ZZIC5": ("", "")}
        for name, pair in expected.items():
            path = override / (name + ".spl")
            assert icons(path) == pair, (name, icons(path), pair, installed_log)
            if name != "ZZIC5":
                data = path.read_bytes()
                offset = struct.unpack_from("<I", data, 0x6a)[0]
                assert struct.unpack_from("<H", data, offset)[0] == 10
                assert struct.unpack_from("<I", data, offset + 4)[0] == 7
        assert native.read_bytes() == native_before, "native template was modified"
        run("--force-uninstall")
        assert not any((override / (name + ".spl")).exists() for name in expected)
        assert native.read_bytes() == native_before
        # Each fallback field must be available; neither missing BAM may be hidden.
        for missing in ("spwi112b", "spwi112c"):
            path = override / (missing + ".bam")
            path.unlink()
            run("--force-install", success=False)
            fixture.write_icon_fixture(path)
    print("WeiDU icons: existing/native/fallback/empty, preserved effects/templates, uninstall and missing-BAM failure gates passed")


if __name__ == "__main__":
    main()
