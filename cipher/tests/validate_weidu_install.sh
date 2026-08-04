#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || exit 127
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gemrb_root="${1:?usage: validate_weidu_install.sh GEMRB_ROOT [LAYOUT]}"
layout="${2:-normalized}"
case "$layout" in normalized|native|legacy) ;; *) exit 2 ;; esac

game="$RUNNER_TEMP/cipher-weidu-game-$layout"
python3 "$repo_root/psion/tests/make_weidu_fixture.py" --gemrb-root "$gemrb_root" --output "$game" --layout "$layout"
cp -R "$repo_root/common" "$game/common"
cp -R "$repo_root/cipher" "$game/cipher"
python3 "$repo_root/cipher/tests/seed_weidu_fixture.py" "$game"

hit_baseline="$(sha256sum "$game/override/CIFHIT.ITM" | cut -d' ' -f1)"
bow_baseline="$(sha256sum "$game/override/CIFBOW.ITM" | cut -d' ' -f1)"
mweap_baseline="$(sha256sum "$game/override/CIFMWEAP.ITM" | cut -d' ' -f1)"
magic_baseline="$(sha256sum "$game/override/CIFMAGIC.ITM" | cut -d' ' -f1)"

install() {
  (cd "$game" && weidu cipher/setup-cipher.tp2 --use-lang en_US --force-install 0 --no-exit-pause)
}

uninstall() {
  (cd "$game" && weidu cipher/setup-cipher.tp2 --use-lang en_US --force-uninstall 0 --no-exit-pause)
}

verify() {
  python3 "$repo_root/cipher/tests/verify_weidu_install.py" "$game" "$layout"
}

install
verify
uninstall
test "$(sha256sum "$game/override/CIFHIT.ITM" | cut -d' ' -f1)" = "$hit_baseline"
test "$(sha256sum "$game/override/CIFBOW.ITM" | cut -d' ' -f1)" = "$bow_baseline"
test "$(sha256sum "$game/override/CIFMWEAP.ITM" | cut -d' ' -f1)" = "$mweap_baseline"
test "$(sha256sum "$game/override/CIFMAGIC.ITM" | cut -d' ' -f1)" = "$magic_baseline"
! grep -q 'CIPHER' "$game/override/class.ids"
install
verify
