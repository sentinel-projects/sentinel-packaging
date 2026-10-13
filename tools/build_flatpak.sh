#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ $# -eq 1 ]] || { echo "usage: build_flatpak.sh NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
[[ ! -e "$1" ]] || { echo "Output exists; refusing overwrite" >&2; exit 2; }
command -v flatpak-builder >/dev/null || { echo "flatpak-builder is required on a Linux host" >&2; exit 2; }
mkdir -p "$1"
out=$(cd "$1" && pwd)
python3 "$root/tools/packaging.py" render --out "$out/rendered"
flatpak-builder --repo="$out/repository" "$out/build" "$out/rendered/flatpak/dev.sentinel.Sentinel.json"
# No install, run, remote-add, unsigned repository registration or publication.
