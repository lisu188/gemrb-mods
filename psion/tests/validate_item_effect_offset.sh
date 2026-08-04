#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_item_effect_offset.sh GEMRB_ROOT}"
game="${RUNNER_TEMP:-/tmp}/psion-itm-offset-game"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game" \
  --layout normalized
cp -R "$repo_root/psion" "$game/psion"

python3 - "$game/override/PSOFFSET.ITM" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
# Header plus two pre-existing 0x30-byte effects. Effect 0 deliberately lies
# before the equipping block; effect 1 is the existing equipping effect.
data = bytearray(0x72 + 2 * 0x30)
data[:8] = b"ITM V1  "
struct.pack_into("<I", data, 0x64, 0x72)  # ability offset
struct.pack_into("<H", data, 0x68, 0)     # no abilities needed for this test
struct.pack_into("<I", data, 0x6A, 0x72)  # common effect table
struct.pack_into("<H", data, 0x6E, 1)     # equipping block begins at effect 1
struct.pack_into("<H", data, 0x70, 1)     # one existing equipping effect
struct.pack_into("<H", data, 0x72, 12)    # sentinel before equipping block
struct.pack_into("<H", data, 0x72 + 0x30, 42)  # existing equipping sentinel
path.write_bytes(data)
PY

cat > "$game/setup-psion-itm-offset-test.tp2" <<'TP2'
BACKUP ~psion-itm-offset-test/backup~
AUTHOR ~Psion regression fixture~
LANGUAGE ~English~ ~en_US~ ~psion/tra/english.tra~

BEGIN ~Psion ITM equipping offset regression~
INCLUDE ~psion/lib/spell-functions.tpa~
COPY_EXISTING ~PSOFFSET.ITM~ ~override~
  LPF ADD_ITEM_EQEFFECT
    INT_VAR
      opcode = 319
      target = 2
      parameter1 = 123
      parameter2 = 5
      timing = 2
  END
BUT_ONLY
TP2

(
  cd "$game"
  weidu setup-psion-itm-offset-test.tp2 \
    --use-lang en_US \
    --force-install 0 \
    --no-exit-pause
)

python3 - "$game/override/PSOFFSET.ITM" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = path.read_bytes()
effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
equipping_index = struct.unpack_from("<H", data, 0x6E)[0]
equipping_count = struct.unpack_from("<H", data, 0x70)[0]
assert equipping_index == 1, equipping_index
assert equipping_count == 2, equipping_count
assert len(data) == 0x72 + 3 * 0x30, len(data)

def effect(index: int) -> tuple[int, int, int, int, int]:
    offset = effect_offset + index * 0x30
    return (
        struct.unpack_from("<H", data, offset)[0],
        data[offset + 0x02],
        struct.unpack_from("<I", data, offset + 0x04)[0],
        struct.unpack_from("<I", data, offset + 0x08)[0],
        data[offset + 0x0C],
    )

# The effect before the equipping block and the existing equipping effect must
# remain byte-aligned and intact. The new restriction must be appended at index 2.
assert effect(0)[0] == 12, effect(0)
assert effect(1)[0] == 42, effect(1)
assert effect(2) == (319, 2, 123, 5, 2), effect(2)
print("Psion ITM nonzero equipping-index regression passed.")
PY
