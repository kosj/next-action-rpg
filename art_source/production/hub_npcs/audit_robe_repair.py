"""Read-only finite raw glTF skin/normal/UV proof for a local robe repair.

Requires NumPy (existing tools/requirements-art.txt); no engine or renderer.
It does not approve visual quality or actual imported runtime TBN frames.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import struct
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from append_character_animations import read_glb,_local_matrix
from inspect_motion_derivatives import slerp


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Asset:
 def __init__(self,path):
  self.path=path;self.doc,self.binary=read_glb(path);self.parents={c:i for i,n in enumerate(self.doc['nodes'])for c in n.get('children',[])}
  self.meshnode=next(i for i,n in enumerate(self.doc['nodes'])if 'mesh'in n);self.prim=self.doc['meshes'][self.doc['nodes'][self.meshnode]['mesh']]['primitives'][0]
  self.positions=self.acc(self.prim['attributes']['POSITION']);self.normals=self.acc(self.prim['attributes']['NORMAL']);self.uv=self.acc(self.prim['attributes']['TEXCOORD_0']);self.tri=self.acc(self.prim['indices']).astype(int).reshape(-1,3)
  self.skin=self.doc['skins'][self.doc['nodes'][self.meshnode]['skin']];self.ibm=self.acc(self.skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);self.joints=self.acc(self.prim['attributes']['JOINTS_0']).astype(int);self.weights=self.acc(self.prim['attributes']['WEIGHTS_0'])
  idle=next(a for a in self.doc['animations']if a['name']=='idle');self.tracks=[]
  for ch in idle['channels']:
   sample=idle['samplers'][ch['sampler']];self.tracks.append((ch['target']['node'],ch['target']['path'],self.acc(sample['input']).flatten(),self.acc(sample['output'])))
  self.duration=max(float(t[-1])for n,p,t,v in self.tracks)
 def acc(self,index):
  a=self.doc['accessors'][index];v=self.doc['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];fmt={5126:'f',5123:'H',5125:'I',5121:'B'}[a['componentType']];off=v.get('byteOffset',0)+a.get('byteOffset',0)
  if 'sparse'in a or 'byteStride'in v:raise ValueError('Only dense tightly packed source accepted')
  return np.array(struct.unpack_from('<'+fmt*(a['count']*width),self.binary,off)).reshape(a['count'],width)
 def matrices(self,time):
  overrides={}
  if time is not None:
   for node,path,times,values in self.tracks:
    index=max(0,min(len(times)-2,bisect.bisect_right(times,time)-1));fraction=max(0,min(1,(time-times[index])/(times[index+1]-times[index])))
    value=slerp(values[index],values[index+1],fraction)if path=='rotation'else values[index]*(1-fraction)+values[index+1]*fraction
    overrides.setdefault(node,{})[path]=list(value)
  worlds={}
  def world(index):
   if index not in worlds:
    local=np.array(_local_matrix({**self.doc['nodes'][index],**overrides.get(index,{})}));worlds[index]=world(self.parents[index])@local if index in self.parents else local
   return worlds[index]
  joint=np.array([world(index)@ibm for index,ibm in zip(self.skin['joints'],self.ibm)])
  conversion=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
  return np.einsum('ij,vjk->vik',conversion,np.einsum('vi,vijk->vjk',self.weights,joint[self.joints]))
 def evaluate(self,time):
  matrices=self.matrices(time);points=np.einsum('vij,vj->vi',matrices,np.column_stack([self.positions,np.ones(len(self.positions))]))[:,:3]
  normals=np.einsum('vij,vj->vi',np.linalg.inv(matrices[:,:3,:3]).transpose(0,2,1),self.normals);normals/=np.linalg.norm(normals,axis=1)[:,None]
  return points,normals


def audit(source,target,repair_report):
 old,new=Asset(source),Asset(target)
 if old.doc!=new.doc:raise ValueError('Source JSON must remain exact, including UV/skin/animation declarations')
 changed=np.flatnonzero(np.any(old.positions!=new.positions,axis=1));normal_changed=np.flatnonzero(np.any(old.normals!=new.normals,axis=1))
 if list(changed)!=sorted(repair_report['changed_position_rows'])or list(normal_changed)!=sorted(repair_report['changed_normal_rows']):raise ValueError('Changed row declaration mismatch')
 if not np.array_equal(old.uv,new.uv)or not np.array_equal(old.tri,new.tri)or not np.array_equal(old.weights,new.weights)or not np.array_equal(old.joints,new.joints):raise ValueError('Topology/UV/skin changed')
 touched=np.union1d(changed,normal_changed)
 affected=np.flatnonzero(np.any(np.isin(old.tri,touched),axis=1));tri=old.tri[affected];uv=old.uv[tri];du1=uv[:,1]-uv[:,0];du2=uv[:,2]-uv[:,0];det=du1[:,0]*du2[:,1]-du1[:,1]*du2[:,0]
 if np.any(abs(det)<1e-12):raise ValueError('Affected triangle has a zero/near-zero UV tangent Jacobian')
 rest,_=old.evaluate(None);foot=np.flatnonzero(rest[:,2]<=rest[:,2].min()+.04)
 if np.intersect1d(foot,changed).size or np.intersect1d(foot,normal_changed).size:raise ValueError('Foot position/normal row unexpectedly changed')
 rows=[];errors=[]
 for fraction in [None,0,.25,.5,.75,1.0]:
  time=None if fraction is None else old.duration*fraction;p0,n0=old.evaluate(time);p1,n1=new.evaluate(time)
  if not np.isfinite(p1).all()or not np.isfinite(n1).all():raise ValueError('Nonfinite evaluated skin')
  proof=[]
  for points,normals in [(p0,n0),(p1,n1)]:
   vertices=points[tri];e1=vertices[:,1]-vertices[:,0];e2=vertices[:,2]-vertices[:,0];area=np.linalg.norm(np.cross(e1,e2),axis=1)*.5
   normal=np.mean(normals[tri],axis=1);normal/=np.linalg.norm(normal,axis=1)[:,None]
   tangent=(e1*du2[:,1,None]-e2*du1[:,1,None])/det[:,None];bitangent=(-e1*du2[:,0,None]+e2*du1[:,0,None])/det[:,None]
   tangent-=normal*np.sum(tangent*normal,axis=1)[:,None];tlength=np.linalg.norm(tangent,axis=1);tangent/=tlength[:,None]
   handed=np.sum(np.cross(normal,tangent)*bitangent,axis=1)
   geometric=np.cross(e1,e2);geometric/=np.linalg.norm(geometric,axis=1)[:,None]
   normal_face_cos=np.sum(normal*geometric,axis=1)
   orthogonal_bitangent=np.cross(normal,tangent)*np.sign(handed)[:,None]
   orthogonality=np.maximum.reduce([abs(np.sum(normal*tangent,axis=1)),abs(np.sum(normal*orthogonal_bitangent,axis=1)),abs(np.sum(tangent*orthogonal_bitangent,axis=1))])
   proof.append((area,tlength,handed,normal_face_cos,float(orthogonality.max())))
  newly_degenerate=np.flatnonzero((proof[0][0]>1e-12)&(proof[1][0]<=1e-12))
  if len(newly_degenerate)or np.any(proof[1][1]<=1e-12)or np.any(abs(proof[1][2])<=1e-12):raise ValueError('Repair introduced degenerate triangle/tangent frame')
  flips=int(np.count_nonzero(np.sign(proof[0][2])!=np.sign(proof[1][2])))
  new_negative=np.flatnonzero((proof[0][3]>=0)&(proof[1][3]<0))
  corrected=np.flatnonzero((proof[0][3]<0)&(proof[1][3]>0))
  expected_handed=np.sign(det)*np.sign(proof[1][3])
  inconsistent=np.flatnonzero(np.sign(proof[1][2])!=expected_handed)
  if len(new_negative):errors.append({'error':'New normal/face negative introduced','time_s':time,'triangle_ids':affected[new_negative].tolist()})
  if len(inconsistent):errors.append({'error':'Target TBN inconsistent with immutable UV basis and corrected normal','time_s':time,'triangle_ids':affected[inconsistent].tolist()})
  rows.append({'pose':'REST'if time is None else 'idle','time_s':time,'maximum_vertex_delta_m':float(np.linalg.norm(p1-p0,axis=1).max()),'foot_vertex_delta_max_m':float(np.linalg.norm(p1[foot]-p0[foot],axis=1).max()),'affected_triangle_min_area_m2_before':float(proof[0][0].min()),'affected_triangle_min_area_m2_after':float(proof[1][0].min()),'new_degenerate_triangles':len(newly_degenerate),'uv_tangent_handedness_changes':flips,'handedness_consistent_with_UV_and_actual_normal':not len(inconsistent),'source_normal_face_negative_triangles':affected[np.flatnonzero(proof[0][3]<0)].tolist(),'target_normal_face_negative_triangles':affected[np.flatnonzero(proof[1][3]<0)].tolist(),'new_normal_face_negatives':affected[new_negative].tolist(),'corrected_source_orientations':[{'triangle':int(affected[i]),'source_normal_face_cos':float(proof[0][3][i]),'target_normal_face_cos':float(proof[1][3][i])}for i in corrected],'target_TBN_orthogonal_dot_max_abs':proof[1][4],'normal_lengths_after':[float(np.linalg.norm(n1,axis=1).min()),float(np.linalg.norm(n1,axis=1).max())]})
 return {'schema_version':1,'ok':not errors,'errors':errors,'status':'finite_raw_skin_normal_UV_structural_checks_passed_visual_pending'if not errors else 'rejected_finite_raw_TBN_gate','gate_revision':'Correct physical target TBN against immutable UV basis; explicitly correct pre-existing source normals opposite geometry. Record old-sign changes rather than resurrecting invalid source normals; reject any new normal/face negative across the full normal one-ring/boundary.','source_file':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),'target_file':target.relative_to(ROOT).as_posix(),'target_sha256':sha(target),'position_rows_changed':len(changed),'normal_rows_changed':len(normal_changed),'position_rows_total':len(old.positions),'affected_triangles':len(affected),'foot_region_vertex_count':len(foot),'foot_rows_unchanged':True,'actual_rest_changed_vertex_bounds':({'min':rest[changed].min(axis=0).tolist(),'max':rest[changed].max(axis=0).tolist()}if len(changed)else None),'source_TANGENT_attribute_present':'TANGENT'in old.prim['attributes'],'target_TANGENT_attribute_present':'TANGENT'in new.prim['attributes'],'TBN_scope':'Raw per-triangle geometric UV frame and skinned normals only. Tangents are absent in both GLBs; actual Godot importer tangent generation and raster remain pending.','frames':rows,'limitations':['Six finite REST/idle raw-skin poses do not approve continuous cloth deformation, actual imported renderer TBN, visuals, contact,hardware or AAA']}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--target',required=True,type=Path);p.add_argument('--repair-report',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();report=audit(a.source.resolve(),a.target.resolve(),json.loads(a.repair_report.read_text()));report.update(tool_file=str(Path(__file__).relative_to(ROOT)),tool_sha256=sha(Path(__file__)));a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','position_rows_changed','normal_rows_changed','affected_triangles','foot_rows_unchanged']}));raise SystemExit(0 if report['ok']else 1)


if __name__=='__main__':main()
