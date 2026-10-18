#!/usr/bin/env python3
"""Run a real non-party Psion scripted cast against the pinned GemRB engine."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINTS = ("accepted_hook", "power_delivered", "pp_spent_once", "combat_completed", "saved", "loaded")
TABLES = {"trigger.ids", "action.ids", "object.ids", "gemtrig.ids", "classes.2da",
          "clastext.2da", "clskills.2da", "hpclass.2da", "qslots.2da", "class.ids",
          "proftype.2da", "weapprof.2da", "xplevel.2da", "thac0.2da", "xpcap.2da"}


def configure_probe_rules(override):
    trigger = override / "trigger.ids"
    text = trigger.read_text(encoding="ascii")
    used = set()
    for name in ("trigger.ids", "gemtrig.ids"):
        path = override / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="ascii").splitlines():
            try:
                used.add(int(line.split()[0], 0) & 0x3FFF)
            except (ValueError, IndexError):
                continue
    for declaration in ("InParty(O:Object*)", "ObjectActionListEmpty(O:Object*)", "CombatCounter(I:Value*)"):
        symbol = declaration.split("(")[0]
        if re.search(r"\b" + symbol + r"\s*\(", text, re.IGNORECASE):
            continue
        # Demo IDS are intentionally sparse. GemRB binds fixture-only numbers
        # by function name; avoid both game and extension dictionary entries.
        number = next(index for index in range(1, 300) if index not in used)
        used.add(number)
        text = text.rstrip() + "\n0x%04x %s\n" % (0x4000 | number, declaration)
    trigger.write_text(text, encoding="ascii")
    # Demo INTMOD has no Maze columns. Native Maze replaces the SPL duration
    # using columns 3/4; use six one-sided dice for a deterministic six rounds.
    (override / "intmod.2da").write_text(
        "2DA V1.0\n0\nLEARN LEVEL SPELLS MAZE_SIZE MAZE_DICE\n"
        + "".join(f"{value} 0 0 0 1 6\n" for value in range(26)), encoding="ascii",
    )


def prepare(root, engine_source, runtime, installed, weidu="weidu"):
    game = root / "game"
    shutil.copytree(engine_source / "demo", game)
    scripts = root / "GUIScripts"
    shutil.copytree(engine_source / "gemrb/GUIScripts", scripts)
    override = game / "override"
    for path in (installed / "override").iterdir():
        name = path.name.casefold()
        if not (name.startswith(("ps", "px", "clabp", "mxpsion", "savepsi")) or name in TABLES):
            continue
        for old in override.iterdir():
            if old.name.casefold() == name:
                old.unlink()
        shutil.copy2(path, override / name)
    # Reuse the companion fixture's checked extraction of BIFF-only IDS. The
    # demo's numbering differs from the installed game's BCS action numbering.
    spec = importlib.util.spec_from_file_location("enemy_script_ids", ROOT / "psion/tests/validate_psicrystal_native.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.copy_script_ids(root, installed, override, weidu)
    configure_probe_rules(override)
    avatars = next(path for path in (installed / "override").iterdir() if path.name.casefold() == "avatars.2da")
    row = next(line for line in avatars.read_text().splitlines() if "PSCRANI" in line.upper())
    with (override / "avatars.2da").open("a") as out:
        out.write("\n" + row + "\n")
    spec = importlib.util.spec_from_file_location("enemy_runtime_installer", ROOT / "common/tools/install_guiscripts.py")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    installer.install_handler(scripts, "Psionics", ROOT / "psion/guiscripts/Psionics.py")
    shutil.copy2(ROOT / "psion/tests/enemy_psion_native_scenario.py", scripts / "EnemyPsionProbe.py")
    for name in ("effects.ids", "savegame.2da"):
        shutil.copy2(engine_source / "gemrb/unhardcoded/bgee" / name, override / name)
    (override / "fatigmod.2da").write_text("2DA V1.0\n0\nVALUE\n0 0\n")
    (override / "mxsplwis.2da").write_text("2DA V1.0\n0\n1 2 3 4 5 6 7 8 9\n" + "".join(f"{value} 0 0 0 0 0 0 0 0 0\n" for value in range(1, 26)))
    shutil.copy2(override / "CHMB1G17.BAM", override / "CHMB1G16.BAM")
    shutil.copy2(installed / "lang/en_US/dialog.tlk", game / "dialog.tlk")
    (scripts / "demo/SetupGame.py").write_text("""import GemRB

