"""Project-authored in-place gait clips for the reviewed VARCO humanoid rigs.

This module reads rest anatomy, never provider animation curves. Blender world
axes are X right on screen, -Y character forward, +Z up. Gameplay owns horizontal
translation; planted-foot metrics add a simulated gameplay translation only in
the report. Source files are never saved or overwritten.

author_locomotion(rig, height_m, walk_speed=6.4, run_speed=8.5,
                  upper_body_callback=None, fps=100, include_idle=True)
returns {"actions": {name: bpy.types.Action}, "reports": {name: dict}}.
The callback receives (rig, seconds, state) after pelvis placement and before
leg IK. It may pose spine/head/arms/fingers but must not change hips or legs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


UP = Vector((0.0, 0.0, 1.0))
FORWARD = Vector((0.0, -1.0, 0.0))
LEG_NAMES = {side: (side + "UpLeg", side + "Leg", side + "Foot", side + "ToeBase")
             for side in ("Left", "Right")}


def _world_rest(rig, name):
    return rig.matrix_world @ rig.data.bones[name].matrix_local


def _reset(rig):
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)


def set_world_pose(rig, name, head, rotation):
    """Set a bone in world meters while preserving the rig's uniform scale."""
    scale = rig.matrix_world.to_scale()
    desired = Matrix.LocRotScale(Vector(head), rotation, scale)
    rig.pose.bones[name].matrix = rig.matrix_world.inverted() @ desired
    bpy.context.view_layer.update()


def _aim(rest_matrix, direction):
    rest_rotation = rest_matrix.to_quaternion()
    axis = rest_rotation @ Vector((0.0, 1.0, 0.0))
    return axis.rotation_difference(direction.normalized()) @ rest_rotation


def solve_chain_world(rig, upper, lower, target, pole, rest):
    """Analytic two-bone IK, no stretch and no persistent IK constraints."""
    hip = rig.matrix_world @ rig.pose.bones[upper].head
    a = (rest[lower].translation - rest[upper].translation).length
    end_name = lower.replace("Leg", "Foot") if lower.endswith("Leg") else None
    if end_name is None or end_name not in rest:
        raise ValueError("Gait solver requires a leg->foot chain")
    b = (rest[end_name].translation - rest[lower].translation).length
    vector = Vector(target) - hip
    requested = vector.length
    distance = min(max(requested, abs(a - b) + 1e-5), a + b - 1e-5)
    direction = vector.normalized() if requested > 1e-8 else Vector((0, 0, -1))
    reached = hip + direction * distance
    projected = Vector(pole) - direction * Vector(pole).dot(direction)
    if projected.length_squared < 1e-10:
        projected = Vector((1, 0, 0)) - direction * direction.x
    projected.normalize()
    along = (a * a - b * b + distance * distance) / (2 * distance)
    bend = math.sqrt(max(0.0, a * a - along * along))
    knee = hip + direction * along + projected * bend
    set_world_pose(rig, upper, hip, _aim(rest[upper], knee - hip))
    set_world_pose(rig, lower, knee, _aim(rest[lower], reached - knee))
    return reached, max(0.0, requested - distance)


def _hermite(p0, p1, m0, m1, phase):
    s = phase
    return ((2*s**3 - 3*s*s + 1)*p0 + (s**3 - 2*s*s + s)*m0
            + (-2*s**3 + 3*s*s)*p1 + (s**3 - s*s)*m1)


def _foot_path(phase, speed, duration, duty, lift):
    """Flat stance has exactly -speed velocity; swing meets that derivative."""
    lead = speed * duration * duty * 0.5
    if phase <= duty:
        return lead - speed * duration * phase, 0.0, True
    swing = (phase - duty) / (1.0 - duty)
    derivative = -speed * duration * (1.0 - duty)
    distance = _hermite(-lead, lead, derivative, derivative, swing)
    height = lift * math.sin(math.pi * swing) ** 2
    return distance, height, False


def _key_all(rig, frame, previous_quaternions):
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
        quat = bone.rotation_quaternion.copy()
        previous = previous_quaternions.get(bone.name)
        if previous is not None and quat.dot(previous) < 0.0:
            quat.negate()
            bone.rotation_quaternion = quat
        previous_quaternions[bone.name] = quat
        bone.keyframe_insert("location", frame=frame, group=bone.name)
        bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
        bone.keyframe_insert("scale", frame=frame, group=bone.name)


