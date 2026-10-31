"""Pose-constrained repaint of one explicitly anchored chest region.

This does NOT call the rejected global/thorax repair. Original joint slots stay
fixed. Only a small geodesic region's weights can vary, with vanishing change
bounds and a fixed outer ring,
same-frame edge-extension constraints, and posed triangle-orientation/area
guards. Geometry, animations, all other weight rows and source files stay exact.
One output candidate per source is written, with explicit finite-sampling limits.
"""
from __future__ import annotations

import os
for _thread_env in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_thread_env] = '1'

import argparse
import heapq
import json
from pathlib import Path
import sys

import numpy as np
from repair_character_weights import Skin, sha, summary, render_cases


REGIONS = {
    'lyra': {'source_sha256': 'a89ced80a24f93685b35bf52e5fedb689e25b0f7ead6188c009d4405c0dfa4a1',
             'edge_index': 53059, 'clip': 'heavy', 'time_s': .63,
             'anchor_y_up_m': [-.09985646739124165, 1.3049161267796672, -.07828663237170398]},
    'sentinel': {'source_sha256': '214bab372dfce2552b1f97fd2fd88a160fa593cb2450c6ffbc66c1547974e721',
                 'edge_index': 40173, 'clip': 'enemy_attack', 'time_s': .68,
                 'anchor_y_up_m': [.19068737210791768, 1.3525148732992997, -.01816812659761251]},
}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


