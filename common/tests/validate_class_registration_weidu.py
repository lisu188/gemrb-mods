#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISCIPLINES = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)


def read_rows(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line.split() for line in lines[3:] if line.split()]


def write_native9(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[2].split()
    if len(header) != 5:
        raise AssertionError((path, header))
    out = [lines[0], lines[1], "        CLASSID KITID LOWER DESCSTR MIXED BIOGRAPHY FALLEN BRIEFDESC"]
    for row in read_rows(path):
        if len(row) < 6:
            continue
        out.append(" ".join(row[:6] + ["-1", "0", row[5]]))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_split_classes(path: Path):
    path.write_text(
        "2DA V1.0\n*\n        SAVE MULTI USABILITY MC_WAS_ID STREXTRA CONBONLVL\n"
        "SORCERER SAVEWIZ 0 0x40000 -1 0 10\n"
        "MONK SAVEMONK 0 0x20000000 -1 0 9\n"
        "SHAMAN SAVEPRS 0 0x40000000 -1 1 9\n",
        encoding="ascii",
    )


def add_combined_hp(path: Path):
    path.write_text("2DA V1.0\n*\n        HP\nMAGE HPWIZ\nSORCERER HPWIZ\nMONK HPMONK\n", encoding="ascii")


def class_ids(path: Path):
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) >= 2:
            try:
                result[fields[1]] = int(fields[0], 0)
            except ValueError:
                pass
    return result


def install(weidu: str, gemrb: Path, mod: str, scenario: str):
    with tempfile.TemporaryDirectory(prefix=f"{mod}-{scenario}-") as tmp:
        game = Path(tmp) / "game"
        base_layout = "legacy" if scenario == "combined_hp" else "normalized"
        fixture_command = [
            sys.executable, str(ROOT / "psion/tests/make_weidu_fixture.py"),
            "--gemrb-root", str(gemrb), "--output", str(game), "--layout", base_layout,
        ]
        if scenario in ("missing_avprefc", "external_avprefc"):
            fixture_command.append("--without-avprefc")
        subprocess.run(fixture_command, check=True)
        override = game / "override"
        avatar = override / "avprefc.2da"
        avatar_before = None
        external_avatar = None
        if scenario == "combined_hp":
            add_combined_hp(override / "hpclass.2da")
        elif scenario == "native9":
            write_split_classes(override / "classes.2da")
            write_native9(override / "clastext.2da")
        elif scenario == "custom_avprefc":
            avatar.write_text("2DA V1.0\n*\nPREFIX\nTYPE 232\nMAGE 0x400\nFIGHTER 0x100\nOTHER_MOD 0x700\n", encoding="ascii")
            avatar_before = avatar.read_bytes()
        elif scenario == "external_avprefc":
            data = Path(tmp) / "gemrb-data"
            (data / "bgee").mkdir(parents=True)
            (data / "shared").mkdir()
            external_avatar = data / "shared/avprefc.2da"
            external_avatar.write_text("2DA V1.0\n*\nPREFIX\nTYPE 232\nMAGE 0x400\nOTHER_MOD 0x700\n", encoding="ascii")
            (game / "gemrb_path.txt").write_text(f"GemRB_Data_Path = {data / 'bgee'}\n", encoding="utf-8")
        elif scenario not in ("commented_split", "missing_avprefc"):
            raise AssertionError(scenario)
        shutil.copytree(ROOT / "common", game / "common")
        shutil.copytree(ROOT / mod, game / mod)
        if mod == "cipher":
            subprocess.run([sys.executable, str(ROOT / "cipher/tests/seed_weidu_fixture.py"), str(game)], check=True)
        tp2 = f"{mod}/setup-{mod}.tp2" if mod != "sorcerer-monk" else "sorcerer-monk/setup-sorcerer-monk.tp2"
        subprocess.run([
            weidu, tp2, "--use-lang", "en_US", "--force-install", "0", "--no-exit-pause",
        ], cwd=game, check=True)

        if mod == "cipher":
            assert (override / "saveciph.2da").is_file(), (mod, scenario, "missing SAVECIPH")
            assert (override / "saveciph.2da").read_bytes() == (override / "savewiz.2da").read_bytes(), (mod, scenario, "Cipher saves differ from native Mage saves")

        ids = class_ids(override / "class.ids")
        clskills = read_rows(override / "clskills.2da")
        qslots = read_rows(override / "qslots.2da")
        names = DISCIPLINES if mod == "psion" else ("CIPHER",)
        if scenario in ("missing_avprefc", "custom_avprefc", "external_avprefc"):
            avatar_rows = dict(read_rows(avatar))
            for name in names:
                assert avatar_rows[name] == "0x600", (mod, scenario, name, avatar_rows)
            if scenario == "missing_avprefc":
                baseline = {
                    row[0]: row[1] for row in read_rows(gemrb / "gemrb/unhardcoded/shared/avprefc.2da")
                    if not row[0].startswith("#")
                }
                assert all(avatar_rows.get(name) == value for name, value in baseline.items()), avatar_rows
            else:
                assert avatar_rows["MAGE"] == "0x400" and avatar_rows["OTHER_MOD"] == "0x700", avatar_rows
        for name in names:
            cl_index = next(index for index, row in enumerate(clskills) if row[0] == name)
            assert ids[name] == cl_index, (mod, scenario, name, ids[name], cl_index)
            assert ids[name] <= 31, (mod, scenario, name, ids[name])
            qs_index = next(index for index, row in enumerate(qslots) if row[0] == name)
            assert qs_index == ids[name] - 1, (mod, scenario, name, qs_index, ids[name])

        if scenario == "combined_hp":
            classes = read_rows(override / "classes.2da")
            for name in names:
                row = next(row for row in classes if row[0] == name)
                assert int(row[6], 0) == ids[name], (mod, scenario, row)
            hp_names = {row[0] for row in read_rows(override / "hpclass.2da")}
            assert not (set(names) & hp_names), (mod, scenario, hp_names)
        else:
            clastext = read_rows(override / "clastext.2da")
            expected_len = 9 if scenario == "native9" else 6
            for name in names:
                row = next(row for row in clastext if row[0] == name)
                assert len(row) == expected_len, (mod, scenario, row)
                assert int(row[1], 0) == ids[name], (mod, scenario, row)

        if scenario in ("missing_avprefc", "custom_avprefc", "external_avprefc"):
            subprocess.run([
                weidu, tp2, "--use-lang", "en_US", "--force-uninstall", "0", "--no-exit-pause",
            ], cwd=game, check=True)
            if mod == "cipher":
                assert not (override / "saveciph.2da").exists(), "SAVECIPH left behind on uninstall"
            if avatar_before is None:
                assert not avatar.exists(), "fallback AVPREFC left behind on uninstall"
            else:
                assert avatar.read_bytes() == avatar_before, "existing AVPREFC not restored exactly"
            if external_avatar:
                assert dict(read_rows(external_avatar)) == {"TYPE": "232", "MAGE": "0x400", "OTHER_MOD": "0x700"}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_class_registration_weidu.py WEIDU GEMRB_ROOT")
    weidu = sys.argv[1]
    gemrb = Path(sys.argv[2]).resolve()
    for mod in ("psion", "cipher"):
        for scenario in ("commented_split", "combined_hp", "native9", "missing_avprefc", "custom_avprefc", "external_avprefc"):
            install(weidu, gemrb, mod, scenario)
    print("Psion and Cipher registration passed commented split, combined+HPCLASS, native 9-column CLASTEXT, missing-AVPREFC lifecycle and custom/external-AVPREFC preservation smoke tests.")


if __name__ == "__main__":
    main()
