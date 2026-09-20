#!/usr/bin/env python3
"""Build owned companion bodies, lifecycle scripts and a five-direction BAM."""
from pathlib import Path
import argparse
import re
import shutil
import struct

OWNER_LIMIT = 255
OWNER_STAT = 163
BUILD_NAME = ".psion-crystal-build"


def party_slots(text):
    slots = sorted({int(match.group(1)) for match in re.finditer(
        r"(?im)^\s*(?:0x[0-9a-f]+|\d+)\s+Player([1-9]\d*)\s*(?://.*)?$", text
    )})
    if not slots or slots != list(range(1, len(slots) + 1)) or len(slots) > 32:
        raise ValueError("OBJECT.IDS must expose contiguous Player1..PlayerN selectors (N <= 32)")
    return slots


def lifecycle_script(token, slots):
    name = f"PSCR{token:03d}"
    blocks = [f'''IF
  Global("PSREADY","LOCALS",0)
THEN
  RESPONSE #100
    DestroySelf()
END

IF
  OR(2)
    GlobalLTGlobal("PSCREP","LOCALS","{name}","GLOBAL")
    GlobalGTGlobal("PSCREP","LOCALS","{name}","GLOBAL")
THEN
  RESPONSE #100
    DestroySelf()
END
''']
    missing = "\n".join(f"  !CheckStat(Player{slot},{token},{OWNER_STAT})" for slot in slots)
    blocks.append(f"IF\n{missing}\nTHEN\n  RESPONSE #100\n    DestroySelf()\nEND\n")
    for slot in slots:
        blocks.append(f'''IF
  CheckStat(Player{slot},{token},{OWNER_STAT})
  OR(2)
    !InMyArea(Player{slot})
    StateCheck(Player{slot},2048)
THEN
  RESPONSE #100
    DestroySelf()
END

IF
  ActionListEmpty()
  CheckStat(Player{slot},{token},{OWNER_STAT})
  InMyArea(Player{slot})
  !Range(Player{slot},6)
THEN
  RESPONSE #100
    MoveToObject(Player{slot})
END
''')
    return "\n".join(blocks)


def crystal_bam():
    width, height, frames = 24, 32, 4
    header_offset = 24
    cycle_offset = header_offset + 12 * frames
    palette_offset = cycle_offset + 4 * 5
    lookup_offset = palette_offset + 1024
    pixels_offset = lookup_offset + 2 * frames * 5
    data = bytearray(struct.pack("<8sHBBIII", b"BAM V1  ", frames, 5, 0,
                                 header_offset, palette_offset, lookup_offset))
    for frame in range(frames):
        data.extend(struct.pack("<HHhhI", width, height, 12, 29,
                                (pixels_offset + frame * width * height) | 0x80000000))
    for direction in range(5):
        data.extend(struct.pack("<HH", frames, direction * frames))
    palette = [(0, 255, 0), (35, 53, 75), (44, 114, 155), (74, 190, 217),
               (165, 240, 249), (226, 254, 255)]
    for red, green, blue in palette + [(0, 0, 0)] * (256 - len(palette)):
        data.extend(bytes((blue, green, red, 0)))
    for direction in range(5):
        for frame in range(frames):
            data.extend(struct.pack("<H", frame))
    for frame in range(frames):
        shift = (0, -1, -2, -1)[frame]
        pixels = bytearray(width * height)
        for y in range(height):
            for x in range(width):
                local_y = y - shift
                dx = abs(x - 11)
                if 4 <= local_y <= 25 and dx * 3 <= min(local_y - 3, 26 - local_y) * 2:
                    edge = dx * 3 > min(local_y - 3, 26 - local_y) * 2 - 3
                    pixels[y * width + x] = 1 if edge else (4 if x <= 10 else 2)
                    if x == 11 and not edge:
                        pixels[y * width + x] = 5
                    elif local_y in (13, 14) and not edge:
                        pixels[y * width + x] = 3
        data.extend(pixels)
    return bytes(data)



