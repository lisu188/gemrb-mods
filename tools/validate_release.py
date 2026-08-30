#!/usr/bin/env python3
from pathlib import Path
import argparse
import importlib.util
import json
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_driver", ROOT / "tools/gemrb_mods.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

EXPECTED = {
    "cipher": "0.3.0",
    "psion": "1.4.0",
    "sorcerer-monk": "2.0",
}


def tp2_version(path):
    match = re.search(r"(?m)^VERSION ~([^~]+)~$", path.read_text(encoding="utf-8"))
    assert match, path
    return match.group(1)


def main():
    for name, version in EXPECTED.items():
        setup = ROOT / driver.MODS[name]["setup"]
        assert tp2_version(setup) == version
        readme = (ROOT / name / "README.md").read_text(encoding="utf-8")
        assert version in readme

    psion = (ROOT / "psion/README.md").read_text(encoding="utf-8")
    assert "Powers are selected by the player" in psion
    assert "current Intelligence" in psion
    assert "Psicrystals" in psion
    assert "PSIITM06" in psion
    assert "cannot yet dynamically alter" not in psion
    assert "fixed power progression" not in psion

    cipher = (ROOT / "cipher/README.md").read_text(encoding="utf-8")
    assert "completes the Reaping Knives Focus-transfer loop" in cipher
    assert "Soul Blade" in cipher
    assert "does not yet transfer Focus" not in cipher
    assert "Soul Blade, and Ascendant are not implemented" not in cipher

    compatibility = (ROOT / "COMPATIBILITY.md").read_text(encoding="utf-8")
    for name, version in EXPECTED.items():
        assert name.replace("-", "/").lower() in compatibility.lower() or name.lower() in compatibility.lower()
        assert version in compatibility
    assert "Live accepted" in compatibility
    assert "does not infer live acceptance" in compatibility

    assert driver.MODS["cipher"]["dependencies"] == ("cipher/guiscripts/CipherSubclass.py",)
    assert set(driver.MODS["psion"]["dependencies"]) == {
        "psion/guiscripts/Psicrystal.py",
        "psion/guiscripts/PsionAI.py",
    }
    driver.verify_runtime_api(ROOT, ["cipher", "psion"])

    manifest = driver.build_manifest(ROOT, ["cipher", "psion"])
    for required in (
        "common/guiscripts/GemRBModCore.py",
        "common/runtime-api.txt",
        "cipher/guiscripts/Cipher.py",
        "cipher/guiscripts/CipherSubclass.py",
        "cipher/runtime-api.txt",
        "psion/guiscripts/Psionics.py",
        "psion/guiscripts/Psicrystal.py",
        "psion/guiscripts/PsionAI.py",
        "psion/runtime-api.txt",
    ):
        assert required in manifest["files"]

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        payload = root / "payload.txt"
        payload.write_text("stable\n", encoding="utf-8")
        (root / driver.MANIFEST).write_text(
            json.dumps({"schema": 1, "modules": [], "files": {"payload.txt": driver.sha256(payload)}}),
            encoding="utf-8",
        )
        driver.verify_manifest(root)
        payload.write_text("changed\n", encoding="utf-8")
        try:
            driver.verify_manifest(root)
        except SystemExit as error:
            assert "mismatched payload.txt" in str(error)
        else:
            raise AssertionError("manifest mismatch was accepted")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "common").mkdir()
        (root / "cipher").mkdir()
        (root / "psion").mkdir()
        (root / "common" / driver.RUNTIME_API).write_text("core-v1\n", encoding="utf-8")
        (root / "cipher" / driver.RUNTIME_API).write_text("core-v1\n", encoding="utf-8")
        (root / "psion" / driver.RUNTIME_API).write_text("core-v2\n", encoding="utf-8")
        try:
            driver.verify_runtime_api(root, ["cipher", "psion"])
        except SystemExit as error:
            assert "Shared-runtime revision mismatch before mutation" in str(error)
            assert "psion=core-v2, common=core-v1" in str(error)
        else:
            raise AssertionError("mixed shared-runtime revisions were accepted")

    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "classes.zip"
        driver.package(argparse.Namespace(modules=["cipher", "psion"], output=output))
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist())
            assert "gemrb-mods/gemrb-mods-release.json" in names
            assert "gemrb-mods/common/guiscripts/GemRBModCore.py" in names
            assert "gemrb-mods/common/runtime-api.txt" in names
            assert "gemrb-mods/cipher/guiscripts/CipherSubclass.py" in names
            assert "gemrb-mods/cipher/runtime-api.txt" in names
            assert "gemrb-mods/psion/guiscripts/Psicrystal.py" in names
            assert "gemrb-mods/psion/guiscripts/PsionAI.py" in names
            assert "gemrb-mods/psion/runtime-api.txt" in names

    print("Release packaging and documentation consistency validation passed")


if __name__ == "__main__":
    main()