def OnLoad():
    GemRB.CreatePlayer("protagon", 1 | 0x8000)
    GemRB.SetPlayerName(1, "Target")
    GemRB.SetPlayerStat(1, 1, 80)
    GemRB.SetPlayerStat(1, 0, 80)
    GemRB.EnterGame()
    import EnemyPsionProbe
    EnemyPsionProbe.schedule(EnemyPsionProbe.start, 1500)
""")
    for name in ("cache", "saves"):
        (root / name).mkdir()
    config = root / "GemRB.cfg"
    config.write_text(f"""GameType=demo
GamePath={game}
GemRBPath={runtime / 'share/gemrb'}
GUIScriptsPath={root}
PluginsPath={runtime / 'lib/gemrb/plugins'}
CachePath={root / 'cache'}
SavePath={root / 'saves'}
AudioDriver=none
VideoDriver=SDLVideo
Width=640
Height=480
SkipIntroVideos=1
FullScreen=0
CaseSensitive=1
""")
    return config


def run(args):
    engine_commit = subprocess.check_output(
        ["git", "-C", str(args.engine_source.resolve()), "rev-parse", "--verify", "HEAD"], text=True,
    ).strip()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    config = prepare(root, args.engine_source.resolve(), args.runtime.resolve(), args.installed.resolve(), args.weidu)
    environment = os.environ.copy()
    runtime = args.runtime.resolve()
    paths = [str(runtime / "lib"), str(runtime / "lib/gemrb")]
    if environment.get("LD_LIBRARY_PATH"):
        paths.append(environment["LD_LIBRARY_PATH"])
    environment["LD_LIBRARY_PATH"] = ":".join(paths)
    if (runtime / "python/lib").is_dir():
        environment["PYTHONHOME"] = str(runtime / "python")
    environment.update(PYTHONUNBUFFERED="1", SDL_AUDIODRIVER="dummy")
    command = ["xvfb-run", "-a", str(runtime / "bin/gemrb"), "-c", str(config)]
    log = root / "engine.log"
    with log.open("w") as output:
        completed = subprocess.run(command, env=environment, cwd=root, stdout=output,
                                   stderr=subprocess.STDOUT, timeout=45)
    text = log.read_text(errors="replace")
    checkpoints = [json.loads(line.split("ENEMY_PSION_NATIVE ", 1)[1])
                   for line in text.splitlines() if "ENEMY_PSION_NATIVE {" in line]
    assert completed.returncode == 0, (completed.returncode, log)
    assert "ENEMY_PSION_NATIVE_PASS" in text and "ENEMY_PSION_NATIVE_FAIL" not in text, log
    assert [entry["checkpoint"] for entry in checkpoints] == list(CHECKPOINTS), checkpoints
    for failure in ("Traceback", "Unhandled trigger", "Invalid scripting trigger:", "Invalid scripting action:",
                    "[GUIScript/ERROR]: Runtime Error:",
                    "[GUIScript/ERROR]: Unhandled target type"):
        assert failure not in text, (failure, log)
    report = {
        "engine_contract_commit": engine_commit,
        "fixture": "public GemRB demo plus actual WeiDU-installed Psion resources",
        "checkpoints": checkpoints,
        "campaign_acceptance": False,
    }
    (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--weidu", default="weidu", help="WeiDU executable for BIFF-only script IDS")
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
