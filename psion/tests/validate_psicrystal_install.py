#!/usr/bin/env python3
"""Validate current psicrystal installation and exact WeiDU rollback."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def snapshot(directory):
    result = {}
    for path in directory.iterdir():
        if not path.is_file():
            continue
        key = path.name.casefold()
        if key in result:
            raise AssertionError("case-ambiguous resource: " + key)
        result[key] = path.read_bytes()
    return result


def verify(game):
    subprocess.run(
        [sys.executable, str(ROOT / "psion/tests/verify_psicrystal_install.py"), str(game)],
        check=True,
    )


def run_weidu(weidu, game, action, log):
    command = [
        str(weidu),
        "psion/setup-psion.tp2",
        "--use-lang",
        "en_US",
        "--no-exit-pause",
        action,
        "0",
    ]
    with log.open("a") as output:
        result = subprocess.run(
            command,
            cwd=game,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
    if result.returncode:
        raise AssertionError(log.read_text(errors="replace")[-6000:])


def lifecycle(weidu, gemrb, parent):
    game = parent / "game"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "psion/tests/seed_savewiz_fixture.py"),
            str(gemrb),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "psion/tests/make_weidu_fixture.py"),
            "--gemrb-root",
            str(gemrb),
            "--output",
            str(game),
        ],
        check=True,
    )
    for name in ("common", "psion"):
        shutil.copytree(ROOT / name, game / name)

    before = snapshot(game / "override")
    log = parent / "weidu.log"

    for action in ("--force-install", "--force-uninstall", "--force-install", "--force-uninstall"):
        run_weidu(weidu, game, action, log)
        if action == "--force-install":
            verify(game)
        else:
            after = snapshot(game / "override")
            changed = sorted(
                key
                for key in before.keys() & after.keys()
                if before[key] != after[key]
            )
            assert before == after, (
                sorted(before.keys() ^ after.keys()),
                changed,
            )

    print("Current psicrystal resources install, uninstall, reinstall and restore exactly")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("weidu", type=Path)
    parser.add_argument("gemrb", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="psicrystal-weidu-") as folder:
        lifecycle(args.weidu.resolve(), args.gemrb.resolve(), Path(folder))


if __name__ == "__main__":
    main()
