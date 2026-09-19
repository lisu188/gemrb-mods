#!/usr/bin/env python3
"""Verify installed startup effects and the real engine's area-free dispatch.

The C++ opcode body is compiled unchanged with controlled API boundaries. This
checks actor/point routing, not full effect processing or live Focus gameplay.
"""

import argparse
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def effects(path):
    data = path.read_bytes()
    assert data[:8] == b"SPL V1  ", path
    header_offset = struct.unpack_from("<I", data, 0x64)[0]
    header_count = struct.unpack_from("<H", data, 0x68)[0]
    effect_offset = struct.unpack_from("<I", data, 0x6A)[0]
    result = []
    for index in range(header_count):
        header = header_offset + index * 0x28
        count, first = struct.unpack_from("<HH", data, header + 0x1E)
        for item in range(count):
            offset = effect_offset + (first + item) * 0x30
            result.append((
                struct.unpack_from("<H", data, offset)[0], data[offset + 2],
                struct.unpack_from("<I", data, offset + 4)[0],
                struct.unpack_from("<I", data, offset + 8)[0], data[offset + 0xC],
                data[offset + 0x14:offset + 0x1C].split(b"\0", 1)[0].decode("ascii"),
            ))
    return result


def opcode_body(source):
    match = re.search(r"\bint\s+fx_add_effects_list\s*\([^;]+?\)\s*\{", source)
    assert match, "engine does not expose the expected ApplyEffectsList callback"
    depth = 1
    end = match.end()
    while depth:
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
        end += 1
    return source[match.start():end]


def validate(game, gemrb_root, compiler):
    files = {path.name.casefold(): path for path in (game / "override").iterdir() if path.is_file()}
    rows = [line.split() for line in files["splprot.2da"].read_text().splitlines()[3:] if line.strip()]
    class_row = next(index for index, row in enumerate(rows) if row[0] == "CIPHER_CLASS")
    condition = rows[class_row]
    assert condition[1] == "0x10d" and condition[3] == "1", condition
    class_id = int(condition[2])
    core_effects = effects(files["cifcore.spl"])
    expected = (326, 2, 0, class_row, 1, "CIFS4")
    assert core_effects.count(expected) == 1, core_effects
    assert not any(effect[0] == 146 for effect in core_effects), core_effects
    state = [effect for effect in effects(files["cifs4.spl"]) if effect[0] == 282]
    assert state == [(282, 1, 4, 9, 9, "CIFOCUS")], state

    source = gemrb_root / "gemrb/plugins/FXOpcodes/FXOpcodes.cpp"
    callback = opcode_body(source.read_text(encoding="utf-8"))
    # Only dependencies are replaced; the actual opcode implementation below
    # decides whether it needs an area and whether it respects the class gate.
    cpp = r'''
#include <cassert>
#include <stdexcept>
#include <string>
constexpr int FX_TARGET_SELF = 1;
constexpr int FX_NOT_APPLIED = 0;
struct Point {};
struct Map {};
struct Scriptable {};
struct Actor : Scriptable {
    int classID;
    int areaQueries = 0;
    Map* GetCurrentArea() { ++areaQueries; return nullptr; }
};
struct Effect {
    int Parameter1, Parameter2, Target, Power;
    std::string Resource;
    Point Pos;
};
struct EffectQueue {
    static bool CheckIWDTargeting(Scriptable*, Actor* actor, int value, int row, Effect*) {
        assert(value == 0 && row == CLASS_ROW);
        return actor->classID == CLASS_ID;
    }
};
struct Core {
    int actorCalls = 0, pointCalls = 0;
    Actor* expectedActor = nullptr;
    void ApplySpell(const std::string& resource, Actor* actor, Scriptable* owner, int) {
        assert(resource == "CIFS4" && actor == expectedActor && owner == actor);
        ++actorCalls;
    }
    void ApplySpellPoint(const std::string&, Map* area, Point, Scriptable*, int) {
        ++pointCalls;
        if (!area) throw std::runtime_error("point application needs an area");
    }
};
Core instance;
Core* core = &instance;
'''.replace("CLASS_ROW", str(class_row)).replace("CLASS_ID", str(class_id))
    cpp += "\n" + callback + r'''
int main() {
    Actor actor;
    actor.classID = CLASS_ID;
    core->expectedActor = &actor;
    Effect effect { 0, CLASS_ROW, 2, 0, "CIFS4", {} };
    assert(fx_add_effects_list(&actor, &actor, &effect) == FX_NOT_APPLIED);
    assert(core->actorCalls == 1 && core->pointCalls == 0 && actor.areaQueries == 0);
    actor.classID = CLASS_ID + 1;
    fx_add_effects_list(&actor, &actor, &effect);
    assert(core->actorCalls == 1 && core->pointCalls == 0);
    // Negative control: self targeting would still take the unsafe point path.
    actor.classID = CLASS_ID;
    effect.Target = FX_TARGET_SELF;
    bool rejected = false;
    try { fx_add_effects_list(&actor, &actor, &effect); }
    catch (const std::runtime_error&) { rejected = true; }
    assert(rejected && core->pointCalls == 1 && actor.areaQueries == 1);
}
'''.replace("CLASS_ROW", str(class_row)).replace("CLASS_ID", str(class_id))
    with tempfile.TemporaryDirectory(prefix="cipher-startup-dispatch-") as folder:
        binary = Path(folder) / "startup-dispatch"
        subprocess.run([compiler, "-std=c++14", "-Wall", "-Wextra", "-Werror", "-x", "c++", "-", "-o", str(binary)],
                       input=cpp, text=True, check=True)
        subprocess.run([str(binary)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("gemrb_root", type=Path)
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    validate(args.game.resolve(), args.gemrb_root.resolve(), args.cxx)
    print("Cipher installed CIFCORE/CIFS4 and actual opcode actor routing passed without an area (controlled API coverage only).")


if __name__ == "__main__":
    main()
