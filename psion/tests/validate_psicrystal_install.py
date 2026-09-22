#!/usr/bin/env python3
"""Validate real WeiDU companion resources and exact installation restoration."""
from pathlib import Path
import argparse
import importlib.util
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def resource(directory, name):
    matches = [path for path in directory.iterdir() if path.name.casefold() == name.casefold()]
    if len(matches) != 1:
        raise AssertionError((name, matches))
    return matches[0]


def snapshot(directory):
    result = {}
    for path in directory.iterdir():
        if path.is_file():
            key = path.name.casefold()
            if key in result:
                raise AssertionError(f"case-ambiguous resource: {key}")
            result[key] = path.read_bytes()
    return result


def validate(game):
    directory = Path(game) / "override"
    config = resource(directory, "pscrcfg.2da").read_text()
    assert "OWNER_LIMIT 255" in config
    party_slots = int(re.search(r"PARTY_SLOTS (\d+)", config)[1])
    assert 1 <= party_slots <= 32
    trigger_text = resource(directory, "trigger.ids").read_text()
    codes = {}
    for name in ("GlobalLTGlobal", "GlobalGTGlobal"):
        code = int(re.search(r"(?im)^\s*(\S+)\s+" + name + r"\(", trigger_text)[1], 0)
        assert (code & 0x3fff) < 300, (name, code)
        codes[name] = code
    avatars = resource(directory, "avatars.2da").read_text()
    avatar = re.search(r"(?im)^(\S+)\s+PSCRANIM\s+PSCRANIM\s+PSCRANIM\s+PSCRANIM\s+13\s+1\s+1\s+\*\s*$", avatars)
    assert avatar
    animation = int(avatar[1], 0)
    for token in range(1, 256):
        name = f"PSCR{token:03d}"
        body = resource(directory, name + ".cre").read_bytes()
        assert body[:8] == b"CRE V1.0"
        assert struct.unpack_from("<I", body, 0x28)[0] == animation
        assert body[0x248:0x250].rstrip(b"\0") == name.encode()
        assert not any(body[0x250:0x270])
        assert body[0x280:0x2a0].rstrip(b"\0") == name.lower().encode()
        assert struct.unpack_from("<I", body, 0x10)[0] == 0x400002
        assert not any(body[0x14:0x24])
        assert body[0x270] == 5 and body[0x53] == 0 and body[0x273] == 0
        for count in (0x2a4, 0x2b4, 0x2c0, 0x2c8):
            assert struct.unpack_from("<I", body, count)[0] == 0, (name, count)
        script = resource(directory, name + ".bcs").read_text()
        assert script.startswith("SC\n") and script.endswith("SC\n")
        for code in codes.values():
            expected = f'{code} 0 0 0 0 "LOCALSPSCREP" "GLOBAL{name}" OB'
            assert script.count(expected) == 1, (name, expected)
        assert '"PSCREP" "LOCALS"' not in script
        assert '"LOCALSPSREADY"' in script
        for slot in range(1, party_slots + 1):
            assert f"16452 {token} " in script
        assert script.count("111OB") == 3 + party_slots
    for name in ("PXCSUM", "PXCDISM"):
        spell = resource(directory, name + ".spl").read_bytes()
        header, count = struct.unpack_from("<IH", spell, 0x64)
        assert count == 1
        assert spell[header + 0x0c] == 7
    bam = resource(directory, "PSCRANIM.bam").read_bytes()
    assert bam[:8] == b"BAM V1  " and bam[10] == 5
    assert not (Path(game) / ".psion-crystal-build").exists()
    print(f"255 companion CRE/BCS pairs, native comparison operands, {party_slots} party selectors and five-direction BAM validated")


def lifecycle(weidu, gemrb, parent):
    game = parent / "game"
    subprocess.run([sys.executable, str(ROOT / "psion/tests/make_weidu_fixture.py"),
                    "--gemrb-root", str(gemrb), "--output", str(game)], check=True)
    for name in ("common", "psion"):
        shutil.copytree(ROOT / name, game / name)
    before = snapshot(game / "override")
    log = parent / "weidu.log"
    command = [str(weidu), "psion/setup-psion.tp2", "--use-lang", "en_US", "--no-exit-pause"]
    for action in ("--force-install", "--force-uninstall", "--force-install", "--force-uninstall"):
        with log.open("a") as output:
            result = subprocess.run(command + [action, "0"], cwd=game, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=180)
        if result.returncode:
            raise AssertionError(log.read_text()[-6000:])
        if action == "--force-install":
            validate(game)
        else:
            after = snapshot(game / "override")
            assert before == after, (sorted(before.keys() ^ after.keys()),
                                     [name for name in before.keys() & after.keys() if before[name] != after[name]])
    print("Real WeiDU install/uninstall/reinstall restores all original override bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("weidu", nargs="?", type=Path)
    parser.add_argument("gemrb", nargs="?", type=Path)
    parser.add_argument("--game", type=Path)
    args = parser.parse_args()
    if args.game:
        validate(args.game)
    else:
        if not args.weidu or not args.gemrb:
            parser.error("WEIDU and GEMRB_ROOT are required without --game")
        with tempfile.TemporaryDirectory(prefix="psicrystal-weidu-") as folder:
            lifecycle(args.weidu.resolve(), args.gemrb.resolve(), Path(folder))


if __name__ == "__main__":
    main()
