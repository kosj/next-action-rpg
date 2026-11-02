"""Freeze actual texture cache; prepare/run read-only Godot mip-pixel comparisons.

``freeze --cache game/.godot/imported --pck build/web/index.pck --extra-prefix
erin_idle_gameplay --extra-prefix roen_idle_gameplay --output NEW_OLD`` copies
the PCK's CTEX roster plus named new cache textures. It never changes a cache.
``compare --frozen NEW_OLD --cache game/.godot/imported --runtime-project
game/project.godot --output NEW_PROOF`` prepares only. Add --decode only after
exclusive CPU-lane coordination. Pinned headless Godot decodes, never encodes.

The actual project must explicitly select method6/factor100. This exact-image
comparison does not prove those settings triggered a fresh import; separately
invalidate generated .ctex+paired.md5 before the one cold import. The stock
4.7.2 texture importer settings hash omits these WebP effort knobs. No source,
sidecar, SCN, editor user data, runtime cache, or export is modified here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from audit_runtime_package import Pck, inspect_ctex
from render_weight_review import run_logged

ROOT = Path(__file__).resolve().parents[1]
GODOT_SCRIPT = Path(__file__).with_suffix(".gd")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    with path.open("x", encoding="utf-8") as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def new_directory(path):
    if path.exists() or path.is_symlink():
        raise ValueError("Use a new, nonexistent output directory")
    path.mkdir(parents=True)


def freeze(cache, pck_path, extra_prefixes, output):
    if output.resolve().is_relative_to(cache.resolve()):
        raise ValueError("Output must be outside the runtime cache")
    pck = Pck(pck_path)
    baseline = {Path(name).name: item for name, item in pck.entries.items() if name.endswith(".ctex")}
    if len(baseline) != sum(name.endswith(".ctex") for name in pck.entries):
        raise ValueError("Ambiguous PCK texture basenames")
    selected = set(baseline)
    for prefix in extra_prefixes:
        if not prefix or "/" in prefix or "\\" in prefix:
            raise ValueError("Extra cache prefix must be a filename prefix")
        matches = {path.name for path in cache.glob(prefix + "*.ctex")}
        if not matches:
            raise ValueError("No textures match requested extra cache prefix: " + prefix)
        selected |= matches
    if not selected:
        raise ValueError("No texture inputs")
    prepared = []
    for name in sorted(selected):
        source = cache / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("Missing or symlinked cache texture: " + name)
        data = source.read_bytes()
        header = inspect_ctex(data)
        if header["data_encoding"] != "webp":
            raise ValueError("This comparator requires actual WebP CTEX inputs")
        old_pck = baseline.get(name)
        prepared.append((name, data, {"name": name, "file": "inputs/" + name,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "texture_header": header,
            "baseline_pck_entry": old_pck["path"] if old_pck else None,
            "cache_matches_existing_pck_md5": hashlib.md5(data).hexdigest() == old_pck["md5"] if old_pck else None}))
    new_directory(output)
    (output / "inputs").mkdir()
    for name, data, record in prepared:
        with (output / record["file"]).open("xb") as file:
            file.write(data)
    inventory = {"schema": 1, "source_cache": str(cache.resolve()), "source_pck": str(pck_path),
        "cases": [record for _, _, record in prepared], "total_bytes": sum(len(data) for _, data, _ in prepared),
        "scope": "Frozen current cache pixels, not generated candidates; original cache/source files unchanged"}
    write_json(output / "inventory.json", inventory)
    return inventory


def frozen_cases(directory):
    manifest = json.loads((directory / "inventory.json").read_text())
    if manifest.get("schema") != 1 or not manifest.get("cases"):
        raise ValueError("Invalid frozen inventory")
    names = set()
    for item in manifest["cases"]:
        name = item["name"]
        if Path(name).name != name or not name.endswith(".ctex") or name in names:
            raise ValueError("Invalid/duplicate frozen texture name")
        names.add(name)
        if item["file"] != "inputs/" + name:
            raise ValueError("Frozen path must remain inside its inputs directory")
        source = directory / item["file"]
        if source.is_symlink() or source.stat().st_size != item["bytes"] or sha(source) != item["sha256"]:
            raise ValueError("Frozen texture bytes/SHA changed: " + name)
        if inspect_ctex(source.read_bytes()) != item["texture_header"]:
            raise ValueError("Frozen texture header/chunks changed")
    return manifest


def prepare(frozen, cache, runtime_project, output):
    if output.resolve().is_relative_to(cache.resolve()):
        raise ValueError("Output must be outside the runtime cache")
    manifest = frozen_cases(frozen)
    cases = []
    for item in manifest["cases"]:
        current = cache / item["name"]
        if current.is_symlink() or not current.is_file():
            raise ValueError("Missing/symlinked new cache texture: " + item["name"])
        cases.append({"name": item["name"], "before": str((frozen / item["file"]).resolve()),
            "before_sha256": item["sha256"], "after": str(current.resolve()),
            "source": {"baseline_pck_entry": item["baseline_pck_entry"]},
            "expected_total_mip_levels": item["texture_header"]["total_mip_levels"]})
    if not runtime_project.is_file():
        raise ValueError("Actual runtime project.godot is required")
    new_directory(output)
    project = output / "project"
    project.mkdir()
    (project / "project.godot").write_text('config_version=5\n\n[application]\nconfig/name="Private CTEX Decode Only"\n')
    shutil.copyfile(GODOT_SCRIPT, project / "compare_ctex.gd")
    config = {"result_path": str((output / "result.json").resolve()),
              "runtime_project_file": str(runtime_project.resolve()), "expected_cases": len(cases), "cases": cases}
    write_json(output / "config.json", config)
    write_json(output / "preparation.json", {"frozen_inventory_sha256": sha(frozen / "inventory.json"),
        "godot_script_sha256": sha(GODOT_SCRIPT), "cases": len(cases), "engine_invoked_during_preparation": False})
    return config


def validate_result(result, config):
    if result.get("status") != "complete_all_actual_imported_mips_RGBA_exact":
        raise ValueError("Actual Godot comparison did not finish successfully")
    actual = result.get("cases", [])
    expected = {item["name"]: item for item in config["cases"]}
    if len(actual) != len(expected) or len({item["name"] for item in actual}) != len(actual):
        raise ValueError("Incomplete/duplicate actual texture proof")
    for item in actual:
        target = expected.get(item["name"])
        if not target or not item.get("passed") or not item.get("first52_header_bytes_exact"):
            raise ValueError("Texture header/identity proof failed")
        if item["before_sha256"] != target["before_sha256"] or item["after_sha256"] != sha(Path(target["after"])):
            raise ValueError("Actual texture data changed or does not match the proof")
        if item["before_bytes"] != Path(target["before"]).stat().st_size or item["after_bytes"] != Path(target["after"]).stat().st_size or item["saved_bytes"] != item["before_bytes"] - item["after_bytes"]:
            raise ValueError("Actual texture byte totals do not match the proof")
        mips = item["mips"]
        if item["mip_levels"] != target["expected_total_mip_levels"] or len(mips) != item["mip_levels"]:
            raise ValueError("Actual mip count mismatch")
        for number, mip in enumerate(mips):
            if mip["level"] != number or not all(mip.get(field) for field in (
                "dimensions_exact", "decoded_format_exact", "complete_RGBA_bytes_exact_including_transparent_RGB")):
                raise ValueError("Actual mip dimensions/format/RGBA mismatch")
            if mip["before_RGBA_sha256"] != mip["after_RGBA_sha256"]:
                raise ValueError("Actual mip RGBA hashes differ")
    return {"cases": len(actual), "mip_levels": sum(item["mip_levels"] for item in actual),
            "before_bytes": sum(item["before_bytes"] for item in actual),
            "after_bytes": sum(item["after_bytes"] for item in actual),
            "saved_bytes": sum(item["saved_bytes"] for item in actual),
            "all_actual_imported_mips_RGBA_header_dimension_format_exact": True}


def decode(args, config):
    env = dict(os.environ)
    env.update({"GODOT_SILENCE_ROOT_WARNING": "1", "LP_NUM_THREADS": "2"})
    for key, folder in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")):
        path = args.output / ("xdg-" + folder)
        path.mkdir()
        env[key] = str(path.resolve())
    result = {"status": "running", "processes_closed": False}
    started = time.monotonic()
    try:
        version = subprocess.check_output([str(args.godot), "--version"], env=env, text=True, timeout=30).strip()
        pinned = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]
        if not version.startswith(pinned + ".stable."):
            raise ValueError("Pinned stable engine is required")
        result["engine"] = {"version": version, "sha256": sha(args.godot)}
        run_logged([str(args.godot), "--headless", "--path", str(args.output / "project"),
                    "--script", "res://compare_ctex.gd", "--", str(args.output / "config.json")],
                   args.output / "decode.log", env, args.wall_timeout)
        logs = (args.output / "decode.log").read_text()
        if any(marker in logs for marker in ("SCRIPT ERROR:", "ERROR:", "leaked at exit")):
            raise ValueError("Godot decode comparison logged an error")
        proof = json.loads((args.output / "result.json").read_text())
        result.update(status="actual_imported_texture_pixels_exact", summary=validate_result(proof, config))
        frozen_cases(args.frozen)
    except BaseException as error:
        result.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        result.update(processes_closed=True, elapsed_seconds=time.monotonic()-started)
        write_json(args.output / "verification.json", result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("freeze")
    first.add_argument("--pck", required=True, type=Path)
    first.add_argument("--extra-prefix", action="append", default=[])
    second = sub.add_parser("compare")
    second.add_argument("--frozen", required=True, type=Path)
    second.add_argument("--runtime-project", required=True, type=Path)
    second.add_argument("--decode", action="store_true")
    second.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    second.add_argument("--wall-timeout", type=int, default=180)
    for command in (first, second):
        command.add_argument("--cache", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    args.output = args.output.resolve()
    if args.command == "freeze":
        result = freeze(args.cache, args.pck, args.extra_prefix, args.output)
        print(json.dumps({"frozen_textures": len(result["cases"]), "frozen_bytes": result["total_bytes"]}))
    else:
        config = prepare(args.frozen, args.cache, args.runtime_project, args.output)
        print(json.dumps({"prepared_textures": len(config["cases"]), "decoding_requested": args.decode}), flush=True)
        if args.decode:
            decode(args, config)


if __name__ == "__main__":
    main()
