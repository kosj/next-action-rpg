"""Bounded actual derivative NPC review; finite studio poses are not game/AAA approval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from render_glb_review import asset_bounds,configure_scene,neutral_floor,area_light,aim


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 if bpy.app.version[:3]!=(4,3,2) or not bpy.app.background:raise ValueError('Blender4.3.2 background required')
 if a.output.exists():raise ValueError('Refuse to overwrite review')
 a.output.mkdir(parents=True)
 sourcehash=hashlib.sha256(a.input.read_bytes()).hexdigest()
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
 bpy.ops.import_scene.gltf(filepath=str(a.input),import_pack_images=True)
 objects=list(bpy.context.scene.objects);rigs=[o for o in objects if o.type=='ARMATURE'];assert len(rigs)==1
 rig=rigs[0];helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape}
 for obj in helpers:obj.hide_render=True
 objects=[o for o in objects if o not in helpers]
 actions=[act for act in bpy.data.actions if act.frame_range[1]-act.frame_range[0]>30]
 assert len(actions)==1;idle=actions[0]
 rig.animation_data_create()
 for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
 rig.data.pose_position='REST';bpy.context.view_layer.update()
 lower,upper,size,center,corners=asset_bounds(objects,bpy.context.evaluated_depsgraph_get());span=max(size)
 scene=configure_scene(640,8);neutral_floor(center,0,span)
 camera_data=bpy.data.cameras.new('NPCReviewCamera');camera_data.type='ORTHO';camera_data.ortho_scale=max(size.z,size.x)*1.16
 camera=bpy.data.objects.new('NPCReviewCamera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
 lights=[area_light('NPCKey',500*span*span,span*1.5),area_light('NPCFill',250*span*span,span*2),area_light('NPCRim',650*span*span,span*1.2)]
 views=[]
 for name,rest,fraction,direction in [('rest-front',True,0,Vector((0,1,0))),('idle-quarter-start',False,0,Vector((.65,1,0)).normalized()),('idle-quarter-mid',False,.5,Vector((.65,1,0)).normalized())]:
  rig.data.pose_position='REST' if rest else 'POSE';rig.animation_data.action=idle
  frame=idle.frame_range[0]+fraction*(idle.frame_range[1]-idle.frame_range[0]);scene.frame_set(int(frame),subframe=frame-int(frame))
  camera.location=center+direction*span*4;aim(camera,center)
  right=Vector((0,0,1)).cross(direction).normalized()
  for light,offset in zip(lights,[(-1.5,2.2,2.3),(2,1.5,1.2),(0,-2,2)]):
   light.location=center+right*offset[0]*span+direction*offset[1]*span+Vector((0,0,offset[2]*span));aim(light,center)
  scene.render.filepath=str(a.output/(name+'.png'));bpy.ops.render.render(write_still=True)
  views.append({'file':name+'.png','rest':rest,'idle_fraction':None if rest else fraction,'time_s':None if rest else frame/30,'camera_blender':list(camera.location),'look_at_blender':list(center),'orthographic_scale':camera_data.ortho_scale})
 assert hashlib.sha256(a.input.read_bytes()).hexdigest()==sourcehash
 (a.output/'review.json').write_text(json.dumps({'schema_version':1,'source_file':str(a.input),'source_sha256':sourcehash,'status':'finite_studio_rasters_for_human_review','blender':bpy.app.version_string,'samples':8,'resolution':[640,640],'views':views,'limitations':['Three finite studio poses only','No actual-game continuous idle/cloth/hardware/AAA approval']},indent=2)+'\n')


if __name__=='__main__':main()
