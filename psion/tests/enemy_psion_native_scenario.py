import json
import traceback

import GemRB
import GemRBModCore
import Psionics

enemy = 0
pool_before = 0
observed = []


def record(name, **data):
    print("ENEMY_PSION_NATIVE " + json.dumps(dict(checkpoint=name, **data), sort_keys=True), flush=True)


def schedule(function, delay=1800):
    def guarded():
        try:
            function()
        except Exception:
            traceback.print_exc()
            print("ENEMY_PSION_NATIVE_FAIL", flush=True)
            GemRB.Quit()
    GemRB.SetTimer(guarded, delay, 0)


def start():
    global enemy, pool_before
    assert GemRBModCore.install_engine_hooks()
    enemy = GemRB.CreateCreature(1, "PSCRBODY")
    assert enemy > 1000
    class_id = int(GemRB.LoadTable("clastext", False, True).GetValue("PSION_NOMAD", "CLASSID"))
    GemRB.SetPlayerStat(enemy, 232, class_id)
    GemRB.SetPlayerStat(enemy, 34, 5)
    GemRB.SetPlayerStat(enemy, 38, 18)
    GemRB.SetPlayerStat(enemy, 1, 40)
    GemRB.SetPlayerStat(enemy, 0, 40)
    GemRB.SetPlayerStat(enemy, 234, 255)
    assert Psionics.is_psion(enemy)
    assert Psionics.discipline(enemy) == "NOMAD"
    pool_before = Psionics.ensure_pool(enemy, True)
    assert pool_before > 3

    def accepted(actor, resref):
        result = GemRBModCore.confirm_nonparty_spell(actor, resref)
        if actor == enemy:
            observed.append((str(resref).upper(), result, Psionics.ensure_pool(actor)))
            record("accepted_hook", actor=actor, requested=str(resref).upper(),
                   executable=str(result), pool=Psionics.ensure_pool(actor))
        return result

    GemRB.SetNonPartySpellCastCheck(accepted)
    GemRB.ExecuteString('ForceSpellRES("PS1ERAY",Player1)', enemy)
    schedule(after_cast, 2600)


def after_cast():
    assert len(observed) == 1, observed
    requested, executable, pool = observed[0]
    assert requested == "PS2CBLS"
    assert executable == "PS2CBLS4", executable
    assert pool == pool_before - 3
    assert Psionics.ensure_pool(enemy) == pool_before - 3
    record("pp_spent_once", before=pool_before, after=pool)
    result = GemRB.SaveGame(None, "Enemy Psion runtime", 0, GemRB.GetGamePreview())
    assert result == 0, result
    games = GemRB.GetSaveGames()
    assert games
    record("saved", pool=pool)
    GemRB.LoadGame(games[0])
    GemRB.EnterGame()
    schedule(after_load, 3000)


def after_load():
    current = Psionics.ensure_pool(enemy)
    assert current == pool_before - 3, (current, pool_before)
    assert Psionics.is_psion(enemy)
    record("loaded", pool=current, actor=enemy)
    print("ENEMY_PSION_NATIVE_PASS", flush=True)
    GemRB.Quit()
