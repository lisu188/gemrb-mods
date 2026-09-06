#!/usr/bin/env python3
"""Validate generated SPL header targets against native GemRB, not effect IDs."""
import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HANDLED = ("TARGET_CREA", "TARGET_DEAD", "TARGET_AREA", "TARGET_SELF", "TARGET_NONE")


def native_targets(engine):
    source = (engine / "gemrb/core/Item.h").read_text()
    definitions = {name: int(value) for name, value in re.findall(r"^#define\s+(TARGET_\w+)\s+(\d+)", source, re.M)}
    handled = {definitions[name] for name in HANDLED}
    assert definitions["TARGET_INV"] not in handled
    assert definitions["TARGET_INVALID"] not in handled
    return definitions, handled


def headers(data):
    assert len(data) >= 0x72 and data[:8] == b"SPL V1  "
    offset = struct.unpack_from("<I", data, 0x64)[0]
    count = struct.unpack_from("<H", data, 0x68)[0]
    assert count > 0 and offset + count * 0x28 <= len(data)
    return [offset + index * 0x28 for index in range(count)]


def validate(game, engine):
    definitions, handled = native_targets(engine)
    files = {path.stem.upper(): path.read_bytes() for path in (game / "override").iterdir()
             if path.suffix.lower() == ".spl" and path.stem.upper().startswith(("PS", "PX", "CI"))}
    assert files, "no generated class spells found"
    signatures = {}
    for name in sorted(files):
        data = files[name]
        signatures[name] = [(data[offset + 0x0C], data[offset + 0x0D]) for offset in headers(data)]
        for target, count in signatures[name]:
            assert target in handled, (name, "unsupported native header target", target)
            assert 1 <= count <= 255, (name, "invalid explicit target count", count)

    expected = {
        "CI1WHSP": "TARGET_CREA", "CI1EYES": "TARGET_CREA", "CI8RKNI": "TARGET_CREA",
        "CI5DBST": "TARGET_CREA", "CI4SSCR": "TARGET_AREA", "CILRN": "TARGET_SELF",
        "PS1CHAR": "TARGET_CREA", "PS1MAGI": "TARGET_CREA", "PSRF01": "TARGET_CREA",
        "PSRF20": "TARGET_CREA", "PSMT01": "TARGET_CREA", "PSMT034": "TARGET_CREA",
        "PS1IARM": "TARGET_SELF", "PS1VIGR": "TARGET_SELF", "PS3SSTP": "TARGET_AREA",
    }
    for name, target in expected.items():
        if name in files:
            assert signatures[name] == [(definitions[target], 1)], (name, signatures[name], target)
    inherited = 0
    for name in files:
        if name.startswith("PS") and name[-1] in "VWXYZ0134567" and name[:-1] in files:
            assert signatures[name] == signatures[name[:-1]], (name, "DC clone changed target")
            inherited += 1
        owner = re.fullmatch(r"CI8RK([0-9]{1,3})", name)
        if owner:
            assert 1 <= int(owner[1]) <= 255, (name, "invalid owner token")
            assert signatures[name] == signatures["CI8RKNI"], (name, "owner clone changed target")
            inherited += 1
        if re.fullmatch(r"(?:PXL|CIL)\d{4}", name):
            assert signatures[name] == [(definitions["TARGET_SELF"], 1)], (name, "learning proxy target")
    if "CI8RKNI" in files:
        assert all(f"CI8RK{token}" in files for token in range(1, 256)), "incomplete legacy/persistent owner variants"
    # Header creature=1 must not corrupt effect target=2 (the effect recipient).
    for name, opcode in (("CI1WHSP", 5), ("PSRF01", 12)):
        if name not in files:
            continue
        data = files[name]
        feature_offset = struct.unpack_from("<I", data, 0x6A)[0]
        effects = []
        for header in headers(data):
            count, first = struct.unpack_from("<HH", data, header + 0x1E)
            for index in range(first, first + count):
                offset = feature_offset + index * 0x30
                effects.append((struct.unpack_from("<H", data, offset)[0], data[offset + 2]))
        assert (opcode, 2) in effects, (name, "effect recipient was changed", effects)
    print(f"Native SPL targets: {len(files)} generated spells; {inherited} internal target inheritances; effect recipients preserved")


def builder_tests(weidu, engine):
    definitions, handled = native_targets(engine)
    spec = importlib.util.spec_from_file_location("target_fixture", ROOT / "psion/tests/make_weidu_fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(prefix="native-spell-target-") as temporary:
        game = Path(temporary) / "game"
        fixture.build_fixture(engine, game, "normalized")
        shutil.copytree(ROOT / "common", game / "common")

        def install(target, count, accepted):
            # WeiDU's expression grammar requires subtraction for negatives.
            count_expression = str(count) if count >= 0 else f"(0 - {abs(count)})"
            tp2 = "BACKUP ~target-backup~\nAUTHOR ~acceptance~\nBEGIN ~Synthetic spell target regression~\nINCLUDE ~common/weidu/spell-functions.tpa~\n"
            tp2 += f"CREATE ~spl~ ~ZZTARGET~\nCOPY_EXISTING ~ZZTARGET.spl~ ~override~\n LPF ADD_SPELL_HEADER INT_VAR target = {target} target_count = {count_expression} END\n"
            (game / "targets.tp2").write_text(tp2)
            command = [weidu, "targets.tp2", "--use-lang", "en_US", "--force-install", "0", "--no-exit-pause"]
            result = subprocess.run(command, cwd=game, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            path = game / "override/ZZTARGET.spl"
            if accepted:
                assert result.returncode == 0, result.stdout
                data = path.read_bytes()
                assert [(data[offset + 12], data[offset + 13]) for offset in headers(data)] == [(target, count)]
                subprocess.run([weidu, "targets.tp2", "--force-uninstall", "0", "--no-exit-pause"], cwd=game,
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            else:
                assert result.returncode != 0 and "ADD_SPELL_HEADER requires" in result.stdout, result.stdout
            assert not path.exists(), "target regression uninstall/rollback did not restore fixture"

        for target in handled:
            install(target, 1, True)
        install(definitions["TARGET_AREA"], 3, True)
        for target in (0, definitions["TARGET_INV"], definitions["TARGET_UNKNOWN"], 8, 256):
            install(target, 1, False)
        for count in (0, -1, 256):
            install(definitions["TARGET_CREA"], count, False)
    print("Native SPL builder: six accepted target/count cases; eight invalid cases rejected with rollback")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gemrb_root", type=Path)
    parser.add_argument("--game", type=Path)
    parser.add_argument("--weidu")
    args = parser.parse_args()
    if not args.game and not args.weidu:
        parser.error("supply --game for installed spells or --weidu for builder failure gates")
    if args.game:
        validate(args.game, args.gemrb_root)
    if args.weidu:
        builder_tests(args.weidu, args.gemrb_root)
