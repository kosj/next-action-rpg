"""Create one COLOR_0-only eye palette comparison; all other bytes stay exact.

No image, geometry, normal, node, material or index is modified. The smaller
pupil is a vertex-color boundary; existing primitive/material groups remain
unchanged. This is a pending comparison asset, never a runtime installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def linear(srgb):
    return np.array([v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in srgb])


def read(path):
    raw=path.read_bytes()
    if struct.unpack_from('<4sII',raw)!=(b'glTF',2,len(raw)):
        raise ValueError('Expected complete GLB2')
    count,kind=struct.unpack_from('<I4s',raw,12)
    if kind!=b'JSON' or count>16*1024*1024:
        raise ValueError('Invalid JSON chunk')
    document=json.loads(raw[20:20+count])
    length,kind=struct.unpack_from('<I4s',raw,20+count)
    if kind!=b'BIN\0' or 28+count+length!=len(raw):
        raise ValueError('Expected one embedded BIN chunk')
    return raw,document,28+count


def array(raw,document,bin_offset,index):
    a=document['accessors'][index]
    if a.get('sparse') or a.get('normalized') or a['componentType']!=5126:
        raise ValueError('Palette candidate requires non-sparse float32 attributes')
    width={'VEC3':3,'VEC4':4}[a['type']]
    view=document['bufferViews'][a['bufferView']]
    start=bin_offset+view.get('byteOffset',0)+a.get('byteOffset',0)
    stride=view.get('byteStride',width*4)
    values=np.ndarray((a['count'],width),dtype='<f4',buffer=raw,offset=start,strides=(stride,4)).copy()
    return values,start,stride


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-glb',type=Path,required=True)
    parser.add_argument('--refit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.input_glb.resolve(strict=True);refit_path=args.refit.resolve(strict=True)
    output=args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Use a separate new or empty output directory')
    raw,document,bin_offset=read(source);source_sha=sha(raw)
    refit=json.loads(refit_path.read_text())
    if source_sha!=refit['web_eye']['sha256']:
        raise ValueError('Input does not match the frozen refit Web-eye SHA')
    primitives=document['meshes'][0]['primitives']
    positions={p['attributes']['POSITION'] for p in primitives}
    colors={p['attributes']['COLOR_0'] for p in primitives}
    if len(positions)!=1 or len(colors)!=1:
        raise ValueError('Expected shared position/color accessors across unchanged material groups')
    position,_,_=array(raw,document,bin_offset,next(iter(positions)))
    old,color_start,color_stride=array(raw,document,bin_offset,next(iter(colors)))
    if len(position)!=len(old) or not np.all(np.isfinite(position)) or not np.all(np.isfinite(old)):
        raise ValueError('Invalid input vertex attributes')
    rigid=np.array(refit['attachment_contract']['source_head_rest_rigid_world_matrix_y_up'],dtype=float)
    source_world=position.astype(float)@rigid[:3,:3].T+rigid[:3,3]
    centers=np.array([e['globe_center_source_world_y_up_m'] for e in refit['apertures']])
    distances=np.linalg.norm(source_world[:,None,:]-centers[None,:,:],axis=2)
    eye_index=np.argmin(distances,axis=1)
    relative=source_world-centers[eye_index]
    rho=np.linalg.norm(relative[:,:2],axis=1)
    theta=np.arctan2(relative[:,1],relative[:,0])
    # The nominal6mm row can move a few nanometres when packed into float32.
    # Original bright sclera rows are explicitly excluded, including that edge.
    float32_radial_tolerance=1e-8
    sclera=np.mean(old[:,:3],axis=1)>.12
    back=relative[:,2]<=0
    editable=(~back)&(~sclera)&(rho<=.006+float32_radial_tolerance)
    old_pupil=np.mean(old[:,:3],axis=1)<.01
    old_base=linear((.20,.27,.24))
    new_base=linear((.32,.40,.36))
    pupil_color=linear((.025,.030,.027))
    target_pupil=.0015;feather=.0006
    changed=old.copy();updated=[]
    for index in np.flatnonzero(editable):
        if not old_pupil[index]:
            # Preserve the existing per-channel angular/limbal/shadow factors.
            iris=old[index,:3].astype(float)*(new_base/old_base)
        else:
            # Newly revealed iris inside the former2.4mm dark region uses the
            # exact original procedural striation/limbal/upper-shadow formula.
            angle=float(theta[index]);radius=float(rho[index])
            variation=1+.16*math.sin(angle*41+radius*1200)*math.sin(angle*13+.4)
            limbal=.48 if radius>.006-.0008 else 1.
            upper_shadow=1-.22*max(0.,math.sin(angle))
            iris=new_base*variation*limbal*upper_shadow
        amount=float(np.clip((rho[index]-(target_pupil-feather))/(2*feather),0,1))
        amount=amount*amount*(3-2*amount)
        rgb=(1-amount)*pupil_color+amount*iris
        if not np.all((rgb>=0)&(rgb<=1)):
            raise ValueError('Color outside linear RGB range')
        changed[index,:3]=rgb.astype('<f4')
        if not np.array_equal(changed[index],old[index]):updated.append(int(index))
    if not updated:
        raise ValueError('Palette produced no changed color rows')
    result=bytearray(raw);permitted=np.zeros(len(raw),dtype=bool)
    for index in updated:
        start=color_start+index*color_stride
        result[start:start+12]=changed[index,:3].astype('<f4').tobytes()
        permitted[start:start+12]=True
    result=bytes(result)
    original_bytes=np.frombuffer(raw,dtype='u1');result_bytes=np.frombuffer(result,dtype='u1')
    differences=original_bytes!=result_bytes
    if len(result)!=len(raw) or np.any(differences&~permitted):
        raise ValueError('A byte outside permitted COLOR_0 RGB changed')
    if result[:bin_offset]!=raw[:bin_offset]:
        raise ValueError('GLB/JSON/BIN headers must remain byte exact')
    assert np.array_equal(changed[sclera],old[sclera])
    assert np.array_equal(changed[back],old[back])
    assert np.array_equal(changed[:,3],old[:,3])
    output.mkdir(parents=True,exist_ok=True)
    candidate=output/'eyes-palette.glb';candidate.write_bytes(result)
    check,check_doc,_=read(candidate)
    if check_doc!=document or sha(source.read_bytes())!=source_sha:
        raise ValueError('JSON or source changed during derivation')
    report={
        'status':'pending_actual_Web_visual_comparison','runtime_adoption':'pending','aaa_approval':'pending',
        'source':{'path':str(source),'sha256':source_sha,'bytes':len(raw),'unchanged':True},
        'refit':{'path':str(refit_path),'sha256':sha(refit_path.read_bytes())},
        'candidate':{'path':str(candidate),'sha256':sha(check),'bytes':len(check)},
        'tool_sha256':sha(Path(__file__).read_bytes()),
        'controlled_change':{'old_iris_srgb':[.20,.27,.24],'new_iris_srgb':[.32,.40,.36],
            'old_iris_linear':old_base.tolist(),'new_iris_linear':new_base.tolist(),
            'old_color_pupil_radius_m':.0024,'new_color_pupil_radius_m':target_pupil,
            'pupil_smoothstep_half_width_m':feather,'iris_radius_m':.006,
            'float32_radial_selection_tolerance_m':float32_radial_tolerance,
            'same_striation_limbal_upper_shadow_formula':True,
            'note':'Smaller pupil exists only in vertex color; existing Pupil/GrayGreenIris material triangle groups stay unchanged'},
        'byte_audit':{'json_and_all_headers_byte_exact':result[:bin_offset]==raw[:bin_offset],
            'all_non_COLOR0_bytes_byte_exact':not bool(np.any(differences&~permitted)),
            'COLOR0_alpha_byte_exact':True,'changed_RGB_vertex_rows':len(updated),
            'changed_byte_count':int(differences.sum()),'updated_vertex_indices':updated,
            'total_vertices':len(position),'sclera_rows_byte_exact':int(sclera.sum()),
            'back_rows_byte_exact':int(back.sum()),'POSITION_NORMAL_indices_materials_nodes_rest_topology_byte_exact':True},
        'unchanged_geometry_contract':refit['attachment_contract'],
        'fit_scope':'Geometry/normal/topology/transform bytes exact: accepted d7d geometry fit is unchanged. Appearance requires independent actual Web comparison.',
        'limitations':['No runtime/shared asset mutation','No image editing/generation','No Blender/browser rendering or GPU performance test','One controlled alternative; no adoption claim']}
    (output/'palette-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'candidate':report['candidate'],'audit':{k:v for k,v in report['byte_audit'].items() if k!='updated_vertex_indices'}},indent=2))


if __name__=='__main__':main()
