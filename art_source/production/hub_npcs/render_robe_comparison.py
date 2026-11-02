"""Six matched original/candidate studio stills; no model, material or motion writes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from render_glb_review import asset_bounds,configure_scene,neutral_floor,area_light,aim


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--candidate',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 if bpy.app.version[:3]!=(4,3,2)or not bpy.app.background:raise ValueError('Blender4.3.2 background required')
 if a.output.exists():raise ValueError('No review overwrite')
 a.output.mkdir(parents=True);views=[];fixed=None;sources=[]
 for role,path in [('original',a.source),('candidate',a.candidate)]:
  sourcehash=hashlib.sha256(path.read_bytes()).hexdigest();sources.append({'role':role,'file':path.as_posix(),'sha256':sourcehash})
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(path),import_pack_images=True)
  objects=list(bpy.context.scene.objects);rig=next(o for o in objects if o.type=='ARMATURE');helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape}
  for obj in helpers:obj.hide_render=True
  objects=[o for o in objects if o not in helpers];idle=next(act for act in bpy.data.actions if act.frame_range[1]-act.frame_range[0]>30)
  for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
  rig.animation_data.action=idle;rig.data.pose_position='REST';bpy.context.view_layer.update()
  lower,upper,size,center,corners=asset_bounds(objects,bpy.context.evaluated_depsgraph_get());span=max(size)
  if fixed is None:fixed={'center':center.copy(),'span':span,'scale':max(size.z,size.x)*1.16}
  else:
   if (fixed['center']-center).length>1e-6 or abs(fixed['span']-span)>1e-6:raise ValueError('Unexpected whole-body bounds change')
  center=fixed['center'];span=fixed['span'];scene=configure_scene(640,12);neutral_floor(center,0,span)
  direction=Vector((.65,1,0)).normalized();right=Vector((0,0,1)).cross(direction).normalized()
  camdata=bpy.data.cameras.new('MatchedCamera');camdata.type='ORTHO';camera=bpy.data.objects.new('MatchedCamera',camdata);scene.collection.objects.link(camera);scene.camera=camera
  for name,power,scale,offset in [('Key',500,1.5,(-1.5,2.2,2.3)),('Fill',250,2,(2,1.5,1.2)),('Rim',650,1.2,(0,-2,2))]:
   light=area_light(name,power*span*span,scale*span);light.location=center+right*offset[0]*span+direction*offset[1]*span+Vector((0,0,offset[2]*span));aim(light,center)
  rig.data.pose_position='POSE'
  for name,fraction,look,scale in [('full-idle0',0,center,fixed['scale']),('close-idle0',0,Vector((.22,.12,.50)),.43),('close-idle-mid',.5,Vector((.22,.12,.50)),.43)]:
   frame=idle.frame_range[0]+fraction*(idle.frame_range[1]-idle.frame_range[0]);scene.frame_set(int(frame),subframe=frame-int(frame));camera.location=look+direction*span*4;aim(camera,look);camdata.ortho_scale=scale
   filename=role+'-'+name+'.png';scene.render.filepath=str(a.output/filename);bpy.ops.render.render(write_still=True)
   views.append({'role':role,'file':filename,'idle_fraction':fraction,'time_s':frame/30,'camera_blender':list(camera.location),'look_at_blender':list(look),'orthographic_scale':scale,'image_sha256':hashlib.sha256((a.output/filename).read_bytes()).hexdigest()})
  if hashlib.sha256(path.read_bytes()).hexdigest()!=sourcehash:raise ValueError('Input mutated during review')
 report={'schema_version':1,'status':'six_matched_studio_rasters_for_human_review','automatic_visual_approval':False,'blender':bpy.app.version_string,'samples':12,'resolution':[640,640],'sources':sources,'views':views,'tool_file':str(Path(__file__).relative_to(ROOT)),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'match_contract':'Identical original-derived camera bounds, materials, images, lighting, samples, seed, idle times and projection. Only bounded candidate POSITION/NORMAL bytes differ.','limitations':['Three finite pose/view pairs do not establish continuous idle, cloth/foot contact, actual game, hardware, or AAA quality']}
 (a.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
