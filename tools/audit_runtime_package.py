"""Read-only post-export Godot4.7.2 PCK/font/texture and raw-Web budget audit.

Usage: python tools/audit_runtime_package.py build/web --asset-prefix
assets/models/production/EXACT_NPC_STEM --report NEW.json

Uses the prior private PCK offset procedure, bounded for standalone unencrypted
Godot PCK v4 only. No engine, extraction, resource mutation or image decoding.
Packed .import remaps prove presence of the named imported files; caller-given
source prefixes group imported NPC files, not a recursively decoded scene
dependency graph. GST2 header mip counts/chunk extents are package information,
not GPU allocations, texture quality or target-device/rendering approval.

Layout references (pinned engine, read 2026-11-02):
https://github.com/godotengine/godot/blob/4.7.2-stable/core/io/file_access_pack.cpp
https://github.com/godotengine/godot/blob/4.7.2-stable/core/io/file_access_pack.h
https://github.com/godotengine/godot/blob/4.7.2-stable/scene/resources/compressed_texture.cpp
https://github.com/godotengine/godot/blob/4.7.2-stable/scene/resources/compressed_texture.h
"""

from __future__ import annotations

import argparse
from collections import Counter
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys

RAW_WEB_CAP = 150_000_000
ORIGINAL_FONT = "NotoSansKR.ttf"
STATIC_FONT = "runefall_kr430.ttf"


def _read(stream, length):
    data = stream.read(length)
    if len(data) != length:
        raise ValueError("Truncated PCK directory/header")
    return data


def canonical(path):
    path = path.removeprefix("res://")
    if not path or "\0" in path or "\\" in path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Unsupported/unsafe PCK resource path")
    if PurePosixPath(path).as_posix() != path:
        raise ValueError("Noncanonical PCK resource path")
    return path


class Pck:
    def __init__(self, path):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        self.initial_stat = self.path.stat()
        self.entries = {}
        with self.path.open("rb") as stream:
            header = _read(stream, 40)
            if header[:4] != b"GDPC":
                raise ValueError("Expected standalone PCK magic at offset0")
            version, major, minor, patch, flags, base, directory = struct.unpack_from("<IIIIIQQ", header, 4)
            if version != 4 or flags & ~2:
                raise ValueError("Only standalone nonencrypted/nonsparse PCK v4 is supported")
            if not 40 <= base <= directory <= self.size - 4:
                raise ValueError("PCK file base/directory is out of bounds")
            self.header = {"format": version, "engine": [major, minor, patch], "flags": flags,
                           "file_base": base, "directory_offset": directory}
            stream.seek(directory)
            count = struct.unpack("<I", _read(stream, 4))[0]
            if count > (self.size - directory - 4) // 40:
                raise ValueError("Impossible PCK directory file count")
            for _ in range(count):
                length = struct.unpack("<I", _read(stream, 4))[0]
                if not length or length > self.size - stream.tell() - 36:
                    raise ValueError("PCK path length exceeds directory bounds")
                name = canonical(_read(stream, length).rstrip(b"\0").decode("utf-8"))
                offset, size, md5, entry_flags = struct.unpack("<QQ16sI", _read(stream, 36))
                absolute = base + offset
                if entry_flags:
                    raise ValueError("Encrypted/removal/delta PCK entries are unsupported")
                if absolute < base or absolute > directory or size > directory - absolute:
                    raise ValueError("PCK file payload exceeds data section bounds")
                if name in self.entries:
                    raise ValueError("Duplicate canonical PCK resource path: " + name)
                self.entries[name] = {"path": name, "offset": absolute, "bytes": size, "md5": md5.hex()}

    def payload(self, name):
        entry = self.entries[name]
        with self.path.open("rb") as stream:
            stream.seek(entry["offset"])
            return _read(stream, entry["bytes"])

    def verify_md5(self):
        with self.path.open("rb") as stream:
            for name, entry in self.entries.items():
                stream.seek(entry["offset"])
                remaining = entry["bytes"]
                digest = hashlib.md5()
                while remaining:
                    data = _read(stream, min(1024 * 1024, remaining))
                    digest.update(data)
                    remaining -= len(data)
                if digest.hexdigest() != entry["md5"]:
                    raise ValueError("PCK directory MD5 mismatch: " + name)

    def unchanged(self):
        current = self.path.stat()
        if (current.st_size, current.st_mtime_ns, current.st_ino) != (
                self.initial_stat.st_size, self.initial_stat.st_mtime_ns, self.initial_stat.st_ino):
            raise ValueError("PCK changed while the audit was running")


