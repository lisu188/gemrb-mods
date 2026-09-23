import json
import traceback

import GemRB
import GemRBModCore
import GUICommon
import Psionics
import Spellbook

bodies = []
creation = GemRB.CreateCreature


def observe_creation(*args):
    result = creation(*args)
    bodies.append(result)
    return result


GemRB.CreateCreature = observe_creation


def record(name, **data):
    print('PSICRYSTAL_NATIVE ' + json.dumps(dict(checkpoint=name, **data), sort_keys=True), flush=True)


def schedule(function, delay=1800):
    def guarded():
        try:
            function()
        except Exception:
            traceback.print_exc()
            print('PSICRYSTAL_NATIVE_FAIL', flush=True)
            GemRB.Quit()
    GemRB.SetTimer(guarded, delay, 0)


def cast(actor, resource):
    GemRB.GameSelectPC(actor, True, 1)
    Psionics.refresh_innate_charges(actor)
    entry = next(entry for entry in Spellbook.GetUsableMemorizedSpells(actor, 2)
                 if entry['SpellResRef'].upper() == resource)
    assert GemRBModCore.begin_spell(Spellbook, actor, entry['SpellIndex'])
    GemRB.SpellCast(actor, 4, entry['SpellIndex'] % 1000)


def exists(token):
    return GemRB.EvaluateString('Exists("PSCR%03d")' % token, True)


def start():
    assert [GUICommon.GetClassRowName(actor) for actor in (1, 2)] == ['PSION_SEER', 'PSION_EGOIST']
    for actor in (1, 2):
        Psionics._write_private_value(actor, Psionics.PSICRYSTAL_PERSONALITY_MARKER,
            Psionics.PSICRYSTAL_PERSONALITY_RESOURCE, 4, Psionics.PSICRYSTAL_EFFECT_SOURCE)
        Psionics.refresh_innate_charges(actor)
    GemRB.GameSelectPC(1, True, 1)
    entry = next(entry for entry in Spellbook.GetUsableMemorizedSpells(1, 2)
                 if entry['SpellResRef'].upper() == 'PXCRSUM')
    assert GemRBModCore.begin_spell(Spellbook, 1, entry['SpellIndex'])
    assert not bodies and not GemRB.GetGameVar('PSCRNEXT')
    GemRBModCore.cancel_pending()
    assert not bodies
    cast(1, 'PXCRSUM')
    cast(2, 'PXCRSUM')
    assert len(bodies) == 2
    record('accepted_cast', bodies=len(bodies))
    schedule(before_save)


def before_save():
    assert exists(1) and exists(2)
    for body in bodies:
        assert GemRB.GetPlayerStat(body, 0) == 40
        assert GemRB.GetPlayerStat(body, 1) == 40
        assert GemRB.GetPlayerStat(body, 8) == 0
        assert GemRB.GetPlayerStat(body, 34) == 5
        assert GemRB.GetPlayerStat(body, 38) == 8
    assert Psionics.can_dismiss_psicrystal(1)
    GemRB.GameSwapPCs(1, 2)
    assert Psionics._psicrystal_owner_token(1) == 2
    assert Psionics._psicrystal_owner_token(2) == 1
    GemRB.SetPlayerStat(bodies[0], 0, 17)
    Psionics.refresh_innate_charges(2)
    assert GemRB.GetPlayerStat(bodies[0], 0) == 17
    GemRBModCore.cancel_pending()
    result = GemRB.SaveGame(None, 'Psicrystal lifecycle', 0, GemRB.GetGamePreview())
    assert result == 0, result
    games = GemRB.GetSaveGames()
    assert games
    record('saved', saves=len(games), owner1=2, owner2=1)
    GemRB.LoadGame(games[0])
    GemRB.EnterGame()
    schedule(after_load, 3000)


def after_load():
    assert GemRB.GetPartySize() == 2
    assert exists(1) and exists(2)
    assert Psionics._psicrystal_owner_token(1) == 2
    assert Psionics._psicrystal_owner_token(2) == 1
    assert GemRB.GetPlayerStat(1, 163) == 2
    assert GemRB.GetPlayerStat(2, 163) == 1
    assert GemRB.EvaluateString('CheckStat("PSCR001",17,0)', True)
    assert GemRB.EvaluateString('CheckStat("PSCR001",0,8)', True)
    assert len(bodies) == 2
    record('loaded', no_duplicate=True, hp_preserved=True, zero_attacks=True)
    cast(2, 'PXCRDIS')
    schedule(after_dismiss)


def after_dismiss():
    assert not exists(1) and exists(2)
    cast(2, 'PXCRSUM')
    assert len(bodies) == 3
    record('dismiss_and_remanifest', epoch=GemRB.GetGameVar('PSCR001'))
    GemRB.GameSelectPC(0, True)
    GemRB.MoveToArea('AR0110')
    schedule(after_area)


def after_area():
    assert GemRB.GetCurrentArea() == 'AR0110', GemRB.GetCurrentArea()
    assert not exists(1) and not exists(2)
    cast(2, 'PXCRSUM')
    assert len(bodies) == 4
    assert exists(1)
    record('area_remanifest', epoch=GemRB.GetGameVar('PSCR001'))
    GemRB.GameSelectPC(0, True)
    GemRB.MoveToArea('AR0100')
    schedule(old_area, 3000)


def old_area():
    assert GemRB.GetCurrentArea() == 'AR0100'
    assert not exists(1)
    cast(2, 'PXCRSUM')
    assert len(bodies) == 5
    GemRB.SetPlayerStat(bodies[-1], 0, 0)
    schedule(after_death, 3000)


def after_death():
    assert not exists(1)
    cast(2, 'PXCRSUM')
    assert len(bodies) == 6
    GemRB.GameSelectPC(1, True, 1)
    GemRB.GameSetProtagonistMode(2)
    GemRB.SetPlayerStat(2, 0, 0)
    record('body_death_resummon')
    schedule(owner_dead, 3000)


def owner_dead():
    assert not exists(1)
    assert not Psionics.psicrystal_companion(2)
    record('owner_death_cleanup')
    print('PSICRYSTAL_NATIVE_PASS', flush=True)
    GemRB.Quit()
