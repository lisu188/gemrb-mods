#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import shutil
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from gemrb_acceptance import MANIFEST_SCHEMA_VERSION, utc_now, write_manifest

SUPPORTED_MODS = ("cipher", "psion", "sorcerer-monk")
ROOT = Path(__file__).resolve().parents[2]


def preflight(source_game, source_guiscripts, output, repo_root, mods):
    source_game = Path(source_game).resolve()
    source_guiscripts = Path(source_guiscripts).resolve()
    output = Path(output).resolve()
    repo_root = Path(repo_root).resolve()
    if not source_game.is_dir():
        raise ValueError(f"source game directory not found: {source_game}")
    if not source_guiscripts.is_dir():
        raise ValueError(f"source GUIScripts directory not found: {source_guiscripts}")
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    if not (repo_root / "common").is_dir():
        raise ValueError(f"common package not found under repository root: {repo_root}")
    for mod in mods:
        if mod not in SUPPORTED_MODS:
            raise ValueError(f"unsupported mod: {mod}")
        if not (repo_root / mod).is_dir():
            raise ValueError(f"mod package not found: {repo_root / mod}")
    return source_game, source_guiscripts, output, repo_root


def prepare(source_game, source_guiscripts, output, repo_root, mods, fixture_id, game_type):
    source_game, source_guiscripts, output, repo_root = preflight(
        source_game, source_guiscripts, output, repo_root, mods
    )
    output.mkdir(parents=True)
    game = output / "game"
    guiscripts = output / "guiscripts"
    try:
        shutil.copytree(source_game, game)
        shutil.copytree(source_guiscripts, guiscripts)
        for package in ("common", *mods):
            destination = game / package
            if destination.exists():
                raise ValueError(
                    f"source fixture is not clean; package path already exists: {destination}"
                )
            shutil.copytree(repo_root / package, destination)
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "fixture_id": fixture_id,
            "game_type": game_type,
            "created_at": utc_now().isoformat(),
            "game_path": "game",
            "guiscripts_path": "guiscripts",
            "packages": ["common", *mods],
        }
        manifest_path = output / "fixture.json"
        write_manifest(manifest_path, manifest)
        return manifest_path, manifest
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def load_fixture(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    game = (root / data["game_path"]).resolve()
    guiscripts = (root / data["guiscripts_path"]).resolve()
    if not game.is_dir() or not guiscripts.is_dir():
        raise ValueError(f"fixture paths are missing for {path}")
    return data, game, guiscripts


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Copy a legal game fixture and GemRB GUIScripts into a disposable acceptance workspace."
    )
    parser.add_argument("--source-game", type=Path, required=True)
    parser.add_argument("--source-guiscripts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--fixture-id", required=True)
    parser.add_argument("--game-type", required=True)
    parser.add_argument("--mod", action="append", choices=SUPPORTED_MODS, default=[])
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    mods = []
    for mod in args.mod:
        if mod not in mods:
            mods.append(mod)
    manifest_path, _ = prepare(
        args.source_game,
        args.source_guiscripts,
        args.output,
        args.repo_root,
        mods,
        args.fixture_id,
        args.game_type,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
