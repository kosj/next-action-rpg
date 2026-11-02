"""Derive a complete, renamed static UI font with the official FontTools instancer.

Requires fonttools (production audit: 4.61.1). No glyph subsetting, contour
simplification, overlap removal, font download, or engine invocation occurs.
``SOURCE OUTPUT --license OFL.txt --report report.json`` creates NEW files only;
``--check`` audits an existing output. Existing source/outputs are never replaced.
Reports distinguish official integer-outline instancing from floating variable
outlines, and from still-pending Godot raster/import/export verification.

Optional system libharfbuzz checks every best-cmap character separately and a
small multilingual/ligature corpus. These are shaping checks, not raster checks
or exhaustive testing of every possible script/feature combination.
"""

from __future__ import annotations

import argparse
import ctypes as C
import ctypes.util
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

try:
    import fontTools
    from fontTools.misc.roundTools import otRound
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.ttLib import TTFont, TTLibError
    from fontTools.varLib.instancer import OverlapMode, instantiateVariableFont
except ImportError:
    fontTools = None
    TTLibError = ValueError


VARIABLE_TABLES = ("fvar", "gvar", "HVAR", "VVAR", "MVAR", "avar", "cvar")
PROBES = (
    "RUNEFALL AV ffi office 0123456789",
    "룬폴 전투 대기 약공격 강공격 회피 설정 계속하기",
    "룬폴 각 한글",
    "日本語 ひらがな カタカナ", "中文一二三天地人",
    "A\u0301 o\u0308 a\u030a", "Ελληνικά Кириллица",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cmap(font):
    """Retain every cmap subtable, including variation-selector mappings."""
    return [
        (table.platformID, table.platEncID, table.language, table.format,
         dict(getattr(table, "cmap", {})), dict(getattr(table, "uvsDict", {})))
        for table in font["cmap"].tables
    ]


def _layout_coverage(font, tag):
    if tag not in font:
        return None
    table = font[tag].table
    scripts = []
    for record in getattr(table.ScriptList, "ScriptRecord", []):
        script = record.Script
        languages = [("default", script.DefaultLangSys)] if script.DefaultLangSys else []
        languages += [(x.LangSysTag, x.LangSys) for x in script.LangSysRecord]
        scripts.append((record.ScriptTag, [
            (language, system.ReqFeatureIndex, tuple(system.FeatureIndex))
            for language, system in languages
        ]))
    # Lookup indices are implementation references, not language coverage. The
    # official instancer resolves VariationIndex devices and prunes/renumbers
    # GPOS lookups. Candidate byte equality to that complete official instance
    # separately checks the actual resolved lookup data.
    features = [record.FeatureTag
                for record in getattr(table.FeatureList, "FeatureRecord", [])]
    return scripts, features


def _instantiate(raw: bytes, weight: float, family: str):
    if fontTools is None:
        raise ValueError("Install fonttools to derive/audit fonts (production used 4.61.1)")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,31}", family):
        raise ValueError("Family must be a short ASCII alphanumeric name")
    source = TTFont(io.BytesIO(raw), recalcTimestamp=False)
    axes = source["fvar"].axes if "fvar" in source else []
    if len(axes) != 1 or axes[0].axisTag != "wght":
        raise ValueError("Only a source with exactly the wght variable axis is supported")
    axis = axes[0]
    if not math.isfinite(weight) or not axis.minValue <= weight <= axis.maxValue:
        raise ValueError("Weight must be finite and within the source wght axis")
    notices = [record.toUnicode() for record in source["name"].names if record.nameID == 0]
    reserved = re.findall(r"Reserved Font Name\s+['\"]([^'\"]+)['\"]", "\n".join(notices), re.I)
    if any(name.casefold() in family.casefold() for name in reserved):
        raise ValueError("Derivative family uses a source Reserved Font Name")
    static = instantiateVariableFont(
        source, {"wght": weight}, inplace=False, optimize=True,
        overlap=OverlapMode.KEEP_AND_DONT_SET_FLAGS,
        updateFontNames=False, static=True,
    )
    replacements = {
        1: family, 2: "Regular", 3: f"{family}-Static{weight:g}-{digest(raw)[:12]}",
        4: f"{family} Regular", 6: f"{family}-Regular", 16: family,
        17: "Regular", 18: f"{family} Regular", 21: family,
        22: "Regular", 25: family,
    }
    for record in static["name"].names:
        if record.nameID in replacements:
            record.string = replacements[record.nameID].encode(record.getEncoding())
    static.recalcTimestamp = False
    output = io.BytesIO()
    static.save(output, reorderTables=False)
    return source, output.getvalue(), reserved


