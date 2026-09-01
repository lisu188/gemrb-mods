#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import sys

MARK_BEGIN = "# GEMRB MODS SOUNDSET DIAGNOSTIC BEGIN"
MARK_END = "# GEMRB MODS SOUNDSET DIAGNOSTIC END"
BACKUP_SUFFIX = ".gemrbmods-soundset.bak"
TARGETS = (
    ("bg1", Path("bg1") / "GUICG19.py"),
    ("bg2", Path("bg2") / "GUICG19.py"),
)
ENUMERATION_LINE = "\tVoices = VoiceList.ListResources (CHR_SOUNDS)\n"


def backup_path(path):
    return path.with_name(path.name + BACKUP_SUFFIX)


def diagnostic_block(family):
    return (
        ENUMERATION_LINE
        + "\t" + MARK_BEGIN + "\n"
        + "\ttry:\n"
        + "\t\t_GemRBModsSlot = GemRB.GetVar (\"Slot\")\n"
        + "\t\t_GemRBModsClass = GUICommon.GetClassRowName (_GemRBModsSlot) if _GemRBModsSlot else \"<none>\"\n"
        + "\t\t_GemRBModsGender = GemRB.GetPlayerStat (_GemRBModsSlot, IE_SEX) if _GemRBModsSlot else -1\n"
        + "\texcept Exception as _GemRBModsError:\n"
        + "\t\t_GemRBModsSlot = GemRB.GetVar (\"Slot\")\n"
        + "\t\t_GemRBModsClass = \"<diagnostic-error>\"\n"
        + "\t\t_GemRBModsGender = -1\n"
        + f"\tprint(\"GEMRB_MODS_SOUNDSET|family={family}|count=%d|slot=%s|class=%s|gender=%s|sample=%r\" % (len(Voices), _GemRBModsSlot, _GemRBModsClass, _GemRBModsGender, Voices[:8]))\n"
        + "\t" + MARK_END + "\n"
    )


def patch_file(path, family):
    text = path.read_text(encoding="utf-8")
    if MARK_BEGIN in text:
        return False
    if text.count(ENUMERATION_LINE) != 1:
        raise RuntimeError(f"{path}: CHR_SOUNDS enumeration layout not recognized")
    backup = backup_path(path)
    if backup.exists():
        raise RuntimeError(f"{path}: diagnostic backup already exists without an installed marker")
    shutil.copy2(path, backup)
    patched = text.replace(ENUMERATION_LINE, diagnostic_block(family), 1)
    path.write_text(patched, encoding="utf-8")
    return True


def restore_file(path):
    backup = backup_path(path)
    if not backup.exists():
        return False
    shutil.copy2(backup, path)
    backup.unlink()
    return True


def patch_root(guiscripts_root, uninstall=False):
    root = Path(guiscripts_root).resolve()
    changed = []
    found = 0
    for family, relative in TARGETS:
        path = root / relative
        if not path.is_file():
            continue
        found += 1
        if uninstall:
            if restore_file(path):
                changed.append(str(relative))
        elif patch_file(path, family):
            changed.append(str(relative))
    if not found:
        raise RuntimeError(f"no bg1/bg2 GUICG19.py found below {root}")
    return changed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Temporarily instrument GemRB chargen soundset enumeration for acceptance diagnostics."
    )
    parser.add_argument("guiscripts_root", type=Path)
    parser.add_argument("--uninstall", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    changed = patch_root(args.guiscripts_root, args.uninstall)
    action = "restored" if args.uninstall else "instrumented"
    for path in changed:
        print(f"{action}: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
