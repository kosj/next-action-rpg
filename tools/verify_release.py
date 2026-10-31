"""Verify downloaded release ZIPs against their manifest and expected commit.

python tools/verify_release.py DOWNLOAD_DIRECTORY --commit FULL_SHA --version 0.1.4
This checks downloaded bytes and packaging, not Windows execution or art quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(folder, commit, version):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected the full reviewed 40-character commit SHA")
    manifest = json.loads((folder / "manifest.json").read_text())
    engine = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]
    if (manifest.get("version"), manifest.get("godot"), manifest.get("commit")) != (version, engine, commit[:8]):
        raise ValueError("Release version, engine or source commit differs from the reviewed build")
    artifacts = manifest["artifacts"]
    expected = {"runefall-web.zip", "runefall-windows.zip"}
    if len(artifacts) != 2 or {item["file"] for item in artifacts} != expected:
        raise ValueError("Expected exactly the Web and Windows distributions")
    results = []
    for item in artifacts:
        path = folder / item["file"]
        if path.stat().st_size != item["bytes"]:
            raise ValueError("Release byte count differs: " + path.name)
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        if checksum.hexdigest() != item["sha256"]:
            raise ValueError("Release SHA-256 differs: " + path.name)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Corrupt ZIP entry: " + path.name)
            files = set(archive.namelist())
            notices = {"THIRD_PARTY_NOTICES.md", "FONT_LICENSE.txt", "GODOT_LICENSE.txt", "GODOT_THIRD_PARTY.txt"}
            if not notices <= files:
                raise ValueError("Distribution is missing dependency notices: " + path.name)
            required = {"index.html", "index.pck", "index.wasm"} if "web" in path.name else {"Runefall.exe", "Runefall.pck"}
            if not required <= files:
                raise ValueError("Distribution is missing playable files: " + path.name)
            raw_bytes = sum(entry.file_size for entry in archive.infolist())
            if "web" in path.name and raw_bytes > 150_000_000:
                raise ValueError("Downloaded Web distribution exceeds the project size budget")
        results.append({**item, "sha256_verified": True, "zip_crc_ok": True,
                        "licenses_present": True, "playable_files_present": True,
                        "uncompressed_bytes": raw_bytes})
    return {"version": version, "godot": engine, "expected_main_sha": commit,
            "manifest_commit": manifest["commit"], "artifacts": results,
            "status": "verified", "scope": "Downloaded bytes and packaging; no hardware or art approval"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    report = verify(args.directory, args.commit, args.version)
    (args.directory / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
