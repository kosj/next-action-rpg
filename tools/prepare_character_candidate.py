"""Merge matching skeletal locomotion candidates without altering their sources.

blender -b --factory-startup --python tools/prepare_character_candidate.py -- \
  --base rigged.glb --motion idle=idle.glb --motion walk=jog.glb \
  --motion run=sprint.glb --output build/lyra-candidate.glb --height 1.82

Only bone pose FCurves are transferred. --normalize-origin-translation permits
an offset only after matching topology, named weights, rest linear transforms
and a common bone/mesh translation are proved, followed by sampled pose checks.
The result has idle, walk, run and a generated bind-pose RESET, not nine clips.
"""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import traceback

import bpy
from mathutils import Matrix, Vector

STATES = {"idle", "walk", "run"}
BONE_CURVE = re.compile(r'^pose\.bones\[("(?:\\.|[^"\\])*")\]\.(location|rotation_quaternion|rotation_euler|scale)$')
SOURCE_HASHES = {}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--motion", action="append", default=[], metavar="STATE=GLB")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--height", type=float, default=1.82)
    parser.add_argument("--tolerance", type=float, default=0.00001)
    parser.add_argument("--normalize-origin-translation", action="store_true",
                        help="Prove and remove a uniform whole-rig/mesh origin translation before strict checks")
    parser.add_argument("--ground-rest-feet", action="store_true",
                        help="Translate the complete uniformly scaled asset wrapper so its rest mesh floor is Z=0")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not math.isfinite(args.height) or args.height <= 0 or not 0 < args.tolerance <= 0.01:
        parser.error("height must be finite and positive; tolerance must be >0 and <=0.01")
    motions = {}
    for item in args.motion:
        state, separator, value = item.partition("=")
        if not separator or state not in STATES or state in motions or not value:
            parser.error("supply each of idle, walk, run exactly once as --motion STATE=GLB")
        motions[state] = Path(value).resolve(strict=True)
    if set(motions) != STATES:
        parser.error("the complete idle, walk, run candidate set is required")
    args.base = args.base.resolve(strict=True)
    args.output = args.output.resolve()
    args.motions = motions
    return args


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            result.update(block)
    return result.hexdigest()


def glb_json(path):
    with path.open("rb") as stream:
        header = stream.read(20)
        if len(header) != 20:
            raise ValueError("Truncated GLB: " + str(path))
        magic, version, total, count, kind = struct.unpack("<4sIII4s", header)
        if magic != b"glTF" or version != 2 or total != path.stat().st_size or kind != b"JSON" or count > 16*1024*1024 or count+20 > total:
            raise ValueError("Expected a complete GLB v2: " + str(path))
        document = json.loads(stream.read(count).decode("utf-8"))
    for resource in [*document.get("buffers", []), *document.get("images", [])]:
        if resource.get("uri") and not resource["uri"].startswith("data:"):
            raise ValueError("External resource URIs must be embedded first: " + str(path))
    return document


