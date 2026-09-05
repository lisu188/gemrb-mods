"""Shared synthetic table/API boundary around the real GemRB CLAB callbacks."""

import ast
from types import SimpleNamespace


class Table:
    def __init__(self, path):
        lines = [line.split("//", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()]
        lines = [line for line in lines if line]
        assert lines[0].upper().split() == ["2DA", "V1.0"], path
        self.columns = lines[2].split()
        self.rows = [line.split()[1:] for line in lines[3:]]
        assert all(len(row) == len(self.columns) for row in self.rows), path

    def GetColumnCount(self):
        return len(self.columns)

    def GetRowCount(self):
        return len(self.rows)

    def GetValue(self, row, column, value_type):
        assert 0 <= row < len(self.rows), row
        assert 0 <= column < len(self.columns), column
        return self.rows[row][column]


def constants(path):
    namespace = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def engine_callbacks(gemrb_root, tables, delivered, applied=None):
    if applied is None:
        applied = []
    scripts = gemrb_root / "gemrb" / "GUIScripts"
    source = scripts / "GUICommon.py"
    parsed = ast.parse(source.read_text(encoding="utf-8"))
    names = {"AddClassAbilities", "AddClassAbility"}
    callbacks = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in callbacks} == names, source
    defines = constants(scripts / "GUIDefines.py")
    spells = constants(scripts / "ie_spells.py")
    namespace = {
        "GemRB": SimpleNamespace(LoadTable=lambda name: tables[name],
                                 ApplySpell=lambda *args: applied.append(args)),
        "Spellbook": SimpleNamespace(LearnSpell=lambda *args: delivered.append(args)),
        "GTV_STR": defines["GTV_STR"],
        "IE_SPELL_TYPE_INNATE": defines["IE_SPELL_TYPE_INNATE"],
        "LS_MEMO": spells["LS_MEMO"],
    }
    exec(compile(ast.Module(body=callbacks, type_ignores=[]), str(source), "exec"), namespace)
    return namespace
