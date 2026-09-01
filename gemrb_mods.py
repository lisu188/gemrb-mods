#!/usr/bin/env python3
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile

SUPPORTED_MODS = ("cipher", "psion")
MANIFEST_SCHEMA_VERSION = 1
RUNTIME_MANIFEST = Path("common/runtime-version.json")
PACKAGE_MANIFEST = "package.json"
WEIDU_LOG_PATTERN = re.compile(r"~([^~]+)~\s+#\d+\s+#(\d+)")


def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"missing package file: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise RuntimeError(f"package file must contain a JSON object: {path}")
    return data


def require_int(data, field, source):
    value = data.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"{source}: {field} must be an integer")
    return value


def require_string(data, field, source):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{source}: {field} must be a non-empty string")
    return value.strip()


def tp2_version(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^VERSION\s+~([^~]+)~\s*$", text)
    if not match:
        raise RuntimeError(f"VERSION not found in {path}")
    return match.group(1)


def validate_runtime_manifest(data, source):
    if require_int(data, "schema_version", source) != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError(f"{source}: unsupported schema_version")
    runtime_api = require_int(data, "runtime_api", source)
    revision = require_string(data, "revision", source)
    if runtime_api < 1:
        raise RuntimeError(f"{source}: runtime_api must be positive")
    return {"runtime_api": runtime_api, "revision": revision}


def validate_package_manifest(data, source, expected_name):
    if require_int(data, "schema_version", source) != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError(f"{source}: unsupported schema_version")
    name = require_string(data, "name", source)
    if name != expected_name:
        raise RuntimeError(f"{source}: expected package name {expected_name}, got {name}")
    version = require_string(data, "version", source)
    runtime_api = require_int(data, "runtime_api", source)
    handler = require_string(data, "handler", source)
    runtime_source = require_string(data, "runtime_source", source)
    weidu = data.get("weidu")
    if not isinstance(weidu, dict):
        raise RuntimeError(f"{source}: weidu must be an object")
    tp2 = require_string(weidu, "tp2", source)
    component = require_int(weidu, "component", source)
    language = require_int(weidu, "language", source)
    if component < 0 or language < 0:
        raise RuntimeError(f"{source}: WeiDU component/language must be non-negative")
    return {
        "name": name,
        "version": version,
        "runtime_api": runtime_api,
        "handler": handler,
        "runtime_source": runtime_source,
        "weidu": {"tp2": tp2, "component": component, "language": language},
    }


def load_package_context(package_root, mod):
    if mod not in SUPPORTED_MODS:
        raise RuntimeError(f"unsupported package: {mod}")
    root = Path(package_root).resolve()
    runtime_path = root / RUNTIME_MANIFEST
    package_path = root / mod / PACKAGE_MANIFEST
    runtime = validate_runtime_manifest(read_json(runtime_path), runtime_path)
    package = validate_package_manifest(read_json(package_path), package_path, mod)
    if package["runtime_api"] != runtime["runtime_api"]:
        raise RuntimeError(
            f"runtime API mismatch for {mod}: package expects {package['runtime_api']}, "
            f"common provides {runtime['runtime_api']}"
        )
    tp2 = root / package["weidu"]["tp2"]
    runtime_source = root / package["runtime_source"]
    if not tp2.is_file():
        raise RuntimeError(f"missing {mod} WeiDU installer: {tp2}")
    if not runtime_source.is_file():
        raise RuntimeError(f"missing {mod} runtime handler: {runtime_source}")
    installed_version = tp2_version(tp2)
    if installed_version != package["version"]:
        raise RuntimeError(
            f"package version mismatch for {mod}: manifest {package['version']}, TP2 {installed_version}"
        )
    return {
        "root": root,
        "runtime": runtime,
        "package": package,
        "tp2": tp2,
        "runtime_source": runtime_source,
        "runtime_manifest": runtime_path,
        "package_manifest": package_path,
    }


def resolve_weidu(executable):
    resolved = shutil.which(str(executable))
    if not resolved:
        candidate = Path(executable)
        if candidate.is_file():
            resolved = str(candidate.resolve())
    if not resolved:
        raise RuntimeError(f"WeiDU executable not found: {executable}")
    return resolved


def load_gui_module(context):
    path = context["root"] / "common" / "tools" / "install_guiscripts.py"
    if not path.is_file():
        raise RuntimeError(f"missing shared GUI installer: {path}")
    spec = importlib.util.spec_from_file_location("gemrb_mods_shared_gui_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_game_root(game):
    game = Path(game).resolve()
    if not game.is_dir():
        raise RuntimeError(f"game directory not found: {game}")
    for name in ("chitin.key", "gemrb_path.txt"):
        if not (game / name).is_file():
            raise RuntimeError(f"game preflight requires {name}: {game / name}")
    return game


def validate_guiscripts_root(guiscripts):
    guiscripts = Path(guiscripts).resolve()
    if not guiscripts.is_dir():
        raise RuntimeError(f"GemRB GUIScripts directory not found: {guiscripts}")
    return guiscripts


def validate_common_modules(context, gui_module):
    common = context["root"] / "common" / "guiscripts"
    for name in gui_module.COMMON_MODULES:
        if not (common / name).is_file():
            raise RuntimeError(f"missing shared runtime module: {common / name}")


def run_command(command, cwd, timeout=600):
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def validate_weidu_parse(context, weidu):
    command = [weidu, "--nogame", "--parse-check", "TP2", str(context["tp2"])]
    result = run_command(command, context["root"], timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"WeiDU parse preflight failed for {context['package']['name']}")


def validate_gui_install(context, guiscripts):
    gui_module = load_gui_module(context)
    validate_common_modules(context, gui_module)
    with tempfile.TemporaryDirectory(prefix="gemrb-mods-gui-preflight-") as folder_name:
        copied = Path(folder_name) / "GUIScripts"
        shutil.copytree(guiscripts, copied)
        gui_module.install_handler(
            copied,
            context["package"]["handler"],
            context["runtime_source"],
        )


def preflight_install(game, guiscripts, mod, weidu="weidu"):
    game = validate_game_root(game)
    guiscripts = validate_guiscripts_root(guiscripts)
    context = load_package_context(game, mod)
    weidu = resolve_weidu(weidu)
    validate_weidu_parse(context, weidu)
    validate_gui_install(context, guiscripts)
    return context, game, guiscripts, weidu


def preflight_uninstall(game, guiscripts, mod, weidu="weidu"):
    game = validate_game_root(game)
    guiscripts = validate_guiscripts_root(guiscripts)
    context = load_package_context(game, mod)
    weidu = resolve_weidu(weidu)
    validate_weidu_parse(context, weidu)
    load_gui_module(context)
    return context, game, guiscripts, weidu


def normalize_tp2(value):
    return value.replace("\\", "/").lstrip("./").casefold()


def weidu_component_installed(game, context):
    log_path = Path(game) / "WeiDU.log"
    if not log_path.is_file():
        return False
    expected_tp2 = normalize_tp2(context["package"]["weidu"]["tp2"])
    expected_component = context["package"]["weidu"]["component"]
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = WEIDU_LOG_PATTERN.search(line)
        if not match:
            continue
        if normalize_tp2(match.group(1)) == expected_tp2 and int(match.group(2)) == expected_component:
            return True
    return False


def active_handlers(guiscripts):
    handlers = []
    for marker in Path(guiscripts).glob(".gemrbmodcore.*.active"):
        name = marker.name
        prefix = ".gemrbmodcore."
        suffix = ".active"
        if name.startswith(prefix) and name.endswith(suffix):
            handlers.append(name[len(prefix):-len(suffix)])
    return sorted(set(handlers))


def handler_runtime_evidence(guiscripts, handler):
    root = Path(guiscripts)
    tag = handler.casefold()
    marker = root / f".gemrbmodcore.{tag}.active"
    target = root / f"{handler}.py"
    backup = target.with_suffix(target.suffix + f".gemrbmodcore.{tag}.bak")
    created = target.with_suffix(target.suffix + f".gemrbmodcore.{tag}.created")
    return {
        "marker": marker.is_file(),
        "runtime_file": target.is_file(),
        "owned_backup": backup.is_file(),
        "owned_created": created.is_file(),
    }


def status_for_context(game, guiscripts, context):
    handler = context["package"]["handler"]
    tag = handler.casefold()
    handlers = active_handlers(guiscripts)
    evidence = handler_runtime_evidence(guiscripts, handler)
    weidu = weidu_component_installed(game, context)
    marker_consistent = evidence["marker"] and evidence["runtime_file"]
    runtime_evidence = evidence["marker"] or evidence["owned_backup"] or evidence["owned_created"]
    other_handlers = [name for name in handlers if name != tag]

    if weidu and marker_consistent:
        state = "installed with other handlers" if other_handlers else "installed"
    elif weidu and not runtime_evidence:
        state = "weidu only"
    elif runtime_evidence:
        state = "runtime only/inconsistent"
    else:
        state = "not installed"

    return {
        "mod": context["package"]["name"],
        "state": state,
        "weidu_installed": weidu,
        "runtime": evidence,
        "active_handlers": handlers,
        "other_handlers": other_handlers,
        "runtime_api": context["runtime"]["runtime_api"],
        "runtime_revision": context["runtime"]["revision"],
        "package_version": context["package"]["version"],
    }


def status_for_mod(game, guiscripts, mod):
    try:
        context = load_package_context(game, mod)
        return status_for_context(game, guiscripts, context)
    except (OSError, RuntimeError, ValueError) as error:
        return {"mod": mod, "state": "package error", "error": str(error)}


def weidu_command(context, game, weidu, install):
    package = context["package"]
    command = [
        weidu,
        package["weidu"]["tp2"],
        "--game", str(game),
        "--language", str(package["weidu"]["language"]),
        "--noautoupdate",
    ]
    if install:
        command.extend(["--force-install-list", str(package["weidu"]["component"])])
    else:
        command.extend(["--force-uninstall", str(package["weidu"]["component"])])
    return command


def run_weidu(context, game, weidu, install):
    command = weidu_command(context, game, weidu, install)
    result = run_command(command, game)
    if result.returncode != 0:
        phase = "install" if install else "uninstall"
        raise RuntimeError(f"WeiDU {phase} failed for {context['package']['name']} with exit code {result.returncode}")


def install_package(game, guiscripts, mod, weidu="weidu"):
    context, game, guiscripts, weidu = preflight_install(game, guiscripts, mod, weidu)
    run_weidu(context, game, weidu, True)
    gui_module = load_gui_module(context)
    try:
        gui_module.install_handler(
            guiscripts,
            context["package"]["handler"],
            context["runtime_source"],
        )
    except (OSError, RuntimeError, ValueError) as error:
        state = status_for_context(game, guiscripts, context)
        raise RuntimeError(
            f"GUI runtime install failed after WeiDU succeeded for {mod}; "
            f"current state: {state['state']}; {error}"
        ) from error
    state = status_for_context(game, guiscripts, context)
    if not state["state"].startswith("installed"):
        raise RuntimeError(f"post-install validation failed for {mod}: {state['state']}")
    return state


def uninstall_package(game, guiscripts, mod, weidu="weidu"):
    context, game, guiscripts, weidu = preflight_uninstall(game, guiscripts, mod, weidu)
    gui_module = load_gui_module(context)
    gui_module.uninstall_handler(guiscripts, context["package"]["handler"])
    try:
        run_weidu(context, game, weidu, False)
    except RuntimeError as error:
        state = status_for_context(game, guiscripts, context)
        raise RuntimeError(
            f"WeiDU uninstall failed after GUI handler removal for {mod}; "
            f"current state: {state['state']}; {error}"
        ) from error
    state = status_for_context(game, guiscripts, context)
    if state["state"] != "not installed":
        raise RuntimeError(f"post-uninstall validation failed for {mod}: {state['state']}")
    return state


def print_status(rows, as_json=False):
    if as_json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return
    for row in rows:
        if row["state"] == "package error":
            print(f"{row['mod']}: package error: {row['error']}")
        else:
            suffix = ""
            if row["other_handlers"]:
                suffix = f"; other handlers: {', '.join(row['other_handlers'])}"
            print(
                f"{row['mod']}: {row['state']} "
                f"(package {row['package_version']}, runtime API {row['runtime_api']}/{row['runtime_revision']}){suffix}"
            )


def build_parser():
    parser = argparse.ArgumentParser(description="Install and diagnose gemrb-mods class packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "uninstall", "preflight"):
        sub = subparsers.add_parser(command)
        sub.add_argument("mod", choices=SUPPORTED_MODS)
        sub.add_argument("--game", type=Path, required=True)
        sub.add_argument("--guiscripts", type=Path, required=True)
        sub.add_argument("--weidu", default="weidu")
    status = subparsers.add_parser("status")
    status.add_argument("--game", type=Path, required=True)
    status.add_argument("--guiscripts", type=Path, required=True)
    status.add_argument("--json", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "install":
            state = install_package(args.game, args.guiscripts, args.mod, args.weidu)
            print_status([state])
        elif args.command == "uninstall":
            state = uninstall_package(args.game, args.guiscripts, args.mod, args.weidu)
            print_status([state])
        elif args.command == "preflight":
            context, _, _, _ = preflight_install(args.game, args.guiscripts, args.mod, args.weidu)
            print(
                f"{args.mod}: preflight passed "
                f"(package {context['package']['version']}, runtime API "
                f"{context['runtime']['runtime_api']}/{context['runtime']['revision']})"
            )
        elif args.command == "status":
            game = Path(args.game).resolve()
            guiscripts = Path(args.guiscripts).resolve()
            rows = [status_for_mod(game, guiscripts, mod) for mod in SUPPORTED_MODS]
            print_status(rows, args.json)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
