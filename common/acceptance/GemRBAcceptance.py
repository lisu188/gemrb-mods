"""Read-only observations for disposable real-engine acceptance GUIScripts.

Copy this module into the fixture's GUIScripts directory, never an installed
production tree. Expected values must come from rules/resources or a recorded
baseline, independently of the observed value. This module does not advance
gameplay, grant XP, repair state, or claim that a scenario passed.
"""

import json

CHECKPOINT_PREFIX = "GEMRB_ACCEPTANCE_CHECKPOINT|"


def checkpoint(checkpoint_id, actual, expected, context=None):
    """Emit JSON evidence; the external runner determines success or failure."""
    if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
        raise ValueError("checkpoint id must be a non-empty string")
    if checkpoint_id != checkpoint_id.strip():
        raise ValueError("checkpoint id must not have surrounding whitespace")
    record = {"id": checkpoint_id, "actual": actual, "expected": expected}
    if context is not None:
        if not isinstance(context, dict):
            raise ValueError("checkpoint context must be an object")
        record["context"] = context
    # Console.Exec wraps stdout in a write-only OutputCapture. Its write()
    # forwards this newline to Main.stdioWrapper, which flushes the engine log.
    print(CHECKPOINT_PREFIX + json.dumps(record, sort_keys=True, allow_nan=False))
    return record


def capture_actor(actor, stats, variables=(), base=False):
    """Read named stat IDs and global GUI variables from the current engine.

    Example: capture_actor(1, {"class": IE_CLASS, "kit": IE_KIT}).
    Pass base=True when the expected oracle concerns unmodified actor stats.
    Additional observations (spellbook, tables, class-runtime pool accessors)
    can be supplied directly to checkpoint using their read-only engine APIs.
    """
    import GemRB

    return {
        "actor": actor,
        "stats": {name: GemRB.GetPlayerStat(actor, stat, int(base)) for name, stat in stats.items()},
        "variables": {name: GemRB.GetVar(name) for name in variables},
    }
