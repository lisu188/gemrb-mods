#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODS = {
    "cipher": {
        "setup": "cipher/setup-cipher.tp2",
        "handler": "Cipher",
        "runtime": "cipher/guiscripts/Cipher.py",
        "dependencies": ("cipher/guiscripts/CipherSubclass.py",),
    },
    "psion": {
        "setup": "psion/setup-psion.tp2",
        "handler": "Psionics",
        "runtime": "psion/guiscripts/Psionics.py",
        "dependencies": (
            "psion/guiscripts/Psicrystal.py",
            "psion/guiscripts/PsionAI.py",
        ),
    },
    "sorcerer-monk": {
        "setup": "sorcerer-monk/setup-sorcerer-monk.tp2",
        "handler": None,
        "runtime": None,
        "dependencies": (),
    },
}
MANIFEST = "gemrb-mods-release.json"
IGNORED_PARTS = {"backup", "__pycache__", ".pytest_cache"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(root: Path, modules: list[str]) -> list[Path]:
    paths = [root / "tools" / "gemrb_mods.py"]
    for directory in ["common", *modules]:
        base = root / directory
        if not base.is_dir():
            raise SystemExit(f"Missing bundled directory: {base}")
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
                continue
            paths.append(path)
    return sorted(set(paths))


def build_manifest(root: Path, modules: list[str]) -> dict:
    files = {}
    for path in included_files(root, modules):
        relative = path.relative_to(root).as_posix()
        files[relative] = sha256(path)
    return {"schema": 1, "modules": modules, "files": files}


def verify_manifest(root: Path) -> None:
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise SystemExit("Unsupported release manifest schema")
    failures = []
    for relative, expected in manifest.get("files", {}).items():
        path = root / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
        elif sha256(path) != expected:
            failures.append(f"mismatched {relative}")
    if failures:
        raise SystemExit("Release bundle validation failed before mutation: " + "; ".join(failures))


def validate_target(game: Path, guiscripts: Path | None, modules: list[str], weidu: str) -> None:
    verify_manifest(ROOT)
    if not game.is_dir():
        raise SystemExit(f"Game directory does not exist: {game}")
    if not (game / "gemrb_path.txt").is_file():
        raise SystemExit(f"{game}/gemrb_path.txt is missing; run GemRB against the game first")
    if shutil.which(weidu) is None and not Path(weidu).is_file():
        raise SystemExit(f"WeiDU executable not found: {weidu}")
    handlers = [MODS[name]["handler"] for name in modules if MODS[name]["handler"]]
    if handlers:
        if guiscripts is None:
            raise SystemExit("--guiscripts is required for Cipher or Psion")
        required = ("ActionsWindow.py", "Spellbook.py", "MenuWindow.py", "GUISTORE.py")
        missing = [name for name in required if not (guiscripts / name).is_file()]
        if missing:
            raise SystemExit("GemRB GUIScripts target is incomplete: " + ", ".join(missing))


def stage_bundle(game: Path, modules: list[str]) -> None:
    for directory in ["common", *modules]:
        source = ROOT / directory
        target = game / directory
        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("backup", "__pycache__", ".pytest_cache"),
        )


def run_weidu(game: Path, weidu: str, setup: str, install: bool) -> None:
    mode = "--force-install" if install else "--force-uninstall"
    command = [weidu, setup, "--use-lang", "en_US", mode, "0", "--no-exit-pause"]
    subprocess.run(command, cwd=game, check=True)


def load_gui_installer(game: Path):
    tools = game / "common" / "tools"
    sys.path.insert(0, str(tools))
    try:
        import install_guiscripts
    finally:
        sys.path.pop(0)
    return install_guiscripts


def install(args) -> None:
    modules = list(dict.fromkeys(args.modules))
    validate_target(args.game, args.guiscripts, modules, args.weidu)
    stage_bundle(args.game, modules)
    installed = []
    gui_installer = load_gui_installer(args.game)
    gui_installed = []
    try:
        for name in modules:
            run_weidu(args.game, args.weidu, MODS[name]["setup"], True)
            installed.append(name)
        for name in modules:
            handler = MODS[name]["handler"]
            if not handler:
                continue
            runtime = args.game / MODS[name]["runtime"]
            dependencies = tuple(args.game / path for path in MODS[name]["dependencies"])
            gui_installer.install_handler(args.guiscripts, handler, runtime, dependencies)
            gui_installed.append(name)
    except Exception:
        for name in reversed(gui_installed):
            try:
                gui_installer.uninstall_handler(args.guiscripts, MODS[name]["handler"])
            except Exception:
                pass
        for name in reversed(installed):
            try:
                run_weidu(args.game, args.weidu, MODS[name]["setup"], False)
            except Exception:
                pass
        raise


def uninstall(args) -> None:
    modules = list(dict.fromkeys(args.modules))
    validate_target(args.game, args.guiscripts, modules, args.weidu)
    gui_installer = load_gui_installer(args.game)
    for name in reversed(modules):
        run_weidu(args.game, args.weidu, MODS[name]["setup"], False)
        handler = MODS[name]["handler"]
        if handler:
            gui_installer.uninstall_handler(args.guiscripts, handler)


def package(args) -> None:
    modules = list(dict.fromkeys(args.modules))
    verify_manifest(ROOT)
    manifest = build_manifest(ROOT, modules)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gemrb-mods-") as temp_dir:
        staging = Path(temp_dir) / "gemrb-mods"
        staging.mkdir()
        for path in included_files(ROOT, modules):
            relative = path.relative_to(ROOT)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        (staging / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, Path("gemrb-mods") / path.relative_to(staging))
    print(output)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subparsers = root.add_subparsers(dest="command", required=True)
    for command, callback in (("install", install), ("uninstall", uninstall)):
        sub = subparsers.add_parser(command)
        sub.add_argument("modules", nargs="+", choices=tuple(MODS))
        sub.add_argument("--game", type=Path, required=True)
        sub.add_argument("--guiscripts", type=Path)
        sub.add_argument("--weidu", default="weidu")
        sub.set_defaults(callback=callback)
    sub = subparsers.add_parser("package")
    sub.add_argument("modules", nargs="+", choices=tuple(MODS))
    sub.add_argument("--output", type=Path, required=True)
    sub.set_defaults(callback=package)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.callback(args)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
