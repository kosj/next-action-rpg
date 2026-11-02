"""Small synthetic variable fonts; no project-font copies or engine invocation."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import derive_ui_font as tool


class DeriveFontTests(unittest.TestCase):
    def setUp(self):
        from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.ttLib.tables.TupleVariation import TupleVariation

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.ttf"
        self.output = self.root / "derived.ttf"
        self.license = self.root / "OFL.txt"
        self.license.write_text("Copyright Example, with Reserved Font Name 'Source'\n"
                                "SIL OPEN FONT LICENSE Version 1.1\n", encoding="utf-8")
        names = [".notdef", "A", "uniAC00", "f", "i", "fi"]
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder(names)
        glyphs = {}
        for name in names:
            pen = TTGlyphPen(None)
            pen.moveTo((0, 0))
            pen.lineTo((100, 700))
            pen.lineTo((200, 0))
            pen.closePath()
            glyphs[name] = pen.glyph()
        builder.setupGlyf(glyphs)
        builder.setupHorizontalMetrics({name: (500, 0) for name in names})
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        builder.setupCharacterMap({65: "A", 0xAC00: "uniAC00", 102: "f", 105: "i"})
        builder.setupNameTable({
            "familyName": "Source Test", "styleName": "Thin",
            "uniqueFontIdentifier": "SourceTest-1", "fullName": "Source Test Thin",
            "psName": "SourceTest-Thin", "version": "Version 1.000",
            "copyright": "Copyright Example, with Reserved Font Name 'Source'",
            "licenseDescription": "SIL Open Font License 1.1", "licenseInfoURL": "https://openfontlicense.org",
        })
        builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
        builder.setupPost()
        builder.setupMaxp()
        builder.setupFvar([("wght", 100, 100, 900, "Weight")], [])
        # Three contour points, then left/right horizontal and top/bottom vertical phantoms.
        variations = {name: [TupleVariation({"wght": (0, 1, 1)},
                       [(0, 0), (100, 0), (0, 0), (0, 0), (80, 0), (0, 0), (0, 0)])]
                      for name in names}
        builder.setupGvar(variations)
        addOpenTypeFeaturesFromString(builder.font, "languagesystem DFLT dflt; "
                                      "languagesystem latn dflt; "
                                      "feature liga { sub f i by fi; } liga; "
                                      "feature kern { pos A A -20; } kern;")
        builder.font.recalcTimestamp = False
        builder.save(self.source)
        self.original = self.source.read_bytes()

    def create(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return tool.main([str(self.source), str(self.output), "--license", str(self.license),
                              "--no-shaping", *extra])

    def test_complete_glyph_metrics_layout_and_license_preserved(self):
        from fontTools.ttLib import TTFont
        self.assertEqual(self.create(), 0)
        report = tool.audit_font(self.source, self.output, shaping=False)
        self.assertTrue(report["passed"])
        self.assertEqual(report["glyph_count"], 6)
        self.assertEqual(report["best_cmap_codepoints"], 4)
        self.assertEqual(report["source_at_weight_outline_audit"]["glyphs_drawn"], 6)
        self.assertEqual(report["source_at_weight_outline_audit"]["drawing_operation_mismatch_count"], 0)
        source = TTFont(self.source)
        derived = TTFont(self.output)
        self.assertEqual(derived.getGlyphOrder(), source.getGlyphOrder())
        self.assertEqual(derived.getBestCmap()[0xAC00], "uniAC00")
        self.assertIn("fi", derived.getGlyphOrder(), "An unencoded ligature must remain")
        self.assertNotEqual(derived["hmtx"]["A"], source["hmtx"]["A"])
        for name_id in (0, 13, 14):
            self.assertEqual([x.toUnicode() for x in source["name"].names if x.nameID == name_id],
                             [x.toUnicode() for x in derived["name"].names if x.nameID == name_id])
        for record in derived["name"].names:
            if record.nameID in (1, 4, 6):
                self.assertIn("RunefallKR430", record.toUnicode())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_existing_output_source_and_report_are_never_overwritten(self):
        report = self.root / "report.json"
        self.assertEqual(self.create("--report", str(report)), 0)
        original_output, original_report = self.output.read_bytes(), report.read_bytes()
        self.assertEqual(self.create(), 1)
        self.assertEqual(self.create("--check", "--report", str(report)), 1)
        self.assertEqual(self.output.read_bytes(), original_output)
        self.assertEqual(report.read_bytes(), original_report)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main([str(self.source), str(self.source),
                                       "--license", str(self.license)]), 1)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_wrong_weight_reserved_name_and_nonvariable_source_are_rejected(self):
        self.assertEqual(self.create("--weight", "99"), 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.create("--family", "SourceDerived"), 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.create(), 0)
        with self.assertRaisesRegex(ValueError, "wght"):
            tool._instantiate(self.output.read_bytes(), 430, "AnotherFamily")

    def test_malformed_font_is_rejected_before_creating_output(self):
        self.source.write_bytes(b"not a font")
        self.assertEqual(self.create(), 1)
        self.assertFalse(self.output.exists())

    def test_reproducible_check_detects_valid_glyph_and_layout_tampering(self):
        from fontTools.ttLib import TTFont
        self.assertEqual(self.create(), 0)
        self.assertEqual(self.create("--check"), 0)
        font = TTFont(self.output, recalcTimestamp=False)
        font["glyf"]["A"].coordinates[1] = (900, 700)
        font["GPOS"].table.LookupList.Lookup[0].SubTable[0].PairSet[0].PairValueRecord[0].Value1.XAdvance = -99
        font.save(self.output)
        report = tool.audit_font(self.source, self.output, shaping=False)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["official_complete_static_instance_byte_exact"])
        self.assertGreater(report["source_at_weight_outline_audit"]["maximum_unrounded_coordinate_delta_font_units"], 700)

    def test_system_shaping_compares_all_characters_and_real_ligature(self):
        # Dev/CI dependencies are required here; absence must fail, never turn
        # the complete-font regression suite into a silently skipped check.
        tool.HarfBuzz()
        self.assertEqual(self.create(), 0)
        report = tool.audit_font(self.source, self.output)
        shaping = report["source_at_weight_shaping_audit"]
        self.assertEqual(shaping["best_cmap_characters_individually_shaped"], 4)
        self.assertEqual(shaping["different_results"], 0)
        self.assertEqual(shaping["maximum_position_delta_font_units"], 0)


if __name__ == "__main__":
    unittest.main()