def _body_meshes(rig):
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"
            and any(mod.type == "ARMATURE" and mod.object == rig for mod in obj.modifiers)]


def _sole_samples(rig, meshes, rest_floor):
    samples = {side: [] for side in LEG_NAMES}
    graph = bpy.context.evaluated_depsgraph_get()
    for mesh in meshes:
        group_names = {group.index: group.name for group in mesh.vertex_groups}
        evaluated = mesh.evaluated_get(graph)
        cooked = evaluated.to_mesh()
        try:
            if len(cooked.vertices) != len(mesh.data.vertices):
                raise ValueError("Gait sole audit needs unchanged evaluated vertex topology")
            for side in LEG_NAMES:
                relevant = {side + "Foot", side + "ToeBase"}
                candidates = []
                for vertex in mesh.data.vertices:
                    weight = sum(item.weight for item in vertex.groups
                                 if group_names[item.group] in relevant)
                    if weight < 0.98:
                        continue
                    point = evaluated.matrix_world @ cooked.vertices[vertex.index].co
                    if point.z <= rest_floor + 0.025:
                        candidates.append(vertex.index)
                # Deterministic representative vertices, without retaining the mesh.
                count = min(32, len(candidates))
                indices = sorted({candidates[int(i * len(candidates) / count)] for i in range(count)}) if count else []
                if candidates:
                    lowest = min(candidates, key=lambda index:(evaluated.matrix_world @ cooked.vertices[index].co).z)
                    if lowest not in indices:
                        if len(indices) == 32:
                            indices.pop()
                        indices.append(lowest)
                samples[side].extend((mesh, index) for index in indices)
        finally:
            evaluated.to_mesh_clear()
    return samples


def _sample_soles(samples):
    result = {side: [] for side in samples}
    by_mesh = {}
    for side, items in samples.items():
        for mesh, index in items:
            by_mesh.setdefault(mesh, []).append((side, index))
    graph = bpy.context.evaluated_depsgraph_get()
    for mesh, items in by_mesh.items():
        evaluated = mesh.evaluated_get(graph)
        cooked = evaluated.to_mesh()
        try:
            for side, index in items:
                result[side].append(evaluated.matrix_world @ cooked.vertices[index].co)
        finally:
            evaluated.to_mesh_clear()
    return result


def _matrix_error(first, second):
    return max(abs(first[row][col] - second[row][col])
               for row in range(4) for col in range(4))