def extend_triggers(text, engine_text=""):
    used = {int(match.group(1), 0) & 0x3fff for match in re.finditer(
        r"(?im)^\s*(0x[0-9a-f]+|[1-9]\d*|0)\s+", text + "\n" + engine_text
    )}
    result = text.rstrip() + "\n"
    for name in ("GlobalLTGlobal", "GlobalGTGlobal", "ActuallyInCombat"):
        pattern = r"(?im)^\s*(\S+)\s+" + name + r"\s*\(([^)]*)\)"
        existing = re.findall(pattern, text)
        native = re.findall(pattern, engine_text)
        expected_args = 0 if name == "ActuallyInCombat" else 4
        for entries in (existing, native):
            if entries:
                if len(entries) != 1 or not 0 <= (int(entries[0][0], 0) & 0x3fff) < 300:
                    raise ValueError(f"unsupported or ambiguous {name} trigger ID")
                arguments = entries[0][1].split(",") if entries[0][1].strip() else []
                if len(arguments) != expected_args:
                    raise ValueError(f"unsupported {name} trigger signature")
        if existing:
            code = int(existing[0][0], 0)
            occupied = [(int(value, 0) & 0x3fff, symbol) for value, symbol in re.findall(
                r"(?im)^\s*(0x[0-9a-f]+|[1-9]\d*|0)\s+(\w+)\s*\(", engine_text)]
            if any(index == (code & 0x3fff) and symbol.casefold() != name.casefold()
                   for index, symbol in occupied):
                raise ValueError(f"{name} is overridden by an engine trigger")
            continue
        if native:
            code = int(native[0][0], 0)
        else:
            code = next((value for value in range(0x4100, 0x412c) if (value & 0x3fff) not in used), None)
            if code is None:
                raise ValueError("no free GemRB trigger ID")
            used.add(code & 0x3fff)
        signature = "" if expected_args == 0 else "S:Name1*,S:Area1*,S:Name2*,S:Area2*"
        result += f"{code:#x} {name}({signature})\n"
    return result


def extend_avatars(text):
    lines = [line.split() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "//"))]
    if lines[0] != ["2DA", "V1.0"] or lines[2] != ["AT_1", "AT_2", "AT_3", "AT_4", "TYPE", "SPACE", "PALETTE", "SIZE"]:
        raise ValueError("unsupported AVATARS.2DA schema")
    used = {int(row[0], 0) for row in lines[3:]}
    if any("PSCRANIM" in map(str.upper, row[1:5]) for row in lines[3:]):
        raise ValueError("psicrystal animation is already registered")
    animation = next((value for value in range(0xe000, 0xe100) if value not in used), None)
    if animation is None:
        raise ValueError("no free psicrystal animation ID")
    return animation, text.rstrip() + f"\n{animation:#x} PSCRANIM PSCRANIM PSCRANIM PSCRANIM 13 1 1 *\n"

def configuration(slots):
    if not 1 <= len(slots) <= 32:
        raise ValueError("invalid psicrystal party capacity")
    return f"2DA V1.0\n0\nVALUE\nOWNER_LIMIT {OWNER_LIMIT}\nPARTY_SLOTS {len(slots)}\nOWNER_STAT {OWNER_STAT}\n"


def resource_path(path):
    path = Path(path)
    if path.is_file():
        return path
    matches = [candidate for candidate in path.parent.iterdir()
               if candidate.is_file() and candidate.name.casefold() == path.name.casefold()]
    if len(matches) != 1:
        raise ValueError(f"missing or ambiguous resource: {path.name}")
    return matches[0]


