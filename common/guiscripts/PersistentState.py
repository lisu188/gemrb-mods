# SPDX-License-Identifier: GPL-2.0-or-later
"""Save-safe integer state carried by private serialized actor effects."""
import GemRB


def read(actor, opcode, marker, resource):
    resource = str(resource).upper()
    try:
        for effect in GemRB.GetEffects(actor, opcode):
            if int(effect.get("Param2", -1)) != int(marker):
                continue
            if str(effect.get("Resource1", "")).upper() != resource:
                continue
            return True, max(0, int(effect.get("Param1", 0)))
    except Exception:
        return False, 0
    return False, 0


def write(actor, opcode, marker, resource, value, source=""):
    value = max(0, int(value))
    GemRB.DispelEffect(actor, opcode, marker)
    GemRB.ApplyEffect(actor, opcode, value, marker, resource, "", "", source)
    return value


def remove(actor, opcode, marker):
    GemRB.DispelEffect(actor, opcode, marker)
