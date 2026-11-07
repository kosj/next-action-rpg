"""Prepare or capture actual Game skill VFX with an explicitly labelled policy.

Default preparation starts no engine/display server. Root owns the sole render
lane and must opt in with --capture. Normal mode earns resources through native
inputs; technical mode visibly records three rune-funding fixture writes.
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

from render_combat_gameplay import (
    archive_baseline, git, initial_import_metadata, inventory, sha, verify_inventory, write_json,
)
from render_weight_review import probe, run_logged, start_xorg, stop_process


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    "tests/skill_vfx_capture.gd", "tests/skill_vfx_capture.tscn",
    "tests/combat_continuity_capture.gd",
)
SCENE = "res://tests/skill_vfx_capture.tscn"
FPS = 60
SCOPE = (
    "Actual main Game, actors, camera, skill API and VFX at logical1x/60Hz. "
    "Script-generated native UI/key inputs, not human play. Technical mode uses "
    "explicit rune100 funding per skill and establishes presentation only; normal "
    "mode earns resources through real parries and ordinary encounters. No direct "
    "continuous watching/hearing, target hardware performance or AAA approval. "
    "Optional observed completion may shorten post-coverage idle; compare matching "
    "actual ticks/skill phases, not equal-duration whole movies."
)


def display_override(project: Path) -> dict:
    path = project / "project.godot"
    before = sha(path)
    text = path.read_text()
    overrides = {
        "window/size/viewport_width": "960", "window/size/viewport_height": "600",
        "window/size/window_width_override": "960", "window/size/window_height_override": "600",
        "window/stretch/mode": '"disabled"',
    }
    for key, value in overrides.items():
        text, count = re.subn(r"^" + re.escape(key) + r"=.*$", key + "=" + value, text, flags=re.M)
        if count != 1:
            raise ValueError("Expected one display setting: " + key)
    path.write_text(text)
    return {"source_sha256": before, "capture_sha256": sha(path), "overrides": overrides,
            "scope": "Private display dimensions only; production gameplay, camera, lighting and VFX inputs unchanged"}


def prepare(args: argparse.Namespace, label: str) -> dict:
    directory = args.output / label
    directory.mkdir()
    if label == "before":
        project = archive_baseline(args.baseline_ref, directory)
        context = {"kind": "isolated_git_archive", "commit": git("rev-parse", args.baseline_ref + "^{commit}"),
                   "dirty": False}
    else:
        project = directory / "project"
        shutil.copytree(args.candidate_project, project,
                        ignore=shutil.ignore_patterns(".godot", "__pycache__"), symlinks=False)
        context = {"kind": "independent_candidate_source_copy", "head": git("rev-parse", "HEAD"),
                   "dirty": bool(git("status", "--porcelain")), "worktree_status": git("status", "--short")}
    original = inventory(project)
    for name in original:
        if name.endswith(".glb.import"):
            preserved = directory / "source-import-settings" / name
            preserved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, preserved)
    for name in FIXTURES:
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "game" / name, destination)
    display = display_override(project)
    frozen = inventory(project)
    if args.import_cache_from:
        cache = args.import_cache_from.resolve() / ".godot"
        if not cache.is_dir():
            raise FileNotFoundError("Import-cache project lacks .godot: " + str(cache))
        shutil.copytree(cache, project / ".godot", symlinks=False)
        context["copied_derived_import_cache"] = str(cache)
    images = directory / "original-png"
    images.mkdir()
    context.update({"label": label, "runner_sha256": sha(Path(__file__)), "display": display,
                    "fixtures": {name: sha(project / name) for name in FIXTURES},
                    "software_threads": args.software_threads,
                    "original_inventory_sha256": hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()})
    config = {
        "fps": FPS, "frames": args.frames, "quality": args.quality,
        "scenario_name": "skill_vfx", "capture_policy": "native_skill_vfx_technical_v1" if args.mode == "technical" else "native_skill_vfx_earned_resources_v1",
        "scope": SCOPE, "source_context": context, "skill_mode": args.mode,
        "stop_when_complete": args.stop_when_complete,
        "software_threads": args.software_threads,
        "require_skill_effects": label == "after",
        "snapshot": str(directory / "frames.json"), "image_directory": str(images),
    }
    write_json(directory / "source-inputs.json", original)
    write_json(directory / "capture-inputs.json", frozen)
    write_json(directory / "config.json", config)
    return {"directory": str(directory), "project": str(project), "config": config,
            "frozen_inputs": frozen}


def validate_trace(trace: dict, take: dict) -> dict:
    config = take["config"]
    if trace.get("status") != "scripted_native_gameplay_captured":
        raise RuntimeError("Skill fixture failed: " + trace.get("failure", "missing result"))
    actual_frames = trace.get("gameplay_frames")
    budget = config["frames"]
    event_driven = bool(config.get("stop_when_complete", False))
    if trace.get("fps") != FPS or trace.get("logical_speed") != 1.0:
        raise RuntimeError("Actual trace clock/duration disagrees with the prescribed take")
    if not isinstance(actual_frames, int) or not 1 <= actual_frames <= budget or (not event_driven and actual_frames != budget):
        raise RuntimeError("Actual frame count is outside its unchanged capture budget")
    rows = trace["frames"]
    if any(abs(float(row["delta"]) - 1/FPS) > 1e-6 for row in rows):
        raise RuntimeError("Native physics delta changed")
    if any(b["tick"] != a["tick"]+1 for a, b in zip(rows, rows[1:])):
        raise RuntimeError("Missing or repeated native physics row")
    gameplay = [row for row in rows if row["gameplay_frame"] >= 0]
    if len(gameplay) != actual_frames or gameplay[-1]["gameplay_frame"] != actual_frames-1 or any(row["quality"] != config["quality"] or row["paused"] for row in gameplay):
        raise RuntimeError("Quality, pause or gameplay frame coverage changed")
    coverage = trace["provenance"].get("skill_vfx_coverage", {})
    for label in ("skill_1", "skill_2", "skill_3"):
        if coverage.get("accepted_casts", {}).get(label, 0) < 1 or coverage.get("active_samples", {}).get(label, 0) < 1:
            raise RuntimeError("Missing real accepted active skill: " + label)
        if config["require_skill_effects"] and coverage.get("new_effect_samples", {}).get(label, 0) < 1:
            raise RuntimeError("Missing actual new effect for " + label)
    writes = coverage.get("technical_resource_writes", [])
    if config["skill_mode"] == "normal" and writes:
        raise RuntimeError("Normal resource-earning mode contains fixture resource writes")
    if config["skill_mode"] == "technical" and len(writes) != 3:
        raise RuntimeError("Technical mode lacks its three explicit rune-funding actions")
    if event_driven:
        if coverage.get("frame_budget") != budget or coverage.get("actual_gameplay_frames") != actual_frames or not coverage.get("stop_when_complete"):
            raise RuntimeError("Early completion changed or omitted its declared frame budget")
        expected_reason = "all_three_skills_recovered_and_effects_expired" if actual_frames < budget else "exact_frame_budget_complete"
        if coverage.get("completion_reason") != expected_reason:
            raise RuntimeError("Missing explicit observed completion reason")
        accepted = [e for e in trace["input_events"] if e.get("type") == "accepted_skill_observed"]
        if not accepted:
            raise RuntimeError("Early completion lacks accepted skill events")
        last_accept = max(e["tick"] for e in accepted)
        quiet = trace["tick_count"]-last_accept
        if coverage.get("last_accepted_skill_tick") != last_accept or quiet < 90 or coverage.get("quiet_after_last_accept_ticks") != quiet:
            raise RuntimeError("Early completion lacks90actual ticks after the last accepted skill")
        if not coverage.get("all_skill_requests_recovered") or coverage.get("live_skill_effect_count") != 0:
            raise RuntimeError("Early completion still owns a cast or live skill effect")
        if gameplay[-1]["hero"].get("dead", False) or gameplay[-1]["hero"]["presentation"].get("attack_id") or gameplay[-1].get("skill_effects_after_physics"):
            raise RuntimeError("Final actual physics sample has a dead actor, attack or live effect")
        recovered = {e.get("attack_id") for e in trace["input_events"]
                     if e.get("type") == "skill_cast_end_observed" and e.get("full_recovery")
                     and float(e.get("elapsed", -1)) >= float(e.get("duration", 0))-1e-6}
        for label in ("skill_1", "skill_2", "skill_3"):
            if label not in recovered or coverage.get("completed_skill_casts", {}).get(label, 0) < 1:
                raise RuntimeError("Early completion lacks a fully recovered cast: " + label)
    contacts = [r for r in trace["receipts"] if str(r.get("attack_id", "")).startswith("skill_")]
    pairs = [(r.get("attack_instance_id"), r.get("target_id")) for r in contacts]
    if len(pairs) != len(set(pairs)):
        raise RuntimeError("Same skill attack hit the same target more than once")
    return {"mode": config["skill_mode"], "gameplay_frames": len(gameplay), "frame_budget": budget,
            "completion_reason": coverage.get("completion_reason", "exact_frame_budget_complete_legacy"),
            "software_threads": config.get("software_threads", 1), "quality": config["quality"],
            "coverage": coverage, "actual_skill_contacts": len(contacts),
            "actual_build_id": trace["provenance"].get("build_id"),
            "normal_resource_earning_proven": config["skill_mode"] == "normal" and not writes,
            "comparison_scope": "Match actual ticks/skill phases; optional completed takes need not have the same whole-movie length as an older exact-budget take",
            "scope": SCOPE}


def encode(directory: Path, trace: dict, env: dict[str, str]) -> dict:
    raw = directory / "gameplay.avi"
    movie = directory / "gameplay-logical1x.mp4"
    raw_info = probe(raw)
    count = max(int(row.get("movie_frame", -1)) for row in trace["frames"])+1
    if raw_info["r_frame_rate"] != "60/1" or count < len(trace["frames"]) or count > int(raw_info["nb_read_frames"]):
        raise RuntimeError("Raw MovieMaker render-frame mapping is incomplete")
    run_logged(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(raw),
                "-map", "0:v:0", "-map", "0:a:0?", "-frames:v", str(count),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-threads", "1", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(movie)],
               directory / "encode.log", env, timeout=600)
    info = probe(movie)
    if info["r_frame_rate"] != "60/1" or int(info["nb_read_frames"]) != count:
        raise RuntimeError("Delivery movie lost or retimed actual frames")
    from PIL import Image
    pngs = []
    for item in trace["images"]:
        path = Path(item["path"])
        with Image.open(path) as original:
            if original.size != (960, 600):
                raise RuntimeError("Actual viewport image dimensions disagree")
        if sha(path) != item["sha256"]:
            raise RuntimeError("Original screenshot changed after capture")
        pngs.append({"label": item["label"], "path": str(path), "sha256": sha(path), "tick": item["tick"]})
    return {"raw": {"path": str(raw), "sha256": sha(raw), "probe": raw_info},
            "delivery": {"path": str(movie), "sha256": sha(movie), "probe": info,
                         "scope": "Same actual frames at logical1x; original engine audio if present transcoded to AAC, no added effects or listening approval"},
            "original_pngs": pngs}


def capture(args: argparse.Namespace, takes: dict) -> None:
    server = None
    result = {"status": "running", "scope": SCOPE, "takes": {}, "started_unix": time.time(),
              "software_renderer_threads": args.software_threads,
              "renderer_thread_scope": "llvmpipe worker setting only, not measured target-device FPS",
              "display_tcp_disabled": True, "processes_closed": False}
    base_env = dict(os.environ)
    base_env.update({"LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe", "LP_NUM_THREADS": str(args.software_threads),
                     "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "GODOT_SILENCE_ROOT_WARNING": "1"})
    try:
        for label, take in takes.items():
            directory, project = Path(take["directory"]), Path(take["project"])
            env = dict(base_env)
            for name, folder in (("XDG_DATA_HOME", "user-data"), ("XDG_CONFIG_HOME", "user-config"), ("XDG_CACHE_HOME", "user-cache")):
                path = directory / folder
                path.mkdir()
                env[name] = str(path)
            print(json.dumps({"stage": "import", "take": label}), flush=True)
            run_logged([str(args.godot), "--headless", "--editor", "--path", str(project), "--quit", SCENE],
                       directory / "import.log", env, timeout=args.wall_timeout)
            if re.search(r"(?:SCRIPT ERROR:|ERROR:)", (directory / "import.log").read_text()):
                raise RuntimeError("Importer/fixture parse error; see import.log")
            runtime_inputs = initial_import_metadata(project, take["frozen_inputs"], directory)
            verify_inventory(project, runtime_inputs)
            if server is None:
                server, display = start_xorg(args.output, base_env, args.xvfb)
            env["DISPLAY"] = display
            print(json.dumps({"stage": "skill_capture", "take": label, "mode": args.mode}), flush=True)
            run_logged([str(args.godot), "--path", str(project), "--scene", SCENE,
                        "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                        "--audio-driver", "Dummy", "--resolution", "960x600", "--windowed", "--single-window",
                        "--fixed-fps", "60", "--disable-vsync", "--write-movie", str(directory / "gameplay.avi"),
                        "--", str(directory / "config.json")], directory / "gameplay.log", env, timeout=args.wall_timeout)
            log = (directory / "gameplay.log").read_text()
            if re.search(r"(?:SCRIPT ERROR:|ERROR:)", log):
                raise RuntimeError("Actual capture logged an engine error; see gameplay.log")
            trace = json.loads((directory / "frames.json").read_text())
            cleanup = json.loads((directory / "cleanup.json").read_text())
            if not cleanup.get("actual_audio_weakrefs_released"):
                raise RuntimeError("Actual audio cleanup did not release its references")
            actual = validate_trace(trace, take)
            verify_inventory(project, runtime_inputs)
            result["takes"][label] = {"actual": actual, "cleanup": cleanup,
                                      "media": encode(directory, trace, env), "source_inputs_unchanged": True}
            write_json(args.output / "capture.json", result)
        result["status"] = "technical_resource_funded_game_presentation_captured" if args.mode == "technical" else "normal_input_earned_resource_gameplay_captured"
    except BaseException as error:
        result["status"] = "failed"
        result["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        stop_process(server)
        result["processes_closed"] = True
        result["finished_unix"] = time.time()
        result["elapsed_s"] = result["finished_unix"]-result["started_unix"]
        write_json(args.output / "capture.json", result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--mode", choices=("normal", "technical"), default="normal")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--stop-when-complete", action=argparse.BooleanOptionalAction, default=None,
                        help="Finish on observed all3skill full recovery, expired effects and90quiet ticks; --frames remains the unchanged upper budget. Defaults on for normal, off for technical; explicit --no-stop-when-complete keeps exact frames")
    parser.add_argument("--software-threads", type=int, choices=range(1, 5), default=1,
                        help="llvmpipe workers only; preserves logical60Hz/1x and does not establish actual deviceFPS")
    parser.add_argument("--quality", type=int, choices=(0, 1), default=1)
    parser.add_argument("--baseline-ref", default="951f314359685706a1db53a8f2351a26c4512222")
    parser.add_argument("--take", choices=("before", "after", "both"), default="after")
    parser.add_argument("--candidate-project", type=Path, default=ROOT / "game")
    parser.add_argument("--import-cache-from", type=Path)
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--xvfb", type=Path)
    parser.add_argument("--wall-timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stop_when_complete is None:
        args.stop_when_complete = args.mode == "normal"
    args.frames = args.frames if args.frames is not None else (840 if args.mode == "technical" else 2700)
    if not 840 <= args.frames <= 2700 or not 120 <= args.wall_timeout <= 3600:
        parser.error("Use840–2700logical60Hz frames and120–3600s wall limit")
    args.output, args.candidate_project, args.godot = args.output.resolve(), args.candidate_project.resolve(), args.godot.resolve()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Fresh output directory required; prior evidence is never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    labels = ("before", "after") if args.take == "both" else (args.take,)
    takes = {label: prepare(args, label) for label in labels}
    write_json(args.output / "prepared.json", {"status": "prepared_only_no_engine_or_server_launched",
               "scope": SCOPE, "mode": args.mode, "runner_sha256": sha(Path(__file__)),
               "software_renderer_threads": args.software_threads,
               "stop_when_complete": args.stop_when_complete,
               "takes": {label: {k: v for k, v in take.items() if k != "frozen_inputs"} for label, take in takes.items()}})
    print(json.dumps({"status": "prepared", "output": str(args.output), "takes": list(takes), "mode": args.mode}), flush=True)
    if args.capture:
        capture(args, takes)


if __name__ == "__main__":
    main()
