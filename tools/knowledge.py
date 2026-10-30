"""Search and validate the Git-managed RUNEFALL knowledge catalog (stdlib only)."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "knowledge/entries.json"
KINDS = ("decision", "pitfall", "limitation", "workflow")
STATUSES = ("verified", "pending", "superseded")
REQUIRED = {"id", "kind", "status", "title", "summary", "tags", "checked_on", "context", "sources"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(nonempty(item) for item in value) and len(value) == len(set(value))


def validate_catalog(data, root=ROOT):
    """Return all schema/reference errors, without fetching remote URLs."""
    errors = []
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        return ["schema_version must be 1"]
    if set(data) != {"schema_version", "entries"}:
        errors.append("catalog fields must be schema_version and entries")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + ["entries must be a nonempty list"]
    ids = set()
    references = {}
    for index, entry in enumerate(entries):
        label = f"entry[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be an object")
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
            errors.append(f"{label}: invalid id")
        else:
            label = identifier
            if identifier in ids:
                errors.append(f"{label}: duplicate id")
            ids.add(identifier)
        if REQUIRED - entry.keys():
            errors.append(f"{label}: missing fields: {', '.join(sorted(REQUIRED - entry.keys()))}")
        if entry.keys() - REQUIRED - {"supersedes"}:
            errors.append(f"{label}: unknown fields")
        for field in ("title", "summary"):
            if not nonempty(entry.get(field)):
                errors.append(f"{label}: {field} must be nonempty text")
        if entry.get("kind") not in KINDS:
            errors.append(f"{label}: invalid kind")
        if entry.get("status") not in STATUSES:
            errors.append(f"{label}: invalid status")
        checked = entry.get("checked_on")
        try:
            if not isinstance(checked, str) or date.fromisoformat(checked).isoformat() != checked:
                raise ValueError()
        except ValueError:
            errors.append(f"{label}: checked_on must be a valid YYYY-MM-DD date")
        if not string_list(entry.get("tags")) or not entry["tags"]:
            errors.append(f"{label}: tags must be nonempty unique strings")
        context = entry.get("context")
        if not isinstance(context, dict) or not context or not all(nonempty(k) and nonempty(v) for k, v in context.items()):
            errors.append(f"{label}: context must map nonempty text keys to text values")
        sources = entry.get("sources")
        if not string_list(sources) or not sources:
            errors.append(f"{label}: sources must be nonempty unique strings")
        else:
            for source in sources:
                try:
                    url = urlsplit(source)
                    if url.scheme or url.netloc:
                        if url.scheme != "https" or not url.hostname or url.username or url.password:
                            errors.append(f"{label}: invalid HTTPS source: {source}")
                    else:
                        target = (root / url.path).resolve()
                        if not url.path or Path(url.path).is_absolute() or not target.is_relative_to(root.resolve()) or not target.is_file():
                            errors.append(f"{label}: missing or invalid local source: {source}")
                except ValueError:
                    errors.append(f"{label}: malformed source: {source}")
        supersedes = entry.get("supersedes", [])
        if not string_list(supersedes):
            errors.append(f"{label}: supersedes must be unique text IDs")
        elif isinstance(identifier, str):
            references[identifier] = supersedes
    for identifier, targets in references.items():
        for target in targets:
            if target == identifier or target not in ids:
                errors.append(f"{identifier}: invalid supersedes reference: {target}")
            elif next(entry for entry in entries if isinstance(entry, dict) and entry.get("id") == target).get("status") != "superseded":
                errors.append(f"{identifier}: superseded target must have status superseded: {target}")
    # Follow replacement links to catch loops, even if every referenced ID exists.
    def visit(identifier, visiting, visited):
        if identifier in visiting:
            errors.append(f"{identifier}: supersedes cycle")
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        for target in references.get(identifier, []):
            if target in references:
                visit(target, visiting, visited)
        visiting.remove(identifier)
        visited.add(identifier)

    visited = set()
    for identifier in references:
        visit(identifier, set(), visited)
    return errors


def load_catalog(path=CATALOG):
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_catalog(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data["entries"]


def search_entries(entries, queries=(), tags=(), status=None):
    terms = " ".join(queries).casefold().split()
    tags = {tag.casefold() for tag in tags}
    matches = []
    for entry in entries:
        if status is None and entry["status"] == "superseded":
            continue
        if status not in (None, "all") and entry["status"] != status:
            continue
        if not tags.issubset({tag.casefold() for tag in entry["tags"]}):
            continue
        text = json.dumps(entry, ensure_ascii=False).casefold()
        if all(term in text for term in terms):
            matches.append(entry)
    return sorted(matches, key=lambda entry: entry["id"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Search current knowledge (superseded entries hidden by default)")
    search.add_argument("query", nargs="*")
    search.add_argument("--tag", action="append", default=[])
    search.add_argument("--status", choices=(*STATUSES, "all"))
    search.add_argument("--json", action="store_true")
    show = commands.add_parser("show", help="Show a complete entry by stable ID")
    show.add_argument("id")
    commands.add_parser("check", help="Validate catalog structure and local references; does not fetch URLs")
    args = parser.parse_args(argv)
    try:
        entries = load_catalog()
    except (OSError, ValueError) as error:
        print(f"Knowledge validation failed: {error}", file=sys.stderr)
        return 1
    if args.command == "check":
        print(f"Knowledge OK: {len(entries)} entries; schema and local references valid (external URLs not fetched)")
    elif args.command == "show":
        entry = next((entry for entry in entries if entry["id"] == args.id), None)
        if entry is None:
            print(f"Unknown knowledge ID: {args.id}", file=sys.stderr)
            return 1
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        matches = search_entries(entries, args.query, args.tag, args.status)
        if args.json:
            print(json.dumps(matches, ensure_ascii=False, indent=2))
        elif not matches:
            print("No matching knowledge. Try related Korean/English keywords or --status all.")
        else:
            for entry in matches:
                print(f"{entry['id']} [{entry['status']}] {entry['title']}")
                print(f"  {entry['summary']}")
                print(f"  checked={entry['checked_on']} context={json.dumps(entry['context'], ensure_ascii=False)}")
                print(f"  sources: {', '.join(entry['sources'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
