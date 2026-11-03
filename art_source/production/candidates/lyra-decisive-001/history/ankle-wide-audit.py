"""Actual raw LBS front-sole nominal active plant; no terrain/physics IK claim."""
from pathlib import Path
import json,hashlib,math,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_skin import skin_for,posed_region
FOLDER=Path(__file__).resolve().parent
p=FOLDER/'source-006.glb';recipe=json.loads((FOLDER/'recipe.json').read_text());reports=[]
for primitive in range(2):
 s=skin_for(p,primitive);rest=posed_region(s,None,0,np.arange(len(s.positions)));floor=rest[:,1].min();footweight=np.array([sum(w for j,w in zip(js,ws)if s.names[j]in ['LeftFoot','LeftToeBase'])for js,ws in zip(s.joints,s.weights)]);indices=np.flatnonzero((footweight>.5)&(rest[:,1]<.04))
 if not len(indices):continue
 for clip in ['charged_heavy','heavy']:
  c=recipe['attacks'][clip];start=c['startup_s'];end=start+c['active_s'];times=np.unique(np.concatenate([s.accessor(v['input']).ravel()for v in s.animations[clip]['samplers']]));times=np.unique(np.r_[times,(times[:-1]+times[1:])*.5,start,end]);times=times[(times>=start-1e-7)&(times<=end+1e-7)];anchor=posed_region(s,clip,start,indices);maximum=0.;worst=None
  for t in times:
   points=posed_region(s,clip,float(t),indices)+np.array([0,0,3.2*max(0,min(c['active_s'],t-start))]);errors=np.linalg.norm(points-anchor,axis=1);index=int(errors.argmax())
   if errors[index]>maximum:maximum=float(errors[index]);worst={'time_s':float(t),'vertex_index':int(indices[index]),'anchor_raw_gltf_m':anchor[index].tolist(),'nominal_world_raw_gltf_m':points[index].tolist()}
  reports.append({'primitive':primitive,'clip':clip,'samples':len(times),'front_sole_vertices':len(indices),'selection':'Actual static skin LeftFoot/LeftToeBase summed weight>.5, restY<.04m; no mesh/weight edits','maximum_nominal_active_drift_m':maximum,'worst':worst,'limit_m':.01,'passed':maximum<=.01})
output={'scope':'Actual raw glTF LBS at all active keys/midpoints plus exact boundaries; nominal collision-free root movement3.2m/s. Supporting front foot only; rear foot intentionally catch-steps. Not real controller collisions, dynamic foot IK, terrain, visual or AAA acceptance.','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'reports':reports,'passed':bool(reports)and all(r['passed']for r in reports)};(FOLDER/'source-006.foot-audit.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output))
