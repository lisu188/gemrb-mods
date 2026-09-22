#!/usr/bin/env python3
"""Exercise runtime rule-table access through native eight-character IDs.

The source filenames may be longer. Only explicitly installed destinations are
visible to this loader, which intentionally reproduces GemRB ResRef truncation.
"""
import ast
import importlib.util
from pathlib import Path
import re
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installed_tables():
    result = {}
    for mod in ("psion", "cipher"):
        sources = [ROOT / mod / ("setup-" + mod + ".tp2"), *(ROOT / mod / "lib").glob("*.tpa")]
        for source in sources:
            for original, destination in re.findall(
                    r"\bCOPY\s+~((?:psion|cipher)/tables/[^~]+\.2da)~\s+~override/([^~]+\.2da)~",
                    source.read_text()):
                name = Path(destination).stem.lower()
                assert re.fullmatch(r"[a-z0-9_]{1,8}", name), (source, destination)
                assert name not in result, ("colliding table resource", name)
                result[name] = ROOT / original
    generator = load_module("psicrystal_table_generator", ROOT / "psion/tools/generate_psicrystal.py")
    assert "pscrcfg" not in result, "generated table collides with a static destination"
    result["pscrcfg"] = types.SimpleNamespace(read_text=lambda: generator.configuration(range(1, 7)))
    return result


class Table:
    def __init__(self, path):
        lines = [line.split("//", 1)[0].split() for line in path.read_text().splitlines()]
        lines = [line for line in lines if line]
        self.columns = lines[2]
        self.rows = {line[0]: line[1:] for line in lines[3:]}

    def GetValue(self, row, column, *unused):
        if isinstance(row, int):
            row = self.GetRowName(row)
        if isinstance(column, str):
            column = self.columns.index(column)
        return self.rows[row][column]

    def GetRowName(self, index):
        return list(self.rows)[index]

    def GetRowCount(self):
        return len(self.rows)


def main():
    installed = installed_tables()

    def load_table(name, *unused):
        return Table(installed[name.lower()[:8]])

    for legacy in ("psionpool", "psionknown", "psionfeatpick", "cipherpowers", "cipherknown"):
        try:
            load_table(legacy)
        except KeyError:
            pass
        else:
            raise AssertionError("long resource silently aliases another table: " + legacy)

    modules = {name: types.ModuleType(name) for name in (
        "GemRB", "GUICommon", "Transactions", "InnateCharges", "PersistentState", "Selectors", "ie_spells")}
    modules["GemRB"].LoadTable = load_table
    modules["GemRB"].GetPlayerStat = lambda actor, stat, *unused: {34: 16, 38: 18}.get(stat, 0)
    modules["GemRB"].GetEffects = lambda *unused: ()
    modules["GUICommon"].GetClassRowName = lambda actor: "PSION_SEER"
    modules["PersistentState"].read = lambda *unused: (False, 0)
    modules["ie_spells"].LS_MEMO = 8

    with patch.dict(sys.modules, modules):
        for package, filename in (("psion", "Psionics"), ("cipher", "Cipher")):
            path = ROOT / package / "guiscripts" / (filename + ".py")
            for call in ast.walk(ast.parse(path.read_text())):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "LoadTable":
                    assert call.args and isinstance(call.args[0], ast.Constant), "audit dynamic table lookup"
                    name = call.args[0].value
                    assert isinstance(name, str) and len(name) <= 8, (filename, name)
                    assert load_table(name).GetRowCount() > 0, (filename, name)
            module = load_module(filename, path)
            if package == "psion":
                assert module.maximum_pool(1) == 253
                assert module.power_learning_limits(1) == (30, 8)
                assert module._base_power_info("PS1ERAY")["cost"] == 1
                assert module._feat_table().GetRowCount() == 4
                assert module._skill_table().GetRowCount() == 11
                assert module._augment_table().GetRowCount() > 0
            else:
                assert module._known_power_table().GetRowCount() == 30
                assert module.power_info("CI1WHSP")["cost"] == 10
    print("Runtime resource IDs validated with native eight-character table resolution")


if __name__ == "__main__":
    main()
