"""Protect knowledge lookup and reject malformed/stale local evidence references."""
from contextlib import redirect_stderr, redirect_stdout
import copy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import knowledge


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "evidence.md").write_text("verified locally", encoding="utf-8")
        self.entry = {
            "id": "save-backup", "kind": "pitfall", "status": "verified",
            "title": "저장 백업", "summary": "Save BACKUP recovery",
            "tags": ["save", "backup"], "checked_on": "2026-10-30",
            "context": {"godot": "4.7.2"}, "sources": ["evidence.md", "https://example.com/docs#save"]
        }

    def catalog(self, *entries):
        return {"schema_version": 1, "entries": list(entries or [self.entry])}

    def test_korean_casefolded_and_multi_term_lookup(self):
        entries = [self.entry]
        self.assertEqual(knowledge.search_entries(entries, ["저장"]), entries)
        self.assertEqual(knowledge.search_entries(entries, ["SAVE backup"]), entries)
        self.assertEqual(knowledge.search_entries(entries, ["save missing"]), [])
        self.assertEqual(knowledge.search_entries(entries, tags=["SAVE", "backup"]), entries)
        self.assertEqual(knowledge.search_entries(entries, tags=["web"]), [])

    def test_superseded_is_hidden_but_available_explicitly(self):
        self.entry["status"] = "superseded"
        self.assertEqual(knowledge.search_entries([self.entry]), [])
        self.assertEqual(knowledge.search_entries([self.entry], status="all"), [self.entry])
        self.assertEqual(knowledge.search_entries([self.entry], status="superseded"), [self.entry])

    def test_duplicate_and_broken_sources_are_rejected(self):
        self.assertTrue(any("duplicate id" in error for error in knowledge.validate_catalog(self.catalog(self.entry, copy.deepcopy(self.entry)), self.root)))
        for source in ("missing.md", "../outside.md", str(self.root / "evidence.md"), "http://example.com", "https://user:password@example.com"):
            with self.subTest(source=source):
                self.entry["sources"] = [source]
                self.assertTrue(knowledge.validate_catalog(self.catalog(), self.root))

    def test_invalid_field_types_and_dates_return_errors(self):
        for field, value in (("checked_on", "2026-02-30"), ("checked_on", "20261030"), ("status", "done"), ("context", {"godot": 4}), ("tags", ["save", []]), ("sources", [None]), ("title", "")):
            with self.subTest(field=field, value=value):
                entry = {**self.entry, field: value}
                self.assertTrue(knowledge.validate_catalog(self.catalog(entry), self.root))
        self.assertTrue(knowledge.validate_catalog({"schema_version": True, "entries": [self.entry]}, self.root))

    def test_replacement_must_point_to_retired_entry_without_cycle(self):
        replacement = {**self.entry, "id": "new-save", "supersedes": ["save-backup"]}
        self.assertTrue(knowledge.validate_catalog(self.catalog(self.entry, replacement), self.root))
        self.entry["status"] = "superseded"
        self.assertEqual(knowledge.validate_catalog(self.catalog(self.entry, replacement), self.root), [])
        self.entry["supersedes"] = ["absent"]
        self.assertTrue(knowledge.validate_catalog(self.catalog(self.entry, replacement), self.root))
        self.entry["supersedes"] = ["new-save"]
        self.assertTrue(any("cycle" in error for error in knowledge.validate_catalog(self.catalog(self.entry, replacement), self.root)))

    def test_valid_catalog_and_machine_readable_cli(self):
        self.assertEqual(knowledge.validate_catalog(self.catalog(), self.root), [])
        with patch.object(knowledge, "load_catalog", return_value=[self.entry]):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(knowledge.main(["search", "저장", "--json"]), 0)
            self.assertEqual(json.loads(output.getvalue()), [self.entry])
            with redirect_stderr(StringIO()):
                self.assertEqual(knowledge.main(["show", "unknown"]), 1)
        with patch.object(knowledge, "load_catalog", side_effect=ValueError("invalid catalog")), redirect_stderr(StringIO()):
            self.assertEqual(knowledge.main(["check"]), 1)


if __name__ == "__main__":
    unittest.main()
