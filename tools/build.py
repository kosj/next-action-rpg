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
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
GODOT_VERSION = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]
TEXTURE_PROFILE_MARKER = "runefall-texture-import-profile.json"
WEBP_SETTINGS = {
    "textures/webp_compression/compression_method": 2,
    "textures/webp_compression/lossless_compression_factor": 25.0,
}


def texture_import_profile(project_file):
    """Read only the two literal settings omitted by Godot 4.7.2's cache key."""
    values = dict(WEBP_SETTINGS)
    seen = set()
    section = ""
    for line in Path(project_file).read_text(encoding="utf-8").splitlines():
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            section = line
            continue
        if section != "[rendering]" or "=" not in line:
            continue
        key, literal = (part.strip() for part in line.split("=", 1))
        if key not in values:
            continue
        if key in seen:
            raise ValueError("Duplicate texture import setting: " + key)
        seen.add(key)
        if key.endswith("/compression_method"):
            if not re.fullmatch(r"[0-6]", literal):
                raise ValueError("WebP compression_method must be an integer from 0 to 6")
            values[key] = int(literal)
        else:
            if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", literal):
                raise ValueError("WebP lossless_compression_factor must be a numeric literal")
            value = float(literal)
            if not 0 <= value <= 100:
                raise ValueError("WebP lossless_compression_factor must be from 0 to 100")
            values[key] = value
    return {"schema": 1, "godot": GODOT_VERSION, "settings": values}


def _texture_cache_paths(project_dir):
    cache = Path(project_dir) / ".godot"
    imported = cache / "imported"
    marker = cache / TEXTURE_PROFILE_MARKER
    for directory in (cache, imported):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("Unsafe generated texture cache directory: " + str(directory))
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise ValueError("Unsafe texture profile marker: " + str(marker))
    return cache, imported, marker


def prepare_texture_import_cache(project_dir, profile):
    """Invalidate generated texture data only; leave all source/sidecars intact.

    Godot 4.7.2 fingerprints VRAM formats but omits global WebP method/factor.
    A marker describes only a completed import. Remove a stale marker before
    invalidation so an interrupted import cannot be mistaken for a warm cache
    even if settings subsequently return to the earlier profile.
    """
    _, imported, marker = _texture_cache_paths(project_dir)
    previous = None
    reason = "missing_marker"
    if marker.exists():
        try:
            previous = json.loads(marker.read_text(encoding="utf-8"))
            reason = "profile_changed"
        except (ValueError, UnicodeError):
            reason = "invalid_marker"
    if previous == profile:
        return {"reason": "profile_unchanged", "invalidated": [], "profile": profile}
    targets = set()
    for texture in sorted(imported.glob("*.ctex")):
        # Godot stores format variants as <source>-<32hex>[.<format>].ctex,
        # sharing the source-hash .md5 file without that optional format suffix.
        match = re.fullmatch(r"(.+-[0-9a-f]{32})(?:\.[A-Za-z0-9_]+)?\.ctex", texture.name)
        if match is None:
            raise ValueError("Unrecognized generated texture name: " + str(texture))
        targets.add(texture)
        digest = imported / (match.group(1) + ".md5")
        if digest.exists() or digest.is_symlink():
            targets.add(digest)
    # Preflight the entire deletion set before removing any entry.
    for target in targets:
        if target.is_symlink() or not target.is_file():
            raise ValueError("Unsafe generated texture cache entry: " + str(target))
    if marker.exists():
        marker.unlink()
    for target in sorted(targets):
        target.unlink()
    return {"reason": reason, "invalidated": [path.name for path in sorted(targets)], "profile": profile}


def record_texture_import_profile(project_dir, profile):
    cache, _, marker = _texture_cache_paths(project_dir)
    cache.mkdir(exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=cache,
                                         prefix=".runefall-texture-profile-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(profile, sort_keys=True, indent=2) + "\n")
        os.replace(temporary, marker)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def import_project():
    project = ROOT / "game"
    profile = texture_import_profile(project / "project.godot")
    report = prepare_texture_import_cache(project, profile)
    print("RUNEFALL_TEXTURE_IMPORT_CACHE " + json.dumps({
        "reason": report["reason"], "invalidated_files": len(report["invalidated"]), "profile": profile}))
    # Method6/factor100 lossless authoring exceeded 310s with only 15/46
    # textures complete. Bound cold encoding to 20min; unchanged profiles reuse
    # the completed cache. Native/export/browser bounds remain independent.
    godot_run(["--editor", "--import"], timeout=1200)
    record_texture_import_profile(project, profile)
    return report


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
    import_project()
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
