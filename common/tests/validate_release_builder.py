#!/usr/bin/env python3
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "common" / "tools" / "build_release.py"
SHARED_VALIDATE = ROOT / "common" / "tests" / "validate.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fake_weidu(path):
    path.write_text('''#!/usr/bin/env python3
from pathlib import Path
import sys

args = sys.argv[1:]
if "--parse-check" in args:
    raise SystemExit(0)
if not args:
    raise SystemExit(2)
tp2 = args[0].replace("\\\\", "/")
try:
    game = Path(args[args.index("--game") + 1])
except (ValueError, IndexError):
    raise SystemExit(2)
log = game / "WeiDU.log"
lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.is_file() else []
if "--force-install-list" in args:
    component = args[args.index("--force-install-list") + 1]
    line = f"~{tp2}~ #0 #{component} // synthetic release validation"
    normalized = line.casefold()
    if all(existing.casefold() != normalized for existing in lines):
        lines.append(line)
elif "--force-uninstall" in args:
    component = args[args.index("--force-uninstall") + 1]
    needle = f"~{tp2}~ #0 #{component}".casefold()
    lines = [line for line in lines if needle not in line.casefold()]
else:
    raise SystemExit(2)
if lines:
    log.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
elif log.exists():
    log.unlink()
raise SystemExit(0)
''', encoding="utf-8")
    path.chmod(0o755)


def run_driver(game, guiscripts, weidu, *args):
    command = [
        sys.executable,
        str(game / "gemrb_mods.py"),
        *args,
        "--game", str(game),
        "--guiscripts", str(guiscripts),
    ]
    if args and args[0] != "status":
        command.extend(["--weidu", str(weidu)])
    result = subprocess.run(
        command,
        cwd=game,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    print("+", " ".join(command), flush=True)
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
    if result.returncode != 0:
        raise AssertionError(f"driver command failed ({result.returncode}): {result.stdout}")
    return result.stdout


def assert_archive_shape(archive):
    with zipfile.ZipFile(archive, "r") as bundle:
        names = bundle.namelist()
        assert names == sorted(names), "archive order is not deterministic"
        required = {
            "gemrb_mods.py",
            "common/runtime-version.json",
            "common/tools/install_guiscripts.py",
            "cipher/package.json",
            "cipher/setup-cipher.tp2",
            "cipher/guiscripts/Cipher.py",
            "psion/package.json",
            "psion/setup-psion.tp2",
            "psion/guiscripts/Psionics.py",
            "release-manifest.json",
        }
        assert required <= set(names), sorted(required - set(names))
        assert not any("/tests/" in f"/{name}" for name in names)
        assert not any("/backup/" in f"/{name}" for name in names)
        assert not any(name.startswith(".github/") for name in names)
        manifest = json.loads(bundle.read("release-manifest.json").decode("utf-8"))
        assert manifest["schema_version"] == 1
        assert [row["name"] for row in manifest["packages"]] == ["cipher", "psion"]
        manifest_paths = {row["path"] for row in manifest["files"]}
        assert manifest_paths == set(names) - {"release-manifest.json"}
        for row in manifest["files"]:
            payload = bundle.read(row["path"])
            assert hashlib.sha256(payload).hexdigest() == row["sha256"]
            assert len(payload) == row["size"]


def main():
    builder = load("release_builder_validation", BUILDER)
    shared = load("shared_fixture_validation", SHARED_VALIDATE)

    with tempfile.TemporaryDirectory(prefix="gemrb-release-builder-") as folder_name:
        root = Path(folder_name)
        first_dir = root / "first"
        second_dir = root / "second"
        first, first_manifest = builder.build_release(["cipher", "psion"], first_dir)
        second, second_manifest = builder.build_release(["cipher", "psion"], second_dir)
        assert first_manifest == second_manifest
        assert sha256(first) == sha256(second), "same inputs did not produce identical ZIP bytes"
        assert_archive_shape(first)

        game = root / "game"
        game.mkdir()
        (game / "chitin.key").write_bytes(b"synthetic-game")
        (game / "gemrb_path.txt").write_text("GemRB_Data_Path = synthetic\n", encoding="utf-8")
        with zipfile.ZipFile(first, "r") as bundle:
            bundle.extractall(game)

        guiscripts = root / "GUIScripts"
        originals = shared.fixture_texts()
        shared.write_fixture(guiscripts, originals)
        original_bytes = {
            name: (guiscripts / name).read_bytes()
            for name in originals
        }
        weidu = root / "weidu"
        write_fake_weidu(weidu)

        run_driver(game, guiscripts, weidu, "preflight", "cipher")
        run_driver(game, guiscripts, weidu, "preflight", "psion")
        run_driver(game, guiscripts, weidu, "install", "cipher")
        run_driver(game, guiscripts, weidu, "install", "psion")

        status_text = run_driver(game, guiscripts, weidu, "status", "--json")
        status = json.loads(status_text)
        by_mod = {row["mod"]: row for row in status}
        assert by_mod["cipher"]["state"] == "installed with other handlers", by_mod
        assert by_mod["psion"]["state"] == "installed with other handlers", by_mod
        assert (guiscripts / ".gemrbmodcore.cipher.active").is_file()
        assert (guiscripts / ".gemrbmodcore.psionics.active").is_file()

        run_driver(game, guiscripts, weidu, "uninstall", "cipher")
        assert not (guiscripts / ".gemrbmodcore.cipher.active").exists()
        assert (guiscripts / ".gemrbmodcore.psionics.active").is_file()
        assert (guiscripts / "GemRBModCore.py").is_file()

        run_driver(game, guiscripts, weidu, "uninstall", "psion")
        assert not (game / "WeiDU.log").exists()
        assert not list(guiscripts.glob(".gemrbmodcore.*.active"))
        for name, original in original_bytes.items():
            assert (guiscripts / name).read_bytes() == original, name
        assert not (guiscripts / "GemRBModCore.py").exists()
        assert not (guiscripts / "Cipher.py").exists()
        assert not (guiscripts / "Psionics.py").exists()

    print("Deterministic release archive and clean-extraction lifecycle validation passed")


if __name__ == "__main__":
    main()
