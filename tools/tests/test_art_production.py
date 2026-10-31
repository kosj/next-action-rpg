"""Guard art input provenance and the timing boundary between design and gameplay."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import struct
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_art_production as production


class ArtProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.defaults = {"damage": 18.0, "poise": 14.0, "startup": 0.13, "active": 0.17, "recovery": 0.22, "reach": 2.7, "arc": 130.0, "lunge": 3.5}
        self.source = self.root / "game/scripts/core/attack_data.gd"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("\n".join(f"@export var {key}: float = {value}" for key, value in self.defaults.items()), encoding="utf-8")
        self.assets = {
            "schema_version": 1, "status": "planned", "verification_status": "pending", "source_commit": "a" * 40, "assets": []
        }
        self.motions = {
            "schema_version": 1, "status": "planned", "verification_status": "pending", "source_commit": "a" * 40,
            "sources": ["game/scripts/core/attack_data.gd"], "clips": []
        }
        self.manifest = {"schema_version": 1, "assets": []}
        reference_root = self.root / production.REFERENCE_ROOT
        reference_root.mkdir(parents=True)
        for identifier in ("lyra_body", "sentinel_melee", "pilgrim_courtyard"):
            filename = f"{identifier}.png"
            # Opaque bytes are intentional: the checker hashes references, not image quality.
            data = f"test-reference-{identifier}".encode()
            (reference_root / filename).write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            entry = {"file": filename, "bytes": len(data), "sha256": digest, "provider": "fixture", "status": "generated_concept_reference", "runtime_asset": False, "varco_generated": False}
            self.manifest["assets"].append(entry)
            relative = str(production.REFERENCE_ROOT / filename)
            asset = {
                "id": identifier, "status": "planned", "visual_acceptance": "pending", "sources": ["game/scripts/core/attack_data.gd"],
                "reference": {"file": relative, "sha256": digest, "provider": "fixture", "status": "generated_2d_concept_only", "runtime_asset": False, "varco_generated": False}
            }
            if identifier != "pilgrim_courtyard":
                asset["generation_input"] = {"reference_file": relative, "reference_sha256": digest}
            self.assets["assets"].append(asset)
        data_dir = self.root / "game/data"
        data_dir.mkdir(parents=True)
        for name in ("idle", "walk", "run", "dodge", "parry", "hit", "light_1", "light_2", "light_3"):
            clip = {"name": name, "status": "planned", "root_motion": False, "loop": name in {"idle", "walk", "run"}, "duration_s": 1.8, "duration_source": "art_target"}
            if name.startswith("light_"):
                resource = f"game/data/{name}.tres"
                overrides = ""
                values = dict(self.defaults)
                if name == "light_3":
                    overrides = "startup = 0.18\nactive = 0.22\nrecovery = 0.3\n"
                    values.update(startup=0.18, active=0.22, recovery=0.3)
                (self.root / resource).write_text('[gd_resource type="Resource" format=3]\n[resource]\n'+overrides, encoding="utf-8")
                end = values["startup"] + values["active"]
                duration = end + values["recovery"]
                clip.update({
                    "resource": resource, "effective_data": values, "duration_source": "effective_AttackData_resource", "duration_s": duration,
                    "gameplay_windows": {"startup_s": [0, values["startup"]], "active_s": [values["startup"], end], "recovery_s": [end, duration], "cancel_eligible_from_s": end},
                    "sweep_angles_degrees": [-values["arc"] / 2, values["arc"] / 2]
                })
                self.motions["sources"].append(resource)
            self.motions["clips"].append(clip)
        self.save()

    def save(self):
        for path, value in ((production.PRODUCTION / "asset_specs.json", self.assets), (production.PRODUCTION / "motion_contract.json", self.motions), (production.REFERENCE_ROOT / "manifest.json", self.manifest)):
            (self.root / path).write_text(json.dumps(value), encoding="utf-8")

    def report(self):
        return production.check_production(self.root)

    def test_wellformed_report_and_cli_are_machine_readable(self):
        report = self.report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["counts"], {"assets": 3, "references": 3, "clips": 9, "attack_resources": 3})
        self.assertIn("runtime animation integration", report["not_checked"])
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(production.main(["--root", str(self.root), "--json"]), 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_changed_reference_bytes_fail_even_when_source_paths_match(self):
        image = self.root / production.REFERENCE_ROOT / "lyra_body.png"
        image.write_bytes(image.read_bytes()+b"tamper")
        report = self.report()
        self.assertFalse(report["ok"])
        self.assertTrue(any("SHA-256 mismatch" in error for error in report["errors"]))

    def test_changed_resource_time_invalidates_effective_duration_and_windows(self):
        resource = self.root / "game/data/light_1.tres"
        resource.write_text(resource.read_text()+"startup = 0.14\n", encoding="utf-8")
        errors = self.report()["errors"]
        for fragment in ("effective_data.startup", "duration_s differs", "active_s differs", "cancel_eligible"):
            self.assertTrue(any(fragment in error for error in errors), (fragment, errors))

    def test_missing_reference_produces_failure_report_without_crashing(self):
        (self.root / production.REFERENCE_ROOT / "sentinel_melee.png").unlink()
        report = self.report()
        self.assertFalse(report["ok"])
        self.assertTrue(any("missing source file" in error for error in report["errors"]))
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(production.main(["--root", str(self.root), "--json"]), 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_unsupported_source_expression_and_duplicate_override_are_rejected(self):
        self.source.write_text(self.source.read_text().replace("startup: float = 0.13", "startup: float = 0.1 + 0.03"), encoding="utf-8")
        self.assertTrue(any("unsupported numeric expression" in error for error in self.report()["errors"]))
        self.source.write_text(self.source.read_text().replace("0.1 + 0.03", "0.13"), encoding="utf-8")
        resource = self.root / "game/data/light_1.tres"
        resource.write_text(resource.read_text()+"active = 0.17\nactive = 0.18\n", encoding="utf-8")
        self.assertTrue(any("duplicate override" in error for error in self.report()["errors"]))

    def test_reference_paths_cannot_escape_the_reference_source_root(self):
        self.assets["assets"][0]["reference"]["file"] = "game/scripts/core/attack_data.gd"
        self.save()
        self.assertTrue(any("escapes allowed source root" in error for error in self.report()["errors"]))

    def test_art_target_duration_is_independent_but_gameplay_window_is_exact(self):
        self.motions["clips"][0]["duration_s"] = 2.1
        self.save()
        self.assertTrue(self.report()["ok"], self.report()["errors"])
        light = next(clip for clip in self.motions["clips"] if clip["name"] == "light_1")
        light["gameplay_windows"]["active_s"][0] = 0.12
        self.save()
        self.assertTrue(any("active_s differs" in error for error in self.report()["errors"]))

    def test_duplicate_clips_or_fake_completion_cannot_pass(self):
        self.motions["clips"][-1]["name"] = "light_1"
        self.assets["assets"][0]["status"] = "complete"
        self.save()
        errors = self.report()["errors"]
        self.assertTrue(any("nine unique" in error for error in errors))
        self.assertTrue(any("still planned/pending" in error for error in errors))

    def test_invalid_metadata_is_reported_instead_of_raising_type_error(self):
        self.motions["clips"][0]["name"] = {"bad": "name"}
        self.assets["assets"][0]["id"] = ["bad"]
        self.save()
        self.assertFalse(self.report()["ok"])

    def test_candidate_source_and_optional_derived_files_detect_tampering(self):
        folder = self.root / production.PRODUCTION / "candidates/fixture-001"
        folder.mkdir(parents=True)
        source = b"candidate source fixture"
        rig = b"derived rig fixture"
        (folder / "source.glb").write_bytes(source)
        (folder / "rigged.glb").write_bytes(rig)
        candidate = {
            "source_file": "source.glb", "source_bytes": len(source), "source_sha256": hashlib.sha256(source).hexdigest(),
            "derived_files": [{"file": "rigged.glb", "bytes": len(rig), "sha256": hashlib.sha256(rig).hexdigest()}]
        }
        (folder / "manifest.json").write_text(json.dumps(candidate), encoding="utf-8")
        report = self.report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["candidate_sources_checked"], 1)
        (folder / "source.glb").write_bytes(source + b"tamper")
        self.assertTrue(any(": source: SHA-256 mismatch" in error for error in self.report()["errors"]))
        (folder / "source.glb").write_bytes(source)
        (folder / "rigged.glb").write_bytes(rig + b"tamper")
        self.assertTrue(any("derived_files[0]: SHA-256 mismatch" in error for error in self.report()["errors"]))

    def test_candidate_source_and_derived_paths_cannot_escape_their_folder(self):
        folder = self.root / production.PRODUCTION / "candidates/fixture-001"
        folder.mkdir(parents=True)
        data = b"source fixture"
        (folder / "source.glb").write_bytes(data)
        candidate = {"source_file": "../../asset_specs.json", "source_bytes": len(data), "source_sha256": hashlib.sha256(data).hexdigest()}
        (folder / "manifest.json").write_text(json.dumps(candidate), encoding="utf-8")
        self.assertTrue(any(": source: path escapes allowed source root" in error for error in self.report()["errors"]))
        candidate["source_file"] = "source.glb"
        candidate["derived_files"] = [{"file": "../outside.glb", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]
        (folder / "manifest.json").write_text(json.dumps(candidate), encoding="utf-8")
        self.assertTrue(any("derived_files[0]: path escapes allowed source root" in error for error in self.report()["errors"]))

    def test_candidate_installed_runtime_and_recipe_pins_detect_tampering(self):
        folder=self.root/production.PRODUCTION/'candidates/impact-fixture'
        folder.mkdir(parents=True)
        payload=json.dumps({'animations':[{'name':'charged_heavy'},{'name':'RESET'}]}).encode()
        payload+=b' '*((-len(payload))%4)
        data=struct.pack('<IIIII',0x46546c67,2,20+len(payload),len(payload),0x4e4f534a)+payload
        (folder/'source.glb').write_bytes(data)
        runtime=self.root/'game/runtime.glb';runtime.write_bytes(data)
        recipe=self.root/'recipe.json';recipe.write_text('{"profile":"impact"}')
        candidate={'source_file':'source.glb','source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),
            'runtime_installation':{'file':'game/runtime.glb','sha256':hashlib.sha256(data).hexdigest()},
            'provenance_files':[{'file':'recipe.json','sha256':hashlib.sha256(recipe.read_bytes()).hexdigest()}],
            'expected_clips':['charged_heavy','RESET']}
        manifest=folder/'manifest.json';manifest.write_text(json.dumps(candidate))
        self.assertTrue(self.report()['ok'])
        runtime.write_bytes(data+b'changed')
        self.assertTrue(any('pinned_file' in e and 'mismatch' in e for e in self.report()['errors']))
        runtime.write_bytes(data);recipe.write_text('{"profile":"different"}')
        self.assertTrue(any('pinned_file' in e and 'mismatch' in e for e in self.report()['errors']))

    def test_candidate_missing_authored_clip_is_rejected(self):
        folder=self.root/production.PRODUCTION/'candidates/impact-fixture'
        folder.mkdir(parents=True)
        payload=json.dumps({'animations':[{'name':'RESET'}]}).encode();payload+=b' '*((-len(payload))%4)
        data=struct.pack('<IIIII',0x46546c67,2,20+len(payload),len(payload),0x4e4f534a)+payload
        (folder/'source.glb').write_bytes(data)
        candidate={'source_file':'source.glb','source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),
            'expected_clips':['charged_heavy','RESET']}
        (folder/'manifest.json').write_text(json.dumps(candidate))
        self.assertTrue(any('expected_clips differ' in e for e in self.report()['errors']))

    def test_impact_curve_and_phase_literals_cannot_drift(self):
        self.motions['impact_slice']={'charged_heavy':{'resource':'game/data/charged.tres','duration_s':1.06,
            'effective_data':{'startup':.34,'active':.18,'recovery':.54,'arc':170.0,'reach':1.5},
            'explicit_physics_fields':{'active_lunge':3.2,'physical_blade_sweep':True,'blade_grip_end':[-.24,1.125,-.14]}}}
        self.save()
        resource=self.root/'game/data/charged.tres'
        original='[gd_resource type="Resource" format=3]\n[resource]\nstartup = 0.34\nactive = 0.18\nrecovery = 0.54\narc = 170.0\nreach = 1.5\nactive_lunge = 3.2\nphysical_blade_sweep = true\nblade_grip_end = Vector3(-0.24, 1.125, -0.14)\n'
        resource.write_text(original)
        self.assertTrue(self.report()['ok'])
        resource.write_text(original.replace('1.125','1.2'))
        self.assertTrue(any('literal mismatch' in e for e in self.report()['errors']))
        resource.write_text(original.replace('3.2','3.0 + 0.2'))
        self.assertTrue(any('unsupported numeric expression' in e for e in self.report()['errors']))


if __name__ == "__main__":
    unittest.main()
