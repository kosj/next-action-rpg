"""Check planned art inputs, reference integrity, and literal AttackData contracts.

This does not connect to VARCO, edit images, decode image quality, validate a rig,
or approve runtime art. It accepts plain finite numeric source literals only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = Path("art_source/production")
REFERENCE_ROOT = PRODUCTION / "references"
EXPECTED_ASSETS = {"lyra_body", "sentinel_melee", "pilgrim_courtyard"}
EXPECTED_CLIPS = {"idle", "walk", "run", "dodge", "light_1", "light_2", "light_3", "parry", "hit"}
ATTACK_FIELDS = {"damage", "poise", "startup", "active", "recovery", "reach", "arc", "lunge"}
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def same_number(actual, expected):
    return finite_number(actual) and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9)


def numeric_literal(expression, label):
    # Godot permits other expressions; this checker deliberately does not evaluate them.
    expression = expression.split("#", 1)[0].strip()
    if not NUMBER.fullmatch(expression):
        raise ValueError(f"{label}: unsupported numeric expression {expression!r}; use a plain finite literal or update this checker explicitly")
    value = float(expression)
    if not math.isfinite(value):
        raise ValueError(f"{label}: numeric literal must be finite")
    return value


def parse_attack_defaults(path):
    """Read one-line '@export var <field>: float = <literal>' declarations."""
    values = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"\s*@export\s+var\s+", line):
            continue
        declaration = re.match(r"\s*@export\s+var\s+(\w+)(.*)", line)
        field = declaration.group(1)
        if field not in ATTACK_FIELDS:
            continue
        match = re.fullmatch(r"\s*:\s*float\s*=\s*(.+)", declaration.group(2))
        if match is None:
            raise ValueError(f"{path.name}:{line_number}: {field} must use a one-line exported float literal")
        if field in values:
            raise ValueError(f"{path.name}:{line_number}: duplicate default for {field}")
        values[field] = numeric_literal(match.group(1), f"{path.name}:{line_number}:{field}")
    missing = ATTACK_FIELDS - values.keys()
    if missing:
        raise ValueError(f"{path.name}: missing exported float defaults: {', '.join(sorted(missing))}")
    return values


def parse_attack_resource(path, defaults):
    """Apply literal tracked-field overrides from exactly one [resource] section."""
    values = dict(defaults)
    in_resource = False
    resource_sections = 0
    assigned = set()
    for line_number, original in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_resource = line == "[resource]"
            resource_sections += int(in_resource)
            continue
        if not in_resource:
            continue
        assignment = re.fullmatch(r"(\w+)\s*=\s*(.+)", line)
        if assignment is None:
            if any(re.match(rf"{field}\b", line) for field in ATTACK_FIELDS):
                raise ValueError(f"{path.name}:{line_number}: malformed tracked override")
            continue
        field, expression = assignment.groups()
        if field not in ATTACK_FIELDS:
            continue
        if field in assigned:
            raise ValueError(f"{path.name}:{line_number}: duplicate override for {field}")
        assigned.add(field)
        values[field] = numeric_literal(expression, f"{path.name}:{line_number}:{field}")
    if resource_sections != 1:
        raise ValueError(f"{path.name}: expected exactly one [resource] section")
    if any(value < 0 for value in values.values()) or values["active"] <= 0:
        raise ValueError(f"{path.name}: tracked attack values must be nonnegative and active must be positive")
    return values


def check_literal_overrides(path, expected):
    """Extra impact fields accept only explicit bool, number or Vector3 literals."""
    assignments={}
    active=False
    for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        line=line.split('#',1)[0].strip()
        if line.startswith('['):
            active=line=='[resource]'
        if not active:
            continue
        match=re.fullmatch(r'(\w+)\s*=\s*(.+)',line)
        if not match or match.group(1) not in expected:
            continue
        field,expression=match.groups()
        if field in assignments:
            raise ValueError(f'{path.name}:{number}: duplicate impact field {field}')
        value=expected[field]
        if type(value) is bool:
            if expression not in ('true','false'):
                raise ValueError(f'{field}: only a boolean literal is supported')
            actual=expression=='true'
            matched=actual==value
        elif isinstance(value,list) and len(value)==3:
            vector=re.fullmatch(r'Vector3\(([^()]*)\)',expression)
            if vector is None:
                raise ValueError(f'{field}: only Vector3 numeric literals are supported')
            parts=vector.group(1).split(',')
            if len(parts)!=3:
                raise ValueError(f'{field}: expected three Vector3 components')
            actual=[numeric_literal(part,field) for part in parts]
            matched=all(same_number(a,b) for a,b in zip(actual,value))
        else:
            actual=numeric_literal(expression,field)
            matched=same_number(actual,value)
        if not matched:
            raise ValueError(f'{field}: impact motion/physics literal mismatch')
        assignments[field]=actual
    missing=expected.keys()-assignments.keys()
    if missing:
        raise ValueError('Missing explicit impact fields: '+', '.join(sorted(missing)))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)


def check_production(root=ROOT):
    root = root.resolve()
    report = {
        "schema_version": 1,
        "ok": False,
        "scope": "planned_source_contract_and_reference_integrity_only",
        "counts": {"assets": 0, "references": 0, "clips": 0, "attack_resources": 0},
        "candidate_sources_checked": 0,
        "errors": [],
        "not_checked": ["MCP authentication or generation", "image or 3D visual quality", "skin deformation", "runtime animation integration", "hardware performance"],
    }
    errors = report["errors"]

    def local_file(relative, label, within=None):
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            errors.append(f"{label}: expected a repository-relative file path")
            return None
        target = (root / relative).resolve()
        allowed = (root / within).resolve() if within else root
        if not allowed.is_relative_to(root) or not target.is_relative_to(allowed):
            errors.append(f"{label}: path escapes allowed source root: {relative}")
            return None
        if not target.is_file():
            errors.append(f"{label}: missing source file: {relative}")
            return None
        return target

    def document(relative):
        path = local_file(str(relative), str(relative))
        if path is None:
            return None
        try:
            data = load_json(path)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{relative}: {error}")
            return None
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            errors.append(f"{relative}: expected schema_version 1 object")
            return None
        return data

    def records(data, field, label):
        value = data.get(field)
        if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
            errors.append(f"{label}: {field} must be a nonempty object list")
            return []
        return value

    def sources(data, label):
        value = data.get("sources")
        if not isinstance(value, list) or not value:
            errors.append(f"{label}: sources must be nonempty local file paths")
            return
        for source in value:
            local_file(source, f"{label}.sources")

    def planning_document(data, label):
        if data.get("status") != "planned" or data.get("verification_status") != "pending":
            errors.append(f"{label}: planning input must retain status=planned and verification_status=pending")
        if not isinstance(data.get("source_commit"), str) or not COMMIT.fullmatch(data["source_commit"]):
            errors.append(f"{label}: source_commit must identify the inspected 40-character commit, not imply current HEAD validation")

    specs = document(PRODUCTION / "asset_specs.json")
    motions = document(PRODUCTION / "motion_contract.json")
    manifest = document(REFERENCE_ROOT / "manifest.json")
    if specs is None or motions is None or manifest is None:
        return report
    planning_document(specs, "asset_specs")
    planning_document(motions, "motion_contract")

    # Hash only local reference files under the reference root. No URLs are fetched.
    references = {}
    for entry in records(manifest, "assets", "reference manifest"):
        filename = entry.get("file")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            errors.append("reference manifest: file must be a single local filename")
            continue
        if filename in references:
            errors.append(f"reference manifest: duplicate file {filename}")
            continue
        references[filename] = entry
        target = local_file(str(REFERENCE_ROOT / filename), "reference manifest", REFERENCE_ROOT)
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"reference manifest: invalid SHA-256 for {filename}")
        elif target is not None:
            try:
                actual = target.read_bytes()
                if hashlib.sha256(actual).hexdigest() != digest:
                    errors.append(f"reference manifest: SHA-256 mismatch for {filename}")
                if type(entry.get("bytes")) is not int or entry["bytes"] != len(actual):
                    errors.append(f"reference manifest: byte count mismatch for {filename}")
            except OSError as error:
                errors.append(f"reference manifest: cannot read {filename}: {error}")
        if entry.get("runtime_asset") is not False or entry.get("varco_generated") is not False or entry.get("status") != "generated_concept_reference":
            errors.append(f"reference manifest: {filename} must remain an explicitly non-runtime, non-VARCO concept reference")
        if not isinstance(entry.get("provider"), str) or not entry["provider"].strip():
            errors.append(f"reference manifest: provider missing for {filename}")
    report["counts"]["references"] = len(references)

    assets = records(specs, "assets", "asset_specs")
    report["counts"]["assets"] = len(assets)
    asset_ids = [entry.get("id") for entry in assets]
    if any(not isinstance(value, str) for value in asset_ids) or len(asset_ids) != len(EXPECTED_ASSETS) or set(value for value in asset_ids if isinstance(value, str)) != EXPECTED_ASSETS:
        errors.append("asset_specs: expected three unique IDs lyra_body, sentinel_melee, pilgrim_courtyard")
    for asset in assets:
        identifier = asset.get("id")
        label = f"asset {identifier}"
        if asset.get("status") != "planned" or asset.get("visual_acceptance") != "pending":
            errors.append(f"{label}: model and visual acceptance are still planned/pending inputs")
        sources(asset, label)
        reference = asset.get("reference")
        if not isinstance(reference, dict):
            errors.append(f"{label}: missing reference object")
            continue
        target = local_file(reference.get("file"), label, REFERENCE_ROOT)
        entry = references.get(target.name) if target is not None else None
        if entry is None:
            errors.append(f"{label}: reference is not present in the reference manifest")
            continue
        for field in ("sha256", "provider"):
            if reference.get(field) != entry.get(field):
                errors.append(f"{label}: reference {field} differs from manifest")
        if reference.get("runtime_asset") is not False or reference.get("varco_generated") is not False or reference.get("status") != "generated_2d_concept_only":
            errors.append(f"{label}: reference must remain explicitly 2D concept only")
        if isinstance(identifier, str) and identifier in {"lyra_body", "sentinel_melee"}:
            generation = asset.get("generation_input")
            if not isinstance(generation, dict) or generation.get("reference_file") != reference.get("file") or generation.get("reference_sha256") != reference.get("sha256"):
                errors.append(f"{label}: generation input must refer to the same reviewed source image and hash")

    clips = records(motions, "clips", "motion_contract")
    report["counts"]["clips"] = len(clips)
    names = [entry.get("name") for entry in clips]
    if any(not isinstance(value, str) for value in names) or len(names) != len(EXPECTED_CLIPS) or set(value for value in names if isinstance(value, str)) != EXPECTED_CLIPS:
        errors.append("motion_contract: expected exactly nine unique clip names")
    sources(motions, "motion_contract")
    defaults_path = local_file("game/scripts/core/attack_data.gd", "AttackData defaults")
    defaults = None
    if defaults_path is not None:
        try:
            defaults = parse_attack_defaults(defaults_path)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"AttackData defaults: {error}")

    for clip in clips:
        name = clip.get("name")
        label = f"clip {name}"
        if not isinstance(name, str):
            continue
        if clip.get("status") != "planned" or clip.get("root_motion") is not False:
            errors.append(f"{label}: expected planned, in-place clip input")
        if not finite_number(clip.get("duration_s")) or clip["duration_s"] <= 0:
            errors.append(f"{label}: duration_s must be positive finite seconds")
        if type(clip.get("loop")) is not bool:
            errors.append(f"{label}: loop must be a boolean")
        if name in {"idle", "walk", "run"}:
            # These durations are design targets, not constants from the controller.
            if not isinstance(clip.get("duration_source"), str) or not clip["duration_source"].startswith("art_target") or clip.get("loop") is not True:
                errors.append(f"{label}: looping locomotion duration must be identified as an art target")
            continue
        if name not in {"light_1", "light_2", "light_3"}:
            continue
        expected_resource = f"game/data/{name}.tres"
        if clip.get("resource") != expected_resource:
            errors.append(f"{label}: resource must be {expected_resource}")
            continue
        if clip.get("duration_source") != "effective_AttackData_resource" or clip.get("loop") is not False:
            errors.append(f"{label}: expected non-looping effective AttackData duration")
        path = local_file(expected_resource, label)
        if defaults is None or path is None:
            continue
        try:
            values = parse_attack_resource(path, defaults)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{label}: {error}")
            continue
        report["counts"]["attack_resources"] += 1
        effective = clip.get("effective_data")
        if not isinstance(effective, dict) or set(effective) != ATTACK_FIELDS:
            errors.append(f"{label}: effective_data must contain exactly the eight tracked float fields")
        else:
            for field, value in values.items():
                if not same_number(effective[field], value):
                    errors.append(f"{label}: effective_data.{field} differs from current source ({value})")
        startup, active, recovery = (values[field] for field in ("startup", "active", "recovery"))
        active_end = startup + active
        duration = active_end + recovery
        if not same_number(clip.get("duration_s"), duration):
            errors.append(f"{label}: duration_s differs from current startup+active+recovery ({duration})")
        windows = clip.get("gameplay_windows")
        if not isinstance(windows, dict):
            errors.append(f"{label}: missing gameplay_windows")
        else:
            expected_windows = {"startup_s": [0, startup], "active_s": [startup, active_end], "recovery_s": [active_end, duration]}
            for field, expected in expected_windows.items():
                actual = windows.get(field)
                if not isinstance(actual, list) or len(actual) != 2 or not all(same_number(actual[index], value) for index, value in enumerate(expected)):
                    errors.append(f"{label}: {field} differs from current source window")
            if not same_number(windows.get("cancel_eligible_from_s"), active_end):
                errors.append(f"{label}: cancel_eligible_from_s differs from active end")
        angles = clip.get("sweep_angles_degrees")
        expected_angles = [-values["arc"] / 2, values["arc"] / 2]
        if not isinstance(angles, list) or len(angles) != 2 or not all(same_number(angles[index], value) for index, value in enumerate(expected_angles)):
            errors.append(f"{label}: signed sweep angles differ from current arc")

    impact=motions.get('impact_slice')
    if impact is not None:
        if not isinstance(impact,dict) or not isinstance(impact.get('charged_heavy'),dict):
            errors.append('impact_slice: expected charged_heavy object')
        else:
            charged=impact['charged_heavy']
            path=local_file(charged.get('resource'),'impact_slice charged_heavy')
            if path is not None and defaults is not None:
                try:
                    values=parse_attack_resource(path,defaults)
                    for field in ['startup','active','recovery','arc','reach']:
                        if not same_number(values[field],charged.get('effective_data',{}).get(field)):
                            raise ValueError('charged_heavy '+field+' differs from motion contract')
                    if not same_number(sum(values[k] for k in ['startup','active','recovery']),charged.get('duration_s')):
                        raise ValueError('charged_heavy duration differs from motion contract')
                    extra=charged.get('explicit_physics_fields')
                    if not isinstance(extra,dict) or not extra:
                        raise ValueError('Missing explicit physical blade/lunge fields')
                    check_literal_overrides(path,extra)
                except (OSError,ValueError) as error:
                    errors.append('impact_slice: '+str(error))

    # Candidate metadata is optional and has no required schema/status here.
    # Only the declared local bytes are checked; this cannot approve runtime art.
    candidates = PRODUCTION / "candidates"
    for manifest_path in sorted((root / candidates).glob("*/manifest.json")):
        relative = manifest_path.relative_to(root)
        label = str(relative)
        checked_path = local_file(str(relative), label, candidates)
        if checked_path is None:
            continue
        try:
            candidate = load_json(checked_path)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{label}: {error}")
            continue
        if not isinstance(candidate, dict):
            errors.append(f"{label}: candidate manifest must be an object")
            continue
        folder = relative.parent

        def candidate_file(filename, byte_count, digest, artifact_label):
            if not isinstance(filename, str) or not filename or Path(filename).is_absolute():
                errors.append(f"{artifact_label}: expected a candidate-relative file path")
                return False
            target = local_file(str(folder / filename), artifact_label, folder)
            if type(byte_count) is not int or byte_count < 0 or not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append(f"{artifact_label}: expected byte count and SHA-256 metadata")
                return False
            if target is None:
                return False
            try:
                actual_bytes = 0
                actual_digest = hashlib.sha256()
                with target.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        actual_bytes += len(chunk)
                        actual_digest.update(chunk)
            except OSError as error:
                errors.append(f"{artifact_label}: cannot read source: {error}")
                return False
            matched = True
            if actual_bytes != byte_count:
                errors.append(f"{artifact_label}: byte count mismatch")
                matched = False
            if actual_digest.hexdigest() != digest:
                errors.append(f"{artifact_label}: SHA-256 mismatch")
                matched = False
            return matched

        if candidate_file(candidate.get("source_file"), candidate.get("source_bytes"), candidate.get("source_sha256"), label + ": source"):
            report["candidate_sources_checked"] += 1
        derived = candidate.get("derived_files", [])
        if not isinstance(derived, list) or not all(isinstance(entry, dict) for entry in derived):
            errors.append(f"{label}: optional derived_files must be an object list")
            continue
        for index, entry in enumerate(derived):
            candidate_file(entry.get("file"), entry.get("bytes"), entry.get("sha256"), f"{label}: derived_files[{index}]")

        # New installed animation candidates pin both their runtime copy and
        # the actual tools/recipe used. Legacy historical manifests stay valid.
        pins = candidate.get("provenance_files", [])
        if not isinstance(pins, list) or not all(isinstance(pin, dict) for pin in pins):
            errors.append(f"{label}: provenance_files must be an object list")
            pins = []
        installation = candidate.get("runtime_installation")
        if installation is not None:
            if not isinstance(installation, dict):
                errors.append(f"{label}: runtime_installation must be an object")
            else:
                pins = pins + [installation]
                if installation.get("sha256") != candidate.get("source_sha256"):
                    errors.append(f"{label}: runtime copy must match candidate source SHA-256")
        for index, pin in enumerate(pins):
            pin_label = f"{label}: pinned_file[{index}]"
            target = local_file(pin.get("file"), pin_label)
            if target is None:
                continue
            digest = pin.get("sha256")
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append(f"{pin_label}: expected SHA-256")
                continue
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append(f"{pin_label}: SHA-256 mismatch")
        expected_names = candidate.get("expected_clips")
        if expected_names is not None:
            if not isinstance(expected_names, list) or not expected_names or not all(isinstance(name,str) and name for name in expected_names) or len(set(expected_names)) != len(expected_names):
                errors.append(f"{label}: expected_clips must contain unique nonempty names")
            elif isinstance(candidate.get("source_file"),str):
                source = local_file(str(folder/candidate["source_file"]), label+": clip_source", folder)
                if source is not None:
                    try:
                        with source.open("rb") as stream:
                            magic, version, length, size, kind = struct.unpack("<IIIII",stream.read(20))
                            if magic != 0x46546c67 or version != 2 or length != source.stat().st_size or kind != 0x4e4f534a or size > 16*1024*1024:
                                raise ValueError("expected bounded complete GLB2 JSON")
                            document=json.loads(stream.read(size))
                        actual_names=[entry.get("name") for entry in document.get("animations",[])]
                        if sorted(actual_names) != sorted(expected_names):
                            errors.append(f"{label}: expected_clips differ from actual GLB animations")
                    except (OSError, ValueError, TypeError, struct.error) as error:
                        errors.append(f"{label}: cannot inspect candidate clips: {error}")

    report["ok"] = not errors
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root; default is this tool's checkout")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report, including on failure")
    args = parser.parse_args(argv)
    try:
        report = check_production(args.root)
    except (OSError, UnicodeError, ValueError) as error:
        report = {"schema_version": 1, "ok": False, "scope": "planned_source_contract_and_reference_integrity_only", "counts": {}, "errors": [str(error)]}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["ok"]:
        counts = report["counts"]
        print(f"ART_PRODUCTION_OK assets={counts['assets']} references={counts['references']} clips={counts['clips']} attack_resources={counts['attack_resources']} candidate_sources={report['candidate_sources_checked']}")
        print("Checked planning structure, local reference integrity, and three literal attack contracts; visual/runtime quality is not approved.")
    else:
        print("Art production validation failed:", file=sys.stderr)
        for error in report["errors"]:
            print(f"- {error}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