class Region:
    def __init__(self, skin, specification, radius=.030, maximum_delta=.025):
        self.skin, self.spec = skin, specification
        if sha(skin.raw) != specification['source_sha256']:
            raise ValueError('Expected the exact frozen original authored GLB')
        self.radius, self.maximum_delta = radius, maximum_delta
        self.unique_positions, self.vertex_group = np.unique(skin.positions, axis=0, return_inverse=True)
        self.group_count = len(self.unique_positions)
        self.representatives = np.full(self.group_count, len(skin.positions), dtype=int)
        np.minimum.at(self.representatives, self.vertex_group, np.arange(len(skin.positions)))
        self.rest = skin.rest[self.representatives]
        self.faces = self.vertex_group[skin.faces]
        self.edges = np.unique(np.sort(self.vertex_group[skin.edges], axis=1), axis=0)
        self.edges = self.edges[self.edges[:, 0] != self.edges[:, 1]]
        target = self.vertex_group[skin.edges[specification['edge_index']]]
        anchor = np.asarray(specification['anchor_y_up_m'])
        if np.linalg.norm(self.rest[target].mean(axis=0)-anchor) > 1e-5:
            raise ValueError('Manual anchor no longer matches the exact source target')
        lengths = np.linalg.norm(self.rest[self.edges[:, 1]]-self.rest[self.edges[:, 0]], axis=1)
        adjacency = [[] for _ in range(self.group_count)]
        for (a, b), length in zip(self.edges, lengths):
            adjacency[a].append((int(b), float(length)))
            adjacency[b].append((int(a), float(length)))
        distances = np.full(self.group_count, np.inf)
        queue = []
        for g in target:
            distances[g] = np.linalg.norm(self.rest[g]-anchor)
            heapq.heappush(queue, (float(distances[g]), int(g)))
        while queue:
            distance, g = heapq.heappop(queue)
            if distance != distances[g] or distance >= radius:
                continue
            for other, length in adjacency[g]:
                d = distance+length
                if d < distances[other] and d < radius:
                    distances[other] = d
                    heapq.heappush(queue, (d, other))
        self.free = np.flatnonzero(distances < radius)
        self.taper = (1-(distances[self.free]/radius)**2)**2
        self.fixed_boundary = np.array(sorted({b for a in self.free for b, _ in adjacency[a]
                                               if b not in set(self.free)}), dtype=int)
        if len(self.free) < 2 or len(self.free) > 80:
            raise ValueError('Manual ROI unexpectedly empty or broad; inspect before proceeding')
        free_set = set(self.free)
        self.edge_mask = np.array([a in free_set or b in free_set for a, b in self.edges])
        self.local_edges = self.edges[self.edge_mask]
        self.face_ids = np.flatnonzero(np.any(np.isin(self.faces, self.free), axis=1))
        self.local_faces = self.faces[self.face_ids]
        self.point_groups = np.unique(np.concatenate((self.local_edges.ravel(), self.local_faces.ravel())))
        self.point_lookup = {int(g): i for i, g in enumerate(self.point_groups)}
        self.free_lookup = {int(g): i for i, g in enumerate(self.free)}
        self.ep = np.array([[self.point_lookup[int(g)] for g in e] for e in self.local_edges])
        self.fp = np.array([[self.point_lookup[int(g)] for g in f] for f in self.local_faces])
        self.tp = np.array([self.point_lookup[int(g)] for g in target])
        self.point_free = np.array([self.free_lookup.get(int(g), -1) for g in self.point_groups])
        self.variable_count = len(self.free)*3
        self.w0 = skin.weights[self.representatives[self.free]].copy()
        self.joints = skin.joints[self.representatives[self.free]]
        # Do not merge a seam if its named weights actually differ.
        dense = np.zeros((len(skin.positions), len(skin.names)))
        np.put_along_axis(dense, skin.joints, skin.weights, axis=1)
        for g in self.free:
            members = np.flatnonzero(self.vertex_group == g)
            if np.max(np.abs(dense[members]-dense[self.representatives[g]])) > 2e-7:
                raise ValueError('ROI seam vertices have distinct source weights; manual review required')
        self.changed_vertex_ids = np.flatnonzero(np.isin(self.vertex_group, self.free))
        protected = np.array([('Hand' in n or 'ForeArm' in n or n in ('LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot'))
                              for n in skin.names])
        if np.any(protected[skin.joints[self.changed_vertex_ids]] & (skin.weights[self.changed_vertex_ids] > 1e-7)):
            raise ValueError('Explicit chest ROI unexpectedly touches protected hand/limb skin')
        self.distances = distances

    def describe(self):
        s = self.skin
        return {'source_sha256': sha(s.raw), 'manual_specification': self.spec,
                'geodesic_radius_m': self.radius, 'maximum_weight_delta_at_core': self.maximum_delta,
                'taper': '(1-(distance/radius)^2)^2 change-bound envelope; fixed outer ring. The envelope is C1, but discrete weights do not prove a continuous derivative.',
                'mutable_welded_groups': len(self.free), 'mutable_exported_vertices': len(self.changed_vertex_ids),
                'fixed_boundary_groups': self.fixed_boundary.tolist(),
                'incident_unique_edges': len(self.local_edges), 'incident_triangles': len(self.local_faces),
                'original_target': s.edge_record(self.spec['edge_index'], self.spec['clip'], self.spec['time_s']),
                'mutable_vertices': [s.vertex_record(int(v), s.rest) for v in self.changed_vertex_ids],
                'weights_only_original_four_joint_slots': True, 'all_outside_rows_frozen': True}

    def prepare_poses(self):
        s = self.skin
        self.samples = list(s.samples(True))
        self.target_sample = min(range(len(self.samples)), key=lambda i:
                                 abs(self.samples[i][1]-self.spec['time_s']) if self.samples[i][0] == self.spec['clip'] else 1e9)
        reps = self.representatives[self.point_groups]
        self.p0 = np.empty((len(self.samples), len(reps), 3))
        self.contributions = np.empty((len(self.samples), len(reps), 4, 3))
        self.d = np.empty((len(self.samples), len(self.free), 3, 3))
        free_point_indices = [self.point_lookup[int(g)] for g in self.free]
        for i, (clip, time) in enumerate(self.samples):
            matrices = s.transforms(clip, time)
            contribution = np.einsum('pkij,pj->pki', matrices[s.joints[reps], :3, :3], s.positions[reps])
            contribution += matrices[s.joints[reps], :3, 3]
            self.contributions[i] = contribution
            self.p0[i] = np.einsum('pki,pk->pi', contribution, s.weights[reps])*1000
            c = contribution[free_point_indices]*1000
            self.d[i] = (c[:, :3]-c[:, 3:4]).transpose(0, 2, 1)
            if i % 400 == 0:
                print('POSE', i, '/', len(self.samples), clip, round(time, 3), flush=True)
        self.e0 = self.p0[:, self.ep[:, 1]]-self.p0[:, self.ep[:, 0]]
        self.length0 = np.linalg.norm(self.e0, axis=2)
        u = self.p0[:, self.fp[:, 1]]-self.p0[:, self.fp[:, 0]]
        v = self.p0[:, self.fp[:, 2]]-self.p0[:, self.fp[:, 0]]
        cross = np.cross(u, v)
        self.area20 = np.linalg.norm(cross, axis=2)
        self.normal0 = cross/np.maximum(self.area20[:, :, None], 1e-30)
        rest = self.rest[self.point_groups]*1000
        self.rest_lengths = np.linalg.norm(rest[self.ep[:, 1]]-rest[self.ep[:, 0]], axis=1)
        ru = rest[self.fp[:, 1]]-rest[self.fp[:, 0]]
        rv = rest[self.fp[:, 2]]-rest[self.fp[:, 0]]
        self.rest_area2 = np.linalg.norm(np.cross(ru, rv), axis=1)
        # A stretched source triangle may shrink towards its rest area, while
        # already compressed triangles may not collapse further or reverse.
        self.area_projection_floor = .95*np.minimum(self.area20, self.rest_area2[None, :])
        self.edge_length_floor = .95*np.minimum(self.length0, self.rest_lengths[None, :])

    def points(self, x):
        result = self.p0.copy()
        delta = np.einsum('sgij,gj->sgi', self.d, x.reshape(-1, 3))
        for j, g in enumerate(self.free):
            result[:, self.point_lookup[int(g)]] += delta[:, j]
        return result

    def values(self, x):
        p = self.points(x)
        edges = p[:, self.ep[:, 1]]-p[:, self.ep[:, 0]]
        length = np.linalg.norm(edges, axis=2)
        u = p[:, self.fp[:, 1]]-p[:, self.fp[:, 0]]
        v = p[:, self.fp[:, 2]]-p[:, self.fp[:, 0]]
        cross = np.cross(u, v)
        projection = np.einsum('sfi,sfi->sf', cross, self.normal0)
        return p, length, projection, np.linalg.norm(cross, axis=2)

    def solve(self, cap_mm=.25, max_rounds=4, normalize_units=True):
        from scipy.optimize import LinearConstraint, minimize
        n, ne, nf = len(self.samples), len(self.ep), len(self.fp)
        edge_active = np.zeros((n, ne), dtype=bool)
        face_active = np.zeros((n, nf), dtype=bool)
        selected = {self.target_sample}
        for clip in self.skin.animations:
            ids = [i for i, (name, _) in enumerate(self.samples) if name == clip]
            selected.update(ids[round(q*(len(ids)-1))] for q in (0, .25, .5, .75, 1))
        edge_active[list(selected)] = True
        face_active[list(selected)] = True
        edge_active[np.argmax(self.length0, axis=0), np.arange(ne)] = True
        edge_active[np.argmin(self.length0, axis=0), np.arange(ne)] = True
        face_active[np.argmin(self.area20, axis=0), np.arange(nf)] = True
        edge_upper = self.length0+cap_mm
        # Fixed original support; three deltas determine the fourth by sum zero.
        weight_linear = np.zeros((len(self.free)*4, self.variable_count))
        for g in range(len(self.free)):
            weight_linear[4*g:4*g+3, 3*g:3*g+3] = np.eye(3)
            weight_linear[4*g+3, 3*g:3*g+3] = -1
        limits = self.maximum_delta*self.taper[:, None]*np.ones((1, 4))
        low = np.maximum(-self.w0, -limits).ravel()
        high = np.minimum(1-self.w0, limits).ravel()
        # A named-weight Laplacian regularizes only changes, including zero
        # changes at fixed neighbouring groups; it does not smooth the source.
        global_basis = np.zeros((len(self.point_groups), len(self.skin.names), self.variable_count))
        for p, g in enumerate(self.point_free):
            if g < 0:
                continue
            for k, bone in enumerate(self.joints[g]):
                global_basis[p, bone] += weight_linear[4*g+k]
        lap = global_basis[self.ep[:, 1]]-global_basis[self.ep[:, 0]]
        regularizer = np.eye(self.variable_count)+3*np.einsum('ebv,ebw->vw', lap, lap)
        reg_scale = 1000.
        target_p0 = self.p0[self.target_sample, self.tp[1]]-self.p0[self.target_sample, self.tp[0]]
        target_j = np.zeros((3, self.variable_count))
        for sign, p in ((-1, self.tp[0]), (1, self.tp[1])):
            g = self.point_free[p]
            if g >= 0:
                target_j[:, 3*g:3*g+3] += sign*self.d[self.target_sample, g]
        def objective(x):
            e = target_p0+target_j@x
            return float(e@e+reg_scale*x@regularizer@x)
        def gradient(x):
            return 2*target_j.T@(target_p0+target_j@x)+2*reg_scale*regularizer@x
        x = np.zeros(self.variable_count)
        # Solve in dimensionless, order-one coordinates. Physical weights,
        # constraints and ROI are unchanged; only numerical units differ.
        variable_scale = np.repeat(self.maximum_delta*self.taper, 3) if normalize_units else np.ones(self.variable_count)
        weight_row_scale = np.repeat(self.maximum_delta*self.taper, 4) if normalize_units else np.ones(len(self.free)*4)
        objective_scale = max(objective(x), 1.) if normalize_units else 1.
        rounds = []
        for round_id in range(max_rounds):
            es, ei = np.nonzero(edge_active)
            fs, fi = np.nonzero(face_active)
            constraint_scale = np.concatenate((
                np.maximum(edge_upper[es, ei]**2-self.length0[es, ei]**2, 1.),
                np.maximum(self.length0[es, ei]**2-self.edge_length_floor[es, ei]**2, 1.),
                np.maximum(self.area20[fs, fi]-self.area_projection_floor[fs, fi], 1.)))
            if not normalize_units:
                constraint_scale[:] = 1
            # Only active cuts allocate dense Jacobians; full schedules are
            # checked after every solve before any candidate can be written.
            ej = np.zeros((len(es), 3, self.variable_count))
            for sign, col in ((-1, 0), (1, 1)):
                for k, p in enumerate(self.ep[ei, col]):
                    g = self.point_free[p]
                    if g >= 0:
                        ej[k, :, 3*g:3*g+3] += sign*self.d[es[k], g]
            def evaluate(x, jacobian=False):
                edge = self.e0[es, ei]+np.einsum('kiv,v->ki', ej, x)
                norm2 = np.einsum('ki,ki->k', edge, edge)
                points = self.p0[fs[:, None], self.fp[fi]].copy()
                for k in range(3):
                    for row, p in enumerate(self.fp[fi, k]):
                        g = self.point_free[p]
                        if g >= 0:
                            points[row, k] += self.d[fs[row], g]@x[3*g:3*g+3]
                u, v = points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]
                normal = self.normal0[fs, fi]
                projected = np.einsum('ki,ki->k', np.cross(u, v), normal)
                if not jacobian:
                    return np.concatenate((edge_upper[es, ei]**2-norm2,
                                           norm2-self.edge_length_floor[es, ei]**2,
                                           projected-self.area_projection_floor[fs, fi]))
                edge_j = 2*np.einsum('ki,kiv->kv', edge, ej)
                face_j = np.zeros((len(fs), self.variable_count))
                gb, gc = np.cross(v, normal), np.cross(normal, u)
                for k, grad in enumerate((-gb-gc, gb, gc)):
                    for row, p in enumerate(self.fp[fi, k]):
                        g = self.point_free[p]
                        if g >= 0:
                            face_j[row, 3*g:3*g+3] += grad[row]@self.d[fs[row], g]
                return np.concatenate((-edge_j, edge_j, face_j), axis=0)
            solution = minimize(lambda z: objective(z*variable_scale)/objective_scale,
                                x/variable_scale,
                                jac=lambda z: gradient(z*variable_scale)*variable_scale/objective_scale,
                                method='SLSQP',
                                constraints=[LinearConstraint(weight_linear*variable_scale[None, :]/weight_row_scale[:, None],
                                                              low/weight_row_scale, high/weight_row_scale),
                                             {'type': 'ineq', 'fun': lambda z: evaluate(z*variable_scale)/constraint_scale,
                                              'jac': lambda z: evaluate(z*variable_scale, True)*variable_scale[None, :]/constraint_scale[:, None]}],
                                options={'maxiter': 90, 'ftol': 1e-8, 'disp': False})
            x = solution.x*variable_scale
            _, lengths, projection, _ = self.values(x)
            excess = lengths-edge_upper
            compression = self.edge_length_floor-lengths
            area_loss = self.area_projection_floor-projection
            row = {'round': round_id, 'solver_success': bool(solution.success), 'solver_message': str(solution.message),
                   'iterations': int(solution.nit), 'active_edge_samples': len(es), 'active_face_samples': len(fs),
                   'solver_units': 'dimensionless' if normalize_units else 'raw mm / mm2 / weight units',
                   'maximum_extension_over_cap_mm': float(excess.max()),
                   'maximum_edge_compression_floor_violation_mm': float(compression.max()),
                   'maximum_oriented_area_floor_violation_mm2': float(area_loss.max())}
            rounds.append(row)
            print('OPTIMIZE', json.dumps(row), flush=True)
            if excess.max() <= 1e-5 and compression.max() <= 1e-5 and area_loss.max() <= 1e-5:
                break
            for matrix, active in ((excess, edge_active), (compression, edge_active), (area_loss, face_active)):
                worst = np.argmax(matrix, axis=0)
                cols = np.flatnonzero(matrix[worst, np.arange(matrix.shape[1])] > 1e-5)
                active[worst[cols], cols] = True
        return x, rounds

    def weights_for(self, x, factor=1.):
        weights = self.skin.weights.astype('<f4').copy()
        delta3 = x.reshape(-1, 3)*factor
        candidate = self.w0+np.column_stack((delta3, -delta3.sum(axis=1)))
        candidate = candidate.astype('<f4')
        candidate[:, 3] = (1-candidate[:, :3].astype(float).sum(axis=1)).astype('<f4')
        for g, row in zip(self.free, candidate):
            members = np.flatnonzero(self.vertex_group == g)
            # The slot order can differ at an exported seam; match named joints.
            reference = self.skin.joints[self.representatives[g]]
            lookup = {int(j): float(w) for j, w in zip(reference, row)}
            for v in members:
                weights[v] = [lookup[int(j)] for j in self.skin.joints[v]]
        return weights


