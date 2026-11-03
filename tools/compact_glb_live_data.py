"""Losslessly compact core GLB live accessor/view data, with semantic receipts.

No rebake, numeric conversion, image encoding or runtime adoption. Only one
embedded buffer, core glTF2 and embedded bufferView images are supported;
extensions/unknown GLB chunks/external resources fail closed. The existing
stdlib-only inspect_glb parser validates all ranges, sparse and strided data.
Opaque extras are preserved, not interpreted as custom index-reference schemas.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

if __package__:
    from .inspect_glb import Inspector, unpack_glb, MAX_FILE_BYTES
else:
    from inspect_glb import Inspector, unpack_glb, MAX_FILE_BYTES

SCHEMA = 1
SCOPE = "Core glTF live-data byte/semantic preservation only; no native/visual/performance/AAA approval"
TOP_LEVEL = {"asset", "scene", "scenes", "nodes", "animations", "materials", "meshes",
             "textures", "images", "skins", "accessors", "bufferViews", "samplers",
             "buffers", "extensionsUsed", "extensionsRequired", "extras"}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _extensions(value):
    if isinstance(value, dict):
        if value.get("extensions"):
            raise ValueError("Extension reference schemas are unsupported")
        for key, child in value.items():
            if key != "extras":
                _extensions(child)
    elif isinstance(value, list):
        for child in value:
            _extensions(child)


def _read(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("GLB exceeds the bounded inspection size")
    data = path.read_bytes()
    doc, binary, unknown = unpack_glb(data)
    if unknown or binary is None:
        raise ValueError("Only JSON plus one embedded BIN chunk is supported")
    if set(doc) - TOP_LEVEL or doc.get("extensionsUsed") or doc.get("extensionsRequired"):
        raise ValueError("Unknown top-level/extension reference schemas are unsupported")
    _extensions(doc)
    buffers = doc.get("buffers", [])
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError("Exactly one embedded buffer is required")
    for image in doc.get("images", []):
        if "uri" in image or "bufferView" not in image:
            raise ValueError("Images must use embedded bufferViews")
    names = [animation.get("name") for animation in doc.get("animations", [])]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ValueError("Animation names must be explicit and unique")
    inspector = Inspector(doc, binary)
    inspector.buffers()
    inspector.accessors()
    inspector.graph()
    inspector.meshes()
    inspector.skins()
    inspector.animations()
    inspector.images()
    return data, doc, binary, inspector


def _references(doc):
    """All retained core owners, including unused animation samplers."""
    accessors = set()
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            accessors.update(primitive.get("attributes", {}).values())
            if "indices" in primitive:
                accessors.add(primitive["indices"])
            for target in primitive.get("targets", []):
                accessors.update(target.values())
    for skin in doc.get("skins", []):
        if "inverseBindMatrices" in skin:
            accessors.add(skin["inverseBindMatrices"])
    for animation in doc.get("animations", []):
        for sampler in animation["samplers"]:
            accessors.update((sampler["input"], sampler["output"]))
    views = {image["bufferView"] for image in doc.get("images", [])}
    for index in accessors:
        accessor = doc["accessors"][index]
        if "bufferView" in accessor:
            views.add(accessor["bufferView"])
        if "sparse" in accessor:
            views.update(accessor["sparse"][piece]["bufferView"] for piece in ("indices", "values"))
    return sorted(accessors), sorted(views)


def _fingerprints(doc, inspector):
    live, _ = _references(doc)
    cached = {}

    def view(index):
        descriptor = copy.deepcopy(doc["bufferViews"][index])
        descriptor.pop("buffer")
        descriptor.pop("byteOffset", None)
        return {"descriptor": descriptor, "payload_sha256": _sha(inspector.view_bytes(index))}

    def accessor(index):
        if index in cached:
            return cached[index]
        declaration = copy.deepcopy(doc["accessors"][index])
        info = inspector.accessor_info[index]
        dense = inspector.view_bytes(info["view"]) if info["view"] is not None else None
        if "bufferView" in declaration:
            declaration["bufferView"] = view(declaration["bufferView"])
        patches = {}
        sparse = declaration.get("sparse")
        if sparse:
            original = doc["accessors"][index]["sparse"]
            indices, values = original["indices"], original["values"]
            index_bytes = inspector.view_bytes(indices["bufferView"])
            value_bytes = inspector.view_bytes(values["bufferView"])
            code, size = {5121:("B", 1), 5123:("H", 2), 5125:("I", 4)}[indices["componentType"]]
            for row in range(original["count"]):
                target = struct.unpack_from("<"+code, index_bytes, indices.get("byteOffset", 0)+row*size)[0]
                patches[target] = (value_bytes, values.get("byteOffset", 0)+row*info["size"])
            for piece in ("indices", "values"):
                sparse[piece]["bufferView"] = view(sparse[piece]["bufferView"])
        digest = hashlib.sha256()
        component_size = struct.calcsize(info["format"])
        zero = b"\0"*component_size
        for row in range(info["count"]):
            payload, start = patches.get(row, (dense, info["offset"]+row*info["stride"]))
            for offset in info["offsets"]:
                digest.update(zero if payload is None else payload[start+offset:start+offset+component_size])
        result = {"declaration": declaration, "count": info["count"],
                  "component_type": doc["accessors"][index]["componentType"],
                  "normalized": doc["accessors"][index].get("normalized", False),
                  "byte_stride": info["stride"], "value_bytes_sha256": digest.hexdigest()}
        result["sha256"] = _sha(_canonical(result))
        cached[index] = result
        return result

    def reference(index):
        return accessor(index)["sha256"]

    meshes = copy.deepcopy(doc.get("meshes", []))
    for mesh in meshes:
        for primitive in mesh["primitives"]:
            primitive["attributes"] = {name:reference(index) for name, index in primitive["attributes"].items()}
            if "indices" in primitive:
                primitive["indices"] = reference(primitive["indices"])
            if "targets" in primitive:
                primitive["targets"] = [{name:reference(index) for name, index in target.items()} for target in primitive["targets"]]
    skins = copy.deepcopy(doc.get("skins", []))
    for skin in skins:
        if "inverseBindMatrices" in skin:
            skin["inverseBindMatrices"] = reference(skin["inverseBindMatrices"])
    images = []
    for image in doc.get("images", []):
        value = copy.deepcopy(image)
        value["bufferView"] = view(value["bufferView"])
        images.append(value)
    clips = {}
    for animation in doc.get("animations", []):
        value = copy.deepcopy(animation)
        for sampler in value["samplers"]:
            sampler["input"] = reference(sampler["input"])
            sampler["output"] = reference(sampler["output"])
        channels = []
        for channel in animation["channels"]:
            sampler = animation["samplers"][channel["sampler"]]
            node = channel["target"]["node"]
            input_fp, output_fp = accessor(sampler["input"]), accessor(sampler["output"])
            channels.append({"node_index": node, "node_name": doc["nodes"][node].get("name"),
                "path": channel["target"]["path"], "interpolation": sampler.get("interpolation", "LINEAR"),
                "input_sha256": input_fp["sha256"], "output_sha256": output_fp["sha256"],
                "input_value_bytes_sha256": input_fp["value_bytes_sha256"],
                "output_value_bytes_sha256": output_fp["value_bytes_sha256"]})
        clips[animation["name"]] = {"sha256": _sha(_canonical(value)), "channel_count": len(channels), "channels": channels}
    static = {key:value for key, value in doc.items() if key not in ("buffers", "bufferViews", "accessors", "meshes", "skins", "images", "animations")}
    # IDs/offsets disappear only where their core reference semantics are known.
    buffer_metadata = copy.deepcopy(doc["buffers"][0])
    buffer_metadata.pop("byteLength")
    result = {"schema_version": SCHEMA, "static_json_sha256": _sha(_canonical(static)),
              "buffer_metadata": buffer_metadata,
              "mesh_skin_sha256": _sha(_canonical({"meshes":meshes, "skins":skins})),
              "images": images, "clips": clips,
              "live_accessors": {accessor(index)["sha256"]:accessor(index) for index in live}}
    result["semantic_sha256"] = _sha(_canonical(result))
    return result


def semantic_fingerprints(path):
    """Return index/offset-independent fingerprints; no file/path SHA in result.

    Compare complete dictionaries for lossless compaction. For changed actions,
    compare clips[name] and mesh_skin/static/images separately across candidates.
    """
    _, doc, _, inspector = _read(path)
    return _fingerprints(doc, inspector)


def compact_document(source_path, output_path):
    """Create a NEW GLB, verify every retained semantic/payload byte, return receipt."""
    source, output = Path(source_path), Path(output_path)
    if source.resolve() == output.resolve() or output.exists() or output.is_symlink():
        raise ValueError("Compaction requires a distinct new output; never overwrite/in-place")
    original, doc, binary, inspector = _read(source)
    before = _fingerprints(doc, inspector)
    live_accessors, live_views = _references(doc)
    result = copy.deepcopy(doc)
    accessor_map = {old:new for new, old in enumerate(live_accessors)}
    view_map = {old:new for new, old in enumerate(live_views)}
    packed = bytearray()
    result["bufferViews"] = []
    for old in live_views:
        packed.extend(b"\0"*((-len(packed)) % 4))
        value = copy.deepcopy(doc["bufferViews"][old])
        value["buffer"] = 0
        value["byteOffset"] = len(packed)
        packed.extend(inspector.view_bytes(old))
        result["bufferViews"].append(value)
    result["accessors"] = []
    for old in live_accessors:
        value = copy.deepcopy(doc["accessors"][old])
        if "bufferView" in value:
            value["bufferView"] = view_map[value["bufferView"]]
        for piece in value.get("sparse", {}).values():
            if isinstance(piece, dict) and "bufferView" in piece:
                piece["bufferView"] = view_map[piece["bufferView"]]
        result["accessors"].append(value)
    for mesh in result.get("meshes", []):
        for primitive in mesh["primitives"]:
            primitive["attributes"] = {key:accessor_map[index] for key, index in primitive["attributes"].items()}
            if "indices" in primitive:
                primitive["indices"] = accessor_map[primitive["indices"]]
            for target in primitive.get("targets", []):
                for key, index in target.items():
                    target[key] = accessor_map[index]
    for skin in result.get("skins", []):
        if "inverseBindMatrices" in skin:
            skin["inverseBindMatrices"] = accessor_map[skin["inverseBindMatrices"]]
    for animation in result.get("animations", []):
        for sampler in animation["samplers"]:
            for key in ("input", "output"):
                sampler[key] = accessor_map[sampler[key]]
    for image in result.get("images", []):
        image["bufferView"] = view_map[image["bufferView"]]
    result["buffers"][0]["byteLength"] = len(packed)
    json_bytes = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    json_bytes += b" "*((-len(json_bytes)) % 4)
    packed.extend(b"\0"*((-len(packed)) % 4))
    encoded = struct.pack("<4sII", b"glTF", 2, 28+len(json_bytes)+len(packed))
    encoded += struct.pack("<II", len(json_bytes), 0x4E4F534A)+json_bytes
    encoded += struct.pack("<II", len(packed), 0x004E4942)+packed
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as target:
            created = True
            target.write(encoded)
        after = semantic_fingerprints(output)
        if before != after or source.read_bytes() != original:
            raise ValueError("Compaction semantic/payload/source-preservation mismatch")
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"schema_version": SCHEMA, "passed": True, "scope": SCOPE,
        "source": {"path":str(source), "bytes":len(original), "sha256":_sha(original)},
        "output": {"path":str(output), "bytes":len(encoded), "sha256":_sha(encoded)},
        "saved_bytes":len(original)-len(encoded), "semantic_snapshot_equal":True,
        "semantic_sha256":before["semantic_sha256"],
        "accessors": {"before":len(doc.get("accessors", [])), "after":len(live_accessors)},
        "buffer_views": {"before":len(doc.get("bufferViews", [])), "after":len(live_views)},
        "buffer_bytes": {"before":doc["buffers"][0]["byteLength"], "after":result["buffers"][0]["byteLength"]},
        "clips": {name:{"sha256":clip["sha256"], "channel_count":clip["channel_count"]} for name, clip in before["clips"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.report and (args.report.exists() or args.report.is_symlink()
            or args.report.resolve() in (args.source.resolve(), args.output.resolve())):
        parser.error("Report must also be a distinct new file")
    report = compact_document(args.source, args.output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as target:
            target.write(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
