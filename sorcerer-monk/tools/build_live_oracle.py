#!/usr/bin/env python3
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

SCHEMA_VERSION = 1
REQUIRED_TABLES = (
    "CLSKILLS.2DA",
    "CLASSES.2DA",
    "QSLOTS.2DA",
    "FISTWEAP.2DA",
    "PROFS.2DA",
    "CLSWPBON.2DA",
    "NUMWSLOT.2DA",
)
OPTIONAL_TABLES = (
    "CLASTEXT.2DA",
    "HPCLASS.2DA",
    "XPCAP.2DA",
    "ALIGNMNT.2DA",
    "THIEFSKL.2DA",
    "THIEFSCL.2DA",
    "WEAPPROF.2DA",
    "LUABBR.2DA",
    "LUNUMAB.2DA",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cleaned_lines(path):
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("//", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse_2da(path):
    lines = cleaned_lines(path)
    if len(lines) < 3 or not lines[0].upper().startswith("2DA V1.0"):
        raise RuntimeError(f"{path}: unsupported 2DA header")
    default = lines[1]
    headers = lines[2].split()
    rows = []
    for line in lines[3:]:
        fields = line.split()
        if not fields:
            continue
        name = fields[0]
        values = fields[1:]
        if len(values) < len(headers):
            values += [default] * (len(headers) - len(values))
        rows.append({
            "name": name,
            "values": values,
            "mapping": dict(zip(headers, values)),
        })
    return {
        "default": default,
        "headers": headers,
        "rows": rows,
    }


def find_row(table, name, required=True):
    matches = [row for row in table["rows"] if row["name"].casefold() == str(name).casefold()]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate row {name}")
    if not matches:
        if required:
            raise RuntimeError(f"row {name} not found")
        return None
    return matches[0]


def find_row_position(table, name):
    positions = [index for index, row in enumerate(table["rows"]) if row["name"].casefold() == name.casefold()]
    if len(positions) != 1:
        raise RuntimeError(f"expected exactly one {name} row, found {len(positions)}")
    return positions[0]


def column_snapshot(table, column):
    matches = [index for index, name in enumerate(table["headers"]) if name.casefold() == column.casefold()]
    if len(matches) != 1:
        return None
    index = matches[0]
    return {
        "column": table["headers"][index],
        "values": {row["name"]: row["values"][index] for row in table["rows"]},
    }


def parse_ids(path):
    result = {}
    for line in cleaned_lines(path):
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            value = int(fields[0], 0)
        except ValueError:
            continue
        symbol = fields[1].upper()
        if symbol in result and result[symbol] != value:
            raise RuntimeError(f"{path}: conflicting IDS symbol {symbol}")
        result[symbol] = value
    return result


def version_from_tp2(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^VERSION\s+~([^~]+)~\s*$", text)
    if not match:
        raise RuntimeError(f"VERSION not found in {path}")
    return match.group(1)


class OverrideIndex:
    def __init__(self, game_root):
        self.game_root = Path(game_root).resolve()
        self.override = self.game_root / "override"
        if not self.override.is_dir():
            raise RuntimeError(f"override directory not found: {self.override}")
        self.files = {}
        for path in self.override.iterdir():
            if path.is_file():
                key = path.name.casefold()
                if key in self.files:
                    raise RuntimeError(f"case-insensitive duplicate override resource: {path.name}")
                self.files[key] = path

    def locate(self, name, required=True):
        path = self.files.get(name.casefold())
        if path is None and required:
            raise RuntimeError(f"installed override resource not found: {name}")
        return path

    def relative(self, path):
        return str(path.relative_to(self.game_root))


def load_tables(index):
    tables = {}
    files = {}
    for name in REQUIRED_TABLES:
        path = index.locate(name)
        tables[name] = parse_2da(path)
        files[name] = {"path": index.relative(path), "sha256": sha256(path)}
    for name in OPTIONAL_TABLES:
        path = index.locate(name, required=False)
        if path is not None:
            tables[name] = parse_2da(path)
            files[name] = {"path": index.relative(path), "sha256": sha256(path)}
    return tables, files


def infer_clskills_id_offset(clskills, ids):
    offsets = []
    for symbol in ("SORCERER", "MONK"):
        if symbol not in ids:
            raise RuntimeError(f"CLASS.IDS missing {symbol}")
        position = find_row_position(clskills, symbol)
        offsets.append(ids[symbol] - position)
    if len(set(offsets)) != 1:
        raise RuntimeError(f"CLSKILLS/CLASS.IDS base-class positions disagree: {offsets}")
    return offsets[0]


def table_row(tables, table_name, row_name, required=False):
    table = tables.get(table_name)
    if table is None:
        return None
    return find_row(table, row_name, required=required)


def hla_snapshot(index, tables):
    luabbr = tables.get("LUABBR.2DA")
    if luabbr is None:
        return {"enabled": False, "reason": "LUABBR.2DA not installed"}
    row = find_row(luabbr, "SORCERER_MONK", required=False)
    if row is None:
        return {"enabled": False, "reason": "SORCERER_MONK has no LUABBR row"}
    abbreviation = next((value for value in row["values"] if value not in ("*", "****", "0")), "")
    if not abbreviation:
        return {"enabled": False, "reason": "SORCERER_MONK LUABBR row has no table abbreviation", "luabbr": row}
    resource = f"LU{abbreviation}.2DA"
    path = index.locate(resource)
    table = parse_2da(path)
    usable_rows = [row for row in table["rows"] if any(value not in ("*", "****", "0") for value in row["values"])]
    return {
        "enabled": True,
        "abbreviation": abbreviation,
        "resource": path.name,
        "resource_path": index.relative(path),
        "resource_sha256": sha256(path),
        "luabbr": row,
        "lunumab": table_row(tables, "LUNUMAB.2DA", "SORCERER_MONK", required=False),
        "rows": table["rows"],
        "usable_row_count": len(usable_rows),
    }


def build_oracle(game_root, metadata=None):
    game_root = Path(game_root).resolve()
    index = OverrideIndex(game_root)
    class_ids_path = index.locate("CLASS.IDS")
    ids = parse_ids(class_ids_path)
    class_id = ids.get("SORCERER_MONK")
    if class_id is None:
        raise RuntimeError("CLASS.IDS missing SORCERER_MONK")
    tables, files = load_tables(index)
    files["CLASS.IDS"] = {"path": index.relative(class_ids_path), "sha256": sha256(class_ids_path)}

    clskills = tables["CLSKILLS.2DA"]
    custom_position = find_row_position(clskills, "SORCERER_MONK")
    id_offset = infer_clskills_id_offset(clskills, ids)
    derived_id = custom_position + id_offset
    if derived_id != class_id:
        raise RuntimeError(
            f"SORCERER_MONK identity mismatch: CLASS.IDS={class_id}, CLSKILLS-derived={derived_id}"
        )

    qslots = tables["QSLOTS.2DA"]
    qslots_position = class_id - 1
    if qslots_position < 0 or qslots_position >= len(qslots["rows"]):
        raise RuntimeError(
            f"QSLOTS positional row {qslots_position} missing for class ID {class_id}"
        )

    fist_row = find_row(tables["FISTWEAP.2DA"], str(class_id))
    version_path = game_root / "sorcerer-monk" / "setup-sorcerer-monk.tp2"
    if not version_path.is_file():
        version_path = Path(__file__).resolve().parents[1] / "setup-sorcerer-monk.tp2"
    version = version_from_tp2(version_path)

    installed = {
        "clskills": find_row(clskills, "SORCERER_MONK"),
        "classes": find_row(tables["CLASSES.2DA"], "SORCERER_MONK"),
        "clastext": table_row(tables, "CLASTEXT.2DA", "SORCERER_MONK", required=False),
        "hpclass": table_row(tables, "HPCLASS.2DA", "SORCERER_MONK", required=False),
        "xpcap": table_row(tables, "XPCAP.2DA", "SORCERER_MONK", required=False),
        "alignment": table_row(tables, "ALIGNMNT.2DA", "SORCERER_MONK", required=False),
        "profs": find_row(tables["PROFS.2DA"], "SORCERER_MONK"),
        "clswpbon": find_row(tables["CLSWPBON.2DA"], "SORCERER_MONK"),
        "numwslot": find_row(tables["NUMWSLOT.2DA"], "SORCERER_MONK"),
        "thiefskl": table_row(tables, "THIEFSKL.2DA", "SORCERER_MONK", required=False),
        "thiefscl": column_snapshot(tables["THIEFSCL.2DA"], "SORCERER_MONK") if "THIEFSCL.2DA" in tables else None,
        "weapprof": column_snapshot(tables["WEAPPROF.2DA"], "SORCERER_MONK") if "WEAPPROF.2DA" in tables else None,
        "qslots": {
            "position_zero_based": qslots_position,
            "row": qslots["rows"][qslots_position],
        },
        "fistweap": {
            "row": fist_row,
            "by_monk_level": {str(level): value for level, value in enumerate(fist_row["values"])},
        },
        "hla": hla_snapshot(index, tables),
    }

    components = {
        "sorcerer": {
            "class_id": ids["SORCERER"],
            "clskills": find_row(clskills, "SORCERER"),
            "profs": table_row(tables, "PROFS.2DA", "SORCERER", required=False),
        },
        "monk": {
            "class_id": ids["MONK"],
            "clskills": find_row(clskills, "MONK"),
            "profs": table_row(tables, "PROFS.2DA", "MONK", required=False),
            "clswpbon": table_row(tables, "CLSWPBON.2DA", "MONK", required=False),
            "numwslot": table_row(tables, "NUMWSLOT.2DA", "MONK", required=False),
            "fistweap": table_row(tables, "FISTWEAP.2DA", str(ids["MONK"]), required=False),
        },
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": dict(metadata or {}),
        "mod": {"name": "sorcerer-monk", "version": version},
        "identity": {
            "class_id": class_id,
            "clskills_position_zero_based": custom_position,
            "clskills_id_offset": id_offset,
            "clskills_derived_id": derived_id,
            "component_class_ids": {
                "sorcerer": ids["SORCERER"],
                "monk": ids["MONK"],
            },
        },
        "installed": installed,
        "components": components,
        "files": files,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a machine-readable Sorcerer/Monk live-test oracle from installed game tables."
    )
    parser.add_argument("game_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("sorcerer-monk-live-oracle.json"))
    parser.add_argument("--game-type", default="")
    parser.add_argument("--fixture-id", default="")
    parser.add_argument("--gemrb-commit", default="")
    parser.add_argument("--weidu-version", default="")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    metadata = {
        "game_type": args.game_type,
        "fixture_id": args.fixture_id,
        "gemrb_commit": args.gemrb_commit,
        "weidu_version": args.weidu_version,
    }
    oracle = build_oracle(args.game_root, metadata)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