def _outline_audit(source, derived, weight):
    original = source.getGlyphSet(location={"wght": weight})
    candidate = derived.getGlyphSet()
    maximum = advance = 0.0
    rounded_differences = 0
    mismatches = []
    for name in source.getGlyphOrder():
        a = DecomposingRecordingPen(original)
        b = DecomposingRecordingPen(candidate)
        original[name].draw(a)
        candidate[name].draw(b)
        if len(a.value) != len(b.value) or any(
                x[0] != y[0] or len(x[1]) != len(y[1]) for x, y in zip(a.value, b.value)):
            mismatches.append(name)
            continue
        rounded_different = False
        for x, y in zip(a.value, b.value):
            for p, q in zip(x[1], y[1]):
                if p is None or q is None:
                    if p != q:
                        mismatches.append(name)
                    continue
                maximum = max(maximum, abs(p[0] - q[0]), abs(p[1] - q[1]))
                rounded_different |= tuple(map(otRound, p)) != tuple(map(otRound, q))
        rounded_differences += int(rounded_different)
        advance = max(advance, abs(original[name].width - candidate[name].width))
    return {
        "glyphs_drawn": len(source.getGlyphOrder()),
        "drawing_operation_mismatch_count": len(mismatches),
        "first_drawing_operation_mismatches": mismatches[:20],
        "maximum_unrounded_coordinate_delta_font_units": maximum,
        "maximum_unrounded_advance_delta_font_units": advance,
        "glyphs_different_from_naive_otRound": rounded_differences,
        "scope": "All glyphs, decomposed contours. Variable floating coordinates vs "
                 "official fixed-point/integer static outlines; raw coordinates need not be exact.",
    }


