#!/usr/bin/env python3
from pathlib import Path
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time

DEFAULT_SCREENS = (
    "class-selection",
    "class-description",
    "alignment",
    "proficiencies",
)

SCREEN_INSTRUCTIONS = {
    "class-selection": "Open the class-selection screen with Fighter and the installed custom classes visible.",
    "class-description": "Select Cipher, Psion, or Sorcerer/Monk so its intended class description is visible.",
    "alignment": "Advance a custom class to the alignment screen without selecting an alignment yet.",
    "proficiencies": "Advance a custom class to the weapon-proficiency screen before opening a proficiency description.",
    "psion-discipline": "Open the Psion discipline chooser and leave its introductory help visible.",
}


def screenshot_command(output):
    candidates = (
        ("gnome-screenshot", ["gnome-screenshot", "-f", str(output)]),
        ("scrot", ["scrot", str(output)]),
        ("grim", ["grim", str(output)]),
        ("import", ["import", "-window", "root", str(output)]),
    )
    for executable, command in candidates:
        if shutil.which(executable):
            return command
    raise RuntimeError("No screenshot utility found; install gnome-screenshot, scrot, grim, or ImageMagick import")


def capture(output):
    command = screenshot_command(output)
    subprocess.run(command, check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Screenshot utility produced no image: {output}")
    return command[0]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Launch GemRB and record live chargen text screenshots plus engine logs."
    )
    parser.add_argument("--output", type=Path, default=Path("chargen-text-acceptance"))
    parser.add_argument("--screen", action="append", choices=tuple(SCREEN_INSTRUCTIONS))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("GemRB launch command is required after --")
    return args


def terminate(process):
    if process.poll() is not None:
        return process.returncode
    process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def main(argv=None):
    args = parse_args(argv)
    screens = args.screen or list(DEFAULT_SCREENS)
    output = args.output.resolve()
    screenshots = output / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    log_path = output / "gemrb.log"
    manifest_path = output / "manifest.json"

    started = dt.datetime.now(dt.timezone.utc)
    records = []
    backend = None
    process = None
    returncode = None

    with log_path.open("w", encoding="utf-8") as log:
        log.write("command: %s\n" % " ".join(args.command))
        log.flush()
        process = subprocess.Popen(
            args.command,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        time.sleep(1)
        if process.poll() is not None:
            raise RuntimeError(f"GemRB exited before capture with code {process.returncode}; see {log_path}")

        try:
            for index, screen in enumerate(screens, 1):
                instruction = SCREEN_INSTRUCTIONS[screen]
                input(f"[{index}/{len(screens)}] {instruction}\nPress Enter to capture {screen}: ")
                target = screenshots / f"{index:02d}-{screen}.png"
                backend = capture(target)
                records.append({
                    "screen": screen,
                    "instruction": instruction,
                    "screenshot": str(target.relative_to(output)),
                    "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
                print(target)
        finally:
            returncode = terminate(process)

    finished = dt.datetime.now(dt.timezone.utc)
    manifest = {
        "command": args.command,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "screenshot_backend": backend,
        "engine_log": str(log_path.relative_to(output)),
        "engine_returncode": returncode,
        "captures": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
