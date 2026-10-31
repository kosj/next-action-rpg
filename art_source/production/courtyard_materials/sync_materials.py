#!/usr/bin/env python3
"""Verify pinned public CC0 maps; optionally restore missing files from source."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Restore missing pinned maps."
    )
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    root = source.parents[2]
    manifest = json.loads((source / "manifest.json").read_text())
    assert manifest["license"] == "CC0-1.0"
    total = 0
    for material in manifest["sets"]:
        assert (root / material["material"]).is_file(), material["material"]
        for image in material["maps"]:
            path = root / image["path"]
            assert path.resolve().is_relative_to(
                (root / "game/assets/materials/courtyard").resolve()
            ), image["path"]
            if not path.exists() and args.download:
                url = image["url"]
                assert url.startswith(
                    "https://dl.polyhaven.org/file/ph-assets/Textures/"
                ), url
                request = urllib.request.Request(
                    url, headers={"User-Agent": "RUNEFALL CC0 material restoration"}
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read()
                assert len(data) == image["size"], image["path"]
                assert hashlib.sha256(data).hexdigest() == image["sha256"], image["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
                    temp.write(data)
                    temporary_path = Path(temp.name)
                temporary_path.replace(path)
            if not path.exists():
                raise SystemExit(f"Missing {image['path']}; rerun with --download.")
            data = path.read_bytes()
            assert len(data) == image["size"], image["path"]
            assert hashlib.sha256(data).hexdigest() == image["sha256"], image["path"]
            assert hashlib.md5(data).hexdigest() == image["md5"], image["path"]
            policy = Path(str(path) + ".import").read_text()
            assert "mipmaps/generate=true" in policy, image["path"]
            assert "detect_3d/compress_to=0" in policy, image["path"]
            if image["channel"] == "nor_gl":
                assert "compress/normal_map=1" in policy, image["path"]
                assert "process/normal_map_invert_y=false" in policy, image["path"]
            total += len(data)
    assert total == manifest["runtime_texture_bytes"]
    assert total <= manifest["runtime_texture_budget_bytes"]
    print(f"Verified 9 pinned CC0 textures: {total:,} bytes / 10,000,000-byte budget.")


if __name__ == "__main__":
    main()