class HarfBuzz:
    """Small readonly binding to the installed library; no downloaded dependency."""

    class Variation(C.Structure):
        _fields_ = [("tag", C.c_uint32), ("value", C.c_float)]

    class Info(C.Structure):
        _fields_ = [("gid", C.c_uint32), ("mask", C.c_uint32),
                    ("cluster", C.c_uint32), ("v1", C.c_uint32), ("v2", C.c_uint32)]

    class Position(C.Structure):
        _fields_ = [("xa", C.c_int32), ("ya", C.c_int32),
                    ("xo", C.c_int32), ("yo", C.c_int32), ("v", C.c_uint32)]

    def __init__(self):
        library = ctypes.util.find_library("harfbuzz")
        if not library:
            raise OSError("system libharfbuzz not available")
        self.lib = C.CDLL(library)
        p, u, i = C.c_void_p, C.c_uint, C.c_int
        signatures = {
            "hb_version_string": (C.c_char_p,),
            "hb_blob_create": (p, C.c_char_p, u, i, p, p),
            "hb_face_create": (p, p, u), "hb_font_create": (p, p),
            "hb_ot_font_set_funcs": (None, p), "hb_face_get_upem": (u, p),
            "hb_font_set_scale": (None, p, i, i),
            "hb_font_set_variations": (None, p, C.POINTER(self.Variation), u),
            "hb_buffer_create": (p,),
            "hb_buffer_add_utf8": (None, p, C.c_char_p, i, u, i),
            "hb_buffer_guess_segment_properties": (None, p),
            "hb_shape": (None, p, p, p, u),
            "hb_buffer_get_glyph_infos": (C.POINTER(self.Info), p, C.POINTER(u)),
            "hb_buffer_get_glyph_positions": (C.POINTER(self.Position), p, C.POINTER(u)),
        }
        for kind in ("blob", "face", "font", "buffer"):
            signatures[f"hb_{kind}_destroy"] = (None, p)
        for name, signature in signatures.items():
            function = getattr(self.lib, name)
            function.restype, function.argtypes = signature[0], list(signature[1:])

    def font(self, raw, weight=None):
        # DUPLICATE=0 makes the blob own a copy after this Python call returns.
        blob = self.lib.hb_blob_create(raw, len(raw), 0, None, None)
        face = self.lib.hb_face_create(blob, 0)
        font = self.lib.hb_font_create(face)
        self.lib.hb_ot_font_set_funcs(font)
        upem = self.lib.hb_face_get_upem(face)
        self.lib.hb_font_set_scale(font, upem, upem)
        if weight is not None:
            values = (self.Variation * 1)(self.Variation(int.from_bytes(b"wght", "big"), weight))
            self.lib.hb_font_set_variations(font, values, 1)
        self.lib.hb_face_destroy(face)
        self.lib.hb_blob_destroy(blob)
        return font

    def shape(self, font, text):
        raw = text.encode("utf-8")
        buffer = self.lib.hb_buffer_create()
        try:
            self.lib.hb_buffer_add_utf8(buffer, raw, len(raw), 0, len(raw))
            self.lib.hb_buffer_guess_segment_properties(buffer)
            self.lib.hb_shape(font, buffer, None, 0)
            count = C.c_uint()
            info = self.lib.hb_buffer_get_glyph_infos(buffer, C.byref(count))
            positions = self.lib.hb_buffer_get_glyph_positions(buffer, C.byref(count))
            return [(info[n].gid, info[n].cluster, positions[n].xa, positions[n].ya,
                     positions[n].xo, positions[n].yo) for n in range(count.value)]
        finally:
            self.lib.hb_buffer_destroy(buffer)


def _shaping_audit(source_bytes, derived_bytes, cmap, weight):
    try:
        hb = HarfBuzz()
    except OSError as error:
        return {"status": "unavailable", "reason": str(error)}
    source, derived = hb.font(source_bytes, weight), hb.font(derived_bytes)
    try:
        differences = []
        maximum = 0
        count = 0
        for label, text in [(f"U+{code:04X}", chr(code)) for code in sorted(cmap)] + [
                (f"probe:{number}", text) for number, text in enumerate(PROBES)]:
            a, b = hb.shape(source, text), hb.shape(derived, text)
            count += 1
            if a != b:
                differences.append(label)
            if len(a) == len(b):
                maximum = max(maximum, max((abs(x - y) for p, q in zip(a, b)
                                           for x, y in zip(p[2:], q[2:])), default=0))
        return {
            "status": "complete", "harfbuzz_version": hb.lib.hb_version_string().decode("ascii"),
            "best_cmap_characters_individually_shaped": len(cmap),
            "additional_multilingual_ligature_probes": len(PROBES),
            "comparisons": count, "different_results": len(differences),
            "first_different_results": differences[:20],
            "maximum_position_delta_font_units": maximum,
            "scope": "Glyph IDs, UTF8 clusters, advances and offsets at UPEM scale. "
                     "Default shaping features; not every script/language/feature combination or pixels.",
        }
    finally:
        hb.lib.hb_font_destroy(source)
        hb.lib.hb_font_destroy(derived)


