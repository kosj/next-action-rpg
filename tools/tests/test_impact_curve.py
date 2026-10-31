"""Actual interpolated FK must agree; exact authored endpoint targets are insufficient."""
import json
import math
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_impact_curve import audit_curve, slerp


def fixture(path,intervals):
    times=[.34+.18*i/intervals for i in range(intervals+1)]
    positions=[];rotations=[]
    for index in range(intervals+1):
        fraction=index/intervals;progress=3*fraction**4-2*fraction**6
        az=math.radians(-85+170*progress);pitch=math.radians(50-95*progress)
        # Invert the runtime PI facing and capsule-floor offset.
        positions.extend([-.22+.46*progress,1.42-.32*progress,.28-.14*progress])
        direction=[math.sin(az)*math.cos(pitch),math.sin(pitch),math.cos(az)*math.cos(pitch)]
        quaternion=[direction[2],0,-direction[0],1+direction[1]]
        length=math.sqrt(sum(v*v for v in quaternion));rotations.extend(v/length for v in quaternion)
    binary=b'';views=[];accessors=[]
    for values,width,type_name in [(times,1,'SCALAR'),(positions,3,'VEC3'),(rotations,4,'VEC4')]:
        data=struct.pack('<'+'f'*len(values),*values)
        views.append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)})
        accessors.append({'bufferView':len(views)-1,'componentType':5126,'count':len(values)//width,'type':type_name})
        binary+=data
    document={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
        'bufferViews':views,'accessors':accessors,'nodes':[{'name':'RightHand'}],
        'animations':[{'name':'charged_heavy','samplers':[{'input':0,'output':1,'interpolation':'LINEAR'},
            {'input':0,'output':2,'interpolation':'LINEAR'}],
            'channels':[{'sampler':0,'target':{'node':0,'path':'translation'}},
                {'sampler':1,'target':{'node':0,'path':'rotation'}}]}]}
    payload=json.dumps(document).encode();payload+=b' '*((-len(payload))%4)
    path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(payload)+len(binary))+
        struct.pack('<II',len(payload),0x4e4f534a)+payload+struct.pack('<II',len(binary),0x004e4942)+binary)


class ImpactCurveTests(unittest.TestCase):
    recipe={'weapon_socket':{'basis_columns':[[1,0,0],[0,1,0],[0,0,1]],'offset_m':[0,0,0]}}

    def test_exact_endpoint_targets_do_not_approve_bad_midpoint(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'coarse.glb';fixture(path,1);report=audit_curve(path,self.recipe)
        keys=[row for row in report['samples'] if abs(row['time_s']-.34)<1e-6 or abs(row['time_s']-.52)<1e-6]
        self.assertTrue(all(row['grip_error_m']<1e-6 and row['tip_error_m']<1e-6 for row in keys))
        self.assertGreater(report['max_tip_error_m'],.1)
        self.assertFalse(report['passed'])

    def test_finely_sampled_actual_trs_passes_existing_limits(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'dense.glb';fixture(path,300);report=audit_curve(path,self.recipe)
        self.assertGreater(report['active_samples'],600)
        self.assertLess(report['max_tip_error_m'],.003)
        self.assertTrue(report['passed'])

    def test_opposite_quaternion_sign_does_not_create_fake_rotation(self):
        self.assertEqual(slerp([0,0,0,1],[0,0,0,-1],.5),[0,0,0,1])


if __name__=='__main__':unittest.main()
