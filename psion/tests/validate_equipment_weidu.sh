#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || exit 127
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_equipment_weidu.sh GEMRB_ROOT}"
game="${RUNNER_TEMP:-/tmp}/psion-equipment-game"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" --gemrb-root "$gemrb_root" --output "$game" --layout normalized
cp -R "$repo_root/common" "$game/common"
cp -R "$repo_root/psion" "$game/psion"

python3 - "$game/override" <<'PY'
import struct
import sys
from pathlib import Path

override = Path(sys.argv[1])
for name in ("AMUL01", "BRAC01", "RING01", "BELT01", "BOOT01", "HELM01"):
    data = bytearray(0x72)
    data[:8] = b"ITM V1  "
    struct.pack_into("<I", data, 0x64, 0x72)
    struct.pack_into("<H", data, 0x68, 0)
    struct.pack_into("<I", data, 0x6A, 0x72)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 0)
    (override / f"{name}.ITM").write_bytes(data)
PY

(
  cd "$game"
  weidu psion/setup-psion.tp2 --use-lang en_US --force-install 0 --no-exit-pause
  weidu psion/setup-psion.tp2 --use-lang en_US --force-install 200 --no-exit-pause
)

python3 - "$game/override" <<'PY'
import struct
import sys
from pathlib import Path

override = Path(sys.argv[1])
expected_bonus = {
    "PSIITM01": (19,),
    "PSIITM02": (0,),
    "PSIITM03": (29,),
    "PSIITM04": (10,),
    "PSIITM05": (126,),
    "PSIITM06": (19, 37),
}
class_ids = []
for name, bonuses in expected_bonus.items():
    path = override / f"{name}.ITM"
    assert path.exists(), path
    data = path.read_bytes()
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    first = struct.unpack_from("<H", data, 0x6E)[0]
    count = struct.unpack_from("<H", data, 0x70)[0]
    assert count == 1 + len(bonuses), (name, count)
    effects = []
    for index in range(first, first + count):
        offset = effect_offset + index * 0x30
        effects.append((
            struct.unpack_from("<H", data, offset)[0],
            data[offset + 0x02],
            data[offset + 0x03],
            struct.unpack_from("<I", data, offset + 0x04)[0],
            struct.unpack_from("<I", data, offset + 0x08)[0],
            data[offset + 0x0C],
        ))
    restriction = effects[0]
    assert restriction[0] == 319, (name, restriction)
    assert restriction[1] == 2, (name, restriction)
    assert restriction[2] == 1, (name, restriction)
    assert restriction[4] == 5, (name, restriction)
    assert restriction[5] == 2, (name, restriction)
    class_ids.append(restriction[3])
    assert tuple(effect[0] for effect in effects[1:]) == bonuses, (name, effects)
assert len(set(class_ids)) == 6, class_ids
print("Psion equipment install validation passed")
PY

(
  cd "$game"
  weidu psion/setup-psion.tp2 --use-lang en_US --force-uninstall 200 --no-exit-pause
)

python3 - "$game/override" <<'PY'
import sys
from pathlib import Path
override = Path(sys.argv[1])
for index in range(1, 7):
    assert not (override / f"PSIITM{index:02d}.ITM").exists()
print("Psion equipment uninstall validation passed")
PY
