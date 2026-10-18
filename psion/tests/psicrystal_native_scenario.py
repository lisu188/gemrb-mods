import json
import traceback

import GemRB
import ActionsWindow
import GemRBModCore
import GUICommon
import Psionics
import Spellbook

bodies = []
saved_names = {}
saved_ids = {}
saved_resources = None


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
    before = Psionics.psicrystal_companion(actor) if resource == 'PXCRSUM' else None
    entry = next(entry for entry in Spellbook.GetUsableMemorizedSpells(actor, 2)
                 if entry['SpellResRef'].upper() == resource)
    assert GemRBModCore.begin_spell(Spellbook, actor, entry['SpellIndex'])
    GemRB.SpellCast(actor, 4, entry['SpellIndex'] % 1000)
    if resource == 'PXCRSUM':
        after = Psionics.psicrystal_companion(actor)
        assert after and after['Alive']
        if not before or not before['Alive']:
            bodies.append(int(after['ActorID']))


def companion(actor):
    # Inspection must not dismiss a dead owner's body and mask missing timer
    # maintenance. The Psion convenience wrapper deliberately has that effect.
    return GemRB.ManageCompanion(actor, Psionics.PSICRYSTAL_BODY, 0)


def exists(actor):
    current = companion(actor)
    return bool(current and current['Alive'])


def resource_state():
    return {actor: [Psionics._read_persistent_pool_state(actor), Psionics._read_focus_state(actor),
                    Psionics._psicrystal_used_state(actor)] for actor in (1, 2)}


def start():
    assert [GUICommon.GetClassRowName(actor) for actor in (1, 2)] == ['PSION_SEER', 'PSION_EGOIST']
    # Exercise the installed shared hook. The demo has no ordinary action bar,
    # so invoke its real redraw endpoint once after GameControl becomes ready.
    ActionsWindow.UpdateActionsWindow()
    assert GemRBModCore._party_sync_timer_started
    record('automatic_sync_started')
    cast(1, 'PXCRYST')
    # Self-targeted selector spells enter the native action queue. Observe
    # their delivered opcode instead of treating queue acceptance as delivery.
    schedule(lambda: personality_selected(1), 6000)


def personality_selected(actor):
    choices = [resource.upper() for resource in GemRB.GetSpelldata(actor)]
    assert choices == ['PXCART', 'PXCFRND', 'PXCOBS', 'PXCSAGE', 'PXCSING'], choices
    raw_spell = 255000 + choices.index('PXCSAGE')
    assert GemRBModCore.begin_spell(Spellbook, actor, raw_spell)
    GemRB.SpellCast(actor, -3, 0, 'PXCSAGE')
    assert Psionics.psicrystal_personality(actor) == 4
    if actor == 1:
        cast(2, 'PXCRYST')
        schedule(lambda: personality_selected(2), 6000)
        return
    record('native_personality_selector', owners=2, personality='SAGE')
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
    global saved_names, saved_ids, saved_resources
    assert exists(1) and exists(2)
    for body in bodies:
        assert GemRB.GetPlayerStat(body, 0) == 40
        assert GemRB.GetPlayerStat(body, 1) == 40
        assert GemRB.GetPlayerStat(body, 8) == 0
        assert GemRB.GetPlayerStat(body, 34) == 5
        assert GemRB.GetPlayerStat(body, 38) == 8
    assert Psionics.can_dismiss_psicrystal(1)
    GemRB.GameSwapPCs(1, 2)
    assert int(companion(1)['ActorID']) == bodies[1]
    assert int(companion(2)['ActorID']) == bodies[0]
    GemRB.SetPlayerStat(bodies[0], 0, 17)
    saved_ids = {actor: int(companion(actor)['ActorID']) for actor in (1, 2)}
    saved_names = {actor: GemRB.GetPlayerName(saved_ids[actor], 2) for actor in (1, 2)}
    saved_resources = resource_state()
    GemRB.SetVar('ActionLevel', 0)
    GemRB.GameSelectPC(0, True)
    GemRB.MoveToArea('AR0110')
    # No recall, innate refresh or explicit synchronization after travel.
    schedule(save_after_travel, 3000)


