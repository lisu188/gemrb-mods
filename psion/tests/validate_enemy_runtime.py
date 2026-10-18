#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
registered = {}


def rows(path):
    lines = [line.split() for line in path.read_text().splitlines() if line.strip() and not line.startswith("2DA") and line.strip() != "*"]
    header = lines[0]
    return {parts[0]: dict(zip(header, parts[1:])) for parts in lines[1:]}


gemrb = types.ModuleType("GemRB")
def set_nonparty(callback):
    registered["callback"] = callback
gemrb.SetNonPartySpellCastCheck = set_nonparty
sys.modules["GemRB"] = gemrb

spec = importlib.util.spec_from_file_location("GemRBModCoreEnemyTest", ROOT / "common/guiscripts/GemRBModCore.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class Handler:
    __name__ = "Psionics"
    def __init__(self):
        self.commits = []
        self.allowed = True
        self.psion = True
    def is_psion(self, actor):
        return self.psion and actor in (4242, 4243)
    def power_info(self, resref):
        return {"resref": resref, "cost": 3} if resref in {"PSENEMY", "PSENEM3", "PSENEM5"} else None
    def manifestation_plan(self, actor, resref):
        return {
            "allowed": self.allowed,
            "reason": "" if self.allowed else "power_points",
            "resref": "PSENEMY",
            "cast_resref": "PSENEM3" if actor == 4242 else "PSENEM5",
            "cost": 3,
            "pool": 10,
        }
    def commit_manifestation(self, actor, resref):
        if not self.allowed:
            return False
        self.commits.append((actor, resref))
        return True

handler = Handler()
core._handlers = lambda: [handler]
callback = registered["callback"]

assert callback(9001, "SPWI112") is True
assert callback(4242, "SPWI112") is True
assert callback(9001, "PSENEMY") is True
assert not handler.commits

assert callback(4242, "PSENEMY") == "PSENEM3"
assert handler.commits == [(4242, "PSENEMY")]
assert callback(4243, "PSENEMY") == "PSENEM5"
assert handler.commits[-1] == (4243, "PSENEMY")

handler.allowed = False
assert callback(4242, "PSENEMY") is False
assert handler.commits == [(4242, "PSENEMY"), (4243, "PSENEMY")]

handler.allowed = True
assert callback(4242, "PSENEM3") is True
assert handler.commits[-1] == (4242, "PSENEMY")

registered.clear()
assert core.install_engine_hooks()
assert registered["callback"] is core.confirm_nonparty_spell

policy = rows(ROOT / "psion/tables/psionai.2da")
powers = rows(ROOT / "psion/tables/psionpowers.2da")
assert set(policy) == {"OFFENSE", "DEFENSE", "CONTROL", "MOBILITY"}
assert {entry["ROLE"] for entry in policy.values()} == set(policy)
assert {entry["TARGET"] for entry in policy.values()} == {"ENEMY", "SELF", "POINT"}
for entry in policy.values():
    assert entry["POWER"] in powers
    assert int(entry["MIN_PP"]) == int(powers[entry["POWER"]]["BASE_COST"])
    assert int(entry["RESERVE"]) >= 0

print("Enemy Psion accepted-cast routing and deterministic AI fixture validation passed")
