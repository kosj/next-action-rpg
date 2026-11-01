"""Offline Godot MovieMaker 1x comparison, separate from interactive/gameplay QA.

Default is preparation only. --capture launches an isolated local-only dummy
Xorg and pinned Godot; coordinate the software-rendering CPU slot first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "game"
FPS = 60
SCOPE = ("Silent offline neutral Godot presentation comparison at logical 1x; "
         "actual ActorVisual/SkeletalVisualBridge, prescribed open-space actor "
         "travel, no interactive combat/contact/collision/audio listening, "
         "hardware performance or AAA approval.")
XORG_CONFIG = '''Section "ServerFlags"
    Option "AutoAddDevices" "false"
    Option "AutoEnableDevices" "false"
    Option "AllowMouseOpenFail" "true"
    Option "DontVTSwitch" "true"
EndSection
Section "Device"
    Identifier "ReviewDummy"
    Driver "dummy"
    VideoRam 256000
EndSection
Section "Monitor"
    Identifier "ReviewMonitor"
    HorizSync 5.0-1000.0
    VertRefresh 5.0-200.0
    Modeline "1280x720" 74.50 1280 1344 1472 1664 720 723 728 748
EndSection
Section "Screen"
    Identifier "ReviewScreen"
    Device "ReviewDummy"
    Monitor "ReviewMonitor"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1280x720"
        Virtual 1280 720
    EndSubSection
EndSection
Section "ServerLayout"
    Identifier "ReviewLayout"
    Screen "ReviewScreen"
EndSection
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resource_path(path: Path) -> str:
    path = path.resolve()
    return "res://" + path.relative_to(GAME).as_posix()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def run_logged(command: list[str], log: Path, env: dict[str, str], timeout=600) -> None:
    process = None
    with log.open("w") as stream:
        try:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            code = process.wait(timeout=timeout)
            if code:
                raise RuntimeError(f"Command exit {code}; see {log}")
        finally:
            stop_process(process)


def probe(path: Path) -> dict:
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_frames", "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,duration",
        "-of", "json", str(path)], timeout=60)
    return json.loads(raw)["streams"][0]


def start_xorg(output: Path, env: dict[str, str], xvfb: Path | None = None) -> tuple[subprocess.Popen, str]:
    number = next((n for n in range(95, 116)
                   if not Path(f"/tmp/.X{n}-lock").exists()
                   and not Path(f"/tmp/.X11-unix/X{n}").exists()), None)
    if number is None:
        raise RuntimeError("No private unused local X display")
    display = f":{number}"
    config = output / "xorg.conf"
    config.write_text(XORG_CONFIG)
    command = ([str(xvfb.resolve()), display, "-screen", "0", "1280x720x24", "-noreset", "-nolisten", "tcp"]
               if xvfb is not None else ["/usr/lib/xorg/Xorg", display, "-config", str(config), "-noreset",
               "-nolisten", "tcp", "-novtswitch", "-logfile", str(output / "xorg.log")])
    # TCP is explicitly disabled. The process only exposes its local Unix
    # socket and is always stopped by the caller's finally block.
    with (output / "xorg-process.log").open("w") as stream:
        process = subprocess.Popen(command, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Private X server failed; see {output / 'xorg-process.log'}")
            try:
                result = subprocess.run(["xdpyinfo", "-display", display], env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
            except subprocess.TimeoutExpired:
                continue
            if result.returncode == 0:
                return process, display
            time.sleep(0.1)
        raise RuntimeError("Private Xorg did not become ready in 10 seconds")
    except BaseException:
        stop_process(process)
        raise


def private_project(output: Path) -> Path:
    """Keep MovieMaker dimensions, user files and shader cache fixture-local.

    Source/resource links are read-only inputs to this normal runtime launch;
    do not run an editor/importer against their symlinked asset directories.
    Already imported native resources and the class cache are reused locally.
    """
    project = output / "project"
    project.mkdir(exist_ok=True)
    for source in GAME.iterdir():
        if source.name in ["project.godot", ".godot"]:
            continue
        target = project / source.name
        if not target.exists():
            target.symlink_to(source, target_is_directory=source.is_dir())
    text = (GAME / "project.godot").read_text()
    replacements = {"config/name":'"RUNEFALL Offline Weight Review"',
        "window/size/viewport_width":"1280", "window/size/viewport_height":"720",
        "window/size/window_width_override":"1280", "window/size/window_height_override":"720",
        "window/stretch/mode":'"disabled"'}
    for key, value in replacements.items():
        text, count = re.subn(r"^"+re.escape(key)+r"=.*$", key+"="+value, text, flags=re.M)
        if count != 1:
            raise ValueError("Unexpected source project setting: "+key)
    (project/"project.godot").write_text(text)
    cache = project/".godot"
    cache.mkdir(exist_ok=True)
    for name in ["global_script_class_cache.cfg", "uid_cache.bin"]:
        source = GAME/".godot"/name
        if source.exists():
            shutil.copy2(source, cache/name)
    imported = cache/"imported"
    imported.mkdir(exist_ok=True)
    for source in (GAME/".godot/imported").iterdir():
        target = imported/source.name
        if not target.exists():
            target.symlink_to(source)
    write_json(output/"fixture-project.json", {"scope":"Offline project settings only, no existing source edits",
        "source_project_sha256":sha(GAME/"project.godot"), "fixture_project_sha256":sha(project/"project.godot"),
        "overrides":replacements,"import_policy":"Normal runtime only, no editor/import of source symlink directories"})
    return project


def make_config(args: argparse.Namespace, profile: str) -> dict:
    hero = profile == "hero"
    before = (args.before_hero if hero else args.before_sentinel).resolve()
    after = (args.after_hero if hero else args.after_sentinel).resolve()
    frames = 162 if hero else 84
    models = [before, after, GAME / "assets/models/production/rune_sword_web.glb"]
    if hero:
        models.append(GAME / "assets/models/production/lyra_eyes.glb")
    source_paths = models + [
        GAME / "scripts/actors/actor_visual.gd", GAME / "scripts/actors/skeletal_visual_bridge.gd",
        GAME / "scripts/actors/production_character_art.gd", GAME / "data/character_grips.json",
        GAME / "import/impact_animation_sampling.gd", GAME / "import/eye_materials.gd",
        GAME / "tests/weight_motion_review.gd", GAME / "tests/weight_motion_review.tscn", Path(__file__)]
    for model in models:
        sidecar = Path(str(model)+".import")
        source_paths.append(sidecar)
        if sidecar.exists():
            match = re.search(r'^path="res://([^"\n]+)"', sidecar.read_text(), flags=re.M)
            if match:
                source_paths.append(GAME/match.group(1))
        for image in sorted(model.parent.glob(model.stem+"_Image_*.png")):
            source_paths.extend([image, Path(str(image)+".import")])
    source_paths = list(dict.fromkeys(source_paths))
    inputs = [{"source_path": str(p.relative_to(ROOT)), "sha256":sha(p) if p.exists() else None,
               "bytes":p.stat().st_size if p.exists() else None} for p in source_paths]
    if args.capture and any(item["sha256"] is None for item in inputs):
        raise FileNotFoundError("Capture requires every frozen input: " + str(inputs))
    return {"profile":profile, "before":resource_path(before), "after":resource_path(after),
            "frames":frames, "fps":FPS, "logical_speed":1.0, "scope":SCOPE,
            "snapshot":str(args.output / (profile + "-frames.json")), "source_inputs":inputs}


def transcode(args: argparse.Namespace, profile: str, config: dict, env: dict[str, str]) -> dict:
    raw = args.output / (profile + ".avi")
    movie = args.output / (profile + "-1x.mp4")
    if config.get("mode") == "arm_strip":
        # These discontinuous subframe seeks are exported only as stills,
        # never presented as normal-speed motion or included in the1x video.
        # MovieMaker PNGs preserve the actual raster losslessly for skin audit.
        raw_pngs = sorted((args.output/(profile+"-frames")).glob("*.png"))
        if len(raw_pngs) < 5:
            raise RuntimeError("MovieMaker did not write all five actual PNG poses")
        for index,source in enumerate(raw_pngs[:5]):
            shutil.copy2(source,args.output/(profile+f"-{index+1:02d}.png"))
        sheet = args.output/(profile+"-static-strip.png")
        run_logged(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-start_number", "1",
            "-i", str(args.output/(profile+"-%02d.png")), "-vf", "scale=640:360,tile=5x1",
            "-frames:v", "1", "-threads", "1", str(sheet)],
            args.output/(profile+"-strip.log"), env)
        stills = [{"path":str((args.output/(profile+f"-{index+1:02d}.png")).relative_to(ROOT)),
                   "charged_elapsed_s":time_value,
                   "sha256":sha(args.output/(profile+f"-{index+1:02d}.png"))}
                  for index,time_value in enumerate(config["review_times_s"])]
        return {"scope":"Five actual-skin static subframe seeks, effects off; not sequential1x motion or gameplay/AAA approval",
                "logical_speed":None,"lossless_actual_raster":True,"raw_png_frames":len(raw_pngs),"stills":stills,
                "static_strip":{"path":str(sheet.relative_to(ROOT)),"sha256":sha(sheet)}}
    raw_probe = probe(raw)
    if raw_probe["r_frame_rate"] != "60/1" or int(raw_probe["nb_read_frames"]) < config["frames"]:
        raise RuntimeError("MovieMaker did not write the required fixed60Hz frames")
    # A quit/drain frame may duplicate the final pose. Retain exactly the
    # prescribed forward-playback frames without any speed/time interpolation.
    run_logged(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(raw), "-an",
        "-frames:v", str(config["frames"]), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-threads", "1", "-movflags", "+faststart", str(movie)],
        args.output / (profile + "-ffmpeg.log"), env)
    final_probe = probe(movie)
    if final_probe["r_frame_rate"] != "60/1" or int(final_probe["nb_read_frames"]) != config["frames"]:
        raise RuntimeError("Final video changed the prescribed frame count/rate")
    moments = ([0.0, .93, 1.0, 1.34, 1.43, 1.52, 1.78, 2.06, 2.4] if profile == "hero"
               else [0.0, .30, .35, .45, .54, .65, .78, .86, 1.2])
    selected = sorted(set(round(t*FPS) for t in moments))
    select = "+".join(f"eq(n\\,{frame})" for frame in selected)
    sheet = args.output / (profile + "-contact-sheet.png")
    run_logged(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(movie),
        "-vf", f"select={select},scale=640:360,tile=3x3", "-frames:v", "1", "-threads", "1", str(sheet)],
        args.output / (profile + "-sheet.log"), env)
    return {"scope":SCOPE, "raw":raw_probe, "final":final_probe,
            "movie":{"path":str(movie.relative_to(ROOT)),"bytes":movie.stat().st_size,"sha256":sha(movie)},
            "contact_sheet":{"path":str(sheet.relative_to(ROOT)),"sha256":sha(sheet),"source_frames":selected},
            "raw_extra_quit_frames_removed":int(raw_probe["nb_read_frames"])-config["frames"],
            "speed_change":False,"audio_in_final_movie":False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=["hero", "sentinel_melee", "both"], default="both")
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--xvfb", type=Path, help="Optional workspace-extracted Xvfb executable fallback; never installs system packages")
    parser.add_argument("--before-hero", type=Path, default=GAME/"assets/models/production/lyra_impact_gameplay.glb")
    parser.add_argument("--after-hero", type=Path, default=GAME/"assets/models/production/lyra_weight_gameplay.glb")
    parser.add_argument("--before-sentinel", type=Path, default=GAME/"assets/models/production/sentinel_impact_gameplay.glb")
    parser.add_argument("--after-sentinel", type=Path, default=GAME/"assets/models/production/sentinel_weight_gameplay.glb")
    parser.add_argument("--capture", action="store_true", help="Launch actual software-render capture; coordinate CPU slot first")
    parser.add_argument("--arm-strip", action="store_true", help="Also export five enlarged static charged subframe pose comparisons; not1x motion")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    profiles = ["hero", "sentinel_melee"] if args.profile == "both" else [args.profile]
    output_keys = profiles+(["hero-arms"] if args.arm_strip else [])
    if any((args.output/(profile+".avi")).exists() or any((args.output/(profile+"-frames")).glob("*.png")) for profile in output_keys):
        raise ValueError("A new capture output directory is required")
    configs = {profile:make_config(args, profile) for profile in profiles}
    if args.arm_strip:
        config = make_config(args, "hero")
        config.update({"mode":"arm_strip", "frames":5, "logical_speed":None,
            "scope":"Actual imported-skin static subframe bridge seeks, effects off; not1x motion, gameplay or AAA approval",
            "review_times_s":[.4667,.475,.478,.480,.4833],
            "snapshot":str(args.output/"hero-arms-frames.json")})
        configs["hero-arms"] = config
    for profile, config in configs.items():
        write_json(args.output/(profile+"-config.json"), config)
    (args.output/"xorg.conf").write_text(XORG_CONFIG)
    if not args.capture:
        print(json.dumps({"status":"prepared_only_no_engine_or_server_launched", "output":str(args.output),
                          "pending_inputs":[item["source_path"] for config in configs.values()
                                            for item in config["source_inputs"] if item["sha256"] is None]}))
        return
    env = dict(os.environ)
    env.update({"LIBGL_ALWAYS_SOFTWARE":"1", "GALLIUM_DRIVER":"llvmpipe", "LP_NUM_THREADS":"1",
                "OMP_NUM_THREADS":"1", "OPENBLAS_NUM_THREADS":"1", "GODOT_SILENCE_ROOT_WARNING":"1",
                "XDG_CACHE_HOME":"/workspace/.runefall-toolchain/cache",
                "XDG_CONFIG_HOME":"/workspace/.runefall-toolchain/config",
                "XDG_DATA_HOME":"/workspace/.runefall-toolchain/data"})
    project = private_project(args.output)
    server = None
    results = {}
    try:
        run_logged([str(args.godot.resolve()), "--headless", "--path", str(project),
            "--script", "res://tests/weight_motion_review.gd", "--check-only"],
            args.output/"fixture-parse.log", env, timeout=120)
        server, env["DISPLAY"] = start_xorg(args.output, env, args.xvfb)
        for profile, config in configs.items():
            movie_path = args.output/(profile+".avi")
            if config.get("mode") == "arm_strip":
                png_directory = args.output/(profile+"-frames")
                png_directory.mkdir(exist_ok=True)
                movie_path = png_directory/"frame.png"
            command = [str(args.godot.resolve()), "--path", str(project), "--scene", "res://tests/weight_motion_review.tscn",
                "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                "--audio-driver", "Dummy", "--resolution", "1280x720", "--windowed", "--single-window",
                "--fixed-fps", "60", "--disable-vsync", "--write-movie", str(movie_path),
                "--", str(args.output/(profile+"-config.json"))]
            run_logged(command, args.output/(profile+"-godot.log"), env)
            snapshot = json.loads(Path(config["snapshot"]).read_text())
            if len(snapshot["frames"]) != config["frames"] or snapshot["engine_time_scale"] != 1.0:
                raise RuntimeError("Actual fixture snapshot does not match prescribed1x frames")
            for item in config["source_inputs"]:
                if sha(ROOT/item["source_path"]) != item["sha256"]:
                    raise RuntimeError("Source changed during capture: "+item["source_path"])
            results[profile] = transcode(args, profile, config, env)
            write_json(args.output/"capture.json", {"scope":SCOPE,"profiles":results,"display_tcp_disabled":True,
                "display_server":{"path":str(args.xvfb.resolve()) if args.xvfb else "/usr/lib/xorg/Xorg",
                    "sha256":sha(args.xvfb if args.xvfb else Path("/usr/lib/xorg/Xorg"))},
                "godot_sha256":sha(args.godot), "official_reference":"https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html",
                "reference_check":"Installed pinned Godot --help confirms write-movie forces fixed-fps and supports quit-after. Online reference returned403 in this environment; no claim that its current text was retrieved."})
    finally:
        stop_process(server)
    print(json.dumps({"status":"captured_offline_1x_only", "output":str(args.output), "profiles":list(results)}))


if __name__ == "__main__":
    main()
