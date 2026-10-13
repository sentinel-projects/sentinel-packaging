# Sentinel distribution recipes

Private local preparation for sentinel-projects/sentinel-packaging. No public repository, commit or distribution release has been created.

The application remains the C++/Qt cross-platform monorepo at https://github.com/sentinel-projects/sentinel. This repository owns only distribution recipes, source-input locking and local packaging helpers. It contains no application source, native integration, CMake/CPack, runtime resource, SDK, original history or release binary.

## Contract

`upstream.lock.json` is authoritative: application 1.0.0-rc.8, numeric package version 1.0.0, immutable sanitized commit, HTTPS archive URL and measured SHA-256. A changed checksum is an error requiring owner review, not an automatic update. Packaging revisions are independent of application version; RPM 0.8 precedes stable release 1. Application ID dev.sentinel.Sentinel, Winget ID Sopwit.Sentinel, executable names, organization-backed user-data paths and macOS bundle Sentinel.app are preserved.

Install scoped validators with `python3 -m pip install -r requirements-dev.txt`. Run `python3 tools/packaging.py validate`, `python3 -m unittest discover -s tests -v`, and `shellcheck tools/*.sh`. Render source recipes with `python3 tools/packaging.py render --out NEW_DIRECTORY`; output must not exist. Helpers work from any current directory and never clone/archive the packaging checkout as application source.

`tools/build_srpm.sh NEW_DIRECTORY` fetches and verifies the pinned application source and builds an SRPM on Fedora. It does not submit to COPR. Use a separately authorized COPR publication procedure only after native RPM build/checks and licensing gates pass. `tools/build_flatpak.sh NEW_DIRECTORY` builds to a new private output without install, run or remote registration. Snap consumes the same archive with source-checksum and the core24 KDE neon 6 extension; native SDK/module, daemon and sandbox acceptance remain required. Do not use Ubuntu core24's stock Qt 6.4 packages against upstream's Qt 6.5 minimum.

KDE Flatpak track 6.11 matches the application's CI Qt line; its source branch exists in KDE's official runtime mirror. Availability/EOL status and exact installed SDK revisions still require Linux validation. Snap extension adds normal KDE desktop/network/graphics interfaces; expanded permissions and SDK versions require native review before store publication. Existing broader home/sandbox permissions are not a confidentiality clearance.

## Binary metadata is deliberately blocked

All obsolete upstream binary assets were withdrawn. There are no verified DMG/EXE/MSI inputs. Cask/Winget files are templates outside an installable tap/community layout. `render --include-binaries` MUST reject absent checksummed artifact descriptors; it never substitutes no_check or zero hashes. Add individually verified immutable release URLs, SHA-256, version and upstream commit only after separately authorized builds/distribution review. Templates preserve identifiers, fix repository/license URLs, set macOS minimum Ventura (13.0), and split Winget's two installers into three schema-compatible manifests. No compatibility claim is made for unavailable installers.

## Ownership and publication gates

EXTRACTION_MAP.json records paths/duplicate ownership. Main keeps its CPack recipe and compiled/installed metadata, services, bundle inputs, resources, tests, SDK and application CI. No active source files are removed by staging. GPL license/attribution is preserved; this does not resolve source/artwork rights, Qt corresponding-source, opaque binary or dependency-security obligations.

CI is packaging-scoped and read-only: validation plus a manual Fedora source-build job, no uploads, COPR submission, release creation or credentials. Native Flatpak/Snap, macOS Cask DMG and Windows Winget validation remain distinct required checks. Publish this source-only recipe repository only under explicit owner authorization; binary/store/COPR publication is separate.
