"""GLB inspection contracts and malformed binary/reference regressions."""
import base64
from contextlib import redirect_stdout
import copy
from io import StringIO
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inspect_glb


def package(document, payload=None, extras=()):
    raw = json.dumps(document, separators=(",", ":")).encode("utf-8")
    raw += b" " * (-len(raw) % 4)
    chunks = [(inspect_glb.JSON_CHUNK, raw)]
    if payload is not None:
        chunks.append((inspect_glb.BIN_CHUNK, payload + b"\0" * (-len(payload) % 4)))
    chunks.extend(extras)
    body = b"".join(struct.pack("<II", len(data), kind) + data for kind, data in chunks)
    return struct.pack("<4sII", b"glTF", 2, len(body) + 12) + body


def candidate():
    payload = bytearray()
    views, accessors = [], []

    def accessor(fmt, values, component, shape, count):
        payload.extend(b"\0" * (-len(payload) % 4))
        data = struct.pack("<" + fmt, *values)
        views.append({"buffer": 0, "byteOffset": len(payload), "byteLength": len(data)})
        payload.extend(data)
        accessors.append({"bufferView": len(views) - 1, "componentType": component, "type": shape, "count": count})
        return len(accessors) - 1

    position = accessor("9f", [0, 0, 0, 1, 0, 0, 0, 1, 0], 5126, "VEC3", 3)
    indices = accessor("3H", [0, 1, 2], 5123, "SCALAR", 3)
    joints = accessor("12B", [0] * 12, 5121, "VEC4", 3)
    weights = accessor("12f", [1, 0, 0, 0] * 3, 5126, "VEC4", 3)
    times = accessor("2f", [0, 1], 5126, "SCALAR", 2)
    output = accessor("6f", [0, 0, 0, 0, 1, 0], 5126, "VEC3", 2)
    document = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "Hero", "mesh": 0, "skin": 0, "children": [1]},
                  {"name": "Root", "children": [2]}, {"name": "WeaponGrip"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": position, "JOINTS_0": joints, "WEIGHTS_0": weights}, "indices": indices}]}],
        "skins": [{"joints": [1], "skeleton": 1}],
        "animations": [{"name": "Idle", "samplers": [{"input": times, "output": output}],
                        "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}]}],
        "buffers": [{"byteLength": len(payload)}], "bufferViews": views, "accessors": accessors,
    }
    return document, bytes(payload)


class InspectGLBTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "candidate.glb"
        self.document, self.payload = candidate()

    def write(self, document=None, payload=None):
        self.path.write_bytes(package(self.document if document is None else document,
                                      self.payload if payload is None else payload))
        return self.path

    def inspect(self, **requirements):
        return inspect_glb.inspect_glb(self.write(), **requirements)

    def invalid(self, pattern):
        with self.assertRaisesRegex(inspect_glb.GLBError, pattern):
            self.inspect()

    def test_valid_candidate_meets_named_structure_requirements(self):
        result = self.inspect(require_skin=True, required_clips=["Idle"], required_nodes=["WeaponGrip"], require_embedded=True)
        self.assertTrue(result["requirements_met"])
        self.assertEqual(result["counts"]["mesh_triangles"], 1)
        self.assertEqual(result["counts"]["skinned_mesh_nodes"], 1)
        self.assertEqual(result["animations"][0]["duration_seconds"], 1)
        self.assertIn("appearance", result["verification_scope"])

    def test_unmet_contract_is_distinct_from_malformed_file(self):
        result = self.inspect(required_clips=["Run"], required_nodes=["MissingGrip"])
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["requirements_met"])
        self.assertEqual(len(result["errors"]), 2)
        self.document["nodes"][0].pop("skin")
        result = self.inspect(require_skin=True)
        self.assertEqual(result["counts"]["skins"], 1)
        self.assertFalse(result["requirements_met"], "An unused skin must not satisfy require-skin")

    def test_header_and_chunks_reject_truncation_alignment_and_duplicates(self):
        valid = package(self.document, self.payload)
        cases = [b"glTF", b"BAD!" + valid[4:], valid[:4] + struct.pack("<I", 1) + valid[8:],
                 valid[:-1], valid + b"\0", package(self.document, self.payload, [(inspect_glb.JSON_CHUNK, b"{}  ")])]
        bad_chunk = bytearray(valid)
        struct.pack_into("<I", bad_chunk, 12, 0xFFFFFFFC)
        cases.append(bytes(bad_chunk))
        for raw in cases:
            with self.subTest(length=len(raw)):
                self.path.write_bytes(raw)
                with self.assertRaises(inspect_glb.GLBError):
                    inspect_glb.inspect_glb(self.path)

    def test_buffer_view_and_accessor_ranges_are_checked(self):
        original = copy.deepcopy(self.document)
        for mutate, message in (
            (lambda d: d["buffers"][0].update(byteLength=1), "BIN size"),
            (lambda d: d["bufferViews"][0].update(byteLength=9999), "range exceeds buffer"),
            (lambda d: d["accessors"][0].update(count=9999), "range exceeds bufferView"),
            (lambda d: d["accessors"][0].update(byteOffset=1), "alignment"),
            (lambda d: d["bufferViews"][0].update(byteStride=8), "incompatible stride"),
            (lambda d: d["accessors"][0].update(type=[]), "unsupported componentType or type"),
        ):
            self.document = copy.deepcopy(original)
            mutate(self.document)
            with self.subTest(message=message):
                self.invalid(message)

    def test_references_and_node_hierarchy_are_checked(self):
        original = copy.deepcopy(self.document)
        for mutate, message in (
            (lambda d: d["nodes"][0].update(mesh=999), "outside table"),
            (lambda d: d["nodes"][0].update(mesh=True), "expected integer"),
            (lambda d: d["nodes"][2].update(children=[0]), "cycle"),
            (lambda d: d["nodes"][0].update(children=[1, 2]), "multiple parents"),
            (lambda d: d["meshes"][0]["primitives"][0].update(material=0), "outside table"),
            (lambda d: d["textures"].append({"source": 7}), "outside table"),
        ):
            self.document = copy.deepcopy(original)
            self.document["textures"] = []
            mutate(self.document)
            with self.subTest(message=message):
                self.invalid(message)

    def test_vertex_indices_and_skin_payload_are_checked(self):
        position = self.document["bufferViews"][1]["byteOffset"]
        altered = bytearray(self.payload)
        struct.pack_into("<H", altered, position + 4, 3)
        self.payload = bytes(altered)
        self.invalid("vertex index outside")
        self.document, self.payload = candidate()
        altered = bytearray(self.payload)
        altered[self.document["bufferViews"][2]["byteOffset"]] = 1
        self.payload = bytes(altered)
        self.invalid("JOINTS_0 index outside")
        self.document, self.payload = candidate()
        altered = bytearray(self.payload)
        start = self.document["bufferViews"][3]["byteOffset"]
        struct.pack_into("<4f", altered, start, 0, 0, 0, 0)
        self.payload = bytes(altered)
        self.invalid("WEIGHTS_0 must be nonnegative and normalized")

    def test_animations_require_valid_timing_output_and_channel(self):
        original = copy.deepcopy(self.document)
        for mutate, message in (
            (lambda d: d["animations"][0]["channels"][0].update(sampler=4), "outside table"),
            (lambda d: d["animations"][0]["channels"][0]["target"].update(node=10), "outside table"),
            (lambda d: d["animations"][0]["channels"][0]["target"].update(path="rotation"), "output shape/count"),
        ):
            self.document = copy.deepcopy(original)
            mutate(self.document)
            with self.subTest(message=message):
                self.invalid(message)
        self.document = original
        altered = bytearray(self.payload)
        struct.pack_into("<2f", altered, self.document["bufferViews"][4]["byteOffset"], 1, 0)
        self.payload = bytes(altered)
        self.invalid("strictly increasing")

    def test_nonfinite_binary_and_json_are_rejected(self):
        altered = bytearray(self.payload)
        struct.pack_into("<f", altered, 0, float("nan"))
        self.payload = bytes(altered)
        self.invalid("nonfinite float payload")
        self.document, self.payload = candidate()
        self.document["nodes"][0]["scale"] = [1e999, 1, 1]
        self.invalid("nonfinite number")

    def test_external_resources_are_not_loaded_and_embedded_rule_fails(self):
        self.document["buffers"][0]["uri"] = "https://example.invalid/do-not-fetch.bin?token=not-a-real-token"
        self.path.write_bytes(package(self.document))
        result = inspect_glb.inspect_glb(self.path, require_embedded=True, required_clips=["Idle"])
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["requirements_met"])
        self.assertEqual(result["resources"][0]["storage"], "external")
        self.assertNotIn("token=", json.dumps(result), "Reports must not copy temporary resource query strings")
        self.assertTrue(result["warnings"])

    def test_data_uri_buffer_and_image_are_embedded_and_validated(self):
        self.document["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(self.payload).decode()
        self.document["images"] = [{"uri": "data:image/png;base64,iVBORw=="}]
        self.path.write_bytes(package(self.document))
        result = inspect_glb.inspect_glb(self.path, require_embedded=True)
        self.assertTrue(result["requirements_met"])
        self.assertEqual([item["storage"] for item in result["resources"]], ["data_uri", "data_uri"])
        self.document["buffers"][0]["uri"] = "data:application/octet-stream;base64,%%%%"
        self.path.write_bytes(package(self.document))
        with self.assertRaisesRegex(inspect_glb.GLBError, "invalid base64"):
            inspect_glb.inspect_glb(self.path)

    def test_sparse_accessor_replacements_are_bounds_checked_and_applied(self):
        original_document, original_payload = candidate()
        for targets, replacements, expected_error in (([0, 2], [0, 2], None),
                                                       ([2, 0], [0, 2], "increase strictly"),
                                                       ([0, 2], [0, 3], "vertex index outside")):
            self.document = copy.deepcopy(original_document)
            payload = bytearray(original_payload)
            sparse_views = []
            for chunk in (bytes(targets), struct.pack("<2H", *replacements)):
                payload.extend(b"\0" * (-len(payload) % 4))
                sparse_views.append(len(self.document["bufferViews"]))
                self.document["bufferViews"].append({"buffer": 0, "byteOffset": len(payload), "byteLength": len(chunk)})
                payload.extend(chunk)
            self.document["buffers"][0]["byteLength"] = len(payload)
            accessor = self.document["accessors"][1]
            accessor.pop("bufferView")
            accessor["sparse"] = {"count": 2, "indices": {"bufferView": sparse_views[0], "componentType": 5121},
                                  "values": {"bufferView": sparse_views[1]}}
            self.payload = bytes(payload)
            with self.subTest(targets=targets, replacements=replacements):
                if expected_error:
                    self.invalid(expected_error)
                else:
                    self.assertTrue(self.inspect()["requirements_met"])

    def test_small_component_matrix_columns_require_four_byte_padding(self):
        payload = bytearray(self.payload)
        payload.extend(b"\0" * (-len(payload) % 4))
        view = {"buffer": 0, "byteOffset": len(payload), "byteLength": 24}
        self.document["bufferViews"].append(view)
        self.document["accessors"].append({"bufferView": len(self.document["bufferViews"]) - 1,
                                           "componentType": 5121, "type": "MAT3", "count": 2})
        payload.extend(b"\0" * 24)
        self.payload = bytes(payload)
        self.document["buffers"][0]["byteLength"] = len(payload)
        self.assertTrue(self.inspect()["requirements_met"])
        view["byteLength"] = 18  # Two 3x3 byte matrices still need 4-byte column alignment.
        self.invalid("range exceeds bufferView")

    def test_cli_reports_json_failures_and_exit_codes(self):
        self.write()
        output = StringIO()
        with redirect_stdout(output):
            status = inspect_glb.main([str(self.path), "--json", "--require-clip", "Run"])
        self.assertEqual(status, 1)
        self.assertFalse(json.loads(output.getvalue())["files"][0]["requirements_met"])
        output = StringIO()
        with redirect_stdout(output):
            status = inspect_glb.main([str(self.path), str(self.path.with_name("absent.glb")), "--json"])
        self.assertEqual(status, 1)
        self.assertEqual(len(json.loads(output.getvalue())["files"]), 2)
        with redirect_stdout(StringIO()):
            self.assertEqual(inspect_glb.main([str(self.path), "--require-skin", "--require-clip", "Idle"]), 0)


if __name__ == "__main__":
    unittest.main()
