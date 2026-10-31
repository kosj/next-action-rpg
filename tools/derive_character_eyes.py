"""Build one small procedural eye-surface candidate without editing its body.

Geometry is written directly to glTF in the ORIGINAL source Head-local rigid
basis, in physical meters, with an identity mesh root. No image is painted,
baked or edited. The candidate requires reimported studio/pose fit review.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np


def read_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or length != len(raw):
        raise ValueError("Expected complete GLB2")
    size, kind = struct.unpack_from("<I4s", raw, 12)
    if kind != b"JSON" or size > 16 * 1024 * 1024:
        raise ValueError("Invalid JSON chunk")
    document = json.loads(raw[20:20 + size])
    bin_size, bin_kind = struct.unpack_from("<I4s", raw, 20 + size)
    if bin_kind != b"BIN\x00":
        raise ValueError("Expected embedded BIN chunk")
    return raw, document, memoryview(raw)[28 + size:28 + size + bin_size]


def accessor(document, binary, index):
    source = document["accessors"][index]
    if "sparse" in source:
        raise ValueError("Sparse source accessors require an explicit decoder")
    view = document["bufferViews"][source["bufferView"]]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[source["type"]]
    dtype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[source["componentType"]]
    item = np.dtype(dtype).itemsize
    return np.ndarray((source["count"], width), dtype=dtype, buffer=binary,
                      offset=view.get("byteOffset", 0) + source.get("byteOffset", 0),
                      strides=(view.get("byteStride", item * width), item)).copy()


def node_matrix(node):
    if "matrix" in node:
        return np.array(node["matrix"]).reshape(4, 4).T
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    rotation = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    result = np.eye(4)
    result[:3, :3] = rotation @ np.diag(node.get("scale", [1, 1, 1]))
    result[:3, 3] = node.get("translation", [0, 0, 0])
    return result


def source_geometry(document, binary):
    parents = {child: i for i, node in enumerate(document["nodes"]) for child in node.get("children", [])}
    matrices = {}
    def world(index):
        if index not in matrices:
            parent = world(parents[index]) if index in parents else np.eye(4)
            matrices[index] = parent @ node_matrix(document["nodes"][index])
        return matrices[index]
    mesh_nodes = [i for i, node in enumerate(document["nodes"]) if "mesh" in node]
    if len(mesh_nodes) != 1:
        raise ValueError("This candidate expects the reviewed single source body")
    node = document["nodes"][mesh_nodes[0]]
    primitives = document["meshes"][node["mesh"]]["primitives"]
    if len(primitives) != 1:
        raise ValueError("Review the source primitive contract first")
    primitive = primitives[0]
    positions = accessor(document, binary, primitive["attributes"]["POSITION"])
    indices = accessor(document, binary, primitive["indices"]).reshape(-1, 3)
    skin = document["skins"][node["skin"]]
    inverse_bind = accessor(document, binary, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    transforms = np.stack([world(i) for i in skin["joints"]]) @ inverse_bind
    joints = accessor(document, binary, primitive["attributes"]["JOINTS_0"]).astype(int)
    weights = accessor(document, binary, primitive["attributes"]["WEIGHTS_0"])
    if not np.allclose(weights.sum(axis=1), 1, atol=1e-5):
        raise ValueError("Expected normalized source skin weights")
    homogeneous = np.column_stack([positions, np.ones(len(positions))])
    evaluated = np.zeros((len(positions), 4))
    for slot in range(joints.shape[1]):
        evaluated += np.einsum("nij,nj->ni", transforms[joints[:, slot]], homogeneous) * weights[:, slot, None]
    head_indices = [i for i, node in enumerate(document["nodes"]) if node.get("name") == "Head"]
    if len(head_indices) != 1:
        raise ValueError("Expected one source Head joint")
    full_head = world(head_indices[0])
    scales = np.linalg.norm(full_head[:3, :3], axis=0)
    rotation = full_head[:3, :3] / scales
    if not np.allclose(scales, scales.mean(), atol=1e-6) or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5) or np.linalg.det(rotation) < 0:
        raise ValueError("Head REST basis must have positive uniform scale")
    rigid_head = full_head.copy()
    rigid_head[:3, :3] = rotation
    return evaluated[:, :3], indices, full_head, rigid_head, scales


class Surface:
    def __init__(self, positions, indices):
        self.indices = indices
        self.triangles = positions[indices]
        self.e1 = self.triangles[:, 1] - self.triangles[:, 0]
        self.e2 = self.triangles[:, 2] - self.triangles[:, 0]
        self.direction = np.array([0., 0., -1.])
        self.h = np.cross(np.broadcast_to(self.direction, self.e2.shape), self.e2)
        determinant = (self.e1 * self.h).sum(1)
        self.valid = abs(determinant) > 1e-12
        self.inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=self.valid)

    def cast(self, origin):
        offset = origin - self.triangles[:, 0]
        u = self.inverse * (offset * self.h).sum(1)
        q = np.cross(offset, self.e1)
        v = self.inverse * (q * self.direction).sum(1)
        distance = self.inverse * (self.e2 * q).sum(1)
        valid = self.valid & (u >= 0) & (v >= 0) & (u+v <= 1) & (distance > 0)
        triangle = np.where(valid, distance, np.inf).argmin()
        if not valid[triangle]:
            raise ValueError("Manual eye aperture ray missed the source surface")
        return origin + distance[triangle] * self.direction, int(triangle)


def cross2(a, b):
    return a[0]*b[1] - a[1]*b[0]


def srgb_to_linear(color):
    return tuple(value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4 for value in color)


def boundary_radius(polygon, direction):
    hits = []
    for index, start in enumerate(polygon):
        edge = polygon[(index+1) % len(polygon)] - start
        determinant = cross2(direction, edge)
        if abs(determinant) < 1e-12:
            continue
        radius = cross2(start, edge) / determinant
        parameter = cross2(start, direction) / determinant
        if radius > 0 and 0 <= parameter <= 1:
            hits.append(radius)
    if not hits:
        raise ValueError("Iris center must lie inside the explicit aperture polygon")
    return min(hits)


def write_glb(path, positions, normals, colors, groups, restrained):
    payload = bytearray()
    views, accessors = [], []
    def add(values, width, kind, target):
        while len(payload) % 4:
            payload.append(0)
        view_index = len(views)
        views.append({"buffer": 0, "byteOffset": len(payload), "byteLength": values.nbytes, "target": target})
        payload.extend(values.tobytes())
        result = {"bufferView": view_index, "componentType": kind, "count": len(values), "type": width}
        if target == 34962 and width == "VEC3":
            result.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        accessors.append(result)
        return len(accessors)-1
    position_index = add(np.asarray(positions, dtype="<f4"), "VEC3", 5126, 34962)
    normal_index = add(np.asarray(normals, dtype="<f4"), "VEC3", 5126, 34962)
    color_index = add(np.asarray(colors, dtype="<f4"), "VEC4", 5126, 34962)
    primitives = []
    for material, triangles in enumerate(groups):
        if not triangles:
            continue
        index = add(np.asarray(triangles, dtype="<u2").reshape(-1), "SCALAR", 5123, 34963)
        primitives.append({"attributes": {"POSITION": position_index, "NORMAL": normal_index, "COLOR_0": color_index},
                           "indices": index, "material": material, "mode": 4})
    materials = []
    responses = [("EyeSclera", .46, .06, .27), ("GrayGreenIris", .34, .22, .14), ("Pupil", .28, .22, .14)] if restrained else [("EyeSclera", .46, .12, .22), ("GrayGreenIris", .32, .45, .10), ("Pupil", .26, .45, .10)]
    for name, roughness, coat, coat_roughness in responses:
        materials.append({"name": name, "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": roughness},
                          "doubleSided": False, "extensions": {"KHR_materials_clearcoat": {"clearcoatFactor": coat, "clearcoatRoughnessFactor": coat_roughness}}})
    document = {"asset": {"version": "2.0", "generator": "RUNEFALL derive_character_eyes.py procedural inlay candidate"},
                "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": "EyesHeadLocal", "mesh": 0}],
                "meshes": [{"name": "FittedOcularInlays", "primitives": primitives}], "materials": materials,
                "extensionsUsed": ["KHR_materials_clearcoat"], "buffers": [{"byteLength": len(payload)}],
                "bufferViews": views, "accessors": accessors}
    data = json.dumps(document, separators=(",", ":")).encode()
    data += b" " * (-len(data) % 4)
    payload.extend(b"\x00" * (-len(payload) % 4))
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 28+len(data)+len(payload)) + struct.pack("<I4s", len(data), b"JSON") + data + struct.pack("<I4s", len(payload), b"BIN\x00") + payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--reference-review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--appearance", choices=["initial", "restrained"], default="restrained")
    args = parser.parse_args()
    source = args.input.resolve(strict=True)
    output = args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Use a new or empty output directory")
    raw, document, binary = read_glb(source)
    source_sha = hashlib.sha256(raw).hexdigest()
    review = json.loads(args.reference_review.read_text())
    if review["source"]["sha256"] != source_sha:
        raise ValueError("Reference review belongs to another source revision")
    positions, indices, full_head, rigid_head, scales = source_geometry(document, binary)
    convert = np.array([[1., 0, 0], [0, 0, -1], [0, 1, 0]])
    blender_positions = positions @ convert.T
    if not np.allclose(blender_positions.min(0), review["bounds_blender_z_up"]["min"], atol=1e-4) or not np.allclose(blender_positions.max(0), review["bounds_blender_z_up"]["max"], atol=1e-4):
        raise ValueError("CPU-skinned source and Blender bounds disagree")
    camera = next(v for v in review["views"] if v["shot"] == "face_front")
    size = review["render"]["size"]
    origin = np.array(camera["camera_position_blender"]) @ convert
    scale = camera["orthographic_scale_m"] / size
    def ray(pixel):
        return origin + np.array([(pixel[0]-size/2)*scale, (size/2-pixel[1])*scale, 0])
    # Human-selected inner painted-eye apertures from the unchanged 640px
    # source face render. These do not claim anatomical eyeball segmentation.
    apertures = [
        {"name": "image_left", "center": [216, 277], "polygon": [[195,272],[200,267],[211,265],[224,266],[238,271],[241,276],[237,282],[225,286],[212,287],[201,283],[197,279]]},
        {"name": "image_right", "center": [407,276], "polygon": [[382,274],[388,269],[400,266],[412,266],[423,270],[425,276],[421,282],[409,285],[398,283],[387,279]]},
    ]
    if size != 640:
        raise ValueError("Manual aperture measurements require the reviewed 640px image")
    surface = Surface(positions, indices)
    vertices, colors, triangles, labels = [], [], [], []
    eye_reports = []
    restrained = args.appearance == "restrained"
    pupil_radius, iris_radius = (.0024, .0060) if restrained else (.00165, .0049)
    edge_clearance, crown = .00040, .00075
    angular_steps = 72
    for eye in apertures:
        center_pixel = np.array(eye["center"], dtype=float)
        pixel_polygon = np.array(eye["polygon"], dtype=float)
        polygon = (pixel_polygon-center_pixel) * np.array([scale, -scale])
        center_surface, center_triangle = surface.cast(ray(center_pixel))
        start = len(vertices)
        rings = 8
        for ring in range(rings+1):
            for angle_index in range(angular_steps):
                theta = angle_index * math.tau/angular_steps
                direction = np.array([math.cos(theta), math.sin(theta)])
                extent = boundary_radius(polygon, direction)
                radii = [0., pupil_radius*.55, pupil_radius, pupil_radius+.0001,
                         (pupil_radius+iris_radius)/2, iris_radius-.0002,
                         iris_radius, iris_radius+.00015, extent]
                radius = min(radii[ring], extent)
                xy = center_pixel + direction*radius/np.array([scale, -scale])
                point, _ = surface.cast(ray(xy))
                offset = edge_clearance + crown*max(0., 1-(radius/extent)**2)
                point[2] += offset
                vertices.append(point)
                if radius <= pupil_radius:
                    color = (.0045, .0055, .005)
                elif radius <= iris_radius+.00001:
                    striation = 1 + .13*math.sin(theta*37+radius*1600)*math.sin(theta*11+.8)
                    rim = .52 if radius >= iris_radius-.00021 else 1.
                    base_iris = srgb_to_linear((.20, .27, .24)) if restrained else (.075, .115, .095)
                    upper_shadow = 1-.30*max(0., direction[1])*radius/extent if restrained else 1.
                    color = tuple(value*striation*rim*upper_shadow for value in base_iris)
                else:
                    base_sclera = srgb_to_linear((.60, .62, .60)) if restrained else (.43, .47, .455)
                    upper_shadow = 1-.45*max(0., direction[1])*radius/extent if restrained else 1.
                    color = tuple(value*upper_shadow for value in base_sclera)
                colors.append((*color, 1.))
        for ring in range(rings):
            for angle_index in range(angular_steps):
                next_angle = (angle_index+1) % angular_steps
                a, b = start+ring*angular_steps+angle_index, start+ring*angular_steps+next_angle
                c, d = a+angular_steps, b+angular_steps
                for face in [(a, c, b), (b, c, d)]:
                    v = np.array([vertices[i] for i in face])
                    if np.linalg.norm(np.cross(v[1]-v[0], v[2]-v[0])) < 1e-11:
                        continue
                    centroid = (v.mean(0)-center_surface)[:2]
                    radius = np.linalg.norm(centroid)
                    material = 2 if radius < pupil_radius else (1 if radius < iris_radius+.00008 else 0)
                    triangles.append(face)
                    labels.append(material)
        eye_reports.append({**eye, "manual_polygon_scope": "Inner painted-eye area; excludes source eyeliner/lid margin",
                            "center_surface_source_gltf_world_y_up_m": center_surface.tolist(),
                            "source_triangle_indices": indices[center_triangle].tolist()})
    vertices = np.array(vertices)
    normals = np.zeros_like(vertices)
    for face in triangles:
        a, b, c = vertices[list(face)]
        normal = np.cross(b-a, c-a)
        for i in face:
            normals[i] += normal
    norms = np.linalg.norm(normals, axis=1)
    normals = np.divide(normals, norms[:,None], out=np.broadcast_to([0.,0.,1.],normals.shape).copy(), where=norms[:,None]>1e-12)
    # Direct glTF output: no Blender axis rotation is introduced into the root.
    local_vertices = (vertices-rigid_head[:3,3]) @ rigid_head[:3,:3]
    local_normals = normals @ rigid_head[:3,:3]
    if (local_normals @ rigid_head[:3,:3].T)[:,2].mean() <= 0:
        raise ValueError("Eye surfaces must face source glTF +Z")
    output.mkdir(parents=True, exist_ok=True)
    groups = [[face for face,label in zip(triangles,labels) if label==material] for material in range(3)]
    eye_path = output/'eyes.glb'
    write_glb(eye_path, local_vertices, local_normals, colors, groups, restrained)
    result = {"status": "candidate_requires_visual_and_pose_fit_review", "automatic_visual_approval": False,
              "source": {"path": str(source), "sha256": source_sha, "unchanged": hashlib.sha256(source.read_bytes()).hexdigest()==source_sha},
              "reference_review": {"path": str(args.reference_review), "sha256": hashlib.sha256(args.reference_review.read_bytes()).hexdigest()},
              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "candidate": {"path": str(eye_path), "sha256": hashlib.sha256(eye_path.read_bytes()).hexdigest(), "bytes": eye_path.stat().st_size,
                            "vertices": len(vertices), "triangles": len(triangles), "materials": 3, "texture_images": 0, "skins": 0},
              "attachment_contract": {"coordinate_system": "Original source glTF Head REST-local orthonormal basis, physical meters",
                                      "root_transform": "identity; direct glTF writer; no Blender C rotation",
                                      "required_socket_basis": [[1,0,0],[0,1,0],[0,0,1]],
                                      "source_head_rest_world_matrix_y_up": full_head.tolist(),
                                      "source_head_rest_rigid_world_matrix_y_up": rigid_head.tolist(),
                                      "source_head_world_scale": scales.tolist(),
                                      "runtime": "Attach under source Head BoneAttachment; inverse uniform imported rig scale only; retain external actor scale"},
              "fitting": {"method": "Manual inner-aperture polygons -> unchanged CPU-skinned REST surface rays -> restrained outward crown",
                          "appearance_calibration": args.appearance,
                          "clearance_m": edge_clearance, "maximum_front_direction_offset_m": edge_clearance+crown,
                          "pupil_radius_m": pupil_radius, "iris_radius_m": iris_radius, "eyes": eye_reports},
              "preserved": ["Original body GLB bytes", "Original meshes/UVs/materials/textures", "Original skeleton/inverse binds/weights", "Every original animation key"],
              "pending": ["Reimported GLB body/eyes overlay from exact reference cameras", "Side view, BVH clearance and head-pose fit", "Godot REST attachment/rig-scale checks", "Gameplay quality and AAA acceptance"]}
    if not result['source']['unchanged']:
        raise ValueError("Source changed during derivation")
    (output/'fit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['candidate'],indent=2))


if __name__ == '__main__':
    main()
