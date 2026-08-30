#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "common/tools"
BASE_TEST = ROOT / "common/tests/validate.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    installer = load("dependency_installer", TOOLS / "install_guiscripts.py")
    fixtures = load("dependency_fixtures", BASE_TEST)
    originals = fixtures.fixture_texts()

    with tempfile.TemporaryDirectory() as folder_name, tempfile.TemporaryDirectory() as source_name:
        folder = Path(folder_name)
        source = Path(source_name)
        fixtures.write_fixture(folder, originals)
        runtime = source / "Psionics.py"
        dependency_a = source / "Psicrystal.py"
        dependency_b = source / "PsionAI.py"
        runtime.write_text("runtime\n", encoding="utf-8")
        dependency_a.write_text("crystal\n", encoding="utf-8")
        dependency_b.write_text("ai\n", encoding="utf-8")

        installer.install_handler(folder, "Psionics", runtime, (dependency_a, dependency_b))
        marker = folder / ".gemrbmodcore.psionics.active"
        text = marker.read_text(encoding="utf-8")
        assert "dependency=Psicrystal.py" in text
        assert "dependency=PsionAI.py" in text
        assert (folder / "Psicrystal.py").read_text(encoding="utf-8") == "crystal\n"
        assert (folder / "PsionAI.py").read_text(encoding="utf-8") == "ai\n"

        installer.uninstall_handler(folder, "Psionics")
        assert not (folder / "Psicrystal.py").exists()
        assert not (folder / "PsionAI.py").exists()
        assert not marker.exists()
        for name, text in originals.items():
            assert (folder / name).read_text(encoding="utf-8") == text

    print("Shared GUI runtime dependency lifecycle validation passed")


if __name__ == "__main__":
    main()
