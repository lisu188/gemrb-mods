# SPDX-License-Identifier: GPL-2.0-or-later
"""Runtime support for the experimental GemRB Psion mod.

The current pool is persisted in actor stat 239, explicitly reserved by GemRB
as a user-defined stat. Stat 188 marks initialization. Base progression comes
from PSIONPOOL.2DA; Intelligence supplies the D&D 3e bonus pool.
"""
import GemRB

CURRENT_POOL_STAT = 239
POOL_READY_STAT = 188
INT_STAT = 38
LEVEL_STAT = 34
PSION_CLASSES = {"PSION_SEER", "PSION_SHAPER", "PSION_KINETICIST", "PSION_EGOIST", "PSION_NOMAD", "PSION_TELEPATH"}

def _class_row(actor):
    try:
        import GUICommon
        return GUICommon.GetClassRowName(actor)
    except Exception:
        return ""

def is_psion(actor):
    return _class_row(actor) in PSION_CLASSES

def maximum_pool(actor):
    if not is_psion(actor):
        return 0
    level=max(1,min(20,GemRB.GetPlayerStat(actor,LEVEL_STAT)))
    intelligence=GemRB.GetPlayerStat(actor,INT_STAT)
    modifier=(intelligence-10)//2
    table=GemRB.LoadTable("psionpool",False,True)
    base=int(table.GetValue(str(level),"BASE_POOL"))
    return max(0,base+(modifier*level)//2)

def ensure_pool(actor, refill=False):
    if not is_psion(actor):
        return 0
    cap=maximum_pool(actor)
    ready=GemRB.GetPlayerStat(actor,POOL_READY_STAT)
    current=GemRB.GetPlayerStat(actor,CURRENT_POOL_STAT)
    if refill or not ready:
        current=cap
        GemRB.SetPlayerStat(actor,POOL_READY_STAT,1)
    current=max(0,min(current,cap))
    GemRB.SetPlayerStat(actor,CURRENT_POOL_STAT,current)
    return current

def restore_party():
    for actor in range(1,7):
        try: ensure_pool(actor,True)
        except Exception: pass

def power_cost(resref):
    table=GemRB.LoadTable("psionpowers",False,True)
    try: return int(table.GetValue(resref.upper(),"BASE_COST"))
    except Exception: return 0

def spend(actor,resref):
    cost=power_cost(resref)
    if not cost: return True
    current=ensure_pool(actor)
    if current < cost:
        GemRB.DisplayString(10417,0xffffff,actor)
        return False
    GemRB.SetPlayerStat(actor,CURRENT_POOL_STAT,current-cost)
    return True
