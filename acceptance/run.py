#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REJECT_PATTERNS = (
    "Traceback (most recent call last):",
    "ModuleNotFoundError:",
    "ImportError:",
)


def write_config(path: Path, game: Path, guiscripts: Path, save_path: Path) -> None:
    text = "\n".join(
        [
            f"GamePath={game.resolve()}",
            f"SavePath={save_path.resolve()}",
            f"GUIScriptsPath={guiscripts.resolve()}",
            "GameType=auto",
            "AudioDriver=none",
            "Logging=1",
            "SkipIntroVideos=1",
            "EnableCheatKeys=1",
            "Width=1280",
            "Height=720",
            "FullScreen=0",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def run_command(command: list[str], cwd: Path, log: Path, timeout: int | None = None) -> int:
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        process = subprocess.run(
            command,
            cwd=cwd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    return process.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--guiscripts", type=Path, required=True)
    parser.add_argument("--gemrb", default="gemrb")
    parser.add_argument("--gemrb-revision", required=True)
    parser.add_argument("--profile", choices=("bgee", "bg2ee", "eet"), required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--manual-result", choices=("pass", "fail", "not-run"), default="not-run")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "acceptance" / "artifacts")
    parser.add_argument("--save-path", type=Path)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--expect-log", action="append", default=[])
    parser.add_argument("--reject-log", action="append", default=[])
    parser.add_argument("--skip-launch", action="store_true")
    args = parser.parse_args()

    if not args.game.is_dir():
        raise SystemExit(f"Game directory does not exist: {args.game}")
    if not args.guiscripts.is_dir():
        raise SystemExit(f"GUIScripts directory does not exist: {args.guiscripts}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.artifacts / f"{args.profile}-{args.scenario}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    save_path = args.save_path or args.game
    config = run_dir / "gemrb.cfg"
    log = run_dir / "gemrb.log"
    write_config(config, args.game, args.guiscripts, save_path)

    reject_patterns = list(dict.fromkeys([*DEFAULT_REJECT_PATTERNS, *args.reject_log]))
    result = {
        "schema": 2,
        "profile": args.profile,
        "scenario": args.scenario,
        "started_utc": stamp,
        "game": str(args.game.resolve()),
        "guiscripts": str(args.guiscripts.resolve()),
        "gemrb_revision": args.gemrb_revision,
        "config": str(config.resolve()),
        "log": str(log.resolve()),
        "expected_log_patterns": args.expect_log,
        "rejected_log_patterns": reject_patterns,
        "manual_result": args.manual_result,
        "launch_skipped": args.skip_launch,
    }

    if args.skip_launch:
        return_code = 0
        log.write_text("launch skipped\n", encoding="utf-8")
    else:
        try:
            return_code = run_command([args.gemrb, "-q", "-c", str(config)], ROOT, log, args.timeout)
        except subprocess.TimeoutExpired:
            return_code = 124
            with log.open("a", encoding="utf-8") as handle:
                handle.write("\nacceptance runner: GemRB timed out\n")

    text = log.read_text(encoding="utf-8", errors="replace")
    missing = [pattern for pattern in args.expect_log if pattern not in text]
    rejected = [pattern for pattern in reject_patterns if pattern in text]
    engine_passed = return_code == 0 and not missing and not rejected
    accepted = engine_passed and args.manual_result == "pass" and not args.skip_launch
    result["return_code"] = return_code
    result["missing_log_patterns"] = missing
    result["matched_rejected_log_patterns"] = rejected
    result["engine_passed"] = engine_passed
    result["passed"] = accepted
    (run_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(run_dir)
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
