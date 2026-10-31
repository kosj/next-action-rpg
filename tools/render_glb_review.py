"""Render an unchanged GLB in an isolated Blender 4.3.2 review scene.

blender -b --factory-startup --python tools/render_glb_review.py -- \
    --input game/assets/models/hero.glb --output build/art-review/hero

Output must be a new or empty directory. The source is never saved or rescaled.
This is a static rest-pose review, not an automated visual or animation approval.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--samples", type=int, default=16)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not 32 <= args.size <= 4096 or not 1 <= args.samples <= 1024:
        parser.error("size must be 32..4096 and samples 1..1024")
    return args


def read_glb(path):
    """Read the bounded JSON chunk only; Blender performs the actual mesh import."""
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError("Truncated GLB header")
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise ValueError("Expected a complete GLB v2 file")
        chunk_header = stream.read(8)
        if len(chunk_header) != 8:
            raise ValueError("Missing GLB JSON chunk")
        size, kind = struct.unpack("<I4s", chunk_header)
        if kind != b"JSON" or size > 16 * 1024 * 1024 or size + 20 > length:
            raise ValueError("Invalid or oversized GLB JSON chunk")
        document = json.loads(stream.read(size).decode("utf-8"))
    for resource in [*document.get("buffers", []), *document.get("images", [])]:
        uri = resource.get("uri", "")
        if uri and not uri.startswith("data:"):
            raise ValueError("Review requires a self-contained GLB; external resource URIs are not fetched")
    return document


def asset_bounds(objects, graph):
    points = []
    for obj in objects:
        if obj.type == "MESH" and not obj.hide_render and len(obj.data.vertices):
            evaluated = obj.evaluated_get(graph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise ValueError("GLB has no finite, renderable mesh bounds")
    lower = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    upper = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    size = upper - lower
    if max(size) < 1e-8:
        raise ValueError("GLB mesh bounds are degenerate")
    corners = [Vector((x, y, z)) for x in (lower.x, upper.x)
               for y in (lower.y, upper.y) for z in (lower.z, upper.z)]
    return lower, upper, size, (lower + upper) * 0.5, corners


def neutral_floor(center, floor_z, span):
    bpy.ops.mesh.primitive_plane_add(size=span * 12, location=(center.x, center.y, floor_z))
    obj = bpy.context.object
    obj.name = "_ReviewFloor"
    material = bpy.data.materials.new("_ReviewFloorMaterial")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.18, 0.18, 0.18, 1.0)
    shader.inputs["Roughness"].default_value = 0.7
    obj.data.materials.append(material)


def area_light(name, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def aim(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(size, samples):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = 0
    # Some distribution builds omit OpenImageDenoise. Review must work on CPU
    # without adding a denoiser dependency or silently changing render engines.
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.render.threads_mode = "FIXED"
    scene.render.threads = min(4, os.cpu_count() or 1)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    world = bpy.data.worlds.new("_ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.18, 0.18, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    scene.world = world
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def imported_metadata(objects, document):
    meshes = [obj for obj in objects if obj.type == "MESH"]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {
        "mesh_objects": len(meshes),
        "unique_meshes": len({obj.data.as_pointer() for obj in meshes}),
        "triangles_per_object_sum": triangles,
        "material_count_gltf": len(document.get("materials", [])),
        "material_names_blender": sorted({slot.material.name for obj in meshes
                                         for slot in obj.material_slots if slot.material}),
        "skin_count_gltf": len(document.get("skins", [])),
        "armatures_blender": [{"name": obj.name, "bones": len(obj.data.bones)}
                              for obj in objects if obj.type == "ARMATURE"],
        "clip_count_gltf": len(document.get("animations", [])),
        "clip_names_gltf": [clip.get("name", "<unnamed>") for clip in document.get("animations", [])],
        "actions_blender": [{"name": action.name, "frame_range": list(action.frame_range)}
                            for action in bpy.data.actions],
        "images_without_resident_pixels_before_render": sorted(image.name for image in bpy.data.images
                                  if image.type != "RENDER_RESULT" and not image.has_data),
        "image_residency_note": "Blender may load embedded images lazily during rendering; this field is not a missing-texture verdict.",
    }


def main():
    args = arguments()
    if not bpy.app.background:
        raise ValueError("Run in a separate background Blender process; an interactive scene is never cleared")
    source = args.input.resolve(strict=True)
    output = args.output.resolve()
    if source.suffix.lower() != ".glb" or not source.is_file():
        raise ValueError("input must be an existing .glb file")
    if output == source or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("output must be a separate new or empty directory; existing files are never overwritten")
    document = read_glb(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
    imported = list(bpy.context.scene.objects)
    # glTF's Blender importer creates viewport-only mesh objects for custom
    # bone displays. They are not source geometry and can sit below the feet.
    helpers = {bone.custom_shape for obj in imported if obj.type == "ARMATURE"
               for bone in obj.pose.bones if bone.custom_shape is not None}
    for helper in helpers:
        helper.hide_render = True
    imported = [obj for obj in imported if obj not in helpers]
    metadata = imported_metadata(imported, document)
    for obj in imported:
        obj.animation_data_clear()
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
        elif obj.type == "LIGHT":
            obj.hide_render = True
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    lower, upper, size, center, corners = asset_bounds(imported, bpy.context.evaluated_depsgraph_get())
    span = max(size)
    scene = configure_scene(args.size, args.samples)
    neutral_floor(center, lower.z - span * 0.002, span)
    camera_data = bpy.data.cameras.new("_ReviewCamera")
    camera_data.type = "ORTHO"
    camera_data.clip_start = max(span * 0.0001, 0.000001)
    camera_data.clip_end = max(span * 20, 100.0)
    camera = bpy.data.objects.new("_ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    lights = [area_light("_ReviewKey", 500 * span * span, span * 1.5),
              area_light("_ReviewFill", 250 * span * span, span * 2),
              area_light("_ReviewRim", 650 * span * span, span * 1.2)]
    views = []
    # glTF +Z becomes Blender -Y; the Blender vertical axis is +Z.
    for name, direction in (("front", Vector((0, -1, 0))),
                            ("side", Vector((1, 0, 0))),
                            ("back", Vector((0, 1, 0)))):
        right = Vector((0, 0, 1)).cross(direction).normalized()
        camera.location = center + direction * max(span * 4, 0.001)
        aim(camera, center)
        projected_x = [(point-center).dot(right) for point in corners]
        projected_z = [point.z-center.z for point in corners]
        camera_data.ortho_scale = max(max(projected_x)-min(projected_x),
                                     max(projected_z)-min(projected_z)) * 1.18
        for light, offset in zip(lights, ((-1.5, 2.2, 2.3), (2.0, 1.5, 1.2), (0.0, -2.0, 2.0))):
            light.location = center + right * offset[0] * span + direction * offset[1] * span + Vector((0, 0, offset[2] * span))
            aim(light, center)
        scene.render.filepath = str(output / (name + ".png"))
        if Path(scene.render.filepath).exists():
            raise ValueError("Refusing to replace an existing review image: " + name)
        bpy.ops.render.render(write_still=True)
        if not (output / (name + ".png")).is_file():
            raise RuntimeError("Render did not produce the expected PNG: " + name)
        views.append({"name": name, "file": name + ".png", "camera_position_blender": list(camera.location),
                      "ortho_scale": camera_data.ortho_scale, "lights_rotate_with_view": True})
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError("Input changed during review; results cannot be associated with the original source")
    report = {
        "status": "rendered_for_human_review",
        "automatic_visual_approval": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "blender": bpy.app.version_string,
        "source": {"path": str(source), "sha256": source_hash, "bytes": source.stat().st_size, "unchanged": True},
        "render": {"engine": "CYCLES", "device": "CPU", "size": args.size, "samples": args.samples,
                   "pose": "REST", "denoising": False, "color_management": "AgX / Base Contrast", "source_rescaled": False},
        "bounds_blender_z_up": {"min": list(lower), "max": list(upper), "size": list(size), "center": list(center)},
        "asset": metadata,
        "excluded_importer_bone_display_helpers": sorted(obj.name for obj in helpers),
        "views": views,
        "limitations": ["Static rest-pose render only; animation, deformation and gameplay integration require separate review",
                        "Blender source units and transforms are preserved; camera and studio adjust to the bounds",
                        "Triangle totals are imported mesh counts, not runtime draw calls or GPU performance"],
    }
    with (output / "review.json").open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(report, ensure_ascii=False, indent=2))
    print("RUNEFALL_ART_REVIEW_OK: " + str(output), flush=True)


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
        os._exit(1)  # Blender otherwise may report Python script errors with exit 0.
