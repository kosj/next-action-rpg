"""Inspect/render an unchanged skeletal GLB with the canonical right-hand sword.

Run with Blender 4.3.2 --background --factory-startup --python this.py --
  --input character.glb --sword sword.glb --output NEW_DIR [--profile samples.json]

Profile is [{"clip":"idle","time":0.0}, ...]. Without it REST is sampled.
This measures evaluated source skin and real geometry. It does not approve visual
quality, gameplay collision, animation transitions, or target-device performance.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import sys
import traceback

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
SOCKET_BASIS = Matrix(((0, -1, 0), (0, 0, -1), (1, 0, 0)))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(points):
    if not points or not all(math.isfinite(x) for p in points for x in p):
        raise ValueError("Non-finite or empty evaluated geometry")
    low = Vector(tuple(min(p[a] for p in points) for a in range(3)))
    high = Vector(tuple(max(p[a] for p in points) for a in range(3)))
    return {"min": list(low), "max": list(high), "size": list(high-low)}


def unit_columns(matrix):
    return [list(matrix.col[a].normalized()) for a in range(3)]


def nearest_surface_report(bvh, points):
    """Report oriented nearest-surface distance; it is not a collision proof."""
    samples = []
    for point in points:
        nearest, normal, index, distance = bvh.find_nearest(point)
        if nearest is None:
            continue
        signed = (point-nearest).dot(normal)
        samples.append({"distance_m": distance, "oriented_distance_m": signed})
    signed = sorted(s["oriented_distance_m"] for s in samples)
    return {"sample_vertices": len(samples),
            "minimum_oriented_distance_m": signed[0] if signed else None,
            "median_oriented_distance_m": signed[len(signed)//2] if signed else None,
            "vertices_below_minus_1mm": sum(d < -.001 for d in signed),
            "vertices_below_minus_5mm": sum(d < -.005 for d in signed),
            "minimum_distance_m": min((s["distance_m"] for s in samples), default=None),
            "method": "nearest evaluated body triangle, oriented by its winding; open/overlapping shells and final grasp require human review"}


def aimed(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


def studio(scene, width, height, samples):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = 0
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 3
    scene.render.threads_mode = "FIXED"
    scene.render.threads = min(4, os.cpu_count() or 1)
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .5
    scene.world = world
    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera_data.type = "ORTHO"
    camera_data.clip_start = .001
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    lights = []
    for n, power in enumerate((650, 350, 700)):
        data = bpy.data.lights.new("ReviewLight"+str(n), "AREA")
        data.energy, data.size = power, 4
        ob = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(ob)
        lights.append(ob)
    return camera, lights


def capture(output, name, camera, lights, center, direction, scale):
    scene = bpy.context.scene
    center, direction = Vector(center), Vector(direction).normalized()
    camera.location = center+direction*12
    aimed(camera, center)
    camera.data.ortho_scale = scale
    right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
    up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
    for ob, (x, y, z) in zip(lights, ((-2, 3, 3), (3, 2, 1), (1, -3, 3))):
        ob.location = center+right*x+direction*y+up*z
        aimed(ob, center)
    scene.render.filepath = str(output/(name+".png"))
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sword", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--author-recipe", type=Path,
                        help="Independently inspect live project-authored poses before GLB export; profile samples need duration")
    parser.add_argument("--socket-z", type=float, default=-.060)
    parser.add_argument("--socket-offset", type=float, nargs=3, metavar=("X_M", "Y_M", "Z_M"),
                        help="Physical right-hand offset; use the authored profile's scaled values")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    physical_offset = Vector(args.socket_offset or (.055, .10, args.socket_z))
    if not all(math.isfinite(v) for v in physical_offset) or physical_offset.length > .25:
        raise ValueError("Socket offset requires finite physical metres near the palm")
    if not bpy.app.background or bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Requires isolated Blender 4.3.2 background process")
    source, sword = args.input.resolve(strict=True), args.sword.resolve(strict=True)
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new/empty; source and prior reviews are preserved")
    output.mkdir(parents=True, exist_ok=True)
    source_sha, sword_sha = sha(source), sha(sword)
    profile = json.loads(args.profile.read_text()) if args.profile else [{"clip": "REST", "time": 0}]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
    original = list(bpy.context.scene.objects)
    # Blender's glTF importer may create a hidden sphere for bone custom shapes.
    # It is not source-renderable skin and must never enter bounds or snapshots.
    rig = next(o for o in original if o.type == "ARMATURE")
    meshes = [o for o in original if o.type == "MESH" and not o.hide_render
              and any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)]
    excluded_hidden_meshes = [o.name for o in original if o.type == "MESH" and o not in meshes]
    if not meshes:
        raise ValueError("No renderable source body with the imported armature modifier")
    actions = {a.name: a for a in bpy.data.actions}
    # Recent GLBs import one Blender action per animated object. The glTF clip
    # remains `idle`, while its armature action can be `idle_Armature`. Resolve
    # through the actual rig NLA track, never a guessed suffix replacement.
    action_aliases = {}
    if rig.animation_data:
        for track in rig.animation_data.nla_tracks:
            linked = {strip.action for strip in track.strips if strip.action is not None}
            if len(linked) == 1:
                action = next(iter(linked))
                if track.name in actions and actions[track.name] != action:
                    raise ValueError("Ambiguous imported armature clip: "+track.name)
                actions[track.name] = action
                action_aliases[track.name] = action.name
    for ob in original:
        if ob.animation_data:
            for track in ob.animation_data.nla_tracks:
                track.mute = True
            ob.animation_data.action = None
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    hand_rest = rig.matrix_world @ rig.data.bones["RightHand"].matrix_local
    rig_scales = hand_rest.to_scale()
    relative_scale = sum(rig_scales)/3
    if max(rig_scales)-min(rig_scales) > 1e-5:
        raise ValueError("Socket cancellation requires uniform imported rig scale")
    hand_rotation = hand_rest.to_quaternion().to_matrix()
    socket = SOCKET_BASIS.to_4x4()
    socket.translation = physical_offset.copy()
    for i in range(3):
        socket.col[i] /= relative_scale
    socket.translation /= relative_scale
    rest_geometry, foot_vertices, hand_cloud, hand_faces = {}, {}, [], []
    graph = bpy.context.evaluated_depsgraph_get()
    hand_inverse = hand_rotation.inverted()
    for ob in meshes:
        ev = ob.evaluated_get(graph)
        me = ev.to_mesh()
        points = [ev.matrix_world @ v.co for v in me.vertices]
        rest_geometry[ob.name] = points
        groups = {g.index: g.name for g in ob.vertex_groups}
        feet = {"left": [], "right": []}
        for v in ob.data.vertices:
            for side, prefix in (("left", "Left"), ("right", "Right")):
                weight = sum(g.weight for g in v.groups if groups[g.group] in (prefix+"Foot", prefix+"ToeBase"))
                if weight > .5:
                    feet[side].append(v.index)
        for side, indices in feet.items():
            minimum = min((points[i].z for i in indices), default=0)
            feet[side] = [i for i in indices if points[i].z <= minimum+.025]
        foot_vertices[ob.name] = feet
        base = len(hand_cloud)
        hand_cloud.extend(hand_inverse @ (p-hand_rest.translation) for p in points)
        hand_faces.extend(tuple(base+i for i in p.vertices) for p in me.polygons)
        ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(hand_cloud, hand_faces, all_triangles=False)
    rays = []
    for x in (-.02, 0, .02):
        for y in (.06, .08, .10, .12):
            location, normal, index, distance = bvh.ray_cast(Vector((x, y, -.2)), Vector((0, 0, 1)), .3)
            rays.append({"x_m": x, "y_m": y, "palmar_first_surface_z_m": location.z if location else None})
    author, contracts, author_evidence = None, {}, None
    if args.author_recipe:
        author_script = Path(__file__).with_name("author_character_actions.py")
        recipe = json.loads(args.author_recipe.read_text())
        author_evidence = {"recipe": str(args.author_recipe), "recipe_sha256": sha(args.author_recipe),
                           "script": str(author_script), "script_sha256_at_load": sha(author_script),
                           "mode": "live analytical project-author poses, not a reviewed final GLB"}
        author_module = runpy.run_path(str(author_script))
        author = author_module["Author"](rig, recipe)
        contracts = author_module["attack_contract"](recipe["profile"])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(sword), import_pack_images=True)
    weapon_objects = [o for o in bpy.context.scene.objects if o not in before]
    weapon_roots = [o for o in weapon_objects if o.parent not in weapon_objects]
    weapon_meshes = [o for o in weapon_objects if o.type == "MESH" and not o.hide_render]
    markers = {o.name: o for o in weapon_objects if o.name in ("GripOrigin", "Guard", "BladeTip")}
    if set(markers) != {"GripOrigin", "Guard", "BladeTip"}:
        raise ValueError("Canonical sword marker contract missing")
    marker_local = {name: ob.matrix_world.translation.copy() for name, ob in markers.items()}
    source_sword_points = [o.matrix_world @ v.co for o in weapon_meshes for v in o.data.vertices]
    # The canonical sword runs along Blender +Z (Godot +Y). This band crosses
    # the right palm at canonical sword Y=.055m; do not include the guard/blade
    # when measuring whether the actual handle sinks through the glove.
    hilt_points = [p for p in source_sword_points if .025 <= p.z <= .085]
    rest_handle_candidates = []
    for depth in dict.fromkeys((-.015, -.055, -.058, -.060, -.065, physical_offset.z)):
        candidate = SOCKET_BASIS.to_4x4()
        candidate.translation = Vector((physical_offset.x, physical_offset.y, depth))
        physical_points = [candidate @ (C @ p) for p in hilt_points]
        rest_handle_candidates.append({"socket_z_m": depth,
                                       **nearest_surface_report(bvh, physical_points)})
    sample_reports, snapshots = [], []
    for sample in profile:
        clip, seconds = sample["clip"], float(sample["time"])
        author_metrics = None
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
        if clip == "REST":
            rig.data.pose_position = "REST"
            rig.animation_data.action = None
            frame = 0
        elif author is not None:
            rig.data.pose_position = "POSE"
            rig.animation_data.action = None
            contract = contracts.get(clip)
            duration = float(sample.get("duration", sum(contract[k] for k in ("startup", "active", "recovery")) if contract else 0))
            if duration <= 0 or not 0 <= seconds <= duration:
                raise ValueError("Live authored sample requires a positive duration and in-range seconds")
            author_metrics = author.pose_action(clip, seconds, duration, contract)
            frame = 0
        else:
            rig.data.pose_position = "POSE"
            if clip not in actions:
                raise ValueError("Unknown clip "+clip+"; available: "+", ".join(actions))
            rig.animation_data_create()
            rig.animation_data.action = actions[clip]
            frame = actions[clip].frame_range[0]+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(int(frame), subframe=frame-int(frame))
        bpy.context.view_layer.update()
        hand_world = rig.matrix_world @ rig.pose.bones["RightHand"].matrix
        weapon_matrix = hand_world @ socket @ C
        for root in weapon_roots:
            root.matrix_world = weapon_matrix
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        body_points, foot_points, body_faces = [], {"left": [], "right": []}, []
        ratios = []
        for ob in meshes:
            ev = ob.evaluated_get(graph)
            me = ev.to_mesh()
            points = [ev.matrix_world @ v.co for v in me.vertices]
            base = len(body_points)
            body_points.extend(points)
            body_faces.extend(tuple(base+i for i in p.vertices) for p in me.polygons)
            for side in foot_points:
                foot_points[side].extend(points[i] for i in foot_vertices[ob.name][side])
            for edge in me.edges:
                a, b = edge.vertices
                rest_length = (rest_geometry[ob.name][a]-rest_geometry[ob.name][b]).length
                if rest_length > .0001:
                    ratios.append((points[a]-points[b]).length/rest_length)
            ev.to_mesh_clear()
        world_markers = {name: weapon_matrix @ p for name, p in marker_local.items()}
        gmarks = {name: C @ p for name, p in world_markers.items()}
        # Apply source +Z -> gameplay -Z bridge exactly once to numerical directions.
        gameplay_markers = {name: Vector((-p.x, p.y, -p.z)) for name, p in gmarks.items()}
        direction = gameplay_markers["BladeTip"]-gameplay_markers["GripOrigin"]
        foot_report = {}
        for side, points in foot_points.items():
            z = sorted(p.z for p in points)
            foot_report[side] = {"fixed_rest_sole_vertices": len(z), "minimum_height_m": min(z) if z else None,
                                 "median_height_m": z[len(z)//2] if z else None,
                                 "vertices_within_20mm_of_rest_floor": sum(abs(v) <= .02 for v in z)}
        ratios.sort()
        sword_axis = (weapon_matrix.to_3x3() @ Vector((0, 0, 1))).normalized()
        sword_projections = [(weapon_matrix @ p).dot(sword_axis) for p in source_sword_points]
        posed_body = BVHTree.FromPolygons(body_points, body_faces, all_triangles=False)
        entry = {"clip": clip, "time_s": seconds, "blender_frame": frame,
                 "live_authored_pose_metrics": author_metrics,
                 "body_bounds_blender_z_up_m": bounds(body_points), "feet": foot_report,
                 "edge_stretch_ratio_max": max(ratios), "edge_stretch_ratio_p99": ratios[int(.99*(len(ratios)-1))],
                 "right_hand_world_blender": [list(row) for row in hand_world],
                 "sword_markers_gameplay_y_up_m": {name: list(p) for name, p in gameplay_markers.items()},
                 "sword_grip_to_tip_m": direction.length,
                 "sword_total_axis_length_m": max(sword_projections)-min(sword_projections),
                 "sword_world_aabb_size_m": bounds([weapon_matrix @ p for p in source_sword_points])["size"],
                 "handle_nearest_body_surface": nearest_surface_report(posed_body, [weapon_matrix @ p for p in hilt_points]),
                 "blade_horizontal_azimuth_deg": math.degrees(math.atan2(direction.x, -direction.z)) if math.hypot(direction.x,direction.z) > .02 else None,
                 "blade_gameplay_sweep_angle_deg": math.degrees(math.atan2(-direction.x, -direction.z)) if math.hypot(direction.x,direction.z) > .02 else None,
                 "gameplay_root_displacement_added": False}
        sample_reports.append(entry)
        if args.render:
            frozen = []
            for ob in meshes+weapon_meshes:
                ev = ob.evaluated_get(graph)
                me = bpy.data.meshes.new_from_object(ev, depsgraph=graph)
                frozen_ob = bpy.data.objects.new("Review_"+clip+"_"+ob.name, me)
                bpy.context.scene.collection.objects.link(frozen_ob)
                frozen_ob.matrix_world = ev.matrix_world.copy()
                frozen.append(frozen_ob)
            snapshots.append((sample, frozen))
    for ob in original+weapon_objects:
        ob.hide_render = True
    views = []
    if args.render:
        camera, lights = studio(bpy.context.scene, 1280, 960, args.samples)
        cols = min(4, len(snapshots))
        rows = math.ceil(len(snapshots)/cols)
        for index, (sample, frozen) in enumerate(snapshots):
            offset = Vector(((index % cols)*3.2, 0, -(index//cols)*2.5))
            for ob in frozen:
                ob.matrix_world.translation += offset
            label = bpy.data.curves.new("PoseLabel", "FONT")
            label.body = sample["clip"]+"  "+str(sample["time"])+"s"
            label.size = .14
            ob = bpy.data.objects.new("PoseLabel", label)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = offset+Vector((-.8, -.25, -.23))
            ob.rotation_euler = (math.pi/2, 0, 0)
        center = Vector(((cols-1)*1.6, 0, .85-(rows-1)*1.25))
        scale = max(cols*3.2*.75, rows*2.5)*1.12
        capture(output, "poses_front", camera, lights, center, (0, -1, .12), scale)
        capture(output, "poses_oblique", camera, lights, center, (2, -5, 1), scale)
        views.extend(["poses_front.png", "poses_oblique.png"])
        if len(snapshots) == 1:
            # Real evaluated hand skin and handle, not a drawn proxy.
            target = hand_world @ Vector((0, physical_offset.y/relative_scale, physical_offset.z/relative_scale))
            posed_hand_rotation = hand_world.to_quaternion().to_matrix()
            normal = posed_hand_rotation @ Vector((0, 0, -1))
            capture(output, "grip_palmar", camera, lights, target, normal, .32)
            capture(output, "grip_oblique", camera, lights, target, normal+posed_hand_rotation @ Vector((1, .4, 0)), .38)
            views.extend(["grip_palmar.png", "grip_oblique.png"])
    report = {"blender": bpy.app.version_string, "automatic_visual_approval": False,
              "source": {"path": str(source), "sha256": source_sha},
              "sword": {"path": str(sword), "sha256": sword_sha},
              "live_author_evidence": author_evidence,
              "blender_action_aliases_from_rig_nla": action_aliases,
              "relative_imported_rig_uniform_scale": relative_scale,
              "renderable_meshes": [ob.name for ob in meshes], "excluded_blender_hidden_custom_shape_meshes": excluded_hidden_meshes,
              "right_hand_rest_world_gltf": [list(row) for row in C @ hand_rest],
              "socket": {"bone": "RightHand", "unit_basis_columns": unit_columns(SOCKET_BASIS),
                         "offset_m": list(physical_offset), "quaternion_xyzw": [.5, -.5, .5, .5],
                         "divide_basis_and_offset_by_relative_rig_scale": True,
                         "right_grasp_sword_y_m": .055, "left_grasp_sword_y_m": -.065,
                         "source_front_bridge_in_socket": False},
              "rest_palm_raycasts_joint_local_physical_m": rays,
              "rest_handle_depth_candidates": rest_handle_candidates,
              "samples": sample_reports, "renders": views,
              "limitations": ["Source pose sampling independently resets bones; runtime crossfades require separate engine checks.",
                              "Foot metrics use fixed rest sole vertices and rest floor zero; they do not prove foot IK or correct root motion.",
                              "Mesh stretch ratios flag deformation changes; human image review is separate.",
                              "Socket/hand contact is a measured candidate; anatomy, glove penetration and final artistry need visual review.",
                              "Source-facing +Z bridge is applied exactly once only to gameplay numerical marker coordinates."]}
    report["angle_convention"] = "gameplay_sweep_angle follows Godot Vector3.FORWARD.rotated(UP, angle); atan2(+x,-z) world heading has the opposite sign"
    if sha(source) != source_sha or sha(sword) != sword_sha:
        raise RuntimeError("Source changed during inspection")
    report["sources_unchanged"] = True
    (output/"review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("RUNEFALL_CHARACTER_REVIEW_OK "+str(output), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
