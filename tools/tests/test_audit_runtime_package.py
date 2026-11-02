"""Synthetic package/header corruption tests; no engine or actual image decode."""

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit_runtime_package as tool


def texture():
    # Structurally sized WebP-container chunks; image codec content is not
    # decoded by this bounded package audit.
    header = b"GST2" + struct.pack("<8I", 1, 8, 4, 1 << 23, 0, 0, 0, 0)
    header += struct.pack("<IHHII", 2, 8, 4, 3, 5)
    chunk = b"RIFF" + struct.pack("<I", 4) + b"WEBP"
    return header + (struct.pack("<I", len(chunk)) + chunk) * 4


def package(path, files):
    base = 112
    payload = bytearray()
    directory = bytearray(struct.pack("<I", len(files)))
    for name, data in files:
        encoded = name.encode()
        encoded += b"\0" * (-len(encoded) % 4)
        directory += struct.pack("<I", len(encoded)) + encoded
        directory += struct.pack("<QQ16sI", len(payload), len(data), hashlib.md5(data).digest(), 0)
        payload += data
    header = b"GDPC" + struct.pack("<IIIIIQQ", 4, 4, 7, 2, 2, base, base + len(payload))
    path.write_bytes(header.ljust(base, b"\0") + payload + directory)


class RuntimePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pck = self.root / "index.pck"
        self.font = ".godot/imported/runefall_kr430.ttf-abcd.fontdata"
        self.files = [(self.font, b"RSCCfake-fontdata"),
                      ("assets/fonts/runefall_kr430.ttf.import",
                       f'[remap]\npath="res://{self.font}"\n\n[deps]\n'.encode())]

    def test_named_imported_files_and_actual_mip_chunks_are_reported(self):
        scene, image = ".godot/imported/npc.glb-abc.scn", ".godot/imported/npc_Image_0.png-def.ctex"
        files = self.files + [(scene, b"RSCCscene"), (image, texture()),
            ("assets/models/npc.glb.import", f'[remap]\npath="res://{scene}"\n[deps]\n'.encode()),
            ("assets/models/npc_Image_0.png.import", f'[remap]\npath="res://{image}"\n[deps]\n'.encode())]
        package(self.pck, files)
        report = tool.audit(self.root, asset_prefixes=["res://assets/models/npc"])
        self.assertTrue(report["passed"])
        group = report["asset_groups"][0]
        self.assertEqual(group["unique_imported_files"], 2)
        self.assertEqual(group["unique_imported_bytes"], len(b"RSCCscene") + len(texture()))
        imported = [x for record in group["import_records"] for x in record["imported_files"]]
        image_info = next(x["texture"] for x in imported if x["path"] == image)
        self.assertEqual(image_info["total_mip_levels"], 4)
        self.assertEqual(image_info["additional_mipmap_count"], 3)
        self.assertEqual(len(image_info["payload_chunks"]), 4)

    def test_original_or_duplicate_static_font_is_not_approved(self):
        files = self.files + [(".godot/imported/NotoSansKR.ttf-orig.fontdata", b"original"),
                              (".godot/imported/runefall_kr430.ttf-second.fontdata", b"second")]
        package(self.pck, files)
        report = tool.audit(self.root)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["original_variable_font_source_remap_and_fontdata_absent"])
        self.assertFalse(report["checks"]["static_fontdata_exactly_once"])

    def test_fixed_raw_web_cap_counts_all_files_without_decompressing_them(self):
        package(self.pck, self.files)
        with (self.root / "oversize.bin").open("wb") as stream:
            stream.truncate(tool.RAW_WEB_CAP)  # Sparse file, no150MB allocation.
        report = tool.audit(self.root)
        self.assertEqual(report["raw_web"]["cap_bytes"], 150_000_000)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["raw_web_within_unchanged_150M_cap"])
        self.assertLess(report["raw_web"]["remaining_bytes"], 0)

    def test_corrupt_payload_digest_or_duplicate_path_is_rejected(self):
        package(self.pck, self.files)
        raw = bytearray(self.pck.read_bytes())
        raw[112] ^= 1
        self.pck.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "MD5"):
            tool.audit(self.root)
        package(self.pck, self.files + [self.files[0]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            tool.Pck(self.pck)

    def test_pck_offset_and_ctex_mipmap_bounds_are_rejected(self):
        package(self.pck, self.files)
        raw = bytearray(self.pck.read_bytes())
        struct.pack_into("<Q", raw, 32, len(raw) + 1)
        self.pck.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            tool.Pck(self.pck)
        raw = bytearray(texture())
        struct.pack_into("<I", raw, 52, len(raw) * 10)
        with self.assertRaisesRegex(ValueError, "payload exceeds"):
            tool.inspect_ctex(raw)
        raw = bytearray(texture())
        struct.pack_into("<I", raw, 44, 12)
        with self.assertRaisesRegex(ValueError, "mip count"):
            tool.inspect_ctex(raw)


if __name__ == "__main__":
    unittest.main()
