"""Source-preserving, bounded front-robe geometry candidate; no automatic adoption.

Only recipe-selected POSITION/NORMAL rows are patched in place. The original
JSON, topology, UVs, skin, animation and all unrelated bytes stay identical.
Anchor-ring planes come from the actual local cloth surface, not a global fit.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from append_character_animations import _local_matrix,read_glb


def sha(data):return hashlib.sha256(data).hexdigest()


def repair(recipe):
 source=ROOT/recipe['source_file'];raw=source.read_bytes()
 if sha(raw)!=recipe['source_sha256']:raise ValueError('Source hash mismatch')
 doc,binary=read_glb(source);parents={c:i for i,n in enumerate(doc['nodes'])for c in n.get('children',[])};worlds={}
 def world(i):
  if i not in worlds:
   local=np.array(_local_matrix(doc['nodes'][i]),float);worlds[i]=world(parents[i])@local if i in parents else local
  return worlds[i]
 nodes=[i for i,n in enumerate(doc['nodes'])if 'mesh'in n]
 if len(nodes)!=1 or len(doc['meshes'][0]['primitives'])!=1:raise ValueError('Exactly one body primitive is supported')
 node=nodes[0];prim=doc['meshes'][doc['nodes'][node]['mesh']]['primitives'][0]
 def array(index):
  a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
  formats={5126:('f',4),5121:('B',1),5123:('H',2),5125:('I',4)};fmt,size=formats[a['componentType']]
  if a.get('sparse')or v.get('byteStride',width*size)!=width*size:raise ValueError('Only dense tightly-packed accessors supported')
  offset=v.get('byteOffset',0)+a.get('byteOffset',0)
  values=np.array(struct.unpack_from('<'+fmt*(a['count']*width),binary,offset)).reshape(a['count'],width)
  return values,offset,size
 positions,po,_=array(prim['attributes']['POSITION']);normals,no,_=array(prim['attributes']['NORMAL']);indices,_,_=array(prim['indices']);triangles=indices.reshape(-1,3)
 conversion=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]],float)
 skin=doc['skins'][doc['nodes'][node]['skin']]
 ibms,_,_=array(skin['inverseBindMatrices'])
 joints,_,_=array(prim['attributes']['JOINTS_0']);weights,_,_=array(prim['attributes']['WEIGHTS_0'])
 if not np.allclose(weights.sum(axis=1),1,rtol=0,atol=1e-6):raise ValueError('Skin weights must sum to one')
 joint_matrices=np.array([world(index)@row.reshape(4,4).T for index,row in zip(skin['joints'],ibms)])
 matrices=np.einsum('ij,vjk->vik',conversion,np.einsum('vi,vijk->vjk',weights,joint_matrices[joints.astype(int)]))
 inverses=np.linalg.inv(matrices)
 points=np.einsum('vij,vj->vi',matrices,np.column_stack([positions,np.ones(len(positions))]))[:,:3]
 normal_matrices=inverses[:,:3,:3].transpose(0,2,1)
 world_normals=np.einsum('vij,vj->vi',normal_matrices,normals);world_normals/=np.linalg.norm(world_normals,axis=1)[:,None]
 groups=defaultdict(list)
 for i,p in enumerate(points):groups[tuple(np.rint(p/1e-7).astype(np.int64))].append(i)
 group_ids=list(groups.values());unique=np.array([np.mean(points[ids],axis=0)for ids in group_ids]);unique_normals=np.array([np.mean(world_normals[ids],axis=0)for ids in group_ids])
 result=points.copy();changed_groups=set();details=[]
 for patch in recipe['patches']:
  center=np.array(patch['center_xz_m']);radii=np.array(patch['radii_xz_m']);radius=np.linalg.norm((unique[:,[0,2]]-center)/radii,axis=1)
  surface=(unique[:,1]>=patch['front_layer_y_min_m'])&(unique_normals[:,1]>.2)
  anchors=np.flatnonzero((radius>=1)&(radius<=patch['anchor_outer_radius'])&surface)
  if len(anchors)<6:raise ValueError('Too few actual front-cloth ring anchors '+patch['id']+': '+str(len(anchors)))
  # Reject isolated low-Y inner surfaces from the measured anchor ring only.
  ymedian=float(np.median(unique[anchors,1]));anchors=anchors[np.abs(unique[anchors,1]-ymedian)<.035]
  if len(anchors)<6:raise ValueError('Too few coherent front-cloth anchors '+patch['id']+': '+str(len(anchors))+' '+repr(unique[anchors].tolist()))
  matrix=np.column_stack([unique[anchors,0],unique[anchors,2],np.ones(len(anchors))])
  plane=np.linalg.lstsq(matrix,unique[anchors,1],rcond=None)[0]
  selected=np.flatnonzero((radius<1)&surface)
  if not len(selected):raise ValueError('No interior cloth vertices selected')
  errors=[]
  for gi in selected:
   p=unique[gi];target=float(np.dot([p[0],p[2],1],plane));weight=(1-radius[gi]**2)**2
   delta=(target-p[1])*weight
   for vi in group_ids[gi]:result[vi,1]+=delta
   changed_groups.add(int(gi));errors.append({'group':int(gi),'source_point_m':p.tolist(),'plane_target_y_m':target,'blend':weight,'displacement_y_m':delta})
  details.append({'id':patch['id'],'center_xz_m':center.tolist(),'radii_xz_m':radii.tolist(),'actual_anchor_unique_vertices':len(anchors),'selected_unique_vertices':len(selected),'source_region_bounds':{'min':unique[selected].min(axis=0).tolist(),'max':unique[selected].max(axis=0).tolist()},'anchor_ring_bounds':{'min':unique[anchors].min(axis=0).tolist(),'max':unique[anchors].max(axis=0).tolist()},'anchor_y_plane_coefficients_x_z_constant':plane.tolist(),'measured_before_plane_depth_max_m':max(abs(float(np.dot([unique[i,0],unique[i,2],1],plane))-unique[i,1])for i in selected),'changes':errors})
 local=np.einsum('vij,vj->vi',inverses,np.column_stack([result,np.ones(len(result))]))[:,:3]
 patched=bytearray(raw);json_length=struct.unpack_from('<I',raw,12)[0];bin_start=28+json_length
 # Area-weighted geometric normals only for the selected physical vertices.
 accumulated=np.zeros_like(result)
 for tri in triangles:
  normal=np.cross(result[tri[1]]-result[tri[0]],result[tri[2]]-result[tri[0]])
  for vi in tri:accumulated[vi]+=normal
 changed=[];normal_rows=[]
 for gi in sorted(changed_groups):
  for vi in group_ids[gi]:
   old_bytes=raw[bin_start+po+vi*12:bin_start+po+vi*12+12];new_bytes=struct.pack('<3f',*local[vi])
   if new_bytes!=old_bytes:
    patched[bin_start+po+vi*12:bin_start+po+vi*12+12]=new_bytes;changed.append(int(vi))
 if not changed:raise ValueError('Candidate did not alter geometry')
 vertex_group={vi:gi for gi,ids in enumerate(group_ids)for vi in ids}
 affected_faces=[tri for tri in triangles if any(int(vi)in set(changed)for vi in tri)]
 normal_groups={vertex_group[int(vi)]for tri in affected_faces for vi in tri}
 smoothing_groups=0
 for gi in sorted(normal_groups):
  groups_by_original_normal=defaultdict(list)
  for vi in group_ids[gi]:groups_by_original_normal[tuple(np.rint(world_normals[vi]/1e-5).astype(np.int64))].append(vi)
  for ids in groups_by_original_normal.values():
   smoothing_groups+=1;normal=np.sum(accumulated[ids],axis=0)
   if np.linalg.norm(normal)<1e-12:raise ValueError('Degenerate repaired one-ring normal')
   normal/=np.linalg.norm(normal)
   for vi in ids:
    local_normal=matrices[vi,:3,:3].T@normal;local_normal/=np.linalg.norm(local_normal)
    new_bytes=struct.pack('<3f',*local_normal)
    if new_bytes!=raw[bin_start+no+vi*12:bin_start+no+vi*12+12]:
     patched[bin_start+no+vi*12:bin_start+no+vi*12+12]=new_bytes;normal_rows.append(int(vi))
 allowed={byte for offset,rows in [(po,changed),(no,normal_rows)]for vi in rows for byte in range(bin_start+offset+vi*12,bin_start+offset+vi*12+12)}
 unexpected=[i for i,(a,b)in enumerate(zip(raw,patched))if a!=b and i not in allowed]
 if unexpected:raise ValueError('Non-local bytes changed')
 displacement=np.linalg.norm(result-points,axis=1)
 report={'schema_version':1,'status':'bounded_geometry_candidate_pending_actual_raster_review','source_file':recipe['source_file'],'source_sha256':sha(raw),'output_sha256':sha(patched),'source_unchanged':sha(source.read_bytes())==sha(raw),'changed_position_rows':changed,'changed_normal_rows':normal_rows,'normal_one_ring_physical_groups':len(normal_groups),'normal_smoothing_groups':smoothing_groups,'normal_policy':'Recompute affected physical one-ring normals by original coincident-normal groups; retain distinct source hard/smoothing normals, keep unrelated NORMAL bytes exact. No source TANGENT attribute; Godot must generate tangents from new positions/normals and byte-identical UVs.','selected_physical_groups':len(changed_groups),'max_vertex_displacement_m':float(displacement.max()),'position_row_count':len(positions),'triangles':len(triangles),'patches':details,'byte_proof':{'same_file_size':len(patched)==len(raw),'json_chunk_byte_exact':patched[:bin_start]==raw[:bin_start],'all_bytes_outside_declared_position_and_normal_rows_exact':not unexpected,'topology_UV_skin_rest_animation_images_materials_byte_exact':True},'limitations':['Two finite front-robe patches only; no full retopology/cloth/hands/face/AAA approval','Whole NPC budget and actual-game acceptance still pending']}
 return bytes(patched),report


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',required=True,type=Path);p.add_argument('--output',type=Path);p.add_argument('--report',required=True,type=Path);a=p.parse_args();recipe=json.loads(a.recipe.read_text());data,report=repair(recipe)
 report.update(recipe_file=str(a.recipe),recipe_sha256=sha(a.recipe.read_bytes()),tool_file=str(Path(__file__).relative_to(ROOT)),tool_sha256=sha(Path(__file__).read_bytes()))
 if a.report.exists()or a.output and a.output.exists():raise ValueError('Refuse to overwrite candidate/report')
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
 a.report.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'candidate_written':bool(a.output),'sha256':sha(data),'changed_vertices':len(report['changed_position_rows']),'max_displacement_m':report['max_vertex_displacement_m'],'patches':[{k:p[k]for k in ['id','selected_unique_vertices','measured_before_plane_depth_max_m']}for p in report['patches']]}))


if __name__=='__main__':main()