def inspect_ctex(data):
    if len(data) < 52 or data[:4] != b"GST2":
        raise ValueError("Expected bounded GST2 texture header")
    version, width, height, flags = struct.unpack_from("<IIII", data, 4)
    encoding, image_width, image_height, mips, image_format = struct.unpack_from("<IHHII", data, 36)
    if version > 1 or not image_width or not image_height or encoding not in (0, 1, 2, 3):
        raise ValueError("Unsupported GST2 version/encoding/dimensions")
    maximum_mips = max(image_width, image_height).bit_length() - 1
    if mips > maximum_mips:
        raise ValueError("GST2 mip count exceeds image dimensions")
    result = {"version": version, "display_size": [width, height],
              "image_size": [image_width, image_height], "format_flags": flags,
              "data_encoding": ["raw_image", "png", "webp", "basis_universal"][encoding],
              "image_format_enum": image_format, "additional_mipmap_count": mips,
              "total_mip_levels": mips + 1, "payload_chunks": []}
    cursor = 52
    if encoding in (1, 2):
        for level in range(mips + 1):
            if cursor + 4 > len(data):
                raise ValueError("Truncated GST2 mip length")
            length = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            if not length or length > len(data) - cursor:
                raise ValueError("GST2 mip payload exceeds file bounds")
            if encoding == 1 and data[cursor:cursor + 8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("GST2 PNG mip signature mismatch")
            if encoding == 2 and (length < 12 or data[cursor:cursor + 4] != b"RIFF"
                                  or data[cursor + 8:cursor + 12] != b"WEBP"):
                raise ValueError("GST2 WebP mip signature mismatch")
            result["payload_chunks"].append({"level": level, "bytes": length,
                "header_implied_size": [max(1, image_width >> level), max(1, image_height >> level)]})
            cursor += length
        if cursor != len(data):
            raise ValueError("Unexpected trailing GST2 bytes")
        result["all_encoded_mip_chunk_extents_checked"] = True
    else:
        result["all_encoded_mip_chunk_extents_checked"] = False
        result["scope_note"] = "Raw/Basis payload not decoded; mip count comes from the GST2 image header"
    return result


def _metadata(pck, name):
    entry = pck.entries[name]
    result = {key: entry[key] for key in ("path", "bytes", "md5")}
    if name.endswith(".ctex"):
        result["texture"] = inspect_ctex(pck.payload(name))
    return result


def _import_destinations(pck, name):
    text = pck.payload(name).decode("utf-8")
    remap = text.split("[remap]", 1)[1].split("[", 1)[0] if "[remap]" in text else ""
    paths = sorted(set(re.findall(r'^path(?:\.[^=\s]+)?\s*=\s*"(res://[^"\n]+)"', remap, re.M)))
    if not paths:
        raise ValueError("No packed importer remap path: " + name)
    result = []
    for path in paths:
        destination = canonical(path)
        if destination not in pck.entries:
            raise ValueError("Packed import destination is missing: " + destination)
        result.append(_metadata(pck, destination))
    return result


def audit(web_directory, pck_path=None, asset_prefixes=()):
    web_directory = Path(web_directory)
    if not web_directory.is_dir():
        raise ValueError("A completed raw Web export directory is required")
    files = []
    for path in sorted(web_directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Raw Web tree must not contain symlinks")
        if path.is_file():
            files.append({"path": path.relative_to(web_directory).as_posix(), "bytes": path.stat().st_size})
    if not files:
        raise ValueError("Raw Web directory is empty")
    pck = Pck(pck_path or web_directory / "index.pck")
    pck.verify_md5()
    original = [name for name in pck.entries if fnmatch.fnmatchcase(name, f".godot/imported/{ORIGINAL_FONT}-*.fontdata")
                or name in (f"assets/fonts/{ORIGINAL_FONT}", f"assets/fonts/{ORIGINAL_FONT}.import")]
    static = [name for name in pck.entries if fnmatch.fnmatchcase(name, f".godot/imported/{STATIC_FONT}-*.fontdata")]
    static_remap = f"assets/fonts/{STATIC_FONT}.import"
    remapped_static = _import_destinations(pck, static_remap) if static_remap in pck.entries else []
    groups = []
    for prefix in asset_prefixes:
        prefix = canonical(prefix)
        imports = [name for name in pck.entries if name.startswith(prefix) and name.endswith(".import")]
        if not imports:
            raise ValueError("No packed import sidecars match requested asset prefix: " + prefix)
        records = [{"source_import": name, "imported_files": _import_destinations(pck, name)} for name in sorted(imports)]
        unique = {item["path"]: item for record in records for item in record["imported_files"]}
        groups.append({"source_prefix": prefix, "import_records": records,
                       "unique_imported_files": len(unique),
                       "unique_imported_bytes": sum(item["bytes"] for item in unique.values()),
                       "imported_scene_bytes": sum(item["bytes"] for item in unique.values() if item["path"].endswith(".scn")),
                       "imported_texture_bytes": sum(item["bytes"] for item in unique.values() if item["path"].endswith(".ctex")),
                       "association_scope": "Exact packed .import remaps for caller-selected source prefix; not a recursive SCN dependency closure"})
    counts, totals = Counter(), Counter()
    for name, item in pck.entries.items():
        extension = Path(name).suffix or "(none)"
        counts[extension] += 1
        totals[extension] += item["bytes"]
    raw_total = sum(item["bytes"] for item in files)
    checks = {"raw_web_within_unchanged_150M_cap": raw_total <= RAW_WEB_CAP,
              "original_variable_font_source_remap_and_fontdata_absent": not original,
              "static_fontdata_exactly_once": len(static) == 1,
              "static_font_import_remaps_to_that_single_fontdata": len(static) == 1 and
                  [item["path"] for item in remapped_static] == static,
              "all_directory_payload_md5_verified": True}
    with pck.path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        sha = digest.hexdigest()
    pck.unchanged()
    return {"schema": 1, "passed": all(checks.values()), "checks": checks,
            "raw_web": {"bytes": raw_total, "cap_bytes": RAW_WEB_CAP,
                        "remaining_bytes": RAW_WEB_CAP - raw_total, "files": files},
            "pck": {"path": str(pck.path), "bytes": pck.size, "sha256": sha,
                    "header": pck.header, "directory_files": len(pck.entries),
                    "by_extension": {key: {"count": counts[key], "bytes": totals[key]} for key in sorted(counts)}},
            "fonts": {"forbidden_original_entries": original,
                      "static_imported_files": [_metadata(pck, name) for name in static],
                      "static_import_remap": remapped_static}, "asset_groups": groups,
            "scope": "Bounded standalone PCKv4/GST2 header+chunk/presence audit. No engine, pixel decode, "
                     "visual/device approval, recursive compressed-SCN dependency analysis or GPU memory estimate.",
            "touch_font_scope": "The isolated raster experiment covers12/16/18/24/36px only; actualTouch14/10px needs separate real-game UI review."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("web_directory", type=Path)
    parser.add_argument("--pck", type=Path)
    parser.add_argument("--asset-prefix", action="append", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.report and args.report.resolve().is_relative_to(args.web_directory.resolve()):
            raise ValueError("Store reports outside the raw Web export tree")
        if args.report and (args.report.exists() or args.report.is_symlink()):
            raise ValueError("Report exists; select a new report path")
        result = audit(args.web_directory, args.pck, args.asset_prefix)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        print(encoded, end="")
        return 0 if result["passed"] else 1
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(json.dumps({"passed": False, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