def author_locomotion(rig, height_m, walk_speed=6.4, run_speed=8.5,
                      upper_body_callback=None, fps=100, include_idle=True, include_samples=False):
    if rig.type != "ARMATURE" or not math.isfinite(height_m) or height_m <= 0:
        raise ValueError("Expected a humanoid armature and finite positive height")
    needed = {"Root", "Hips", "Spine", *[name for names in LEG_NAMES.values() for name in names]}
    missing = needed - set(rig.pose.bones.keys())
    if missing:
        raise ValueError("Missing gait bones: " + ", ".join(sorted(missing)))
    scale = rig.matrix_world.to_scale()
    if min(scale) <= 0 or max(scale) - min(scale) > 1e-5:
        raise ValueError("Gait authoring requires positive uniform rig scale")
    if fps < 30 or any(not math.isfinite(x) or x <= 0 for x in (walk_speed, run_speed)):
        raise ValueError("Expected >=30 authoring fps and finite positive speeds")
    bpy.context.scene.render.fps = fps
    bpy.context.scene.render.fps_base = 1.0
    rig.animation_data_create()
    rig.animation_data.action = None
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
    rig.data.pose_position = "POSE"
    _reset(rig)
    bpy.context.view_layer.update()
    rest = {bone.name: _world_rest(rig, bone.name) for bone in rig.data.bones}
    meshes = _body_meshes(rig)
    graph = bpy.context.evaluated_depsgraph_get()
    all_points = []
    for mesh in meshes:
        evaluated = mesh.evaluated_get(graph)
        cooked = evaluated.to_mesh()
        try:
            all_points.extend(evaluated.matrix_world @ vertex.co for vertex in cooked.vertices)
        finally:
            evaluated.to_mesh_clear()
    floor = min((point.z for point in all_points), default=0.0)
    sole_samples = _sole_samples(rig, meshes, floor)
    factor = height_m / 1.82
    walk_duration = 0.48 if walk_speed >= 5 else 0.70
    run_duration = 0.40 if run_speed >= 5 else 0.70
    definitions = [
        ("walk", Vector((0,-1,0)), walk_speed, walk_duration, 0.0),
        ("run", Vector((0,-1,0)), run_speed, run_duration, 0.0),
        ("walk_back", Vector((0,1,0)), walk_speed, walk_duration, 0.0),
        ("walk_left", Vector((1,0,0)), walk_speed, walk_duration, 0.55),
        ("walk_right", Vector((-1,0,0)), walk_speed, walk_duration, -0.55),
    ]
    if include_idle:
        definitions.insert(0, ("idle", Vector((0,0,0)), 0.0, 1.8, 0.0))
    actions, reports = {}, {}
    for state, direction, speed, duration, yaw in definitions:
        action = bpy.data.actions.new("RUNEFALL_" + state)
        rig.animation_data.action = action
        count = max(2, round(duration * fps))
        duration = count / fps
        duty = 0.28
        crouch = (0.18 if state == "run" and speed >= 5 else 0.155) * factor
        if speed < 5:
            crouch = 0.095 * factor
        if state == "idle":
            crouch = 0.045 * factor
        bob = (0.022 if speed >= 5 else 0.012) * factor
        hip_rotation = Quaternion(UP, yaw) @ rest["Hips"].to_quaternion()
        lateral = Quaternion(UP, yaw) @ Vector((1,0,0))
        forward = Quaternion(UP, yaw) @ FORWARD
        first_pose = None
        previous_quaternions = {}
        records, reach_max = [], 0.0
        rig["_gait_duration"] = duration
        rig["_gait_pelvis_yaw"] = yaw
        for sample in range(count + 1):
            time = duration * sample / count
            phase = (time / duration) % 1.0
            bpy.context.scene.frame_set(math.floor(time*fps), subframe=time*fps % 1)
            _reset(rig)
            drop = -crouch - bob * math.cos(4*math.pi*(phase-duty*0.5)) if speed else -crouch
            hip = rest["Hips"].translation + UP * drop
            set_world_pose(rig, "Hips", hip, hip_rotation)
            rig["_gait_phase"] = phase
            rig["_gait_pelvis_offset_world"] = [0.0, 0.0, drop]
            intended_hips = rig.pose.bones["Hips"].matrix_basis.copy()
            if upper_body_callback is not None:
                upper_body_callback(rig, time, state)
            if (_matrix_error(rig.pose.bones["Root"].matrix_basis, Matrix.Identity(4)) > 1e-6
                    or _matrix_error(rig.pose.bones["Hips"].matrix_basis, intended_hips) > 1e-6):
                raise ValueError("Upper-body gait callback may not change Root or Hips")
            foot_phases = {}
            for side, (upper, lower, foot, toe) in LEG_NAMES.items():
                offset = 0.0 if side == "Left" else 0.5
                raw_phase = time / duration + offset
                leg_phase = raw_phase % 1.0
                distance, lift, stance = _foot_path(leg_phase, speed, duration, duty, 0.13*factor) if speed else (0.0,0.0,True)
                sign = 1.0 if side == "Left" else -1.0
                center = Vector((hip.x, hip.y, 0.0)) + lateral * sign * 0.13*factor - forward * 0.045*factor
                target = center + direction * distance
                target.z = rest[foot].translation.z + lift
                if not stance:
                    # Meeting the stance velocity at lift-off/landing makes
                    # swing overshoot its endpoints slightly. Raise that foot
                    # enough to stay within the measured two-bone reach rather
                    # than stretching the leg or silently clipping its path.
                    leg_hip = rig.matrix_world @ rig.pose.bones[upper].head
                    reach = ((rest[lower].translation-rest[upper].translation).length
                             + (rest[foot].translation-rest[lower].translation).length - 0.008*factor)
                    horizontal = Vector((target.x-leg_hip.x,target.y-leg_hip.y,0.0)).length
                    if horizontal >= reach:
                        raise ValueError("Authored swing exceeds horizontal leg reach: " + state)
                    reachable_z = leg_hip.z - math.sqrt(reach*reach-horizontal*horizontal)
                    # Smooth maximum avoids a sharp ankle-velocity kink where
                    # the ordinary swing arc meets the anatomical envelope.
                    target.z = 0.5*(target.z+reachable_z+math.sqrt((target.z-reachable_z)**2+(0.003*factor)**2))
                reached, reach_error = solve_chain_world(rig, upper, lower, target, forward, rest)
                reach_max = max(reach_max, reach_error)
                foot_rotation = Quaternion(UP, yaw) @ rest[foot].to_quaternion()
                set_world_pose(rig, foot, reached, foot_rotation)
                foot_phases[side] = {"phase":leg_phase,"stance":stance,"cycle":math.floor(raw_phase+1e-8),
                                     "ankle":list(reached),"target":list(target),"reach_error_m":reach_error}
            bpy.context.view_layer.update()
            if first_pose is None:
                first_pose = {bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones}
            if sample == count:
                for name, basis in first_pose.items():
                    rig.pose.bones[name].matrix_basis = basis.copy()
                bpy.context.view_layer.update()
            _key_all(rig, time*fps, previous_quaternions)
            soles = _sample_soles(sole_samples)
            for side, points in soles.items():
                foot_phases[side]["skinned_sole_points"] = [list(p) for p in points]
            records.append({"t":time,"feet":foot_phases})
        for curve in action.fcurves:
            curve.extrapolation = "CONSTANT"
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
        endpoint_error = max(_matrix_error(first_pose[bone.name], bone.matrix_basis) for bone in rig.pose.bones)
        stance_groups = {}
        for record in records:
            translation = direction * speed * record["t"]
            for side, foot in record["feet"].items():
                if foot["stance"]:
                    key = (side, foot["cycle"])
                    stance_groups.setdefault(key, []).append((record["t"], [Vector(p)+translation for p in foot["skinned_sole_points"]]))
        drift = floor_error = 0.0
        for group in stance_groups.values():
            if not group or not group[0][1]:
                continue
            baseline = group[0][1]
            for _, points in group:
                for first, point in zip(baseline, points):
                    drift = max(drift, (point-first).length)
                if points:
                    floor_error = max(floor_error, abs(min(point.z for point in points)-floor))
        reports[state] = {"duration_s":duration,"reference_speed_m_s":speed,"sample_fps":fps,
            "source":"project_authored_analytic_leg_ik; provider curves were not read",
            "direction_blender_world":list(direction),"pelvis_yaw_rad":yaw,"pelvis_drop_m":crouch,
            "stance_duty_per_foot":duty if speed else 1.0,"stance_time_s":duration*duty if speed else duration,
            "max_target_reach_clamp_m":reach_max,"loop_endpoint_bone_matrix_error":endpoint_error,
            "skinned_sole_samples_per_foot":{side:len(items) for side,items in sole_samples.items()},
            "skinned_stance_world_drift_m":drift,"skinned_stance_floor_max_abs_m":floor_error,
            "horizontal_root_animation":"constant bind Root channels only; gameplay translation simulated only for foot audit",
            "limitations":["Loop seam/contact metrics do not approve cross-state transitions, cloth intersections, rendered style or hardware performance"]}
        if include_samples:
            reports[state]["samples"] = records
        actions[state] = action
    return {"actions":actions,"reports":reports}


def _cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--height", type=float, default=1.82)
    parser.add_argument("--walk-speed", type=float, default=6.4)
    parser.add_argument("--run-speed", type=float, default=8.5)
    parser.add_argument("--fps", type=int, default=100)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.output.exists():
        raise ValueError("Refusing to overwrite gait report")
    before = hashlib.sha256(args.input.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(rigs) != 1:
        raise ValueError("Expected one source rig")
    result = author_locomotion(rigs[0], args.height, args.walk_speed, args.run_speed, fps=args.fps, include_samples=True)
    after = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if before != after:
        raise ValueError("Source changed during gait audit")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"source_sha256":before,"source_unchanged":True,"clips":result["reports"]},indent=2)+"\n")
    print("RUNEFALL_AUTHORED_GAIT_REPORT", args.output)


if __name__ == "__main__":
    _cli()
