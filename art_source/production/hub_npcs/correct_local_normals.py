"""Minimize a strictly local normal correction, constrained by actual adjacent faces.

Only the two declared face vertices and their matching UV-seam normals may be
written. Geometry, UV, skin, clips, maps and all unrelated bytes stay exact.
The finite adjacency constraints are necessary structural checks, not art approval.
"""
import argparse,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(Path(__file__).parent))
from audit_robe_repair import Asset


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--faces',required=True,nargs='+',type=int);a=p.parse_args()
 if a.output.exists()or a.report.exists():raise ValueError('No source or candidate overwrite')
 asset=Asset(a.source);rest,normals=asset.evaluate(None);seed=set(int(i)for i in asset.tri[a.faces].flatten());groups={}
 for i,point in enumerate(rest):
  key=(tuple(np.rint(point/1e-7).astype(np.int64)),tuple(np.rint(normals[i]/1e-5).astype(np.int64)))
  groups.setdefault(key,[]).append(i)
 chosen=[ids for ids in groups.values()if seed.intersection(ids)];rows=sorted(i for ids in chosen for i in ids)
 if len(rows)>32:raise ValueError('Declared local faces unexpectedly expand beyond32 normal rows')
 row_to_group={i:gi for gi,ids in enumerate(chosen)for i in ids};incident=np.flatnonzero(np.any(np.isin(asset.tri,rows),axis=1));tri=asset.tri[incident]
 old=np.array([normals[ids].mean(axis=0)for ids in chosen]);old/=np.linalg.norm(old,axis=1)[:,None]
 accum=np.zeros_like(rest)
 for t in asset.tri:
  normal=np.cross(rest[t[1]]-rest[t[0]],rest[t[2]]-rest[t[0]])
  for i in t:accum[i]+=normal
 desired=np.array([accum[ids].sum(axis=0)for ids in chosen]);desired/=np.linalg.norm(desired,axis=1)[:,None]
 matrices=asset.matrices(None);schedules=[]
 for fraction in [None,0,.25,.5,.75,1]:
  time=None if fraction is None else fraction*asset.duration;points,ns=asset.evaluate(time);pose_matrices=asset.matrices(time)
  normal_transform=np.linalg.inv(pose_matrices[:,:3,:3]).transpose(0,2,1)@matrices[:,:3,:3].transpose(0,2,1)
  face=np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]]);face/=np.linalg.norm(face,axis=1)[:,None]
  schedules.append((time,ns,normal_transform,face))
 def newnorm(x):return Rotation.from_rotvec(x.reshape(-1,3)).apply(old)
 def objective(x):
  n=newnorm(x);return float(np.sum((n-desired)**2)+.0001*np.sum(x*x))
 def constraints(x):
  n=newnorm(x);all_values=[]
  for time,baseline,transform,face in schedules:
   ns=baseline.copy()
   for i in rows:
    v=transform[i]@n[row_to_group[i]];ns[i]=v/np.linalg.norm(v)
   avg=ns[tri].sum(axis=1)
   all_values.extend(np.sum(avg*face,axis=1)-1e-5)
  return np.array(all_values)
 result=minimize(objective,np.zeros(len(chosen)*3),method='SLSQP',bounds=[(-np.pi,np.pi)]*(len(chosen)*3),constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':150,'ftol':1e-11})
 if not result.success or constraints(result.x).min()<-1e-7:raise ValueError('Local normal constraints infeasible; no output: '+result.message)
 final=newnorm(result.x);raw=a.source.read_bytes();patched=bytearray(raw);jlen=struct.unpack_from('<I',raw,12)[0];binary_start=28+jlen;ni=asset.prim['attributes']['NORMAL'];accessor=asset.doc['accessors'][ni];view=asset.doc['bufferViews'][accessor['bufferView']];offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
 changed=[]
 for i in rows:
  local=matrices[i,:3,:3].T@final[row_to_group[i]];local/=np.linalg.norm(local);new=struct.pack('<3f',*local);start=binary_start+offset+i*12
  if new!=raw[start:start+12]:patched[start:start+12]=new;changed.append(i)
 allowed={byte for i in changed for byte in range(binary_start+offset+i*12,binary_start+offset+i*12+12)}
 if any(old!=new and i not in allowed for i,(old,new)in enumerate(zip(raw,patched))):raise ValueError('Unrelated byte changed')
 report={'schema_version':1,'status':'bounded_local_normal_candidate_finite_constraints_passed_visual_pending','source_file':a.source.as_posix(),'source_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(patched).hexdigest(),'declared_bad_faces':a.faces,'normal_rows_changed':changed,'normal_groups':len(chosen),'adjacent_faces_checked':incident.tolist(),'finite_pose_count':len(schedules),'minimum_face_summed_normal_dot_margin':float(constraints(result.x).min()+1e-5),'max_world_normal_rotation_deg':float(np.degrees(np.arccos(np.clip(np.sum(old*final,axis=1),-1,1))).max()),'changed_position_rows':[],'changed_normal_rows':changed,'byte_proof':{'only_declared_NORMAL_rows_changed':True,'geometry_UV_skin_rest_animation_images_materials_exact':True},'solver':{'method':'SLSQP','iterations':int(result.nit),'success':bool(result.success),'objective':'Closest area-weighted geometric one-ring normals constrained to positive actual adjacent-face orientation at REST+5idle poses; small rotation regularizer'},'tool_file':str(Path(__file__).relative_to(ROOT)),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limitations':['Finite local structural normal correction; no full-mesh, actual import, visual, or AAA approval']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(patched);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'sha256':report['output_sha256'],'normal_rows':len(changed),'groups':len(chosen),'faces':len(incident),'max_rotation_deg':report['max_world_normal_rotation_deg'],'finite_margin':report['minimum_face_summed_normal_dot_margin']}))


if __name__=='__main__':main()
