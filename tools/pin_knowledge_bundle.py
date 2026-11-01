"""Pin portable knowledge provenance to an existing, explicit Git snapshot.

Dry-run by default. This updates provenance only; review the bundle's release
notes/version labels and regenerate/verify its ZIP separately. No URL is fetched.
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "reusable/game-production-kit/provenance.json"
CATALOG = "knowledge/entries.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="Existing full 40-character source commit")
    parser.add_argument("--version", required=True, help="New bundle version, independent of the game version")
    parser.add_argument("--prepared-on", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--write", action="store_true", help="Write the reviewed provenance; default only reports")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("--commit must be a full lowercase Git commit SHA")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("--version must be a numeric three-part version")
    date.fromisoformat(args.prepared_on)
    resolved = subprocess.check_output(
        ["git", "rev-parse", "--verify", args.commit + "^{commit}"], cwd=ROOT, text=True).strip()
    if resolved != args.commit:
        raise ValueError("Source must name the exact commit object")
    raw = subprocess.check_output(["git", "show", args.commit + ":" + CATALOG], cwd=ROOT)
    entries = json.loads(raw)["entries"]
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    repository = provenance["source_catalog"]["repository"].rstrip("/")
    provenance["bundle_version"] = args.version
    provenance["prepared_on"] = args.prepared_on
    provenance["source_catalog"] = {
        "repository": repository,
        "commit": args.commit,
        "catalog_url": repository + "/blob/" + args.commit + "/" + CATALOG,
        "catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "entry_count": len(entries),
        "entries": [{
            "id": entry["id"],
            "source_title": entry["title"],
            "source_status": entry["status"],
            "source_checked_on": entry["checked_on"],
            "source_context": entry["context"],
            "evidence_urls": [source if urlsplit(source).scheme else
                              repository + "/blob/" + args.commit + "/" + source
                              for source in entry["sources"]],
        } for entry in entries],
    }
    if args.write:
        PROVENANCE.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "provenance_written" if args.write else "dry_run_no_files_changed",
        "bundle_version": args.version,
        "commit": args.commit,
        "entry_count": len(entries),
        "catalog_sha256": provenance["source_catalog"]["catalog_sha256"],
        "catalog_matches_worktree": raw == (ROOT / CATALOG).read_bytes(),
        "remaining": ["review version labels and release notes", "package and independently verify ZIP"],
    }))


if __name__ == "__main__":
    main()
