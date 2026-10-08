#!/usr/bin/env python3
"""Exercise installed Focus resources with controlled actor/effect boundaries.

This follows the emitted SPL/SPLPROT graph, including effect order, persistent
setters and caster/target routing. It complements actual GemRB combat acceptance;
it does not substitute for engine execution of these resources.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import sys

from verify_high_tier_weidu import features, locate


@dataclass
class Actor:
    class_id: int
    level: int = 1
    subclass: int = 0
    focus: int = 0
    owner: int = 0
    hostile: bool = False
    states: dict = field(default_factory=dict)


class InstalledFocus:
    def __init__(self, game):
        self.override = game / "override"
        self.rows = [line.split() for line in (self.override / "splprot.2da").read_text().splitlines()[3:]
                     if line.strip()]
        self.class_id = int(next(row[2] for row in self.rows if row[0] == "CIPHER_CLASS"), 0)
        self.party = []

    @lru_cache(maxsize=None)
    def effects(self, resref):
        return features(locate(self.override, resref))

    def matches(self, row, caster, actor):
        _, stat, expected, relation = self.rows[row]
        stat, expected, relation = int(stat, 0), int(expected, 0), int(relation, 0)
        if stat == 0x104:
            return not (self.matches(expected, caster, actor) or self.matches(relation, caster, actor))
        value = {
            0x10D: actor.class_id, 0x108: 2 if caster.hostile != actor.hostile else 0,
            34: actor.level, 164: actor.owner, 165: actor.focus, 163: actor.subclass,
        }[stat]
        return {1: value == expected, 2: value < expected,
                4: value >= expected, 5: value != expected}[relation]

    def apply(self, resref, caster, recipient):
        for effect in self.effects(resref):
            targets = {1: [caster], 2: [recipient], 3: self.party}[effect["target"]]
            for target in targets:
                opcode, resource = effect["opcode"], effect["resource"]
                if opcode == 326:
                    if self.matches(effect["parameter2"], caster, target):
                        self.apply(resource, caster, target)
                elif opcode == 321:
                    target.states.pop(resource, None)
                elif opcode == 282:
                    assert effect["parameter2"] == 9 and effect["timing"] == 9, effect
                    target.states[resref] = effect["parameter1"]
                    target.focus = effect["parameter1"]
                else:
                    raise AssertionError((resref, effect))

    def hit(self, caster, target, *, critical=False, landed=True):
        if not landed:
            return
        # CIFCRIT is the same hostile gate as the installed weapon carrier.
        self.apply("CIFCRIT", caster, target)
        if critical:
            self.apply("CIFCRIT", caster, target)


def validate(game):
    graph = InstalledFocus(game)
    mirror = graph.effects("CISUBFX")
    assert [(effect["opcode"], effect["target"], effect["parameter1"],
             effect["parameter2"], effect["timing"], effect["resource"])
            for effect in mirror] == [
                (321, 1, 0, 0, 1, "CISUBFX"),
                (282, 1, 1, 7, 9, "CISUBCLS"),
            ], mirror
    enemy = Actor(1, hostile=True)
    friend = Actor(1)
    checks = 0
    for subclass, gain in ((0, 1), (1, 2)):
        for level in range(1, 31):
            cap = 4 + level
            for current in range(cap + 1):
                for critical in (False, True):
                    actor = Actor(graph.class_id, level, subclass, current,
                                  states={f"CIFS{current}": current})
                    graph.hit(actor, enemy, critical=critical)
                    expected = min(cap, current + gain * (2 if critical else 1))
                    assert actor.focus == expected, (subclass, level, current, critical, actor.focus, expected)
                    assert list(actor.states.values()) == [expected], actor.states
                    checks += 1
            actor = Actor(graph.class_id, level, subclass, cap - 1)
            graph.hit(actor, friend, critical=True)
            graph.hit(actor, enemy, landed=False)
            assert actor.focus == cap - 1 and not actor.states
            # Reaping Knives always credits exactly one unit to its owner,
            # including Soul Blade owners and before any GUI refresh.
            owner = Actor(graph.class_id, level, subclass, cap - 1, owner=7,
                          states={f"CIFS{cap - 1}": cap - 1})
            other = Actor(graph.class_id, level, subclass, 0, owner=8)
            graph.party = [friend, owner, other]
            graph.apply("CIRKG7", friend, enemy)
            graph.apply("CIRKG7", friend, enemy)
            assert owner.focus == cap and list(owner.states.values()) == [cap], owner
            assert other.focus == 0 and not other.states, other
            assert not friend.states, friend

    # Every weapon is patched. A default subclass mirror must never let a
    # non-Cipher acquire private Focus effects, even if its stats resemble one.
    for subclass in (0, 1):
        ordinary = Actor(graph.class_id + 1, 30, subclass)
        graph.hit(ordinary, enemy, critical=True)
        assert ordinary.focus == 0 and not ordinary.states, ordinary
    assert not enemy.states, enemy
    print(f"Installed Cipher Focus graph passed {checks} normal/critical transitions, "
          "all level caps, class isolation and Reaping Knives routing (controlled actor boundaries).")


if __name__ == "__main__":
    validate(Path(sys.argv[1]))
