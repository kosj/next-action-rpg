from pathlib import Path
import json,sys,bisect,math,hashlib,argparse
import numpy as np
sys.path.insert(0,str(Path.cwd()/'tools'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from skin_lbs_audit import skin_for
from append_character_animations import read_glb
parser=argparse.ArgumentParser(description='Calibrate actual production socket/scale/marker against charged LUT');parser.add_argument('--body',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=Path.cwd();body=args.body.resolve(strict=True);weapon=root/'game/assets/models/production/rune_greatsword_geometry.glb';lutpath=root/'game/data/charged_blade_curve.json';lut=json.loads(lutpath.read_text());s=skin_for(body,0);right=s.names.index('RightHand');ibm_inverse=np.linalg.inv(s.inverse_binds[right]);grip=json.loads((root/'game/data/character_grips.json').read_text())['hero'];basis=np.array(grip['basis_columns']).reshape(3,3).T;offset=np.array(grip['offset_m']);weapon_doc,_=read_glb(weapon);markers={name:np.array(next(n for n in weapon_doc['nodes']if n.get('name')==name).get('translation',[0,0,0]),float)for name in ['GripOrigin','BladeTip']}
rawtimes=np.unique(np.concatenate([s.accessor(x['input']).ravel()for x in s.animations['charged_heavy']['samplers']]));rawtimes=rawtimes[(rawtimes>=.34-1e-7)&(rawtimes<=.52+1e-7)];times=sorted(set(map(float,rawtimes))|set(map(float,(rawtimes[:-1]+rawtimes[1:])*.5))|{x['time_s']for x in lut['samples']}|{(a['time_s']+b['time_s'])*.5 for a,b in zip(lut['samples'],lut['samples'][1:])});merged=[]
for t in times:
 if not merged or t-merged[-1]>1e-7:merged.append(t)
kt=[x['time_s']for x in lut['samples']]
def expected(t,key):
 j=max(0,min(len(kt)-2,bisect.bisect_right(kt,t)-1));u=max(0,min(1,(t-kt[j])/(kt[j+1]-kt[j])));return (1-u)*np.array(lut['samples'][j][key])+u*np.array(lut['samples'][j+1][key])
rows=[]
for t in merged:
 matrix=s.transforms('charged_heavy',t)[right]@ibm_inverse;scale=np.linalg.norm(matrix[:3,0]);socket=np.eye(4);socket[:3,:3]=basis/scale;socket[:3,3]=offset/scale;frame=matrix@socket;record={'time_s':t,'inherited_rig_scale':float(scale)}
 for marker,key in [('GripOrigin','grip'),('BladeTip','tip')]:
  raw=frame[:3,:3]@markers[marker]+frame[:3,3];actor=np.array([-raw[0],raw[1]+.025,-raw[2]]);want=expected(t,key);record[key+'_actor_m']=actor.tolist();record[key+'_lut_m']=want.tolist();record[key+'_error_m']=float(np.linalg.norm(actor-want))
 rows.append(record)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();result={'schema_version':1,'scope':'Independent actual LBS worldJoint*inverseBind inversion recovers hand frame; production grip+uniform-scale cancellation and actual broadblade GripOrigin/BladeTip are compared to the unchanged sourcebound charged91point LUT at every actual active key and midpoint plus LUT keys/midpoints. No engine/native or visual approval is claimed.','audit_script_sha256':sha(__file__),'skin_helper_sha256':sha(Path(__file__).parent/'skin_lbs_audit.py'),'candidate_sha256':sha(body),'geometry_sha256':sha(weapon),'runtime_grip_sha256':sha(root/'game/data/character_grips.json'),'lut_sha256':sha(lutpath),'lut_source_sha256':lut['source_metadata']['sha256'],'source_clip_policy':'charged_heavy dictionary/sourceBIN/static hierarchy are preserved exactly from LUT original f2ed; full GLB source pin remains old until adoption.','floor_offset_m':.025,'position_conversion':'[-raw_x,raw_y+.025,-raw_z]','marker_length_m':float(np.linalg.norm(markers['BladeTip']-markers['GripOrigin'])),'key_and_midpoint_samples':len(rows),'maximum_grip_error_m':max(x['grip_error_m']for x in rows),'maximum_tip_error_m':max(x['tip_error_m']for x in rows),'limit_m':.003,'samples':rows};result['passed']=result['maximum_grip_error_m']<=.003 and result['maximum_tip_error_m']<=.003;args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='samples'}))
