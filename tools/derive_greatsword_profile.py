"""Bake a broader Hero blade as geometry only; runtime reuses the source PBR.

The original scene still supplies its markers, hilt/guard and material/texture
resources. No additional texture atlas is imported or shipped by this asset.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct

from append_character_animations import read_glb


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3.0-2.0*t)


def dsmooth(t):
    return 6.0*t*(1.0-t) if 0.0 < t < 1.0 else 0.0


def profile(y, factor):
    a, b = (y-.24)/.10, (y-1.03)/.155
    w = smooth(a)*(1.0-smooth(b))
    derivative = dsmooth(a)/.10*(1.0-smooth(b))-smooth(a)*dsmooth(b)/.155
    return 1.0+(factor-1.0)*w, (factor-1.0)*derivative


def normalized(v):
    length = math.sqrt(sum(x*x for x in v))
    if length < 1e-10:
        raise ValueError("Degenerate direction")
    return tuple(x/length for x in v)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--factor', type=float, default=1.8)
    args = p.parse_args()
    if not 1.0 < args.factor <= 2.0:
        p.error('Blade profile factor must be in (1,2]')
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        p.error('A separate new output is required')
    source_digest = sha(args.source)
    doc, binary = read_glb(args.source)
    if doc.get('skins') or doc.get('animations') or len(doc['meshes']) != 1:
        raise ValueError('One static canonical sword mesh required')
    for node in doc['nodes']:
        if 'mesh' in node and any(key in node for key in ['matrix','translation','rotation','scale']):
            raise ValueError('Canonical geometry must already be in marker coordinates')
    primitive = doc['meshes'][0]['primitives'][0]
    if len(doc['meshes'][0]['primitives']) != 1 or primitive.get('mode',4) != 4:
        raise ValueError('One indexed triangle surface required')
    attrs = primitive['attributes']
    if set(attrs) != {'POSITION','NORMAL','TANGENT','TEXCOORD_0'}:
        raise ValueError('Unexpected source attributes')
    def values(index):
        a = doc['accessors'][index];view = doc['bufferViews'][a['bufferView']]
        if a['componentType'] != 5126 or 'sparse' in a:
            raise ValueError('Dense float transform attributes required')
        width = {'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        offset = view.get('byteOffset',0)+a.get('byteOffset',0)
        stride = view.get('byteStride',width*4)
        return [struct.unpack_from('<'+'f'*width,binary,offset+i*stride) for i in range(a['count'])]
    positions, normals, tangents = [values(attrs[n]) for n in ['POSITION','NORMAL','TANGENT']]
    output_positions=[];output_normals=[];output_tangents=[];changed=[]
    for i, ((x,y,z),n,t) in enumerate(zip(positions,normals,tangents)):
        scale, derivative = profile(y,args.factor)
        output_positions.append((x*scale,y,z))
        # Exact inverse-transpose and Jacobian for x'=x*scale(y), followed by
        # tangent Gram-Schmidt. Preserve the imported handedness component.
        nn = normalized((n[0]/scale,n[1]-n[0]*x*derivative/scale,n[2]))
        tt = (scale*t[0]+x*derivative*t[1],t[1],t[2])
        dot = sum(a*b for a,b in zip(nn,tt))
        tt = normalized(tuple(a-dot*b for a,b in zip(tt,nn)))
        output_normals.append(nn);output_tangents.append((*tt,t[3]))
        if abs(scale-1.0)>1e-10:
            changed.append(i)
    result = copy.deepcopy(doc)
    for key in ['materials','images','textures','samplers','extensionsUsed','extensionsRequired']:
        result.pop(key,None)
    result['meshes'][0]['primitives'][0].pop('material',None)
    result['buffers']=[{'byteLength':0}];result['bufferViews']=[]
    # Keep only geometry bufferViews, preserving UV/index bytes and all source
    # accessor/node topology. The original image blobs are not duplicated.
    mapping={};payload=bytearray()
    for accessor in result['accessors']:
        old=accessor['bufferView']
        if old not in mapping:
            view=doc['bufferViews'][old];padding=(-len(payload))%4;payload.extend(b'\0'*padding)
            start=len(payload);offset=view.get('byteOffset',0)
            payload.extend(binary[offset:offset+view['byteLength']])
            copied=copy.deepcopy(view);copied['buffer']=0;copied['byteOffset']=start
            mapping[old]=len(result['bufferViews']);result['bufferViews'].append(copied)
        accessor['bufferView']=mapping[old]
    def replace(index, rows):
        accessor=result['accessors'][index];view=result['bufferViews'][accessor['bufferView']]
        width=len(rows[0]);stride=view.get('byteStride',width*4)
        offset=view['byteOffset']+accessor.get('byteOffset',0)
        for i,row in enumerate(rows):struct.pack_into('<'+'f'*width,payload,offset+i*stride,*row)
        if 'min' in accessor:accessor['min']=[min(row[j] for row in rows) for j in range(width)]
        if 'max' in accessor:accessor['max']=[max(row[j] for row in rows) for j in range(width)]
    replace(attrs['POSITION'],output_positions);replace(attrs['NORMAL'],output_normals);replace(attrs['TANGENT'],output_tangents)
    result['asset']['extras']={'source_sha256':source_digest,'profile':'hero_broadblade_geometry_only','width_factor':args.factor,'material_policy':'Reuse original material resources on the Hero mesh instance; no new atlas.','visual_approval':'pending'}
    result['buffers'][0]['byteLength']=len(payload)
    encoded=json.dumps(result,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    payload+=b'\0'*((-len(payload))%4)
    raw=struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(payload))+struct.pack('<II',len(encoded),0x4E4F534A)+encoded+struct.pack('<II',len(payload),0x004E4942)+payload
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
    assert sha(args.source)==source_digest
    assert result['nodes']==doc['nodes']
    assert all(a[1:]==b[1:] for a,b in zip(positions,output_positions))
    assert all(positions[i]==output_positions[i] for i in range(len(positions)) if positions[i][1]<=.24 or positions[i][1]>=1.185)
    widths=[]
    for y in [.35,.55,.75,.95]:
        ids=[i for i,p in enumerate(positions) if abs(p[1]-y)<.025]
        widths.append({'y_m':y,'old_width_m':max(positions[i][0] for i in ids)-min(positions[i][0] for i in ids),'new_width_m':max(output_positions[i][0] for i in ids)-min(output_positions[i][0] for i in ids)})
    def capsule_distance(p):
        y=max(.3342,min(1.07,p[1]));return math.dist(p,(0,y,0))
    report={'scope':'Static Hero blade-only geometric derivative; no skin/visual/gameplay/AAA approval','source_sha256':source_digest,'output_sha256':sha(args.output),'output_bytes':len(raw),'tool_sha256':sha(Path(__file__)),'factor':args.factor,'changed_vertices':len(changed),'vertex_count':len(positions),'triangles':doc['accessors'][primitive['indices']]['count']//3,'nodes_and_markers_unchanged':True,'hilt_guard_apex_positions_unchanged':True,'all_y_z_unchanged':True,'UV_indices_topology_unchanged':True,'normal_tangent_policy':'Analytic Jacobian, inverse-transpose and Gram-Schmidt; original tangent handedness retained','texture_bytes_added':0,'width_samples':widths,'changed_vertex_max_inner_axis_distance_m':max(capsule_distance(output_positions[i]) for i in changed),'whole_damage_zone_max_before_m':max(capsule_distance(p) for p in positions if p[1]>=.2142),'whole_damage_zone_max_after_m':max(capsule_distance(p) for p in output_positions if p[1]>=.2142),'limitations':['Existing unchanged vertices may extend outside nominal sharp capsule; do not claim full-mesh containment.','Runtime must reuse original PBR material/surface resources.','Same-camera neutral/game and hand/armor clearance review pending.']}
    args.output.with_suffix('.derivation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
