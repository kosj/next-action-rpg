"""Finite Hero continuity studio with the actual runtime broadblade composition.

Reuses the existing renderer in memory without editing it or old proof files.
The original weapon root/markers and PBR material remain; only its mesh data is
replaced, matching ActorVisual.apply_hero_blade_profile. Not actual gameplay.
Use isolated Blender4.3.2 and --python-exit-code1 in an assigned CPU lane.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import render_fury_review as studio
from author_continuity_actions import Raw
from append_character_animations import read_glb,_local_matrix

BASE=ROOT/'game/assets/models/production/rune_sword_web.glb'
BROAD=ROOT/'game/assets/models/production/rune_greatsword_geometry.glb'
GRIPS=ROOT/'game/data/character_grips.json'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def marker_positions(path):
 doc,_=read_glb(path);parents={c:i for i,n in enumerate(doc['nodes'])for c in n.get('children',[])};world={}
 def matrix(i):
  if i not in world:world[i]=(matrix(parents[i])if i in parents else Matrix.Identity(4))@Matrix(_local_matrix(doc['nodes'][i]))
  return world[i]
 return {name:matrix(next(i for i,n in enumerate(doc['nodes'])if n.get('name')==name)).translation for name in ['GripOrigin','BladeTip']}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True)
 p.add_argument('--clip',choices=['light_1','light_2','light_3'],required=True);p.add_argument('--times',required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--eyes',type=Path)
 p.add_argument('--size',type=int,default=640);p.add_argument('--samples',type=int,default=12)
 p.add_argument('--view',choices=['full','arms','front','opposite'],default='opposite')
 p.add_argument('--camera',type=float,nargs=3);p.add_argument('--aim',type=float,nargs=3);p.add_argument('--ortho',type=float)
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 if bpy.app.version[:3]!=(4,3,2)or not bpy.app.background:raise ValueError('Assigned isolated Blender4.3.2 required')
 if (a.camera is None)!=(a.aim is None):raise ValueError('Custom camera and aim must be supplied together')
 if not all(math.isfinite(v)for v in (a.camera or [])+(a.aim or [])):raise ValueError('Finite camera required')
 if a.ortho is not None and(not math.isfinite(a.ortho)or a.ortho<=0):raise ValueError('Positive finite ortho required')
 grip=json.loads(GRIPS.read_text())['hero'];recipe=json.loads(a.recipe.read_text())
 columns=[grip['basis_columns'][i:i+3]for i in [0,3,6]]
 if recipe['height_m']!=1.82 or recipe['weapon_socket']['basis_columns']!=columns or recipe['weapon_socket']['offset_m']!=grip['offset_m']:
  raise ValueError('Borrowed renderer recipe must exactly match the current physical Hero grip/height')
 for path in [BASE,BROAD]:
  doc,_=read_glb(path);mesh=next(n for n in doc['nodes']if n.get('name')=='CanonicalGeometry')
  if set(mesh)!={'name','mesh'}or len(doc['meshes'][mesh['mesh']]['primitives'])!=1:
   raise ValueError('Runtime composition requires identity CanonicalGeometry with one surface')
 raw=Raw(a.input);duration=max(t for _,_,times,_ in raw.clips[a.clip]for t in times)
 times=[float(t)for t in a.times.split(',')]
 if not times or any(not math.isfinite(t)or t<0 or t>duration+1e-6 for t in times):raise ValueError('Times must lie in the actual clip')
 state={};original_import=studio.imported;original_aim=studio.aim;original_argv=sys.argv
 def compose_import(path):
  objects=original_import(path)
  if Path(path).resolve()!=BASE.resolve():return objects
  original=next(o for o in objects if o.type=='MESH'and o.name.split('.')[0]=='CanonicalGeometry')
  materials=list(original.data.materials)
  if len(materials)!=1 or materials[0]is None:raise ValueError('Original single PBR material required')
  profile=original_import(BROAD);replacement=next(o for o in profile if o.type=='MESH'and o.name.split('.')[0]=='CanonicalGeometry')
  if max(abs(original.matrix_world[r][c]-replacement.matrix_world[r][c])for r in range(4)for c in range(4))>1e-6:
   raise ValueError('Original/replacement geometry frames differ')
  geometry=replacement.data.copy();geometry.materials.clear();geometry.materials.append(materials[0])
  if any(poly.material_index!=0 for poly in geometry.polygons):raise ValueError('Multiple replacement surfaces unsupported')
  original.data=geometry
  if list(original.data.materials)!=materials:raise ValueError('Original PBR reference was not preserved')
  state.update(composed=True,material_names=[m.name for m in materials],material_reference_preserved=True,mesh_vertices=len(geometry.vertices),mesh_polygons=len(geometry.polygons))
  for obj in sorted(profile,key=studio.depth,reverse=True):bpy.data.objects.remove(obj,do_unlink=True)
  return objects
 def aim(obj,target):
  if obj.type=='CAMERA':
   if a.camera is not None:obj.location=Vector(a.camera);target=Vector(a.aim)
   if a.ortho is not None:obj.data.ortho_scale=a.ortho
  return original_aim(obj,target)
 delegated=['--input',str(a.input),'--recipe',str(a.recipe),'--clip',a.clip,'--times',a.times,'--output',str(a.output),'--weapon',str(BASE),'--size',str(a.size),'--samples',str(a.samples),'--view',a.view]
 if a.eyes is not None:delegated+=['--eyes',str(a.eyes)]
 try:
  studio.imported=compose_import;studio.aim=aim;sys.argv=[original_argv[0],'--',*delegated]
  studio.main()
 finally:studio.imported=original_import;studio.aim=original_aim;sys.argv=original_argv
 if not state.get('composed'):raise ValueError('Actual Hero broadblade composition did not occur')
 review=json.loads((a.output/'review.json').read_text());markers=marker_positions(BASE);rows=[]
 for shot in review['shots']:
  _,world=raw.at(a.clip,shot['time_s']);hand=world[raw.names['RightHand']];scale=hand.to_scale().x
  socket=Matrix(columns).transposed().to_4x4();socket.translation=Vector(grip['offset_m'])
  for r in range(3):
   for c in range(4):socket[r][c]/=scale
  frame=hand@socket;row={'time_s':shot['time_s']}
  for name,key in [('GripOrigin','grip'),('BladeTip','tip')]:
   point=frame@markers[name];expected=Vector((point.x,-point.z,point.y));actual=Vector(shot['actual_weapon_'+key+'_m'])
   row[key+'_expected_blender_m']=list(expected);row[key+'_actual_blender_m']=list(actual);row[key+'_error_m']=(actual-expected).length
  rows.append(row)
 report={'schema_version':1,'scope':'Actual base root/markers/PBR material plus actual runtime Hero broadblade mesh replacement in neutral Blender studio. Finite stills and raw marker calibration only; not actual Game camera, gameplay, continuous AV, hardware or AAA approval.',
         'helper_sha256':sha(__file__),'borrowed_renderer_sha256':sha(Path(studio.__file__)),'raw_fk_helper_sha256':sha(ROOT/'tools/author_continuity_actions.py'),
         'source_sha256':sha(a.input),'weapon_base_sha256':sha(BASE),'actual_weapon_geometry_sha256':sha(BROAD),'runtime_grip_sha256':sha(GRIPS),
         'runtime_composition_reference':'game/scripts/actors/actor_visual.gd:apply_hero_blade_profile','runtime_composition_source_sha256':sha(ROOT/'game/scripts/actors/actor_visual.gd'),
         'composition':state,'studio_coordinate_system':'Blender point=[source_glTF_x,-source_glTF_z,source_glTF_y]; pre-gameplay-PI/floor studio, distances/relative composition unchanged',
         'camera_override':a.camera,'aim_override':a.aim,'ortho_override_m':a.ortho,'captured_camera_matrix':review['camera_matrix'],
         'raw_marker_limit_m':.003,'maximum_grip_error_m':max(x['grip_error_m']for x in rows),'maximum_tip_error_m':max(x['tip_error_m']for x in rows),'raw_marker_samples':rows,
         'original_base_report':'review.json','shots':review['shots']}
 report['raw_markers_passed']=report['maximum_grip_error_m']<=.003 and report['maximum_tip_error_m']<=.003
 (a.output/'continuity-composition.json').write_text(json.dumps(report,indent=2)+'\n')
 if not report['raw_markers_passed']:raise ValueError('Actual imported studio markers exceed existing3mm source-frame contract')
 print('RUNEFALL_CONTINUITY_STUDIO',a.output,flush=True)

if __name__=='__main__':main()
