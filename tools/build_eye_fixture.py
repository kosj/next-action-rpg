"""Build independent native eye-fit test inputs from frozen glTF geometry.

Run from the repository root; Python's standard library is sufficient:

    python tools/build_eye_fixture.py \
      --eyes art_source/production/candidates/lyra-eye-sockets-001/eyes-web.glb \
      --refit art_source/production/candidates/lyra-eye-sockets-001/refit.json \
      --output build/verification/character-polish/lyra-eye-fit-reproduced.json

Existing outputs are refused. After reviewing an input change, use --replace
to deliberately replace a fixture. A color-only derivative additionally needs
--palette-audit its-audit.json; the archived refit/geometry reference remains
immutable and every byte outside COLOR_0 RGB must independently match it.

This generates test data, not collision, visual, adoption or AAA approval.
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

from inspect_glb import Inspector, inspect_glb, unpack_glb

ROOT = Path(__file__).resolve().parents[1]
HEAD_SPACE = "Original source glTF Head REST-local orthonormal basis; physical meters"
MATERIALS = (("EyeSclera", .46), ("GrayGreenIris", .34), ("Pupil", .28))
SAMPLES = (("front_pole", 0), ("back_pole", 1024), ("outer_surface", 832))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def matrix_multiply(a, b):
    return [[sum(a[row][k]*b[k][col] for k in range(4)) for col in range(4)] for row in range(4)]


def node_matrix(node):
    if "matrix" in node:
        return [[node["matrix"][col*4+row] for col in range(4)] for row in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    rotation = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    scale, position = node.get("scale", [1, 1, 1]), node.get("translation", [0, 0, 0])
    return [[rotation[row][col]*scale[col] for col in range(3)]+[position[row]] for row in range(3)]+[[0., 0., 0., 1.]]


def world_head(document):
    nodes = document["nodes"]
    heads = [index for index, node in enumerate(nodes) if node.get("name") == "Head"]
    require(len(heads) == 1, "Frozen body needs exactly one Head node")
    parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}
    def world(index):
        local = node_matrix(nodes[index])
        return matrix_multiply(world(parents[index]), local) if index in parents else local
    return world(heads[0])


def matrix_close(a, b, tolerance=1e-6):
    return max(abs(a[row][col]-b[row][col]) for row in range(4) for col in range(4)) <= tolerance


def validate_head(contract, source_document, body_document):
    identity = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    require(contract["coordinate_system"] == HEAD_SPACE and contract["root_transform"] == "identity; direct glTF writer", "Unsupported Head coordinate/root contract")
    require(contract["required_socket_basis"] == identity, "Expected identity socket basis; do not apply a second coordinate conversion")
    full = contract["source_head_rest_world_matrix_y_up"]
    rigid = contract["source_head_rest_rigid_world_matrix_y_up"]
    for matrix in (full, rigid):
        require(isinstance(matrix, list) and len(matrix) == 4 and all(isinstance(row, list) and len(row) == 4 for row in matrix), "Head matrices must be 4x4 rows")
        require(all(type(value) in (int, float) and math.isfinite(value) for row in matrix for value in row), "Nonfinite Head matrix")
        require(matrix[3] == [0., 0., 0., 1.], "Head matrix must be affine")
    require(matrix_close(full, world_head(source_document)) and matrix_close(full, world_head(body_document)), "Refit Head REST differs from the actual frozen body/source glTF nodes")
    scales = [math.sqrt(sum(full[row][col]**2 for row in range(3))) for col in range(3)]
    require(min(scales) > 0 and max(scales)-min(scales) < 1e-6, "Head requires positive uniform inherited scale")
    require(all(abs(scales[col]-contract["source_head_world_scale"][col]) < 1e-6 for col in range(3)), "Recorded Head scale differs from its matrix")
    for row in range(3):
        require(abs(full[row][3]-rigid[row][3]) < 1e-9, "Rigid/full Head origins differ")
        for col in range(3):
            require(abs(full[row][col]/scales[col]-rigid[row][col]) < 1e-6, "Rigid Head basis is not the normalized source Head")
    for a in range(3):
        for b in range(3):
            require(abs(sum(rigid[row][a]*rigid[row][b] for row in range(3))-(1 if a == b else 0)) < 1e-6, "Head rigid basis is not orthonormal")
    determinant = sum(rigid[0][a]*(rigid[1][(a+1)%3]*rigid[2][(a+2)%3]-rigid[1][(a+2)%3]*rigid[2][(a+1)%3]) for a in range(3))
    require(abs(determinant-1) < 1e-6, "Head basis must be right-handed")
    return full, rigid


def frozen_file(refit_path, record, sibling_names=()):
    candidates = [refit_path.parent/name for name in sibling_names]
    recorded = Path(record["path"])
    candidates.append(recorded if recorded.is_absolute() else ROOT/recorded)
    for candidate in candidates:
        if candidate.is_file():
            require(digest(candidate) == record["sha256"], "Frozen input SHA mismatch: "+portable(candidate))
            if "bytes" in record:
                require(candidate.stat().st_size == record["bytes"], "Frozen input byte count mismatch")
            return candidate.resolve()
    raise ValueError("Frozen input missing; use the archived refit with its source/geometry files: "+record["path"])


def load_glb(path):
    raw = path.read_bytes()
    document, binary, _ = unpack_glb(raw)
    return raw, document, binary


def validate_body(document):
    require(len(document.get("skins", [])) == 1 and len(document["skins"][0]["joints"]) == 53 and len(document.get("animations", [])) == 20, "Frozen socket body must retain its 53-bone/20-clip skin")
    require(len(document.get("meshes", [])) == 1 and len(document["meshes"][0]["primitives"]) == 2, "Socket body must have exactly the original surface and one inner lid")
    original, wall = document["meshes"][0]["primitives"]
    materials = document["materials"]
    original_material, lid = materials[original["material"]], materials[wall["material"]]
    require(original_material["name"] == "material_0" and "normalTexture" in original_material and "baseColorTexture" in original_material["pbrMetallicRoughness"], "Source body albedo/normal contract changed")
    pbr = lid["pbrMetallicRoughness"]
    require(lid["name"] == "NewEyelidInnerDepth" and lid.get("alphaMode", "OPAQUE") == "OPAQUE" and pbr["metallicFactor"] == 0 and pbr["roughnessFactor"] == .57 and pbr["baseColorFactor"][3] == 1, "Inner lid material differs from its bounded procedural contract")
    require(document["accessors"][wall["indices"]]["count"] == 136*3, "Expected only the reviewed 136-triangle lid wall")


def palette_proof(eyes, geometry, audit_path, refit_path, refit):
    audit = json.loads(audit_path.read_text())
    require(audit["source"]["sha256"] == refit["web_eye"]["sha256"] == digest(geometry), "Palette source does not chain to the frozen refit geometry")
    require(audit["candidate"]["sha256"] == digest(eyes), "Palette audit candidate SHA differs from the actual input")
    require(audit["refit"]["sha256"] == digest(refit_path), "Palette audit refers to another refit revision")
    base_raw, base, _ = load_glb(geometry)
    raw, document, _ = load_glb(eyes)
    require(base == document and len(base_raw) == len(raw), "Palette derivative changed glTF JSON or total bytes")
    attribute = base["meshes"][0]["primitives"][0]["attributes"]["COLOR_0"]
    accessor = base["accessors"][attribute]
    view = base["bufferViews"][accessor["bufferView"]]
    require(accessor["componentType"] == 5126 and accessor["type"] == "VEC4" and not accessor.get("sparse") and view["buffer"] == 0, "Expected embedded float RGBA palette attribute")
    binary_start = 20+struct.unpack_from("<I", base_raw, 12)[0]+8
    offset = binary_start+view.get("byteOffset", 0)+accessor.get("byteOffset", 0)
    stride = view.get("byteStride", 16)
    masked = bytearray(base_raw)
    changed_rows = changed_bytes = 0
    for index in range(accessor["count"]):
        start = offset+index*stride
        before, after = base_raw[start:start+12], raw[start:start+12]
        changed_rows += before != after
        changed_bytes += sum(a != b for a, b in zip(before, after))
        masked[start:start+12] = after
    require(bytes(masked) == raw, "Palette changed bytes outside COLOR_0 RGB, including headers, alpha, geometry or materials")
    require(changed_rows > 0 and changed_rows == audit["byte_audit"]["changed_RGB_vertex_rows"] and changed_bytes == audit["byte_audit"]["changed_byte_count"], "Palette changed-byte counts do not match the audit")
    return {"geometry_reference_sha256":digest(geometry), "palette_audit_sha256":digest(audit_path), "all_non_COLOR0_RGB_bytes_exact":True, "changed_RGB_vertex_rows":changed_rows, "changed_byte_count":changed_bytes}


def build_fixture(eyes, refit_path, palette_audit=None):
    refit = json.loads(refit_path.read_text())
    body = frozen_file(refit_path, refit["unchanged_body"], ("source.glb",))
    original = frozen_file(refit_path, refit["original_source_archive"])
    tracked = {path:digest(path) for path in (eyes, refit_path, body, original)}
    source_document = load_glb(original)[1]
    body_document = load_glb(body)[1]
    validate_body(body_document)
    full, rigid = validate_head(refit["attachment_contract"], source_document, body_document)
    geometry = eyes
    palette = None
    if palette_audit is None:
        require(tracked[eyes] == refit["web_eye"]["sha256"], "Eye SHA differs from frozen refit; color derivatives require --palette-audit")
    else:
        geometry = frozen_file(refit_path, refit["web_eye"], ("eyes-geometry-reference.glb", "eyes-web.glb"))
        tracked[geometry] = digest(geometry)
        tracked[palette_audit] = digest(palette_audit)
        palette = palette_proof(eyes, geometry, palette_audit, refit_path, refit)
    inspection = inspect_glb(eyes, require_embedded=True)
    require(inspection["structurally_valid"] and inspection["requirements_met"], "Eye GLB failed strict embedded structural inspection")
    raw, document, binary = load_glb(eyes)
    require(not document.get("skins") and not document.get("animations") and not document.get("images"), "Eyes must be static procedural geometry without skin, playback or textures")
    require(len(document.get("nodes", [])) == 1 and node_matrix(document["nodes"][0]) == [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], "Eye asset root must remain identity")
    require(len(document["meshes"]) == 1 and document["meshes"][0]["name"] == "FittedOcularInlays", "Unexpected eye mesh")
    primitives = document["meshes"][0]["primitives"]
    require(len(primitives) == len(document["materials"]) == 3, "Expected exactly three procedural eye material parts")
    require(inspection["counts"]["mesh_triangles"] == refit["web_eye"]["triangles"] == 3840, "Reviewed Web-eye topology changed")
    inspector = Inspector(document, binary)
    inspector.buffers()
    inspector.accessors()
    attributes = primitives[0]["attributes"]
    require(all(primitive["attributes"] == attributes for primitive in primitives), "Expected one shared eye POSITION/NORMAL/COLOR_0 layout")
    vertices = list(inspector.values(attributes["POSITION"]))
    colors = list(inspector.values(attributes["COLOR_0"]))
    require(len(vertices) == len(colors) == refit["web_eye"]["vertices"] == 2176, "Eye sample index layout changed")
    require(all(len(color) == 4 and color[3] == 1 and all(0 <= value <= 1 for value in color) for color in colors), "Expected finite opaque bounded eye vertex colors")
    material_expectations = []
    for index, (name, roughness) in enumerate(MATERIALS):
        material = document["materials"][index]
        pbr = material["pbrMetallicRoughness"]
        require(material["name"] == name and primitives[index]["material"] == index and material.get("alphaMode", "OPAQUE") == "OPAQUE" and not material.get("doubleSided", False), "Procedural eye part/material order changed")
        require(pbr["roughnessFactor"] == roughness and pbr["metallicFactor"] == 0 and pbr["baseColorFactor"] == [1,1,1,1], "Eye PBR response changed")
        require(not any(key.endswith("Texture") for key in pbr), "Unexpected eye material texture")
        indices = [value[0] for value in inspector.values(primitives[index]["indices"])]
        white = all(colors[vertex] == (1.,1.,1.,1.) for vertex in indices)
        require(not white, "Reviewed eye parts need their nonwhite vertex colors enabled")
        material_expectations.append({"name":name, "roughness":roughness, "metallic":pbr["metallicFactor"], "source_vertex_colors_constant_white":white, "vertex_color_required":not white})
    samples = []
    centers = {aperture["name"]:aperture["globe_center_source_world_y_up_m"] for aperture in refit["apertures"]}
    require(set(centers) == {"image_left", "image_right"}, "Expected both independently fitted eye centers")
    for eye, offset in (("image_left", 0), ("image_right", 1088)):
        for role, index in SAMPLES:
            vertex = offset+index
            point = list(vertices[vertex])
            world = [sum(rigid[row][col]*point[col] for col in range(3))+rigid[row][3] for row in range(3)]
            expected = centers[eye][:]
            if role in ("front_pole", "back_pole"):
                expected[2] += .0128 if role == "front_pole" else -.012
                require(math.dist(world, expected) < 1e-6, "Sample poles differ from refit center/radius or source Head basis")
            samples.append({"name":eye+"_"+role, "eye":eye, "role":role, "source_accessor_vertex":vertex, "head_rigid_local_m":point, "source_world_y_up_m":world, "source_linear_rgba":list(colors[vertex])})
    fixture = {"schema_version":1, "scope":"Frozen actual Web-eye vertices and independent source Head REST anchors; attachment/scale/material regression, not visual or AAA approval.",
        "source_body_sha256":refit["original_source_archive"]["sha256"], "socket_body_sha256":refit["unchanged_body"]["sha256"], "eye_glb_sha256":hashlib.sha256(raw).hexdigest(),
        "mesh_name":"FittedOcularInlays", "expected_triangles":3840, "materials":material_expectations,
        "source_head_rest_world_y_up_rows":full, "source_head_rest_rigid_world_y_up_rows":rigid, "samples":samples,
        "diameter_range_m":[.0235,.0255], "position_tolerance_m":.00002, "import_vertex_tolerance_m":.000003,
        "coordinate_contract":"glTF Head REST-local orthonormal basis in physical meters; original body glTF is source+Z-facing; gameplay applies exactly one PI yaw; eye root rotation/translation identity.",
        "provenance":{"derivation":portable(refit_path), "source_eye":portable(eyes)},
        "body_material_contract":{"body_meshes":1, "skin_bind_count":53, "surfaces":2, "textured_surface":{"index":0, "name":"material_0", "albedo_and_normal_required":True}, "new_inner_wall":{"index":1, "name":"NewEyelidInnerDepth", "triangles":136, "metallic":0.0, "roughness":.57, "opaque":True}},
        "import_vertex_color_channel_tolerance":1/255+.000001, "globe_centers_source_world_y_up_m":centers}
    if palette is not None:
        fixture["provenance"].update(palette_audit=portable(palette_audit), geometry_reference=portable(geometry))
        fixture["palette_derivation"] = palette
    require(all(digest(path) == before for path, before in tracked.items()), "An input changed during fixture generation")
    return fixture, set(tracked)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eyes", type=Path, required=True)
    parser.add_argument("--refit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--palette-audit", type=Path)
    parser.add_argument("--replace", action="store_true", help="explicitly replace an existing output fixture")
    args = parser.parse_args()
    require(not args.output.is_symlink(), "Refusing a symlink output")
    output = args.output.resolve()
    require(output.suffix.lower() == ".json", "Fixture output must be a JSON file")
    require(args.replace or not output.exists(), "Existing output refused; use --replace only for a reviewed update")
    eyes, refit = args.eyes.resolve(strict=True), args.refit.resolve(strict=True)
    audit = args.palette_audit.resolve(strict=True) if args.palette_audit else None
    require(output not in {eyes, refit, audit}, "Fixture output must not overwrite an input")
    fixture, inputs = build_fixture(eyes, refit, audit)
    require(output not in inputs, "Fixture output must not overwrite a frozen source")
    data = (json.dumps(fixture, indent=2)+"\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".eye-fixture-", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        if args.replace:
            os.replace(temporary, output)
        else:
            os.link(temporary, output) # Atomic no-clobber, including a racing creator.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps({"output":portable(output), "sha256":hashlib.sha256(data).hexdigest(), "eyes_sha256":fixture["eye_glb_sha256"], "samples":len(fixture["samples"])}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("Eye fixture generation refused: "+str(error), file=sys.stderr)
        raise SystemExit(1)
