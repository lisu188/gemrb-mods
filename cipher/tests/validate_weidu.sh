#!/usr/bin/env bash
set -euo pipefail

command -v weidu >/dev/null 2>&1 || {
  echo "WeiDU executable not found in PATH" >&2
  exit 127
}

output="$(weidu --nogame --list-components cipher/setup-cipher.tp2 0 2>&1)"
printf '%s\n' "$output"
grep -Eq '(^|[^0-9])0([^0-9]|$)' <<<"$output"
grep -Fqi 'Cipher' <<<"$output"

parse_dir="$(mktemp -d)"
trap 'rm -rf "$parse_dir"' EXIT
status=0

while IFS= read -r file; do
  target="$parse_dir/$(basename "$file").parsed"
  echo "Parsing $file"
  if ! parse_output="$(weidu --nogame --forceify "$file" --out "$target" 2>&1)"; then
    printf '%s\n' "$parse_output" >&2
    status=1
    continue
  fi
  printf '%s\n' "$parse_output"
  if [[ ! -s "$target" ]]; then
    echo "WeiDU produced no parsed output for $file" >&2
    status=1
  fi
done < <(find cipher/lib -maxdepth 1 -type f -name '*.tpa' -print | sort)

exit "$status"
