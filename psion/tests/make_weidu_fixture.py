#!/usr/bin/env python3
"""Build reproducible BG-family WeiDU installation fixtures.

The fixture starts from GemRB's official demo, overlays pinned GemRB rule data,
and then selects one of the class-table layouts supported by the installer:

- ``normalized``: released GemRB's six-field split CLASTEXT layout;
- ``native``: Enhanced Edition's ten-field split CLASTEXT layout;
- ``legacy``: older GemRB's nineteen-field combined CLASSES layout.

The result is an installer fixture, not a playable campaign. It exercises real
WeiDU resource loading, table patching, SPL/CRE/ITM creation, TLK writes, backup,
uninstall and reinstall without distributing proprietary game data.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

LAYOUTS = ("normalized", "native", "legacy")
PROGRESSION_LEVELS = {
    "normalized": 20,
    "native": 41,
    "legacy": 40,
}

# Deterministic zero-effect ITMs used to validate the Psion-specific opcode-319
# usability conversion. Values are item type, legacy usability mask and weapon
# proficiency byte. All resrefs stay within the engine's eight-character limit.
ITEM_USABILITY_FIXTURES = {
    "psspear.itm": (29, 0x40000, 0x62),  # legal Psion weapon, Mage-blocked
    "psxbow.itm": (27, 0x40000, 0x67),   # legal Psion weapon, Mage-blocked
    "psclub.itm": (17, 0x40000, 0x73),   # legal club, shared mace/club type
    "psmace.itm": (17, 0, 0x65),         # illegal mace, same item type as club
    "pssword.itm": (19, 0, 0x5B),        # illegal weapon without Mage bit
    "psarmor.itm": (2, 0, 0),            # armor must always be blocked
    "psshield.itm": (12, 0, 0),          # shield must always be blocked
    "psringx.itm": (10, 0x40000, 0),     # nonweapon inherits Mage restriction
    "psringok.itm": (10, 0, 0),          # ordinary nonweapon remains usable
    "psbullet.itm": (14, 0x40000, 0),    # sling ammunition exception
    "psbolt.itm": (31, 0x40000, 0),      # crossbow ammunition exception
}

# BG2-family WEAPPROF ordering, including the eight retained BG1 group rows.
# IDs for the modern rows match the engine proficiency stats where applicable.
WEAPPROF_ROWS = (
    ("LARGE_SWORD", 0),
    ("SMALL_SWORD", 1),
    ("BOW", 2),
    ("SPEAR", 3),
    ("BLUNT", 4),
    ("SPIKED", 5),
    ("AXE", 6),
    ("MISSILE", 7),
    ("BASTARDSWORD", 89),
    ("LONGSWORD", 90),
    ("SHORTSWORD", 91),
    ("AXE", 92),
    ("TWOHANDEDSWORD", 93),
    ("KATANA", 94),
    ("SCIMITARWAKISASHININJATO", 95),
    ("DAGGER", 96),
    ("WARHAMMER", 97),
    ("CLUB", 115),
    ("SPEAR", 98),
    ("HALBERD", 99),
    ("FLAILMORNINGSTAR", 100),
    ("MACE", 101),
    ("QUARTERSTAFF", 102),
    ("CROSSBOW", 103),
    ("LONGBOW", 104),
    ("SHORTBOW", 105),
    ("DART", 106),
    ("SLING", 107),
    ("2HANDED", 111),
    ("SWORDANDSHIELD", 112),
    ("SINGLEWEAPON", 113),
    ("2WEAPON", 114),
    *((f"EXTRA{number}", 114 + number) for number in range(2, 20)),
)


def lowercase_relative(path: Path) -> Path:
    """Return a case-normalized relative path for IE resource lookup."""
    return Path(*(part.lower() for part in path.parts))


def normalize_tree_case(directory: Path) -> None:
    """Collapse Linux case variants into one deterministic lowercase tree."""
    if not directory.is_dir():
        return

    with tempfile.TemporaryDirectory(prefix="psion-fixture-") as temporary:
        normalized = Path(temporary) / "normalized"
        normalized.mkdir()
        for path in sorted(directory.rglob("*"), key=lambda item: str(item).lower()):
            if not path.is_file():
                continue
            target = normalized / lowercase_relative(path.relative_to(directory))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

        shutil.rmtree(directory)
        shutil.copytree(normalized, directory)


def merge_tree(source: Path, destination: Path) -> None:
    """Copy files with case-insensitive overwrite semantics."""
    if not source.is_dir():
        return
    for path in sorted(source.rglob("*"), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        target = destination / lowercase_relative(path.relative_to(source))
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


def write_item_fixture(path: Path, item_type: int, usability: int, proficiency: int) -> None:
    """Write a minimal structurally valid ITM V1 resource with no abilities/effects."""
    data = bytearray(0x72)
    data[:8] = b"ITM V1  "
    struct.pack_into("<H", data, 0x1C, item_type)
    struct.pack_into("<I", data, 0x1E, usability)
    data[0x31] = proficiency
    struct.pack_into("<I", data, 0x64, 0x72)
    struct.pack_into("<H", data, 0x68, 0)
    struct.pack_into("<I", data, 0x6A, 0x72)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 0)
    path.write_bytes(data)


def configure_item_usability_fixtures(override: Path) -> None:
    # WeiDU normalizes same-resref override destinations to uppercase on Linux.
    # Match that convention so uninstall backups capture the actual source bytes
    # instead of treating the uppercase destination as previously absent.
    for filename, (item_type, usability, proficiency) in ITEM_USABILITY_FIXTURES.items():
        write_item_fixture(override / filename.upper(), item_type, usability, proficiency)


def read_2da_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        rows.append(stripped.split())
    return rows


def mage_xp_values(level_count: int) -> tuple[str, ...]:
    values = [
        0, 2500, 5000, 10000, 20000, 40000, 60000, 90000, 135000,
        250000, 375000,
    ]
    while len(values) < level_count:
        values.append(values[-1] + 375000)
    return tuple(str(value) for value in values[:level_count])


def configure_progression_tables(override: Path, layout: str) -> None:
    level_count = PROGRESSION_LEVELS[layout]
    columns = tuple(str(level) for level in range(1, level_count + 1))
    mage_xp = mage_xp_values(level_count)

    write_2da(
        override / "xplevel.2da",
        columns,
        (
            ("MAGE", *mage_xp),
            ("FIGHTER", *(str((level - 1) * 2000) for level in range(1, level_count + 1))),
        ),
        default="0",
    )

    write_2da(
        override / "thac0.2da",
        columns,
        (
            ("MAGE", *("20" for _ in range(level_count))),
            ("FIGHTER", *(str(max(0, 20 - (level - 1))) for level in range(1, level_count + 1))),
        ),
        default="20",
    )

    write_2da(
        override / "lore.2da",
        ("RATE",),
        (
            ("MAGE", "3"),
            ("THIEF", "3"),
            ("FIGHTER", "1"),
        ),
        default="0",
    )


def configure_class_rule_tables(override: Path) -> None:
    write_2da(
        override / "abclasrq.2da",
        ("MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHR"),
        (
            ("MAGE", "0", "0", "0", "9", "0", "0"),
            ("SORCERER", "0", "0", "0", "9", "0", "0"),
        ),
        default="0",
    )

    mage_allowed = {
        "SMALL_SWORD", "BLUNT", "MISSILE", "DAGGER",
        "QUARTERSTAFF", "DART", "SLING",
    }
    rows = []
    for index, (name, stat_id) in enumerate(WEAPPROF_ROWS):
        value = "1" if name in mage_allowed else "0"
        rows.append(
            (
                name,
                str(stat_id),
                str(1000 + index),
                str(2000 + index),
                value,
                value,
            )
        )
    write_2da(
        override / "weapprof.2da",
        ("ID", "NAME_REF", "DESC_REF", "MAGE", "SORCERER"),
        tuple(rows),
        default="0",
    )


def configure_class_layout(override: Path, layout: str) -> None:
    if layout == "normalized":
        return

    if layout == "native":
        source_rows = read_2da_rows(override / "clastext.2da")
        native_rows: list[tuple[str, ...]] = []
        for row in source_rows:
            if len(row) < 6 or not row[1].isdigit():
                continue
            native_rows.append(tuple(row[:6] + ["-1", "0", row[5], "-1"]))
        if not native_rows:
            raise RuntimeError("unable to derive native CLASTEXT fixture rows")
        write_2da(
            override / "clastext.2da",
            (
                "CLASSID", "KITID", "LOWER", "DESCSTR", "MIXED",
                "BIOGRAPHY", "FALLEN", "BRIEFDESC", "FALLEN_NOTICE",
            ),
            tuple(native_rows),
            default="*",
        )
        return

    if layout == "legacy":
        for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):
            (override / filename).unlink(missing_ok=True)
        write_2da(
            override / "classes.2da",
            (
                "NAME_REF", "DESC_REF", "CAP_REF", "SAVE", "MULTI", "ID",
                "HP", "USABILITY", "MC_WAS_ID", "HUMAN", "ELF", "HALF_ELF",
                "DWARF", "HALFLING", "GNOME", "HALFORC", "STREXTRA",
                "CONBONLVL",
            ),
            (
                (
                    "SORCERER", "45849", "45866", "45856", "SAVEWIZ", "0",
                    "19", "HPWIZ", "0x40000", "-1", "1", "1", "1", "0",
                    "0", "0", "0", "0", "10",
                ),
                (
                    "MONK", "45851", "45867", "45858", "SAVEMONK", "0",
                    "20", "HPMONK", "0x20000000", "-1", "1", "0", "0", "0",
                    "0", "0", "0", "0", "9",
                ),
            ),
            default="*",
        )
        return

    raise ValueError(f"unsupported fixture layout: {layout}")


def require_files(root: Path, names: tuple[str, ...]) -> None:
    missing = [name for name in names if not (root / name).is_file()]
    if missing:
        raise RuntimeError(f"fixture is missing required resources: {', '.join(missing)}")


def build_fixture(gemrb_root: Path, output: Path, layout: str) -> None:
    demo = gemrb_root / "demo"
    if not demo.is_dir():
        raise RuntimeError(f"GemRB demo directory not found: {demo}")

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(demo, output)

    override = output / "override"
    override.mkdir(parents=True, exist_ok=True)
    normalize_tree_case(override)

    unhardcoded = gemrb_root / "gemrb" / "unhardcoded"
    for directory in ("shared", "bg2", "bgee"):
        merge_tree(unhardcoded / directory, override)

    dialog = output / "dialog.tlk"
    if not dialog.is_file() or dialog.read_bytes()[:8] != b"TLK V1  ":
        raise RuntimeError("GemRB demo dialog.tlk is missing or invalid")

    language = output / "lang" / "en_US"
    language.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dialog, language / "dialog.tlk")

    (override / "oh1000.are").write_bytes(b"AREAV1.0")

    creature_candidates = sorted(
        path for path in output.rglob("*") if path.is_file() and path.suffix.lower() == ".cre"
    )
    if not creature_candidates:
        raise RuntimeError("GemRB demo contains no CRE resource for WOLF.CRE")
    shutil.copy2(creature_candidates[0], override / "wolf.cre")

    write_ids(
        override / "missile.ids",
        (
            (0, "None"),
            (1, "Fireball_Just_Projectile"),
            (5, "Lightning_Bolt"),
            (6, "New_Cone_Of_Cold"),
            (7, "Cone_Of_Cold"),
        ),
    )
    write_ids(
        override / "dmgtype.ids",
        ((0, "MAGIC"), (1, "ELECTRICITY"), (2, "SLASHING")),
    )

    write_ids(
        override / "class.ids",
        ((1, "MAGE"), (2, "FIGHTER"), (19, "SORCERER"), (20, "MONK")),
    )
    write_2da(
        override / "alignmnt.2da",
        ("LG", "NG", "CG", "LN", "TN", "CN", "LE", "NE", "CE"),
        (("SORCERER", "1", "1", "1", "1", "1", "1", "1", "1", "1"),),
    )
    write_2da(
        override / "profs.2da",
        ("FIRST_LEVEL", "RATE"),
        (("SORCERER", "2", "4"),),
    )
    write_2da(
        override / "xpcap.2da",
        ("VALUE",),
        (("MAGE", "161000"), ("SORCERER", "8000000")),
    )
    configure_progression_tables(override, layout)
    configure_class_rule_tables(override)
    configure_class_layout(override, layout)

    (output / "gemrb_path.txt").write_text(
        f"GemRB_Data_Path = {override.resolve()}\n",
        encoding="utf-8",
    )

    required = [
        "classes.2da", "class.ids", "alignmnt.2da", "abclasrq.2da",
        "weapprof.2da", "profs.2da", "xpcap.2da", "xplevel.2da",
        "thac0.2da", "lore.2da", "avprefc.2da", "qslots.2da",
        "clskills.2da", "wolf.cre", "missile.ids", "dmgtype.ids",
        "oh1000.are",
    ]
    if layout != "legacy":
        required.extend(("clastext.2da", "clsrcreq.2da", "hpclass.2da"))
    require_files(override, tuple(required))

    preview_name = "classes.2da" if layout == "legacy" else "clastext.2da"
    preview_lines = (override / preview_name).read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    print(f"Fixture layout={layout} {preview_name.upper()} preview:")
    for line in preview_lines[:10]:
        print(f"  {line}")
    print(
        f"Fixture progression columns={PROGRESSION_LEVELS[layout]} "
        f"for XPLEVEL.2DA and THAC0.2DA; semantic WEAPPROF/ABCLASRQ enabled"
    )

    # GemRB's demo KEY intentionally contains no BIFFs and assigns locator 0 to
    # every scanned override resource. WeiDU can read those resources, but a
    # same-name COPY_EXISTING_REGEXP backup can then treat the KEY locator as a
    # zero-byte BIFF resource. Build CHITIN.KEY before the synthetic ITMs.
    # WeiDU GLOB explicitly merges override files with KEY resources, so these
    # late-created ITMs are still enumerated and patched like normal override
    # resources while retaining correct backup bytes.
    key_script = gemrb_root / "tools" / "demo_key_file.py"
    subprocess.run(["python3", str(key_script), str(output)], check=True)
    if (output / "chitin.key").read_bytes()[:8] != b"KEY V1  ":
        raise RuntimeError("generated chitin.key is invalid")

    configure_item_usability_fixtures(override)
    require_files(override, tuple(filename.upper() for filename in ITEM_USABILITY_FIXTURES))
    print("Added uppercase override-only semantic ITM fixtures after CHITIN.KEY generation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gemrb-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--layout", choices=LAYOUTS, default="normalized")
    args = parser.parse_args()
    build_fixture(args.gemrb_root.resolve(), args.output.resolve(), args.layout)
    print(f"WeiDU {args.layout} fixture created at {args.output.resolve()}")


if __name__ == "__main__":
    main()