def exact_local(region, weights):
    """Check actual float32 candidate weights, not the optimizer's doubles."""
    s = region.skin
    reps = region.representatives[region.point_groups]
    candidate = np.einsum('spki,pk->spi', region.contributions, weights[reps])*1000
    lengths = np.linalg.norm(candidate[:, region.ep[:, 1]]-candidate[:, region.ep[:, 0]], axis=2)
    u = candidate[:, region.fp[:, 1]]-candidate[:, region.fp[:, 0]]
    v = candidate[:, region.fp[:, 2]]-candidate[:, region.fp[:, 0]]
    cross = np.cross(u, v)
    area2 = np.linalg.norm(cross, axis=2)
    projection = np.einsum('sfi,sfi->sf', cross, region.normal0)
    return candidate, lengths, projection, area2


def write_candidate(skin, weights, allowed_vertices, output=None):
    index = skin.attrs['WEIGHTS_0']
    a = skin.doc['accessors'][index]
    view = skin.doc['bufferViews'][a['bufferView']]
    if a['componentType'] != 5126 or view.get('byteStride') or a.get('byteOffset', 0):
        raise ValueError('Writer requires the frozen tightly packed float32 weights layout')
    start = skin.bin_offset+view.get('byteOffset', 0)
    raw = bytearray(skin.raw)
    source_weights = skin.accessor(index)
    changed = np.flatnonzero(np.any(weights != source_weights, axis=1))
    if not np.all(np.isin(changed, allowed_vertices)):
        raise AssertionError('Attempted change outside explicit ROI')
    mask = np.zeros(len(raw), dtype=bool)
    for v in changed:
        offset = start+int(v)*16
        raw[offset:offset+16] = weights[v].tobytes()
        mask[offset:offset+16] = True
    old, new = np.frombuffer(skin.raw, dtype=np.uint8), np.frombuffer(raw, dtype=np.uint8)
    if not np.array_equal(old[~mask], new[~mask]):
        raise AssertionError('Unexpected byte change outside explicit weight rows')
    if output is not None:
        if output.exists():
            raise ValueError('One new candidate output only; refusing overwrite')
        output.write_bytes(raw)
    return {'source_sha256': sha(skin.raw), 'candidate_sha256': sha(raw), 'changed_vertex_ids': changed.tolist(),
            'changed_weight_rows': len(changed), 'forbidden_changed_bytes': 0,
            'only_weight_rows_changed': True, 'joints_all_byte_exact': True,
            'preserved_bytes_sha256': sha(old[~mask].tobytes()),
            'source_and_candidate_bytes': len(raw), 'outside_region_weight_rows_byte_exact': True,
            'geometry_uv_textures_rest_all_animation_bytes_exact': True}


