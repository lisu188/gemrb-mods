#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_save_weidu.sh GEMRB_ROOT}"

for layout in normalized native legacy; do
  case "$layout" in
    normalized) levels=20 ;;
    native) levels=41 ;;
    legacy) levels=40 ;;
  esac

  game="$RUNNER_TEMP/psion-save-game-$layout"
  python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
    --gemrb-root "$gemrb_root" \
    --output "$game" \
    --layout "$layout"

  # Exercise different real-game table widths. The generic vendor seed only
  # exists so the broader lifecycle test can install; this dedicated test
  # rewrites SAVEWIZ inside each generated game before installation.
  python3 - "$game/override/savewiz.2da" "$levels" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
levels = int(sys.argv[2])
columns = [str(level) for level in range(1, levels + 1)]
starts = [14, 12, 13, 15, 11]
rows = []
for row, start in enumerate(starts):
    values = [str(max(1, start - min((level - 1) // 4, 8))) for level in range(1, levels + 1)]
    rows.append(f"{row} " + " ".join(values))
path.write_text(
    "2DA V1.0\n20\n        " + " ".join(columns) + "\n" + "\n".join(rows) + "\n",
    encoding="ascii",
)
PY

  cp -R "$repo_root/psion" "$game/psion"
  before_sha="$(sha256sum "$game/override/savewiz.2da" | awk '{print $1}')"

  install() {
    (
      cd "$game"
      weidu psion/setup-psion.tp2 --use-lang en_US --force-install 0 --no-exit-pause
    )
  }

  uninstall() {
    (
      cd "$game"
      weidu psion/setup-psion.tp2 --use-lang en_US --force-uninstall 0 --no-exit-pause
    )
  }

  verify_installed() {
    python3 - "$game" "$layout" "$levels" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
layout = sys.argv[2]
levels = int(sys.argv[3])
override = root / "override"
disciplines = {
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
}


def find_casefold(directory: Path, name: str) -> Path:
    matches = [path for path in directory.iterdir() if path.name.lower() == name.lower()]
    assert len(matches) == 1, (layout, name, matches)
    return matches[0]


def read_2da(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    assert lines[0].strip().upper() == "2DA V1.0", (layout, path)
    columns = lines[2].split()
    rows = {}
    for line in lines[3:]:
        fields = line.split()
        if fields:
            rows[fields[0]] = fields[1:]
    return columns, rows

savewiz = find_casefold(override, "savewiz.2da")
savepsi = find_casefold(override, "savepsi.2da")
wiz_cols, wiz_rows = read_2da(savewiz)
psi_cols, psi_rows = read_2da(savepsi)
assert len(wiz_cols) == levels == len(psi_cols), (layout, len(wiz_cols), len(psi_cols), levels)
assert wiz_cols == psi_cols, (layout, wiz_cols, psi_cols)
assert list(wiz_rows) == ["0", "1", "2", "3", "4"], (layout, wiz_rows)
assert list(psi_rows) == ["0", "1", "2", "3", "4"], (layout, psi_rows)
for row in ("0", "2", "3"):
    assert psi_rows[row] == wiz_rows[row], (layout, row, psi_rows[row], wiz_rows[row])
for row in ("1", "4"):
    expected = [str(int(value) - 2) for value in wiz_rows[row]]
    assert psi_rows[row] == expected, (layout, row, psi_rows[row], expected)

class_cols, class_rows = read_2da(find_casefold(override, "classes.2da"))
assert "SAVE" in class_cols, (layout, class_cols)
save_col = class_cols.index("SAVE")
for discipline in disciplines:
    assert discipline in class_rows, (layout, discipline)
    assert class_rows[discipline][save_col] == "SAVEPSI", (
        layout, discipline, class_rows[discipline][save_col]
    )
print(f"{layout}: SAVEPSI matches Mage physical saves and improves wands/spells by 2")
PY
  }

  install
  verify_installed
  uninstall

  after_sha="$(sha256sum "$game/override/savewiz.2da" | awk '{print $1}')"
  test "$before_sha" = "$after_sha"
  if find "$game/override" -maxdepth 1 -type f -iname 'savepsi.2da' | grep -q .; then
    echo "$layout: SAVEPSI.2DA remained after uninstall" >&2
    exit 1
  fi

  install
  verify_installed
done

echo "Psion saving throw install/uninstall/reinstall validation passed."
