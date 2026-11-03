from pathlib import Path
import sys,json,math,hashlib
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'tools/toolchain.json').is_file());f=ROOT/'art_source/production/candidates/lyra-decisive-001';sys.path.insert(0,str(f));from audit_raw import GLB,angle,markers,actual_marker
base=ROOT/'art_source/production/candidates/lyra-continuity-001/source-006-guarded.glb';new=f/'source-006.glb';recipe=json.loads((f/'recipe.json').read_text());points=markers(ROOT/recipe['weapon_source']['file']);rows=[]
for clip,times in {'charge':[0,.325,.65],'charged_heavy':[0,.262,.34,.43,.52,.60,1.06],'heavy':[0,.24,.32,.43,.54,.70,.86]}.items():
 a,b=GLB(base,clip),GLB(new,clip)
 for t in times:
  old,newpose=a.pose(t),b.pose(t);m={'clip':clip,'time_s':t,'baseline':{},'candidate':{},'changes':{}}
  for role,p,asset in [('baseline',old,a),('candidate',newpose,b)]:
   for bone in ['Hips','Spine2','LeftShoulder','RightShoulder','LeftForeArm','RightForeArm','LeftHand','RightHand','LeftLeg','RightLeg']:
    v=p[bone]['position_m'];m[role][bone]={'actor_position_m':[-v[0],v[1]+.025,-v[2]],'world_quaternion_xyzw':p[bone]['global_quat_xyzw']}
   m[role]['actual_weapon']={n:v.tolist()for n,v in actual_marker(asset,t,recipe,points).items()}
  for bone in ['Hips','Spine2','LeftShoulder','RightShoulder','LeftForeArm','RightForeArm']:
   m['changes'][bone]={'global_position_delta_m':math.dist(old[bone]['position_m'],newpose[bone]['position_m']),'height_delta_m':newpose[bone]['position_m'][1]-old[bone]['position_m'][1],'global_rotation_delta_deg':angle(old[bone]['global_quat_xyzw'],newpose[bone]['global_quat_xyzw'])}
  rows.append(m)
report={'scope':'Actual raw glTF pose/physical blade comparison at finite times, independently calibrated socket; actorPI/floor applied. No visual/terrain/AAA approval','source_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'samples':rows};(f/'source-006.pose-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:
 if(r['clip']=='charge'and r['time_s']==.65)or(r['clip']=='heavy'and r['time_s']==.32)or(r['clip']=='charged_heavy'and r['time_s']in [.262,.43,.60]):print(r['clip'],r['time_s'],'hips',r['changes']['Hips'],'chest',r['changes']['Spine2'],'old/new blade G/T height',[r[x]['actual_weapon'][n][1]for x in ['baseline','candidate']for n in ['GripOrigin','BladeTip']])
