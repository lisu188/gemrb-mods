#!/usr/bin/env python3
"""Exercise native wolf-template selection through complete WeiDU installs."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def casefold_path(directory, name):
    return next((path for path in directory.iterdir() if path.name.casefold() == name.casefold()), None)


def validate(weidu, gemrb, template):
    with tempfile.TemporaryDirectory(prefix=f"psion-construct-{template}-") as folder:
        game = Path(folder) / "game"
        subprocess.run([
            sys.executable, str(ROOT / "psion/tests/make_weidu_fixture.py"),
            "--gemrb-root", str(gemrb), "--output", str(game), "--wolf-resource", template,
        ], check=True)
        override = game / "override"
        for resource in ("wolf", "wolf01"):
            assert (casefold_path(override, resource + ".cre") is not None) == (resource == template)
        before = (override / (template + ".cre")).read_bytes() if template != "none" else None
        for package in ("common", "psion"):
            shutil.copytree(ROOT / package, game / package)
        command = [weidu, "psion/setup-psion.tp2", "--use-lang", "en_US", "--no-exit-pause"]
        result = subprocess.run(command + ["--force-install", "0"], cwd=game, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        construct = casefold_path(override, "PSACON01.CRE")
        if template == "none":
            assert result.returncode != 0, "missing both native bodies unexpectedly installed"
            assert "requires WOLF.CRE or WOLF01.CRE" in result.stdout
            assert construct is None, "failed install left a construct behind"
            return
        assert result.returncode == 0, (template, result.returncode)
        assert construct is not None, template
        after = construct.read_bytes()
        # Keep the existing name-only clone semantics: every creature field
        # outside NAME1/NAME2 must match the selected campaign template.
        assert after[:8] == before[:8] == b"CRE V1.0"
        assert after[16:] == before[16:], template
        assert after[8:16] != before[8:16], "construct name was not assigned"
        assert (override / (template + ".cre")).read_bytes() == before
        subprocess.run(command + ["--force-uninstall", "0"], cwd=game, check=True)
        assert casefold_path(override, "PSACON01.CRE") is None
        assert (override / (template + ".cre")).read_bytes() == before


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_construct_weidu.py WEIDU GEMRB_ROOT")
    for template in ("wolf", "wolf01", "none"):
        validate(sys.argv[1], Path(sys.argv[2]).resolve(), template)
    print("Psion WOLF/WOLF01 construct selection, uninstall, and missing-template rejection passed.")


if __name__ == "__main__":
    main()
