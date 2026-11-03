"""Independent core-schema and failure guards; never uses runtime assets."""
import copy,hashlib,json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import compact_glb_live_data as tool

def encode(doc,binary,extra=b''):
    text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*((-len(text))%4)
    binary+=b'\0'*((-len(binary))%4)
    return struct.pack('<4sII',b'glTF',2,28+len(text)+len(binary)+len(extra))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary+extra

def fixture():
    binary=bytearray();views=[];accessors=[]
    def view(data,**kw):
        binary.extend(b'\0'*((-len(binary))%4));v={'buffer':0,'byteOffset':len(binary),'byteLength':len(data),**kw};binary.extend(data);views.append(v);return len(views)-1
    def acc(v,component,shape,count,**kw):
        a={'componentType':component,'type':shape,'count':count,**kw}
        if v is not None:a['bufferView']=v
        accessors.append(a);return len(accessors)-1
    vertex=view(struct.pack('<18f',0,0,0,0,0,1,1,0,0,0,0,1,0,1,0,0,0,1),byteStride=24,target=34962)
    pos=acc(vertex,5126,'VEC3',3);normal=acc(vertex,5126,'VEC3',3,byteOffset=12)
    joints=acc(view(bytes(12)),5121,'VEC4',3)
    weights=acc(view(struct.pack('<12f',*([1,0,0,0]*3))),5126,'VEC4',3)
    indices=acc(view(struct.pack('<3H',0,1,2),target=34963),5123,'SCALAR',3)
    sparse_index=view(bytes([1]));sparse_values=view(struct.pack('<3f',0,.05,0))
    morph=acc(None,5126,'VEC3',3,sparse={'count':1,'indices':{'bufferView':sparse_index,'componentType':5121},'values':{'bufferView':sparse_values}})
    identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    inverse=acc(view(struct.pack('<16f',*identity)),5126,'MAT4',1)
    times=acc(view(struct.pack('<2f',0,1)),5126,'SCALAR',2)
    values=acc(view(struct.pack('<6f',0,0,0,0,1,0)),5126,'VEC3',2)
    unused_sampler_output=acc(view(struct.pack('<6f',0,0,0,1,0,0)),5126,'VEC3',2)
    image=view(b'\x89PNG\r\n\x1a\nKEEP-EVERY-IMAGE-BYTE')
    acc(view(struct.pack('<f',123.0)),5126,'SCALAR',1) # truly unreferenced old graft
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1]}],
         'nodes':[{'name':'RootJoint','extras':{'unchanged':'metadata'}},{'name':'Mesh','mesh':0,'skin':0}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':pos,'NORMAL':normal,'JOINTS_0':joints,'WEIGHTS_0':weights},'indices':indices,'material':0,'targets':[{'POSITION':morph}]}],'weights':[0]}],
         'skins':[{'joints':[0],'skeleton':0,'inverseBindMatrices':inverse}],
         'animations':[{'name':'light_1','samplers':[{'input':times,'output':values},{'input':times,'output':unused_sampler_output}], 'channels':[{'sampler':0,'target':{'node':0,'path':'translation'}}]}],
         'images':[{'bufferView':image,'mimeType':'image/png'}],'samplers':[{'magFilter':9729}],
         'textures':[{'source':0,'sampler':0}],'materials':[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}}}],
         'bufferViews':views,'accessors':accessors,'buffers':[{'byteLength':len(binary),'name':'KeepBufferMetadata'}]}
    return doc,bytes(binary)

