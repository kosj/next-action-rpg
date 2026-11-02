"""Matched actual-scene lighting stills; preparation only unless --capture.

Coordinate the sole local heavy lane before --capture. These deterministic
scene-view fixtures prescribe actor transforms/idle pose and freeze gameplay.
They do not establish actual input, motion/AV, Web export, hardware or AAA quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from render_combat_gameplay import (archive_baseline, git, initial_import_metadata,
    inventory, override_capture_display, sha, verify_inventory, write_json)
from render_weight_review import run_logged, start_xorg, stop_process

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ("tests/lighting_review_capture.gd", "tests/lighting_review_capture.tscn")
SCOPE = ("Deterministic actual Game/production actors/courtyard lighting scene-view "
         "comparison in native Compatibility at1280x720. Prescribed transforms, idle "
         "pose and frozen physics are fixture controls, not real-input gameplay. "
         "Native quality0 balanced has1.0 render scale; quality1 performance.65. "
         "Web/DPR, interactive motion/AV, hardware performance and AAA remain separate.")


def project_version(project: Path) -> str:
    match = re.search(r'^config/version="([^"\n]+)"$',
                      (project / "project.godot").read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError("Source project has no explicit application version")
    return match.group(1)


def prepare(args: argparse.Namespace, label: str) -> dict:
    directory = args.output / label
    directory.mkdir()
    if label == "before":
        project = archive_baseline(args.baseline_ref, directory)
        context = {"kind": "isolated_git_archive", "commit": git("rev-parse", args.baseline_ref + "^{commit}"),
                   "tree": git("rev-parse", args.baseline_ref + "^{tree}"), "dirty": False}
    else:
        project = directory / "project"
        shutil.copytree(args.candidate_project, project,
                        ignore=shutil.ignore_patterns(".godot", "__pycache__"), symlinks=False)
        context = {"kind": "independent_source_copy", "head": git("rev-parse", "HEAD"),
                   "worktree_status": git("status", "--short"), "dirty": bool(git("status", "--porcelain"))}
    context.update({"requested_baseline_ref": args.baseline_ref,
                    "baseline_commit": git("rev-parse", args.baseline_ref + "^{commit}"),
                    "application_version": project_version(project)})
    baseline_version = re.search(r'^config/version="([^"\n]+)"$',
                                git("show", args.baseline_ref + ":game/project.godot"), re.MULTILINE)
    if not baseline_version:
        raise RuntimeError("Baseline project has no explicit application version")
    context["baseline_application_version"] = baseline_version.group(1)
    original = inventory(project)
    for name in original:
        if name.endswith(".glb.import"):
            target = directory / "source-import-settings" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, target)
    for name in FIXTURES:
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "game" / name, target)
    context["display_overrides"] = override_capture_display(project)
    context.update({"fixture_sha256": {name: sha(project / name) for name in FIXTURES},
                    "runner_sha256": sha(Path(__file__)),
                    "shared_helpers_sha256": {name: sha(ROOT / "tools" / name) for name in
                                               ["render_combat_gameplay.py", "render_weight_review.py"]}})
    if args.import_cache_from is not None:
        cache = args.import_cache_from.resolve() / ".godot"
        if not cache.is_dir():
            raise FileNotFoundError("Supplied cache project lacks .godot: " + str(cache))
        shutil.copytree(cache, project / ".godot", symlinks=False)
        context["copied_derived_cache"] = {"from": str(cache), "policy": "Copy only; normal pinned editor import validates dependencies"}
    frozen = inventory(project)
    for filename, value in [("source-inputs.json", original), ("capture-inputs.json", frozen)]:
        write_json(directory / filename, value)
    images = directory / "original-png"
    images.mkdir()
    config = {"scope": SCOPE, "source_context": context, "show_ui": args.show_ui,
              "qualities": args.qualities, "views": args.views,
              "output_directory": str(images), "result_path": str(directory / "scene-review.json")}
    write_json(directory / "config.json", config)
    return {"directory": str(directory), "project": str(project), "context": context,
            "frozen": frozen, "config": config}


def validate_report(report: dict, take: dict) -> dict:
    if report.get("status") != "deterministic_actual_scene_captured" or report.get("renderer") != "gl_compatibility":
        raise RuntimeError("Actual scene/Compatibility renderer report incomplete")
    if report.get("application_version") != take["context"]["application_version"]:
        raise RuntimeError("Actual application version disagrees with frozen source context")
    collision = report.get("sanctuary_static_collision", {})
    rows = collision.get("canonical_rows", [])
    if not rows or rows != sorted(rows) or collision.get("shape_count") != len(rows) or collision.get("sha256") != hashlib.sha256("\n".join(rows).encode()).hexdigest():
        raise RuntimeError("Actual Sanctuary static shape multiset fingerprint is incomplete")
    expected = {(view, q) for view in take["config"]["views"] for q in take["config"]["qualities"]}
    actual = {(row["view"], row["quality"]) for row in report["shots"]}
    if actual != expected or len(report["shots"]) != len(expected):
        raise RuntimeError("Scene review is missing or duplicating matched views/qualities")
    images = Path(take["directory"]) / "original-png"
    from PIL import Image, ImageStat
    checks = []
    for shot in report["shots"]:
        quality = shot["quality"]
        if abs(shot["render_scale"] - (1.0 if quality == 0 else .65)) > 1e-6:
            raise RuntimeError("Actual native quality render scale disagrees with its declared mode")
        key = next(light for light in shot["lights"] if light["name"] == "SanctuaryKey")
        if key["shadows"] != (quality == 0):
            raise RuntimeError("Actual production sun does not follow balanced/performance shadow policy")
        for actor in shot["actors"]:
            art = actor["art"]
            if art.get("mode") != "skeletal" or art.get("profile") != actor["profile"] or not art.get("weapon_attached") or abs(art.get("grip_to_tip_m",0)-1.19) > .003:
                raise RuntimeError("Scene fixture fell back from its actual production body/weapon profile")
        path = images / shot["file"]
        if path.name != shot["file"] or sha(path) != shot["sha256"]:
            raise RuntimeError("Original raster path/hash changed")
        with Image.open(path) as image:
            if image.size != (1280, 720):
                raise RuntimeError("Actual original viewport image is not1280x720")
            means = ImageStat.Stat(image.convert("RGB")).mean
            if max(means) < 4:
                raise RuntimeError("Actual scene raster is empty/black")
            checks.append({"file": shot["file"], "sha256": sha(path), "rgb_means": means,
                           "scope": "Raw dimension/hash/nonblack sanity, not visual-quality approval"})
    for view in take["config"]["views"]:
        rows = [shot for shot in report["shots"] if shot["view"] == view]
        if any(row["camera"] != rows[0]["camera"] or
               [actor["position"] for actor in row["actors"]] != [actor["position"] for actor in rows[0]["actors"]]
               for row in rows[1:]):
            raise RuntimeError("Quality comparison changed the prescribed actual camera/actor positions")
    return {"shots": len(checks), "original_rasters": checks, "renderer": report["renderer"],
            "quality_policy_observed": "0 balanced/shadowsON/native1.0;1 performance/shadowsOFF/native.65"}


def capture(args: argparse.Namespace, takes: dict) -> None:
    result = {"scope": SCOPE, "status": "running", "takes": {}, "started_unix": time.time(),
              "processes_closed": False, "display_tcp_disabled": True}
    server = None
    env_base = dict(os.environ)
    env_base.update({"LP_NUM_THREADS": "2", "GODOT_SILENCE_ROOT_WARNING": "1"})
    try:
        probe_env = dict(env_base)
        for key, folder in [("XDG_DATA_HOME","version-data"),("XDG_CONFIG_HOME","version-config"),("XDG_CACHE_HOME","version-cache")]:
            target = args.output / folder
            target.mkdir()
            probe_env[key] = str(target)
        version = subprocess.check_output([str(args.godot), "--version"], text=True,env=probe_env).strip()
        required = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]
        if not version.startswith(required + ".stable."):
            raise RuntimeError("Lighting review requires pinned stable engine " + required)
        result["engine"] = version
        for label, take in takes.items():
            directory, project = Path(take["directory"]), Path(take["project"])
            env = dict(env_base)
            for key, folder in [("XDG_DATA_HOME", "user-data"), ("XDG_CONFIG_HOME", "user-config"), ("XDG_CACHE_HOME", "user-cache")]:
                target = directory / folder
                target.mkdir()
                env[key] = str(target)
            print(json.dumps({"stage": "import_and_parse", "take": label}), flush=True)
            run_logged([str(args.godot), "--headless", "--editor", "--path", str(project), "--quit",
                        "res://tests/lighting_review_capture.tscn"], directory / "import.log", env, args.wall_timeout)
            if re.search(r"(?:SCRIPT ERROR:|ERROR:)", (directory / "import.log").read_text()):
                raise RuntimeError("Project/fixture parse logged an engine error")
            runtime = initial_import_metadata(project, take["frozen"], directory)
            verify_inventory(project, runtime)
            if server is None:
                server, display = start_xorg(args.output, env_base, args.xvfb)
            env["DISPLAY"] = display
            print(json.dumps({"stage": "actual_scene_raster_capture", "take": label}), flush=True)
            run_logged([str(args.godot), "--path", str(project), "--scene", "res://tests/lighting_review_capture.tscn",
                        "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                        "--audio-driver", "Dummy", "--resolution", "1280x720", "--windowed", "--single-window", "--disable-vsync",
                        "--", str(directory / "config.json")], directory / "capture.log", env, args.wall_timeout)
            lines = (directory / "capture.log").read_text().splitlines()
            errors = [line for line in lines if "SCRIPT ERROR:" in line or line.startswith("ERROR:")]
            report = json.loads((directory / "scene-review.json").read_text())
            check = validate_report(report, take)
            verify_inventory(project, runtime)
            result["takes"][label] = {"actual": check, "source_inputs_unchanged": True,
                                      "engine_errors": errors, "engine_warnings": [line for line in lines if line.startswith("WARNING:")]}
            write_json(args.output / "capture.json", result)
            if errors:
                raise RuntimeError("Actual scene capture logged engine errors: " + "; ".join(errors))
        result["status"] = "deterministic_actual_scene_captured"
    except BaseException as error:
        result.update(status="failed", failure=f"{type(error).__name__}: {error}")
        raise
    finally:
        stop_process(server)
        result.update(processes_closed=True, elapsed_s=time.time()-result["started_unix"])
        write_json(args.output / "capture.json", result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="Explicitly launch heavy render work after lane coordination")
    parser.add_argument("--baseline-ref", required=True,
                        help="Explicit comparison baseline; resolve and record its exact commit in every take")
    parser.add_argument("--candidate-project", type=Path, default=ROOT / "game")
    parser.add_argument("--import-cache-from", type=Path)
    parser.add_argument("--take", choices=["both", "before", "after"], default="both")
    parser.add_argument("--qualities", type=int, nargs="+", choices=[0,1], default=[0,1])
    parser.add_argument("--views", nargs="+", choices=["landing", "fight", "overview"], default=["landing", "fight", "overview"])
    parser.add_argument("--hide-ui", dest="show_ui", action="store_false", default=True,
                        help="Hide controlled static actualHUD; default retains HUD for gameplay-camera readability")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--xvfb", type=Path)
    parser.add_argument("--wall-timeout", type=int, default=600)
    args = parser.parse_args()
    if not 60 <= args.wall_timeout <= 1800:
        parser.error("Use bounded60–1800s per-process timeout")
    args.output = args.output.resolve()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("A fresh output directory is required")
    args.output.mkdir(parents=True, exist_ok=True)
    labels = ["before", "after"] if args.take == "both" else [args.take]
    takes = {label: prepare(args, label) for label in labels}
    write_json(args.output / "prepared.json", {"status": "prepared_only_no_engine_or_display_started", "scope": SCOPE,
               "capture_requested": args.capture, "takes": {label: {key: value for key, value in take.items() if key != "frozen"}
                                                            for label, take in takes.items()}})
    print(json.dumps({"status": "prepared_only", "output": str(args.output), "takes": labels}), flush=True)
    if args.capture:
        capture(args, takes)


if __name__ == "__main__":
    main()
