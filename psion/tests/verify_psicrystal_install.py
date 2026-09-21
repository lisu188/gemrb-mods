#!/usr/bin/env python3
"""Inspect actual installed companion resources produced by WeiDU."""
from pathlib import Path
import struct
import sys


def main():
    game = Path(sys.argv[1])
    resources = {path.name.lower(): path for path in (game / "override").iterdir()}
    for name in ("pscrbody.cre", "pscrai.bcs", "pscrani.bam", "pxcrsum.spl", "pxcrdis.spl", "pscrlvl.2da"):
        assert name in resources, name
    creature = resources["pscrbody.cre"].read_bytes()
    assert creature[:8] == b"CRE V1.0"
    assert creature[0x270] == 5 and creature[0x271] == 0
    assert creature[0x248:0x250].rstrip(b"\0") == b"PSCRAI"
    animation = struct.unpack_from("<I", creature, 0x28)[0]
    rows = [line.split("//", 1)[0].split() for line in resources["avatars.2da"].read_text().splitlines()[3:]]
    own = [row for row in rows if row and not row[0].startswith("#") and int(row[0], 0) == animation]
    assert len(own) == 1 and [item.upper() for item in own[0][1:]] == ["PSCRANI"] * 4 + ["1", "1", "1", "*"]
    bam = resources["pscrani.bam"].read_bytes()
    assert bam[:8] == b"BAM V1  " and bam[10] == 80
    assert resources["pscrai.bcs"].read_bytes().startswith(b"SC")
    for name in ("pxcrsum.spl", "pxcrdis.spl"):
        spell = resources[name].read_bytes()
        assert spell[:8] == b"SPL V1  "
        header = struct.unpack_from("<I", spell, 0x64)[0]
        assert struct.unpack_from("<H", spell, 0x68)[0] == 1
        assert spell[header + 12] == 7, "management action must be instant, with no targeting cursor"
    assert not (game / ".psion-crystal-build").exists()
    print("Installed psicrystal CRE/BAM/BCS, allocated avatar and instant management actions validated")


if __name__ == "__main__":
    main()
