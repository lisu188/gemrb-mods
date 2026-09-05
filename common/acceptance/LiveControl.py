"""Private file mailbox for driving disposable GemRB acceptance sessions.

This is a test console, not a production GUI module. Its expressions run on
GemRB's GUI thread, like the in-game console, and every request/result is kept
in the private session directory for reproduction.
"""

import json
import os
from pathlib import Path
import stat
import traceback

import GemRB

_session = None
_namespace = {"GemRB": GemRB}


def private_session(session):
    """Keep the executable mailbox private, including when supplied externally."""
    details = session.lstat()
    if (not stat.S_ISDIR(details.st_mode) or details.st_mode & 0o077
            or not hasattr(os, "getuid") or details.st_uid != os.getuid()):
        raise RuntimeError("acceptance session must be an owner-only directory owned by this user")
    return session.resolve()


def _poll():
    private_session(_session)
    for path in sorted(_session.glob("*.request.json")):
        result_path = path.with_name(path.name.replace(".request.json", ".result.json"))
        if result_path.exists():
            continue
        try:
            request = json.loads(path.read_text(encoding="utf-8"))
            value = eval(request["expression"], _namespace)
            result = {"id": request["id"], "value": value}
        except Exception:
            detail = traceback.format_exc()
            print(detail, flush=True)
            result = {"error": detail}
        result_path.write_text(json.dumps(result, default=str) + "\n", encoding="utf-8")


def start():
    global _session
    location = os.environ.get("GEMRB_ACCEPTANCE_SESSION")
    if not location or _session is not None:
        return
    _session = private_session(Path(location))
    GemRB.SetTimer(_poll, 100)
    print("GEMRB_ACCEPTANCE_CONSOLE_READY", flush=True)


def controls(group, window_id, control_ids):
    """Observe rendered control text and positions for real mouse interaction."""
    window = GemRB.GetView(group, window_id)
    if not window:
        return None
    frame = window.GetFrame()
    result = {"frame": frame, "visible": window.IsVisible(), "controls": {}}
    for control_id in control_ids:
        control = window.GetControl(control_id)
        if control:
            control_frame = control.GetFrame()
            result["controls"][control_id] = {
                "text": control.QueryText(), "frame": control_frame,
                "visible": control.IsVisible(), "flags": control.Flags,
                "value": control.Value, "variable": control.VarName,
                "center": [frame["x"] + control_frame["x"] + control_frame["w"] // 2,
                           frame["y"] + control_frame["y"] + control_frame["h"] // 2],
            }
    return result
