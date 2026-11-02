"""Profile changes and interrupted imports must not reuse stale generated CTEX."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


class TextureImportCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "game"
        self.imported = self.project / ".godot/imported"
        self.imported.mkdir(parents=True)
        self.marker = self.project / ".godot" / build.TEXTURE_PROFILE_MARKER
        self.source = self.project / "project.godot"
        self.settings()

    def settings(self, method=2, factor=25):
        self.source.write_text(
            '[application]\nconfig/name="RUNEFALL"\n[rendering]\n'
            f'textures/webp_compression/compression_method={method}\n'
            f'textures/webp_compression/lossless_compression_factor={factor}\n', encoding="utf-8")
        return build.texture_import_profile(self.source)

    def texture(self, name="atlas.png", variant=""):
        stem = name + "-" + "a" * 32
        texture = self.imported / (stem + variant + ".ctex")
        digest = self.imported / (stem + ".md5")
        texture.write_bytes(b"generated GST2")
        digest.write_bytes(b"generated import fingerprint")
        return texture, digest

    def test_literal_parser_defaults_comments_and_rejects_code_or_duplicate(self):
        self.source.write_text('[rendering]\n; numeric defaults\n', encoding="utf-8")
        defaults = build.texture_import_profile(self.source)
        self.assertEqual(defaults, self.settings(2, "25.0 ; explicit equivalent"))
        for method, factor in [("int(6)", 25), (7, 25), (6, "nan"), (6, 101), (6, '"100"')]:
            with self.subTest(method=method, factor=factor), self.assertRaises(ValueError):
                self.settings(method, factor)
        self.settings()
        with self.source.open("a") as stream:
            stream.write("textures/webp_compression/compression_method=6\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build.texture_import_profile(self.source)

    def test_warm_unchanged_profile_does_not_touch_any_generated_file(self):
        profile = self.settings()
        texture, digest = self.texture()
        build.record_texture_import_profile(self.project, profile)
        before = {path: (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())
                  for path in (texture, digest, self.marker)}
        report = build.prepare_texture_import_cache(self.project, profile)
        self.assertEqual(report["reason"], "profile_unchanged")
        self.assertEqual(report["invalidated"], [])
        self.assertEqual(before, {path: (path.stat().st_ino, path.stat().st_mtime_ns, path.read_bytes())
                                  for path in before})

    def test_missing_marker_invalidates_only_generated_textures_and_paired_digests(self):
        texture, digest = self.texture(variant=".s3tc")
        preserved = [self.project / "atlas.png", self.project / "atlas.png.import",
                     self.imported / "model.scn", self.imported / "font.fontdata",
                     self.imported / "sound.md5", self.project / ".godot/editor/state.cfg"]
        for path in preserved:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"preserve this exact source/editor/nontexture content")
        report = build.prepare_texture_import_cache(self.project, self.settings())
        self.assertEqual(set(report["invalidated"]), {texture.name, digest.name})
        self.assertFalse(texture.exists())
        self.assertFalse(digest.exists())
        self.assertFalse(self.marker.exists())
        for path in preserved:
            self.assertEqual(path.read_bytes(), b"preserve this exact source/editor/nontexture content")

    def test_each_global_compression_setting_invalidates_previous_profile(self):
        for method, factor in [(6, 25), (2, 100)]:
            with self.subTest(method=method, factor=factor):
                build.record_texture_import_profile(self.project, self.settings())
                texture, digest = self.texture()
                report = build.prepare_texture_import_cache(self.project, self.settings(method, factor))
                self.assertEqual(report["reason"], "profile_changed")
                self.assertFalse(texture.exists() or digest.exists() or self.marker.exists())

    def test_profile_is_committed_only_after_successful_import(self):
        def successful_import(args, timeout):
            self.assertEqual(args, ["--editor", "--import"])
            self.assertEqual(timeout, 1200)
            self.assertFalse(self.marker.exists())
            self.texture()
        with patch.object(build, "ROOT", self.root), patch.object(build, "godot_run", side_effect=successful_import):
            build.import_project()
        self.assertEqual(json.loads(self.marker.read_text()), self.settings())

    def test_interrupted_import_cannot_trust_old_marker_after_settings_revert(self):
        old_profile = self.settings()
        build.record_texture_import_profile(self.project, old_profile)
        self.texture()
        self.settings(6, 100)
        def interrupted_import(_args, timeout):
            self.assertEqual(timeout, 1200)
            self.assertFalse(self.marker.exists())
            self.texture()
            raise SystemExit("synthetic import failure")
        with patch.object(build, "ROOT", self.root), patch.object(build, "godot_run", side_effect=interrupted_import):
            with self.assertRaises(SystemExit):
                build.import_project()
        self.assertFalse(self.marker.exists())
        report = build.prepare_texture_import_cache(self.project, self.settings())
        self.assertEqual(report["reason"], "missing_marker")
        self.assertEqual(len(report["invalidated"]), 2)

    def test_corrupt_marker_is_not_a_valid_warm_profile(self):
        self.marker.write_text("{truncated", encoding="utf-8")
        texture, _ = self.texture()
        self.assertEqual(build.prepare_texture_import_cache(self.project, self.settings())["reason"], "invalid_marker")
        self.assertFalse(texture.exists() or self.marker.exists())

    def test_external_cache_symlinks_rejected_before_any_deletion(self):
        texture, digest = self.texture()
        outside = self.root / "external.md5"
        outside.write_bytes(b"external content")
        digest.unlink()
        digest.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            build.prepare_texture_import_cache(self.project, self.settings())
        self.assertTrue(texture.exists())
        self.assertEqual(outside.read_bytes(), b"external content")
        digest.unlink()
        texture.unlink()
        self.imported.rmdir()
        external_directory = self.root / "external-cache"
        external_directory.mkdir()
        self.imported.symlink_to(external_directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            build.prepare_texture_import_cache(self.project, self.settings())

    def test_profile_marker_symlink_cannot_read_or_overwrite_external_file(self):
        outside = self.root / "external-profile.json"
        outside.write_text(json.dumps(self.settings()), encoding="utf-8")
        original = outside.read_bytes()
        self.marker.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            build.prepare_texture_import_cache(self.project, self.settings())
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            build.record_texture_import_profile(self.project, self.settings(6, 100))
        self.assertEqual(outside.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
