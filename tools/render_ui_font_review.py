"""Prepare/capture a minimal matched native Godot UI-font raster experiment.

Default prepares only new private files. --capture requires a coordinated
exclusive local render slot. Only the two fonts, mirrored import settings and
the isolated fixture are copied; no production project, save or import cache is
modified. Pinned Godot, private XDG, local-only Xorg and bounded subprocesses
are used. Raw PNGs are retained unchanged. Pixel/layout differences are
measurements for review, not implicit approval; PCK/Web budgets remain pending.
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

from render_weight_review import run_logged, start_xorg, stop_process

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252"
CANDIDATE = "038bb3e475466a2ffec9b78acc4d0d6ca10b558a02214e371fe7f7993eb609b3"
FONTS = ("NotoSansKR.ttf", "runefall_kr430.ttf")
FIXTURES = ("ui_font_review.gd", "ui_font_review.tscn")
SCOPE = ("Isolated real Godot Control/TextServer original variable430 vs complete static430 "
         "raster/layout measurements. Not actual Game/browser UI, hardware, PCK or export approval.")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def prepare(output: Path):
    if output.exists() or output.is_symlink():
        raise ValueError("Use a new, nonexistent output directory")
    source = ROOT / "game/assets/fonts" / FONTS[0]
    candidate = ROOT / "game/assets/fonts" / FONTS[1]
    if (sha(source), sha(candidate)) != (SOURCE, CANDIDATE):
        raise ValueError("Font source/candidate does not match the reviewed complete derivation")
    import_source = source.with_suffix(source.suffix + ".import")
    import_text = import_source.read_text()
    if import_text.count("[params]") != 1:
        raise ValueError("Cannot mirror original font import parameters")
    parameters = import_text.split("[params]", 1)[1]
    output.mkdir(parents=True)
    project = output / "project"
    font_directory = project / "assets/fonts"
    font_directory.mkdir(parents=True)
    (project / "tests").mkdir()
    inventory = {}
    for original in (source, candidate, import_source,
                     *(ROOT / "game/tests" / name for name in FIXTURES)):
        inventory[str(original.relative_to(ROOT))] = {"sha256": sha(original), "bytes": original.stat().st_size}
    for original in (source, candidate):
        target = font_directory / original.name
        shutil.copyfile(original, target)
        resource = "res://assets/fonts/" + original.name
        imported = f"res://.godot/imported/{original.name}-{hashlib.md5(resource.encode()).hexdigest()}.fontdata"
        # New private sidecars use identical source [params]; importer owns UIDs.
        target.with_suffix(target.suffix + ".import").write_text(
            '[remap]\nimporter="font_data_dynamic"\ntype="FontFile"\npath="' + imported +
            '"\n\n[deps]\nsource_file="' + resource + '"\ndest_files=["' + imported + '"]\n\n[params]' + parameters)
    for name in FIXTURES:
        shutil.copyfile(ROOT / "game/tests" / name, project / "tests" / name)
    (project / "project.godot").write_text('''config_version=5

[application]
config/name="RUNEFALL Isolated Font Review"
run/main_scene="res://tests/ui_font_review.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")

[display]
window/size/viewport_width=844
window/size/viewport_height=844
window/size/window_width_override=844
window/size/window_height_override=844
window/stretch/mode="disabled"
window/vsync/vsync_mode=0

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
environment/defaults/default_clear_color=Color(0.0431373,0.0705882,0.0941176,1)
''')
    write_json(output / "config.json", {"output_directory": str(output.resolve()),
                                        "result_path": str((output / "godot-review.json").resolve())})
    write_json(output / "source-inputs.json", inventory)
    write_json(output / "preparation.json", {"scope": SCOPE, "project": str(project.resolve()),
        "source_inputs": inventory, "mirrored_font_import_params": parameters,
        "fixture_only": True, "production_project_or_cache_copied": False})
    return project, inventory


def compare_values(a, b, path="", result=None):
    """Exact nested comparison with bounded examples and unrounded deltas."""
    if result is None:
        result = {"different_fields": 0, "maximum_numeric_delta": 0.0, "first_differences": []}
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        for key in a:
            compare_values(a[key], b[key], path + "." + key, result)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for number, (x, y) in enumerate(zip(a, b)):
            compare_values(x, y, f"{path}[{number}]", result)
    elif a != b:
        result["different_fields"] += 1
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            result["maximum_numeric_delta"] = max(result["maximum_numeric_delta"], abs(a - b))
        if len(result["first_differences"]) < 20:
            result["first_differences"].append({"path": path, "baseline": a, "candidate": b})
    return result


def pixel_difference(baseline: Path, candidate: Path):
    from PIL import Image, ImageChops
    with Image.open(baseline) as original, Image.open(candidate) as changed:
        if original.size != changed.size or original.mode != changed.mode:
            raise ValueError("Font raster dimensions/modes differ")
        a, b = original.convert("RGB"), changed.convert("RGB")
        if original.mode == "RGBA" and (original.getchannel("A").getextrema() != (255, 255)
                                         or changed.getchannel("A").getextrema() != (255, 255)):
            raise ValueError("Font raster comparison requires the fixture's fully opaque background")
        difference = ImageChops.difference(a, b)
        extrema = difference.getextrema()
        histogram = difference.histogram()
        channels = len(histogram) // 256
        total = sum((number % 256) * count for number, count in enumerate(histogram))
        pixels = difference.get_flattened_data() if hasattr(difference, "get_flattened_data") else difference.getdata()
        changed_pixels = sum(1 for pixel in pixels if any(pixel))
        width, height = a.size
        return {"size": [width, height], "pixels": width * height,
                "changed_pixels": changed_pixels, "changed_fraction": changed_pixels / (width * height),
                "maximum_channel_delta_0_255": max(high for low, high in extrema),
                "mean_absolute_channel_delta_0_255": total / (width * height * channels),
                "difference_bbox_xyxy": difference.getbbox(), "pixel_exact": changed_pixels == 0,
                "comparison": "Original unedited PNG RGB channels; no registration, scaling, masking or tolerance"}


def analyze(output: Path):
    report = json.loads((output / "godot-review.json").read_text())
    if report.get("status") != "isolated_font_raster_captured" or report.get("renderer") != "gl_compatibility":
        raise ValueError("Unexpected font fixture status/renderer")
    shots = {(shot["take"], *shot["viewport"], shot["size"]): shot for shot in report["shots"]}
    if len(shots) != 30 or len(report["shots"]) != 30:
        raise ValueError("Expected exactly fifteen matched before/after font raster pairs")
    glyphs = [glyph for shot in report["shots"] for text in shot["metrics"]["strings"]
              for glyph in text["shaped"]["glyphs"]]
    if not glyphs or any(not glyph["uses_requested_font"] or glyph["index"] == 0 for glyph in glyphs):
        raise ValueError("The fixture used a fallback font or a missing glyph")
    results = []
    for profile in report["profiles"]:
        for size in report["font_sizes"]:
            a, b = (shots[(take, *profile, size)] for take in ("variable430", "static430"))
            for shot in (a, b):
                if shot["image_size"] != profile:
                    raise ValueError("Actual SubViewport PNG size mismatch")
            numeric = compare_values({"font": a["metrics"], "controls": a["controls"]},
                                     {"font": b["metrics"], "controls": b["controls"]})
            paths = [output / shot["png"] for shot in (a, b)]
            results.append({"viewport": profile, "font_size": size,
                "layout": numeric, "layout_exact": numeric["different_fields"] == 0,
                "all_content_inside_viewport": a["content_bottom"] <= profile[1] and b["content_bottom"] <= profile[1],
                "content_bottom": [a["content_bottom"], b["content_bottom"]],
                "pixels": pixel_difference(*paths),
                "raw_pngs": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in paths]})
    return {"scope": SCOPE, "pairs": results,
            "shaped_glyph_records_checked": len(glyphs), "fallback_or_missing_glyphs": 0,
            "strict_layout_exact_all_pairs": all(x["layout_exact"] for x in results),
            "pixel_exact_all_pairs": all(x["pixels"]["pixel_exact"] for x in results),
            "all_content_inside_all_viewports": all(x["all_content_inside_viewport"] for x in results),
            "root_visual_adoption_decision": "pending", "pending": ["Actual Game/browser UI", "PCK/raw Web export budget"]}


def capture(args, project, inventory):
    result = {"status": "running", "scope": SCOPE, "processes_closed": False}
    env = dict(os.environ)
    env.update({"LP_NUM_THREADS": "2", "GODOT_SILENCE_ROOT_WARNING": "1"})
    for key, folder in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")):
        path = args.output / ("xdg-" + folder)
        path.mkdir()
        env[key] = str(path.resolve())
    server = None
    started = time.monotonic()
    try:
        version = subprocess.check_output([str(args.godot), "--version"], env=env, text=True, timeout=30).strip()
        required = json.loads((ROOT / "tools/toolchain.json").read_text())["godot_version"]
        if not version.startswith(required + ".stable."):
            raise ValueError("Pinned stable Godot " + required + " is required")
        result["engine"] = {"version": version, "binary_sha256": sha(args.godot)}
        run_logged([str(args.godot), "--headless", "--editor", "--path", str(project), "--quit"],
                   args.output / "import.log", env, args.wall_timeout)
        imported = {}
        for name in FONTS:
            imported_path = next((project / ".godot/imported").glob(name + "-*.fontdata"))
            sidecar = project / "assets/fonts" / (name + ".import")
            text = sidecar.read_text()
            if text.split("[params]", 1)[1] != json.loads((args.output / "preparation.json").read_text())["mirrored_font_import_params"]:
                raise ValueError("Importer changed mirrored font parameters")
            imported[name] = {"path": str(imported_path.relative_to(args.output)),
                              "bytes": imported_path.stat().st_size, "sha256": sha(imported_path),
                              "header_hex": imported_path.read_bytes()[:4].hex(), "import_sidecar_sha256": sha(sidecar)}
        result["actual_private_import_fontdata"] = imported
        if re.search(r"(?:SCRIPT ERROR:|ERROR:)", (args.output / "import.log").read_text()):
            raise RuntimeError("Font project import/parse reported an engine error")
        server, env["DISPLAY"] = start_xorg(args.output, env)
        result["display_tcp_disabled"] = True
        print(json.dumps({"stage": "font_actual_godot_raster", "pairs": 15}), flush=True)
        run_logged([str(args.godot), "--path", str(project), "--scene", "res://tests/ui_font_review.tscn",
                    "--display-driver", "x11", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                    "--audio-driver", "Dummy", "--resolution", "844x844", "--windowed", "--single-window", "--disable-vsync",
                    "--", str((args.output / "config.json").resolve())], args.output / "capture.log", env, args.wall_timeout)
        logs = (args.output / "capture.log").read_text()
        errors = [line for line in logs.splitlines() if "SCRIPT ERROR:" in line or line.startswith("ERROR:") or "leaked at exit" in line]
        if errors:
            raise RuntimeError("Font capture engine errors: " + "; ".join(errors))
        result["analysis"] = analyze(args.output)
        for name, item in inventory.items():
            if sha(ROOT / name) != item["sha256"]:
                raise RuntimeError("Original source/fixture changed during capture: " + name)
        for name, expected in zip(FONTS, (SOURCE, CANDIDATE)):
            if sha(project / "assets/fonts" / name) != expected:
                raise RuntimeError("Private font source changed during capture")
        result.update(status="actual_font_raster_measured_not_adoption_approved", source_inputs_unchanged=True,
                      engine_errors=[], warnings=[x for x in logs.splitlines() if x.startswith("WARNING:")])
    except BaseException as error:
        result.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        stop_process(server)
        result.update(processes_closed=True, elapsed_seconds=time.monotonic()-started)
        write_json(args.output / "capture.json", result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--godot", type=Path, default=Path("/workspace/.runefall-toolchain/godot"))
    parser.add_argument("--wall-timeout", type=int, default=180)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args(argv)
    args.output = args.output.resolve()
    args.godot = args.godot.resolve()
    project, inventory = prepare(args.output)
    print(json.dumps({"stage": "font_review_prepared", "output": str(args.output)}), flush=True)
    if args.capture:
        capture(args, project, inventory)


if __name__ == "__main__":
    main()
