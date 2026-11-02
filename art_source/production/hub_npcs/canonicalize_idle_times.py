"""Repair one explicitly supported provider loop-export defect without changing raw GLBs.

Only LINEAR float VEC3/VEC4 channels whose sole timestamp violation is a doubled
final timestamp, with the final output row byte-identical to the first loop
pose, are accepted. Keep the final loop closure and drop its earlier duplicate.
No tolerance, arbitrary duplicate removal, retiming, mesh or material edits.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import struct


def digest(data):return hashlib.sha256(data).hexdigest()


def _canonicalize(data):
    if len(data)<28 or struct.unpack_from('<4sII',data)!=(b'glTF',2,len(data)):
        raise ValueError('Expected a complete GLB2')
    size,kind=struct.unpack_from('<I4s',data,12)
    if kind!=b'JSON' or size>16*1024*1024 or size%4 or 20+size+8>len(data):raise ValueError('Invalid JSON chunk')
    document=json.loads(data[20:20+size]);offset=20+size
    length,kind=struct.unpack_from('<I4s',data,offset)
    if kind!=b'BIN\0' or length%4 or offset+8+length!=len(data):raise ValueError('Expected one embedded BIN chunk')
    original=data[offset+8:];binary=bytearray(original)
    changed=deepcopy(document)
    if len(document.get('buffers',[]))!=1 or document['buffers'][0].get('uri'):
        raise ValueError('Only one embedded buffer is supported')
    declared=document['buffers'][0]['byteLength']
    if type(declared) is not int or not 0<declared<=len(original) or len(original)-declared>3:
        raise ValueError('Invalid declared embedded buffer boundary')
    if not isinstance(document.get('accessors'),list) or not document['accessors'] or not isinstance(document.get('bufferViews'),list):
        raise ValueError('Nonempty accessors and bufferViews are required')
    def rows(index):
        if type(index) is not int or not 0<=index<len(document['accessors']):
            raise ValueError('Invalid animation accessor index')
        a=document['accessors'][index]
        if a.get('sparse') or a['componentType']!=5126 or a['type'] not in ['SCALAR','VEC3','VEC4']:
            raise ValueError('Only dense float SCALAR/VEC3/VEC4 accessors are supported')
        vi=a['bufferView']
        if type(vi) is not int or not 0<=vi<len(document['bufferViews']):raise ValueError('Invalid bufferView index')
        view=document['bufferViews'][vi]
        width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]*4
        if view.get('byteStride',width)!=width or view.get('buffer',0)!=0:
            raise ValueError('Only tightly packed float accessors are supported')
        vo,vl,ao,count=view.get('byteOffset',0),view['byteLength'],a.get('byteOffset',0),a['count']
        if any(type(v) is not int for v in [vo,vl,ao,count]) or min(vo,ao)<0 or min(vl,count)<=0:
            raise ValueError('Invalid accessor/view offset, length or count')
        if vo%4 or ao%4 or vo+vl>declared or ao+width*count>vl:
            raise ValueError('Accessor or bufferView exceeds its declared boundary')
        start=vo+ao
        raw=original[start:start+width*a['count']]
        if len(raw)!=width*a['count']:raise ValueError('Accessor exceeds embedded data')
        return a,[raw[i:i+width] for i in range(0,len(raw),width)]
    def append_accessor(old,raw_rows,is_time=False):
        while len(binary)%4:binary.append(0)
        start=len(binary);raw=b''.join(raw_rows);binary.extend(raw)
        view_index=len(changed['bufferViews'])
        changed['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(raw)})
        new=deepcopy(old);new['bufferView']=view_index;new.pop('byteOffset',None)
        new['count']=len(raw_rows);new.pop('min',None);new.pop('max',None)
        if is_time:
            values=[struct.unpack('<f',r)[0] for r in raw_rows];new['min']=[min(values)];new['max']=[max(values)]
        changed['accessors'].append(new);return len(changed['accessors'])-1
    records=[]
    if not isinstance(document.get('animations'),list) or len(document['animations'])!=1:
        raise ValueError('Exactly one provider idle clip is required')
    for ai,animation in enumerate(document['animations']):
        if not isinstance(animation.get('samplers'),list) or not animation['samplers'] or not isinstance(animation.get('channels'),list) or not animation['channels']:
            raise ValueError('Nonempty animation samplers and channels are required')
        for channel in animation['channels']:
            index=channel['sampler']
            if type(index) is not int or not 0<=index<len(animation['samplers']):raise ValueError('Invalid channel sampler index')
        for si,sampler in enumerate(animation['samplers']):
            if sampler.get('interpolation','LINEAR')!='LINEAR':raise ValueError('Only LINEAR interpolation is supported')
            ta,trows=rows(sampler['input']);oa,orows=rows(sampler['output'])
            if ta['type']!='SCALAR' or oa['type'] not in ['VEC3','VEC4'] or len(trows)!=len(orows) or len(trows)<3:
                raise ValueError('Unsupported channel input/output shape')
            times=[struct.unpack('<f',row)[0] for row in trows]
            components=[value for row in orows for value in struct.unpack('<'+'f'*(len(row)//4),row)]
            if not all(math.isfinite(v) for v in [*times,*components]):
                raise ValueError('All animation times and output components must be finite')
            if any(t<0 for t in times) or any(times[i]<=times[i-1] for i in range(1,len(times)-1)) or times[-1]!=times[-2]:
                raise ValueError('Not the exact isolated duplicated-final-timestamp pattern')
            if orows[-1]!=orows[0]:raise ValueError('Final duplicate is not byte-identical to first loop pose')
            kept=list(range(len(times)-2))+[len(times)-1]
            target=changed['animations'][ai]['samplers'][si]
            target['input']=append_accessor(ta,[trows[i] for i in kept],True)
            target['output']=append_accessor(oa,[orows[i] for i in kept])
            count=len(orows[-1])//4
            before=struct.unpack('<'+'f'*count,orows[-2]);after=struct.unpack('<'+'f'*count,orows[-1])
            records.append({'animation':ai,'sampler':si,'source_count':len(times),'derived_count':len(kept),
                'duplicate_time_s':times[-1],'first_time_s':times[0],
                'final_matches_first_byte_exact':True,'removed_row':'earlier of two final equal-time samples',
                'removed_vs_retained_value_component_max':max(abs(a-b) for a,b in zip(before,after))})
    changed['buffers'][0]['byteLength']=len(binary)
    while len(binary)%4:binary.append(0)
    encoded=json.dumps(changed,separators=(',',':'),ensure_ascii=False).encode()
    encoded+=b' '*((-len(encoded))%4)
    output=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    return output,{'schema_version':1,'status':'explicit_final_duplicate_canonicalization_not_new_motion_authorship',
        'source_sha256':digest(data),'output_sha256':digest(output),'source_bin_prefix_byte_exact':bytes(binary[:len(original)])==original,
        'mesh_skin_rest_material_document_unchanged':all(changed.get(k)==document.get(k) for k in ['meshes','nodes','skins','materials','textures','images','scenes','scene']),
        'common_time_shift_s':0,'samplers':records,
        'interpretation':'At each final doubled timestamp retain the provider final sample, which exactly closes the first loop pose; no other samples changed.'}


def canonicalize(data):
    try:
        return _canonicalize(data)
    except (KeyError,IndexError,TypeError,AttributeError,struct.error,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('Malformed or unsupported GLB chunk/accessor/animation structure') from exc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--report',required=True,type=Path);a=p.parse_args()
    raw=a.input.read_bytes();output,report=canonicalize(raw)
    report.update(source_file=str(a.input),output_file=str(a.output),tool_file=__file__,tool_sha256=digest(Path(__file__).read_bytes()))
    if a.output.exists() or a.report.exists():raise ValueError('Refuse to overwrite prior artifacts')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('xb') as stream:stream.write(output)
    with a.report.open('x') as stream:stream.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if digest(a.input.read_bytes())!=report['source_sha256']:raise ValueError('Raw source changed')
    print(json.dumps({'output':str(a.output),'sha256':report['output_sha256'],'samplers':len(report['samplers']),'raw_unchanged':True}))


if __name__=='__main__':main()
