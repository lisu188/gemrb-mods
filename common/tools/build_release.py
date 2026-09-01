#!/usr/bin/env python3
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "gemrb_mods.py"
SUPPORTED_MODS = ("cipher", "psion")
ROOT_FILES = (
    "gemrb_mods.py",
    "README.md",
    "COPYING",
)
COMMON_FILES = (
    "common/README.md",
    "common/runtime-version.json",
    "common/tools/install_guiscripts.py",
)
COMMON_DIRS = (
    "common/guiscripts",
    "common/weidu",
)
MOD_FILES = (
    "README.md",
    "package.json",
)
MOD_OPTIONAL_FILES = (
    "CHANGELOG.md",
)
MOD_DIRS = (
    "guiscripts",
    "lib",
    "tables",
    "tools",
    "tra",
)
EXCLUDED_PARTS = {"backup", "tests", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MANIFEST_NAME = "release-manifest.json"


def load_driver():
    spec = importlib.util.spec_from_file_location("gemrb_mods_release_driver", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def should_include(path):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix.casefold() in EXCLUDED_SUFFIXES:
        return False
    if path.name in {".DS_Store"}:
        return False
    return path.is_file()


def require_path(relative):
    path = ROOT / relative
    if not path.exists():
        raise RuntimeError(f"release input is missing: {relative}")
    return path


def add_file(files, relative):
    path = require_path(relative)
    if not path.is_file():
        raise RuntimeError(f"release input must be a file: {relative}")
    files[relative] = path


def add_tree(files, relative):
    root = require_path(relative)
    if not root.is_dir():
        raise RuntimeError(f"release input must be a directory: {relative}")
    included = 0
    for path in sorted(root.rglob("*")):
        if should_include(path):
            key = path.relative_to(ROOT).as_posix()
            files[key] = path
            included += 1
    if included == 0:
        raise RuntimeError(f"release directory contains no files: {relative}")


def normalize_mods(mods):
    if not mods:
        raise RuntimeError("at least one package is required")
    result = []
    for mod in mods:
        if mod not in SUPPORTED_MODS:
            raise RuntimeError(f"unsupported release package: {mod}")
        if mod not in result:
            result.append(mod)
    return result


def collect_release_files(mods):
    mods = normalize_mods(mods)
    driver = load_driver()
    contexts = {}
    files = {}

    for relative in ROOT_FILES:
        add_file(files, relative)
    for relative in COMMON_FILES:
        add_file(files, relative)
    for relative in COMMON_DIRS:
        add_tree(files, relative)

    for mod in mods:
        context = driver.load_package_context(ROOT, mod)
        contexts[mod] = context
        setup_name = Path(context["package"]["weidu"]["tp2"]).name
        for name in MOD_FILES:
            add_file(files, f"{mod}/{name}")
        add_file(files, f"{mod}/{setup_name}")
        for name in MOD_OPTIONAL_FILES:
            candidate = ROOT / mod / name
            if candidate.is_file():
                files[f"{mod}/{name}"] = candidate
        for name in MOD_DIRS:
            add_tree(files, f"{mod}/{name}")

        runtime_source = context["package"]["runtime_source"]
        tp2 = context["package"]["weidu"]["tp2"]
        for required in (runtime_source, tp2, f"{mod}/package.json"):
            if required not in files:
                raise RuntimeError(f"allowlist omitted required package file: {required}")

    gui_installer = "common/tools/install_guiscripts.py"
    if gui_installer not in files:
        raise RuntimeError("allowlist omitted shared GUI installer")
    return contexts, files


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def build_manifest(mods, contexts, files):
    runtime = next(iter(contexts.values()))["runtime"]
    package_rows = []
    for mod in mods:
        package = contexts[mod]["package"]
        package_rows.append({
            "name": package["name"],
            "version": package["version"],
            "runtime_api": package["runtime_api"],
            "handler": package["handler"],
            "weidu_component": package["weidu"]["component"],
        })
    file_rows = []
    for relative, path in sorted(files.items()):
        data = path.read_bytes()
        file_rows.append({
            "path": relative,
            "sha256": sha256_bytes(data),
            "size": len(data),
        })
    return {
        "schema_version": 1,
        "runtime": {
            "api": runtime["runtime_api"],
            "revision": runtime["revision"],
        },
        "packages": package_rows,
        "files": file_rows,
    }


def release_filename(mods, contexts):
    pieces = ["gemrb-mods"]
    for mod in mods:
        pieces.extend((mod, contexts[mod]["package"]["version"]))
    return "-".join(pieces) + ".zip"


def zip_info(name, executable=False):
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if executable else 0o644
    info.external_attr = (mode & 0xFFFF) << 16
    info.create_system = 3
    return info


def write_release(output, mods, contexts, files):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / release_filename(mods, contexts)
    if archive.exists():
        archive.unlink()

    manifest = build_manifest(mods, contexts, files)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with zipfile.ZipFile(archive, "w") as bundle:
        for relative, path in sorted(files.items()):
            executable = relative == "gemrb_mods.py" or relative.endswith("/install_guiscripts.py")
            bundle.writestr(zip_info(relative, executable), path.read_bytes())
        bundle.writestr(zip_info(MANIFEST_NAME), manifest_bytes)
    return archive, manifest


def verify_archive(archive, mods, contexts, files):
    expected = set(files) | {MANIFEST_NAME}
    with zipfile.ZipFile(archive, "r") as bundle:
        names = bundle.namelist()
        if names != sorted(names):
            raise RuntimeError("release ZIP members are not deterministically ordered")
        if set(names) != expected:
            missing = sorted(expected - set(names))
            extra = sorted(set(names) - expected)
            raise RuntimeError(f"release ZIP member mismatch; missing={missing}, extra={extra}")
        for name in files:
            if sha256_bytes(bundle.read(name)) != sha256_bytes(files[name].read_bytes()):
                raise RuntimeError(f"release ZIP content mismatch: {name}")
        manifest = json.loads(bundle.read(MANIFEST_NAME).decode("utf-8"))
        if manifest != build_manifest(mods, contexts, files):
            raise RuntimeError("release manifest does not match archive inputs")
    return True


def build_release(mods, output):
    mods = normalize_mods(mods)
    contexts, files = collect_release_files(mods)
    archive, manifest = write_release(output, mods, contexts, files)
    verify_archive(archive, mods, contexts, files)
    return archive, manifest


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build deterministic gemrb-mods release ZIPs.")
    parser.add_argument("mod", nargs="+", choices=SUPPORTED_MODS)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        archive, manifest = build_release(args.mod, args.output)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        return 1
    packages = ", ".join(f"{row['name']} {row['version']}" for row in manifest["packages"])
    print(f"built {archive}: {packages}; {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