def build(template, objects, triggers, avatars, output, engine_triggers):
    output = Path(output)
    if output.name != BUILD_NAME:
        raise ValueError(f"output directory must be named {BUILD_NAME}")
    body = resource_path(template).read_bytes()
    if len(body) < 0x2d4 or body[:8] != b"CRE V1.0":
        raise ValueError("psicrystal template must be a complete CRE V1.0")
    slots = party_slots(resource_path(objects).read_text(encoding="ascii"))
    trigger_text = extend_triggers(resource_path(triggers).read_text(encoding="ascii"),
                                   resource_path(engine_triggers).read_text(encoding="ascii"))
    animation, avatar_text = extend_avatars(resource_path(avatars).read_text(encoding="ascii"))
    if output.exists():
        raise FileExistsError("remove the previous owned build directory before generating companions")
    resources, scripts = output / "resources", output / "scripts"
    resources.mkdir(parents=True)
    scripts.mkdir()
    for token in range(1, OWNER_LIMIT + 1):
        name = f"PSCR{token:03d}"
        creature = bytearray(body)
        struct.pack_into("<I", creature, 0x28, animation)
        creature[0x280:0x2a0] = name.lower().encode("ascii").ljust(32, b"\0")
        creature[0x248:0x250] = name.encode("ascii").ljust(8, b"\0")
        (resources / f"{name}.cre").write_bytes(creature)
        (scripts / f"{name}.baf").write_text(lifecycle_script(token, slots), encoding="ascii")
    (resources / "PSCRANIM.bam").write_bytes(crystal_bam())
    (resources / "trigger.ids").write_text(trigger_text, encoding="ascii")
    (resources / "avatars.2da").write_text(avatar_text, encoding="ascii")
    (resources / "pscrcfg.2da").write_text(configuration(slots), encoding="ascii")


def correct_compiled(override, output):
    override, output = Path(override), Path(output)
    if output.name != BUILD_NAME or not output.is_dir() or output.is_symlink():
        raise ValueError("compiled output requires this generator's build directory")
    text = resource_path(override / "trigger.ids").read_text(encoding="ascii")
    codes = {}
    for name in ("GlobalLTGlobal", "GlobalGTGlobal"):
        matches = re.findall(r"(?im)^\s*(\S+)\s+" + name + r"\s*\(", text)
        if len(matches) != 1 or not 0 <= (int(matches[0], 0) & 0x3fff) < 300:
            raise ValueError(f"unsupported or ambiguous {name} trigger ID")
        codes[int(matches[0], 0)] = name
    compiled = output / "compiled"
    compiled.mkdir()
    for token in range(1, OWNER_LIMIT + 1):
        name = f"PSCR{token:03d}"
        counts = {code: 0 for code in codes}
        def replace(match):
            code = int(match.group(1))
            if code not in codes:
                return match.group(0)
            counts[code] += 1
            pair = (match.group(3), match.group(4))
            expected = ("LOCALSPSCREP", "GLOBAL" + name)
            if pair not in (("PSCREP", "LOCALS"), expected):
                raise ValueError(f"unexpected {name} comparison encoding: {pair}")
            return f'{code}{match.group(2)} "{expected[0]}" "{expected[1]}" OB'
        source = resource_path(override / (name + ".bcs")).read_text(encoding="ascii")
        result = re.sub(r'(?m)^(\d+)([^\n]*?) "([^"\n]*)" "([^"\n]*)" OB$', replace, source)
        if any(count != 1 for count in counts.values()):
            raise ValueError(f"incomplete {name} generation checks: {counts}")
        (compiled / (name + ".bcs")).write_text(result, encoding="ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--objects", type=Path)
    parser.add_argument("--triggers", type=Path)
    parser.add_argument("--avatars", type=Path)
    parser.add_argument("--engine-triggers", type=Path)
    parser.add_argument("--output", type=Path, default=Path(BUILD_NAME))
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--compiled", type=Path)
    args = parser.parse_args()
    if args.cleanup:
        if args.output.name != BUILD_NAME or args.output.is_symlink():
            parser.error("refusing to remove a directory not owned by this generator")
        if args.output.exists():
            shutil.rmtree(args.output)
    elif args.compiled:
        correct_compiled(args.compiled, args.output)
    elif any(value is None for value in (args.template, args.objects, args.triggers, args.avatars, args.engine_triggers)):
        parser.error("--template, --objects, --triggers, --engine-triggers and --avatars are required")
    else:
        build(args.template, args.objects, args.triggers, args.avatars, args.output, args.engine_triggers)


if __name__ == "__main__":
    main()
