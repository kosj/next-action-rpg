"""Validate, package and verify this standalone knowledge kit (stdlib only)."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "game-production-kit"
SKILLS = {"evidence-led-project-memory", "godot-web-production", "generated-3d-game-art"}
LINK = re.compile(r"\]\(([^)]+)\)")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_files(root):
    result = []
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.relative_to(root).parts:
            continue
        if path.is_symlink():
            raise ValueError("Package source must not contain symlinks: " + str(path))
        if not path.is_file() or path == root / "MANIFEST.json":
            continue
        relative = path.relative_to(root)
        allowed_root = str(relative) in {"README.md", "HANDBOOK.md", "provenance.json"}
        allowed_tree = relative.parts[0] in {"skills", "scripts"} and path.suffix in {".md", ".json", ".py"}
        if not (allowed_root or allowed_tree):
            raise ValueError("Unexpected package file: " + str(relative))
        result.append(path)
    return result


def validate(root):
    files = source_files(root)
    for name in ["README.md", "HANDBOOK.md", "provenance.json", "scripts/package.py"]:
        if root / name not in files:
            raise ValueError("Missing package file: " + name)
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    origin = provenance["source_catalog"]
    entries = origin["entries"]
    if len(entries) != origin["entry_count"] or len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Source entry count or IDs differ")
    for entry in entries:
        if entry["source_status"] not in {"verified", "pending", "superseded"}:
            raise ValueError("Invalid source status")
        date.fromisoformat(entry["source_checked_on"])
        if not entry["evidence_urls"]:
            raise ValueError("Missing source evidence")
        for url in entry["evidence_urls"]:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Source evidence must use permanent HTTPS URLs")
    skills = {p.parent.name for p in files if p.name == "SKILL.md"}
    if skills != SKILLS:
        raise ValueError("Expected the three documented portable skills")
    for path in files:
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(content)
            if "references" in path.parts and isinstance(data, dict) and "status" in data and data["status"] != "pending":
                raise ValueError("Distribution templates must start pending: " + str(path))
        if path.name == "SKILL.md":
            match = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
            if not match:
                raise ValueError("Missing skill frontmatter: " + str(path))
            header = match.group(1)
            name = re.search(r"^name:\s*([^\n]+)$", header, re.M)
            description = re.search(r"^description:\s*(.*?)(?=\n\S|\Z)", header, re.M | re.S)
            if not name or name.group(1).strip() != path.parent.name or not description or not description.group(1).strip(">| \n"):
                raise ValueError("Invalid skill name/description: " + str(path))
        if path.suffix != ".md":
            continue
        relative = path.relative_to(root)
        boundary = root / "skills" / relative.parts[1] if relative.parts[0] == "skills" else root
        for link in LINK.findall(content):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError("Invalid external link: " + link)
                continue
            if not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(boundary.resolve()) or not target.is_file():
                raise ValueError("Missing/outside portable local link: " + str(relative) + " -> " + link)
    return files, provenance


def package(root, output):
    files, provenance = validate(root)
    output = output.resolve()
    if output.is_relative_to(root.resolve()):
        raise ValueError("Write the ZIP outside its source kit")
    payloads = {p.relative_to(root).as_posix(): p.read_bytes() for p in files}
    manifest = {"schema_version": 1, "bundle": NAME, "version": provenance["bundle_version"],
                "scope": "Portable methods and source observations; target projects require revalidation",
                "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in payloads.items()}}
    payloads["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(NAME + "/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    verify(output)
    return {"file": str(output), "bytes": output.stat().st_size, "sha256": sha(output.read_bytes()),
            "skills": len(SKILLS), "source_entries": provenance["source_catalog"]["entry_count"], "status": "verified_package"}


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or archive.testzip() is not None:
            raise ValueError("Duplicate/corrupt archive entries")
        for info in archive.infolist():
            parts = PurePosixPath(info.filename).parts
            if not parts or parts[0] != NAME or ".." in parts or PurePosixPath(info.filename).is_absolute() or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Invalid archive path")
        manifest = json.loads(archive.read(NAME + "/MANIFEST.json"))
        if manifest["schema_version"] != 1 or manifest["bundle"] != NAME:
            raise ValueError("Unexpected manifest")
        expected = {NAME + "/" + name for name in manifest["files"]} | {NAME + "/MANIFEST.json"}
        if set(names) != expected:
            raise ValueError("Manifest/file list differs")
        for name, record in manifest["files"].items():
            data = archive.read(NAME + "/" + name)
            if len(data) != record["bytes"] or sha(data) != record["sha256"]:
                raise ValueError("Manifest bytes/hash differ: " + name)
    return {"file": str(path), "files": len(names), "status": "verified_integrity"}


def verify_source(root, path):
    files, provenance = validate(root)
    verify(path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read(NAME + "/MANIFEST.json"))
    expected = {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in files}
    if manifest["version"] != provenance["bundle_version"] or manifest["files"] != expected:
        raise ValueError("Distributed ZIP differs from current source files")
    return {"file": str(path), "files": len(files), "status": "matches_current_source"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    mode.add_argument("--verify-source", type=Path)
    args = parser.parse_args()
    if args.check:
        files, provenance = validate(ROOT)
        result = {"status": "valid_source", "skills": len(SKILLS), "source_entries": provenance["source_catalog"]["entry_count"], "files": len(files)}
    elif args.output:
        result = package(ROOT, args.output)
    elif args.verify:
        result = verify(args.verify)
    else:
        result = verify_source(ROOT, args.verify_source)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
