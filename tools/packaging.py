#!/usr/bin/env python3
"""Render independent recipes from one explicit upstream lock. Never publish."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tempfile
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"@[A-Z_0-9]+@")

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def validate(lock):
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    commit = lock["commit"]
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "Invalid upstream commit")
    require(lock["schema_version"] == 1, "Unsupported lock schema")
    require(lock["upstream_repository"] == "https://github.com/sentinel-projects/sentinel", "Unexpected repository")
    version = lock["application_version"]
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?", version), "Invalid version")
    require(lock["numeric_version"] == version.split("-")[0], "Numeric version mismatch")
    require(lock["app_id"] == "dev.sentinel.Sentinel" and lock["package_id"] == "Sopwit.Sentinel", "Identity changed")
    source = lock["source"]
    require(source["url"] == "https://codeload.github.com/sentinel-projects/sentinel/tar.gz/" + commit, "Source must pin exact commit")
    require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) and source["sha256"] != "0" * 64, "Invalid source checksum")
    require(source["filename"] == "sentinel-" + commit + ".tar.gz", "Unsafe filename")
    require(source["archive_root"] == "sentinel-" + commit, "Archive root mismatch")
    require(isinstance(source["bytes"], int) and source["bytes"] > 0, "Missing archive size")
    require(re.fullmatch(r"[0-9]+\.[0-9]+", lock["flatpak_runtime"]), "Invalid runtime")
    require(lock["snap_base"] == "core24" and lock["snap_extension"] == "kde-neon-6", "Unexpected Snap contract")
    return lock

def values(lock, binaries=False):
    validate(lock)
    source = lock["source"]
    result = dict(APP_VERSION=lock["application_version"], NUMERIC_VERSION=lock["numeric_version"],
                  SOURCE_URL=source["url"], SOURCE_SHA256=source["sha256"], SOURCE_FILENAME=source["filename"],
                  ARCHIVE_ROOT=source["archive_root"], FLATPAK_RUNTIME=lock["flatpak_runtime"],
                  RPM_RELEASE=("0." + lock["application_version"].split("-rc.")[1] if "-rc." in lock["application_version"] else "1"))
    if binaries:
        for kind in ("dmg", "exe", "msi"):
            artifact = lock["binary_artifacts"].get(kind)
            if not artifact:
                raise ValueError("Missing verified binary artifact: " + kind)
            if artifact.get("version") != lock["application_version"] or artifact.get("upstream_commit") != lock["commit"]:
                raise ValueError("Binary version/commit mismatch")
            prefix = "https://github.com/sentinel-projects/sentinel/releases/download/"
            url = artifact["url"]
            if not re.fullmatch(re.escape(prefix) + r"v?[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?/[A-Za-z0-9_.+-]+", url):
                raise ValueError("Unsafe or mutable binary URL")
            if url[len(prefix):].split("/")[0].removeprefix("v") != lock["application_version"]:
                raise ValueError("Binary release tag mismatch")
            sha = artifact["sha256"]
            if not re.fullmatch(r"[0-9a-fA-F]{64}", sha) or sha == "0" * 64:
                raise ValueError("Invalid binary checksum")
            result[kind.upper() + "_URL"] = url
            result[kind.upper() + "_SHA256"] = sha
    return result

def recipes(lock, binaries=False):
    replacements = values(lock, binaries)
    outputs = {}
    directories = ["rpm", "flatpak", "snap"] + (["homebrew", "winget"] if binaries else [])
    for directory in directories:
        for source in sorted((ROOT / directory).rglob("*.in")):
            content = source.read_text()
            content = TOKEN.sub(lambda match: replacements[match.group()[1:-1]], content)
            if TOKEN.search(content):
                raise ValueError("Unresolved token")
            target = source.relative_to(ROOT).with_suffix("")
            if target.suffix == ".json":
                json.loads(content)
            elif target.suffix == ".yaml":
                yaml.safe_load(content)
            outputs[target] = content
    if len(outputs) != (7 if binaries else 3):
        raise ValueError("Recipe inventory mismatch")
    flatpak = json.loads(outputs[Path("flatpak/dev.sentinel.Sentinel.json")])
    if flatpak["app-id"] != lock["app_id"]:
        raise ValueError("Flatpak identity mismatch")
    snap = yaml.safe_load(outputs[Path("snap/snapcraft.yaml")])
    if snap["version"] != lock["application_version"] or snap["base"] != lock["snap_base"]:
        raise ValueError("Snap contract mismatch")
    return outputs

def render(lock, out, binaries=False):
    outputs = recipes(lock, binaries)  # All checks before the first write.
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for target, content in outputs.items():
        destination = out / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)

def verify_source(lock, archive):
    validate(lock)
    archive = Path(archive)
    if archive.stat().st_size != lock["source"]["bytes"] or digest(archive) != lock["source"]["sha256"]:
        raise ValueError("Source archive size/checksum mismatch")
    root = lock["source"]["archive_root"]
    with tarfile.open(archive, "r:gz") as tar:
        # Inspect without extracting anything or following archived links.
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if not parts or parts[0] != root or ".." in parts or Path(member.name).is_absolute():
                raise ValueError("Unsafe source archive path")
        cmake = tar.extractfile(root + "/CMakeLists.txt").read().decode()
        if 'SENTINEL_APP_VERSION "' + lock["application_version"] + '"' not in cmake:
            raise ValueError("Source version mismatch")
        for path in ("LICENSE", "cmake/SentinelCPack.cmake"):
            member = tar.getmember(root + "/" + path)
            if not member.isfile():
                raise ValueError("Missing required source file")

def fetch_source(lock, out):
    validate(lock)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / lock["source"]["filename"]
    if target.exists():
        raise FileExistsError("Refusing to replace existing source")
    with tempfile.NamedTemporaryFile(dir=out, suffix=".unverified", delete=False) as stream:
        pending = Path(stream.name)
        try:
            with urllib.request.urlopen(lock["source"]["url"], timeout=120) as response:
                while data := response.read(1024 * 1024):
                    stream.write(data)
            stream.flush()
            verify_source(lock, pending)
            # Exclusive creation protects an output concurrently created by another process.
            with target.open("xb") as destination, pending.open("rb") as source:
                while data := source.read(1024 * 1024):
                    destination.write(data)
        finally:
            pending.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "upstream.lock.json")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--source-archive", type=Path)
    output = sub.add_parser("render")
    output.add_argument("--out", type=Path, required=True)
    output.add_argument("--include-binaries", action="store_true")
    fetch = sub.add_parser("fetch-source")
    fetch.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    try:
        validate(lock)
        if args.command == "validate":
            recipes(lock)
            if args.source_archive:
                verify_source(lock, args.source_archive)
        elif args.command == "render":
            render(lock, args.out, args.include_binaries)
        else:
            fetch_source(lock, args.out)
    except (ValueError, KeyError, OSError, tarfile.TarError) as error:
        parser.exit(2, str(error) + "\n")
    print(args.command + ": PASS")

if __name__ == "__main__":
    main()
