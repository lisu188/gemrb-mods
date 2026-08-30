#!/usr/bin/env python3
from dataclasses import dataclass

FOCUS_GAIN = 5


@dataclass
class CipherState:
    focus: int
    cap: int


@dataclass
class ReapingKnivesEffect:
    source_cipher: int
    active: bool = True

    def serialize(self):
        return {"source_cipher": self.source_cipher, "active": self.active}

    @classmethod
    def deserialize(cls, data):
        return cls(int(data["source_cipher"]), bool(data["active"]))


def resolve_hit(effect, ciphers, hostile, critical=False):
    if not effect.active or not hostile:
        return 0
    owner = ciphers[effect.source_cipher]
    before = owner.focus
    owner.focus = min(owner.cap, owner.focus + FOCUS_GAIN)
    return owner.focus - before


def main():
    ciphers = {
        1: CipherState(20, 40),
        2: CipherState(10, 25),
    }
    first = ReapingKnivesEffect(1)
    second = ReapingKnivesEffect(2)

    assert resolve_hit(first, ciphers, hostile=True) == 5
    assert ciphers[1].focus == 25
    assert ciphers[2].focus == 10

    assert resolve_hit(second, ciphers, hostile=True) == 5
    assert ciphers[1].focus == 25
    assert ciphers[2].focus == 15

    assert resolve_hit(first, ciphers, hostile=False) == 0
    assert ciphers[1].focus == 25

    assert resolve_hit(first, ciphers, hostile=True, critical=True) == 5
    assert ciphers[1].focus == 30

    ciphers[1].focus = 38
    assert resolve_hit(first, ciphers, hostile=True) == 2
    assert ciphers[1].focus == 40
    assert resolve_hit(first, ciphers, hostile=True) == 0

    saved = first.serialize()
    restored = ReapingKnivesEffect.deserialize(saved)
    ciphers[1].focus = 20
    assert resolve_hit(restored, ciphers, hostile=True) == 5
    assert ciphers[1].focus == 25

    restored.active = False
    assert resolve_hit(restored, ciphers, hostile=True) == 0
    assert ciphers[1].focus == 25

    assert FOCUS_GAIN == 5
    print("Reaping Knives behavioral contract validation passed")


if __name__ == "__main__":
    main()
