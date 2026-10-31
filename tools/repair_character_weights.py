"""Local skin-weight repair without resampling or re-exporting the source GLB.

The binary writer changes ONLY JOINTS_0/WEIGHTS_0 accessor bytes. Mesh shape,
UVs, normals, images, rest transforms, inverse binds and animation data remain
byte-identical. Analysis samples every exported key plus interval midpoints.
This tool measures deformation; its output is not an AAA quality certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quat_matrix(q):
    x, y, z, w = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array(((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
                     (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
                     (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y))))


def slerp(a, b, t):
    a, b = a/np.linalg.norm(a), b/np.linalg.norm(b)
    dot = float(a @ b)
    if dot < 0:
        b, dot = -b, -dot
    if dot > .9995:
        q = (1-t)*a+t*b
        return q/np.linalg.norm(q)
    theta = math.acos(max(-1, min(1, dot)))
    return (math.sin((1-t)*theta)*a+math.sin(t*theta)*b)/math.sin(theta)


class Skin:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        self.raw = self.path.read_bytes()
        magic, version, length = struct.unpack_from('<III', self.raw)
        if (magic, version, length) != (0x46546C67, 2, len(self.raw)):
            raise ValueError('Requires a valid GLB 2.0')
        jl, jt = struct.unpack_from('<II', self.raw, 12)
        self.doc = json.loads(self.raw[20:20+jl])
        bl, bt = struct.unpack_from('<II', self.raw, 20+jl)
        if jt != 0x4E4F534A or bt != 0x004E4942:
            raise ValueError('Expected JSON + BIN chunks')
        self.bin_offset = 28+jl
        self.binary = memoryview(self.raw)[self.bin_offset:self.bin_offset+bl]
        self.cache = {}
        meshes = self.doc['meshes']
        if len(meshes) != 1 or len(meshes[0]['primitives']) != 1:
            raise ValueError('Explicit single-primitive source contract required')
        self.primitive = meshes[0]['primitives'][0]
        self.attrs = self.primitive['attributes']
        self.positions = self.accessor(self.attrs['POSITION']).astype(float)
        self.joints = self.accessor(self.attrs['JOINTS_0']).astype(int)
        self.weights = self.accessor(self.attrs['WEIGHTS_0']).astype(float)
        self.faces = self.accessor(self.primitive['indices']).reshape(-1, 3).astype(int)
        self.edges = np.unique(np.sort(np.concatenate((self.faces[:, [0, 1]],
                                                      self.faces[:, [1, 2]],
                                                      self.faces[:, [2, 0]])), axis=1), axis=0)
        self.skin = self.doc['skins'][0]
        self.joint_nodes = self.skin['joints']
        self.names = [self.doc['nodes'][i].get('name', str(i)) for i in self.joint_nodes]
        self.inverse_binds = self.accessor(self.skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        self.parents = {c: p for p, n in enumerate(self.doc['nodes']) for c in n.get('children', [])}
        self.animations = {a['name']: a for a in self.doc.get('animations', [])}
        self.rest = self.evaluate(None, 0)
        self.rest_lengths = np.linalg.norm(self.rest[self.edges[:, 1]]-self.rest[self.edges[:, 0]], axis=1)
        self.valid = self.rest_lengths > .0001

    def accessor(self, index):
        if index in self.cache:
            return self.cache[index]
        a = self.doc['accessors'][index]
        if a.get('sparse') or a.get('normalized'):
            raise ValueError('Explicit non-sparse, non-normalized source contract')
        view = self.doc['bufferViews'][a['bufferView']]
        dtype = {5120: '<i1', 5121: '<u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[a['componentType']]
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        size = np.dtype(dtype).itemsize
        offset = view.get('byteOffset', 0)+a.get('byteOffset', 0)
        result = np.ndarray((a['count'], width), dtype=dtype, buffer=self.binary,
                            offset=offset, strides=(view.get('byteStride', size*width), size)).copy()
        self.cache[index] = result
        return result

    def transforms(self, clip, time):
        nodes = self.doc['nodes']
        channels = {}
        if clip is not None:
            action = self.animations[clip]
            for channel in action['channels']:
                sampler = action['samplers'][channel['sampler']]
                ts = self.accessor(sampler['input']).ravel()
                values = self.accessor(sampler['output'])
                right = min(len(ts)-1, max(0, int(np.searchsorted(ts, time, side='right'))))
                left = max(0, right-1)
                u = max(0., min(1., (time-ts[left])/(ts[right]-ts[left]))) if ts[right] != ts[left] else 0.
                path = channel['target']['path']
                interpolation = sampler.get('interpolation', 'LINEAR')
                if interpolation == 'STEP':
                    value = values[left]
                elif interpolation == 'LINEAR':
                    value = slerp(values[left], values[right], u) if path == 'rotation' else (1-u)*values[left]+u*values[right]
                else:
                    raise ValueError('Unsupported interpolation '+interpolation)
                channels[(channel['target']['node'], path)] = value
        local = []
        for i, n in enumerate(nodes):
            if 'matrix' in n:
                matrix = np.array(n['matrix'], dtype=float).reshape(4, 4).T
            else:
                t = channels.get((i, 'translation'), n.get('translation', (0, 0, 0)))
                q = channels.get((i, 'rotation'), n.get('rotation', (0, 0, 0, 1)))
                s = channels.get((i, 'scale'), n.get('scale', (1, 1, 1)))
                matrix = np.eye(4)
                matrix[:3, :3] = quat_matrix(q) @ np.diag(s)
                matrix[:3, 3] = t
            local.append(matrix)
        world = {}
        def global_matrix(i):
            if i not in world:
                world[i] = global_matrix(self.parents[i]) @ local[i] if i in self.parents else local[i]
            return world[i]
        return np.array([global_matrix(i) for i in self.joint_nodes]) @ self.inverse_binds

    def evaluate(self, clip, time, joints=None, weights=None, matrices=None):
        joints = self.joints if joints is None else joints
        weights = self.weights if weights is None else weights
        matrices = self.transforms(clip, time) if matrices is None else matrices
        # glTF world-space skin result = worldJoint * inverseBind * localVertex.
        transformed = np.einsum('vkij,vj->vki', matrices[joints, :3, :3], self.positions)
        transformed += matrices[joints, :3, 3]
        return np.einsum('vki,vk->vi', transformed, weights)

    def samples(self, midpoints=True):
        for name, action in self.animations.items():
            ts = np.unique(np.concatenate([self.accessor(s['input']).ravel() for s in action['samplers']]))
            if midpoints:
                ts = np.unique(np.concatenate((ts, (ts[:-1]+ts[1:])*.5)))
            for time in ts:
                yield name, float(time)

    def vertex_record(self, i, posed):
        active_names = [self.names[j] for j, w in zip(self.joints[i], self.weights[i]) if w > .05]
        if any('Finger' in name for name in active_names):
            region = 'hand/finger skin'
        elif any('Arm' in name or 'Shoulder' in name for name in active_names):
            region = 'shoulder/arm or adjacent thorax'
        elif any('Spine' in name for name in active_names):
            region = 'thorax/abdomen'
        elif any('UpLeg' in name or name == 'Hips' for name in active_names):
            region = 'pelvis/upper-leg and attached clothing'
        else:
            region = 'inspect named weights and rest coordinates'
        return {'vertex': int(i), 'rest_world_xyz_m_y_up': self.rest[i].tolist(),
                'posed_world_xyz_m_y_up': posed[i].tolist(),
                'anatomical_region_estimate': region,
                'weights': {self.names[j]: float(w) for j, w in zip(self.joints[i], self.weights[i]) if w > 1e-7}}

    def edge_record(self, edge_index, clip, time, joints=None, weights=None):
        pose = self.evaluate(clip, time, joints, weights)
        e = self.edges[edge_index]
        rest = self.rest_lengths[edge_index]
        length = np.linalg.norm(pose[e[1]]-pose[e[0]])
        return {'edge_index': int(edge_index), 'clip': clip, 'time_s': float(time),
                'rest_length_mm': float(rest*1000), 'posed_length_mm': float(length*1000),
                'extension_mm': float((length-rest)*1000), 'ratio': float(length/rest),
                'vertices': [self.vertex_record(i, pose) for i in e]}


def summary(values):
    return {k: float(v) for k, v in zip(('min', 'p50', 'p90', 'p95', 'p99', 'p999', 'max'),
                                      np.quantile(values, (0, .5, .9, .95, .99, .999, 1)))}


def audit(skin, output, joints=None, weights=None, midpoints=True, top=40):
    edges, rest = skin.edges[skin.valid], skin.rest_lengths[skin.valid]
    all_indices = np.flatnonzero(skin.valid)
    max_ratio = np.zeros(len(edges))
    max_extension = np.full(len(edges), -np.inf)
    extrema_sample = np.zeros(len(edges), dtype=int)
    extension_sample = np.zeros(len(edges), dtype=int)
    samples, frames = [], []
    for count, (clip, time) in enumerate(skin.samples(midpoints)):
        points = skin.evaluate(clip, time, joints, weights)
        length = np.linalg.norm(points[edges[:, 1]]-points[edges[:, 0]], axis=1)
        ratio = length/rest
        extension = (length-rest)*1000
        extrema_sample[ratio > max_ratio] = count
        extension_sample[extension > max_extension] = count
        max_ratio = np.maximum(max_ratio, ratio)
        max_extension = np.maximum(max_extension, extension)
        samples.append((clip, time))
        frames.append({'clip': clip, 'time_s': time, 'ratio': summary(ratio),
                       'extension_mm': summary(extension)})
        if count % 200 == 0:
            print('Sample', count, clip, round(time, 4), 'max', round(float(ratio.max()), 3), flush=True)
    worst = np.argsort(max_ratio)[-top:][::-1]
    worst_abs = np.argsort(max_extension)[-top:][::-1]
    report = {'source': str(skin.path), 'source_sha256': sha(skin.raw),
              'coordinate_system': 'glTF world metres; X right, Y up, Z forward',
              'sampling': 'every exported timestamp and every adjacent midpoint' if midpoints else 'every exported timestamp',
              'sample_count': len(samples), 'vertex_count': len(skin.positions), 'triangle_count': len(skin.faces),
              'clip_count': len(skin.animations), 'clips': list(skin.animations),
              'edge_count': len(skin.edges), 'measured_edge_count': len(edges),
              'rest_length_floor_mm': .1, 'per_edge_max_ratio': summary(max_ratio),
              'per_edge_max_extension_mm': summary(max_extension),
              'worst_ratio_edges': [skin.edge_record(all_indices[i], *samples[extrema_sample[i]], joints, weights) for i in worst],
              'worst_absolute_extension_edges': [skin.edge_record(all_indices[i], *samples[extension_sample[i]], joints, weights) for i in worst_abs],
              'frames': frames,
              'limitations': ['Finite exported-key and midpoint samples do not prove a continuous bound.',
                              'Ratios and edge lengths require body/material closeups, not percentile-only art approval.']}
    output.write_text(json.dumps(report, indent=2)+'\n')
    np.savez_compressed(output.with_suffix('.npz'), source_sha256=np.array(sha(skin.raw)),
                        vertex_count=np.array(len(skin.positions)), edge_count=np.array(len(skin.edges)),
                        edges=all_indices, max_ratio=max_ratio,
                        max_extension_mm=max_extension, extrema_sample=extrema_sample,
                        extension_sample=extension_sample,
                        samples=np.array(samples, dtype=str))
    print('REPORT', output, report['per_edge_max_ratio'], flush=True)
    return report


def render_cases(source, output, cases_path):
    """Independent Blender import/deformation/render of exact GLB samples."""
    import bpy
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    import runpy
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError('Validated Blender 4.3.2 required')
    helper = runpy.run_path(str(Path(__file__).with_name('review_character_deformation.py')))
    cases = json.loads(cases_path.read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
    original = list(bpy.context.scene.objects)
    rig = next(o for o in original if o.type == 'ARMATURE')
    meshes = [o for o in original if o.type == 'MESH' and not o.hide_render
              and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    aliases = {}
    for track in rig.animation_data.nla_tracks:
        linked = {strip.action for strip in track.strips if strip.action}
        if len(linked) == 1:
            aliases[track.name] = next(iter(linked))
    for ob in original:
        if ob.animation_data:
            for track in ob.animation_data.nla_tracks:
                track.mute = True
            ob.animation_data.action = None
        if ob.type == 'MESH' and ob not in meshes:
            ob.hide_render = True
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    rest = []
    offsets = []
    for ob in meshes:
        ev = ob.evaluated_get(graph)
        me = ev.to_mesh()
        offsets.append(len(rest))
        rest.extend([ev.matrix_world @ v.co for v in me.vertices])
        ev.to_mesh_clear()
    tree = KDTree(len(rest))
    for i, p in enumerate(rest):
        tree.insert(p, i)
    tree.balance()
    skin = Skin(source)
    convert = lambda p: Vector((p[0], -p[2], p[1]))
    mapping = np.array([tree.find(convert(p))[1] for p in skin.rest])
    rest_errors = [tree.find(convert(p))[2] for p in skin.rest]
    camera, lights = helper['studio'](bpy.context.scene, 768, 768, 24)
    bpy.context.scene.render.threads = 1
    weapon_objects, weapon_roots = [], []
    if any(case.get('grip_view') for case in cases):
        sword = Path(__file__).resolve().parents[1]/'game/assets/models/production/rune_sword_web.glb'
        already = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(sword), import_pack_images=True)
        weapon_objects = [o for o in bpy.context.scene.objects if o not in already]
        weapon_roots = [o for o in weapon_objects if o.parent not in weapon_objects]
    validation = {'source_sha256': sha(skin.raw), 'bpy_rest_mapping_max_error_m': max(rest_errors), 'samples': []}
    for case in cases:
        action = aliases[case['clip']]
        rig.data.pose_position = 'POSE'
        rig.animation_data.action = action
        scene = bpy.context.scene
        frame = action.frame_range[0] + case['time_s']*scene.render.fps/scene.render.fps_base
        scene.frame_set(int(frame), subframe=frame-int(frame))
        bpy.context.view_layer.update()
        points = []
        for ob in meshes:
            ev = ob.evaluated_get(graph)
            me = ev.to_mesh()
            points.extend([ev.matrix_world @ v.co for v in me.vertices])
            ev.to_mesh_clear()
        pose = skin.evaluate(case['clip'], case['time_s'])
        errors = [float((points[mapping[i]]-convert(p)).length) for i, p in enumerate(pose)]
        # Both versions share fixed cameras centred on the BEFORE sample.
        center = convert(case.get('center_world_xyz_m_y_up', [0, 0, 0]))
        direction = convert(case.get('camera_direction_y_up', [.8, .2, 1.]))
        for ob in weapon_objects:
            ob.hide_render = not case.get('grip_view', False)
        if case.get('grip_view'):
            hand_world = rig.matrix_world @ rig.pose.bones['RightHand'].matrix
            scales = hand_world.to_scale()
            relative_scale = sum(scales)/3
            if max(scales)-min(scales) > 1e-5:
                raise ValueError('Uniform source rig scale required')
            physical = Vector(case['physical_socket_offset_m'])
            socket = helper['SOCKET_BASIS'].to_4x4()
            for axis in range(3):
                socket.col[axis] /= relative_scale
            socket.translation = physical/relative_scale
            for ob in weapon_roots:
                ob.matrix_world = hand_world @ socket @ helper['C']
            rotation = hand_world.to_quaternion().to_matrix()
            center = hand_world @ Vector((0, physical.y/relative_scale, physical.z/relative_scale))
            direction = rotation @ Vector((.7, .28, -1))
            bpy.context.view_layer.update()
        helper['capture'](output, case['name'], camera, lights, center, direction, case['scale_m'])
        validation['samples'].append({'case': case['name'], 'clip': case['clip'], 'time_s': case['time_s'],
                                      'bpy_vs_cpu_max_error_m': max(errors),
                                      'bpy_vs_cpu_p99_error_m': float(np.quantile(errors, .99))})
    (output/'blender-validation.json').write_text(json.dumps(validation, indent=2)+'\n')


def repair(skin, evidence_path, output, radius=.045, iterations=24):
    """Anatomical folding + bounded geodesic smoothing of measured defects.

    Adjacent source vertices exchange the fourth influence between unrelated
    bones across short edges. Coherent named-chain folding removes thigh
    influence from the thorax; a welded surface graph smooths only measured
    problem neighbourhoods. No Euclidean nearest-vertex shortcut bridges limbs.
    """
    source_evidence = json.loads(evidence_path.with_suffix('.json').read_text())
    if source_evidence['source_sha256'] != sha(skin.raw):
        raise ValueError('Repair evidence must belong to this exact immutable input')
    baseline = np.load(evidence_path)
    if ('source_sha256' in baseline and str(baseline['source_sha256']) != sha(skin.raw)):
        raise ValueError('NPZ source SHA does not match the input')
    if source_evidence['vertex_count'] != len(skin.positions) or source_evidence['edge_count'] != len(skin.edges):
        raise ValueError('Audit topology counts do not match the input')
    if not np.array_equal(baseline['edges'], np.flatnonzero(skin.valid)):
        raise ValueError('Audit measured-edge identity/order differs from the input')
    expected = np.array(list(skin.samples('midpoint' in source_evidence['sampling'])), dtype=str)
    if not np.array_equal(expected, baseline['samples']) or source_evidence['sample_count'] != len(expected):
        raise ValueError('Audit clip/time schedule differs from the input')
    for key, field in (('max_ratio', 'per_edge_max_ratio'), ('max_extension_mm', 'per_edge_max_extension_mm')):
        values = baseline[key]
        if values.shape != baseline['edges'].shape or not np.all(np.isfinite(values)):
            raise ValueError('Invalid audit extrema arrays')
        if any(not math.isclose(v, source_evidence[field][k], rel_tol=1e-12, abs_tol=1e-10)
               for k, v in summary(values).items()):
            raise ValueError('NPZ extrema do not belong to their corresponding JSON audit')
    ids = baseline['edges']
    bad = ids[(baseline['max_ratio'] > 2.) & (baseline['max_extension_mm'] > 8.)]
    worlds = skin.transforms(None, 0) @ np.linalg.inv(skin.inverse_binds)
    heads = {name: worlds[i, :3, 3] for i, name in enumerate(skin.names)}
    hip_y = heads['Hips'][1]
    arm_x = (abs(heads['LeftArm'][0])+abs(heads['RightArm'][0]))*.5
    spine_joints = [i for i, name in enumerate(skin.names) if name in ('Spine', 'Spine1', 'Spine2')]
    source_spine_support = np.where(np.isin(skin.joints, spine_joints), skin.weights, 0).sum(axis=1)
    # This candidate repairs the measured thorax defects only. The generated
    # glove and split tabard need separate art work; generic smoothing there
    # produced visible collateral deformation in rejected experiments.
    torso_source = ((skin.rest[:, 1] > hip_y+.035) &
                    (skin.rest[:, 1] < heads['Neck'][1]-.08) &
                    (np.abs(skin.rest[:, 0]) < arm_x+.04) & (source_spine_support > .55))
    bad = bad[np.all(torso_source[skin.edges[bad]], axis=1)]
    # UV/normal splits at identical world positions need identical repair. This
    # changes weights, never geometry, indices, UVs, or exported vertex order.
    _, inverse = np.unique(np.round(skin.rest, 6), axis=0, return_inverse=True)
    count = int(inverse.max())+1
    group_count = np.bincount(inverse)
    dense = np.zeros((len(skin.positions), len(skin.names)))
    np.put_along_axis(dense, skin.joints, skin.weights, axis=1)
    grouped = np.zeros((count, len(skin.names)))
    np.add.at(grouped, inverse, dense)
    grouped /= group_count[:, None]
    spine_support = grouped[:, spine_joints].sum(axis=1)
    support_fade = np.clip((spine_support-.55)/.15, 0, 1)
    positions = np.zeros((count, 3))
    np.add.at(positions, inverse, skin.rest)
    positions /= group_count[:, None]
    torso = ((positions[:, 1] > hip_y+.035) &
             (positions[:, 1] < heads['Neck'][1]-.08) &
             (np.abs(positions[:, 0]) < arm_x+.04) & (spine_support > .55))
    welded_edges = np.unique(np.sort(inverse[skin.edges], axis=1), axis=0)
    welded_edges = welded_edges[welded_edges[:, 0] != welded_edges[:, 1]]
    edge_lengths = np.linalg.norm(positions[welded_edges[:, 0]]-positions[welded_edges[:, 1]], axis=1)
    adjacency = [[] for _ in range(count)]
    for (a, b), length in zip(welded_edges, edge_lengths):
        adjacency[a].append((int(b), float(length)))
        adjacency[b].append((int(a), float(length)))
    seeds = np.unique(inverse[skin.edges[bad]].ravel())
    distances = np.full(count, np.inf)
    queue = []
    for i in seeds:
        distances[i] = 0
        heapq.heappush(queue, (0., int(i)))
    while queue:
        distance, i = heapq.heappop(queue)
        if distance != distances[i] or distance > radius:
            continue
        for j, length in adjacency[i]:
            if not torso[j]:
                continue
            candidate = distance+length
            if candidate < distances[j] and candidate <= radius:
                distances[j] = candidate
                heapq.heappush(queue, (candidate, j))
    blend = np.cos(np.minimum(distances/radius, 1)*math.pi*.5)**2
    blend[~np.isfinite(distances)] = 0
    blend *= support_fade
    names = {name: i for i, name in enumerate(skin.names)}
    y = positions[:, 1]
    fold_log = []

    def transfer(source, destination, factor, reason):
        factor = np.clip(factor, 0, 1)
        amount = grouped[:, names[source]]*factor
        grouped[:, names[source]] -= amount
        grouped[:, names[destination]] += amount
        fold_log.append({'source_bone': source, 'destination_bone': destination, 'reason': reason,
                         'welded_vertices': int(np.count_nonzero(amount > 1e-7)),
                         'maximum_transferred_weight': float(amount.max())})

    # Upper-thigh bones should not pull a breastplate or upper abdomen. Fade
    # across the anatomical pelvis-to-thorax span: a short height cutoff would
    # create a new strain band at the waist even while fixing the chest.
    leg_start, leg_end = hip_y-.05, heads['Spine1'][1]+.035
    leg_fold = np.clip((y-leg_start)/(leg_end-leg_start), 0, 1)
    leg_fold = leg_fold*leg_fold*(3-2*leg_fold)
    torso_fade = np.clip((y-hip_y-.035)/.08, 0, 1)
    torso_fade *= np.clip((heads['Neck'][1]-.08-y)/.05, 0, 1)
    torso_fade *= np.clip((arm_x+.04-np.abs(positions[:, 0]))/.06, 0, 1)
    # A thigh-owned tasset can sit above the hip in REST. Spatial height alone
    # must never convert that valid rigid attachment into torso weighting.
    torso_fade *= support_fade
    leg_fold *= torso_fade
    for side in ('Left', 'Right'):
        transfer(side+'UpLeg', 'Hips', leg_fold,
                 'remove anatomically remote thigh influence above the pelvis')
    lateral = np.clip((arm_x+.04-np.abs(positions[:, 0]))/.06, 0, 1)
    upper_torso = np.clip((y-heads['Spine1'][1]+.025)/.045, 0, 1)*lateral
    upper_torso *= torso_fade
    transfer('Spine', 'Spine1', upper_torso,
             'coherent upper-thorax spine chain removes abrupt fourth-influence exchange')
    transfer('Hips', 'Spine1', upper_torso,
             'upper-thorax spine chain replaces remote pelvic/thigh influence')

    # Add directly folded vertices as geodesic repair centres too: their named
    # chain correction must fade through the actual local surface, not jump at
    # a UV split. Source skeleton and every clip key stay unchanged.
    rows = np.concatenate((welded_edges[:, 0], welded_edges[:, 1]))
    cols = np.concatenate((welded_edges[:, 1], welded_edges[:, 0]))
    graph_weight = np.tile(1/np.maximum(edge_lengths, .005), 2)
    degree = np.bincount(rows, weights=graph_weight, minlength=count)
    corrected = grouped.copy()
    smoothing = .65*blend
    for _ in range(iterations):
        average = np.zeros_like(corrected)
        np.add.at(average, rows, corrected[cols]*graph_weight[:, None])
        average /= np.maximum(degree, 1e-30)[:, None]
        corrected = corrected*(1-smoothing[:, None])+average*smoothing[:, None]
    corrected = np.maximum(corrected, 0)
    corrected /= corrected.sum(axis=1, keepdims=True)
    # Keep exactly four allocated slots; zero slots retain a valid joint index.
    selected = np.argsort(corrected, axis=1)[:, -4:][:, ::-1]
    values = np.take_along_axis(corrected, selected, axis=1)
    values /= values.sum(axis=1, keepdims=True)
    joints = selected[inverse].astype(np.uint8)
    weights = values[inverse].astype('<f4')
    actual_dense = np.zeros_like(dense)
    np.put_along_axis(actual_dense, joints, weights, axis=1)
    changed = np.max(np.abs(actual_dense-dense), axis=1) > 1e-6
    # Preserve even the byte representation/order/rounding for untouched skin.
    joints[~changed] = skin.joints[~changed]
    weights[~changed] = skin.weights[~changed]
    output.mkdir(parents=True, exist_ok=True)
    result = output/(skin.path.stem+'-weights.glb')
    if result.exists() or result.resolve() == skin.path:
        raise ValueError('Repair output must be new, source immutable')
    raw = bytearray(skin.raw)
    changed_ranges = []
    for name, array in (('JOINTS_0', joints), ('WEIGHTS_0', weights)):
        accessor = skin.doc['accessors'][skin.attrs[name]]
        view = skin.doc['bufferViews'][accessor['bufferView']]
        if view.get('byteStride') or accessor.get('byteOffset', 0):
            raise ValueError('Writer contract requires tightly packed source weights')
        start = skin.bin_offset+view.get('byteOffset', 0)
        payload = array.tobytes()
        if len(payload) != view['byteLength']:
            raise ValueError('Writer refuses layout changes')
        raw[start:start+len(payload)] = payload
        changed_ranges.append((start, start+len(payload), name))
    # Verify every byte outside the two explicitly allowed attribute ranges.
    cursor = 0
    for start, end, name in sorted(changed_ranges):
        if raw[cursor:start] != skin.raw[cursor:start]:
            raise AssertionError('Non-weight bytes changed')
        cursor = end
    if raw[cursor:] != skin.raw[cursor:]:
        raise AssertionError('Non-weight bytes changed')
    result.write_bytes(raw)
    metadata = {'source': str(skin.path), 'source_sha256': sha(skin.raw), 'output': str(result),
                'output_sha256': sha(raw), 'source_byte_count': len(skin.raw), 'output_byte_count': len(raw),
                'byte_identical_except': [{'attribute': name, 'start': start, 'end_exclusive': end} for start, end, name in changed_ranges],
                'preserved_byte_exact': ['POSITION', 'NORMAL', 'TEXCOORD_0', 'indices', 'all images and material JSON',
                                        'all node/rest transforms', 'inverse bind matrices', 'all animation samplers/channels/timestamps',
                                        'all skin joint names/order', 'every other byte outside JOINTS_0 and WEIGHTS_0'],
                'clips': list(skin.animations), 'clip_count': len(skin.animations),
                'measured_bad_edges': len(bad), 'seed_welded_vertices': len(seeds),
                'geodesic_radius_m': radius, 'smoothing_iterations': iterations,
                'smoothing_welded_vertices': int(np.count_nonzero(blend > 1e-8)),
                'changed_source_vertices': int(np.count_nonzero(changed)),
                'normalized_weight_sum_max_error': float(np.max(np.abs(weights.sum(axis=1)-1))),
                'allocated_influences': 4, 'anatomical_folds': fold_log,
                'scope': 'thorax/abdomen weights only; hands, arms outside torso, head, lower limbs and split tabard preserve source weights',
                'source_position_accessor_sha256': sha(skin.accessor(skin.attrs['POSITION']).tobytes()),
                'source_indices_accessor_sha256': sha(skin.accessor(skin.primitive['indices']).tobytes()),
                'limitations': ['Geometry and textures are deliberately unchanged: holes, generated sculpt/UV and hand topology remain art gates.',
                                'This is a deformation repair candidate, not final AAA art approval.']}
    (output/'repair.json').write_text(json.dumps(metadata, indent=2)+'\n')
    np.savez_compressed(output/'weight-changes.npz', changed_vertex_ids=np.flatnonzero(changed),
                        source_joints=skin.joints, source_weights=skin.weights,
                        output_joints=joints, output_weights=weights,
                        geodesic_distance_m=distances, welded_group=inverse)
    if skin.path.read_bytes() != skin.raw:
        raise AssertionError('Input was modified during repair')
    print('REPAIRED', result, 'vertices', metadata['changed_source_vertices'], flush=True)
    return result


def compare(before_path, after_path, output):
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    old, new = Skin(before['source']), Skin(after['source'])
    if sha(old.raw) != before['source_sha256'] or sha(new.raw) != after['source_sha256']:
        raise ValueError('Comparison reports must match immutable input bytes')
    a, b = np.load(after_path.with_suffix('.npz')), np.load(before_path.with_suffix('.npz'))
    if not np.array_equal(a['edges'], b['edges']) or not np.array_equal(a['samples'], b['samples']):
        raise ValueError('Before/after must use identical topology and sample schedule')
    ranges = []
    for attribute in ('JOINTS_0', 'WEIGHTS_0'):
        accessor = old.doc['accessors'][old.attrs[attribute]]
        view = old.doc['bufferViews'][accessor['bufferView']]
        start = old.bin_offset+view.get('byteOffset', 0)
        ranges.append((start, start+view['byteLength'], attribute))
    cursor, preserved_old, preserved_new = 0, bytearray(), bytearray()
    for start, end, _ in sorted(ranges):
        preserved_old.extend(old.raw[cursor:start])
        preserved_new.extend(new.raw[cursor:start])
        cursor = end
    preserved_old.extend(old.raw[cursor:])
    preserved_new.extend(new.raw[cursor:])
    if preserved_old != preserved_new or len(old.raw) != len(new.raw):
        raise AssertionError('Forbidden GLB byte changes')
    if np.max(np.abs(new.weights.sum(axis=1)-1)) > 2e-7 or np.any(new.weights < 0) or not np.all(np.isfinite(new.weights)):
        raise AssertionError('Invalid repaired normalized weights')
    hand_joints = [i for i, name in enumerate(old.names) if 'Hand' in name]
    hand_mask = np.any(np.isin(old.joints, hand_joints) & (old.weights > 0), axis=1)
    hands_same = (np.array_equal(old.joints[hand_mask], new.joints[hand_mask]) and
                  np.array_equal(old.weights[hand_mask], new.weights[hand_mask]))
    difference = a['max_extension_mm']-b['max_extension_mm']
    changed_ratio = a['max_ratio']-b['max_ratio']
    worst = np.argsort(difference)[-12:][::-1]
    worst_records = []
    for i in worst:
        clip, time = a['samples'][a['extension_sample'][i]]
        edge = int(a['edges'][i])
        worst_records.append({'maximum_extension_envelope_change_mm': float(difference[i]),
                              'original_maximum_extension_mm': float(b['max_extension_mm'][i]),
                              'repaired_maximum_extension_mm': float(a['max_extension_mm'][i]),
                              'source_at_repaired_peak': old.edge_record(edge, str(clip), float(time)),
                              'repaired_at_peak': new.edge_record(edge, str(clip), float(time))})
    targets = []
    for e in before['worst_ratio_edges'][:6]:
        targets.append({'before': e, 'after_at_identical_pose': new.edge_record(e['edge_index'], e['clip'], e['time_s'])})
    report = {'source_sha256': sha(old.raw), 'output_sha256': sha(new.raw),
              'source_path': str(old.path), 'output_path': str(new.path),
              'source_and_output_bytes': len(old.raw), 'sampling': before['sampling'],
              'sample_count': before['sample_count'], 'clip_count': after['clip_count'], 'clips': after['clips'],
              'before_edge_max_ratio_distribution': before['per_edge_max_ratio'],
              'after_edge_max_ratio_distribution': after['per_edge_max_ratio'],
              'before_edge_max_extension_mm_distribution': before['per_edge_max_extension_mm'],
              'after_edge_max_extension_mm_distribution': after['per_edge_max_extension_mm'],
              'edge_extension_envelope_change_mm_distribution': summary(difference),
              'edge_extension_envelope_change_counts': {'improved_over_1mm': int(sum(difference < -1)),
                  'worsened_over_1mm': int(sum(difference > 1)), 'worsened_over_2mm': int(sum(difference > 2)),
                  'worsened_over_5mm': int(sum(difference > 5)), 'worsened_over_10mm': int(sum(difference > 10))},
              'edge_ratio_envelope_change_distribution': summary(changed_ratio),
              'worst_original_ratio_edges_at_identical_poses': targets,
              'worst_repaired_ratio_edge': after['worst_ratio_edges'][0],
              'largest_extension_envelope_increases': worst_records,
              'strict_byte_mask': {'passed': True, 'forbidden_changed_bytes': 0,
                  'only_allowed_ranges': [{'start': start, 'end_exclusive': end, 'attribute': name} for start, end, name in ranges],
                  'all_preserved_bytes_source_sha256': sha(preserved_old),
                  'all_preserved_bytes_output_sha256': sha(preserved_new)},
              'four_influences_normalized': True,
              'weight_sum_max_error': float(np.max(np.abs(new.weights.sum(axis=1)-1))),
              'hand_finger_weight_vertex_count': int(sum(hand_mask)), 'hand_finger_weight_rows_byte_exact': hands_same,
              'rest_evaluated_vertex_max_difference_mm': float(np.linalg.norm(new.rest-old.rest, axis=1).max()*1000),
              'algorithm': {'script': 'tools/repair_character_weights.py', 'script_sha256': sha(Path(__file__).read_bytes()),
                  'geodesic_radius_m': .045, 'iterations': 24,
                  'scope': 'thorax/abdomen; no arm-parent folding or hand/tabard smoothing',
                  'source_audit_keys_only_used_for_patch_locality': True,
                  'final_before_after_audits_include_all_exported_keys_and_midpoints': True},
              'automatic_visual_approval': False, 'aaa_art_approval': 'pending',
              'limitations': ['Envelope deltas compare per-edge maxima over identical sampled poses; full temporal arrays remain separate.',
                  'Sampling all keys and midpoints is not a continuous deformation proof.',
                  'Unchanged hand anatomy, source clothing intersections, texture/sculpt fidelity, transitions and device performance remain art gates.']}
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('COMPARISON', output, 'max extension increase mm', float(difference.max()), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--keys-only', action='store_true')
    parser.add_argument('--render-cases', type=Path)
    parser.add_argument('--repair-from', type=Path, help='before.npz produced by the complete source audit')
    parser.add_argument('--radius', type=float, default=.045)
    parser.add_argument('--iterations', type=int, default=24)
    parser.add_argument('--report-name', default='before')
    parser.add_argument('--compare-before', type=Path)
    parser.add_argument('--compare-after', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.compare_before or args.compare_after:
        if not args.compare_before or not args.compare_after:
            raise ValueError('Both comparison reports are required')
        compare(args.compare_before, args.compare_after, args.output/(args.report_name+'.json'))
        return
    if args.render_cases:
        render_cases(args.input.resolve(strict=True), args.output, args.render_cases)
        return
    skin = Skin(args.input)
    if args.repair_from:
        if not math.isfinite(args.radius) or args.radius <= 0 or not 1 <= args.iterations <= 128:
            raise ValueError('Finite positive radius and 1..128 smoothing iterations required')
        repair(skin, args.repair_from, args.output, args.radius, args.iterations)
        return
    if Path(args.report_name).name != args.report_name:
        raise ValueError('report-name is a plain basename')
    report_path = args.output/(args.report_name+'.json')
    if report_path.exists():
        raise ValueError('Preserve existing reports; output must be new')
    audit(skin, report_path, midpoints=not args.keys_only)


if __name__ == '__main__':
    main()
