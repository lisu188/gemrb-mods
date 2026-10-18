import json
import traceback

import GemRB
import GemRBModCore
import Psionics

enemy = 0
enemy_name = ""
target = 0
target_name = ""
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
    global enemy, enemy_name, target, target_name, pool_before
    assert GemRBModCore.install_engine_hooks()
    # A native owner/token identity makes this nonparty actor persistent without
    # joining the party. Global ActorIDs are reassigned when a save is loaded.
    body = GemRB.ManageCompanion(1, "PSCRBODY", 1)
    assert body and body["Created"]
    enemy = int(body["ActorID"])
    assert enemy > 1000
    enemy_name = GemRB.GetPlayerName(enemy, 2)
    target = GemRB.CreateCreature(1, "PSCRBODY")
    assert target > 1000 and target != enemy
    target_name = GemRB.GetPlayerName(target, 2)
    assert target_name and target_name != enemy_name
    for script_index in range(8):
        GemRB.SetPlayerScript(enemy, "", script_index)
        GemRB.SetPlayerScript(target, "", script_index)
    class_id = int(GemRB.LoadTable("clastext", False, True).GetValue("PSION_NOMAD", "CLASSID"))
    GemRB.SetPlayerStat(enemy, 232, class_id)
    GemRB.SetPlayerStat(enemy, 34, 5)
    GemRB.SetPlayerStat(enemy, 38, 18)
    GemRB.SetPlayerStat(enemy, 1, 40)
    GemRB.SetPlayerStat(enemy, 0, 40)
    GemRB.SetPlayerStat(enemy, 234, 255)
    GemRB.SetPlayerStat(target, 234, 4)
    GemRB.SetPlayerStat(target, 13, 25)  # deterministic failed save vs spell
    GemRB.SetPlayerStat(target, 18, 0)  # no magic resistance
    GemRB.SetPlayerStat(target, 38, 8)  # Maze lasts long enough to inspect
    assert GemRB.GetPlayerStat(target, 13) == 25
    assert GemRB.GetPlayerStat(target, 18) == 0
    assert GemRB.CountEffects(target, "Maze", -1, -1) == 0
    assert GemRB.GetPlayerStat(target, 201) == 0
    assert Psionics.is_psion(enemy)
    assert Psionics.discipline(enemy) == "NOMAD"
    assert GemRB.GetPartySize() == 1
    assert not GemRB.EvaluateString('InParty("%s")' % enemy_name, True)
    assert not GemRB.EvaluateString('InParty("%s")' % target_name, True)
    pool_before = Psionics.ensure_pool(enemy, True)
    assert pool_before > 5

    def accepted(actor, resref):
        plan = Psionics.manifestation_plan(actor, resref) if actor == enemy else None
        result = GemRBModCore.confirm_nonparty_spell(actor, resref)
        if actor == enemy:
            assert GemRB.GetPlayerStat(actor, 234) == 255
            assert GemRB.GetPlayerStat(target, 234) == 4
            assert not GemRB.EvaluateString('InParty("%s")' % enemy_name, True)
            assert not GemRB.EvaluateString('InParty("%s")' % target_name, True)
            observed.append((str(resref).upper(), result, Psionics.ensure_pool(actor)))
            record("accepted_hook", actor=actor, requested=str(resref).upper(),
                   executable=str(result), pool=Psionics.ensure_pool(actor), plan=plan,
                   caster_ea=GemRB.GetPlayerStat(actor, 234), caster_nonparty=True,
                   target=target, target_name=target_name,
                   target_ea=GemRB.GetPlayerStat(target, 234), target_nonparty=True)
        return result

    GemRB.SetNonPartySpellCastCheck(accepted)
    # Time Hop may Maze its target. Keep that effect off the party so the
    # ordinary save rules remain meaningful after the cast has completed.
    GemRB.ExecuteString('ForceSpellRES("PS3THOP","%s")' % target_name, enemy)
    schedule(after_cast, 2600)


def after_cast(attempt=0):
    assert len(observed) == 1, observed
    requested, executable, pool = observed[0]
    assert requested == "PS3THOP"
    assert executable == "PS3THOP4", executable
    assert pool == pool_before - 5
    assert Psionics.ensure_pool(enemy) == pool_before - 5
    assert GemRB.GetPlayerStat(enemy, 234) == 255
    assert GemRB.GetPlayerStat(target, 234) == 4
    maze = GemRB.CountEffects(target, "Maze", -1, -1, "", executable)
    removed = GemRB.GetPlayerStat(target, 201)
    if maze != 1 or removed != 1:
        # ForceSpell keeps its real casting time. Interface timers use wall
        # time, so a busy runner can observe this before the cast winds down.
        assert attempt < 30, (maze, removed, attempt)
        schedule(lambda: after_cast(attempt + 1), 500)
        return
    record("power_delivered", target=target, identity=target_name, source=executable,
           maze_effects=maze, avatar_removal=removed,
           save_vs_spell=GemRB.GetPlayerStat(target, 13), magic_resistance=GemRB.GetPlayerStat(target, 18))
    record("pp_spent_once", before=pool_before, after=pool)
    # End this controlled encounter without bypassing CanSave's nearby-enemy
    # check. Do not clear the cast action: observe it finish naturally below.
    GemRB.SetPlayerStat(enemy, 234, 128)
    await_safe_save()


def await_safe_save(attempt=0):
    idle = GemRB.EvaluateString('ObjectActionListEmpty("%s")' % enemy_name, True)
    peaceful = GemRB.EvaluateString("CombatCounter(0)", True)
    if not (idle and peaceful):
        assert attempt < 30, (idle, peaceful)
        schedule(lambda: await_safe_save(attempt + 1), 500)
        return
    assert GemRB.GetPlayerStat(enemy, 234) == 128
    assert Psionics.ensure_pool(enemy) == pool_before - 5
    record("combat_completed", actor=enemy, caster_ea=128, action_empty=idle,
           combat_counter_zero=peaceful, pool=pool_before - 5)
    result = GemRB.SaveGame(None, "Enemy Psion runtime", 0, GemRB.GetGamePreview())
    assert result == 0, result
    games = GemRB.GetSaveGames()
    assert games
    record("saved", pool=pool_before - 5, owner=1, resource="PSCRBODY", identity=enemy_name)
    GemRB.LoadGame(games[0])
    GemRB.EnterGame()
    schedule(after_load, 3000)


def after_load():
    body = GemRB.ManageCompanion(1, "PSCRBODY", 0)
    assert body and body["Alive"]
    restored = int(body["ActorID"])
    assert GemRB.GetPlayerName(restored, 2) == enemy_name
    assert GemRB.GetPartySize() == 1
    assert not GemRB.EvaluateString('InParty("%s")' % enemy_name, True)
    current = Psionics.ensure_pool(restored)
    assert current == pool_before - 5, (current, pool_before)
    assert Psionics.is_psion(restored)
    record("loaded", pool=current, actor=restored, previous_actor=enemy,
           owner=1, resource="PSCRBODY", identity=enemy_name, nonparty=True)
    print("ENEMY_PSION_NATIVE_PASS", flush=True)
    GemRB.Quit()
