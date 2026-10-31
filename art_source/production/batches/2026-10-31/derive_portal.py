"""Derive a thin gateway from the front of the generated four-sided portal.

Run in an isolated Blender 4.3.2 background process. The input is immutable;
output GLB and .derivation.json must not already exist. This is an explicitly
edited static art candidate, not an automatic gameplay/collision approval.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import traceback

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SOURCE = None
SOURCE_SHA = None


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def glb_document(path):
    with path.open("rb") as stream:
        header = stream.read(20)
        if len(header) != 20:
            raise ValueError("Truncated GLB")
        magic, version, total, size, kind = struct.unpack("<4sIII4s", header)
        if magic != b"glTF" or version != 2 or total != path.stat().st_size or kind != b"JSON" or size > 16 * 1024 * 1024 or size + 20 > total:
            raise ValueError("Expected self-contained GLB 2.0")
        document = json.loads(stream.read(size).decode("utf-8"))
    for item in [*document.get("images", []), *document.get("buffers", [])]:
        if item.get("uri") and not item["uri"].startswith("data:"):
            raise ValueError("External buffers/images must be embedded")
    if document.get("skins") or document.get("animations"):
        raise ValueError("This recipe accepts static geometry only")
    return document


def bounds(points):
    points = list(points)
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise ValueError("Expected finite nonempty mesh")
    lower = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    upper = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return {"min": list(lower), "max": list(upper), "size": list(upper - lower)}


def static_object():
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and not obj.hide_render]
    if len(objects) != 1 or any(obj.type == "ARMATURE" for obj in bpy.context.scene.objects):
        raise ValueError("Exactly one visible static mesh is required")
    obj = objects[0]
    if obj.data.shape_keys or obj.modifiers or obj.animation_data:
        raise ValueError("No morph targets, modifiers or animation are supported")
    world = obj.matrix_world.copy()
    obj.data = obj.data.copy()
    obj.data.transform(world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    for other in list(bpy.context.scene.objects):
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    return obj


def bvh_for(mesh):
    return BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons], all_triangles=False)


def triangle_box_intersects(points, center, half):
    vertices = [point - center for point in points]
    edges = [vertices[1] - vertices[0], vertices[2] - vertices[1], vertices[0] - vertices[2]]
    basis = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    axes = [*basis, edges[0].cross(edges[1]), *(edge.cross(axis) for edge in edges for axis in basis)]
    for axis in axes:
        if axis.length_squared < 1e-24:
            continue
        projections = [point.dot(axis) for point in vertices]
        radius = sum(half[i] * abs(axis[i]) for i in range(3))
        if min(projections) > radius + 1e-10 or max(projections) < -radius - 1e-10:
            return False
    return True


def audit_mesh(obj, require_clear=True):
    mesh = obj.data
    result = {"bounds_blender_z_up": bounds(v.co for v in mesh.vertices)}
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    result["manifold_after_1e_6m_spatial_weld"] = {
        "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
        "non_manifold_edges": sum(not edge.is_manifold for edge in bm.edges),
        "loose_vertices": sum(not vertex.link_edges for vertex in bm.verts),
        "zero_area_faces": sum(face.calc_area() <= 1e-12 for face in bm.faces),
    }
    bm.free()
    bvh = bvh_for(mesh)
    rays = []
    for x in (-5.9, -4.0, -2.0, 0.0, 2.0, 4.0, 5.9):
        for z in (0.3, 1.0, 2.0, 3.0, 4.0, 5.0, 5.9):
            hit = bvh.ray_cast(Vector((x, -1.8, z)), Vector((0, 1, 0)), 3.6)[0]
            rays.append({"x_m": x, "z_m": z, "clear": hit is None})
    controls = []
    for name, x, z in (("left_pier", -7.3, 3.0), ("right_pier", 7.3, 3.0), ("lintel", 0.0, 6.9)):
        hit = bvh.ray_cast(Vector((x, -1.8, z)), Vector((0, 1, 0)), 3.6)[0]
        controls.append({"name": name, "hit": hit is not None, "hit_point": list(hit) if hit else None})
    mesh.calc_loop_triangles()
    intersections = []
    for index, triangle in enumerate(mesh.loop_triangles):
        if triangle_box_intersects([mesh.vertices[v].co for v in triangle.vertices], Vector((0, 0, 3.0)), Vector((5.999, 0.801, 2.999))):
            intersections.append(index)
    result.update(triangles=len(mesh.loop_triangles), vertices=len(mesh.vertices), materials=len(mesh.materials),
                  opening_rays=rays, positive_control_rays=controls,
                  opening_interior_box={"requested_width_m": 12, "requested_height_m": 6, "numeric_inset_m": 0.001,
                                        "intersecting_triangle_count": len(intersections), "intersecting_triangles_first_20": intersections[:20]})
    if intersections:
        result["intersection_vertices_first_20"] = [[list(mesh.vertices[v].co) for v in mesh.loop_triangles[index].vertices] for index in intersections[:20]]
    size = result["bounds_blender_z_up"]["size"]
    if any(abs(actual - expected) > 1e-4 for actual, expected in zip(size, (17.0, 1.6, 7.8))):
        raise ValueError("Derived bounds do not match17x1.6x7.8m: " + repr(size))
    if abs(result["bounds_blender_z_up"]["min"][2]) > 1e-4:
        raise ValueError("Derived floor is not Z=0")
    if any(result["manifold_after_1e_6m_spatial_weld"].values()):
        raise ValueError("Derived mesh is not a closed nondegenerate manifold")
    if require_clear and (intersections or not all(ray["clear"] for ray in rays) or not all(ray["hit"] for ray in controls)):
        Path("/tmp/runefall-derive-portal-audit-failure.json").write_text(json.dumps(result, indent=2))
        raise ValueError("Derived opening/control geometry did not pass")
    return result


def main():
    global SOURCE, SOURCE_SHA
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--front-depth-fraction", type=float, default=0.25)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not bpy.app.background or bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Use a separate Blender4.3.2 background process")
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    report_path = output.with_suffix(".derivation.json")
    if source.suffix.lower() != ".glb" or output.suffix.lower() != ".glb" or source == output or output.exists() or report_path.exists():
        raise ValueError("Source must be GLB; output GLB and report must be separate new files")
    if not math.isfinite(args.front_depth_fraction) or not 0.15 <= args.front_depth_fraction <= 0.35:
        raise ValueError("Front fraction must lie in verified recipe range0.15..0.35")
    SOURCE, SOURCE_SHA = source, digest(source)
    glb_document(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
    obj = static_object()
    obj.name = "SanctuaryThinGateway"
    original = bounds(v.co for v in obj.data.vertices)
    original_triangles = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    original_vertex_count = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    welded_vertex_count = len(bm.verts)
    cut_y = original["min"][1] + original["size"][1] * args.front_depth_fraction
    bmesh.ops.bisect_plane(bm, geom=[*bm.verts, *bm.edges, *bm.faces], dist=1e-7,
                          plane_co=Vector((0, cut_y, 0)), plane_no=Vector((0, 1, 0)), clear_outer=True, clear_inner=False)
    wires = [edge for edge in bm.edges if not edge.link_faces]
    if wires:
        bmesh.ops.delete(bm, geom=wires, context="EDGES")
    loose = [vertex for vertex in bm.verts if not vertex.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    caps = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)["faces"] if boundary else []
    cap_material = bpy.data.materials.new("SourceCutCapStone")
    cap_material.use_nodes = True
    shader = cap_material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.42, 0.39, 0.32, 1.0)
    shader.inputs["Roughness"].default_value = 0.88
    shader.inputs["Metallic"].default_value = 0.0
    obj.data.materials.append(cap_material)
    for face in caps:
        face.material_index = len(obj.data.materials) - 1
    cropped = bounds(vertex.co for vertex in bm.verts)
    low_z = cropped["min"][2] + cropped["size"][2] * 0.45
    center_x = (cropped["min"][0] + cropped["max"][0]) * 0.5
    left = max(vertex.co.x for vertex in bm.verts if vertex.co.z < low_z and vertex.co.x < center_x)
    right = min(vertex.co.x for vertex in bm.verts if vertex.co.z < low_z and vertex.co.x > center_x)
    if not left < center_x < right or right - left < cropped["size"][0] * 0.4:
        raise ValueError("Could not identify the two source piers")
    beam_floor = min(vertex.co.z for vertex in bm.verts if left + 1e-5 < vertex.co.x < right - 1e-5)
    if not low_z < beam_floor < cropped["max"][2] - cropped["size"][2] * 0.05:
        raise ValueError("Could not identify the source lintel underside")
    for axis, coordinate in ((0, left), (0, right), (2, beam_floor)):
        normal = Vector((1, 0, 0)) if axis == 0 else Vector((0, 0, 1))
        position = Vector((coordinate, 0, 0)) if axis == 0 else Vector((0, 0, coordinate))
        bmesh.ops.bisect_plane(bm, geom=[*bm.verts, *bm.edges, *bm.faces], dist=1e-7,
                              plane_co=position, plane_no=normal, clear_outer=False, clear_inner=False)
    for vertex in bm.verts:
        x, y, z = vertex.co
        if x <= left:
            new_x = -8.5 + (x - cropped["min"][0]) * 2.5 / (left - cropped["min"][0])
        elif x >= right:
            new_x = 6.0 + (x - right) * 2.5 / (cropped["max"][0] - right)
        else:
            new_x = -6.0 + (x - left) * 12.0 / (right - left)
        new_y = -0.8 + (y - cropped["min"][1]) * 1.6 / cropped["size"][1]
        if z <= beam_floor:
            new_z = (z - cropped["min"][2]) * 6.0 / (beam_floor - cropped["min"][2])
        else:
            new_z = 6.0 + (z - beam_floor) * 1.8 / (cropped["max"][2] - beam_floor)
        vertex.co = Vector((new_x, new_y, new_z))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    before_corner_trim = audit_mesh(obj, require_clear=False)
    if before_corner_trim["opening_interior_box"]["intersecting_triangle_count"]:
        # Authored geometry edit: remove the source's small rounded/chamfered
        # upper-corner intrusions. This does not relax the clear-volume test.
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 3.0))
        cutter = bpy.context.object
        cutter.name = "_GatewayOpeningCutter"
        cutter.dimensions = (12.002, 4.0, 6.002)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for material in obj.data.materials:
            cutter.data.materials.append(material)
        for polygon in cutter.data.polygons:
            polygon.material_index = len(obj.data.materials) - 1
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new("AuthoredRectangularOpening", "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        modifier.material_mode = "INDEX"
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
        obj.data.update()
        # Exact booleans may produce n-gons. Triangulate after the boolean too,
        # so tangent-space normals export with a well-defined triangle basis.
        final_bm = bmesh.new()
        final_bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(final_bm, faces=list(final_bm.faces))
        bmesh.ops.triangulate(final_bm, faces=list(final_bm.faces))
        final_bm.to_mesh(obj.data)
        final_bm.free()
        obj.data.update()
    before_export = audit_mesh(obj)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".portal-candidate-", dir=output.parent) as staging:
        staged = Path(staging) / output.name
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(filepath=str(staged), export_format="GLB", use_selection=True,
                                 export_yup=True, export_apply=True, export_animations=False,
                                 export_normals=True, export_tangents=True, export_materials="EXPORT")
        glb_document(staged)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(staged), import_pack_images=True)
        reimported = static_object()
        after_import = audit_mesh(reimported)
        if digest(source) != SOURCE_SHA:
            raise ValueError("Source changed; derived output will not be published")
        report = {"status": "geometry_prepared_candidate_requires_visual_and_runtime_review", "blender": bpy.app.version_string,
                  "source": {"file": str(source), "sha256": SOURCE_SHA, "bytes": source.stat().st_size, "unchanged": True},
                  "source_bounds_blender_z_up": original, "source_triangles": original_triangles,
                  "front_crop": {"fraction": args.front_depth_fraction, "cut_y": cut_y, "cropped_bounds": cropped,
                                 "vertices_before_spatial_weld": original_vertex_count, "vertices_after_spatial_weld": welded_vertex_count,
                                 "new_cap_faces_before_triangulation": len(caps), "cap_material": "SourceCutCapStone"},
                  "authored_static_geometry_fit": {"target_size_xyz_m": [17, 1.6, 7.8], "opening_width_m": 12,
                                                 "opening_height_m": 6, "source_left_inner_x": left,
                                                 "source_right_inner_x": right, "source_lintel_underside_z": beam_floor,
                                                 "method": "Static vertex edit: split at X/Z break planes, piecewise X/Z fit, independent depth fit; root transform identity"},
                  "opening_corner_trim": {"method": "EXACT boolean difference for a12.002x4.0x6.002m cutter centered at(0,0,3m)",
                                          "pre_trim_intersecting_triangles": before_corner_trim["opening_interior_box"]["intersecting_triangle_count"],
                                          "reason": "Remove original small rounded/chamfered upper-corner intrusions; preserve the stricter clear-volume test"},
                  "material_policy": "Original loop UVs and PBR materials retained on original faces; new rear cut caps have a separate untextured rough limestone material and require visual review",
                  "before_export": before_export, "reimported": after_import,
                  "output": {"file": output.name, "bytes": staged.stat().st_size, "sha256": digest(staged)},
                  "limitations": ["Source geometry is deliberately changed; no original shape fidelity claim",
                                  "Interior volume SAT and sparse visual-mesh rays are geometry checks, not Godot collision/navigation/capsule approval",
                                  "No self-intersection, production lighting, texture-density, target hardware or final AAA quality approval"]}
        staged_report = Path(staging) / report_path.name
        staged_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        os.link(staged, output)
        try:
            os.link(staged_report, report_path)
        except Exception:
            output.unlink()
            raise
    print("RUNEFALL_THIN_GATEWAY_GEOMETRY_OK: " + str(output), flush=True)


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
        if SOURCE is not None and digest(SOURCE) != SOURCE_SHA:
            print("ERROR: input source hash changed", flush=True)
            exit_code = 1
        sys.stdout.flush()
        sys.stderr.flush()
    if exit_code:
        os._exit(exit_code)
