"""Run the real browser reader against bounded Node IndexedDB event fixtures.

No Playwright import or npm dependencies are needed. The JavaScript function is
extracted with Python AST from browser_smoke.py, so fixtures cannot test a stale
copy of the reader. Real Chromium persistence remains an independent gate.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / "tools/browser_smoke.py"
FIXTURE = Path(__file__).with_name("browser_storage_fixture.cjs")


def reader_source():
    module = ast.parse(READER.read_text(encoding="utf-8"), filename=str(READER))
    values = [ast.literal_eval(node.value) for node in ast.walk(module)
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "read_persisted_saves"
                      for target in node.targets)]
    if len(values) != 1 or not isinstance(values[0], str):
        raise AssertionError("Expected one literal read_persisted_saves function in browser_smoke.py")
    return values[0]


def run_fixture(case="all", *, node=None):
    node = node or shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is needed for browser-storage fixtures; no npm installation is required")
    source = reader_source()
    with TemporaryDirectory(prefix="runefall-storage-reader-") as folder:
        path = Path(folder) / "reader.json"
        path.write_text(json.dumps(source), encoding="utf-8")
        result = subprocess.run([node, str(FIXTURE), str(path), case], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
    if result.returncode:
        raise AssertionError("Node browser-storage fixture failed:\n" + result.stderr + result.stdout)
    report = json.loads(result.stdout)
    report["reader_file"] = "tools/browser_smoke.py:read_persisted_saves"
    report["reader_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    report["fixture_file"] = "tools/tests/browser_storage_fixture.cjs"
    report["fixture_sha256"] = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    return report


class BrowserStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            if os.environ.get("CI"):
                raise RuntimeError("CI must provide Node.js for readonly browser-storage fixtures")
            raise unittest.SkipTest("Node.js is not installed locally; no browser/npm setup is required")

    def case(self, name):
        report = run_fixture(name, node=self.node)
        self.assertEqual(report["status"], "passed")
        self.assertEqual([item["id"] for item in report["cases"]], [name])

    def test_discovers_keys_without_reading_unrelated_file_values(self):
        self.case("discover_primary")

    def test_observed_primary_key_is_reused_for_direct_readonly_lookup(self):
        self.case("cached_lookup")

    def test_missing_store_is_closed_without_schema_creation(self):
        self.case("missing_store")

    def test_unexpected_upgrade_is_aborted_without_a_transaction(self):
        self.case("abort_upgrade")

    def test_malformed_primary_rejects_instead_of_appearing_valid(self):
        self.case("malformed_primary")


if __name__ == "__main__":
    if "--report" in sys.argv[1:]:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--report", type=Path, required=True)
        args = parser.parse_args()
        report = run_fixture()
        report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"READONLY_STORAGE_FIXTURE_OK {len(report['cases'])} cases; {args.report}")
    else:
        unittest.main()
