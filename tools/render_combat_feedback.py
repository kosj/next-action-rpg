"""Render v0.1.19 combat-feedback review stills in the actual Game scene.

python tools/render_combat_feedback.py --output build/combat-feedback --quality 0 1

Uses a private Xvfb display and Mesa llvmpipe with the Compatibility renderer
(the Web renderer). The stills are a finite staged visual review: they are not
normal-input gameplay, continuous AV, target-device performance or AAA approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCENE = "res://tests/combat_feedback_capture.tscn"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def free_display() -> str:
    for number in range(95, 130):
        if not Path(f"/tmp/.X{number}-lock").exists() and not Path(f"/tmp/.X11-unix/X{number}").exists():
            return f":{number}"
    raise RuntimeError("No unused local X display")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/combat-feedback")
    parser.add_argument("--quality", type=int, nargs="+", choices=(0, 1), default=[0, 1])
    parser.add_argument("--godot", default=os.environ.get("GODOT_BIN", "godot"))
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    display = free_display()
    env = dict(os.environ)
    env.update({"LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe", "DISPLAY": display,
                "GODOT_SILENCE_ROOT_WARNING": "1"})
    server = subprocess.Popen(["Xvfb", display, "-screen", "0", "1280x720x24", "-nolisten", "tcp", "-noreset"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    summary = {"scope": "Staged finite stills in the actual Game scene; Xvfb + llvmpipe Compatibility renderer. "
                        "Not normal-input gameplay, continuous AV, device performance or AAA approval.",
               "runs": []}
    try:
        time.sleep(1.0)
        for quality in args.quality:
            log = output / f"capture_q{quality}.log"
            command = [args.godot, "--path", str(ROOT / "game"), "--scene", SCENE,
                       "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                       "--audio-driver", "Dummy", "--resolution", "960x600", "--windowed", "--fixed-fps", "60",
                       "--disable-vsync", "--", str(output), str(quality)]
            with log.open("w") as stream:
                result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
            text = log.read_text(errors="replace")
            errors = re.findall(r"(?:SCRIPT ERROR:|ERROR:).*", text)
            pngs = sorted(output.glob(f"*_q{quality}.png"))
            summary["runs"].append({"quality": quality, "exit": result.returncode, "errors": errors[:20],
                                    "pngs": [{"path": p.name, "sha256": sha(p)} for p in pngs]})
            print(json.dumps({"quality": quality, "exit": result.returncode, "errors": len(errors), "pngs": len(pngs)}))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return 0 if all(run["exit"] == 0 and not run["errors"] for run in summary["runs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
