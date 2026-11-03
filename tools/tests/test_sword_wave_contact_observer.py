"""Audit real charged blade/wave receipts and reject forged observer packets."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from charged_heavy_browser_smoke import validate_contact, validate_wave_contact, validate_charged_events


FIXTURE=Path(__file__).with_name('fixtures')/'charged_wave_contact_main_9a1e9dc.json'


class SwordWaveContactObserverTests(unittest.TestCase):
    def setUp(self):
        self.fixture=json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.events=self.fixture['events']
        self.quality=self.fixture['quality']
        self.target_id=self.fixture['target_id']
        self.wave=deepcopy(self.events[1])

    def point_in_wave_frame(self,x,y,z):
        forward=self.wave['direction']
        norm=math.sqrt(sum(v*v for v in forward))
        forward=[v/norm for v in forward]
        right=[-forward[2],0,forward[0]]
        self.wave['point']=[o+x*r-z*f+(y if i==1 else 0)
            for i,(o,r,f) in enumerate(zip(self.wave['wave_origin'],right,forward))]

    def test_real_failed_browser_receipts_have_one_blade_and_two_waves(self):
        report=validate_charged_events(self.events,self.quality,self.target_id)
        self.assertEqual(report['attack_instance_id'],5)
        self.assertEqual([e['sequence'] for e in report['physical']],[1])
        self.assertEqual([e['sequence'] for e in report['waves']],[2,3])
        self.assertEqual(len(report['physical_checks']),1)
        self.assertEqual(len(report['wave_checks']),2)
        self.assertEqual(len(report['pairs']),3)
        for event in report['waves']:
            self.assertAlmostEqual(event['amount'],69.3*.65)
            validate_wave_contact(event,self.quality)

    def test_wave_never_masquerades_as_physical_blade_contact(self):
        validate_contact(self.events[0])
        with self.assertRaises(AssertionError):
            validate_contact(self.wave)
        forged=deepcopy(self.events)
        forged[0]['amount']=45.045
        forged[0]['health_after']=forged[0]['health_before']-45.045
        with self.assertRaises(AssertionError):
            validate_charged_events(forged,self.quality,self.target_id)

    def test_wave_damage_and_health_delta_are_both_audited(self):
        for amount,after in [(69.3,25.7),(45.5,49.5),(45.045,50.0)]:
            with self.subTest(amount=amount,health_after=after):
                event=deepcopy(self.wave)
                event.update(amount=amount,health_after=after)
                with self.assertRaises(AssertionError):
                    validate_wave_contact(event,self.quality)

    def test_wave_rejects_forged_curve_phase_and_blade_markers(self):
        mutations={'curve_sha256':self.events[0]['curve_sha256'],
            'curve_source_sha256':self.events[0]['curve_source_sha256'],
            'contact_phase':.5,'damage_start_fraction':.18}
        for name in ('contact_blade_grip','contact_blade_tip','contact_blade_motion',
                     'contact_damage_base','contact_damage_tip',
                     'contact_damage_axis_base','contact_damage_axis_tip'):
            mutations[name]=[0,.001,0]
        for field,value in mutations.items():
            with self.subTest(field=field):
                event=deepcopy(self.wave)
                event[field]=value
                with self.assertRaises(AssertionError):
                    validate_wave_contact(event,self.quality)

    def test_wave_source_spawn_offset_and_height_are_independent_checks(self):
        for field,axis in [('source_position',0),('wave_origin',1),('wave_origin',2)]:
            with self.subTest(field=field,axis=axis):
                event=deepcopy(self.wave)
                event[field][axis]+=.02
                with self.assertRaises(AssertionError):
                    validate_wave_contact(event,self.quality)

    def test_wave_rejects_untravelled_out_of_range_and_impossible_age_packets(self):
        mutations=[{'wave_sweep_start_m':-.01},
            {'wave_sweep_start_m':1.21}, {'wave_sweep_end_m':1.3},
            {'wave_travel_m':1.3},
            {'wave_sweep_start_m':6.6,'wave_sweep_end_m':6.91,'wave_travel_m':6.91,'wave_age_s':.4},
            {'wave_age_s':.01},{'wave_age_s':0}, {'wave_age_s':1},
            {'attack_elapsed':.40}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                event=deepcopy(self.wave)
                event.update(mutation)
                with self.assertRaises(AssertionError):
                    validate_wave_contact(event,self.quality)

    def test_actual_width_height_and_curved_sweep_exclude_aabb_false_contacts(self):
        # Each coordinate is relative to the launch frame. The final two
        # points fit a broad wave AABB but miss the actual crescent at x=1.15.
        for x,y,z in [(1.21,0,-.8),(0,.13,-1.0),
                      (1.15,0,-1.18),(1.15,0,-.33)]:
            with self.subTest(local_point=(x,y,z)):
                self.point_in_wave_frame(x,y,z)
                with self.assertRaises(AssertionError):
                    validate_wave_contact(self.wave,self.quality)

    def test_geometry_uses_the_actual_quality_segment_split(self):
        # At x=.9 the eight-segment rendered front is .19125m and the
        # six-segment front is .198333m. These edge packets distinguish the
        # actual prism policy despite the existing 5mm position budget.
        self.point_in_wave_frame(.9,0,.19125-1.2+.001)
        validate_wave_contact(self.wave,0)
        with self.assertRaises(AssertionError):
            validate_wave_contact(self.wave,1)
        self.point_in_wave_frame(.9,0,.198333333333333+.24-.9+.003)
        validate_wave_contact(self.wave,1)
        with self.assertRaises(AssertionError):
            validate_wave_contact(self.wave,0)

    def test_wave_geometry_respects_facing_rotations(self):
        # A rigid ninety-degree Y rotation preserves all packet geometry.
        for field in ('direction','normal','source_position','wave_origin','point','target_position'):
            x,y,z=self.wave[field]
            self.wave[field]=[z,y,-x]
        validate_wave_contact(self.wave,self.quality)

    def test_wave_rejects_nonfinite_values_and_non_scalar_identity(self):
        mutations=[('amount',float('nan')),('wave_age_s',float('inf')),
            ('attack_instance_id',True),('attack_instance_id',2**53),
            ('target_id',0),('sequence',1.5),('sword_wave',1),
            ('direction',[0,1,0]),('point',[0,float('nan'),0])]
        for field,value in mutations:
            with self.subTest(field=field,value=value):
                event=deepcopy(self.wave)
                event[field]=value
                with self.assertRaises(AssertionError):
                    validate_wave_contact(event,self.quality)

    def test_shared_strike_target_ledger_rejects_wave_and_cross_kind_duplicates(self):
        for duplicate_target in (self.events[0]['target_id'],self.events[1]['target_id']):
            with self.subTest(target=duplicate_target):
                events=deepcopy(self.events)
                duplicate=deepcopy(events[2])
                duplicate.update(sequence=4,target_id=duplicate_target)
                events.append(duplicate)
                with self.assertRaises(AssertionError):
                    validate_charged_events(events,self.quality,self.target_id)

    def test_wave_cannot_replace_required_physical_target_or_original_strike(self):
        with self.assertRaises(AssertionError):
            validate_charged_events(self.events[1:],self.quality,self.target_id)
        with self.assertRaises(AssertionError):
            validate_charged_events(self.events,self.quality,self.wave['target_id'])
        events=deepcopy(self.events)
        events[1]['attack_instance_id']=6
        with self.assertRaises(AssertionError):
            validate_charged_events(events,self.quality,self.target_id)

    def test_pure_receipt_audit_does_not_modify_input_events(self):
        before=deepcopy(self.events)
        validate_charged_events(self.events,self.quality,self.target_id)
        self.assertEqual(self.events,before)


if __name__=='__main__':unittest.main()
