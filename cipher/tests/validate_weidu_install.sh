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

baseline() { sha256sum "$1" | cut -d' ' -f1; }
hit_baseline="$(baseline "$game/override/CIFHIT.ITM")"
bow_baseline="$(baseline "$game/override/CIFBOW.ITM")"
mweap_baseline="$(baseline "$game/override/CIFMWEAP.ITM")"
magic_baseline="$(baseline "$game/override/CIFMAGIC.ITM")"
leather_baseline="$(baseline "$game/override/CIFLEATH.ITM")"
chain_baseline="$(baseline "$game/override/CIFCHAIN.ITM")"
robe_baseline="$(baseline "$game/override/CIFROBE.ITM")"
shield_baseline="$(baseline "$game/override/CIFSHLD.ITM")"

install() {
  (cd "$game" && weidu cipher/setup-cipher.tp2 --use-lang en_US --force-install 0 --no-exit-pause)
}

uninstall() {
  (cd "$game" && weidu cipher/setup-cipher.tp2 --use-lang en_US --force-uninstall 0 --no-exit-pause)
}

verify() {
  python3 "$repo_root/cipher/tests/verify_weidu_install.py" "$game" "$layout"
  python3 "$repo_root/cipher/tests/verify_item_usability.py" "$game"
  python3 "$repo_root/cipher/tests/verify_power_learning.py" "$game"
  python3 "$repo_root/cipher/tests/verify_high_tier_weidu.py" "$game"
}

install
verify
uninstall
python3 "$repo_root/cipher/tests/verify_power_learning.py" "$game" --uninstalled
test ! -e "$game/override/CI5DBST.SPL"
test ! -e "$game/override/CI5DBST.spl"
test ! -e "$game/override/CI9SDEX.SPL"
test ! -e "$game/override/CI9SDEX.spl"
test "$(baseline "$game/override/CIFHIT.ITM")" = "$hit_baseline"
test "$(baseline "$game/override/CIFBOW.ITM")" = "$bow_baseline"
test "$(baseline "$game/override/CIFMWEAP.ITM")" = "$mweap_baseline"
test "$(baseline "$game/override/CIFMAGIC.ITM")" = "$magic_baseline"
test "$(baseline "$game/override/CIFLEATH.ITM")" = "$leather_baseline"
test "$(baseline "$game/override/CIFCHAIN.ITM")" = "$chain_baseline"
test "$(baseline "$game/override/CIFROBE.ITM")" = "$robe_baseline"
test "$(baseline "$game/override/CIFSHLD.ITM")" = "$shield_baseline"
! grep -q 'CIPHER' "$game/override/class.ids"
install
verify