def complete_report(region, weights, pose, lengths, projection, area2, baseline_path, proof, rounds, cap):
    s = region.skin
    before = json.loads(baseline_path.read_text())
    baseline = np.load(baseline_path.with_suffix('.npz'))
    expected_schedule = np.array(region.samples, dtype=str)
    if before['source_sha256'] != sha(s.raw) or not np.array_equal(expected_schedule, baseline['samples']):
        raise ValueError('Full-mesh baseline does not belong to this immutable source and schedule')
    ids = baseline['edges']
    if not np.array_equal(ids, np.flatnonzero(s.valid)):
        raise ValueError('Full-mesh baseline edge topology differs')
    before_ratios = baseline['max_ratio']
    before_extension = baseline['max_extension_mm']
    after_ratios, after_extension = before_ratios.copy(), before_extension.copy()
    edge_lookup = {tuple(e): i for i, e in enumerate(region.local_edges)}
    changed_welded = np.sort(region.vertex_group[s.edges[ids]], axis=1)
    local_ids, baseline_ids = [], []
    for i, e in enumerate(changed_welded):
        if tuple(e) in edge_lookup:
            local_ids.append(edge_lookup[tuple(e)])
            baseline_ids.append(i)
    local_ids, baseline_ids = np.array(local_ids), np.array(baseline_ids)
    rest = s.rest_lengths[ids[baseline_ids]]*1000
    after_ratios[baseline_ids] = (lengths[:, local_ids]/rest).max(axis=0)
    after_extension[baseline_ids] = (lengths[:, local_ids]-rest).max(axis=0)
    delta = after_extension-before_extension
    same_frame = lengths-region.length0
    si, ei = np.unravel_index(np.argmax(same_frame), same_frame.shape)
    fi_s, fi_i = np.unravel_index(np.argmin(projection-region.area_projection_floor), projection.shape)
    target_before = np.linalg.norm(region.p0[region.target_sample, region.tp[1]]-region.p0[region.target_sample, region.tp[0]])
    target_after = np.linalg.norm(pose[region.target_sample, region.tp[1]]-pose[region.target_sample, region.tp[0]])
    area_cos = projection/np.maximum(area2, 1e-30)
    report = {'source_sha256': sha(s.raw), 'candidate_sha256': proof['candidate_sha256'],
              'source_path': str(s.path), 'source_geometry_positions_sha256': sha(s.accessor(s.attrs['POSITION']).tobytes()),
              'source_geometry_indices_sha256': sha(s.accessor(s.primitive['indices']).tobytes()),
              'sample_count': len(region.samples), 'exported_key_count': len(list(s.samples(False))),
              'clip_count': len(s.animations), 'clips': list(s.animations),
              'sampling': 'Every exported timestamp plus every adjacent midpoint; finite, not continuous proof',
              'complete_mesh_comparison': 'All changed/incident edges evaluated at every sample; all other vertex weight bytes and thus all other posed edges are provably identical. Original full-mesh baseline SHA/schedule/topology validated.',
              'roi': region.describe(), 'proof': proof, 'solver_rounds': rounds,
              'same_frame_extension_cap_mm': cap,
              'maximum_same_frame_extension_increase_mm': float(same_frame.max()),
              'maximum_same_frame_extension_decrease_mm': float(same_frame.min()),
              'worst_increase': {'clip': region.samples[si][0], 'time_s': region.samples[si][1],
                  'welded_edge_groups': region.local_edges[ei].tolist(),
                  'rest_length_mm': float(region.rest_lengths[ei]),
                  'before_length_mm': float(region.length0[si, ei]), 'after_length_mm': float(lengths[si, ei])},
              'target_before_length_mm': float(target_before), 'target_after_length_mm': float(target_after),
              'target_reduction_mm': float(target_before-target_after),
              'before_edge_max_ratio': summary(before_ratios), 'after_edge_max_ratio': summary(after_ratios),
              'before_edge_max_extension_mm': summary(before_extension), 'after_edge_max_extension_mm': summary(after_extension),
              'extension_envelope_delta_mm': summary(delta),
              'envelope_improved_over_point1mm_edges': int(sum(delta < -.1)),
              'envelope_worsened_over_point1mm_edges': int(sum(delta > .1)),
              'triangle_diagnostics': {'incident_source_triangle_count': len(region.face_ids),
                  'source_min_area_mm2': float(region.area20.min()*.5), 'candidate_min_area_mm2': float(area2.min()*.5),
                  'source_min_area_over_rest': float((region.area20/np.maximum(region.rest_area2, 1e-30)).min()),
                  'candidate_min_area_over_rest': float((area2/np.maximum(region.rest_area2, 1e-30)).min()),
                  'minimum_candidate_normal_cosine_against_same_pose_source': float(area_cos.min()),
                  'new_orientation_reversals': int(sum((projection < -1e-8).ravel())),
                  'area_constraint': 'oriented double area >= .95 * min(source posed double area, source REST double area)',
                  'minimum_area_constraint_margin_mm2': float((projection-region.area_projection_floor).min()),
                  'worst_area_constraint': {'clip': region.samples[fi_s][0], 'time_s': region.samples[fi_s][1],
                                            'source_triangle_id': int(region.face_ids[fi_i])}},
              'edge_compression_floor_margin_mm': float((lengths-region.edge_length_floor).min()),
              'maximum_weight_sum_error': float(np.abs(weights.sum(axis=1)-1).max()),
              'automatic_aaa_approval': False, 'final_art_status': 'pending',
              'candidate_numeric_gate': 'pass' if (same_frame.max() <= cap+1e-5 and
                  (projection-region.area_projection_floor).min() >= -1e-5 and
                  (lengths-region.edge_length_floor).min() >= -1e-5 and target_before-target_after >= .5) else 'rejected',
              'runtime_adoption': 'pending visual review; original runtime unchanged',
              'limitations': ['At most one output per asset; unchanged skeleton/clip times do not prove final anatomy, transitions or AAA appearance.',
                              'The small finite-sample extension allowance is explicitly reported; it is not a new art-quality threshold.',
                              'No hands, tabard or limb correction and no target-device performance claim.']}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--character', choices=REGIONS, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--solve-only', action='store_true', help='Report an in-memory solve; never write a GLB')
    parser.add_argument('--solver-units', choices=('normalized', 'raw'), default='normalized',
                        help='Reproduce the numerical scaling check without changing physical constraints')
    parser.add_argument('--render-cases', type=Path)
    parser.add_argument('--extension-cap-mm', type=float, default=.25)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.render_cases:
        args.output.mkdir(parents=True, exist_ok=True)
        render_cases(args.input.resolve(strict=True), args.output, args.render_cases)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    region = Region(Skin(args.input), REGIONS[args.character])
    dump(args.output/'roi.json', region.describe())
    if args.prepare_only:
        print('REGION', len(region.free), 'groups', len(region.changed_vertex_ids), 'vertices', flush=True)
        return
    if args.baseline is None or args.extension_cap_mm <= 0:
        raise ValueError('Original full-sampling baseline and positive extension cap required')
    if not args.solve_only and (args.output/'candidate.glb').exists():
        raise ValueError('One new output per asset; refusing overwrite')
    region.prepare_poses()
    solution, rounds = region.solve(args.extension_cap_mm, normalize_units=args.solver_units == 'normalized')
    # Cast-to-float validation is exhaustive over the same pose schedule. A
    # small line search towards the source can remove optimizer/rounding excess;
    # it is not a new repair candidate or a spatial mask change.
    factor = 1.
    for attempt in range(7):
        weights = region.weights_for(solution, factor)
        pose, length, projection, area2 = exact_local(region, weights)
        feasible = (np.max(length-region.length0) <= args.extension_cap_mm+1e-5 and
                    np.min(length-region.edge_length_floor) >= -1e-5 and
                    np.min(projection-region.area_projection_floor) >= -1e-5)
        if feasible:
            break
        if attempt < 6:
            factor *= .8
    proof = write_candidate(region.skin, weights, region.changed_vertex_ids,
                            None if args.solve_only else args.output/'candidate.glb')
    proof['line_search_factor'] = factor
    proof['float32_full_schedule_constraints_feasible'] = bool(feasible)
    report = complete_report(region, weights, pose, length, projection, area2, args.baseline, proof, rounds, args.extension_cap_mm)
    report['tool_sha256'] = sha(Path(__file__).read_bytes())
    report['glb_written'] = not args.solve_only
    report['solver_units'] = args.solver_units
    solve_prefix = 'scaled' if args.solver_units == 'normalized' else 'raw'
    dump(args.output/(solve_prefix+'-solve-review.json' if args.solve_only else 'review.json'), report)
    if args.solve_only:
        np.savez_compressed(args.output/(solve_prefix+'-solution.npz'), source_sha256=np.array(sha(region.skin.raw)),
                            weights=weights, source_joints=region.skin.joints)
    np.savez_compressed(args.output/(solve_prefix+'-pose-comparison.npz' if args.solve_only else 'local-pose-comparison.npz'), before_lengths_mm=region.length0,
                        after_lengths_mm=length, source_area2_mm2=region.area20, candidate_area2_mm2=area2,
                        normal_projection_mm2=projection, sample_schedule=np.array(region.samples, dtype=str),
                        source_triangle_ids=region.face_ids, welded_edges=region.local_edges)
    if sha(region.skin.path.read_bytes()) != region.spec['source_sha256']:
        raise AssertionError('Frozen input changed')
    print('CANDIDATE', report['candidate_numeric_gate'], 'target reduction mm', report['target_reduction_mm'],
          'worst new extension mm', report['maximum_same_frame_extension_increase_mm'], flush=True)


if __name__ == '__main__':
    main()