class Guards(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='compact-guards-');self.directory=Path(self.temporary.name)
        self.doc,self.bin=fixture();self.source=self.directory/'source.glb';self.source.write_bytes(encode(self.doc,self.bin));self.original=self.source.read_bytes();self.output=self.directory/'out.glb'
    def tearDown(self):self.temporary.cleanup()
    def rejected(self,doc=None,binary=None,extra=b''):
        self.source.write_bytes(encode(doc if doc is not None else self.doc,binary if binary is not None else self.bin,extra))
        before=self.source.read_bytes()
        with self.assertRaises(ValueError):tool.compact_document(self.source,self.output)
        self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),before)
    def test_strided_sparse_morph_skin_images_and_all_samplers_preserved(self):
        report=tool.compact_document(self.source,self.output)
        before=tool.semantic_fingerprints(self.source);after=tool.semantic_fingerprints(self.output)
        self.assertEqual(before,after);self.assertTrue(report['semantic_snapshot_equal'])
        self.assertEqual(report['accessors'],{'before':11,'after':10})
        self.assertEqual(report['buffer_views'],{'before':12,'after':11})
        self.assertEqual(before['buffer_metadata'],{'name':'KeepBufferMetadata'})
        self.assertTrue(any(fp['byte_stride']==24 for fp in before['live_accessors'].values()))
        self.assertTrue(any('sparse' in fp['declaration'] for fp in before['live_accessors'].values()))
        fingerprints=list(before['live_accessors'].values())
        digest=lambda raw:hashlib.sha256(raw).hexdigest()
        position=next(fp for fp in fingerprints if fp['byte_stride']==24 and fp['declaration'].get('byteOffset',0)==0)
        self.assertEqual(position['value_bytes_sha256'],digest(struct.pack('<9f',0,0,0,1,0,0,0,1,0)))
        sparse=next(fp for fp in fingerprints if 'sparse' in fp['declaration'])
        self.assertEqual(sparse['value_bytes_sha256'],digest(struct.pack('<9f',0,0,0,0,.05,0,0,0,0)))
        inverse=next(fp for fp in fingerprints if fp['declaration']['type']=='MAT4')
        self.assertEqual(inverse['value_bytes_sha256'],digest(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)))
        self.assertEqual(before['images'][0]['bufferView']['payload_sha256'],digest(b'\x89PNG\r\n\x1a\nKEEP-EVERY-IMAGE-BYTE'))
        self.assertTrue(any(fp['count']==2 and fp['value_bytes_sha256']==digest(struct.pack('<6f',0,0,0,1,0,0)) for fp in fingerprints))
        # Unused *sampler* is retained; only the truly orphaned accessor disappears.
        self.assertEqual(len(after['live_accessors']),10);self.assertEqual(self.source.read_bytes(),self.original)
    def test_existing_output_is_never_overwritten(self):
        self.output.write_bytes(b'keep');self.assertRaises(ValueError,tool.compact_document,self.source,self.output);self.assertEqual(self.output.read_bytes(),b'keep')
    def test_inplace_is_rejected(self):
        self.assertRaises(ValueError,tool.compact_document,self.source,self.source);self.assertEqual(self.source.read_bytes(),self.original)
    def test_bad_accessor_range_is_rejected_without_output(self):
        doc=copy.deepcopy(self.doc);doc['accessors'][0]['count']=100;self.rejected(doc)
    def test_sparse_index_out_of_range_is_rejected(self):
        binary=bytearray(self.bin);v=self.doc['bufferViews'][self.doc['accessors'][self.doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION']]['sparse']['indices']['bufferView']];binary[v['byteOffset']]=9;self.rejected(binary=bytes(binary))
    def test_required_extension_is_rejected(self):
        doc=copy.deepcopy(self.doc);doc['extensionsRequired']=['EXT_unknown'];self.rejected(doc)
    def test_undeclared_nested_extension_is_rejected(self):
        doc=copy.deepcopy(self.doc);doc['nodes'][0]['extensions']={'EXT_unknown':{'accessor':0}};self.rejected(doc)
    def test_unknown_glb_chunk_is_rejected(self):self.rejected(extra=struct.pack('<II',4,0x12345678)+b'keep')
    def test_external_image_is_rejected(self):
        doc=copy.deepcopy(self.doc);doc['images']=[{'uri':'external.png'}];self.rejected(doc)
    def test_semantic_mismatch_removes_created_output(self):
        with patch.object(tool,'semantic_fingerprints',return_value={}):self.assertRaises(ValueError,tool.compact_document,self.source,self.output)
        self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),self.original)
    def test_live_payload_and_static_changes_change_fingerprints(self):
        original=tool.semantic_fingerprints(self.source)
        binary=bytearray(self.bin);struct.pack_into('<f',binary,self.doc['bufferViews'][0]['byteOffset'],.125)
        self.source.write_bytes(encode(self.doc,bytes(binary)));changed=tool.semantic_fingerprints(self.source)
        self.assertNotEqual(original['mesh_skin_sha256'],changed['mesh_skin_sha256'])
        doc=copy.deepcopy(self.doc);doc['nodes'][0]['translation']=[0,.1,0];self.source.write_bytes(encode(doc,self.bin))
        self.assertNotEqual(original['static_json_sha256'],tool.semantic_fingerprints(self.source)['static_json_sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
