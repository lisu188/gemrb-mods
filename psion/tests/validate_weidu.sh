#!/usr/bin/env bash
set -euo pipefail

# Parse the complete installer and every included TPA without requiring a game
# installation. This catches real WeiDU grammar errors that Python source-text
# checks cannot detect.
command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

output="$(weidu --list-components psion/setup-psion.tp2 2>&1)"
printf '%s\n' "$output"

# The installer currently exposes exactly one component. Verify that WeiDU not
# only exited successfully, but also discovered the intended component.
grep -Fq '0' <<<"$output"
grep -Fqi 'Psion' <<<"$output"
