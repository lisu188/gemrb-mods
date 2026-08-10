#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_weidu_install.sh GEMRB_ROOT [LAYOUT]}"
layout="${2:-normalized}"
case "$layout" in
  normalized|native|legacy) ;;
  *) echo "Unsupported fixture layout: $layout" >&2; exit 2 ;;
esac

game="$RUNNER_TEMP/psion-weidu-game-$layout"
baseline="$RUNNER_TEMP/psion-weidu-baseline-$layout.json"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game" \
  --layout "$layout"
cp -R "$repo_root/common" "$game/common"
cp -R "$repo_root/psion" "$game/psion"

# Snapshot every pre-existing table and synthetic ITM that the installer edits.
# WeiDU restores those resources byte-for-byte. DIALOG.TLK is different:
# uninstall preserves the original entries but may leave newly allocated,
# now-unreferenced string slots at the end. Record a semantic digest of the
# original entry prefix.
python3 - "$game" "$baseline" <<'PY'
from __future__ import annotations
import hashlib
import json
import struct
import sys
from pathlib import Path


def tlk_entries(path: Path) -> list[bytes]:
    data = path.read_bytes()
    assert data[:8] == b"TLK V1  ", path
    count = struct.unpack_from("<I", data, 0x0A)[0]
    text_offset = struct.unpack_from("<I", data, 0x0E)[0]
    entries: list[bytes] = []
    for index in range(count):
        offset = 0x12 + index * 0x1A
        flags = data[offset : offset + 2]
        sound = data[offset + 2 : offset + 10]
        volume_pitch = data[offset + 10 : offset + 18]
        relative, length = struct.unpack_from("<II", data, offset + 18)
        text = data[text_offset + relative : text_offset + relative + length]
        entries.append(flags + sound + volume_pitch + struct.pack("<I", length) + text)
    return entries


root = Path(sys.argv[1])
out = Path(sys.argv[2])
candidates = (
    "classes.2da", "clastext.2da", "clsrcreq.2da", "hpclass.2da",
    "class.ids", "alignmnt.2da", "abclasrq.2da", "weapprof.2da",
    "profs.2da", "xpcap.2da", "xplevel.2da", "thac0.2da", "lore.2da",
    "avprefc.2da", "qslots.2da", "clskills.2da",
    "psspear.itm", "psxbow.itm", "psclub.itm", "psmace.itm",
    "pssword.itm", "psarmor.itm", "psshield.itm", "psringx.itm",
    "psringok.itm", "psbullet.itm", "psbolt.itm",
)
paths = [root / "override" / name for name in candidates if (root / "override" / name).is_file()]
entries = tlk_entries(root / "lang/en_US/dialog.tlk")
data = {
    "files": {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    },
    "tlk": {
        "count": len(entries),
        "prefix_sha256": hashlib.sha256(b"".join(entries)).hexdigest(),
    },
}
out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

install() {
  (
    cd "$game"
    weidu psion/setup-psion.tp2 \
      --use-lang en_US \
      --force-install 0 \
      --no-exit-pause
  )
}

uninstall() {
  (
    cd "$game"
    weidu psion/setup-psion.tp2 \
      --use-lang en_US \
      --force-uninstall 0 \
      --no-exit-pause
  )
}

verify_installed() {
  python3 - "$game" "$layout" <<'PY'
from __future__ import annotations
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
layout = sys.argv[2]
override = root / "override"
disciplines = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)


