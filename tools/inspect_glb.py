"""Inspect GLB 2.0 structure and explicit import requirements, without a renderer.

python tools/inspect_glb.py game/assets/models/*.glb --json
python tools/inspect_glb.py candidate.glb --require-skin --require-clip Idle --require-embedded

Exit 0: structural and requested checks passed. Exit 1: invalid/unreadable input
or unmet requirements. Exit 2: command-line usage error. Passing does not verify
appearance, deformation, animation quality, Godot import, licensing, or FPS.
External resources are reported but never loaded or fetched.
"""
import argparse
import base64
import binascii
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
MAX_FILE_BYTES = 256_000_000
MAX_DECODE_ELEMENTS = 5_000_000
COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
              5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
DIMENSIONS = {"SCALAR": (1, 1), "VEC2": (1, 2), "VEC3": (1, 3), "VEC4": (1, 4),
              "MAT2": (2, 2), "MAT3": (3, 3), "MAT4": (4, 4)}
SCOPE = ("Core GLB/glTF structure and explicitly requested requirements only; "
         "extension payload schemas, appearance, deformation, animation quality, "
         "Godot import, licensing and performance are unverified.")


class GLBError(ValueError):
    """Malformed or unsupported data that cannot pass structural inspection."""


def fail(message):
    raise GLBError(message)


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        fail(f"{label}: expected integer >= {minimum}")
    return value


def reference(value, table, label):
    index = integer(value, label)
    if index >= len(table):
        fail(f"{label}: index {index} outside table of {len(table)}")
    return index


def object_list(document, name):
    result = document.get(name, [])
    if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        fail(f"{name}: expected array of objects")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"JSON: duplicate member {key!r}")
        result[key] = value
    return result


def finite_json_float(value):
    result = float(value)
    if not math.isfinite(result):
        fail("JSON: number exceeds finite float range")
    return result


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def unpack_glb(data):
    if len(data) < 20:
        fail("GLB: missing header or JSON chunk")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2:
        fail("GLB: expected magic glTF and version 2")
    if length != len(data):
        fail(f"GLB: declared length {length} differs from actual {len(data)}")
    chunks = []
    offset = 12
    while offset < length:
        if offset + 8 > length:
            fail("GLB: truncated chunk header")
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size % 4 or offset + size > length:
            fail("GLB: chunk is unaligned or exceeds file length")
        chunks.append((kind, memoryview(data)[offset:offset + size]))
        offset += size
    if not chunks or chunks[0][0] != JSON_CHUNK:
        fail("GLB: JSON must be the first chunk")
    if sum(kind == JSON_CHUNK for kind, _ in chunks) != 1 or sum(kind == BIN_CHUNK for kind, _ in chunks) > 1:
        fail("GLB: duplicate JSON or BIN chunk")
    if any(kind == BIN_CHUNK and index != 1 for index, (kind, _) in enumerate(chunks)):
        fail("GLB: BIN must immediately follow JSON")
    try:
        document = json.loads(bytes(chunks[0][1]).decode("utf-8"), object_pairs_hook=unique_object,
                              parse_constant=lambda value: fail(f"JSON: nonfinite number {value}"),
                              parse_float=finite_json_float)
    except (ValueError, RecursionError) as error:
        fail(f"GLB JSON: {error}")
    if not isinstance(document, dict) or not isinstance(document.get("asset"), dict) or document["asset"].get("version") != "2.0":
        fail("glTF: asset.version must be 2.0")
    binary = next((payload for kind, payload in chunks if kind == BIN_CHUNK), None)
    ignored = [f"0x{kind:08x}" for kind, _ in chunks if kind not in (JSON_CHUNK, BIN_CHUNK)]
    return document, binary, ignored


def resource(uri, label):
    if not isinstance(uri, str) or not uri:
        fail(f"{label}: URI must be nonempty text")
    if not uri.startswith("data:"):
        return "external", None
    prefix, separator, payload = uri.partition(",")
    if not separator or not prefix.endswith(";base64"):
        fail(f"{label}: only base64 data URIs are supported")
    try:
        return "data_uri", memoryview(base64.b64decode(payload, validate=True))
    except (binascii.Error, ValueError) as error:
        fail(f"{label}: invalid base64 data URI ({error})")


