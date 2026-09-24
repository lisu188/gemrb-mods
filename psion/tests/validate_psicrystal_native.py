#!/usr/bin/env python3
"""Run the actual pinned engine against public demo assets and installed Psion rules."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINTS = ("accepted_cast", "saved", "loaded", "dismiss_and_remanifest",
               "area_remanifest", "body_death_resummon", "owner_death_cleanup")
TABLES = {"trigger.ids", "action.ids", "object.ids", "gemtrig.ids", "classes.2da",
          "clastext.2da", "clskills.2da", "hpclass.2da", "qslots.2da", "class.ids",
          "proftype.2da", "weapprof.2da", "xplevel.2da", "thac0.2da", "xpcap.2da"}
SCRIPT_IDS = {"trigger.ids", "action.ids", "object.ids"}


def copy_script_ids(root, installed, override, weidu):
    """Use the installed game's script numbering, including BIFF-only tables."""
    available = {path.name.casefold() for path in (installed / "override").iterdir()}
    missing = sorted(SCRIPT_IDS - available)
    if not missing:
        return
    executable = shutil.which(str(weidu))
    if not executable:
        raise RuntimeError("WeiDU is required to extract BIFF-only script IDS; pass --weidu")
    log = root / "weidu-ids.log"
    with tempfile.TemporaryDirectory(prefix="script-ids-", dir=root) as directory:
        destination = Path(directory)
        command = [str(Path(executable).resolve()), "--use-lang", "en_US",
                   "--out", str(destination), "--log", str(root / "weidu-ids.debug"),
                   "--no-exit-pause"]
        for name in missing:
            command += ["--biff-get", name]
        with log.open("w") as output:
            subprocess.run(command, cwd=installed, stdout=output,
                           stderr=subprocess.STDOUT, check=True, timeout=60)
        extracted = {path.name.casefold(): path for path in destination.iterdir() if path.is_file()}
        # WeiDU can exit successfully after a fatal extraction error. Never
        # silently retain the demo's incompatible script-numbering tables.
        if any(name not in extracted for name in missing):
            raise RuntimeError(f"Script IDS extraction incomplete; see {log}")
        for name in missing:
            for old in override.iterdir():
                if old.name.casefold() == name:
                    old.unlink()
            shutil.copy2(extracted[name], override / name)


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
    copy_script_ids(root, installed, override, weidu)
    avatars = next(path for path in (installed / "override").iterdir() if path.name.casefold() == "avatars.2da")
    row = next(line for line in avatars.read_text().splitlines() if "PSCRANI" in line.upper())
    with (override / "avatars.2da").open("a") as out:
        out.write("\n" + row + "\n")
    for path in (ROOT / "common/guiscripts").glob("*.py"):
        shutil.copy2(path, scripts / path.name)
    shutil.copy2(ROOT / "psion/guiscripts/Psionics.py", scripts / "Psionics.py")
    shutil.copy2(ROOT / "psion/tests/psicrystal_native_scenario.py", scripts / "CompanionProbe.py")
    for name in ("effects.ids", "savegame.2da"):
        shutil.copy2(engine_source / "gemrb/unhardcoded/bgee" / name, override / name)
    (override / "fatigmod.2da").write_text("2DA V1.0\n0\nVALUE\n0 0\n")
    (override / "mxsplwis.2da").write_text("2DA V1.0\n0\n1 2 3 4 5 6 7 8 9\n" + "".join(f"{value} 0 0 0 0 0 0 0 0 0\n" for value in range(1, 26)))
    shutil.copy2(override / "CHMB1G17.BAM", override / "CHMB1G16.BAM")
    shutil.copy2(installed / "lang/en_US/dialog.tlk", game / "dialog.tlk")
    (scripts / "demo/SetupGame.py").write_text('''import GemRB

def OnLoad():
    for actor in (1, 2):
        GemRB.CreatePlayer("protagon", actor | 0x8000)
        row = "PSION_SEER" if actor == 1 else "PSION_EGOIST"
        GemRB.SetPlayerStat(actor, 232, GemRB.LoadTable("clastext").GetValue(row, "CLASSID"))
        GemRB.SetPlayerName(actor, "Psion %d" % actor)
        GemRB.SetPlayerStat(actor, 1, 80)
        GemRB.SetPlayerStat(actor, 0, 80)
        GemRB.SetPlayerStat(actor, 34, 5)
    GemRB.EnterGame()
    import CompanionProbe
    CompanionProbe.schedule(CompanionProbe.start, 1500)
''')
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
                                   stderr=subprocess.STDOUT, timeout=55)
    text = log.read_text(errors="replace")
    checkpoints = [json.loads(line.split("PSICRYSTAL_NATIVE ", 1)[1])
                   for line in text.splitlines() if "PSICRYSTAL_NATIVE {" in line]
    assert completed.returncode == 0, (completed.returncode, log)
    assert "PSICRYSTAL_NATIVE_PASS" in text and "PSICRYSTAL_NATIVE_FAIL" not in text, log
    assert [entry["checkpoint"] for entry in checkpoints] == list(CHECKPOINTS), checkpoints
    assert "Traceback" not in text and "Unhandled trigger" not in text, log
    report = {"engine_contract_commit": "28d8a9d2ebd19f0de560856e67dc3cd7a7b74204",
              "fixture": "public GemRB demo plus actual WeiDU-installed Psion resources",
              "checkpoints": checkpoints, "campaign_acceptance": False}
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
