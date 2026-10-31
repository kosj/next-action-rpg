import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest


SPEC=importlib.util.spec_from_file_location('append_character_animations',Path(__file__).resolve().parents[1]/'append_character_animations.py')
graft=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graft)


def write_fixture(path,animation='idle',reverse_nodes=False,rest_offset=0):
    binary=b'immutable-body!!'+struct.pack('<2f6f',0,.1,0,0,0,.01,0,0)
    bone={'name':'Bone','translation':[rest_offset,1,0]}
    parent={'name':'Armature','children':[0 if reverse_nodes else 1]}
    document={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
        'nodes':[bone,parent] if reverse_nodes else [parent,bone],
        'meshes':[{'name':'immutable body'}],'materials':[{'name':'original material'}],
        'skins':[{'joints':[1]}],'scenes':[{'nodes':[0]}],'scene':0,
        'bufferViews':[{'buffer':0,'byteOffset':16,'byteLength':8},{'buffer':0,'byteOffset':24,'byteLength':24}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':2,'type':'SCALAR','min':[0],'max':[.1]},
            {'bufferView':1,'componentType':5126,'count':2,'type':'VEC3'}],
        'animations':[{'name':animation,'samplers':[{'input':0,'output':1,'interpolation':'LINEAR'}],
            'channels':[{'sampler':0,'target':{'node':0 if reverse_nodes else 1,'path':'translation'}}]}]}
    payload=json.dumps(document,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4)
    path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(payload)+len(binary))+
        struct.pack('<II',len(payload),0x4e4f534a)+payload+struct.pack('<II',len(binary),0x004e4942)+binary)


class AnimationGraftTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.glb';self.motion=self.root/'motion.glb';self.output=self.root/'new.glb'
        write_fixture(self.source);write_fixture(self.motion,'charged_heavy',reverse_nodes=True)

    def test_original_body_binary_and_unrelated_animation_are_preserved(self):
        source_doc,source_bin=graft.read_glb(self.source)
        before=hashlib.sha256(self.source.read_bytes()).hexdigest()
        report=graft.append_animations(self.source,self.motion,self.output,{'charged_heavy'})
        result,result_bin=graft.read_glb(self.output)
        self.assertEqual(result_bin[:len(source_bin)],source_bin)
        for field in ['nodes','meshes','materials','skins','scenes','scene']:
            self.assertEqual(result[field],source_doc[field])
        self.assertEqual(result['animations'][0],source_doc['animations'][0])
        self.assertEqual(result['animations'][1]['channels'][0]['target']['node'],1)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),before)
        self.assertTrue(report['original_bin_prefix_exact'])

    def test_rest_basis_difference_is_rejected_before_publication(self):
        write_fixture(self.motion,'charged_heavy',reverse_nodes=True,rest_offset=.01)
        with self.assertRaisesRegex(ValueError,'rest basis differs'):
            graft.append_animations(self.source,self.motion,self.output,{'charged_heavy'})
        self.assertFalse(self.output.exists())

    def test_existing_candidate_is_never_overwritten(self):
        self.output.write_bytes(b'existing reviewed candidate')
        with self.assertRaisesRegex(ValueError,'Never overwrite'):
            graft.append_animations(self.source,self.motion,self.output,{'charged_heavy'})
        self.assertEqual(self.output.read_bytes(),b'existing reviewed candidate')

    def test_unexpected_action_set_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'action set differs'):
            graft.append_animations(self.source,self.motion,self.output,{'other_state'})
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
