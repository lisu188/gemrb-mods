#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_weidu_install.sh GEMRB_ROOT}"
game="$RUNNER_TEMP/psion-weidu-game"
baseline="$RUNNER_TEMP/psion-weidu-baseline.json"

python3 "$repo_root/psion/tests/make_weidu_fixture.py" \
  --gemrb-root "$gemrb_root" \
  --output "$game"
cp -R "$repo_root/psion" "$game/psion"

# Snapshot every pre-existing table that the installer edits. WeiDU restores
# those resources byte-for-byte. DIALOG.TLK is different: uninstall preserves
# the original entries but may leave newly allocated, now-unreferenced string
# slots at the end. Record a semantic digest of the original entry prefix.
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
paths = [
    root / "override" / name
    for name in (
        "classes.2da", "clastext.2da", "clsrcreq.2da", "hpclass.2da",
        "class.ids", "alignmnt.2da", "weapprof.2da", "profs.2da",
        "xpcap.2da", "avprefc.2da", "qslots.2da", "clskills.2da",
    )
]
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
  python3 - "$game" <<'PY'
from __future__ import annotations
import sys
from pathlib import Path

root = Path(sys.argv[1])
override = root / "override"
disciplines = (
    "PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST",
    "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH",
)

for filename in (
    "classes.2da", "clastext.2da", "clsrcreq.2da", "hpclass.2da",
    "class.ids", "alignmnt.2da", "profs.2da", "xpcap.2da",
    "avprefc.2da", "qslots.2da", "clskills.2da",
):
    text = (override / filename).read_text(encoding="utf-8", errors="replace")
    for discipline in disciplines:
        assert discipline in text, (filename, discipline)

for filename in (
    "psionpool.2da", "psionknown.2da", "psiondisc.2da",
    "psionskills.2da", "psionfeats.2da", "psionpowers.2da",
    "psionaugment.2da", "ps1eray.2da", "ps1mthr.2da",
    "ps1vigr.2da", "ps2aaff.2da", "mxpsion.2da",
    "clabpsee.2da", "clabpsha.2da", "clabpkin.2da",
    "clabpego.2da", "clabpnom.2da", "clabptel.2da",
):
    assert (override / filename).is_file(), filename

# WeiDU preserves the source resource's filename case, which differs between
# platforms and fixture inputs. Inspect names semantically instead of relying on
# case-sensitive glob patterns.
generated = [path for path in override.iterdir() if path.is_file()]
spells = {
    path.name.lower()
    for path in generated
    if path.suffix.lower() == ".spl" and path.stem.lower().startswith("ps")
}
assert len(spells) >= 117, len(spells)
assert any(path.name.lower() == "psacon01.cre" for path in generated)

log = next(
    path for path in root.iterdir()
    if path.is_file() and path.name.lower() == "weidu.log"
)
log_text = log.read_text(encoding="utf-8", errors="replace")
assert "PSION/SETUP-PSION.TP2" in log_text.upper()
assert "#0 #0" in log_text
print("WeiDU fixture installation validation passed.")
PY
}

verify_uninstalled() {
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
baseline = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for relative, expected in baseline["files"].items():
    path = root / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (relative, expected, actual)

# WeiDU generally does not compact DIALOG.TLK on uninstall. Verify that every
# original entry is unchanged and in the same position; appended orphan slots
# are acceptable and will be reused by future installations.
entries = tlk_entries(root / "lang/en_US/dialog.tlk")
original_count = baseline["tlk"]["count"]
assert len(entries) >= original_count, (len(entries), original_count)
prefix_hash = hashlib.sha256(b"".join(entries[:original_count])).hexdigest()
assert prefix_hash == baseline["tlk"]["prefix_sha256"], prefix_hash

override = root / "override"
remaining = [path for path in override.iterdir() if path.is_file()]
assert not any(
    path.suffix.lower() == ".spl" and path.stem.lower().startswith("ps")
    for path in remaining
)
assert not any(path.name.lower() == "psacon01.cre" for path in remaining)
for filename in (
    "psionpool.2da", "psionknown.2da", "psiondisc.2da",
    "psionskills.2da", "psionfeats.2da", "psionpowers.2da",
    "psionaugment.2da", "ps1eray.2da", "ps1mthr.2da",
    "ps1vigr.2da", "ps2aaff.2da", "mxpsion.2da",
    "clabpsee.2da", "clabpsha.2da", "clabpkin.2da",
    "clabpego.2da", "clabpnom.2da", "clabptel.2da",
):
    assert not (override / filename).exists(), filename
print("WeiDU fixture uninstall restored tables and original TLK entries.")
PY
}

# Exercise backup creation, rollback and a clean second installation. Reinstall
# catches stale backup state and scripts that only work in a pristine directory.
install
verify_installed
uninstall
verify_uninstalled
install
verify_installed
