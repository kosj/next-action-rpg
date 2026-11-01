"""Capture actual scripted native gameplay with production physics/presentation.

Preparation is the default and starts no engine or display server. Coordinate
the sole software GPU/CPU slot before --capture. Every take gets an independent
project and empty XDG user-data directory; no repository checkout is switched.
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
import tarfile
import time

from render_weight_review import probe, run_logged, start_xorg, stop_process

ROOT = Path(__file__).resolve().parents[1]
FPS = 60
BASELINE = "1e524b1275c6c55d3020ea5c3122afbb8db403e9"
FIXTURES = ("tests/combat_gameplay_capture.gd", "tests/combat_gameplay_capture.tscn")
SCOPE = (
    "Scripted native MovieMaker gameplay at logical1x/60Hz using actual Game, "
    "RunePlayer/RuneEnemy physics, production camera, real confirmed damage and VFX. "
    "Native GUI/key/mouse events are script-generated, not human play or browser QA. "
    "Silent delivery does not establish audio-hearing, real-time FPS, hardware "
    "performance, animation naturalness or AAA approval."
)
POLICY = {
    "ui": "Native mouse clicks: Settings; quality1 via OptionButton and Down/Enter; Done; New Game; prologue Continue",
    "movement": "Native W+Shift to actual first encounter, Tab lock; hold right mouse Heavy while approaching within2m",
    "release": "Stop movement; wait for real incoming health decrease and stagger clear with Heavy>=.65; release right mouse",
    "completion": "Observe real charged contact and both actors paused, then ordinary recovery to bounded end",
    "prohibited": ["teleport", "invulnerability writes", "forced damage", "save injection", "QA state writes", "forced sync"],
    "variance": "Matched event-driven input policy, not identical AI trajectories or fixed event timestamps",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def inventory(project: Path) -> dict[str, dict]:
    """All actual project source/resources, excluding only generated cache."""
    result = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if ".godot" in relative.parts or not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError(f"Source snapshots must be independent regular files: {path}")
        result[relative.as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return result


def verify_inventory(project: Path, expected: dict[str, dict]) -> None:
    changed = [name for name, item in expected.items()
               if not (project / name).is_file() or sha(project / name) != item["sha256"]]
    if changed:
        raise RuntimeError("Frozen project inputs changed: " + ", ".join(changed[:20]))


def initial_import_metadata(project: Path, expected: dict[str, dict], directory: Path) -> dict[str, dict]:
    """Account for newly serialized4.7.2 defaults without accepting input edits.

    First import of the four old placeholder GLBs writes these previously
    implicit defaults. Preserve source bytes, permit only exact inserted default
    lines, then freeze and verify the resulting runtime metadata independently.
    No production GLB, hook, existing setting value or code change is permitted.
    """
    defaults = {"mesh_library/use_node_names_as_mesh_names=false",
                "array_mesh/deduplicate_surfaces=true", "gltf/texture_map_mode=0"}
    changes = []
    actual = dict(expected)
    for name, item in expected.items():
        path = project / name
        if path.is_file() and sha(path) == item["sha256"]:
            continue
        original = directory / "source-import-settings" / name
        if not name.endswith(".glb.import") or not original.is_file() or not path.is_file():
            raise RuntimeError("Initial import modified a frozen production input: " + name)
        before = original.read_text().splitlines(keepends=True)
        after = path.read_text().splitlines(keepends=True)
        inserted = [line.strip() for line in after if line.strip() in defaults and line not in before]
        filtered = [line for line in after if not (line.strip() in inserted and line not in before)]
        if not inserted or len(inserted) != len(set(inserted)) or filtered != before:
            raise RuntimeError("Unexpected initial importer metadata change: " + name)
        changes.append({"path": name, "source_sha256": item["sha256"], "runtime_sha256": sha(path),
                        "only_added_implicit_default_lines": inserted})
        actual[name] = {"sha256": sha(path), "bytes": path.stat().st_size}
    write_json(directory / "initial-import-metadata.json", {"changes": changes,
               "scope": "Only exact newly serialized Godot4.7.2 implicit defaults; source sidecars preserved separately"})
    write_json(directory / "runtime-inputs.json", actual)
    return actual


def archive_baseline(ref: str, output: Path) -> Path:
    actual_ref = git("rev-parse", ref + "^{commit}")
    archive = output / "baseline-game.tar"
    with archive.open("wb") as stream:
        subprocess.run(["git", "-C", str(ROOT), "archive", actual_ref, "game"],
                       stdout=stream, check=True)
    with tarfile.open(archive) as source:
        # Git archive only, nevertheless refuse absolute/escaping paths and links.
        for member in source.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts or member.issym() or member.islnk():
                raise ValueError("Unsafe baseline archive entry: " + member.name)
        source.extractall(output, filter="data")
    project = output / "project"
    (output / "game").rename(project)
    archive.unlink()
    return project


def override_capture_display(project: Path) -> dict:
    path = project / "project.godot"
    before = sha(path)
    text = path.read_text()
    replacements = {"window/size/viewport_width": "1280", "window/size/viewport_height": "720",
                    "window/size/window_width_override": "1280", "window/size/window_height_override": "720",
                    "window/stretch/mode": '"disabled"'}
    for key, value in replacements.items():
        text, count = re.subn(r"^" + re.escape(key) + r"=.*$", key + "=" + value, text, flags=re.M)
        if count != 1:
            raise ValueError("Expected exactly one source display setting: " + key)
    path.write_text(text)
    return {"source_sha256": before, "capture_sha256": sha(path), "overrides": replacements,
            "scope": "Matched isolated capture dimensions only; game code, physics, lighting and materials unmodified"}


def prepare_take(args: argparse.Namespace, label: str) -> dict:
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
        context = {"kind": "independent_source_copy", "source_project": str(args.candidate_project),
                   "repository_head": git("rev-parse", "HEAD"),
                   "repository_worktree_status": git("status", "--short"),
                   "dirty": bool(git("status", "--porcelain"))}
    original = inventory(project)
    for name in original:
        if name.endswith(".glb.import"):
            preserved = directory / "source-import-settings" / name
            preserved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, preserved)
    for name in FIXTURES:
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "game" / name, target)
    display = override_capture_display(project)
    frozen = inventory(project)
    images = directory / "original-png"
    images.mkdir()
    context.update({"label": label, "display": display,
                    "source_inventory_sha256": hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
                    "fixture_sha256": {name: sha(project / name) for name in FIXTURES},
                    "runner_sha256": sha(Path(__file__)),
                    "helper_sha256": sha(ROOT / "tools/render_weight_review.py")})
    if args.import_cache_from is not None:
        cache = args.import_cache_from.resolve() / ".godot"
        if not cache.is_dir():
            raise FileNotFoundError("Reused project has no private import cache: " + str(cache))
        shutil.copytree(cache, project / ".godot", symlinks=False)
        context["reused_derived_import_cache"] = {"source": str(cache),
            "policy": "Copy only; normal pinned editor import still runs and validates source/dependency hashes before capture"}
    # Both complete inventories are durable, including actual production model,
    # import hook, imported-source sidecar, curve, camera and weapon input hashes.
    write_json(directory / "source-inputs.json", original)
    write_json(directory / "capture-inputs.json", frozen)
    config = {"fps": FPS, "frames": args.frames, "scope": SCOPE, "scenario": POLICY,
              "source_context": context, "snapshot": str(directory / "frames.json"),
              "image_directory": str(images)}
    write_json(directory / "config.json", config)
    return {"directory": str(directory), "project": str(project), "config": config,
            "frozen_inputs": frozen, "display": display}


def validate_trace(trace: dict, expected_frames: int) -> dict:
    if trace.get("status") != "scripted_native_gameplay_captured":
        raise RuntimeError("Actual gameplay fixture failed: " + trace.get("failure", "missing result"))
    if trace.get("logical_speed") != 1.0 or trace.get("fps") != FPS:
        raise RuntimeError("Actual capture clock does not match logical1x/60Hz")
    if trace.get("gameplay_frames") != expected_frames or trace.get("paired_pause_frames", 0) < 1:
        raise RuntimeError("Actual gameplay duration/both-actor pause proof is incomplete")
    rows = trace["frames"]
    if any(abs(row["delta"] - 1 / FPS) > 1e-6 for row in rows):
        raise RuntimeError("Actual physics samples are not fixed60Hz")
    if any(b["tick"] != a["tick"] + 1 for a, b in zip(rows, rows[1:])):
        raise RuntimeError("Missing/duplicate recorded physics tick")
    play_rows = [row for row in rows if row["gameplay_frame"] >= 0]
    if len(play_rows) != expected_frames or play_rows[-1]["gameplay_frame"] != expected_frames - 1:
        raise RuntimeError("Actual gameplay trace does not contain exactly its prescribed60Hz ticks")
    if any(row["quality"] != 1 or row["checkpoint"] != 0 or row["paused"] for row in play_rows):
        raise RuntimeError("Quality/checkpoint/unpaused gameplay changed during the take")
    contacts = [packet for packet in trace["receipts"]
                if packet.get("source") == "player" and packet.get("attack_id") == "charged_heavy"]
    if not contacts or any(packet.get("contact_source") not in ("hurtbox_ray", "hurtbox_proxy") for packet in contacts):
        raise RuntimeError("Missing actual hurtbox charged contact receipt")
    pairs = [(packet.get("attack_instance_id"), packet.get("target_id")) for packet in contacts]
    if len(set(pairs)) != len(pairs):
        raise RuntimeError("Same charged attack damaged the same target more than once")
    for packet in contacts:
        if packet.get("blocked") or abs(float(packet.get("amount", 0)) - 69.3) > 0.02:
            raise RuntimeError("Recorded first-encounter charged damage is not its actual69.3 unblocked cut")
    models = trace["provenance"]["models"]
    if any(not value.get("sha256") or len(value["sha256"]) != 64 for value in models.values()):
        raise RuntimeError("Actual ProductionCharacterArt model source hash is missing")
    curve = trace["provenance"]["curve"]
    if curve.get("mode") != "baseline_analytic_blade" and not curve.get("ok"):
        raise RuntimeError("Actual runtime curve resource rejected its pinned input")
    return {"charged_contacts": len(contacts), "paired_pause_frames": trace["paired_pause_frames"],
            "actual_models": models, "actual_curve": curve, "contact_tick": trace["contact_tick"],
            "release_tick": trace["release_tick"], "actual_build_id": trace["provenance"]["build_id"],
            "start_health": play_rows[0]["hero"]["health"], "end_health": play_rows[-1]["hero"]["health"],
            "frame_count": len(rows), "gameplay_frames": trace["gameplay_frames"]}


def inspect_png(path: Path) -> dict:
    """Read only original daytime first-encounter raster; no image edits."""
    from PIL import Image, ImageStat
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.size != (1280, 720):
            raise RuntimeError("Original native viewport PNG dimensions differ")
        mean = ImageStat.Stat(image).mean
        middle = [x for x in range(image.width) if max(image.getpixel((x, image.height // 2))) > 8]
        span = max(middle) - min(middle) + 1 if middle else 0
        if min(mean) < 4 or span < image.width * 0.8:
            raise RuntimeError("First-room original raster is black/letterboxed or empty")
        return {"path": str(path), "sha256": sha(path), "size": list(image.size),
                "rgb_mean": mean, "middle_row_nonblack_span": span,
                "scope": "Bounded daylight first-encounter raster sanity, not visual-quality approval"}


def encode_take(directory: Path, trace: dict, env: dict[str, str]) -> dict:
    raw = directory / "gameplay.avi"
    movie = directory / "gameplay-logical1x.mp4"
    raw_info = probe(raw)
    if raw_info["r_frame_rate"] != "60/1" or int(raw_info["nb_read_frames"]) < len(trace["frames"]):
        raise RuntimeError("MovieMaker did not write the required native60Hz frames")
    # Retain actual UI and gameplay in order. Only a possible engine quit/drain
    # frame is trimmed; no seeked poses, time interpolation, camera or pixel edit.
    count = max(int(row.get("movie_frame", -1)) for row in trace["frames"]) + 1
    if count < len(trace["frames"]) or count > int(raw_info["nb_read_frames"]):
        raise RuntimeError("Recorded render-frame mapping does not fit the actual movie")
    run_logged(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(raw), "-an",
                "-frames:v", str(count), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-threads", "1", "-movflags", "+faststart", str(movie)],
               directory / "encode.log", env, timeout=300)
    info = probe(movie)
    if info["r_frame_rate"] != "60/1" or int(info["nb_read_frames"]) != count:
        raise RuntimeError("Delivery movie lost or retimed actual frames")
    # Menus can be dark. Raster guards apply only to real unpaused first-room
    # gameplay/charge/contact images, never the title/prologue shade.
    images = [inspect_png(Path(item["path"])) for item in trace["images"]
              if item["label"].startswith(("01-", "02-", "04-"))]
    if len(images) < 3:
        raise RuntimeError("Required gameplay/charge/contact original PNGs are missing")
    return {"raw": {"path": str(raw), "sha256": sha(raw), "probe": raw_info},
            "delivery": {"path": str(movie), "sha256": sha(movie), "probe": info,
                         "logical_speed": 1.0, "audio": "silent, not listened/approved", "frames": count},
            "original_png_checks": images}


def capture(args: argparse.Namespace, takes: dict[str, dict]) -> None:
    server = None
    result = {"scope": SCOPE, "scenario": POLICY, "status": "running", "takes": {},
              "display_tcp_disabled": True, "processes_closed": False, "started_unix": time.time()}
    base_env = dict(os.environ)
    base_env.update({"LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe", "LP_NUM_THREADS": "1",
                     "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "GODOT_SILENCE_ROOT_WARNING": "1"})
    try:
        for label, take in takes.items():
            directory = Path(take["directory"])
            project = Path(take["project"])
            env = dict(base_env)
            for name, folder in (("XDG_DATA_HOME", "user-data"), ("XDG_CONFIG_HOME", "user-config"),
                                 ("XDG_CACHE_HOME", "user-cache")):
                path = directory / folder
                path.mkdir()
                env[name] = str(path)
            print(json.dumps({"stage": "import", "take": label, "log": str(directory / "import.log")}), flush=True)
            # Open the scene in project editor mode so autoload identifiers
            # (Session/Audio/TouchControls) are registered. Standalone --script
            # --check-only intentionally lacks that project runtime context.
            run_logged([str(args.godot), "--headless", "--editor", "--path", str(project), "--quit",
                        "res://tests/combat_gameplay_capture.tscn"],
                       directory / "import.log", env, timeout=args.wall_timeout)
            if re.search(r"(?:SCRIPT ERROR:|ERROR:)", (directory / "import.log").read_text()):
                raise RuntimeError("Project import/scene parse logged an engine error; see import.log")
            runtime_inputs = initial_import_metadata(project, take["frozen_inputs"], directory)
            verify_inventory(project, runtime_inputs)
            if server is None:
                server, display = start_xorg(args.output, base_env, args.xvfb)
            env["DISPLAY"] = display
            command = [str(args.godot), "--path", str(project), "--scene", "res://tests/combat_gameplay_capture.tscn",
                       "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                       "--audio-driver", "Dummy", "--resolution", "1280x720", "--windowed", "--single-window",
                       "--fixed-fps", "60", "--disable-vsync", "--write-movie", str(directory / "gameplay.avi"),
                       "--", str(directory / "config.json")]
            print(json.dumps({"stage": "actual_gameplay_capture", "take": label,
                              "log": str(directory / "gameplay.log")}), flush=True)
            run_logged(command, directory / "gameplay.log", env, timeout=args.wall_timeout)
            engine_lines = (directory / "gameplay.log").read_text().splitlines()
            engine_errors = [line for line in engine_lines if "SCRIPT ERROR:" in line or line.startswith("ERROR:")]
            engine_warnings = [line for line in engine_lines if line.startswith("WARNING:")]
            trace = json.loads((directory / "frames.json").read_text())
            cleanup = json.loads((directory / "cleanup.json").read_text())
            if not cleanup.get("actual_audio_weakrefs_released"):
                raise RuntimeError("Actual audio playback WeakRefs were not released after the take")
            actual = validate_trace(trace, args.frames)
            verify_inventory(project, runtime_inputs)
            result["takes"][label] = {"actual": actual, "media": encode_take(directory, trace, env),
                                      "source_inputs_unchanged": True, "engine_errors": engine_errors,
                                      "engine_warnings": engine_warnings, "cleanup": cleanup}
            write_json(args.output / "capture.json", result)
            if engine_errors:
                raise RuntimeError("Actual take produced engine errors (media/trace retained): " + "; ".join(engine_errors))
        result["status"] = "scripted_native_gameplay_captured"
    except BaseException as error:
        result["status"] = "failed"
        result["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        stop_process(server)
        result["processes_closed"] = True
        result["finished_unix"] = time.time()
        result["elapsed_s"] = result["finished_unix"] - result["started_unix"]
        write_json(args.output / "capture.json", result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="Explicitly launch engines/local-only display after slot coordination")
    parser.add_argument("--baseline-ref", default=BASELINE)
    parser.add_argument("--candidate-project", type=Path, default=ROOT / "game")
    parser.add_argument("--import-cache-from", type=Path,
                        help="Optional prior isolated project cache; normal editor source/dependency validation still runs")
    parser.add_argument("--take", choices=("both", "before", "after"), default="both")
    parser.add_argument("--frames", type=int, default=720, help="Actual gameplay ticks, excluding at most240 normal UI ticks")
    parser.add_argument("--output", type=Path, default=ROOT / "build/art-review/combat-gameplay")
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--xvfb", type=Path, help="Optional extracted Xvfb; local-only dummy Xorg is the default")
    parser.add_argument("--wall-timeout", type=int, default=1200, help="Per import/take wall resource budget, independent of logical movie duration")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.candidate_project = args.candidate_project.resolve()
    args.godot = args.godot.resolve()
    if not 600 <= args.frames <= 960 or not 120 <= args.wall_timeout <= 1800:
        parser.error("Use 600–960 actual gameplay ticks and120–1800s wall resource limit")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("A fresh output directory is required; prior evidence is never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    labels = ("before", "after") if args.take == "both" else (args.take,)
    takes = {label: prepare_take(args, label) for label in labels}
    manifest = {"status": "prepared_only_no_engine_or_server_launched", "scope": SCOPE, "scenario": POLICY,
                "takes": {label: {key: value for key, value in take.items() if key != "frozen_inputs"}
                          for label, take in takes.items()}, "runner_sha256": sha(Path(__file__)),
                "godot": str(args.godot), "capture_requested": args.capture,
                "baseline_repository_checkout_unchanged": True,
                "reference": "https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html"}
    write_json(args.output / "prepared.json", manifest)
    print(json.dumps({"status": manifest["status"], "output": str(args.output), "takes": list(takes)}), flush=True)
    if args.capture:
        capture(args, takes)


if __name__ == "__main__":
    main()