class Inspector:
    def __init__(self, document, binary):
        self.doc = document
        self.tables = {name: object_list(document, name) for name in (
            "buffers", "bufferViews", "accessors", "nodes", "meshes", "materials",
            "skins", "animations", "images", "textures", "samplers", "scenes")}
        self.binary = binary
        self.buffer_data = []
        self.resources = []
        self.accessor_info = []
        self.sparse = {}
        self.warnings = []

    def ref(self, value, table, label):
        return reference(value, self.tables[table], label)

    def buffers(self):
        buffers = self.tables["buffers"]
        for index, buffer in enumerate(buffers):
            label = f"buffers[{index}]"
            length = integer(buffer.get("byteLength"), label + ".byteLength", 1)
            if "uri" in buffer:
                kind, data = resource(buffer["uri"], label)
            else:
                if index != 0 or self.binary is None:
                    fail(f"{label}: missing URI and matching BIN chunk")
                kind, data = "bin_chunk", self.binary
                if not length <= len(data) <= length + 3:
                    fail(f"{label}: BIN size differs from declared byteLength/padding")
            if data is not None and len(data) < length:
                fail(f"{label}: decoded resource shorter than byteLength")
            self.buffer_data.append(data)
            self.resources.append({"type": "buffer", "index": index, "storage": kind, "declared_bytes": length})
        if self.binary is not None and (not buffers or "uri" in buffers[0]):
            fail("BIN chunk has no matching embedded buffers[0]")
        for index, view in enumerate(self.tables["bufferViews"]):
            label = f"bufferViews[{index}]"
            buffer = self.ref(view.get("buffer"), "buffers", label + ".buffer")
            start = integer(view.get("byteOffset", 0), label + ".byteOffset")
            size = integer(view.get("byteLength"), label + ".byteLength", 1)
            if start + size > buffers[buffer]["byteLength"]:
                fail(f"{label}: range exceeds buffer byteLength")
            if "byteStride" in view:
                stride = integer(view["byteStride"], label + ".byteStride", 4)
                if stride > 252 or stride % 4:
                    fail(f"{label}: byteStride must be a multiple of 4 through 252")

    def view_bytes(self, index):
        view = self.tables["bufferViews"][index]
        data = self.buffer_data[view["buffer"]]
        if data is None:
            return None
        start = view.get("byteOffset", 0)
        return data[start:start + view["byteLength"]]

    def accessors(self):
        for index, accessor in enumerate(self.tables["accessors"]):
            label = f"accessors[{index}]"
            component = accessor.get("componentType")
            if type(component) is not int or component not in COMPONENTS or not isinstance(accessor.get("type"), str) or accessor["type"] not in DIMENSIONS:
                fail(f"{label}: unsupported componentType or type")
            code, size = COMPONENTS[component]
            columns, rows = DIMENSIONS[accessor["type"]]
            column_bytes = rows * size if columns == 1 else ((rows * size + 3) // 4) * 4
            offsets = [column * column_bytes + row * size for column in range(columns) for row in range(rows)]
            element_size = column_bytes * columns
            count = integer(accessor.get("count"), label + ".count", 1)
            offset = integer(accessor.get("byteOffset", 0), label + ".byteOffset")
            normalized = accessor.get("normalized", False)
            if type(normalized) is not bool or (normalized and component in (5125, 5126)):
                fail(f"{label}: invalid normalized flag")
            view_index = accessor.get("bufferView")
            stride = element_size
            if view_index is not None:
                self.ref(view_index, "bufferViews", label + ".bufferView")
                view = self.tables["bufferViews"][view_index]
                stride = view.get("byteStride", element_size)
                if stride < element_size or stride % size or (view.get("byteOffset", 0) + offset) % size:
                    fail(f"{label}: incompatible stride or component alignment")
                if offset + (count - 1) * stride + element_size > view["byteLength"]:
                    fail(f"{label}: range exceeds bufferView")
            elif offset:
                fail(f"{label}: byteOffset requires bufferView")
            self.accessor_info.append({"format": "<" + code, "offsets": offsets, "stride": stride,
                                       "size": element_size, "count": count, "view": view_index, "offset": offset})
            sparse = accessor.get("sparse")
            if sparse is not None:
                self.sparse[index] = self.read_sparse(index, sparse, count, element_size, size)
        for index, accessor in enumerate(self.tables["accessors"]):
            if accessor["componentType"] == 5126:
                values = self.values(index)
                if values is not None and any(not math.isfinite(value) for row in values for value in row):
                    fail(f"accessors[{index}]: nonfinite float payload")

    def read_sparse(self, index, sparse, count, element_size, component_size):
        label = f"accessors[{index}].sparse"
        if not isinstance(sparse, dict):
            fail(f"{label}: expected object")
        sparse_count = integer(sparse.get("count"), label + ".count", 1)
        if sparse_count > count:
            fail(f"{label}: sparse count exceeds accessor count")
        pieces = []
        for name in ("indices", "values"):
            item = sparse.get(name)
            if not isinstance(item, dict):
                fail(f"{label}.{name}: expected object")
            view_index = self.ref(item.get("bufferView"), "bufferViews", label + "." + name)
            view = self.tables["bufferViews"][view_index]
            if "byteStride" in view:
                fail(f"{label}.{name}: sparse bufferView cannot be strided")
            offset = integer(item.get("byteOffset", 0), label + "." + name + ".byteOffset")
            size = element_size
            alignment = component_size
            code = None
            if name == "indices":
                component = item.get("componentType")
                if type(component) is not int or component not in (5121, 5123, 5125):
                    fail(f"{label}.indices: invalid componentType")
                code, size = COMPONENTS[component]
                alignment = size
            if (view.get("byteOffset", 0) + offset) % alignment or offset + sparse_count * size > view["byteLength"]:
                fail(f"{label}.{name}: unaligned or out-of-bounds range")
            pieces.append((self.view_bytes(view_index), offset, size, code))
        indices, start, size, code = pieces[0]
        values, value_start, value_size, _ = pieces[1]
        if indices is None or values is None:
            return None
        if sparse_count > MAX_DECODE_ELEMENTS:
            fail(f"{label}: exceeds inspection decode limit")
        result = {}
        previous = -1
        info = self.accessor_info[index]
        for row in range(sparse_count):
            target = struct.unpack_from("<" + code, indices, start + row * size)[0]
            if target <= previous or target >= count:
                fail(f"{label}: indices must increase strictly within accessor count")
            previous = target
            result[target] = tuple(struct.unpack_from(info["format"], values, value_start + row * value_size + offset)[0]
                                   for offset in info["offsets"])
        return result

    def values(self, index):
        info = self.accessor_info[index]
        sparse = self.sparse.get(index, {})
        data = self.view_bytes(info["view"]) if info["view"] is not None else None
        if sparse is None or (info["view"] is not None and data is None):
            return None
        if info["count"] > MAX_DECODE_ELEMENTS:
            fail(f"accessors[{index}]: exceeds inspection decode limit")

        def rows():
            for row in range(info["count"]):
                if row in sparse:
                    yield sparse[row]
                elif data is None:
                    yield (0,) * len(info["offsets"])
                else:
                    start = info["offset"] + row * info["stride"]
                    yield tuple(struct.unpack_from(info["format"], data, start + offset)[0] for offset in info["offsets"])
        return rows()

    def graph(self):
        nodes = self.tables["nodes"]
        parents = {}
        for index, node in enumerate(nodes):
            label = f"nodes[{index}]"
            for field, table in (("mesh", "meshes"), ("skin", "skins")):
                if field in node:
                    self.ref(node[field], table, label + "." + field)
            if "skin" in node and "mesh" not in node:
                fail(f"{label}: skin requires mesh")
            children = node.get("children", [])
            if not isinstance(children, list):
                fail(f"{label}.children: expected array")
            for child in children:
                self.ref(child, "nodes", label + ".children")
                if child in parents:
                    fail(f"{label}: child has multiple parents or is repeated")
                parents[child] = index
            if "matrix" in node and any(field in node for field in ("translation", "rotation", "scale")):
                fail(f"{label}: matrix and TRS cannot both be present")
            for field, size in (("matrix", 16), ("translation", 3), ("rotation", 4), ("scale", 3)):
                if field in node:
                    values = node[field]
                    if not isinstance(values, list) or len(values) != size or any(not finite_number(value) for value in values):
                        fail(f"{label}.{field}: invalid finite transform")
        visited = set()
        for start in range(len(nodes)):
            path = set()
            current = start
            while current in parents and current not in visited:
                if current in path:
                    fail("nodes: hierarchy cycle")
                path.add(current)
                current = parents[current]
            visited.update(path)
        for index, scene in enumerate(self.tables["scenes"]):
            roots = scene.get("nodes", [])
            if not isinstance(roots, list):
                fail(f"scenes[{index}].nodes: expected array")
            seen = set()
            for root in roots:
                self.ref(root, "nodes", f"scenes[{index}].nodes")
                if root in parents or root in seen:
                    fail(f"scenes[{index}]: repeated or non-root node")
                seen.add(root)
        if "scene" in self.doc:
            self.ref(self.doc["scene"], "scenes", "scene")

    def meshes(self):
        primitive_count = triangles = 0
        accessors = self.tables["accessors"]
        for mesh_index, mesh in enumerate(self.tables["meshes"]):
            primitives = mesh.get("primitives")
            if not isinstance(primitives, list) or not primitives:
                fail(f"meshes[{mesh_index}]: missing primitives")
            for primitive in primitives:
                label = f"meshes[{mesh_index}].primitive[{primitive_count}]"
                primitive_count += 1
                if not isinstance(primitive, dict):
                    fail(f"{label}: expected object")
                extensions = primitive.get("extensions", {})
                if isinstance(extensions, dict) and "KHR_draco_mesh_compression" in extensions:
                    fail(f"{label}: compressed geometry unsupported; export decoded GLB for inspection")
                attributes = primitive.get("attributes")
                if not isinstance(attributes, dict) or "POSITION" not in attributes:
                    fail(f"{label}: missing POSITION attribute")
                for semantic, accessor in attributes.items():
                    self.ref(accessor, "accessors", label + "." + semantic)
                position = accessors[attributes["POSITION"]]
                if position["type"] != "VEC3" or position["componentType"] != 5126:
                    fail(f"{label}: POSITION must be float VEC3")
                count = position["count"]
                if any(accessors[index]["count"] != count for index in attributes.values()):
                    fail(f"{label}: attribute counts differ")
                if "material" in primitive:
                    self.ref(primitive["material"], "materials", label + ".material")
                if "indices" in primitive:
                    index = self.ref(primitive["indices"], "accessors", label + ".indices")
                    accessor = accessors[index]
                    if accessor["type"] != "SCALAR" or accessor["componentType"] not in (5121, 5123, 5125) or accessor.get("normalized", False):
                        fail(f"{label}: indices must be unsigned non-normalized SCALAR")
                    view = self.accessor_info[index]["view"]
                    if view is not None and "byteStride" in self.tables["bufferViews"][view]:
                        fail(f"{label}: index bufferView cannot be strided")
                    values = self.values(index)
                    if values is not None and any(row[0] >= count for row in values):
                        fail(f"{label}: vertex index outside POSITION count")
                    count = accessor["count"]
                mode = primitive.get("mode", 4)
                if type(mode) is not int or mode not in range(7):
                    fail(f"{label}: invalid primitive mode")
                if mode == 4:
                    if count % 3:
                        fail(f"{label}: TRIANGLES count must be divisible by 3")
                    triangles += count // 3
                elif mode in (5, 6):
                    triangles += max(0, count - 2)
                targets = primitive.get("targets", [])
                if not isinstance(targets, list):
                    fail(f"{label}: morph targets must be an array")
                for target in targets:
                    if not isinstance(target, dict):
                        fail(f"{label}: invalid morph target")
                    for semantic, index in target.items():
                        self.ref(index, "accessors", label + ".target." + semantic)
                        if accessors[index]["count"] != position["count"]:
                            fail(f"{label}: morph target count differs from POSITION")
        return primitive_count, triangles

    def skins(self):
        nodes = self.tables["nodes"]
        accessors = self.tables["accessors"]
        for index, skin in enumerate(self.tables["skins"]):
            label = f"skins[{index}]"
            joints = skin.get("joints")
            if not isinstance(joints, list) or not joints:
                fail(f"{label}: nonempty joints required")
            for joint in joints:
                self.ref(joint, "nodes", label + ".joints")
            if len(set(joints)) != len(joints):
                fail(f"{label}: duplicate joints")
            if "skeleton" in skin:
                self.ref(skin["skeleton"], "nodes", label + ".skeleton")
            if "inverseBindMatrices" in skin:
                accessor = accessors[self.ref(skin["inverseBindMatrices"], "accessors", label + ".inverseBindMatrices")]
                if accessor["type"] != "MAT4" or accessor["componentType"] != 5126 or accessor["count"] < len(joints):
                    fail(f"{label}: inverse bind matrices must cover every joint as float MAT4")
        attached = []
        for index, node in enumerate(nodes):
            if "skin" not in node:
                continue
            joint_count = len(self.tables["skins"][node["skin"]]["joints"])
            for primitive in self.tables["meshes"][node["mesh"]]["primitives"]:
                attributes = primitive["attributes"]
                if not all(name in attributes for name in ("JOINTS_0", "WEIGHTS_0")):
                    fail(f"nodes[{index}]: skinned primitive lacks JOINTS_0/WEIGHTS_0")
                joints = accessors[attributes["JOINTS_0"]]
                weights = accessors[attributes["WEIGHTS_0"]]
                if joints["type"] != "VEC4" or joints["componentType"] not in (5121, 5123) or joints.get("normalized", False):
                    fail(f"nodes[{index}]: invalid JOINTS_0 accessor")
                if weights["type"] != "VEC4" or weights["componentType"] not in (5121, 5123, 5126) or (weights["componentType"] != 5126 and not weights.get("normalized", False)):
                    fail(f"nodes[{index}]: invalid WEIGHTS_0 accessor")
                values = self.values(attributes["JOINTS_0"])
                if values is not None and any(joint >= joint_count for row in values for joint in row):
                    fail(f"nodes[{index}]: JOINTS_0 index outside skin joints")
                values = self.values(attributes["WEIGHTS_0"])
                if values is not None:
                    scale = {5121: 255, 5123: 65535, 5126: 1}[weights["componentType"]]
                    if any(any(weight < 0 or weight > scale for weight in row) or abs(sum(row) / scale - 1) > 0.02 for row in values):
                        fail(f"nodes[{index}]: WEIGHTS_0 must be nonnegative and normalized")
            attached.append(index)
        return attached

    def animations(self):
        result = []
        accessors = self.tables["accessors"]
        for index, animation in enumerate(self.tables["animations"]):
            label = f"animations[{index}]"
            samplers = animation.get("samplers")
            channels = animation.get("channels")
            if not isinstance(samplers, list) or not samplers or not all(isinstance(item, dict) for item in samplers) or not isinstance(channels, list) or not channels:
                fail(f"{label}: nonempty samplers and channels required")
            times = []
            for sampler_index, sampler in enumerate(samplers):
                for field in ("input", "output"):
                    self.ref(sampler.get(field), "accessors", label + ".sampler." + field)
                input_accessor = accessors[sampler["input"]]
                output_accessor = accessors[sampler["output"]]
                if input_accessor["type"] != "SCALAR" or input_accessor["componentType"] != 5126 or output_accessor["componentType"] != 5126:
                    fail(f"{label}: animation input must be float SCALAR and output float")
                if sampler.get("interpolation", "LINEAR") not in ("LINEAR", "STEP", "CUBICSPLINE"):
                    fail(f"{label}: invalid interpolation")
                values = self.values(sampler["input"])
                span = None
                if values is not None:
                    first = previous = None
                    for (time,) in values:
                        if time < 0 or (previous is not None and time <= previous):
                            fail(f"{label}.samplers[{sampler_index}]: times must be nonnegative and strictly increasing")
                        first = time if first is None else first
                        previous = time
                    span = previous - first
                times.append(span)
            targeted = set()
            for channel in channels:
                if not isinstance(channel, dict) or not isinstance(channel.get("target"), dict):
                    fail(f"{label}: invalid channel target")
                sampler = samplers[reference(channel.get("sampler"), samplers, label + ".channel.sampler")]
                target = channel["target"]
                node = self.ref(target.get("node"), "nodes", label + ".target.node")
                path = target.get("path")
                if path not in ("translation", "rotation", "scale", "weights"):
                    fail(f"{label}: unsupported target path")
                if (node, path) in targeted:
                    fail(f"{label}: duplicate node/path animation channel")
                targeted.add((node, path))
                output = accessors[sampler["output"]]
                input_count = accessors[sampler["input"]]["count"]
                multiplier = 3 if sampler.get("interpolation") == "CUBICSPLINE" else 1
                if path != "weights":
                    expected_type = "VEC4" if path == "rotation" else "VEC3"
                    if output["type"] != expected_type or output["count"] != input_count * multiplier:
                        fail(f"{label}: animation output shape/count does not match channel")
                else:
                    mesh = self.tables["nodes"][node].get("mesh")
                    if mesh is None:
                        fail(f"{label}: weights target requires mesh node")
                    morph_counts = {len(primitive.get("targets", [])) for primitive in self.tables["meshes"][mesh]["primitives"]}
                    if len(morph_counts) != 1 or not next(iter(morph_counts)):
                        fail(f"{label}: weights target lacks consistent morph targets")
                    if output["type"] != "SCALAR" or output["count"] != input_count * multiplier * next(iter(morph_counts)):
                        fail(f"{label}: morph weight output count mismatch")
            name = animation.get("name")
            if name is not None and not isinstance(name, str):
                fail(f"{label}: name must be text")
            result.append({"index": index, "name": name, "channels": len(channels),
                           "duration_seconds": max(times) if all(time is not None for time in times) else None})
        return result

    def images(self):
        for index, image in enumerate(self.tables["images"]):
            label = f"images[{index}]"
            if ("uri" in image) == ("bufferView" in image):
                fail(f"{label}: exactly one of uri and bufferView required")
            if "uri" in image:
                kind, data = resource(image["uri"], label)
            else:
                view = self.ref(image["bufferView"], "bufferViews", label + ".bufferView")
                if not isinstance(image.get("mimeType"), str) or not image["mimeType"]:
                    fail(f"{label}: bufferView image requires mimeType")
                data = self.view_bytes(view)
                kind = "buffer_view" if data is not None else "external_buffer_view"
            self.resources.append({"type": "image", "index": index, "storage": kind,
                                   "bytes_available": len(data) if data is not None else None})
        for index, texture in enumerate(self.tables["textures"]):
            if "source" in texture:
                self.ref(texture["source"], "images", f"textures[{index}].source")
            if "sampler" in texture:
                self.ref(texture["sampler"], "samplers", f"textures[{index}].sampler")
        def check_texture_info(value, label):
            if not isinstance(value, dict):
                fail(f"{label}: expected texture info object")
            self.ref(value.get("index"), "textures", label + ".index")
        for index, material in enumerate(self.tables["materials"]):
            for field in ("normalTexture", "occlusionTexture", "emissiveTexture"):
                if field in material:
                    check_texture_info(material[field], f"materials[{index}].{field}")
            pbr = material.get("pbrMetallicRoughness", {})
            if not isinstance(pbr, dict):
                fail(f"materials[{index}]: invalid PBR object")
            for field in ("baseColorTexture", "metallicRoughnessTexture"):
                if field in pbr:
                    check_texture_info(pbr[field], f"materials[{index}].{field}")


def inspect_glb(path, *, require_skin=False, required_clips=(), required_nodes=(), require_embedded=False):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        fail(f"GLB exceeds inspection byte limit {MAX_FILE_BYTES}")
    data = path.read_bytes()
    document, binary, ignored_chunks = unpack_glb(data)
    inspector = Inspector(document, binary)
    inspector.buffers()
    inspector.accessors()
    inspector.graph()
    primitives, triangles = inspector.meshes()
    attached = inspector.skins()
    animations = inspector.animations()
    inspector.images()
    nodes = inspector.tables["nodes"]
    node_names = [node.get("name") for node in nodes]
    if any(name is not None and not isinstance(name, str) for name in node_names):
        fail("nodes: names must be text")
    errors = []
    if require_skin and not attached:
        errors.append("require-skin: no mesh node has a valid attached skin and JOINTS_0/WEIGHTS_0")
    for name in required_nodes:
        if node_names.count(name) != 1:
            errors.append(f"require-node: expected exactly one node named {name!r}")
    for name in required_clips:
        matches = [animation for animation in animations if animation["name"] == name]
        if len(matches) != 1:
            errors.append(f"require-clip: expected exactly one animation named {name!r}")
        elif matches[0]["duration_seconds"] is None or matches[0]["duration_seconds"] <= 0:
            errors.append(f"require-clip: {name!r} needs an inspectable nonzero time span")
    external = [item for item in inspector.resources if item["storage"] in ("external", "external_buffer_view")]
    if require_embedded and external:
        errors.append(f"require-embedded: {len(external)} external resource references")
    warnings = inspector.warnings
    if external:
        warnings.append("External resources were not loaded; associated binary values cannot all be validated.")
    if ignored_chunks:
        warnings.append("Unknown GLB chunks ignored: " + ", ".join(ignored_chunks))
    return {
        "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "structurally_valid": True, "requirements_met": not errors, "errors": errors,
        "counts": {"nodes": len(nodes), "meshes": len(inspector.tables["meshes"]),
                   "mesh_primitives": primitives, "mesh_triangles": triangles,
                   "materials": len(inspector.tables["materials"]), "skins": len(inspector.tables["skins"]),
                   "skinned_mesh_nodes": len(attached), "animations": len(animations)},
        "triangle_count_scope": "Unique mesh primitives, not scene instances/draw calls; strip/fan counts include degenerates.",
        "node_names": node_names, "animations": animations, "resources": inspector.resources,
        "all_resource_bytes_available": not external,
        "warnings": warnings, "verification_scope": SCOPE,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON, including failures")
    parser.add_argument("--require-skin", action="store_true", help="Require a mesh node with a valid skin and joint/weight attributes")
    parser.add_argument("--require-clip", action="append", default=[], metavar="NAME", help="Require a unique named animation with an inspectable nonzero span (repeatable)")
    parser.add_argument("--require-node", action="append", default=[], metavar="NAME", help="Require a unique node name (repeatable)")
    parser.add_argument("--require-embedded", action="store_true", help="Reject external buffers/images; does not fetch them")
    args = parser.parse_args(argv)
    reports = []
    for path in args.paths:
        try:
            report = inspect_glb(path, require_skin=args.require_skin, required_clips=args.require_clip,
                                 required_nodes=args.require_node, require_embedded=args.require_embedded)
        except (OSError, GLBError) as error:
            report = {"path": str(path), "structurally_valid": False, "requirements_met": False, "errors": [str(error)]}
        reports.append(report)
    if args.json:
        print(json.dumps({"schema_version": 1, "verification_scope": SCOPE, "files": reports}, ensure_ascii=False, indent=2))
    else:
        print(SCOPE)
        for report in reports:
            status = "PASS" if report["structurally_valid"] and report["requirements_met"] else "FAIL"
            print(f"{status} {report['path']}")
            if "counts" in report:
                print("  " + json.dumps(report["counts"]))
            for message in report["errors"]:
                print("  ERROR: " + message)
            for message in report.get("warnings", []):
                print("  NOTE: " + message)
    return 0 if all(report["structurally_valid"] and report["requirements_met"] for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
