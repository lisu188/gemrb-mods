from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from weidu_smoke import build_fixture, write_2da


SLOTS = [
    "ARMOR", "SHIELD", "HELM", "BAG", "RING1", "RING2", "CLOAK", "BOOTS",
    "AMULET", "BRACERS", "BELT", "AMMO1", "AMMO2", "AMMO3", "MISC1", "MISC2",
    "MISC3", "MISC4", "MISC5", "WEAPON1",
]


def write_starter_table(path, slots):
    rows = [(name, [i, 1000 + i, 2000 + i, f"ITEM{i:02d}"]) for i, name in enumerate(slots)]
    write_2da(path, ["ID", "NAME_REF", "DESC_REF", "MONK"], rows)


def install(weidu, game):
    return subprocess.run(
        [weidu, "sorcerer-monk/setup-sorcerer-monk.tp2", "--game", str(game),
         "--language", "0", "--noautoupdate", "--force-install-list", "0"],
        cwd=game, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120,
    )


def exercise_rejection(weidu, slots, label):
    with tempfile.TemporaryDirectory(prefix=f"sorcerer-monk-25stweap-{label}-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        write_starter_table(override / "25stweap.2da", slots)
        originals = {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}

        result = install(weidu, game)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "25STWEAP.2DA does not match GemRB's 20-slot ToB starter-equipment layout" in output, output
        for name, original in originals.items():
            assert (override / name).read_bytes() == original, name
        print(f"{label}: rejected safely", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    exercise_rejection(weidu, SLOTS + ["EXTRA"], "extra-row")
    reordered = SLOTS.copy()
    reordered[2], reordered[3] = reordered[3], reordered[2]
    exercise_rejection(weidu, reordered, "reordered-rows")


if __name__ == "__main__":
    main()
