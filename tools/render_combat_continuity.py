"""Capture actual scripted native continuity with engine-mixed MovieWriter audio.

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
import time

from render_weight_review import probe, run_logged, start_xorg, stop_process
from render_combat_gameplay import (archive_baseline,git,initial_import_metadata,inventory,sha,verify_inventory,write_json)
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FPS = 60
BASELINE = "ff1171a1834a99e29b3dfecac2498c84fad4a90e"
FIXTURES = ("tests/combat_continuity_capture.gd", "tests/combat_continuity_capture.tscn")
WRITER_REFERENCES = {
    "fixed_dummy_driver":"https://github.com/godotengine/godot/blob/4.7.2-stable/main/main.cpp#L2829",
    "per_frame_engine_mix":"https://github.com/godotengine/godot/blob/4.7.2-stable/servers/movie_writer/movie_writer.cpp#L244",
    "actual_audio_server_process":"https://github.com/godotengine/godot/blob/4.7.2-stable/servers/audio/audio_driver_dummy.cpp#L113",
    "AVI_PCM_write":"https://github.com/godotengine/godot/blob/4.7.2-stable/modules/jpg/movie_writer_mjpeg.cpp#L180",
}
SCOPE = (
    "Scripted native MovieMaker gameplay at logical1x/60Hz using actual Game, "
    "RunePlayer/RuneEnemy physics, production camera, real confirmed damage and VFX. "
    "Native GUI/key/mouse events are script-generated, not human play or browser QA. "
    "Engine-mixed PCM is preserved, but numerical audio checks do not establish direct hearing, real-time FPS, hardware "
    "performance, animation naturalness or AAA approval."
)
POLICY = {
    "ui": "Native mouse clicks: Settings; quality1 via OptionButton and Down/Enter; Done; New Game; prologue Continue",
    "movement": "Continuity: safe W/A/D locomotion, ordinary3-light chain and charged whiff, heal attempt; real first encounter with W+Shift/Tab/heavy. Contact scenario omits prelude.",
    "release": "Stop movement; wait for real incoming health decrease and stagger clear with Heavy>=.65; release right mouse",
    "completion": "Observe real charged contact and both actors paused, then normal recovery, optional healing/defensive movement to bounded end. Observed coverage is recorded separately from attempted inputs.",
    "prohibited": ["teleport", "invulnerability writes", "forced damage", "save injection", "QA state writes", "forced sync"],
    "variance": "Matched event-driven input policy, not identical AI trajectories or fixed event timestamps",
}


def override_capture_display(project: Path,width: int,height: int) -> dict:
    path = project / "project.godot"
    before = sha(path)
    text = path.read_text()
    # Preserve the production logical viewport and canvas_items stretch.
    # Native UI rects remain in viewport coordinates; events map through the
    # actual final transform into the smaller physical capture window.
    replacements = {"window/size/window_width_override": str(width), "window/size/window_height_override": str(height)}
    for key, value in replacements.items():
        text, count = re.subn(r"^" + re.escape(key) + r"=.*$", key + "=" + value, text, flags=re.M)
        if count != 1:
            raise ValueError("Expected exactly one source display setting: " + key)
    path.write_text(text)
    logical = [int(re.search(r"^window/size/viewport_"+axis+r"=(\d+)$",text,re.M).group(1)) for axis in ["width","height"]]
    if width*logical[1]!=height*logical[0]:
        raise ValueError("Physical output aspect must match source logical viewport to prevent MovieWriter crop/resize")
    return {"source_sha256": before, "capture_sha256": sha(path), "overrides": replacements,
            "logical_viewport":logical,"physical_capture_size":[width,height],"source_aspect_preserved":True,
            "scope": "Only physical window dimensions overridden; source logical viewport/stretch preserved; native pointers use actual final transform"}


def raster_profile(threads: int) -> dict:
    return {"backend": "Mesa llvmpipe software", "requested_LP_NUM_THREADS": threads,
            "OMP_NUM_THREADS": 1, "OPENBLAS_NUM_THREADS": 1,
            "scope": "Requested software raster worker limit, not observed worker count or hardware/FPS evidence; compare takes with the same requested profile"}


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
    display = override_capture_display(project,args.width,args.height)
    frozen = inventory(project)
    images = directory / "original-png"
    images.mkdir()
    capture_policy = "continuity_plus_ordinary_heavy_v015" if args.include_heavy else "continuity_v014"
    context.update({"label": label, "display": display,"physical_capture_size":[args.width,args.height],"logical_viewport":display["logical_viewport"],
                    "capture_policy":capture_policy,"include_heavy":args.include_heavy,
                    "raster_profile":raster_profile(args.raster_threads),
                    "baseline_commit":git("rev-parse",args.baseline_ref+"^{commit}"),
                    "application_version":re.search(r'config/version="([^"\n]+)"',(project/"project.godot").read_text()).group(1),
                    "source_inventory_sha256": hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
                    "fixture_sha256": {name: sha(project / name) for name in FIXTURES},
                    "runner_sha256": sha(Path(__file__)),
                    "helper_sha256": {name:sha(ROOT/"tools"/name) for name in ["render_weight_review.py","render_combat_gameplay.py"]}})
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
    policy = dict(POLICY)
    if args.include_heavy:
        policy["movement"] = "Continuity: safe W/A/D, ordinary3-light chain, one ordinary right-tap heavy whiff, charged whiff, heal attempt; real first encounter/contact/recovery. No attack state writes."
    config = {"fps": FPS, "frames": args.frames, "scope": SCOPE, "scenario": policy,"include_heavy":args.include_heavy,"capture_policy":capture_policy,
              "source_context": context, "snapshot": str(directory / "frames.json"),
              "image_directory": str(images),"scenario_name":args.scenario,"quality":args.quality,
              "physical_capture_size":[args.width,args.height],"raster_profile":raster_profile(args.raster_threads),
              "ui_geometry_probe":args.ui_geometry_probe,"ui_route_probe":args.ui_route_probe}
    write_json(directory / "config.json", config)
    return {"directory": str(directory), "project": str(project), "config": config,
            "frozen_inputs": frozen, "display": display}


def validate_trace(trace: dict, expected_frames: int,quality: int=1) -> dict:
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
    if any(row["quality"] != quality or row["checkpoint"] != 0 or row["paused"] for row in play_rows):
        raise RuntimeError("Quality/checkpoint/unpaused gameplay changed during the take")
    if any(abs(row["render_scale"]-(.65 if quality==1 else 1.0))>1e-6 for row in play_rows):
        raise RuntimeError("Actual native render scale disagrees with selected quality")
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
    if trace.get("scenario_name")=="continuity":
        active = set()
        for row in play_rows:
            state = row["hero"]["presentation"]
            if float(state["attack_startup"]) <= float(state["attack_elapsed"]) < float(state["attack_startup"])+float(state["attack_active"]):
                active.add(state["attack_id"])
        if not {"light_1","light_2","light_3"}.issubset(active):
            raise RuntimeError("Actual trace did not observe all3 ordinary light active phases")
        coverage = trace["observed_coverage"]
        whiff = int(coverage["whiff_attack_instance_id"])
        if not coverage["safe_charged_whiff"] or whiff<=0 or any(int(packet.get("attack_instance_id",0))==whiff for packet in trace["receipts"]):
            raise RuntimeError("Actual charged-whiff instance unexpectedly contacted or was not observed")
        if coverage["heal_input_attempts"]<1 or coverage["maximum_locomotion_displacement_m"]<.5:
            raise RuntimeError("Continuity locomotion/heal-input coverage missing")
        if trace.get("include_heavy"):
            heavy=int(coverage.get("ordinary_heavy_attack_instance_id",0))
            if "heavy" not in active or coverage.get("ordinary_heavy_active_samples",0)<1 or not coverage.get("ordinary_heavy_whiff") or heavy<=0:
                raise RuntimeError("Requested ordinary heavy active-phase/whiff coverage missing")
            if any(int(packet.get("attack_instance_id",0))==heavy for packet in trace["receipts"]):
                raise RuntimeError("Observed safe ordinary heavy instance unexpectedly contacted")
    return {"charged_contacts": len(contacts), "paired_pause_frames": trace["paired_pause_frames"],
            "actual_models": models, "actual_curve": curve, "contact_tick": trace["contact_tick"],
            "release_tick": trace["release_tick"], "actual_build_id": trace["provenance"]["build_id"],
            "start_health": play_rows[0]["hero"]["health"], "end_health": play_rows[-1]["hero"]["health"],
            "frame_count": len(rows), "gameplay_frames": trace["gameplay_frames"],
            "capture_policy":trace.get("capture_policy","continuity_v014"),"include_heavy":bool(trace.get("include_heavy",False)),
            "observed_coverage":trace.get("observed_coverage",{}),"scenario_name":trace.get("scenario_name")}


def inspect_png(path: Path,size: tuple[int,int]) -> dict:
    """Read only original daytime first-encounter raster; no image edits."""
    from PIL import Image, ImageStat
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.size != size:
            raise RuntimeError("Original native viewport PNG dimensions differ")
        mean = ImageStat.Stat(image).mean
        middle = [x for x in range(image.width) if max(image.getpixel((x, image.height // 2))) > 8]
        span = max(middle) - min(middle) + 1 if middle else 0
        if min(mean) < 4 or span < image.width * 0.8:
            raise RuntimeError("First-room original raster is black/letterboxed or empty")
        return {"path": str(path), "sha256": sha(path), "size": list(image.size),
                "rgb_mean": mean, "middle_row_nonblack_span": span,
                "scope": "Bounded daylight first-encounter raster sanity, not visual-quality approval"}


def av_probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format",
                                               "-of","json",str(path)],text=True))


def pcm_bytes(path: Path) -> bytes:
    return subprocess.check_output(["ffmpeg","-nostdin","-v","error","-i",str(path),"-map","0:a:0",
                                    "-vn","-c:a","pcm_s16le","-f","s16le","pipe:1"])


def pcm_report(data: bytes, channels: int, rate: int) -> dict:
    values = np.frombuffer(data,dtype="<i2")
    if not len(values) or len(values)%channels:
        raise RuntimeError("Engine PCM has incomplete/empty sample frames")
    values = values.reshape(-1,channels)
    rows = []
    for channel in range(channels):
        samples = values[:,channel].astype(np.float64)
        nonzero = np.flatnonzero(samples)
        rows.append({"channel":channel,"nonzero_samples":int(len(nonzero)),
                     "absolute_peak_int16":int(np.max(np.abs(samples))),
                     "rms_normalized":float(np.sqrt(np.mean((samples/32768.0)**2))),
                     "clipped_samples":int(np.count_nonzero(np.abs(samples)>=32767)),
                     "first_nonzero_frame":int(nonzero[0]) if len(nonzero) else None,
                     "last_nonzero_frame":int(nonzero[-1]) if len(nonzero) else None})
    if not any(row["nonzero_samples"] for row in rows):
        raise RuntimeError("Recorded engine-mixed PCM is entirely silent")
    return {"scope":"Decoded engine PCM/sample counts/peak/RMS only; not direct hearing or perceptual sync approval",
            "sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"sample_frames":len(values),
            "sample_rate":rate,"channels":channels,"seconds":len(values)/rate,"channel_metrics":rows}


def encode_take(directory: Path, trace: dict, env: dict[str,str]) -> dict:
    raw = directory/"gameplay.avi"
    movie = directory/"gameplay-logical1x-av.mp4"
    wav = directory/"engine-mix-logical1x.wav"
    raw_info = probe(raw)
    streams = av_probe(raw)
    audio = [stream for stream in streams["streams"] if stream["codec_type"]=="audio"]
    if len(audio)!=1 or audio[0]["codec_name"]!="pcm_s16le":
        raise RuntimeError("Raw MovieWriter must expose one genuine16-bit PCM audio stream")
    rate,channels = int(audio[0]["sample_rate"]),int(audio[0]["channels"])
    if rate!=48000 or channels!=2 or rate%FPS:
        raise RuntimeError("Expected observed48kHz stereo PCM divisible by fixed60Hz")
    raw_frames = int(raw_info["nb_read_frames"])
    physical = tuple(trace["provenance"]["source_context"]["physical_capture_size"])
    if (int(raw_info["width"]),int(raw_info["height"]))!=physical or any(tuple(item["pixel_size"])!=physical for item in trace["images"]):
        raise RuntimeError("Actual viewport PNG/raw AVI/physical output dimensions differ; refuse implicit writer crop/resize")
    if raw_info["r_frame_rate"]!="60/1" or raw_frames<len(trace["frames"]):
        raise RuntimeError("Raw MovieWriter did not retain fixed60Hz gameplay frames")
    count = max(int(row.get("movie_frame",-1)) for row in trace["frames"])+1
    if count<len(trace["frames"]) or count>raw_frames:
        raise RuntimeError("Trace-to-render-frame mapping is incomplete")
    decoded = pcm_bytes(raw)
    raw_audio = pcm_report(decoded,channels,rate)
    samples_per_frame = rate//FPS
    if raw_audio["sample_frames"]!=raw_frames*samples_per_frame:
        raise RuntimeError("Raw audio/video counts violate the writer's per-frame PCM contract")
    sample_frames = count*samples_per_frame
    # Only matched quit/drain tail is omitted. The raw AV master stays intact.
    # This WAV is the exact prefix of its own engine mixer, never added audio.
    run_logged(["ffmpeg","-nostdin","-v","error","-i",str(raw),"-map","0:a:0","-vn",
                "-af",f"atrim=end_sample={sample_frames},asetpts=PTS-STARTPTS","-c:a","pcm_s16le",str(wav)],
               directory/"audio-prefix.log",env,timeout=300)
    exact = pcm_bytes(wav)
    if exact!=decoded[:sample_frames*channels*2]:
        raise RuntimeError("WAV changed engine PCM samples instead of retaining its exact aligned prefix")
    wav_audio = pcm_report(exact,channels,rate)
    duration = count/FPS
    run_logged(["ffmpeg","-nostdin","-v","error","-threads","1","-i",str(raw),"-i",str(wav),
                "-map","0:v:0","-map","1:a:0","-frames:v",str(count),"-t",f"{duration:.9f}",
                "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-threads","1",
                "-c:a","aac","-b:a","192k","-movflags","+faststart",str(movie)],
               directory/"encode-av.log",env,timeout=600)
    final_video = probe(movie)
    final_av = av_probe(movie)
    final_audio = [stream for stream in final_av["streams"] if stream["codec_type"]=="audio"]
    if final_video["r_frame_rate"]!="60/1" or int(final_video["nb_read_frames"])!=count:
        raise RuntimeError("AV delivery lost/retimed actual render frames")
    if len(final_audio)!=1 or int(final_audio[0]["sample_rate"])!=rate or int(final_audio[0]["channels"])!=channels:
        raise RuntimeError("AV delivery lost its engine audio stream")
    audio_duration = float(final_audio[0]["duration"])
    if abs(audio_duration-duration)>1/FPS+.002:
        raise RuntimeError("Delivery audio/video duration differs beyond one fixed frame")
    delivery_audio = pcm_report(pcm_bytes(movie),channels,rate)
    images = [inspect_png(Path(item["path"]),physical)
              for item in trace["images"] if item["label"].startswith(("01-","02-","04-","08-"))]
    if len(images)<3:
        raise RuntimeError("Required actual gameplay/charge/contact originals are missing")
    result = {"raw":{"path":str(raw),"sha256":sha(raw),"video_probe":raw_info,"av_probe":streams,"engine_PCM":raw_audio},
              "lossless_audio":{"path":str(wav),"sha256":sha(wav),"engine_PCM_prefix_exact":True,"decoded":wav_audio},
              "delivery":{"path":str(movie),"sha256":sha(movie),"video_probe":final_video,"av_probe":final_av,
                          "audio_decoded":delivery_audio,"audio_codec":"AAC lossy delivery; exact original PCM retained in AVI/WAV",
                          "logical_speed":1.0,"video_frames":count,"seconds":duration,"audio_seconds":audio_duration,
                          "no_speed_or_time_interpolation":True,"no_added_audio":True,"direct_hearing_approval":False},
              "sync":{"sample_frames_per_video_frame":samples_per_frame,"raw_counts_exact":True,
                      "trimmed_video_frames":raw_frames-count,"trimmed_audio_sample_frames":raw_audio["sample_frames"]-sample_frames,
                      "scope":"Container/sample-clock alignment only; perceived whoosh/contact timing requires continuous AV review"},
              "original_png_checks":images}
    write_json(directory/"av-verification.json",result)
    return result


def capture(args: argparse.Namespace, takes: dict[str, dict]) -> None:
    server = None
    result = {"scope": SCOPE, "scenario": next(iter(takes.values()))["config"]["scenario"],
              "capture_policy":next(iter(takes.values()))["config"]["capture_policy"],"include_heavy":args.include_heavy,
              "status": "running", "takes": {},
              "display_tcp_disabled": True, "processes_closed": False, "started_unix": time.time(),
              "writer_contract_sources":WRITER_REFERENCES,"raster_profile":raster_profile(args.raster_threads)}
    base_env = dict(os.environ)
    base_env.update({"LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe", "LP_NUM_THREADS": str(args.raster_threads),
                     "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "GODOT_SILENCE_ROOT_WARNING": "1"})
    try:
        probe_env = dict(base_env)
        for name,folder in (("XDG_DATA_HOME","version-data"),("XDG_CONFIG_HOME","version-config"),("XDG_CACHE_HOME","version-cache")):
            directory = args.output/folder
            directory.mkdir()
            probe_env[name] = str(directory)
        version = subprocess.check_output([str(args.godot),"--version"],text=True,env=probe_env).strip()
        required = json.loads((ROOT/"tools/toolchain.json").read_text())["godot_version"]
        if not version.startswith(required+".stable."):
            raise RuntimeError("Continuity AV requires the pinned stable engine "+required)
        result.update(engine_version=version,engine_sha256=sha(args.godot))
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
                        "res://tests/combat_continuity_capture.tscn"],
                       directory / "import.log", env, timeout=args.wall_timeout)
            if re.search(r"(?:SCRIPT ERROR:|ERROR:)", (directory / "import.log").read_text()):
                raise RuntimeError("Project import/scene parse logged an engine error; see import.log")
            runtime_inputs = initial_import_metadata(project, take["frozen_inputs"], directory)
            verify_inventory(project, runtime_inputs)
            if server is None:
                server, display = start_xorg(args.output, base_env, args.xvfb)
            env["DISPLAY"] = display
            command = [str(args.godot), "--path", str(project), "--scene", "res://tests/combat_continuity_capture.tscn",
                       "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                       "--audio-driver", "Dummy", "--resolution", f"{args.width}x{args.height}", "--windowed", "--single-window",
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
            if bool(trace.get("include_heavy",False))!=args.include_heavy:
                raise RuntimeError("Actual fixture heavy policy differs from requested input policy")
            if not cleanup.get("actual_audio_weakrefs_released"):
                raise RuntimeError("Actual audio playback WeakRefs were not released after the take")
            if args.ui_geometry_probe or args.ui_route_probe:
                expected_status = "ui_route_probe_captured" if args.ui_route_probe else "ui_geometry_probe_captured"
                if trace.get("status")!=expected_status or not trace.get("ui_geometry"):
                    raise RuntimeError("Actual read-only UI geometry probe incomplete")
                if args.ui_route_probe and (trace["ui_geometry"]["modal_present"] or trace["frames"][-1]["quality"]!=args.quality):
                    raise RuntimeError("Native UI route did not actually resume with requested quality")
                actual = {"scope":"UI geometry diagnostic only; no gameplay/AV coverage approval","ui_geometry":trace["ui_geometry"]}
            else:
                actual = validate_trace(trace, args.frames,args.quality)
            verify_inventory(project, runtime_inputs)
            media = {"scope":"Raw UI-only diagnostic; no AV delivery or nonzero-audio gate applied","raw_path":str(directory/"gameplay.avi")} if (args.ui_geometry_probe or args.ui_route_probe) else encode_take(directory,trace,env)
            result["takes"][label] = {"actual": actual, "media": media,
                                      "source_inputs_unchanged": True, "engine_errors": engine_errors,
                                      "engine_warnings": engine_warnings, "cleanup": cleanup}
            write_json(args.output / "capture.json", result)
            if engine_errors:
                raise RuntimeError("Actual take produced engine errors (media/trace retained): " + "; ".join(engine_errors))
        result["status"] = ("ui_route_probe_captured" if args.ui_route_probe else "ui_geometry_probe_captured") if (args.ui_geometry_probe or args.ui_route_probe) else "scripted_native_gameplay_captured"
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
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--candidate-project", type=Path, default=ROOT / "game")
    parser.add_argument("--import-cache-from", type=Path,
                        help="Optional prior isolated project cache; normal editor source/dependency validation still runs")
    parser.add_argument("--take", choices=("both", "before", "after"), default="both")
    parser.add_argument("--seconds", type=int, choices=[14,45,60], default=14)
    parser.add_argument("--scenario", choices=["continuity","contact"], default="continuity")
    parser.add_argument("--include-heavy",action="store_true",help="Distinct v15 policy: add one native right-tap ordinary heavy whiff; default retains v14 input policy")
    parser.add_argument("--ui-geometry-probe",action="store_true",help="Read native UI geometry and exit after4ticks; no gameplay/AV approval")
    parser.add_argument("--ui-route-probe",action="store_true",help="Drive actual Settings/NewGame/prologue, then exit; no combat/AV approval")
    parser.add_argument("--quality", type=int, choices=[0,1], default=1)
    parser.add_argument("--width", type=int, choices=[960,1280], default=960)
    parser.add_argument("--height", type=int, choices=[600,800], default=600)
    parser.add_argument("--raster-threads",type=int,choices=[1,3],default=1,
                        help="Requested LP_NUM_THREADS for software rasterization; match before/after (not observed worker count)")
    parser.add_argument("--output", type=Path, default=ROOT / "build/art-review/combat-continuity")
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--xvfb", type=Path, help="Optional extracted Xvfb; local-only dummy Xorg is the default")
    parser.add_argument("--wall-timeout", type=int, default=3600, help="Per import/take wall resource budget, independent of logical movie duration")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.candidate_project = args.candidate_project.resolve()
    args.godot = args.godot.resolve()
    args.frames = args.seconds * FPS
    if args.ui_geometry_probe and args.ui_route_probe:
        parser.error("Choose one bounded UI diagnostic mode")
    if args.include_heavy and args.scenario!="continuity":
        parser.error("--include-heavy requires the full continuity scenario")
    if (args.width,args.height) not in [(960,600),(1280,800)] or not 120 <= args.wall_timeout <= 7200:
        parser.error("Use960x600 or1280x800 and120–7200s per-process wall resource limit")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("A fresh output directory is required; prior evidence is never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    labels = ("before", "after") if args.take == "both" else (args.take,)
    takes = {label: prepare_take(args, label) for label in labels}
    manifest = {"status": "prepared_only_no_engine_or_server_launched", "scope": SCOPE,
                "scenario":next(iter(takes.values()))["config"]["scenario"],"include_heavy":args.include_heavy,
                "capture_policy":next(iter(takes.values()))["config"]["capture_policy"],
                "takes": {label: {key: value for key, value in take.items() if key != "frozen_inputs"}
                          for label, take in takes.items()}, "runner_sha256": sha(Path(__file__)),
                "godot": str(args.godot), "capture_requested": args.capture,"raster_profile":raster_profile(args.raster_threads),
                "baseline_repository_checkout_unchanged": True,
                "reference": "https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html"}
    write_json(args.output / "prepared.json", manifest)
    print(json.dumps({"status": manifest["status"], "output": str(args.output), "takes": list(takes)}), flush=True)
    if args.capture:
        capture(args, takes)


if __name__ == "__main__":
    main()
