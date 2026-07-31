#!/usr/bin/env bash
set -euo pipefail

# Parse the complete installer and every included TPA without requiring a game
# installation. This catches real WeiDU grammar errors that Python source-text
# checks cannot detect.
command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

# --list-components takes both the TP2 path and a zero-based language index.
# --nogame prevents WeiDU from looking for CHITIN.KEY or DIALOG.TLK during this
# parser-only smoke test.
output="$(weidu --nogame --list-components psion/setup-psion.tp2 0 2>&1)"
printf '%s\n' "$output"

# The installer currently exposes exactly one component. Verify that WeiDU not
# only exited successfully, but also discovered the intended component.
grep -Eq '(^|[^0-9])0([^0-9]|$)' <<<"$output"
grep -Fqi 'Psion' <<<"$output"
