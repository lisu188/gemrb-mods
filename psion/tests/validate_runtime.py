#!/usr/bin/env python3
"""Fake-GemRB power-point, selector, transaction, and charge checks."""

from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]


def lines(name: str) -> list[str]:
    return (ROOT / "tables" / name).read_text(encoding="utf-8").splitlines()


def header(name: str) -> list[str]:
    return lines(name)[2].split()


def rows(name: str) -> list[list[str]]:
    return [line.split() for line in lines(name)[3:] if line.strip()]


def fake_table(name: str):
    columns, data = header(name), rows(name)

    class Table:
        names = [row[0] for row in data]
        values = {row[0]: dict(zip(columns, row[1:])) for row in data}

        def GetValue(self, row, column):
            return self.values[str(row)][column]

        def GetRowCount(self):
            return len(self.names)

        def GetRowName(self, index):
            return self.names[index]

    return Table()


def main() -> None:
    gemrb = types.ModuleType("GemRB")
    gui = types.ModuleType("GUICommon")
    stats = {(1, 38): 18, (1, 34): 3, (1, 188): 0, (1, 239): 0}
    tables = {
        name: fake_table(name + ".2da")
        for name in ("psionpool", "psionpowers", "psionaugment")
    }
    known_innates = [
        {"SpellResRef": "PS1ERAY"},
        {"SpellResRef": "PS1VIGR"},
        {"SpellResRef": "SPCL900"},
    ]
    memorized_innates = [
        {"SpellResRef": "PS1ERAY", "Flags": 0},
        {"SpellResRef": "PS1VIGR", "Flags": 1},
        {"SpellResRef": "SPCL900", "Flags": 0},
    ]

    gui.GetClassRowName = lambda actor: "PSION_EGOIST" if actor == 1 else ""
    gemrb.GetPlayerStat = lambda actor, stat: stats.get((actor, stat), 0)
    gemrb.SetPlayerStat = lambda actor, stat, value: stats.__setitem__((actor, stat), value)
    gemrb.LoadTable = lambda name, *_: tables[name.lower()]
    gemrb.DisplayString = lambda *_: None
    gemrb.Log = lambda *_: None
    gemrb.GetKnownSpellsCount = lambda actor, spell_type, level: len(known_innates)
    gemrb.GetKnownSpell = lambda actor, spell_type, level, index: dict(known_innates[index])
    gemrb.GetMemorizedSpellsCount = (
        lambda actor, spell_type, level, real: len(memorized_innates)
    )
    gemrb.GetMemorizedSpell = (
        lambda actor, spell_type, level, index: dict(memorized_innates[index])
    )

    def unmemorize(actor, spell_type, level, index):
        memorized_innates.pop(index)
        return True

    def memorize(actor, spell_type, level, known_index, usable):
        memorized_innates.append(
            {
                "SpellResRef": known_innates[known_index]["SpellResRef"],
                "Flags": 1 if usable else 0,
            }
        )
        return True

    gemrb.UnmemorizeSpell = unmemorize
    gemrb.MemorizeSpell = memorize

    old_gemrb, old_gui = sys.modules.get("GemRB"), sys.modules.get("GUICommon")
    sys.modules["GemRB"], sys.modules["GUICommon"] = gemrb, gui
    try:
        path = ROOT / "guiscripts" / "Psionics.py"
        spec = importlib.util.spec_from_file_location("psion_runtime_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.ensure_pool(1) == 17
        for parent in ("PS1ERAY", "PS1MTHR", "PS1VIGR", "PS2AAFF"):
            assert module.power_info(parent)["selector"]
            assert module.can_manifest(1, parent)

        assert module.power_info("PSAADEX")["cost"] == 3
        mixed = ["SPWI112", "PSRF01", "PSRF04", "PSAADEX"]
        assert module.filter_spellinfo(1, mixed) == ["SPWI112", "PSRF01", "PSAADEX"]

        before = module.ensure_pool(1)
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before
        assert module.begin_manifest(1, "PSAADEX")
        assert module.ensure_pool(1) == before - 3

        # One depleted Psion power is replaced with a charged copy. The already
        # usable Psion power and the unrelated depleted innate remain untouched.
        assert module.refresh_innate_charges(1) == 1
        states = {
            spell["SpellResRef"]: spell["Flags"] for spell in memorized_innates
        }
        assert states == {"PS1ERAY": 1, "PS1VIGR": 1, "SPCL900": 0}, states
        assert module.refresh_innate_charges(2) == 0

        stats[(1, 188)], stats[(1, 239)] = 1, 0
        assert not module.can_manifest(1, "PS2AAFF")
        assert module.filter_spellinfo(1, ["SPWI112", "PSAASTR"]) == ["SPWI112"]
    finally:
        if old_gemrb is None:
            sys.modules.pop("GemRB", None)
        else:
            sys.modules["GemRB"] = old_gemrb
        if old_gui is None:
            sys.modules.pop("GUICommon", None)
        else:
            sys.modules["GUICommon"] = old_gui

    print("Psion fake-GemRB runtime validation passed.")


if __name__ == "__main__":
    main()
