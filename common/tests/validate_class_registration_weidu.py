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
        subprocess.run([
            sys.executable, str(ROOT / "psion/tests/make_weidu_fixture.py"),
            "--gemrb-root", str(gemrb), "--output", str(game), "--layout", base_layout,
        ], check=True)
        override = game / "override"
        if scenario == "combined_hp":
            add_combined_hp(override / "hpclass.2da")
        else:
            write_split_classes(override / "classes.2da")
            write_native9(override / "clastext.2da")
        shutil.copytree(ROOT / "common", game / "common")
        shutil.copytree(ROOT / mod, game / mod)
        if mod == "cipher":
            subprocess.run([sys.executable, str(ROOT / "cipher/tests/seed_weidu_fixture.py"), str(game)], check=True)
        tp2 = f"{mod}/setup-{mod}.tp2" if mod != "sorcerer-monk" else "sorcerer-monk/setup-sorcerer-monk.tp2"
        subprocess.run([
            weidu, tp2, "--use-lang", "en_US", "--force-install", "0", "--no-exit-pause",
        ], cwd=game, check=True)

        ids = class_ids(override / "class.ids")
        clskills = read_rows(override / "clskills.2da")
        qslots = read_rows(override / "qslots.2da")
        names = DISCIPLINES if mod == "psion" else ("CIPHER",)
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
            for name in names:
                row = next(row for row in clastext if row[0] == name)
                assert len(row) == 9, (mod, scenario, row)
                assert int(row[1], 0) == ids[name], (mod, scenario, row)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_class_registration_weidu.py WEIDU GEMRB_ROOT")
    weidu = sys.argv[1]
    gemrb = Path(sys.argv[2]).resolve()
    for mod in ("psion", "cipher"):
        for scenario in ("combined_hp", "native9"):
            install(weidu, gemrb, mod, scenario)
    print("Psion and Cipher registration passed combined+HPCLASS and native 9-column CLASTEXT smoke tests.")


if __name__ == "__main__":
    main()
