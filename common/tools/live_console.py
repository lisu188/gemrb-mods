#!/usr/bin/env python3
"""Send an expression to a private, instrumented real GemRB test process."""

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import time
import uuid


def private_session(session):
    """Refuse shared/symlink mailboxes: requests execute with engine privileges."""
    details = session.lstat()
    if (not stat.S_ISDIR(details.st_mode) or details.st_mode & 0o077
            or not hasattr(os, "getuid") or details.st_uid != os.getuid()):
        raise RuntimeError("acceptance session must be an owner-only directory owned by this user")
    return session.resolve()


def prepare(guiscripts, session):
    guiscripts = guiscripts.resolve()
    session.mkdir(parents=True, exist_ok=True, mode=0o700)
    session = private_session(session)
    source = Path(__file__).resolve().parents[1] / "acceptance"
    for name in ("LiveControl.py", "GemRBAcceptance.py"):
        shutil.copy2(source / name, guiscripts / name)
    entrypoint = guiscripts / "bg2" / "Start.py"
    marker = "\n# Disposable acceptance console\nimport LiveControl\nLiveControl.start()\n"
    content = entrypoint.read_text(encoding="utf-8")
    if marker not in content:
        backup = entrypoint.with_suffix(".py.acceptance-backup")
        if backup.exists():
            raise RuntimeError("acceptance backup already exists; inspect the disposable target")
        shutil.copy2(entrypoint, backup)
        entrypoint.write_text(content + marker, encoding="utf-8")
    print("Set GEMRB_ACCEPTANCE_SESSION=" + str(session.resolve()) + " when launching GemRB")


def request(session, expression, timeout):
    session = private_session(session)
    request_id = str(time.time_ns()) + "-" + uuid.uuid4().hex[:8]
    path = session / (request_id + ".request.json")
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps({"id": request_id, "expression": expression}) + "\n", encoding="utf-8")
    os.replace(pending, path)
    response = session / (request_id + ".result.json")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response.exists():
            try:
                result = json.loads(response.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(0.05)
                continue
            print(json.dumps(result, indent=2))
            return 1 if "error" in result else 0
        time.sleep(0.1)
    raise TimeoutError("engine did not answer " + request_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--prepare", type=Path, metavar="DISPOSABLE_GUISCRIPTS")
    parser.add_argument("--expression")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if bool(args.prepare) == bool(args.expression):
        parser.error("choose exactly one of --prepare or --expression")
    if args.prepare:
        prepare(args.prepare, args.session)
        return 0
    return request(args.session, args.expression, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
