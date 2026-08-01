#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_startup_weidu.sh GEMRB_ROOT}"
game="$RUNNER_TEMP/psion-startup-weidu-game"
baseline="$RUNNER_TEMP/psion-startup-baseline.json"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game" \
  --layout normalized

# The generic installer fixture intentionally contains only tables required by
# every supported campaign. Add BG2-family chargen tables here so the optional
# STRTGOLD and ToB 25STWEAP branches execute under real WeiDU.
python3 - "$game" "$baseline" <<'PY'
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
override = root / "override"


def write_2da(path: Path, columns: tuple[str, ...], rows: tuple[tuple[str, ...], ...], default="*") -> None:
    lines = ["2DA V1.0", default, "    " + " ".join(columns)]
    lines.extend(" ".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Deliberately non-canonical Mage dice prove the installer copies the active
# game's row rather than embedding BG2 constants.
write_2da(
    override / "strtgold.2da",
    ("SIDES", "ROLLS", "MODIFIER", "MULTIPLIER"),
    (
        ("MAGE", "6", "2", "3", "7"),
        ("FIGHTER", "4", "3", "5", "10"),
    ),
    default="0",
)

mage = (
    "*", "*", "*", "BAG29", "RING06", "RING40", "*", "BOOT01",
    "AMUL21", "BRAC15", "BELT10", "AROW11,40", "BULL03,40", "BOLT06,40",
    "POTN52,5", "POTN04,2", "POTN14,5", "SLNG05", "DAGG05,20", "STAF20",
)
slots = (
    "ARMOR", "SHIELD", "HELM", "BAG", "RING1", "RING2", "CLOAK", "BOOTS",
    "AMULET", "BRACERS", "BELT", "AMMO1", "AMMO2", "AMMO3", "MISC1",
    "MISC2", "MISC3", "MISC4", "MISC5", "WEAPON1",
)
rows = tuple(
    (slot, str(index), str(8000 + index), str(9000 + index), mage[index], "*")
    for index, slot in enumerate(slots)
)
write_2da(
    override / "25stweap.2da",
    ("ID", "NAME_REF", "DESC_REF", "MAGE", "FIGHTER"),
    rows,
)

files = (override / "strtgold.2da", override / "25stweap.2da")
Path(sys.argv[2]).write_text(
    json.dumps(
        {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)
PY

# Regenerate CHITIN.KEY after adding the optional fixture resources.
python3 "$gemrb_root/tools/demo_key_file.py" "$game"
cp -R "$repo_root/psion" "$game/psion"

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
  python3 - "$game" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "override"
disciplines = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)


def read_2da(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    columns = lines[2].split()
    rows = []
    for line in lines[3:]:
        fields = line.split()
        if fields:
            rows.append(fields)
    return columns, rows


columns, rows = read_2da(root / "strtgold.2da")
by_name = {row[0]: row[1:] for row in rows}
assert by_name["MAGE"] == ["6", "2", "3", "7"], by_name["MAGE"]
for discipline in disciplines:
    assert by_name.get(discipline) == by_name["MAGE"], (
        discipline, by_name.get(discipline), by_name["MAGE"]
    )

columns, rows = read_2da(root / "25stweap.2da")
mage_column = columns.index("MAGE")
for discipline in disciplines:
    assert discipline in columns, (discipline, columns)
    discipline_column = columns.index(discipline)
    for row in rows:
        # +1 because row[0] is the 2DA row name and columns excludes it.
        assert row[1 + discipline_column] == row[1 + mage_column], (
            discipline, row[0], row[1 + discipline_column], row[1 + mage_column]
        )

print("Psion startup tables installed with Mage-equivalent data.")
PY
}

verify_uninstalled() {
  python3 - "$game" "$baseline" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "override"
baseline = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for name, expected in baseline.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert actual == expected, (name, actual, expected)
print("Psion startup tables restored byte-for-byte after uninstall.")
PY
}

install
verify_installed
uninstall
verify_uninstalled
install
verify_installed
