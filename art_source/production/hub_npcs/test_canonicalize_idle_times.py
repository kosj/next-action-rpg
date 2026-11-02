import json
import math
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent))
from canonicalize_idle_times import canonicalize


def fixture(times=(0,.1,.2,.2), values=None, change=None):
    values=values or [(0,0,0,1),(.1,0,0,.995),(.2,0,0,.98),(0,0,0,1)]
    timebytes=struct.pack('<'+'f'*len(times),*times)
    outbytes=struct.pack('<'+'f'*(len(values)*4),*(x for row in values for x in row))
    binary=timebytes+outbytes
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(timebytes)},{'buffer':0,'byteOffset':len(timebytes),'byteLength':len(outbytes)}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':len(times),'type':'SCALAR'},{'bufferView':1,'componentType':5126,'count':len(values),'type':'VEC4'}],
        'nodes':[{'name':'Hips'}], 'animations':[{'samplers':[{'input':0,'output':1,'interpolation':'LINEAR'}],'channels':[{'sampler':0,'target':{'node':0,'path':'rotation'}}]}]}
    if change:change(doc)
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4)
    return struct.pack('<4sII',b'glTF',2,28+len(raw)+len(binary))+struct.pack('<I4s',len(raw),b'JSON')+raw+struct.pack('<I4s',len(binary),b'BIN\0')+binary


class CanonicalizationTests(unittest.TestCase):
    def test_keeps_final_closure_and_drops_only_earlier_duplicate(self):
        original=fixture();derived,report=canonicalize(original)
        self.assertTrue(report['source_bin_prefix_byte_exact'])
        self.assertTrue(report['mesh_skin_rest_material_document_unchanged'])
        self.assertEqual(report['samplers'][0]['derived_count'],3)
        n=struct.unpack_from('<I',derived,12)[0];d=json.loads(derived[20:20+n]);b=derived[28+n:]
        sampler=d['animations'][0]['samplers'][0];a=d['accessors'][sampler['output']];v=d['bufferViews'][a['bufferView']]
        values=struct.unpack_from('<12f',b,v['byteOffset'])
        self.assertEqual(values[-4:],(0,0,0,1))
        self.assertNotEqual(values[-4:],(.2,0,0,.98))

    def test_rejects_interior_duplicate(self):
        with self.assertRaises(ValueError):canonicalize(fixture(times=(0,.1,.1,.1)))

    def test_rejects_nonfinite_times_and_outputs(self):
        for bad in [float('nan'),float('inf'),-float('inf')]:
            with self.subTest(kind='time',value=bad),self.assertRaises(ValueError):canonicalize(fixture(times=(0,bad,.2,.2)))
            with self.subTest(kind='output',value=bad),self.assertRaises(ValueError):canonicalize(fixture(values=[(0,0,0,1),(bad,0,0,1),(.2,0,0,.98),(0,0,0,1)]))

    def test_rejects_other_final_pattern(self):
        with self.assertRaises(ValueError):canonicalize(fixture(times=(0,.1,.2,.3)))
        with self.assertRaises(ValueError):canonicalize(fixture(values=[(0,0,0,1),(.1,0,0,1),(.2,0,0,1),(.01,0,0,1)]))

    def test_rejects_invalid_boundaries_empty_and_missing_animation(self):
        cases=[lambda d:d['bufferViews'][1].update(byteLength=4),lambda d:d['accessors'][1].update(bufferView=100),lambda d:d.update(animations=[]),lambda d:d['animations'][0].update(samplers=[]),lambda d:d.pop('animations')]
        for change in cases:
            with self.subTest(change=change),self.assertRaises(ValueError):canonicalize(fixture(change=change))
        with self.assertRaises(ValueError):canonicalize(fixture()[:-4])


if __name__=='__main__':unittest.main()
