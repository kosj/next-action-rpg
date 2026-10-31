"""Render actual reimported impact clips with the runtime sword/socket contract.

These are fixed neutral Blender studio captures, not actual Godot gameplay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from render_glb_review import configure_scene, neutral_floor, area_light, aim


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def imported(path):
    old=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path),import_pack_images=True)
    result=[o for o in bpy.context.scene.objects if o not in old]
    helpers={b.custom_shape for o in result if o.type=='ARMATURE' for b in o.pose.bones if b.custom_shape}
    for helper in helpers:helper.hide_render=True
    return [o for o in result if o not in helpers]


def depth(obj):
    result=0
    while obj.parent:
        result+=1;obj=obj.parent
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--clip',required=True)
    p.add_argument('--times',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--weapon',type=Path,default=Path('game/assets/models/production/rune_sword_web.glb'))
    p.add_argument('--eyes',type=Path)
    p.add_argument('--size',type=int,default=640)
    p.add_argument('--samples',type=int,default=12)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version[:3]!=(4,3,2) or not bpy.app.background:raise ValueError('Use isolated Blender4.3.2')
    if args.output.exists() and any(args.output.iterdir()):raise ValueError('New empty review directory required')
    args.output.mkdir(parents=True,exist_ok=True)
    recipe=json.loads(args.recipe.read_text());times=[float(t) for t in args.times.split(',')]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=100
    body=imported(args.input)
    rig=next(o for o in body if o.type=='ARMATURE')
    actions=[a for a in bpy.data.actions if a.name==args.clip or a.name.startswith(args.clip+'_')]
    if len(actions)!=1:raise ValueError('Ambiguous imported clip '+args.clip+': '+str([a.name for a in bpy.data.actions]))
    action=actions[0];start=float(action.frame_range[0])
    for obj in body:obj.animation_data_clear()
    rig.animation_data_create();rig.animation_data.action=action
    actor=bpy.data.objects.new('_ActorTranslation',None);bpy.context.scene.collection.objects.link(actor)
    for obj in body:
        if obj.parent is None:
            original=obj.matrix_world.copy();obj.parent=actor;obj.matrix_world=original
    weapon=imported(args.weapon)
    weapon_world={o:o.matrix_world.copy() for o in weapon}
    eyes=imported(args.eyes) if args.eyes else []
    eye_world={o:o.matrix_world.copy() for o in eyes}
    inverse_yup=Matrix.Rotation(-math.pi/2,4,'X')
    scene=configure_scene(args.size,args.samples)
    scene.render.threads=1
    scene.render.resolution_x=args.size;scene.render.resolution_y=args.size
    neutral_floor(Vector((0,-.3,1)),0,3.5)
    key=area_light('_Key',650,4);key.location=(3,-4,5);aim(key,Vector((0,0,1)))
    fill=area_light('_Fill',350,3);fill.location=(-3,-1,3);aim(fill,Vector((0,0,1)))
    rim=area_light('_Rim',500,3);rim.location=(1,3,4);aim(rim,Vector((0,0,1)))
    data=bpy.data.cameras.new('_ImpactReviewCamera');camera=bpy.data.objects.new('_ImpactReviewCamera',data)
    scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.ortho_scale=3.5
    camera.location=(4.5,-7,3.6);aim(camera,Vector((0,-.2,1.25)))
    ratio=recipe['height_m']/1.82
    socket=Matrix(recipe['weapon_socket']['basis_columns']).transposed().to_4x4()
    socket.translation=Vector(recipe['weapon_socket']['offset_m'])*ratio
    scale=rig.matrix_world.to_scale().x
    socket.translation/=scale
    compensation=Matrix.Diagonal((1/scale,1/scale,1/scale,1))
    records=[]
    for time in times:
        scene.frame_set(math.floor(start+time*100),subframe=(start+time*100)%1)
        travel=3.2*max(0,min(.18,time-.34)) if args.clip=='charged_heavy' else 0
        actor.location.y=-travel
        bpy.context.view_layer.update()
        grip=rig.matrix_world@rig.pose.bones['RightHand'].matrix@socket@compensation
        for obj in sorted(weapon,key=depth):obj.matrix_world=grip@inverse_yup@weapon_world[obj]
        if eyes:
            head=rig.matrix_world@rig.pose.bones['Head'].matrix
            rigid=Matrix.LocRotScale(head.translation,head.to_quaternion(),Vector((1,1,1)))
            for obj in sorted(eyes,key=depth):obj.matrix_world=rigid@inverse_yup@eye_world[obj]
        bpy.context.view_layer.update()
        file=args.output/(args.clip+'-'+str(round(time*1000)).zfill(4)+'.png')
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        marker_grip=next((o for o in weapon if o.name.split('.')[0]=='GripOrigin'),None)
        marker_tip=next((o for o in weapon if o.name.split('.')[0]=='BladeTip'),None)
        records.append({'time_s':time,'file':file.name,'sha256':digest(file),'virtual_actor_travel_m':travel,
            'actual_weapon_grip_m':list(marker_grip.matrix_world.translation) if marker_grip else None,
            'actual_weapon_tip_m':list(marker_tip.matrix_world.translation) if marker_tip else None})
    report={'scope':'Actual new GLB reimport with its original body/materials, runtime sword and physical socket; neutral fixed Blender studio, not gameplay/AAA approval.',
        'input':str(args.input),'input_sha256':digest(args.input),'weapon':str(args.weapon),'weapon_sha256':digest(args.weapon),
        'eyes_sha256':digest(args.eyes) if args.eyes else None,'blender':bpy.app.version_string,
        'clip':args.clip,'imported_action':action.name,'frame_start':start,'sample_hz':100,
        'camera_matrix':[list(row) for row in camera.matrix_world],'orthographic_scale':data.ortho_scale,'shots':records}
    (args.output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('RUNEFALL_IMPACT_REVIEW',args.output,flush=True)


if __name__=='__main__':main()
