#!/usr/bin/env python3
"""Build a small, reproducible BGEE-like game directory for WeiDU CI.

The fixture starts from GemRB's official demo, overlays GemRB's shipped BG2 and
BGEE rule tables, adds the BGEE autodetection marker, and regenerates CHITIN.KEY.
It is intentionally only an installer fixture: it exercises real WeiDU resource
loading, table patching, SPL/CRE creation, TLK writes, backup and uninstall.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def merge_tree(source: Path, destination: Path) -> None:
    """Copy every regular file from source over destination."""
    if not source.is_dir():
        return
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def write_ids(path: Path, rows: tuple[tuple[int, str], ...]) -> None:
    """Write a stable IDS symbol subset used by the installer."""
    path.write_text(
        "\n".join(f"0x{number:04x} {symbol}" for number, symbol in rows) + "\n",
        encoding="ascii",
    )


def write_2da(
    path: Path,
    columns: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    default: str = "0",
) -> None:
    """Write a conventional whitespace-delimited 2DA V1.0 table."""
    lines = ["2DA V1.0", default, "        " + " ".join(columns)]
    lines.extend(" ".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def require_files(root: Path, names: tuple[str, ...]) -> None:
    missing = [name for name in names if not (root / name).is_file()]
    if missing:
        raise RuntimeError(f"fixture is missing required resources: {', '.join(missing)}")


def build_fixture(gemrb_root: Path, output: Path) -> None:
    demo = gemrb_root / "demo"
    if not demo.is_dir():
        raise RuntimeError(f"GemRB demo directory not found: {demo}")

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(demo, output)

    override = output / "override"
    override.mkdir(parents=True, exist_ok=True)

    # GemRB's normalized BG2 tables expose the split class layout used by
    # released GemRB versions. BGEE-specific files override the shared/BG2
    # versions when present.
    unhardcoded = gemrb_root / "gemrb" / "unhardcoded"
    for directory in ("shared", "bg2", "bgee"):
        merge_tree(unhardcoded / directory, override)

    dialog = output / "dialog.tlk"
    if not dialog.is_file() or dialog.read_bytes()[:8] != b"TLK V1  ":
        raise RuntimeError("GemRB demo dialog.tlk is missing or invalid")

    language = output / "lang" / "en_US"
    language.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dialog, language / "dialog.tlk")

    # WeiDU detects BGEE from OH1000.ARE. Its contents are irrelevant for this
    # installer-only fixture; the resource only has to exist in CHITIN.KEY.
    (override / "OH1000.ARE").write_bytes(b"AREAV1.0")

    # Astral Construct currently clones WOLF.CRE. Reuse a valid demo creature
    # body so WeiDU's CRE name patches operate on a structurally valid resource.
    creature_candidates = sorted(
        path for path in output.rglob("*") if path.is_file() and path.suffix.lower() == ".cre"
    )
    if not creature_candidates:
        raise RuntimeError("GemRB demo contains no CRE resource for WOLF.CRE")
    shutil.copy2(creature_candidates[0], override / "WOLF.CRE")

    # These symbols are resolved while the purpose-built powers are generated.
    # The fixture values only need to be stable and distinct; gameplay values
    # are supplied by the actual target game's IDS resources.
    write_ids(
        override / "MISSILE.IDS",
        (
            (0, "None"),
            (1, "Fireball_Just_Projectile"),
            (5, "Lightning_Bolt"),
            (6, "New_Cone_Of_Cold"),
            (7, "Cone_Of_Cold"),
        ),
    )
    write_ids(
        override / "DMGTYPE.IDS",
        (
            (0, "MAGIC"),
            (1, "ELECTRICITY"),
            (2, "SLASHING"),
        ),
    )

    # The demo intentionally omits several original-game tables. Supply only
    # the structural subset required by the class installer. Values are chosen
    # to exercise APPEND and APPEND_COL, not to model a playable campaign.
    write_ids(
        override / "class.ids",
        (
            (1, "MAGE"),
            (2, "FIGHTER"),
            (19, "SORCERER"),
            (20, "MONK"),
        ),
    )
    write_2da(
        override / "alignmnt.2da",
        ("LG", "NG", "CG", "LN", "TN", "CN", "LE", "NE", "CE"),
        (("SORCERER", "1", "1", "1", "1", "1", "1", "1", "1", "1"),),
    )
    write_2da(
        override / "profs.2da",
        ("FIRST_LEVEL", "OTHER_LEVELS"),
        (("SORCERER", "2", "4"),),
    )
    write_2da(
        override / "xpcap.2da",
        ("VALUE",),
        (("SORCERER", "8000000"),),
    )

    # class-common.tpa appends exactly fifty proficiency values per discipline.
    # A one-column, fifty-row fixture exercises the full APPEND_COL path.
    write_2da(
        override / "weapprof.2da",
        ("SORCERER",),
        tuple((f"PROF{index:02d}", "0") for index in range(50)),
    )

    # A real GemRB run writes this file. Point at the fixture override so WeiDU
    # also exercises GemRB_Data_Path parsing without depending on host paths.
    (output / "gemrb_path.txt").write_text(
        f"GemRB_Data_Path = {override.resolve()}\n",
        encoding="utf-8",
    )

    require_files(
        override,
        (
            "classes.2da",
            "clastext.2da",
            "clsrcreq.2da",
            "hpclass.2da",
            "class.ids",
            "alignmnt.2da",
            "weapprof.2da",
            "profs.2da",
            "xpcap.2da",
            "avprefc.2da",
            "qslots.2da",
            "clskills.2da",
            "WOLF.CRE",
            "MISSILE.IDS",
            "DMGTYPE.IDS",
            "OH1000.ARE",
        ),
    )

    key_script = gemrb_root / "tools" / "demo_key_file.py"
    subprocess.run(["python3", str(key_script), str(output)], check=True)
    if (output / "chitin.key").read_bytes()[:8] != b"KEY V1  ":
        raise RuntimeError("generated chitin.key is invalid")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gemrb-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build_fixture(args.gemrb_root.resolve(), args.output.resolve())
    print(f"WeiDU BGEE fixture created at {args.output.resolve()}")


if __name__ == "__main__":
    main()
