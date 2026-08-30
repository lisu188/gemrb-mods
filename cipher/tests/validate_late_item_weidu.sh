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

python3 - "$game/override/CILATE.ITM" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
header_offset = 0x72
effect_offset = header_offset + 0x38
data = bytearray(effect_offset)
data[:8] = b"ITM V1  "
struct.pack_into("<I", data, 0x64, header_offset)
struct.pack_into("<H", data, 0x68, 1)
struct.pack_into("<I", data, 0x6A, effect_offset)
struct.pack_into("<H", data, 0x6E, 0)
struct.pack_into("<H", data, 0x70, 0)
data[header_offset] = 1
data[header_offset + 0x02] = 1
struct.pack_into("<H", data, header_offset + 0x1E, 0)
struct.pack_into("<H", data, header_offset + 0x20, 0)
path.write_bytes(data)
PY

(
  cd "$game"
  weidu cipher/setup-cipher.tp2 --use-lang en_US --force-install 100 --no-exit-pause
)

python3 - "$game/override/CILATE.ITM" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = path.read_bytes()
header_offset = struct.unpack_from("<I", data, 0x64)[0]
effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
count = struct.unpack_from("<H", data, header_offset + 0x1E)[0]
first = struct.unpack_from("<H", data, header_offset + 0x20)[0]
assert count == 1, count
offset = effect_offset + first * 0x30
assert struct.unpack_from("<H", data, offset)[0] == 326
assert data[offset + 0x02] == 2
assert data[offset + 0x0C] == 1
resource = data[offset + 0x14:offset + 0x1C].rstrip(b"\x00").decode("ascii")
assert resource == "CIFGAIN", resource
print("Cipher late item compatibility validation passed")
PY
