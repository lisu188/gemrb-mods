from pathlib import Path
import shutil
import sys
import tempfile

from weidu_smoke import build_fixture, run_weidu, write_2da


def read_2da(path):
    lines = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.split()]
    return lines[2], lines[3:]


def verify_live_monk_column(override, expected):
    headers, rows = read_2da(override / "weapprof.2da")
    monk = headers.index("MONK") + 1
    sorcerer_monk = headers.index("SORCERER_MONK") + 1
    assert len(rows) == len(expected), (len(rows), len(expected))
    assert [row[monk] for row in rows] == expected
    assert [row[sorcerer_monk] for row in rows] == expected


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")

    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-weapprof-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"

        expected = [str((i * 2 + i // 3) % 3) for i in range(63)]
        rows = [(f"PROF{i:02d}", [0, expected[i]]) for i in range(len(expected))]
        write_2da(override / "weapprof.2da", ["MAGE", "MONK"], rows, default="0")
        original = (override / "weapprof.2da").read_bytes()

        run_weidu(weidu, game, "--force-install-list", "0")
        verify_live_monk_column(override, expected)
        print("live Monk WEAPPROF column install: OK", flush=True)

        run_weidu(weidu, game, "--reinstall")
        verify_live_monk_column(override, expected)
        print("live Monk WEAPPROF column reinstall: OK", flush=True)

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert (override / "weapprof.2da").read_bytes() == original
        print("live Monk WEAPPROF uninstall restore: OK", flush=True)


if __name__ == "__main__":
    main()
