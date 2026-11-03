"""Read-only actual glTF all53 local/global and reimport-LUT audit, no engine."""
from pathlib import Path
import sys,json,math,bisect,hashlib
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'tools/toolchain.json').is_file());sys.path.insert(0,str(ROOT/'tools'))
from inspect_motion_derivatives import GLB,angle
from append_character_animations import read_glb,_local_matrix

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def schedules(asset):
 keys=sorted(asset.times)
 return {'keys_and_midpoints':sorted(set(keys+[(a+b)*.5 for a,b in zip(keys,keys[1:])])),**{str(hz)+'Hz':sorted(set([i/hz for i in range(math.floor(asset.duration*hz)+1)]+[asset.duration]))for hz in [60,120]}}
def rates(asset,times):
 old=asset.pose(times[0]);report={bone:{}for bone in asset.bones}
 for first,last in zip(times,times[1:]):
  new=asset.pose(last);dt=last-first
  if dt<=1e-8:raise ValueError('Ambiguous derivative interval')
  for bone in asset.bones:
   for label,field in [('local','local_quat_xyzw'),('global','global_quat_xyzw')]:
    degrees=angle(old[bone][field],new[bone][field]);rate=degrees/dt
    if rate>report[bone].get(label,{}).get('deg_s',-1):report[bone][label]={'deg_s':rate,'degrees':degrees,'interval_s':[first,last]}
  old=new
 peak=max((row['deg_s'],bone,space,row)for bone,d in report.items()for space,row in d.items())
 return {'samples':len(times),'peak':{'bone':peak[1],'space':peak[2],**peak[3]},'bones':report,'passed':peak[0]<=2700}
def markers(path):
 d,_=read_glb(path);parents={c:i for i,n in enumerate(d['nodes'])for c in n.get('children',[])};cache={}
 def world(i):
  if i not in cache:cache[i]=(world(parents[i])if i in parents else np.eye(4))@np.array(_local_matrix(d['nodes'][i]),float)
  return cache[i]
 return {n:world(next(i for i,v in enumerate(d['nodes'])if v.get('name')==n))[:3,3]for n in ['GripOrigin','BladeTip']}
def actual_marker(asset,t,recipe,points):
 hand=asset.pose(t)['RightHand'];rotation=Rotation.from_quat(hand['global_quat_xyzw']).as_matrix();basis=np.array(recipe['weapon_socket']['basis_columns']).T;offset=np.array(recipe['weapon_socket']['offset_m']);result={}
 for n,p in points.items():
  v=rotation@(basis@p+offset)+np.array(hand['position_m']);result[n]=np.array([-v[0],v[1]+.025,-v[2]])
 return result
def lookup(curve,t,key):
 rows=curve['samples'];times=[r['time_s']for r in rows];i=max(0,min(len(rows)-2,bisect.bisect_right(times,t)-1));u=max(0,min(1,(t-times[i])/(times[i+1]-times[i])));return (1-u)*np.array(rows[i][key])+u*np.array(rows[i+1][key])
def curve_check(asset,curve,recipe,points):
 first=curve['active_start_s'];last=first+curve['active_duration_s'];times=sorted(set([t for t in schedules(asset)['keys_and_midpoints']if first-1e-7<=t<=last+1e-7]+[r['time_s']for r in curve['samples']]+[(a['time_s']+b['time_s'])*.5 for a,b in zip(curve['samples'],curve['samples'][1:])]))
 rows=[]
 for t in times:
  got=actual_marker(asset,t,recipe,points);rows.append({'time_s':t,'grip_error_m':float(np.linalg.norm(got['GripOrigin']-lookup(curve,t,'grip'))),'tip_error_m':float(np.linalg.norm(got['BladeTip']-lookup(curve,t,'tip')))})
 g=max(rows,key=lambda r:r['grip_error_m']);p=max(rows,key=lambda r:r['tip_error_m'])
 return {'samples':len(rows),'max_grip':g,'max_tip':p,'limit_m':.003,'passed':max(g['grip_error_m'],p['tip_error_m'])<=.003}
def main():
 base=ROOT/'art_source/production/candidates/lyra-continuity-001/source-006-guarded.glb';folder=Path(__file__).parent;new=folder/'source-006.glb';recipe=json.loads((folder/'recipe.json').read_text());weapon=ROOT/recipe['weapon_source']['file'];points=markers(weapon)
 # Independent socket/frame calibration against published curve before using
 # this FK oracle for the new body/trajectory.
 old_curve=json.loads((ROOT/'game/data/charged_blade_curve.json').read_text());calibration=curve_check(GLB(base,'charged_heavy'),old_curve,recipe,points)
 if not calibration['passed']:raise ValueError('Published-source raw socket calibration failed: '+str(calibration))
 output={'scope':'Raw glTF TRS/slerp all53 local/global derivatives and actual physical1.19m marker versus Blender-reimported LUT; no Godot, rendered skin, terrain, hardware or AAA approval','tool_sha256':sha(__file__),'source_sha256':sha(base),'candidate_sha256':sha(new),'published_source_socket_calibration':calibration,'clips':{}}
 for clip in ['charge','charged_heavy','heavy']:
  item={}
  for name,path in [('baseline',base),('candidate',new)]:
   asset=GLB(path,clip);item[name]={'duration_s':asset.duration,'key_count':len(asset.times),'schedules':{label:rates(asset,times)for label,times in schedules(asset).items()}}
  if clip!='charge':item['candidate_curve']=curve_check(GLB(new,clip),json.loads((folder/('source-006.'+clip+'-curve.json')).read_text()),recipe,points)
  output['clips'][clip]=item;print('RAW_CLIP',clip,json.dumps({n:{s:r['peak']for s,r in d['schedules'].items()}for n,d in item.items()if n in ['baseline','candidate']}),flush=True)
 output['passed']=all(r['passed']for c in output['clips'].values()for r in c['candidate']['schedules'].values())and all(c.get('candidate_curve',{'passed':True})['passed']for c in output['clips'].values())
 (folder/'source-006.raw-audit.json').write_text(json.dumps(output,indent=2)+'\n');print('RAW_AUDIT_PASSED',output['passed'],flush=True)
if __name__=='__main__':main()
