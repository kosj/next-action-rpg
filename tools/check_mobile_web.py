"""Serve the actual Web export below /web/ and run mobile touch emulation QA."""
import argparse
import asyncio
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
from urllib.parse import quote

from check_web import QuietHandler
from mobile_browser_smoke import run


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "build/verification/mobile")
    parser.add_argument("--web-dir", type=Path, default=root / "build/web",
                        help="Actual export directory; preliminary previews are separate from build/web")
    parser.add_argument("--phase",choices=["full","input-focus","multitouch-focus","lifecycle-focus","lifecycle-tail","settings-focus","rotation-focus","scroll-focus","narrow-focus","restart-focus","charged-heavy-focus"],default="full")
    parser.add_argument("--rotation-driver",choices=["double","playwright"],default="playwright",
                        help="Rotation-focus diagnostic only: compare existing duplicate CDP override with Playwright's native mobile rotation")
    args = parser.parse_args()
    web = args.web_dir.resolve()
    if not (web / "index.html").is_file():
        raise SystemExit("Build the final Web preset before mobile QA")
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = ["tools/mobile_browser_smoke.py", "tools/check_mobile_web.py", "tools/browser_smoke.py",
              "game/project.godot", "game/scripts/ui/touch_controls.gd", "game/scripts/ui/hud.gd",
              "game/scripts/actors/player.gd", "game/scripts/game.gd", "game/scripts/world/camera_rig.gd",
              "game/web/shell.html", "game/assets/models/production/lyra_impact_gameplay.glb",
              "game/assets/models/production/lyra_eyes.glb", "game/assets/models/production/sentinel_impact_gameplay.glb",
              "tools/charged_heavy_browser_smoke.py", "game/scripts/core/strike.gd", "game/scripts/core/attack_data.gd", "game/scripts/actors/enemy.gd",
              "game/data/charged_heavy.tres", "game/data/heavy.tres", "game/scripts/core/audio.gd",
              "game/import/impact_animation_sampling.gd",
              "game/assets/models/production/lyra_impact_gameplay.glb.import",
              "game/assets/models/production/sentinel_impact_gameplay.glb.import",
              "game/scripts/world/impact_effect.gd", "game/scripts/actors/actor_visual.gd",
              "game/scripts/actors/production_character_art.gd", "game/scripts/actors/skeletal_visual_bridge.gd",
              "tools/author_impact_actions.py", "tools/author_character_actions.py",
              "tools/generate_impact_audio.py", "tools/render_impact_review.py"]
    inputs.extend(str(path.relative_to(root)) for path in sorted((root/"game/assets/audio/impact").glob("*.wav")))
    context = {"scope": "Actual mobile test export bytes and contemporaneous source hashes; dirty previews are not a committed-source or final-release approval",
               "phase":args.phase,
               "rotation_driver":args.rotation_driver,
               "started_utc": datetime.now(timezone.utc).isoformat(),
               "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
               "source_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root)),
               "export_directory": str(web),
               "source_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs},
               "export_files": {file.name: {"bytes": file.stat().st_size,
                                           "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
                                for file in sorted(web.iterdir()) if file.is_file()}}
    (args.output/"mobile-export-context.json").write_text(json.dumps(context, indent=2)+"\n", encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(web.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    completed = False
    try:
        runner=run
        if args.phase=="charged-heavy-focus":
            from charged_heavy_browser_smoke import run as runner
        asyncio.run(runner(f"http://127.0.0.1:{server.server_port}/{quote(web.name)}/", args.output,args.phase,args.rotation_driver))
        completed = True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        context["server_closed"] = True
        context["finished_utc"] = datetime.now(timezone.utc).isoformat()
        context["export_bytes_unchanged"] = all(file.is_file() and file.stat().st_size == record["bytes"]
            and hashlib.sha256(file.read_bytes()).hexdigest() == record["sha256"]
            for name, record in context["export_files"].items() for file in [web/name])
        (args.output/"mobile-export-context.json").write_text(json.dumps(context, indent=2)+"\n", encoding="utf-8")
    if completed and not context["export_bytes_unchanged"]:
        result_file = args.output/("charged-heavy-result.json" if args.phase=="charged-heavy-focus" else "mobile-result.json")
        result = json.loads(result_file.read_text(encoding="utf-8"))
        result["outcome"] = "invalidated_changed_export"
        result_file.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        raise RuntimeError("Web export changed during the run; no consistent-build approval")


if __name__ == "__main__":
    main()
