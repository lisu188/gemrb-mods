from pathlib import Path
import shutil
import sys
import tempfile

from weidu_smoke import build_fixture, find_row, run_weidu


COMMENTS = """# table listing bonuses:
# - who gets full wspatck.2da APR bonuses
# - fist APR progression
# - non-proficiency penalty
#
# kits can be listed as well; if not present, their class will be used
"""


def snapshot(override):
    return {p.name: p.read_bytes() for p in override.iterdir() if p.is_file()}


def assert_snapshot(override, expected, label):
    actual = snapshot(override)
    assert actual.keys() == expected.keys(), f"{label}: file set changed"
    for name, original in expected.items():
        assert actual[name] == original, f"{label}: {name} changed"


def write_commented_clswpbon(path):
    text = (
        "2DA V1.0\n"
        "0\n"
        "                        GETS_PROF_APR     UNARMED_DIVISOR   ZERO_SKILL_THAC0\n"
        "SORCERER                0                 0                 4\n"
        "MONK                    0                 5                 7\n"
        "\n"
        + COMMENTS
    )
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def exercise_comment_preservation(weidu):
    with tempfile.TemporaryDirectory(prefix="sorcerer-monk-clswpbon-comments-") as tmp:
        game = Path(tmp)
        build_fixture(game)
        override = game / "override"
        table = override / "clswpbon.2da"
        write_commented_clswpbon(table)
        originals = snapshot(override)

        run_weidu(weidu, game, "--force-install-list", "0")
        installed = table.read_text(encoding="utf-8")
        assert COMMENTS in installed, "CLSWPBON documentation comments were removed on install"
        assert find_row(table, "SORCERER_MONK")[1:] == ["0", "5", "7"]

        run_weidu(weidu, game, "--force-install-list", "0")
        reinstalled = table.read_text(encoding="utf-8")
        assert COMMENTS in reinstalled, "CLSWPBON documentation comments were removed on reinstall"
        assert reinstalled.count("# table listing bonuses:") == 1
        assert find_row(table, "SORCERER_MONK")[1:] == ["0", "5", "7"]

        run_weidu(weidu, game, "--force-uninstall", "0")
        assert_snapshot(override, originals, "commented CLSWPBON uninstall")
        print("commented GemRB CLSWPBON is preserved: OK", flush=True)


def main():
    weidu = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "weidu")
    if not weidu:
        raise SystemExit("WeiDU executable not found")
    exercise_comment_preservation(weidu)


if __name__ == "__main__":
    main()