def audit_font(source_path: Path, derived_path: Path, weight=430.0, family="RunefallKR430",
               *, shaping=True):
    raw, candidate = source_path.read_bytes(), derived_path.read_bytes()
    source, expected, reserved = _instantiate(raw, weight, family)
    derived = TTFont(io.BytesIO(candidate), recalcTimestamp=False)
    exact = candidate == expected
    checks = {
        "official_complete_static_instance_byte_exact": exact,
        "glyph_order_exact": source.getGlyphOrder() == derived.getGlyphOrder(),
        "all_cmap_subtables_exact": _cmap(source) == _cmap(derived),
        "GSUB_script_language_feature_coverage_exact": _layout_coverage(source, "GSUB") == _layout_coverage(derived, "GSUB"),
        "GPOS_script_language_feature_coverage_exact": _layout_coverage(source, "GPOS") == _layout_coverage(derived, "GPOS"),
        "no_remaining_variable_tables": not any(tag in derived for tag in VARIABLE_TABLES),
        "source_file_unchanged": source_path.read_bytes() == raw,
        "copyright_and_license_name_records_exact": [
            (x.nameID, x.platformID, x.platEncID, x.langID, x.toUnicode())
            for x in source["name"].names if x.nameID in (0, 13, 14)
        ] == [
            (x.nameID, x.platformID, x.platEncID, x.langID, x.toUnicode())
            for x in derived["name"].names if x.nameID in (0, 13, 14)
        ],
    }
    return {
        "schema": 1, "status": "verified_static_derivation_engine_raster_pending" if all(checks.values()) else "failed",
        "passed": all(checks.values()), "fonttools_version": fontTools.__version__,
        "source": {"path": source_path.as_posix(), "bytes": len(raw), "sha256": digest(raw)},
        "derived": {"path": derived_path.as_posix(), "bytes": len(candidate), "sha256": digest(candidate)},
        "raw_ttf_bytes_saved": len(raw) - len(candidate), "weight": weight, "family": family,
        "reserved_font_names": reserved, "checks": checks,
        "glyph_count": len(source.getGlyphOrder()), "best_cmap_codepoints": len(source.getBestCmap()),
        "layout_tables": {
            tag: {
                "source_lookup_count": source[tag].table.LookupList.LookupCount if tag in source else 0,
                "derived_lookup_count": derived[tag].table.LookupList.LookupCount if tag in derived else 0,
                "note": "Official instancing may resolve variable positioning and renumber lookups; "
                        "script/language/feature coverage is checked separately from lookup indices.",
            } for tag in ("GSUB", "GPOS")
        },
        "source_at_weight_outline_audit": _outline_audit(source, derived, weight),
        "source_at_weight_shaping_audit": _shaping_audit(raw, candidate, source.getBestCmap(), weight) if shaping else {"status": "not_requested"},
        "pending": ["Godot same-driver original FontVariation430 vs derived raster A/B",
                    "Actual Godot import and Web/Windows export byte measurements",
                    "Runtime UI/browser regressions after integration"],
        "scope": "Complete official static instancing and naming only. No glyph/character subsetting, "
                 "contour simplification or overlap removal. Raw TTF bytes are not PCK/export bytes.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--weight", type=float, default=430.0)
    parser.add_argument("--family", default="RunefallKR430")
    parser.add_argument("--license", type=Path, required=True, dest="license_path")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check", action="store_true", help="Audit existing output without writing it")
    parser.add_argument("--no-shaping", action="store_true", help="Explicitly omit optional system-HarfBuzz checks")
    args = parser.parse_args(argv)
    try:
        if args.source.resolve() == args.output.resolve():
            raise ValueError("Source and output must be different files")
        if args.report and (args.report.exists() or args.report.is_symlink()):
            raise ValueError("Report already exists; choose a new report path")
        license_raw = args.license_path.read_bytes()
        if b"SIL OPEN FONT LICENSE Version 1.1" not in license_raw:
            raise ValueError("The original SIL OFL1.1 license file is required")
        if not args.check:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("Output already exists; use --check or choose a new output")
            _, candidate, _ = _instantiate(args.source.read_bytes(), args.weight, args.family)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as file:
                file.write(candidate)
        report = audit_font(args.source, args.output, args.weight, args.family, shaping=not args.no_shaping)
        report["license"] = {"path": args.license_path.as_posix(), "sha256": digest(license_raw),
                             "license": "SIL Open Font License 1.1; original copyright and reserved name notice retained"}
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as file:
                file.write(encoded)
        print(encoded, end="")
        return 0 if report["passed"] else 1
    except (OSError, ValueError, KeyError, TTLibError) as error:
        print(json.dumps({"passed": False, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
