#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || exit 127
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_late_item_weidu.sh GEMRB_ROOT}"
game="$RUNNER_TEMP/psion-late-item-game"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game" \
  --layout normalized
cp -R "$repo_root/common" "$game/common"
cp -R "$repo_root/psion" "$game/psion"

(
  cd "$game"
  weidu psion/setup-psion.tp2 --use-lang en_US --force-install 0 --no-exit-pause
)

python3 - "$game/override/PSLATE.ITM" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = bytearray(0x72)
data[:8] = b"ITM V1  "
struct.pack_into("<H", data, 0x1C, 2)
struct.pack_into("<I", data, 0x1E, 0)
struct.pack_into("<I", data, 0x64, 0x72)
struct.pack_into("<H", data, 0x68, 0)
struct.pack_into("<I", data, 0x6A, 0x72)
struct.pack_into("<H", data, 0x6E, 0)
struct.pack_into("<H", data, 0x70, 0)
path.write_bytes(data)
PY

(
  cd "$game"
  weidu psion/setup-psion.tp2 --use-lang en_US --force-install 100 --no-exit-pause
)

python3 - "$game" <<'PY'
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
override = root / "override"
disciplines = {
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
}
class_ids = {}
for line in (override / "class.ids").read_text(encoding="utf-8", errors="replace").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1] in disciplines:
        class_ids[fields[1]] = int(fields[0], 0)
assert set(class_ids) == disciplines, class_ids


def restrictions(path):
    data = path.read_bytes()
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    first = struct.unpack_from("<H", data, 0x6E)[0]
    count = struct.unpack_from("<H", data, 0x70)[0]
    result = []
    for index in range(count):
        offset = effect_offset + (first + index) * 0x30
        result.append((
            struct.unpack_from("<H", data, offset)[0],
            data[offset + 0x02],
            struct.unpack_from("<I", data, offset + 0x04)[0],
            struct.unpack_from("<I", data, offset + 0x08)[0],
            data[offset + 0x0C],
        ))
    return result

for name in ("PSLATE.ITM", "PSMACE.ITM"):
    effects = restrictions(override / name)
    assert len(effects) == 6, (name, effects)
    assert {effect[2] for effect in effects} == set(class_ids.values()), (name, effects)
    assert all((opcode, target, parameter2, timing) == (319, 2, 5, 2)
               for opcode, target, _, parameter2, timing in effects), (name, effects)

print("Psion late item compatibility validation passed")
PY
