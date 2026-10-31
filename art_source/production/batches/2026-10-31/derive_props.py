"""Bake immutable VARCO sword/pillar sources into canonical static candidates.

Run in a separate Blender 4.3.2 background process, for example:
blender -b --factory-startup --python art_source/production/batches/2026-10-31/derive_props.py -- \
  --asset sword --source build/source.glb --output build/source_canonical.glb --triangle-budget 8000

The sword guard/grip are explicit geometry heuristics, not semantic part labels
or final hand-grip approval. Geometry, UV correspondence, markers, source hashes
and exported normals/tangents are checked after reimport. No gameplay is edited.
"""
import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import traceback

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
from inspect_glb import Inspector, inspect_glb, unpack_glb

SOURCE = None
SOURCE_SHA = None
POSITION_TOLERANCE = 0.00001
UV_TOLERANCE = 0.0000001
LENGTH_TOLERANCE = 0.00001


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", choices=("sword", "pillar"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--triangle-budget", type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.source = args.source.resolve(strict=True)
    args.output = args.output.resolve()
    args.report = args.output.with_suffix(".derivation.json")
    if not args.source.is_file() or args.source.suffix.lower() != ".glb" or args.output.suffix.lower() != ".glb":
        parser.error("source and output must be GLB files")
    if args.source == args.output or args.output.exists() or args.report.exists():
        parser.error("output GLB and derivation report must be separate new files")
    if args.triangle_budget is not None and args.triangle_budget <= 0:
        parser.error("triangle budget must be a positive integer")
    return args


def document_and_inspection(path, required_nodes=()):
    inspection = inspect_glb(path, require_embedded=True, required_nodes=required_nodes)
    if not inspection["structurally_valid"] or not inspection["requirements_met"]:
        raise ValueError("Embedded/core GLB requirements failed: " + repr(inspection["errors"]))
    document, binary, _ = unpack_glb(path.read_bytes())
    if document.get("skins") or document.get("animations"):
        raise ValueError("Only static unskinned sources are supported")
    if inspection["counts"]["meshes"] != 1:
        raise ValueError("Exactly one source mesh is required")
    return document, binary, inspection


def source_mesh():
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH" and not obj.hide_render]
    if len(meshes) != 1 or any(obj.type == "ARMATURE" for obj in objects):
        raise ValueError("Expected exactly one visible static mesh and no armature")
    obj = meshes[0]
    if obj.data.shape_keys or obj.modifiers or obj.animation_data:
        raise ValueError("Morph targets, modifiers and animation are unsupported")
    if not obj.data.uv_layers.active:
        raise ValueError("A source UV layer is required")
    obj.data = obj.data.copy()
    obj.data.transform(obj.matrix_world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    for other in objects:
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    return obj


def bounds(points):
    points = list(points)
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise ValueError("Expected finite nonempty geometry")
    lower = Vector([min(point[i] for point in points) for i in range(3)])
    upper = Vector([max(point[i] for point in points) for i in range(3)])
    size = upper - lower
    if min(size) <= 0.000001:
        raise ValueError("Degenerate source dimensions")
    return {"min": list(lower), "max": list(upper), "size": list(size)}


def uv_snapshot(mesh):
    return {layer.name: [tuple(item.uv) for item in layer.data] for layer in mesh.uv_layers}


def recalculate_shading(mesh):
    # Zero custom vectors ask Blender to use newly calculated geometric normals.
    # Existing faces, smooth/sharp flags, UV seams and triangle topology remain.
    if mesh.has_custom_normals:
        mesh.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(mesh.loops))
    mesh.update(calc_edges=True)
    mesh.calc_loop_triangles()
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    for corner in mesh.corner_normals:
        if not all(math.isfinite(value) for value in corner.vector):
            raise ValueError("Nonfinite recalculated normal")
    for loop in mesh.loops:
        if not all(math.isfinite(value) for value in loop.tangent) or not math.isfinite(loop.bitangent_sign):
            raise ValueError("Nonfinite recalculated tangent")


