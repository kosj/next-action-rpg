"""Exercise the portable knowledge kit's provenance and integrity gates (stdlib only).

The source catalog is read from a pinned local Git object. No network request,
engine, Blender, browser, target-project approval, or external freshness check is
part of this verification. All mutation probes use disposable copies in /tmp.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = "knowledge/entries.json"
CHECKS = [
    ("pinned-catalog-and-handbook", "Pinned source catalog, provenance and handbook coverage agree"),
    ("standalone-renamed-kit", "Extracted renamed kit checks and verifies source outside the repository"),
    ("same-runtime-repack", "Standalone repack in this Python/zlib runtime has identical archive bytes"),
    ("valid-crc-payload-tamper", "Changed same-length payload with valid CRC fails manifest SHA verification"),
    ("changed-source-old-archive", "Internally valid old ZIP is rejected after source content changes"),
    ("broken-local-link", "Broken local documentation link is rejected"),
    ("external-symlink", "Symlink to material outside the kit is rejected"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


class ProbeNotRun(ValueError):
    """A prerequisite failed before a disposable mutation probe could run."""


class Commands:
    def __init__(self, cwd, timeout):
        self.cwd = cwd
        self.timeout = timeout
        self.records = []

    def run(self, command, *, include_stdout=True):
        started = time.monotonic()
        record = {"argv": [str(arg) for arg in command], "cwd": str(self.cwd)}
        try:
            result = subprocess.run(
                record["argv"], cwd=self.cwd, capture_output=True,
                timeout=self.timeout, check=False,
            )
            stdout, stderr = result.stdout, result.stderr
            record.update(returncode=result.returncode, timed_out=False)
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            record.update(returncode=None, timed_out=True)
        except OSError as error:
            stdout, stderr = b"", str(error).encode("utf-8")
            record.update(returncode=None, timed_out=False, launch_error=type(error).__name__)
        record["duration_seconds"] = round(time.monotonic() - started, 6)
        for name, data in (("stdout", stdout), ("stderr", stderr)):
            record[name + "_bytes"] = len(data)
            record[name + "_sha256"] = sha(data)
            if name == "stdout" and not include_stdout:
                record[name + "_omitted"] = True
            else:
                record[name] = data[:8192].decode("utf-8", errors="replace")
                record[name + "_truncated"] = len(data) > 8192
        self.records.append(record)
        return record, stdout, stderr

    def package(self, kit, *arguments):
        # -I excludes the caller's PYTHONPATH, user site and script directory.
        # package.py imports only stdlib; its ROOT must come from its own path.
        return self.run([sys.executable, "-I", kit / "scripts/package.py", *arguments])


def expect_success(result):
    record, stdout, _ = result
    require(record["returncode"] == 0 and not record["timed_out"], "Command did not exit successfully")
    return json.loads(stdout)


def expect_rejection(result, message):
    record, stdout, stderr = result
    require(record["returncode"] not in (None, 0) and not record["timed_out"], "Expected a real nonzero rejection")
    require(message in (stdout + stderr).decode("utf-8", errors="replace"), "Rejected for an unexpected reason: " + message)


def check_catalog(repository, kit, provenance, commands):
    origin = provenance["source_catalog"]
    commit = origin["commit"]
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "Origin must pin a full Git commit")
    repository_url = origin["repository"].rstrip("/")
    parsed = urlsplit(repository_url)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
            "Origin repository must be a permanent HTTPS URL")
    expected_url = f"{repository_url}/blob/{commit}/{CATALOG_PATH}"
    require(origin["catalog_url"] == expected_url, "Catalog URL differs from pinned repository/path")
    result, catalog_bytes, _ = commands.run(
        ["git", "--no-replace-objects", "-C", repository, "show", f"{commit}:{CATALOG_PATH}"],
        include_stdout=False,
    )
    require(result["returncode"] == 0 and not result["timed_out"], "Pinned catalog is unavailable in local Git")
    require(sha(catalog_bytes) == origin["catalog_sha256"], "Pinned catalog SHA-256 differs from provenance")
    entries = json.loads(catalog_bytes)["entries"]
    source_ids = [entry["id"] for entry in entries]
    require(len(source_ids) == len(set(source_ids)), "Pinned source catalog has duplicate IDs")
    expected_entries = {}
    for entry in entries:
        evidence = []
        for source in entry["sources"]:
            url = urlsplit(source)
            if url.scheme or url.netloc:
                require(url.scheme == "https" and url.hostname and not url.username and not url.password,
                        "Invalid source evidence URL")
                evidence.append(source)
            else:
                path = PurePosixPath(url.path)
                require(url.path and not path.is_absolute() and ".." not in path.parts, "Invalid local source evidence path")
                evidence.append(f"{repository_url}/blob/{commit}/{source}")
        expected_entries[entry["id"]] = {
            "id": entry["id"], "source_title": entry["title"],
            "source_status": entry["status"], "source_checked_on": entry["checked_on"],
            "source_context": entry["context"], "evidence_urls": evidence,
        }
    observed = origin["entries"]
    require(len(observed) == len(entries) == origin["entry_count"], "Provenance entry count differs from pinned catalog")
    require(len({entry["id"] for entry in observed}) == len(observed), "Provenance has duplicate source IDs")
    require({entry["id"]: entry for entry in observed} == expected_entries,
            "Provenance IDs/title/status/date/context/evidence differ from pinned catalog")
    handbook = (kit / "HANDBOOK.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*((?:`[^`]+`(?:,?\s*)?)+)\s*\|", handbook, re.M)
    covered = {identifier for row in rows for identifier in re.findall(r"`([^`]+)`", row)}
    require(covered == set(source_ids), "Handbook source-ID table coverage differs from pinned catalog")
    return {
        "commit": commit, "catalog_path": CATALOG_PATH, "catalog_bytes": len(catalog_bytes),
        "catalog_sha256": sha(catalog_bytes), "source_entries": len(entries),
        "handbook_covered_ids": len(covered), "evidence_urls": sum(len(entry["sources"]) for entry in entries),
        "source_status_counts": dict(sorted(Counter(entry["status"] for entry in entries).items())),
        "matched_fields": ["id", "title", "status", "checked_on", "context", "sources"],
        "external_url_freshness_checked": False,
    }


def extract_renamed(archive_path, temporary):
    extraction = temporary / "archive-unpacked"
    extraction.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.testzip() is None, "Cannot extract ZIP with invalid CRC")
        names = archive.namelist()
        require(len(names) == len(set(names)), "Cannot extract duplicate ZIP paths")
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and ".." not in path.parts and path.parts,
                    "Unsafe ZIP extraction path")
            require(not stat.S_ISLNK(info.external_attr >> 16), "Cannot extract symlink ZIP entry")
        roots = {PurePosixPath(name).parts[0] for name in names}
        require(len(roots) == 1, "Expected one ZIP root folder")
        archive.extractall(extraction)
    extracted = extraction / roots.pop()
    renamed = temporary / "renamed-consumer-bundle"
    extracted.rename(renamed)
    require(not (renamed / ".git").exists(), "Extracted bundle unexpectedly contains repository metadata")
    return renamed


def copy_kit(kit, destination):
    shutil.copytree(kit, destination, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
    return destination


def verify(args, report):
    repository = args.repository.resolve(strict=True)
    kit = args.kit.resolve(strict=True)
    archive = args.archive.resolve(strict=True)
    require(not args.report.resolve().is_relative_to(kit), "Write the report outside the kit")
    provenance = json.loads((kit / "provenance.json").read_text(encoding="utf-8"))
    archive_bytes = archive.read_bytes()
    report.update(
        bundle_version=provenance["bundle_version"], source_kit=str(kit), archive=str(archive),
        zip_bytes=len(archive_bytes), zip_sha256=sha(archive_bytes),
        package_script_sha256=sha((kit / "scripts/package.py").read_bytes()),
        provenance_sha256=sha((kit / "provenance.json").read_bytes()),
    )
    with tempfile.TemporaryDirectory(prefix="portable-knowledge-check-", dir="/tmp") as temporary_name:
        temporary = Path(temporary_name).resolve()
        require(not temporary.is_relative_to(repository) and not temporary.is_relative_to(kit),
                "Independent verification directory must be outside source repository and kit")
        unrelated = temporary / "unrelated-working-directory"
        unrelated.mkdir()
        commands = Commands(unrelated, args.timeout)
        state = {}

        def run_check(index, function):
            identifier, name = CHECKS[index]
            start = len(commands.records)
            check = {"id": identifier, "name": name}
            try:
                check["details"] = function()
                check["status"] = "passed"
            except ProbeNotRun as error:
                check.update(status="skipped", reason=str(error))
            except Exception as error:
                check.update(status="failed", error_type=type(error).__name__, error=str(error))
            check["commands"] = commands.records[start:]
            report["checks"].append(check)

        def catalog():
            details = check_catalog(repository, kit, provenance, commands)
            report["source_entries"] = details["source_entries"]
            return details

        def standalone():
            source = expect_success(commands.package(kit, "--check"))
            report.update(skills=source["skills"], source_files=source["files"])
            expect_success(commands.package(kit, "--verify-source", archive))
            expect_success(commands.package(kit, "--verify", archive))
            isolated = extract_renamed(archive, temporary)
            state["isolated"] = isolated
            checked = expect_success(commands.package(isolated, "--check"))
            expect_success(commands.package(isolated, "--verify", archive))
            expect_success(commands.package(isolated, "--verify-source", archive))
            return {"renamed_root": str(isolated), "cwd": str(unrelated),
                    "outside_repository": True, "python_isolated_mode": True, "extracted_check": checked}

        def isolated_kit():
            if "isolated" not in state:
                raise ProbeNotRun("Standalone archive prerequisites did not pass; probe not executed")
            return state["isolated"]

        def repack():
            output = temporary / "same-runtime-repacked.zip"
            packaged = expect_success(commands.package(isolated_kit(), "--output", output))
            expect_success(commands.package(isolated_kit(), "--verify-source", output))
            equal = output.read_bytes() == archive_bytes
            require(equal, "Same-runtime repack archive bytes differ from distributed ZIP")
            return {"original_sha256": sha(archive_bytes), "repacked_sha256": packaged["sha256"],
                    "repacked_bytes": output.stat().st_size, "archive_bytes_equal": equal}

        def tamper():
            isolated = isolated_kit()
            changed = temporary / "valid-crc-changed-payload.zip"
            with zipfile.ZipFile(archive) as original:
                payload_name = next(name for name in original.namelist() if name.endswith("/README.md"))
                before = original.read(payload_name)
                require(before, "Tamper probe needs a nonempty payload")
                after = bytes([before[0] ^ 1]) + before[1:]
                manifest_name = payload_name.split("/", 1)[0] + "/MANIFEST.json"
                original_manifest = original.read(manifest_name)
                with zipfile.ZipFile(changed, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as output:
                    for info in original.infolist():
                        output.writestr(info, after if info.filename == payload_name else original.read(info), compresslevel=9)
            with zipfile.ZipFile(changed) as probe:
                crc_valid = probe.testzip() is None
                require(crc_valid and probe.read(manifest_name) == original_manifest, "Tamper probe must preserve manifest and valid CRC")
                require(len(before) == len(probe.read(payload_name)) and sha(before) != sha(probe.read(payload_name)),
                        "Tamper probe must change SHA without changing payload length")
            expect_rejection(commands.package(isolated, "--verify", changed), "Manifest bytes/hash differ:")
            return {"payload": payload_name, "payload_bytes": len(before), "before_sha256": sha(before),
                    "after_sha256": sha(after), "valid_crc": crc_valid, "manifest_unchanged": True}

        def changed_source():
            isolated = isolated_kit()
            changed = copy_kit(isolated, temporary / "changed-source-consumer")
            document = changed / "README.md"
            before = document.read_bytes()
            document.write_bytes(before + b"\nPortable source-change integrity probe.\n")
            expect_success(commands.package(changed, "--check"))
            expect_success(commands.package(changed, "--verify", archive))
            expect_rejection(commands.package(changed, "--verify-source", archive), "Distributed ZIP differs from current source files")
            return {"changed_file": "README.md", "before_sha256": sha(before), "after_sha256": sha(document.read_bytes()),
                    "source_still_structurally_valid": True, "old_archive_still_internally_valid": True}

        def broken_link():
            changed = copy_kit(isolated_kit(), temporary / "broken-link-consumer")
            target = changed / "portable-missing-probe.md"
            require(not target.exists(), "Broken-link probe target unexpectedly exists")
            document = changed / "README.md"
            document.write_bytes(document.read_bytes() + b"\n[Missing portability probe](portable-missing-probe.md)\n")
            expect_rejection(commands.package(changed, "--check"), "Missing/outside portable local link:")
            return {"changed_file": "README.md", "missing_local_target": target.name}

        def symlink():
            changed = copy_kit(isolated_kit(), temporary / "symlink-consumer")
            outside = temporary / "outside-material.md"
            outside.write_text("Outside the consumer kit.\n", encoding="utf-8")
            link = changed / "skills/generated-3d-game-art/references/outside-probe.md"
            link.symlink_to(outside)
            require(link.is_symlink() and not link.resolve().is_relative_to(changed), "Probe must link outside kit")
            expect_rejection(commands.package(changed, "--check"), "Package source must not contain symlinks:")
            return {"link": link.relative_to(changed).as_posix(), "target_outside_kit": True}

        for index, function in enumerate((catalog, standalone, repack, tamper, changed_source, broken_link, symlink)):
            run_check(index, function)
        report["subprocess_count"] = len(commands.records)
        report["ephemeral_workspace"] = str(temporary)
    report["ephemeral_workspace_removed"] = not Path(temporary_name).exists()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Write actual verification evidence JSON outside the kit")
    parser.add_argument("--repository", type=Path, default=ROOT, help="Local repository containing the pinned catalog Git object")
    parser.add_argument("--kit", type=Path, default=ROOT / "reusable/game-production-kit")
    parser.add_argument("--archive", type=Path, default=ROOT / "reusable/game-production-kit.zip")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-subprocess limit in seconds (maximum 60)")
    args = parser.parse_args()
    if not 0 < args.timeout <= 60:
        parser.error("--timeout must be positive and no greater than 60 seconds")
    if args.report.resolve().is_relative_to(args.kit.resolve()) or args.report.resolve() == args.archive.resolve():
        parser.error("Write --report outside the kit and separately from the archive")
    report = {
        "scope": "Pinned local catalog/provenance, standalone packaging and integrity; no target-project runtime, art approval or external URL freshness",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "verification_tool_sha256": sha(Path(__file__).read_bytes()),
        "packaging_environment": {"python": platform.python_version(), "python_executable": sys.executable,
                                  "zlib": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION},
        "per_subprocess_timeout_seconds": args.timeout,
        "target_project_validation": "pending", "external_url_freshness_checked": False,
        "checks": [],
    }
    try:
        verify(args, report)
    except Exception as error:
        report["setup_error"] = {"type": type(error).__name__, "message": str(error)}
    ran = {check["id"] for check in report["checks"]}
    for identifier, name in CHECKS:
        if identifier not in ran:
            report["checks"].append({"id": identifier, "name": name, "status": "skipped", "reason": "Verification setup did not complete", "commands": []})
    counts = Counter(check["status"] for check in report["checks"])
    report["check_counts"] = {name: counts[name] for name in ("passed", "failed", "skipped")}
    report["status"] = "passed" if counts["passed"] == len(CHECKS) and not report.get("setup_error") else "failed"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["check_counts"], "report": str(args.report)}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
