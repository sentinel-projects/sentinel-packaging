#!/usr/bin/env bash
# Prepare an SRPM only. No COPR submission or network publication is implemented.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ $# -eq 1 ]] || { echo "usage: build_srpm.sh NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
[[ ! -e "$1" ]] || { echo "Output exists; refusing overwrite" >&2; exit 2; }
command -v rpmbuild >/dev/null || { echo "rpmbuild is required on the Fedora build host" >&2; exit 2; }
mkdir -p "$1"
out=$(cd "$1" && pwd)
python3 "$root/tools/packaging.py" render --out "$out/rendered"
mkdir -p "$out/SOURCES" "$out/SPECS" "$out/SRPMS" "$out/BUILD" "$out/RPMS"
python3 "$root/tools/packaging.py" fetch-source --out "$out/SOURCES"
cp "$out/rendered/rpm/sentinel-desktop.spec" "$out/SPECS/"
rpmbuild -bs --define "_topdir $out" "$out/SPECS/sentinel-desktop.spec"
