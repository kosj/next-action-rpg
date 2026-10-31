"""Render unchanged skinned GLB head/face/wrist regions for human review.

blender -b --factory-startup --python tools/review_character_regions.py -- \
  --input game/assets/models/production/lyra_gameplay.glb \
  --output build/art-review/character-polish/lyra-regions-001

Source geometry, materials, weights, animation and files remain unchanged.
This is a neutral REST studio review, not a gameplay or AAA approval.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_glb_review as shared


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--overlay", type=Path, help="Reimport a separately exported Head-local eye GLB")
    parser.add_argument("--overlay-fit", type=Path)
    parser.add_argument("--reference-review", type=Path, help="Reuse exact camera transforms for matching shot names")
    parser.add_argument("--head-yaw-degrees", type=float, default=0)
    parser.add_argument("--head-pitch-degrees", type=float, default=0)
    parser.add_argument("--shots", nargs="+", choices=["head_front", "face_front", "head_three_quarter", "face_side", "right_wrist"],
                        default=["head_front", "face_front", "head_three_quarter", "right_wrist"])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not 128 <= args.size <= 2048 or not 1 <= args.samples <= 128:
        parser.error("size must be128..2048; samples1..128")
    if bool(args.overlay) != bool(args.overlay_fit):
        parser.error("--overlay and --overlay-fit must be provided together")
    if any(not math.isfinite(v) or abs(v) > 45 for v in [args.head_yaw_degrees, args.head_pitch_degrees]):
        parser.error("Review head yaw/pitch must be finite and within45degrees")
    return args


def mesh_points(objects, graph):
    result = []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            result.extend((obj.name, vertex.index, evaluated.matrix_world @ vertex.co)
                          for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not result or not all(math.isfinite(v) for _, _, point in result for v in point):
        raise ValueError("No finite evaluated source mesh points")
    return result


def region(points, predicate):
    selected = [(name, index, point) for name, index, point in points if predicate(point)]
    if not selected:
        raise ValueError("Region selection is empty")
    lower = Vector(tuple(min(point[a] for _, _, point in selected) for a in range(3)))
    upper = Vector(tuple(max(point[a] for _, _, point in selected) for a in range(3)))
    return selected, lower, upper, (lower + upper) / 2


def overlay_distances(body_objects, eye_objects, graph):
    vertices, triangles = [], []
    for obj in body_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            offset = len(vertices)
            vertices.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
            triangles.extend(tuple(offset+i for i in triangle.vertices) for triangle in mesh.loop_triangles)
        finally:
            evaluated.to_mesh_clear()
    bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    signed, distances = [], []
    for obj in eye_objects:
        if obj.type != "MESH":
            continue
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            nearest, normal, _, distance = bvh.find_nearest(point)
            if nearest is None:
                raise ValueError("Candidate-to-source BVH lookup failed")
            signed.append((point-nearest).dot(normal))
            distances.append(distance)
    if not distances:
        raise ValueError("Candidate reimport contains no vertices")
    return {"method": "BVH nearest actual reimported eye vertices to actual evaluated source-body triangles",
            "vertex_samples": len(distances), "nearest_distance_min_m": min(distances),
            "nearest_distance_max_m": max(distances), "signed_outward_min_m": min(signed),
            "signed_outward_max_m": max(signed), "penetrating_vertex_count": sum(v < -1e-5 for v in signed)}


def main():
    args = arguments()
    if not bpy.app.background:
        raise ValueError("Run in an isolated background Blender process")
    source = args.input.resolve(strict=True)
    output = args.output.resolve()
    if source.suffix.lower() != ".glb":
        raise ValueError("Expected a self-contained GLB")
    if output == source or output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output must be a separate new or empty directory")
    document = shared.read_glb(source)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
    imported = list(bpy.context.scene.objects)
    helpers = {bone.custom_shape for obj in imported if obj.type == "ARMATURE"
               for bone in obj.pose.bones if bone.custom_shape is not None}
    for obj in helpers:
        obj.hide_render = True
    imported = [obj for obj in imported if obj not in helpers]
    for obj in imported:
        obj.animation_data_clear()
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
        elif obj.type in {"LIGHT", "CAMERA"}:
            obj.hide_render = True
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise ValueError("Review expects one armature")
    armature = armatures[0]
    for name in ["Head", "RightHand"]:
        if name not in armature.data.bones:
            raise ValueError("Required named landmark is absent: " + name)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    lower, upper, dimensions, center, _ = shared.asset_bounds(imported, graph)
    height = dimensions.z
    if height <= 0:
        raise ValueError("Invalid upright mesh height")
    landmarks = {name: armature.matrix_world @ armature.data.bones[name].head_local
                 for name in ["Head", "RightHand"]}
    points = mesh_points(imported, graph)
    head = landmarks["Head"]
    hand = landmarks["RightHand"]
    # Spatial selections crop actual evaluated mesh; no source vertex is edited.
    # Limits are explicitly recorded as fractions of actual mesh height so a
    # camera can be reproduced and inspected rather than assumed anatomical.
    head_predicate = lambda p: (head.z - height * .045 <= p.z <= head.z + height * .15
                                and abs(p.x - head.x) <= height * .105)
    face_predicate = lambda p: (head.z - height * .025 <= p.z <= head.z + height * .082
                                and abs(p.x - head.x) <= height * .055
                                and p.y <= head.y + height * .012)
    wrist_predicate = lambda p: (p - hand).length <= height * .085
    regions = {"head": region(points, head_predicate), "face": region(points, face_predicate),
               "right_wrist": region(points, wrist_predicate)}
    eye_objects = []
    eye_roots = []
    overlay_report = None
    overlay_fit = None
    head_rest_world = armature.matrix_world @ armature.pose.bones["Head"].matrix.copy()
    if args.overlay:
        overlay_fit = json.loads(args.overlay_fit.read_text())
        overlay_sha = hashlib.sha256(args.overlay.read_bytes()).hexdigest()
        if overlay_fit["source"]["sha256"] != source_sha or overlay_fit["candidate"]["sha256"] != overlay_sha:
            raise ValueError("Overlay fit/source/candidate hashes disagree")
        overlay_document = shared.read_glb(args.overlay)
        if overlay_document.get("skins") or overlay_document.get("animations"):
            raise ValueError("Expected independent unskinned Head-local geometry")
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(args.overlay.resolve()), import_pack_images=True)
        eye_objects = [o for o in bpy.context.scene.objects if o not in before]
        eye_roots = [o for o in eye_objects if o.parent not in eye_objects]
        # Imported geometry is already transformed from glTF Y-up into Blender
        # Z-up. Conjugate the ORIGINAL glTF Head basis exactly once.
        convert = Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
        head_rigid = Matrix(overlay_fit["attachment_contract"]["source_head_rest_rigid_world_matrix_y_up"])
        placement = convert @ head_rigid @ convert.inverted()
        for obj in eye_roots:
            obj.matrix_world = placement @ obj.matrix_world
        bpy.context.view_layer.update()
        overlay_report = {"path": str(args.overlay), "sha256": overlay_sha,
                          "fit_path": str(args.overlay_fit), "actually_reimported_glb": True,
                          "placement_matrix_blender": [list(row) for row in placement],
                          "source_gltf_rigid_head_basis_used": True,
                          "root_matrices_rest_blender": {o.name:[list(row) for row in o.matrix_world] for o in eye_roots}}
    eye_rest_world = {o:o.matrix_world.copy() for o in eye_roots}
    if args.head_yaw_degrees or args.head_pitch_degrees:
        armature.data.pose_position = "POSE"
        pivot = head_rest_world.translation
        rotation = Matrix.Rotation(math.radians(args.head_yaw_degrees), 4, "Z") @ Matrix.Rotation(math.radians(args.head_pitch_degrees), 4, "X")
        target_world = Matrix.Translation(pivot) @ rotation @ Matrix.Translation(-pivot) @ head_rest_world
        armature.pose.bones["Head"].matrix = armature.matrix_world.inverted() @ target_world
        bpy.context.view_layer.update()
        delta = (armature.matrix_world @ armature.pose.bones["Head"].matrix) @ head_rest_world.inverted()
        for obj in eye_roots:
            obj.matrix_world = delta @ eye_rest_world[obj]
        bpy.context.view_layer.update()
    if eye_objects:
        clearance = overlay_distances(imported, eye_objects, bpy.context.evaluated_depsgraph_get())
        clearance["within_declared_clearance_limit"] = clearance["nearest_distance_max_m"] <= overlay_fit["fitting"]["maximum_front_direction_offset_m"] + .0003
        clearance["nonpenetrating"] = clearance["penetrating_vertex_count"] == 0
        overlay_report["clearance"] = clearance
        overlay_report["pose_matrices_blender"] = {o.name:[list(row) for row in o.matrix_world] for o in eye_roots}
    reference = json.loads(args.reference_review.read_text()) if args.reference_review else None
    scene = shared.configure_scene(args.size, args.samples)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.cycles.seed = 0
    shared.neutral_floor(center, lower.z - height * .002, height)
    camera_data = bpy.data.cameras.new("_RegionCamera")
    camera_data.type = "ORTHO"
    camera_data.clip_start = .001
    camera_data.clip_end = max(height * 20, 100)
    camera = bpy.data.objects.new("_RegionCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    direction = Vector((0, -1, 0))
    right = Vector((1, 0, 0))
    lights = []
    for name, power, width, offset in [
        ("_NeutralKey", 500, 1.5, (-1.5, 2.2, 2.3)),
        ("_NeutralFill", 250, 2, (2, 1.5, 1.2)),
        ("_NeutralRim", 650, 1.2, (0, -2, 2)),
    ]:
        light = shared.area_light(name, power * height * height, width * height)
        light.location = center + right * offset[0] * height + direction * offset[1] * height + Vector((0, 0, offset[2] * height))
        shared.aim(light, center)
        lights.append(light)
    settings = {
        "head_front": ("head", Vector((0, -1, 0)), 1.12),
        "face_front": ("face", Vector((0, -1, 0)), 1.15),
        "head_three_quarter": ("head", Vector((.58, -.815, .025)).normalized(), 1.12),
        "face_side": ("face", Vector((1, -.06, .015)).normalized(), 1.2),
        "right_wrist": ("right_wrist", Vector((.30, -.88, .36)).normalized(), 1.15),
    }
    views = []
    for name in args.shots:
        region_name, direction, margin = settings[name]
        selected, lo, hi, target = regions[region_name]
        corners = [Vector((x, y, z)) for x in [lo.x, hi.x] for y in [lo.y, hi.y] for z in [lo.z, hi.z]]
        camera.location = target + direction * height * 3
        shared.aim(camera, target)
        rotation = camera.rotation_euler.to_matrix()
        camera_right, camera_up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
        projected_x = [(p - target).dot(camera_right) for p in corners]
        projected_y = [(p - target).dot(camera_up) for p in corners]
        camera_data.ortho_scale = max(max(projected_x) - min(projected_x), max(projected_y) - min(projected_y)) * margin
        match = next((v for v in reference["views"] if v["shot"] == name), None) if reference else None
        if match:
            camera.location = match["camera_position_blender"]
            camera.rotation_euler = match["camera_rotation_euler"]
            camera_data.ortho_scale = match["orthographic_scale_m"]
        scene.render.filepath = str(output / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        if not Path(scene.render.filepath).is_file():
            raise RuntimeError("Missing region render: " + name)
        views.append({"shot": name, "file": name + ".png", "region": region_name,
                      "camera_position_blender": list(camera.location), "camera_rotation_euler": list(camera.rotation_euler),
                      "target_blender": list(target), "orthographic_scale_m": camera_data.ortho_scale,
                      "camera_reused_from_reference": bool(match),
                      "selected_vertex_count": len(selected), "region_min_blender": list(lo), "region_max_blender": list(hi),
                      "image_sha256": hashlib.sha256(Path(scene.render.filepath).read_bytes()).hexdigest()})
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha:
        raise RuntimeError("Source changed during region review")
    metadata = shared.imported_metadata(imported, document)
    report = {"status": "rendered_for_human_review", "automatic_visual_approval": False,
              "generated_at_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string,
              "source": {"path": str(source), "sha256": source_sha, "bytes": source.stat().st_size, "unchanged": True},
              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "shared_renderer_sha256": hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
              "render": {"engine": "CYCLES", "device": "CPU", "threads": 1, "size": args.size,
                         "samples": args.samples, "pose": "Head-only review pose" if args.head_yaw_degrees or args.head_pitch_degrees else "REST", "denoising": False,
                         "head_yaw_degrees": args.head_yaw_degrees, "head_pitch_degrees": args.head_pitch_degrees,
                         "color_management": "AgX / Base Contrast", "source_geometry_materials_modified": False},
              "bounds_blender_z_up": {"min": list(lower), "max": list(upper), "height": height},
              "landmarks_blender_z_up": {k: list(v) for k, v in landmarks.items()},
              "region_selection": {"head": "Head.z +[-.045,.15]*height; abs(x-Head.x)<=.105*height",
                                   "face": "Head.z +[-.025,.082]*height; abs(x-Head.x)<=.055*height; y<=Head.y+.012*height",
                                   "right_wrist": "distance to RightHand<=.085*height"},
              "excluded_importer_bone_display_helpers": sorted(o.name for o in helpers),
              "asset": metadata, "images": [{"name": i.name, "pixels": list(i.size)} for i in bpy.data.images if i.type != "RENDER_RESULT"],
              "overlay": overlay_report,
              "lights": [{"name": l.name, "position": list(l.location), "energy_w": l.data.energy,
                          "size_m": l.data.size} for l in lights], "views": views,
              "limitations": ["Unchanged source in a neutral REST studio; not an actual gameplay capture or AAA approval",
                              "Spatial region bounds are source-specific camera framing, not anatomical segmentation",
                              "Texture pixels, sculpt, eye/hair geometry and deformation need human closeup inspection"]}
    with (output / "review.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("CHARACTER_REGIONS_OK", output, flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as error:
        if error.code:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(int(error.code))
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