def save_after_travel():
    assert GemRB.GetCurrentArea() == 'AR0110'
    for actor in (1, 2):
        current = companion(actor)
        assert current and current['Alive'] and current['InArea']
        assert int(current['ActorID']) == saved_ids[actor]
    assert GemRB.GetPlayerStat(saved_ids[2], 0) == 17
    assert resource_state() == saved_resources
    assert len(bodies) == 2
    record('automatic_area_sync', bodies=saved_ids, hp=17, innates_closed=True)
    GemRB.GameSelectPC(1, True, 1)
    result = GemRB.SaveGame(None, 'Psicrystal lifecycle', 0, GemRB.GetGamePreview())
    assert result == 0, result
    games = GemRB.GetSaveGames()
    assert games
    record('saved', saves=len(games), owner1=2, owner2=1, bodies=saved_ids, identities=saved_names)
    GemRB.LoadGame(games[0])
    GemRB.EnterGame()
    schedule(after_load, 3000)


def after_load():
    assert GemRB.GetPartySize() == 2
    assert GemRB.GetCurrentArea() == 'AR0110'
    assert exists(1) and exists(2)
    loaded1 = companion(1)
    loaded2 = companion(2)
    assert loaded1 and loaded2
    assert int(loaded1['ActorID']) != int(loaded2['ActorID'])
    assert loaded1['InArea'] and loaded2['InArea']
    loaded_ids = {actor: int(companion(actor)['ActorID']) for actor in (1, 2)}
    assert {actor: GemRB.GetPlayerName(loaded_ids[actor], 2) for actor in (1, 2)} == saved_names
    assert resource_state() == saved_resources
    body = companion(2)
    assert body
    body_id = int(body['ActorID'])
    assert GemRB.GetPlayerStat(body_id, 0) == 17
    assert GemRB.GetPlayerStat(body_id, 8) == 0
    assert len(bodies) == 2
    record('loaded', no_duplicate=True, hp_preserved=True, zero_attacks=True,
           bodies=loaded_ids, identities=saved_names, innates_closed=True)
    cast(2, 'PXCRDIS')
    schedule(after_dismiss)


def after_dismiss():
    assert exists(1) and not exists(2)
    Psionics.restore_party()
    cast(2, 'PXCRSUM')
    assert len(bodies) == 3
    record('dismiss_and_remanifest', body=int(companion(2)['ActorID']))
    GemRB.SetPlayerStat(bodies[2], 0, 11)
    GemRB.SetVar('ActionLevel', 0)
    GemRB.GameSelectPC(0, True)
    GemRB.MoveToArea('AR0100')
    schedule(after_area, 3000)


def after_area():
    assert GemRB.GetCurrentArea() == 'AR0100', GemRB.GetCurrentArea()
    before = companion(2)
    assert before and before['Alive']
    body_id = int(before['ActorID'])
    assert before['InArea']
    assert body_id == bodies[2]
    assert GemRB.GetPlayerStat(body_id, 0) == 11
    assert len(bodies) == 3
    record('automatic_return_sync', body=body_id, hp=11, innates_closed=True)
    GemRB.SetPlayerStat(body_id, 0, 0)
    schedule(after_death, 3000)


def after_death():
    assert not exists(2)
    assert not Psionics.can_summon_psicrystal(2)
    Psionics.restore_party()
    cast(2, 'PXCRSUM')
    assert len(bodies) == 4
    GemRB.GameSelectPC(1, True, 1)
    GemRB.SetVar('ActionLevel', 0)
    GemRB.GameSetProtagonistMode(2)
    GemRB.SetPlayerStat(2, 0, 0)
    record('body_death_resummon')
    schedule(owner_dead, 3000)


def owner_dead():
    assert not exists(2)
    assert not companion(2)
    record('owner_death_cleanup', owner_selected=False, innates_closed=True)
    print('PSICRYSTAL_NATIVE_PASS', flush=True)
    GemRB.Quit()