def triangle_corner_data(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    return [[(obj.matrix_world @ mesh.vertices[mesh.loops[index].vertex_index].co,
              Vector(uv[index].uv)) for index in triangle.loops] for triangle in mesh.loop_triangles]


def compare_corner_data(expected, actual):
    if len(expected) != len(actual):
        raise ValueError("Export/reimport changed the triangle count")
    tree = KDTree(len(expected))
    for index, triangle in enumerate(expected):
        tree.insert(sum((point for point, _ in triangle), Vector()) / 3.0, index)
    tree.balance()
    used = set()
    maximum_position_error = maximum_uv_error = 0.0
    for triangle in actual:
        center = sum((point for point, _ in triangle), Vector()) / 3.0
        match = None
        for _, index, _ in tree.find_range(center, POSITION_TOLERANCE):
            if index in used:
                continue
            for permutation in itertools.permutations(expected[index]):
                position_error = max((a[0] - b[0]).length for a, b in zip(triangle, permutation))
                uv_error = max(max(abs(a[1][axis] - b[1][axis]) for axis in range(2))
                               for a, b in zip(triangle, permutation))
                if position_error <= POSITION_TOLERANCE and uv_error <= UV_TOLERANCE:
                    match = (index, position_error, uv_error)
                    break
            if match is not None:
                break
        if match is None:
            raise ValueError("Reimported triangle position/UV correspondence differs")
        index, position_error, uv_error = match
        used.add(index)
        maximum_position_error = max(maximum_position_error, position_error)
        maximum_uv_error = max(maximum_uv_error, uv_error)
    if len(used) != len(expected):
        raise ValueError("Export did not preserve every source triangle/UV assignment")
    return {"matched_triangles": len(used), "max_corner_position_error_m": maximum_position_error,
            "max_corner_uv_error": maximum_uv_error, "position_tolerance_m": POSITION_TOLERANCE,
            "uv_tolerance": UV_TOLERANCE,
            "method": "Bijective triangle/corner position and UV matching after export/reimport"}


def derive_sword(obj, original):
    lower, size = Vector(original["min"]), Vector(original["size"])
    upper = Vector(original["max"])
    center_x = (lower.x + upper.x) * 0.5
    cluster = [vertex.index for vertex in obj.data.vertices
               if abs(vertex.co.x - center_x) > size.x * 0.4
               and lower.z + size.z * 0.1 < vertex.co.z < lower.z + size.z * 0.45]
    if len(cluster) < 8:
        raise ValueError("The lower maximum-width guard-tip cluster is not identifiable")
    guard_z = statistics.median(obj.data.vertices[index].co.z for index in cluster)
    if not lower.z < guard_z < upper.z:
        raise ValueError("Invalid heuristic guard plane")
    xy_scale = 1.35 / size.z
    blade_scale = 1.03 / (upper.z - guard_z)
    hilt_scale = 0.32 / (guard_z - lower.z)
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        z = 0.16 + (z - guard_z) * (blade_scale if z >= guard_z else hilt_scale)
        vertex.co = (x * xy_scale, y * xy_scale, z)
    grip_band = [vertex.co.copy() for vertex in obj.data.vertices if -0.05 <= vertex.co.z <= 0.05]
    if len(grip_band) < 8:
        raise ValueError("The heuristic hilt-middle band is not identifiable")
    grip_x = (min(point.x for point in grip_band) + max(point.x for point in grip_band)) * 0.5
    grip_y = (min(point.y for point in grip_band) + max(point.y for point in grip_band)) * 0.5
    for vertex in obj.data.vertices:
        vertex.co.x -= grip_x
        vertex.co.y -= grip_y
    tip_z = max(vertex.co.z for vertex in obj.data.vertices)
    tip_points = [vertex.co.copy() for vertex in obj.data.vertices if abs(vertex.co.z - tip_z) <= 0.000001]
    tip = sum(tip_points, Vector()) / len(tip_points)
    markers = {"GripOrigin": Vector((0, 0, 0)), "Guard": Vector((0, 0, 0.16)), "BladeTip": tip}
    post_cluster = [obj.data.vertices[index].co.copy() for index in cluster]
    detail = {"guard_identification": "Heuristic median Z of lower-half maximum-width crossguard-tip vertices; not semantic labels",
              "guard_cluster_vertices": len(cluster), "source_heuristic_guard_z": guard_z,
              "source_heuristic_blade_length": upper.z - guard_z,
              "source_heuristic_hilt_length": guard_z - lower.z,
              "xy_uniform_scale": xy_scale, "blade_z_scale": blade_scale, "hilt_z_scale": hilt_scale,
              "grip_axis": "BBox center in the mapped hilt-middle Z[-.05,.05] band; not anatomical hand-grip approval",
              "grip_band_source_vertex_count": len(grip_band),
              "grip_axis_xy_translation_applied_m": [-grip_x, -grip_y],
              "target_blade_above_heuristic_guard_m": 1.03, "target_hilt_below_heuristic_guard_m": 0.32,
              "target_total_length_m": 1.35, "target_guard_z_m": 0.16,
              "target_bottom_z_m": -0.16, "target_tip_z_m": 1.19,
              "mapped_guard_cluster_median_z_m": statistics.median(point.z for point in post_cluster),
              "mapped_guard_cluster_median_error_m": abs(statistics.median(point.z for point in post_cluster) - 0.16),
              "blade_tip_transverse_offset_m": [tip.x, tip.y],
              "semantic_blade_grip_review_approved": False}
    return markers, detail


def derive_pillar(obj, original):
    lower, size = Vector(original["min"]), Vector(original["size"])
    upper = Vector(original["max"])
    center = (lower + upper) * 0.5
    scale = Vector((1.6 / size.x, 1.6 / size.y, 7.0 / size.z))
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = ((x - center.x) * scale.x, (y - center.y) * scale.y, (z - lower.z) * scale.z)
    return {}, {"method": "Nonuniform static vertex bake; source UV corner assignments preserved",
                "axis_scale_xyz": list(scale), "source_center_xy": [center.x, center.y],
                "source_floor_z": lower.z, "target_size_xyz_m": [1.6, 1.6, 7.0],
                "target_floor_z_m": 0.0, "material_or_texel_density_approved": False}


def add_root_and_markers(obj, asset, marker_positions):
    root = bpy.data.objects.new("RunebladeCanonical" if asset == "sword" else "PillarCanonical", None)
    bpy.context.scene.collection.objects.link(root)
    root["candidate_only"] = True
    root["gameplay_or_final_art_approved"] = False
    obj.name = "CanonicalGeometry"
    obj.parent = root
    obj.matrix_world = Matrix.Identity(4)
    for name, position in marker_positions.items():
        marker = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(marker)
        marker.parent = root
        marker.location = position
        marker["heuristic_candidate_marker"] = True
    bpy.context.view_layer.update()
    return root


def geometry_contract(asset, obj, expected_markers):
    actual = bounds(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
    error = {}
    if asset == "sword":
        error = {"total_length_m": abs(actual["size"][2] - 1.35),
                 "bottom_z_m": abs(actual["min"][2] + 0.16),
                 "tip_z_m": abs(actual["max"][2] - 1.19)}
        band = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices if -0.05 <= (obj.matrix_world @ vertex.co).z <= 0.05]
        center = Vector(((min(p.x for p in band) + max(p.x for p in band)) * 0.5,
                         (min(p.y for p in band) + max(p.y for p in band)) * 0.5, 0))
        error["grip_band_xy_center_m"] = max(abs(center.x), abs(center.y))
    else:
        error = {"size_x_m": abs(actual["size"][0] - 1.6), "size_y_m": abs(actual["size"][1] - 1.6),
                 "size_z_m": abs(actual["size"][2] - 7.0), "floor_z_m": abs(actual["min"][2]),
                 "center_x_m": abs((actual["min"][0] + actual["max"][0]) * 0.5),
                 "center_y_m": abs((actual["min"][1] + actual["max"][1]) * 0.5)}
    markers = {}
    for name, expected in expected_markers.items():
        marker = bpy.data.objects.get(name)
        if marker is None or marker.type != "EMPTY":
            raise ValueError("Missing unique expected empty marker: " + name)
        position = marker.matrix_world.translation
        delta = (position - expected).length
        error[name + "_marker_m"] = delta
        markers[name] = {"blender_z_up_m": list(position), "gltf_y_up_m": [position.x, position.z, -position.y],
                         "expected_blender_z_up_m": list(expected), "position_error_m": delta}
    if any(value > LENGTH_TOLERANCE for value in error.values()):
        raise ValueError("Canonical bounds/marker contract failed: " + repr(error))
    parents = [item for item in bpy.context.scene.objects if item.parent is None]
    if len(parents) != 1 or max(abs(parents[0].matrix_world[row][column] - (1.0 if row == column else 0.0))
                                for row in range(4) for column in range(4)) > 0.000001:
        raise ValueError("Canonical root transform is not identity")
    return {"bounds_blender_z_up": actual, "markers": markers, "numeric_contract_errors": error,
            "tolerance_m": LENGTH_TOLERANCE, "root_transform_identity": True}


def exported_shading(path):
    document, binary, _ = unpack_glb(path.read_bytes())
    inspector = Inspector(document, binary)
    inspector.buffers()
    inspector.accessors()
    count = 0
    normal_error = tangent_error = dot_error = 0.0
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            if not all(name in attributes for name in ("POSITION", "NORMAL", "TANGENT", "TEXCOORD_0")):
                raise ValueError("Export must contain positions, recalculated normals/tangents and source UVs")
            normals = list(inspector.values(attributes["NORMAL"]))
            tangents = list(inspector.values(attributes["TANGENT"]))
            if len(normals) != len(tangents):
                raise ValueError("Normal/tangent accessor counts differ")
            for normal, tangent in zip(normals, tangents):
                n, t = Vector(normal), Vector(tangent[:3])
                normal_error = max(normal_error, abs(n.length - 1.0))
                tangent_error = max(tangent_error, abs(t.length - 1.0), abs(abs(tangent[3]) - 1.0))
                dot_error = max(dot_error, abs(n.dot(t)))
            count += len(normals)
    if max(normal_error, tangent_error, dot_error) > 0.001:
        raise ValueError("Exported normal/tangent basis is not finite, normalized and orthogonal")
    return {"normal_tangent_vertices": count, "max_normal_length_error": normal_error,
            "max_tangent_length_or_handedness_error": tangent_error, "max_normal_tangent_dot": dot_error,
            "tolerance": 0.001, "normal_tangent_recalculated": True}


def main():
    global SOURCE, SOURCE_SHA
    args = arguments()
    if not bpy.app.background or bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Use a separate Blender4.3.2 background process")
    SOURCE, SOURCE_SHA = args.source, digest(args.source)
    _, _, source_inspection = document_and_inspection(args.source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.source), import_pack_images=True)
    obj = source_mesh()
    original = bounds(vertex.co for vertex in obj.data.vertices)
    original_uvs = uv_snapshot(obj.data)
    original_triangles = source_inspection["counts"]["mesh_triangles"]
    if args.asset == "sword":
        marker_positions, recipe = derive_sword(obj, original)
    else:
        marker_positions, recipe = derive_pillar(obj, original)
    if uv_snapshot(obj.data) != original_uvs:
        raise ValueError("The vertex edit changed source UV corner data")
    recalculate_shading(obj.data)
    root = add_root_and_markers(obj, args.asset, marker_positions)
    before_export = geometry_contract(args.asset, obj, marker_positions)
    expected_corners = triangle_corner_data(obj)
    if len(expected_corners) != original_triangles:
        raise ValueError("The static vertex bake changed source triangle count")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prop-candidate-", dir=args.output.parent) as staging:
        staged = Path(staging) / args.output.name
        bpy.ops.object.select_all(action="DESELECT")
        for item in [root, obj, *root.children]:
            item.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(filepath=str(staged), export_format="GLB", use_selection=True,
                                 export_yup=True, export_apply=False, export_animations=False,
                                 export_normals=True, export_tangents=True, export_texcoords=True,
                                 export_materials="EXPORT", export_extras=True,
                                 export_draco_mesh_compression_enable=False)
        _, _, output_inspection = document_and_inspection(staged, required_nodes=tuple(marker_positions))
        if output_inspection["counts"]["mesh_triangles"] != original_triangles:
            raise ValueError("GLB export changed triangle count")
        shading = exported_shading(staged)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(staged), import_pack_images=True)
        reimported = [item for item in bpy.context.scene.objects if item.type == "MESH"]
        if len(reimported) != 1:
            raise ValueError("Reimport did not retain one static mesh")
        after_import = geometry_contract(args.asset, reimported[0], marker_positions)
        correspondence = compare_corner_data(expected_corners, triangle_corner_data(reimported[0]))
        if digest(args.source) != SOURCE_SHA:
            raise ValueError("Source changed during derivation; output will not be published")
        budget_met = args.triangle_budget is None or original_triangles <= args.triangle_budget
        report = {"schema_version": 1, "status": "canonical_static_candidate_not_runtime_approved",
                  "blender": bpy.app.version_string, "asset": args.asset,
                  "source": {"path": str(args.source), "bytes": args.source.stat().st_size,
                             "sha256": SOURCE_SHA, "unchanged": True},
                  "recipe": recipe, "source_bounds_blender_z_up": original,
                  "before_export": before_export, "reimported": after_import,
                  "uv_corner_data_unchanged_before_export": True,
                  "reimport_corner_correspondence": correspondence, "exported_shading": shading,
                  "triangle_budget": {"requested": args.triangle_budget, "source": original_triangles,
                                      "derived": output_inspection["counts"]["mesh_triangles"],
                                      "met": budget_met, "excess": max(0, original_triangles - args.triangle_budget)
                                      if args.triangle_budget is not None else 0},
                  "output_sha256": digest(staged), "output_bytes": staged.stat().st_size,
                  "structural_inspection": output_inspection,
                  "uv_semantics": "Per-corner UVs preserved; local geometry proportions changed. Texel density/material response still need art review.",
                  "limitations": ["Heuristic sword guard/grip markers are not semantic blade labels or final hand-grip approval",
                                  "No actor, attack timing, damage, physics, collision, final material or FPS approval",
                                  "Triangle counts are preserved, including any source budget excess",
                                  "These static source edits do not approve final AAA art"]}
        staged_report = Path(staging) / args.report.name
        staged_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.link(staged, args.output)
        try:
            os.link(staged_report, args.report)
        except Exception:
            args.output.unlink()
            raise
    print("RUNEFALL_CANONICAL_PROP_OK: " + str(args.output), flush=True)


if __name__ == "__main__":
    exit_code = 0
    try:
        main()
    except SystemExit as error:
        exit_code = 0 if error.code in (None, 0) else 1
    except Exception:
        traceback.print_exc()
        exit_code = 1
    finally:
        try:
            if SOURCE is not None and digest(SOURCE) != SOURCE_SHA:
                raise RuntimeError("Source SHA changed during derivation")
            if SOURCE is not None:
                print("RUNEFALL_PROP_SOURCE_UNCHANGED: " + SOURCE_SHA, flush=True)
        except Exception:
            traceback.print_exc()
            exit_code = 1
        sys.stdout.flush()
        sys.stderr.flush()
    if exit_code:
        os._exit(exit_code)