def import_asset(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
    return list(set(bpy.data.objects)-before_objects), list(set(bpy.data.actions)-before_actions)


def armature(objects, label):
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(rigs) != 1 or not rigs[0].data.bones:
        raise ValueError(label + " must contain exactly one nonempty armature")
    return rigs[0]


def without_helpers(objects, rig):
    helpers = {bone.custom_shape for bone in rig.pose.bones if bone.custom_shape}
    return [obj for obj in objects if obj not in helpers], sorted(obj.name for obj in helpers)


def rest_bounds(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type == "MESH" and not obj.hide_render and len(obj.data.vertices):
            evaluated = obj.evaluated_get(graph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points or not all(math.isfinite(x) for point in points for x in point):
        raise ValueError("No finite renderable mesh bounds")
    lower = [min(point[axis] for point in points) for axis in range(3)]
    upper = [max(point[axis] for point in points) for axis in range(3)]
    height = upper[2]-lower[2]
    if height <= 0.000001:
        raise ValueError("Degenerate character height")
    return {"min":lower, "max":upper, "height":height}


def matrix_error(a, b):
    return max(abs(a[row][column]-b[row][column]) / max(1.0, abs(a[row][column]), abs(b[row][column]))
               for row in range(4) for column in range(4))


def compare_rigs(base, source, tolerance, state):
    if set(base.data.bones.keys()) != set(source.data.bones.keys()):
        raise ValueError(state + ": bone names differ from the base rig")
    largest = matrix_error(base.matrix_world, source.matrix_world)
    if largest > tolerance:
        raise ValueError(state + ": armature world transform differs from base (error %.9g)" % largest)
    for bone in base.data.bones:
        other = source.data.bones[bone.name]
        if (bone.parent.name if bone.parent else None) != (other.parent.name if other.parent else None):
            raise ValueError(state + ": bone parent differs: " + bone.name)
        error = matrix_error(bone.matrix_local, other.matrix_local)
        largest = max(largest, error)
        if error > tolerance:
            raise ValueError(state + ": rest matrix differs: %s (error %.9g)" % (bone.name, error))
    return largest


def body_mesh(objects, label):
    meshes = [obj for obj in objects if obj.type == "MESH" and not obj.hide_render]
    if len(meshes) != 1 or meshes[0].data.shape_keys is not None:
        raise ValueError(label + ": origin proof currently requires one body mesh without morph targets")
    return meshes[0]


def origin_proof(base_rig, source_rig, base_mesh, source_mesh, tolerance, state):
    if set(base_rig.data.bones.keys()) != set(source_rig.data.bones.keys()):
        raise ValueError(state + ": bone names differ")
    world_error = matrix_error(base_rig.matrix_world, source_rig.matrix_world)
    relationship_error = matrix_error(base_rig.matrix_world.inverted() @ base_mesh.matrix_world,
                                      source_rig.matrix_world.inverted() @ source_mesh.matrix_world)
    if max(world_error, relationship_error) > tolerance:
        raise ValueError(state + ": armature or mesh world relationship differs")
    differences = []
    for bone in base_rig.data.bones:
        other = source_rig.data.bones[bone.name]
        if (bone.parent.name if bone.parent else None) != (other.parent.name if other.parent else None):
            raise ValueError(state + ": bone parent differs: " + bone.name)
        differences.append(other.matrix_local @ bone.matrix_local.inverted())
    delta = differences[0].translation.copy()
    linear_error = max(abs(matrix[row][column]-(1.0 if row == column else 0.0))
                       for matrix in differences for row in range(3) for column in range(3))
    translation_error = max((matrix.translation-delta).length for matrix in differences)
    if max(linear_error,translation_error) > tolerance:
        raise ValueError(state + ": rest differences are not one uniform translation")
    a, b = base_mesh.data, source_mesh.data
    if len(a.vertices) != len(b.vertices) or len(a.polygons) != len(b.polygons):
        raise ValueError(state + ": mesh topology size differs")
    if any(tuple(x.vertices) != tuple(y.vertices) or x.material_index != y.material_index for x,y in zip(a.polygons,b.polygons)):
        raise ValueError(state + ": indexed mesh topology or material assignment differs")
    names_a = {group.index:group.name for group in base_mesh.vertex_groups}
    names_b = {group.index:group.name for group in source_mesh.vertex_groups}
    if set(names_a.values()) != set(names_b.values()):
        raise ValueError(state + ": vertex group names differ")
    global_delta = base_rig.matrix_world.to_3x3() @ delta
    geometry_error = weight_error = 0.0
    for x,y in zip(a.vertices,b.vertices):
        geometry_error = max(geometry_error,((source_mesh.matrix_world@y.co)-(base_mesh.matrix_world@x.co)-global_delta).length)
        weights_a = {names_a[item.group]:item.weight for item in x.groups if item.weight > 0.0}
        weights_b = {names_b[item.group]:item.weight for item in y.groups if item.weight > 0.0}
        if weights_a.keys() != weights_b.keys():
            raise ValueError(state + ": vertex weight bone membership differs")
        weight_error = max(weight_error,max((abs(value-weights_b[name]) for name,value in weights_a.items()),default=0.0))
    if geometry_error > tolerance or weight_error > 0.000001:
        raise ValueError(state + ": mesh positions or named vertex weights do not prove the same origin shift")
    return delta,global_delta,{"translation_armature_local":list(delta),"translation_world":list(global_delta),
        "linear_identity_max_error":linear_error,"bone_translation_residual_max":translation_error,
        "mesh_translation_residual_max":geometry_error,"named_weight_max_error":weight_error,
        "armature_world_max_error":world_error,"mesh_world_relationship_max_error":relationship_error,
        "mesh_vertices":len(a.vertices),"mesh_polygons":len(a.polygons)}


def canonicalize_origin(rig, mesh, delta, world_delta):
    # Transform the data as a whole so connected bones are not moved twice.
    rig.data.transform(Matrix.Translation(-delta))
    mesh_delta = mesh.matrix_world.inverted().to_3x3() @ world_delta
    mesh.data.transform(Matrix.Translation(-mesh_delta))
    mesh.data.update()
    rig.data.update_tag()
    bpy.context.view_layer.update()


def pose_samples(rig, mesh, action):
    rig.data.pose_position = "POSE"
    rig.animation_data_create()
    rig.animation_data.action = action
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    start,end = action.frame_range
    samples = []
    for fraction in (0.0,0.5,1.0):
        time = start+(end-start)*fraction
        frame = math.floor(time)
        bpy.context.scene.frame_set(frame,subframe=time-frame)
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = mesh.evaluated_get(graph)
        evaluated_mesh = evaluated.to_mesh(preserve_all_data_layers=False,depsgraph=graph)
        try:
            samples.append([evaluated.matrix_world@vertex.co for vertex in evaluated_mesh.vertices])
        finally:
            evaluated.to_mesh_clear()
    return samples


def transfer_action(actions, source_rig, base_rig, state):
    candidates = [action for action in actions if any(BONE_CURVE.fullmatch(curve.data_path) for curve in action.fcurves)]
    if len(candidates) != 1:
        raise ValueError(state + ": expected one unambiguous bone pose action, got " + str(len(candidates)))
    source = candidates[0]
    if not source.fcurves or source.frame_range[1] <= source.frame_range[0]:
        raise ValueError(state + ": bone action is empty or has zero duration")
    for obj in [source_rig, *source_rig.children_recursive]:
        action = obj.animation_data.action if obj.animation_data else None
        if action and any(curve.data_path in {"location", "rotation_euler", "rotation_quaternion", "scale"} for curve in action.fcurves):
            raise ValueError(state + ": object transform animation requires manual root-motion review")
    for curve in source.fcurves:
        match = BONE_CURVE.fullmatch(curve.data_path)
        if match is None or not curve.keyframe_points or curve.modifiers:
            raise ValueError(state + ": only keyed bone pose curves without modifiers are supported: " + curve.data_path)
        bone_name = ast.literal_eval(match.group(1))
        if bone_name not in base_rig.pose.bones or curve.array_index >= (4 if match.group(2) == "rotation_quaternion" else 3):
            raise ValueError(state + ": action channel does not match a base bone: " + curve.data_path)
        if source_rig.pose.bones[bone_name].rotation_mode != base_rig.pose.bones[bone_name].rotation_mode:
            raise ValueError(state + ": bone rotation mode differs: " + bone_name)
        if not all(math.isfinite(value) for point in curve.keyframe_points for value in point.co):
            raise ValueError(state + ": nonfinite animation keys")
    copied = source.copy()
    copied.use_fake_user = True
    start, end = copied.frame_range
    for curve in copied.fcurves:
        for point in curve.keyframe_points:
            point.co.x -= start
            point.handle_left.x -= start
            point.handle_right.x -= start
        curve.update()
    copied["source_state"] = state
    copied["loop_candidate_unverified"] = True
    return copied, {"source_action":source.name, "source_frames":[start,end], "duration_seconds":(end-start)/30.0,
                    "pose_curves":len(copied.fcurves), "loop_seam_verified":False}, source


def reset_action(rig):
    reset = bpy.data.actions.new("RESET")
    reset.id_root = "OBJECT"
    reset.use_fake_user = True
    reset["source"] = "generated_bind_pose_reset_not_a_motion"
    for bone in rig.pose.bones:
        rotation = "rotation_quaternion" if bone.rotation_mode == "QUATERNION" else "rotation_euler"
        for property_name, values in (("location", (0,0,0)), (rotation, (1,0,0,0) if rotation == "rotation_quaternion" else (0,0,0)), ("scale", (1,1,1))):
            for index, value in enumerate(values):
                curve = reset.fcurves.new(bone.path_from_id(property_name), index=index, action_group=bone.name)
                for frame in (0, 1):
                    curve.keyframe_points.insert(frame, value).interpolation = "LINEAR"
    return reset


def export_options(path):
    properties = bpy.ops.export_scene.gltf.get_rna_type().properties
    flags = {"filepath":str(path), "export_format":"GLB", "use_selection":True, "use_renderable":True,
             "export_yup":True, "export_apply":False, "export_animations":True,
             "export_animation_mode":"ACTIONS", "export_anim_single_armature":True,
             "export_force_sampling":True, "export_frame_range":False, "export_frame_step":1,
             "export_optimize_animation_size":False, "export_nla_strips":False, "export_extras":True}
    missing = sorted(set(flags)-set(properties.keys()))
    if missing:
        raise ValueError("Blender exporter does not support required options: " + ", ".join(missing))
    if "ACTIONS" not in {item.identifier for item in properties["export_animation_mode"].enum_items}:
        raise ValueError("Exporter does not support all-Actions animation mode")
    return flags


def main():
    args = arguments()
    if not bpy.app.background or bpy.app.version[:3] != (4,3,2):
        raise ValueError("Use a separate Blender 4.3.2 background process for the verified FCurve pipeline")
    sources = [args.base, *args.motions.values()]
    if any(not path.is_file() or path.suffix.lower() != ".glb" for path in sources):
        raise ValueError("Every source must be an existing .glb file")
    report_path = args.output.with_suffix(".preparation.json")
    if args.output in sources or report_path in sources or args.output.exists() or report_path.exists() or args.output.suffix.lower() != ".glb":
        raise ValueError("Output GLB and report must be separate new files; existing files are never replaced")
    source_hashes = {path:digest(path) for path in sources}
    SOURCE_HASHES.update(source_hashes)
    source_documents = {path:glb_json(path) for path in sources}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.context.scene.render.fps_base = 1.0
    base_objects, base_actions = import_asset(args.base)
    base_rig = armature(base_objects, "base")
    base_objects, helpers = without_helpers(base_objects, base_rig)
    base_mesh = body_mesh(base_objects,"base")
    base_rig.data.pose_position = "REST"
    for obj in base_objects:
        obj.animation_data_clear()
    for action in base_actions:
        bpy.data.actions.remove(action, do_unlink=True)
    bpy.context.view_layer.update()
    original_bounds = rest_bounds(base_objects)
    reports = {}
    merged = []
    for state in ("idle", "walk", "run"):
        objects, actions = import_asset(args.motions[state])
        source_rig = armature(objects, state)
        source_objects, _ = without_helpers(objects,source_rig)
        source_mesh = body_mesh(source_objects,state)
        copied, detail, source_action = transfer_action(actions, source_rig, base_rig, state)
        source_samples = pose_samples(source_rig,source_mesh,source_action)
        delta,world_delta,proof = origin_proof(base_rig,source_rig,base_mesh,source_mesh,args.tolerance,state)
        if delta.length > args.tolerance:
            if not args.normalize_origin_translation:
                raise ValueError(state + ": proven origin translation requires explicit --normalize-origin-translation")
            canonicalize_origin(source_rig,source_mesh,delta,world_delta)
        error = compare_rigs(base_rig, source_rig, args.tolerance, state)
        _,_,after_proof = origin_proof(base_rig,source_rig,base_mesh,source_mesh,args.tolerance,state)
        normalized_samples = pose_samples(source_rig,source_mesh,source_action)
        target_samples = pose_samples(base_rig,base_mesh,copied)
        pose_errors = []
        normalized_errors = []
        for original,normalized,target in zip(source_samples,normalized_samples,target_samples):
            if len(original) != len(normalized) or len(original) != len(target):
                raise ValueError(state + ": evaluated mesh topology changed during pose comparison")
            pose_errors.append(max((source-world_delta-result).length for source,result in zip(original,target)))
            normalized_errors.append(max((source-world_delta-result).length for source,result in zip(original,normalized)))
        if max([*pose_errors,*normalized_errors]) > 0.0001:
            raise ValueError(state + ": evaluated source/target vertex error exceeds 1e-4: " + repr(pose_errors))
        base_rig.animation_data.action = None
        base_rig.data.pose_position = "REST"
        bpy.context.view_layer.update()
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for action in actions:
            bpy.data.actions.remove(action, do_unlink=True)
        copied.name = state
        if copied.name != state:
            raise ValueError("Action name collision: " + state)
        merged.append(copied)
        reports[state] = {**detail, "source":str(args.motions[state]), "rest_matrix_error_max":error,
                         "origin_normalization":proof,"normalized_strict_proof":after_proof,
                         "origin_translation_applied_in_memory":delta.length > args.tolerance,
                         "sample_fractions":[0.0,0.5,1.0],"source_to_target_vertex_errors":pose_errors,
                         "source_to_normalized_vertex_errors":normalized_errors,"pose_validation_tolerance":0.0001}
    reset_action(base_rig)
    wrapper = bpy.data.objects.new("CandidateUniformScale", None)
    bpy.context.scene.collection.objects.link(wrapper)
    for obj in [obj for obj in base_objects if obj.parent not in base_objects]:
        world_matrix = obj.matrix_world.copy()
        obj.parent = wrapper
        obj.matrix_world = world_matrix
    factor = args.height/original_bounds["height"]
    for state,detail in reports.items():
        detail["target_scale_vertex_errors"] = [error*factor for error in detail["source_to_target_vertex_errors"]]
        if max(detail["target_scale_vertex_errors"]) > 0.0001:
            raise ValueError(state + ": evaluated pose error exceeds 1e-4 at target world scale")
    wrapper.scale = (factor,factor,factor)
    bpy.context.view_layer.update()
    scaled_bounds = rest_bounds(base_objects)
    grounding_offset = -scaled_bounds["min"][2] if args.ground_rest_feet else 0.0
    if args.ground_rest_feet:
        wrapper.location.z = grounding_offset
        bpy.context.view_layer.update()
        scaled_bounds = rest_bounds(base_objects)
    if abs(scaled_bounds["height"]-args.height) > max(0.0001,args.height*0.0001):
        raise ValueError("Uniform wrapper did not produce the requested rest height")
    if args.ground_rest_feet and abs(scaled_bounds["min"][2]) > 0.0001:
        raise ValueError("Static grounding wrapper did not place the rest floor at Z=0")
    base_rig.data.pose_position = "POSE"
    base_rig.animation_data_create()
    base_rig.animation_data.action = merged[0]
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [wrapper,*base_objects]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base_rig
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-",dir=args.output.parent) as staging:
        staged = Path(staging)/args.output.name
        flags = export_options(staged)
        bpy.ops.export_scene.gltf(**flags)
        exported = glb_json(staged)
        names = [animation.get("name", "") for animation in exported.get("animations", [])]
        if set(names) != STATES|{"RESET"} or len(names) != 4 or not exported.get("skins"):
            raise ValueError("Exporter did not preserve exactly idle/walk/run/RESET and a skin: " + repr(names))
        generated_objects, _ = import_asset(staged)
        generated_rig = armature(generated_objects,"reimported candidate")
        generated_objects, _ = without_helpers(generated_objects,generated_rig)
        generated_rig.data.pose_position = "REST"
        for obj in generated_objects:
            obj.animation_data_clear()
        bpy.context.view_layer.update()
        verified_bounds = rest_bounds(generated_objects)
        if abs(verified_bounds["height"]-args.height) > max(0.0001,args.height*0.0001):
            raise ValueError("Reimported GLB height differs from the requested height")
        if args.ground_rest_feet and abs(verified_bounds["min"][2]) > 0.0001:
            raise ValueError("Reimported GLB rest floor is not Z=0")
        if source_hashes != {path:digest(path) for path in sources}:
            raise ValueError("An input changed during preparation; output will not be published")
        report = {"status":"prepared_candidate_not_animation_or_visual_approval", "blender":bpy.app.version_string,
                  "sources":[{"path":str(path),"sha256":source_hashes[path],"unchanged":True,
                              "skins":len(source_documents[path].get("skins",[])),"clips":len(source_documents[path].get("animations",[]))} for path in sources],
                  "base_mesh_and_materials":"retained from base; motion meshes are not exported", "excluded_import_helpers":helpers,
                  "height":{"source_rest_m":original_bounds["height"],"uniform_wrapper_scale":factor,"target_m":args.height,
                            "reimported_rest_m":verified_bounds["height"],"bounds":verified_bounds,"recentered_xy":False,
                            "ground_rest_feet":args.ground_rest_feet,"wrapper_translation_blender":[0.0,0.0,grounding_offset]},
                  "bones":len(base_rig.data.bones),"motions":reports,"exported_clips":names,
                  "reset":"Generated identity bone pose curves, two identical keys at frames 0 and 1; not an extra motion",
                  "export_flags":{key:value for key,value in flags.items() if key!="filepath"},
                  "loop_configuration":"glTF has no standard loop flag. Inspect foot/root seams, then configure Godot idle/walk/run loop modes; RESET must not loop",
                  "output_sha256":digest(staged), "limitations":["Only three locomotion candidates; the nine required gameplay clips are not complete",
                      "Bone pose curves and matching rest transforms do not prove foot contact, seamless loops, visual quality or gameplay timing",
                      "No object root-motion curves or gameplay events were added"]}
        staged_report = Path(staging)/report_path.name
        staged_report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        os.link(staged,args.output) # Atomic creation; fails rather than replacing an existing file.
        try:
            os.link(staged_report,report_path)
        except Exception:
            args.output.unlink()
            raise
    print("RUNEFALL_CHARACTER_CANDIDATE_OK: "+str(args.output),flush=True)


if __name__ == "__main__":
    exit_code = 0
    try:
        main()
    except SystemExit as error:
        exit_code = int(error.code or 0)
    except Exception:
        traceback.print_exc()
        exit_code = 1
    finally:
        try:
            if SOURCE_HASHES != {path:digest(path) for path in SOURCE_HASHES}:
                raise RuntimeError("Source SHA-256 changed during preparation")
            if SOURCE_HASHES:
                print("RUNEFALL_CHARACTER_SOURCES_UNCHANGED: %d files" % len(SOURCE_HASHES), flush=True)
        except Exception:
            traceback.print_exc()
            exit_code = 1
        sys.stdout.flush()
        sys.stderr.flush()
    if exit_code:
        os._exit(exit_code) # Blender otherwise may return 0 after Python failures.
