"""Validate comparison strictness without launching Godot or a display server."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_ui_font_review as tool


class FontReviewTests(unittest.TestCase):
    def test_nested_layout_has_no_hidden_numeric_tolerance(self):
        a = {"glyphs": [{"advance": 12.0, "index": 65}], "lines": 2}
        b = {"glyphs": [{"advance": 12.015625, "index": 65}], "lines": 2}
        result = tool.compare_values(a, b)
        self.assertEqual(result["different_fields"], 1)
        self.assertEqual(result["maximum_numeric_delta"], .015625)
        self.assertEqual(result["first_differences"][0]["path"], ".glyphs[0].advance")
        self.assertEqual(tool.compare_values(a, a)["different_fields"], 0)

    def test_existing_output_is_rejected_before_copying_or_launching(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root)
            with self.assertRaisesRegex(ValueError, "new, nonexistent"):
                tool.prepare(output)
            self.assertEqual(list(output.iterdir()), [])

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_pixel_comparison_reports_one_channel_delta_without_masking(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / "a.png", Path(root) / "b.png"
            image = Image.new("RGB", (3, 2), (20, 30, 40))
            image.save(a)
            image.putpixel((1, 0), (20, 31, 40))
            image.save(b)
            report = tool.pixel_difference(a, b)
            self.assertFalse(report["pixel_exact"])
            self.assertEqual(report["changed_pixels"], 1)
            self.assertEqual(report["maximum_channel_delta_0_255"], 1)
            self.assertEqual(report["mean_absolute_channel_delta_0_255"], 1 / 18)
            self.assertEqual(report["difference_bbox_xyxy"], (1, 0, 2, 1))
            self.assertTrue(tool.pixel_difference(a, a)["pixel_exact"])


if __name__ == "__main__":
    unittest.main()
