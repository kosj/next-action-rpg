"""Portable freeze/header/proof guards without launching Godot or encoding."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compare_ctex_storage as tool
from test_audit_runtime_package import package, texture


class CtexStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.filename = "body_Image_0.png-123.ctex"
        self.data = texture()
        (self.cache / self.filename).write_bytes(self.data)
        self.pck = self.root / "index.pck"
        package(self.pck, [(".godot/imported/" + self.filename, self.data)])
        self.frozen = self.root / "frozen"
        self.project = self.root / "project.godot"
        self.project.write_text('config_version=5\n')

    def freeze(self):
        return tool.freeze(self.cache, self.pck, [], self.frozen)

    def test_byte_exact_portable_freeze_and_prepare_do_not_launch_or_mutate_cache(self):
        original = (self.cache / self.filename).read_bytes()
        manifest = self.freeze()
        self.assertEqual(manifest["cases"][0]["bytes"], len(original))
        self.assertTrue(manifest["cases"][0]["cache_matches_existing_pck_md5"])
        self.assertEqual((self.frozen / "inputs" / self.filename).read_bytes(), original)
        output = self.root / "proof"
        config = tool.prepare(self.frozen, self.cache, self.project, output)
        self.assertEqual(config["expected_cases"], 1)
        self.assertEqual((self.cache / self.filename).read_bytes(), original)
        self.assertFalse((output / "result.json").exists())
        with self.assertRaisesRegex(ValueError, "new, nonexistent"):
            tool.prepare(self.frozen, self.cache, self.project, output)

    def test_tampered_frozen_bytes_and_path_escape_are_rejected(self):
        self.freeze()
        (self.frozen / "inputs" / self.filename).write_bytes(b"damaged")
        with self.assertRaisesRegex(ValueError, "bytes/SHA"):
            tool.prepare(self.frozen, self.cache, self.project, self.root / "proof")
        self.assertFalse((self.root / "proof").exists())
        manifest = json.loads((self.frozen / "inventory.json").read_text())
        manifest["cases"][0]["name"] = "../escape.ctex"
        (self.frozen / "inventory.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Invalid/duplicate"):
            tool.frozen_cases(self.frozen)

    def test_changed_payload_format_and_symlink_sources_are_rejected(self):
        source = self.cache / self.filename
        source.unlink()
        source.symlink_to(self.pck)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            self.freeze()
        self.assertFalse(self.frozen.exists())
        source.unlink()
        changed = bytearray(self.data)
        changed[36:40] = (0).to_bytes(4, "little")
        source.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "WebP CTEX"):
            self.freeze()

    def test_incomplete_header_format_mip_or_RGBA_proof_never_passes(self):
        self.freeze()
        config = tool.prepare(self.frozen, self.cache, self.project, self.root / "proof")
        case = {"name": self.filename, "passed": True, "first52_header_bytes_exact": True,
                "before_sha256": hashlib.sha256(self.data).hexdigest(),
                "after_sha256": hashlib.sha256(self.data).hexdigest(),
                "before_bytes": len(self.data), "after_bytes": len(self.data), "saved_bytes": 0,
                "mip_levels": 4, "mips": [{"level": i, "dimensions_exact": True,
                    "decoded_format_exact": True, "complete_RGBA_bytes_exact_including_transparent_RGB": True,
                    "before_RGBA_sha256": "1" * 64, "after_RGBA_sha256": "1" * 64} for i in range(4)]}
        result = {"status": "complete_all_actual_imported_mips_RGBA_exact", "cases": [case]}
        self.assertEqual(tool.validate_result(result, config)["mip_levels"], 4)
        for change in ("header", "format", "mip", "RGBA"):
            damaged = copy.deepcopy(result)
            item = damaged["cases"][0]
            if change == "header": item["first52_header_bytes_exact"] = False
            elif change == "format": item["mips"][1]["decoded_format_exact"] = False
            elif change == "mip": item["mips"].pop()
            else: item["mips"][0]["after_RGBA_sha256"] = "2" * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                tool.validate_result(damaged, config)


if __name__ == "__main__":
    unittest.main()