def read_2da(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(lines) >= 3 and lines[0].strip().upper() == "2DA V1.0", path
    columns = lines[2].split()
    rows: dict[str, list[str]] = {}
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        fields = stripped.split()
        rows[fields[0]] = fields[1:]
    return columns, rows


def read_2da_list(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert len(lines) >= 3 and lines[0].strip().upper() == "2DA V1.0", path
    columns = lines[2].split()
    rows = []
    for line in lines[3:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        rows.append(stripped.split())
    return columns, rows


def read_class_ids(path: Path) -> dict[str, int]:
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[1] not in disciplines:
            continue
        result[fields[1]] = int(fields[0], 0)
    return result


def casefold_path(path: Path) -> Path:
    if path.exists():
        return path
    matches = [
        candidate
        for candidate in path.parent.iterdir()
        if candidate.name.lower() == path.name.lower()
    ]
    assert len(matches) == 1, (layout, path, matches)
    return matches[0]


def equipping_effects(path: Path) -> list[tuple[int, int, int, int, int, int]]:
    path = casefold_path(path)
    data = path.read_bytes()
    assert data[:8] == b"ITM V1  ", (layout, path.name, data[:8])
    assert len(data) >= 0x72, (layout, path.name, len(data))
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    equipping_index = struct.unpack_from("<H", data, 0x6E)[0]
    equipping_count = struct.unpack_from("<H", data, 0x70)[0]
    effects = []
    for index in range(equipping_count):
        offset = effect_offset + (equipping_index + index) * 0x30
        assert offset + 0x30 <= len(data), (layout, path.name, offset, len(data))
        effects.append((
            struct.unpack_from("<H", data, offset)[0],
            data[offset + 0x02],
            data[offset + 0x03],
            struct.unpack_from("<I", data, offset + 0x04)[0],
            struct.unpack_from("<I", data, offset + 0x08)[0],
            data[offset + 0x0C],
        ))
    return effects


class_columns, _ = read_2da(override / "classes.2da")
assert len(class_columns) in (6, 18), (layout, class_columns)
split_schema = len(class_columns) == 6
class_tables = ["classes.2da"]
if split_schema:
    class_tables.extend(("clastext.2da", "clsrcreq.2da", "hpclass.2da"))
for filename in (
    *class_tables,
    "class.ids", "alignmnt.2da", "abclasrq.2da", "weapprof.2da",
    "profs.2da", "xpcap.2da", "avprefc.2da", "qslots.2da", "clskills.2da",
):
    text = (override / filename).read_text(encoding="utf-8", errors="replace")
    for discipline in disciplines:
        assert discipline in text, (layout, filename, discipline)
if not split_schema:
    for filename in ("clastext.2da", "clsrcreq.2da", "hpclass.2da"):
        path = override / filename
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            for discipline in disciplines:
                assert discipline not in text, (layout, filename, discipline)

# A custom class cannot safely reuse the Mage/Sorcerer legacy ITM usability bit:
# doing so would incorrectly reject legal Psion spears, crossbows, and clubs.
# The class rows are neutral and item-local opcode 319 effects carry the rules.
class_columns, class_rows = read_2da(override / "classes.2da")
assert "USABILITY" in class_columns, (layout, class_columns)
usability_column = class_columns.index("USABILITY")
for discipline in disciplines:
    assert int(class_rows[discipline][usability_column], 0) == 0, (
        layout, discipline, class_rows[discipline][usability_column]
    )

# Character creation requires Intelligence 15 and no other class-specific
# ability minimum. This must be enforced in chargen, not merely at manifest time.
ability_columns, ability_rows = read_2da(override / "abclasrq.2da")
assert ability_columns == [
    "MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHR"
], (layout, ability_columns)
for discipline in disciplines:
    assert ability_rows.get(discipline) == ["0", "0", "0", "15", "0", "0"], (
        layout, discipline, ability_rows.get(discipline)
    )

# Character creation grants two proficiency points and level-up grants one new
# point every four levels, matching the design and GemRB's PROFS.RATE lookup.
profs_columns, profs_rows = read_2da(override / "profs.2da")
assert profs_columns == ["FIRST_LEVEL", "RATE"], (layout, profs_columns)
for discipline in disciplines:
    assert profs_rows.get(discipline) == ["2", "4"], (
        layout, discipline, profs_rows.get(discipline)
    )

# WEAPPROF is positional at runtime but semantic by row name. Each Psion may
# place at most one pip in dagger, club, spear, quarterstaff, crossbow, dart and
# sling; every other proficiency/style row is disabled. Duplicate SPEAR rows
# intentionally receive the same value without relying on their offsets.
weapprof_columns, weapprof_rows = read_2da_list(override / "weapprof.2da")
allowed = {"DAGGER", "CLUB", "SPEAR", "QUARTERSTAFF", "CROSSBOW", "DART", "SLING"}
seen = {name: 0 for name in allowed}
for discipline in disciplines:
    assert discipline in weapprof_columns, (layout, discipline, weapprof_columns)
    column = weapprof_columns.index(discipline)
    for fields in weapprof_rows:
        row_name = fields[0]
        value = fields[1 + column]
        expected = "1" if row_name in allowed else "0"
        assert value == expected, (layout, discipline, row_name, value, expected)
        if row_name in seen:
            seen[row_name] += 1
assert all(seen[name] >= 1 for name in allowed), (layout, seen)

# Preserve the campaign's real XP ceiling. The fixture deliberately gives Mage
# 161000 and Sorcerer 8000000 so cloning the wrong seed is detectable.
xpcap_columns, xpcap_rows = read_2da(override / "xpcap.2da")
assert xpcap_columns == ["VALUE"], (layout, xpcap_columns)
assert xpcap_rows["MAGE"] == ["161000"], (layout, xpcap_rows["MAGE"])
for discipline in disciplines:
    assert xpcap_rows.get(discipline) == xpcap_rows["MAGE"], (
        layout, discipline, xpcap_rows.get(discipline), xpcap_rows["MAGE"]
    )

# Item-local restrictions: legal Psion weapons and their ammunition remain
# unrestricted even when the fixture marks them unusable by Mages. Illegal
# weapons, armor, shields, and Mage-blocked nonweapons receive exactly six
# CLASS.IDS-targeted opcode-319 restrictions, one per discipline.
class_ids = read_class_ids(override / "class.ids")
assert set(class_ids) == set(disciplines), (layout, class_ids)
_, clskills_list = read_2da_list(override / "clskills.2da")
_, qslots_list = read_2da_list(override / "qslots.2da")
for discipline in disciplines:
    cl_index = next(index for index, row in enumerate(clskills_list) if row[0] == discipline)
    qs_index = next(index for index, row in enumerate(qslots_list) if row[0] == discipline)
    assert class_ids[discipline] == cl_index, (layout, discipline, class_ids[discipline], cl_index)
    assert class_ids[discipline] <= 31, (layout, discipline, class_ids[discipline])
    assert qs_index == class_ids[discipline] - 1, (layout, discipline, qs_index, class_ids[discipline])
psion_ids = set(class_ids.values())
restricted_items = {
    "psmace.itm", "pssword.itm", "psarmor.itm", "psshield.itm", "psringx.itm"
}
legal_items = {
    "psspear.itm", "psxbow.itm", "psclub.itm", "psringok.itm",
    "psbullet.itm", "psbolt.itm",
}
for filename in restricted_items:
    effects = equipping_effects(override / filename)
    assert len(effects) == 6, (layout, filename, effects)
    assert {effect[3] for effect in effects} == psion_ids, (layout, filename, effects, psion_ids)
    for opcode, target, power, parameter1, parameter2, timing in effects:
        assert (opcode, target, power, parameter2, timing) == (319, 2, 0, 5, 2), (
            layout, filename, opcode, target, power, parameter1, parameter2, timing
        )
for filename in legal_items:
    assert equipping_effects(override / filename) == [], (
        layout, filename, equipping_effects(override / filename)
    )

# New single classes require explicit XP and attack progression. Every Psion
# must clone the complete installed-game MAGE XP row, regardless of table width.
xp_columns, xp_rows = read_2da(override / "xplevel.2da")
assert "MAGE" in xp_rows, (layout, "missing MAGE XPLEVEL row")
assert len(xp_columns) in (20, 40, 41), (layout, len(xp_columns))
assert len(xp_rows["MAGE"]) == len(xp_columns), (layout, "MAGE XPLEVEL width")
for discipline in disciplines:
    assert xp_rows.get(discipline) == xp_rows["MAGE"], (
        layout, discipline, xp_rows.get(discipline), xp_rows["MAGE"]
    )
assert xp_rows["MAGE"][8] == "135000", (layout, xp_rows["MAGE"][8])

# THAC0 is deliberately not cloned from another class. It follows the Psion
# half-rate formula for every level column exposed by the current game.
thac0_columns, thac0_rows = read_2da(override / "thac0.2da")
assert len(thac0_columns) == len(xp_columns), (
    layout, len(thac0_columns), len(xp_columns)
)
expected_thac0 = [str(max(0, 20 - (level // 2))) for level in range(1, len(thac0_columns) + 1)]
for discipline in disciplines:
    assert thac0_rows.get(discipline) == expected_thac0, (
        layout, discipline, thac0_rows.get(discipline), expected_thac0
    )

# GemRB's LUCommon.SetupLore indexes LORE.2DA by class row name. All custom
# disciplines therefore need an explicit RATE matching the Psion design.
lore_columns, lore_rows = read_2da(override / "lore.2da")
assert lore_columns == ["RATE"], (layout, lore_columns)
for discipline in disciplines:
    assert lore_rows.get(discipline) == ["5"], (
        layout, discipline, lore_rows.get(discipline)
    )

for filename in (
    "psionpool.2da", "psionknown.2da", "psiondisc.2da",
    "psionskills.2da", "psionfeats.2da", "psionpowers.2da",
    "psionaugment.2da", "ps1eray.2da", "ps1mthr.2da",
    "ps1vigr.2da", "ps2aaff.2da", "mxpsion.2da",
    "clabpsee.2da", "clabpsha.2da", "clabpkin.2da",
    "clabpego.2da", "clabpnom.2da", "clabptel.2da",
):
    assert (override / filename).is_file(), (layout, filename)

generated = [path for path in override.iterdir() if path.is_file()]
spells = {
    path.name.lower()
    for path in generated
    if path.suffix.lower() == ".spl" and path.stem.lower().startswith("ps")
}
assert len(spells) >= 117, (layout, len(spells))
assert any(path.name.lower() == "psacon01.cre" for path in generated), layout

for name in spells:
    path = next(item for item in generated if item.name.lower() == name)
    data = path.read_bytes()
    assert data[:8] == b"SPL V1  ", (layout, name, data[:8])
    assert len(data) >= 0x72, (layout, name, len(data))
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    global_effects = struct.unpack_from("<H", data, 0x70)[0]
    assert header_count >= 1, (layout, name, header_count)
    assert header_offset + header_count * 0x28 <= len(data), (layout, name)
    maximum_effect = global_effects
    for index in range(header_count):
        ability = header_offset + index * 0x28
        count = struct.unpack_from("<H", data, ability + 0x1E)[0]
        first = struct.unpack_from("<H", data, ability + 0x20)[0]
        maximum_effect = max(maximum_effect, first + count)
    assert effect_offset + maximum_effect * 0x30 <= len(data), (layout, name, maximum_effect)

log = next(
    path for path in root.iterdir()
    if path.is_file() and path.name.lower() == "weidu.log"
)
log_text = log.read_text(encoding="utf-8", errors="replace")
assert "PSION/SETUP-PSION.TP2" in log_text.upper()
assert "#0 #0" in log_text
print(f"WeiDU {layout} fixture installation validation passed.")
PY
}

verify_uninstalled() {
  python3 - "$game" "$baseline" "$layout" <<'PY'
from __future__ import annotations
import hashlib
import json
import struct
import sys
from pathlib import Path


def tlk_entries(path: Path) -> list[bytes]:
    data = path.read_bytes()
    assert data[:8] == b"TLK V1  ", path
    count = struct.unpack_from("<I", data, 0x0A)[0]
    text_offset = struct.unpack_from("<I", data, 0x0E)[0]
    entries: list[bytes] = []
    for index in range(count):
        offset = 0x12 + index * 0x1A
        flags = data[offset : offset + 2]
        sound = data[offset + 2 : offset + 10]
        volume_pitch = data[offset + 10 : offset + 18]
        relative, length = struct.unpack_from("<II", data, offset + 18)
        text = data[text_offset + relative : text_offset + relative + length]
        entries.append(flags + sound + volume_pitch + struct.pack("<I", length) + text)
    return entries


def casefold_path(path: Path) -> Path:
    if path.exists():
        return path
    matches = [candidate for candidate in path.parent.iterdir() if candidate.name.lower() == path.name.lower()]
    assert len(matches) == 1, (path, matches)
    return matches[0]


root = Path(sys.argv[1])
baseline = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
layout = sys.argv[3]
for relative, expected in baseline["files"].items():
    path = casefold_path(root / relative)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (layout, relative, expected, actual, path)

entries = tlk_entries(root / "lang/en_US/dialog.tlk")
original_count = baseline["tlk"]["count"]
assert len(entries) >= original_count, (layout, len(entries), original_count)
prefix_hash = hashlib.sha256(b"".join(entries[:original_count])).hexdigest()
assert prefix_hash == baseline["tlk"]["prefix_sha256"], (layout, prefix_hash)

override = root / "override"
remaining = [path for path in override.iterdir() if path.is_file()]
assert not any(
    path.suffix.lower() == ".spl" and path.stem.lower().startswith("ps")
    for path in remaining
), layout
assert not any(path.name.lower() == "psacon01.cre" for path in remaining), layout
for filename in (
    "psionpool.2da", "psionknown.2da", "psiondisc.2da",
    "psionskills.2da", "psionfeats.2da", "psionpowers.2da",
    "psionaugment.2da", "ps1eray.2da", "ps1mthr.2da",
    "ps1vigr.2da", "ps2aaff.2da", "mxpsion.2da",
    "clabpsee.2da", "clabpsha.2da", "clabpkin.2da",
    "clabpego.2da", "clabpnom.2da", "clabptel.2da",
):
    assert not (override / filename).exists(), (layout, filename)
print(f"WeiDU {layout} fixture uninstall restored tables, ITMs, and original TLK entries.")
PY
}

install
verify_installed
uninstall
verify_uninstalled
install
verify_installed
