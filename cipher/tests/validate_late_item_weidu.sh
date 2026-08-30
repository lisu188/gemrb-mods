#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || exit 127
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_late_item_weidu.sh GEMRB_ROOT}"
game="$RUNNER_TEMP/cipher-late-item-game"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game" \
  --layout normalized
cp -R "$repo_root/common" "$game/common"
cp -R "$repo_root/cipher" "$game/cipher"

(
  cd "$game"
  weidu cipher/setup-cipher.tp2 --use-lang en_US --force-install 0 --no-exit-pause
)

python3 - "$game/override/CILATE.ITM" "$game/override/CILCHAIN.ITM" <<'PY'
import struct
import sys
from pathlib import Path


def write_item(path, *, item_type=19, animation=b"  ", attack=False):
    header_count = 1 if attack else 0
    header_offset = 0x72
    effect_offset = header_offset + 0x38 * header_count
    data = bytearray(effect_offset)
    data[:8] = b"ITM V1  "
    struct.pack_into("<H", data, 0x1C, item_type)
    data[0x22:0x24] = animation
    struct.pack_into("<I", data, 0x64, header_offset)
    struct.pack_into("<H", data, 0x68, header_count)
    struct.pack_into("<I", data, 0x6A, effect_offset)
    struct.pack_into("<H", data, 0x6E, 0)
    struct.pack_into("<H", data, 0x70, 0)
    if attack:
        data[header_offset] = 1
        data[header_offset + 0x02] = 1
        struct.pack_into("<H", data, header_offset + 0x1E, 0)
        struct.pack_into("<H", data, header_offset + 0x20, 0)
    path.write_bytes(data)


write_item(Path(sys.argv[1]), attack=True)
write_item(Path(sys.argv[2]), item_type=0x02, animation=b"3A")
PY

(
  cd "$game"
  weidu cipher/setup-cipher.tp2 --use-lang en_US --force-install 100 --no-exit-pause
)

python3 - "$game/override/CILATE.ITM" "$game/override/CILCHAIN.ITM" "$game/override/class.ids" <<'PY'
import struct
import sys
from pathlib import Path

weapon = Path(sys.argv[1]).read_bytes()
header_offset = struct.unpack_from("<I", weapon, 0x64)[0]
effect_offset = struct.unpack_from("<I", weapon, 0x6A)[0]
count = struct.unpack_from("<H", weapon, header_offset + 0x1E)[0]
first = struct.unpack_from("<H", weapon, header_offset + 0x20)[0]
assert count == 1, count
offset = effect_offset + first * 0x30
assert struct.unpack_from("<H", weapon, offset)[0] == 326
assert weapon[offset + 0x02] == 2
assert weapon[offset + 0x0C] == 1
resource = weapon[offset + 0x14:offset + 0x1C].rstrip(b"\x00").decode("ascii")
assert resource == "CIFGAIN", resource

class_id = None
for line in Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1] == "CIPHER":
        class_id = int(fields[0], 0)
        break
assert class_id is not None

armor = Path(sys.argv[2]).read_bytes()
effect_offset = struct.unpack_from("<I", armor, 0x6A)[0]
first = struct.unpack_from("<H", armor, 0x6E)[0]
count = struct.unpack_from("<H", armor, 0x70)[0]
matches = 0
for index in range(count):
    offset = effect_offset + (first + index) * 0x30
    opcode = struct.unpack_from("<H", armor, offset)[0]
    target = armor[offset + 0x02]
    parameter1 = struct.unpack_from("<I", armor, offset + 0x04)[0]
    parameter2 = struct.unpack_from("<I", armor, offset + 0x08)[0]
    timing = armor[offset + 0x0C]
    if (opcode, target, parameter1, parameter2, timing) == (319, 2, class_id, 5, 2):
        matches += 1
assert matches == 1, matches

print("Cipher late weapon and equipment compatibility validation passed")
PY
