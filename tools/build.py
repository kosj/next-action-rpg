"""Import, validate, export and package RUNEFALL with the pinned Godot toolchain.

python tools/build.py                 # Web
python tools/build.py --windows       # Web + Windows x86_64
python tools/build.py --test-only      # import + regression tests
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
GODOT_VERSION = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]


def project_version():
    config = (ROOT / "game/project.godot").read_text()
    match = re.search(r'^config/version="([^"]+)"$', config, re.MULTILINE)
    if not match:
        raise SystemExit("Missing application version in game/project.godot")
    return match.group(1)


def godot_run(args, marker=None, timeout=180):
    command = [os.environ.get("GODOT_BIN", "godot"), "--headless", "--path", str(ROOT / "game"), *args]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    print(result.stdout)
    if result.returncode or "SCRIPT ERROR:" in result.stdout or "ERROR:" in result.stdout or (marker and marker not in result.stdout):
        raise SystemExit("Godot validation failed: " + " ".join(args))


def package(folder, name):
    target = BUILD / name
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder))
    return {"file": target.name, "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", action="store_true")
    parser.add_argument("--test-only", action="store_true")
    args = parser.parse_args()
    version = subprocess.check_output([os.environ.get("GODOT_BIN", "godot"), "--version"], text=True).strip()
    if not version.startswith(GODOT_VERSION + ".stable."):
        raise SystemExit("Godot " + GODOT_VERSION + " stable is required; found " + version)
    app_version = project_version()
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/v") and ref.removeprefix("refs/tags/v") != app_version:
        raise SystemExit("Release tag does not match application version " + app_version)
    BUILD.mkdir(exist_ok=True)
    godot_run(["--editor", "--import"])
    godot_run(["res://tests/runner.tscn"], "RUNEFALL_TESTS:", timeout=60)
    if args.test_only:
        return
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except subprocess.CalledProcessError:
        commit = "local"
    (ROOT / "game/build_id.txt").write_text(app_version + " · " + commit + "\n")
    for name in ["web", "windows"] if args.windows else ["web"]:
        shutil.rmtree(BUILD / name, ignore_errors=True)
        (BUILD / name).mkdir()
        godot_run(["--export-release", "Web" if name == "web" else "Windows"])
    web_files = [p for p in (BUILD / "web").rglob("*") if p.is_file()]
    if sum(p.stat().st_size for p in web_files) > 150_000_000:
        raise SystemExit("Web build exceeds the 150 MB project budget")
    (BUILD / "web/.nojekyll").touch()
    # Keep dependency licenses with every distribution.
    for name in ["web", "windows"] if args.windows else ["web"]:
        shutil.copy(ROOT / "THIRD_PARTY_NOTICES.md", BUILD / name)
        shutil.copy(ROOT / "game/assets/fonts/OFL.txt", BUILD / name / "FONT_LICENSE.txt")
        engine_license = ROOT / "docs/GODOT_LICENSE.txt"
        shutil.copy(engine_license, BUILD / name)
        shutil.copy(ROOT / "docs/GODOT_THIRD_PARTY.txt", BUILD / name)
    artifacts = [package(BUILD / "web", "runefall-web.zip")]
    if args.windows:
        artifacts.append(package(BUILD / "windows", "runefall-windows.zip"))
    (BUILD / "manifest.json").write_text(json.dumps({"version":app_version, "godot":GODOT_VERSION, "commit":commit,"artifacts":artifacts}, indent=2))
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
