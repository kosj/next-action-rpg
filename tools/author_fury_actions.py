"""Author a body-led descending greatsword stroke and export its actual blade LUT.

Blender4.3.2 only. Published geometry, bind skeleton, materials and unrelated
clips are preserved by raw GLB graft. This does not approve AAA motion quality.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Matrix,Quaternion,Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_character_actions import Author,PoseRig,frame_matrix,interpolate_transform,key_action,smooth,world_transform,skin_coordinates
from author_weight_actions import WeightAuthor,actual_clip_semantics,semantic_comparison,shortest_rotation_degrees
from author_sentinel_recovery import pose_at,compare
from append_character_animations import append_animations,read_glb,_local_matrix
from audit_impact_curve import multiply
from character_gait import _sole_samples,_sample_soles


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ramp(t,a,b):return smooth((t-a)/(b-a))


class FuryAuthor(Author):
    feet=WeightAuthor.feet
    travel=staticmethod(WeightAuthor.travel)

    def __init__(self,rig,recipe):
        super().__init__(rig,recipe)
        self.reach_issues=[];self.arm_metrics=[];self.loading=0
        self.minimum_pole_margin=float('inf');self.minimum_hand_distance=float('inf')
        self.minimum_twist_denominator=1.0
        self.previous_axial={}
        self.pose.limb=self.limb

    def limb(self,upper,lower,end,target,pole,end_rotation):
        if upper not in ('LeftArm','RightArm'):
            return PoseRig.limb(self.pose,upper,lower,end,target,pole,end_rotation)
        start=self.pose.matrix(upper).translation.copy();delta=target-start;distance=delta.length
        maximum=self.pose.length[upper]+self.pose.length[lower]-.0001
        self.minimum_hand_distance=min(self.minimum_hand_distance,distance)
        if distance>maximum:
            self.reach_issues.append({'time_s':self.current_time,'action':self.current_action,'bone':upper,'distance_m':distance,'maximum_m':maximum})
        direction=delta.normalized();side=-1 if upper=='RightArm' else 1
        chest=self.pose.matrix('Spine2').to_quaternion()@self.pose.rest_world['Spine2'].to_quaternion().inverted()
        anatomical=chest@Vector((side*.46,-.16,-.36))
        old=pole-start;old-=direction*old.dot(direction)
        new=anatomical-direction*anatomical.dot(direction)
        if new.length<.04*self.ratio:raise ValueError('Anatomical elbow plane approaches singularity')
        self.minimum_pole_margin=min(self.minimum_pole_margin,new.length)
        plane=old.normalized().lerp(new.normalized(),self.loading)
        if plane.length<.05:raise ValueError('Elbow-plane interpolation approaches cancellation')
        # Use the source-idle solver at zero load. The anatomical plane moves
        # continuously with the chest and avoids a fixed world-space pole.
        PoseRig.limb(self.pose,upper,lower,end,target,start+plane.normalized()*self.ratio,end_rotation)
        matrices={name:self.pose.matrix(name).copy() for name in [upper,lower,end]}
        hand_rest=self.pose.rest_world[end].to_quaternion()
        for bone,fraction in [(upper,.30),(lower,.85)]:
            matrix=matrices[bone];basis=matrix.to_3x3().normalized();axis=basis.col[1].normalized();x=basis.col[0].normalized()
            relation=self.pose.rest_world[bone].to_quaternion().inverted()@hand_rest
            desired=end_rotation@relation.inverted()
            # Closest axial twist uses the whole relative quaternion rather
            # than projecting one palm axis (which can align with the link).
            relative=desired@matrix.to_quaternion().inverted()
            projection=axis.dot(Vector((relative.x,relative.y,relative.z)))
            denominator=math.hypot(relative.w,projection)
            if self.loading>1e-6:self.minimum_twist_denominator=min(self.minimum_twist_denominator,denominator)
            if denominator<.02 and self.loading>1e-6:raise ValueError('Axial twist ambiguity '+str((self.current_action,self.current_time,bone)))
            angle=2*math.atan2(projection,relative.w)
            angle=(angle+math.pi)%(2*math.pi)-math.pi
            # Offline authoring walks each clip in increasing time; unwrap
            # this axial scalar so a principal-angle ±PI cut never changes
            # the distributed partial twist. Runtime only reads baked poses.
            previous=self.previous_axial.get(bone,angle)
            angle+=round((previous-angle)/(2*math.pi))*2*math.pi
            self.previous_axial[bone]=angle
            self.arm_metrics.append({'bone':bone,'time_s':self.current_time,'action':self.current_action,'axial_angle_deg':math.degrees(angle),'loading':self.loading})
            twist=Quaternion(axis,angle*fraction*self.loading)
            rotation=twist@matrix.to_quaternion()
            self.pose.set_world(bone,world_transform(matrix.translation,rotation,self.pose.scale))
        self.pose.set_world(end,world_transform(target,end_rotation,self.pose.scale))

    def pose_slice(self,name,t,duration):
        self.current_action=name;self.current_time=t;self.pose.reset()
        guard=self.guard;baseline=guard['pelvis_drop_m']*self.ratio
        if name=='charge':
            loaded=smooth(t/.65);coil=0;pelvis=0;torso=0;recover=0
            self.loading=loaded
            drop=baseline+.13*self.ratio*loaded;yaw=math.radians(-6-34*loaded)
            chest_yaw=math.radians(-6-24*loaded);lean=math.radians(5+3*loaded)
            shift=Vector((-.025,.035,0))*self.ratio*loaded
        elif name=='charged_heavy':
            loaded=1;coil=ramp(t,0,.22);pelvis=ramp(t,.23,.45);torso=ramp(t,.28,.50);recover=ramp(t,.64,1.06)
            self.loading=1-recover
            settle=ramp(t,.52,.63)
            drop=baseline+self.ratio*(.13+.025*coil-.065*pelvis+.055*settle)*(1-recover)
            yaw=math.radians((-40-6*coil+82*pelvis)*(1-recover)-6*recover)
            chest_yaw=math.radians((-30-5*coil+67*torso)*(1-recover)-6*recover)
            lean=math.radians(8+8*torso)*(1-recover)+math.radians(5)*recover
            shift=Vector((-.025+.05*pelvis,.035*(1-pelvis),0))*self.ratio*(1-recover)
        else:raise ValueError('Fury authors only charge and charged_heavy')
        self.body(drop,yaw,lean)
        hip=self.pose.matrix('Hips').copy();hip.translation+=shift;self.pose.set_world('Hips',hip)
        for bone,weight in [('Spine',.20),('Spine1',.25),('Spine2',.25)]:
            self.pose.local_rotation(bone,Quaternion((0,1,0),chest_yaw*weight)@Quaternion((1,0,0),lean*weight))
        chest_delta=self.pose.matrix('Spine2').to_quaternion()@self.pose.rest_world['Spine2'].to_quaternion().inverted()
        chest_position=self.pose.matrix('Spine2').translation
        def relative(position,az,pitch):
            matrix=frame_matrix(Vector(position)*self.ratio,math.radians(az),math.radians(pitch))
            return world_transform(chest_position+chest_delta@matrix.translation,chest_delta@matrix.to_quaternion(),1)
        loaded_grip=relative((-.12,-.28,.19),-25,63)
        if name=='charge':grip=interpolate_transform(self.guard_grip(),loaded_grip,loaded)
        else:
            if t<.22:grip=interpolate_transform(loaded_grip,relative((-.14,-.27,.22),-30,68),coil)
            elif t<.34:grip=interpolate_transform(relative((-.14,-.27,.22),-30,68),relative((-.26,-.30,.14),-45,55),ramp(t,.22,.34))
            elif t<=.52:
                f=smooth((t-.34)/.18)
                position=Vector((-.26,-.30,.14)).lerp(Vector((.02,-.26,0)),f)
                grip=relative(position,-45+70*f,55-85*f)
            else:
                follow=ramp(t,.52,.64)
                end=relative((.02,-.26,0),25,-30)
                through=relative((.015,-.24,-.025),31,-30)
                grip=interpolate_transform(end,through,follow)
                grip=interpolate_transform(grip,self.guard_grip(),recover)
        self.feet(t,name=='charged_heavy');self.fingers();self.arms(grip,0)
        self.pose.apply()
        local_left=self.k_left.copy();local_left.translation/=self.pose.scale
        left_actual=self.pose.matrix('LeftHand')@local_left@Matrix.Diagonal((1/self.pose.scale,1/self.pose.scale,1/self.pose.scale,1))
        expected=grip@Vector((0,self.socket['left_grasp_blade_axis_m']*self.ratio,0))
        return {**self.frame_metrics,'left_support_error_m':(left_actual.translation-expected).length,
            'virtual_actor_forward_m':self.travel(t) if name=='charged_heavy' else 0,
            'pelvis_drop_m':drop,'hips_world_m':list(self.pose.matrix('Hips').translation),
            'chest_world_m':list(self.pose.matrix('Spine2').translation),'loading':self.loading,
            'full_body_local':self.pose.values()}


def sword_markers(path):
    document,binary=read_glb(path);parents={c:i for i,n in enumerate(document['nodes']) for c in n.get('children',[])}
    def matrix(i):
        local=_local_matrix(document['nodes'][i]);return multiply(matrix(parents[i]),local) if i in parents else local
    result={}
    for i,node in enumerate(document['nodes']):
        if node.get('name') in ('GripOrigin','BladeTip'):result[node['name']]=Vector([matrix(i)[r][3] for r in range(3)])
    if set(result)!=set(['GripOrigin','BladeTip']):raise ValueError('Missing actual sword marker')
    return result


def extract_curve(rig,recipe,weapon,output):
    matches=[a for a in bpy.data.actions if a.name=='charged_heavy' or a.name.startswith('charged_heavy_')]
    if len(matches)!=1:raise ValueError('Ambiguous imported charged action')
    rig.animation_data.action=matches[0];start=float(matches[0].frame_range[0])
    fps=recipe['fps'];socket=Matrix(recipe['weapon_socket']['basis_columns']).transposed().to_4x4()
    socket.translation=Vector(recipe['weapon_socket']['offset_m']);scale=rig.matrix_world.to_scale().x;socket.translation/=scale
    compensation=Matrix.Diagonal((1/scale,1/scale,1/scale,1));markers=sword_markers(weapon);samples=[]
    for i in range(91):
        time=.34+i*.002;frame=start+time*fps;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        grip=rig.matrix_world@rig.pose.bones['RightHand'].matrix@socket@compensation
        def actor(point):
            v=grip@point;return [-v.x,v.z+.025,v.y]
        samples.append({'time_s':round(time,6),'grip':actor(markers['GripOrigin']),'tip':actor(markers['BladeTip'])})
    if max(abs(math.dist(s['grip'],s['tip'])-1.19) for s in samples)>.0001:raise ValueError('Actual blade length differs from contract')
    return {'schema_version':1,'coordinate_system':'actor_y_up_minus_z_forward','floor_offset_m':.025,'blade_length_m':1.19,
        'active_start_s':.34,'active_duration_s':.18,'sample_step_s':.002,
        'source_metadata':{'asset_path':'game/assets/models/production/lyra_fury_gameplay.glb','sha256':sha(output)},'samples':samples}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);recipe=json.loads(args.recipe.read_text());source=args.source.resolve(strict=True);output=args.output.resolve()
    if bpy.app.version[:3]!=(4,3,2) or not bpy.app.background:raise ValueError('Use Blender4.3.2 background')
    if output.exists() or output.with_suffix('.authoring.json').exists():raise ValueError('New output required')
    if sha(source)!=recipe['source_sha256']:raise ValueError('Source SHA differs')
    bpy.ops.wm.read_factory_settings(use_empty=True);fps=recipe['fps'];bpy.context.scene.render.fps=fps
    bpy.ops.import_scene.gltf(filepath=str(source),import_pack_images=True);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    idle=pose_at(rig,'idle',0,fps);before={name:actual_clip_semantics(rig,name,fps) for name in ['charge','charged_heavy']}
    helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape};objects=[o for o in bpy.context.scene.objects if o not in helpers];meshes=[o for o in objects if o.type=='MESH']
    if len(meshes)!=1:raise ValueError('Expected one body mesh')
    mesh=meshes[0];mesh.data.calc_loop_triangles()
    if len(mesh.data.loop_triangles)!=recipe['triangles']:raise ValueError('Body topology differs')
    for obj in objects:obj.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    rig.data.pose_position='REST';bpy.context.view_layer.update();floor=float(skin_coordinates(mesh)[:,2].min());soles=_sole_samples(rig,meshes,floor)
    rig.data.pose_position='POSE';rig.animation_data_create();author=FuryAuthor(rig,recipe);actions={};reports={}
    for name,duration in [('charge',.65),('charged_heavy',1.06)]:
        rows=[];values=[]
        for index in range(round(duration*fps)+1):
            t=index/fps;r=author.pose_slice(name,t,duration);translation=Vector((0,-r['virtual_actor_forward_m'],0));r['time_s']=t
            r['soles_nominal_world']={side:[list(p+translation) for p in points] for side,points in _sample_soles(soles).items()}
            values.append((t,r.pop('full_body_local')));rows.append(r)
        steps=[(shortest_rotation_degrees(a[1][bone][1],b[1][bone][1]),bone,a[0],b[0]) for a,b in zip(values,values[1:]) for bone in a[1]]
        max_step,bone,first,last=max(steps)
        if max_step>15:
            print('FURY_JOINT_TRACE',json.dumps([r for r in author.arm_metrics if r['action']==name and first-.004<=r['time_s']<=last+.004]),flush=True)
            raise ValueError('Adjacent joint exceeds15deg: '+str((max_step,bone,first,last)))
        right=max(r['grip_target_error_m'] for r in rows);left=max(r['left_support_error_m'] for r in rows)
        if max(right,left)>.001 or author.pose.max_reach_clamp>.001:
            print('FURY_REACH',json.dumps(sorted(author.reach_issues,key=lambda r:r['distance_m'],reverse=True)[:12]),flush=True);raise ValueError('Reach/grip exceeds1mm')
        reports[name]={'duration_s':duration,'sample_hz':fps,'max_right_grip_error_m':right,'max_left_support_error_m':left,'max_adjacent_joint_degrees':max_step,'samples':rows}
        if name=='charged_heavy':
            plant=[r for r in rows if .30<=r['time_s']<=.52];anchor=plant[0]['soles_nominal_world']['Left']
            drift=max(math.dist(p,q) for r in plant for p,q in zip(r['soles_nominal_world']['Left'],anchor));reports[name]['nominal_front_sole_drift_m']=drift
            if drift>.01:raise ValueError('Nominal active plant exceeds10mm')
        actions[name]=key_action(rig,name,values,fps);print('FURY_ACTION',name,flush=True)
    rig.animation_data.action=actions['charge'];bpy.context.scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig;output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fury-',dir=output.parent) as directory:
        motion=Path(directory)/'motion.glb';bpy.ops.export_scene.gltf(filepath=str(motion),export_format='GLB',use_selection=True,use_renderable=True,export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_optimize_animation_size=False,export_nla_strips=False,export_extras=True)
        preservation=append_animations(source,motion,output,actions)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps;bpy.ops.import_scene.gltf(filepath=str(output),import_pack_images=True);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    guard_joins={'charge0':compare(idle,pose_at(rig,'charge',0,fps)),'recovery_end':compare(idle,pose_at(rig,'charged_heavy',1.06,fps))}
    held=pose_at(rig,'charge',.65,fps);guard_joins['charge_to_release']=compare(held,pose_at(rig,'charged_heavy',0,fps))
    if any(v['max_joint_distance_m']>.001 or v['max_local_rotation_degrees']>.1 for v in guard_joins.values()):raise ValueError('Actual full-source join differs: '+str(guard_joins))
    after={name:actual_clip_semantics(rig,name,fps) for name in ['charge','charged_heavy']}
    weapon=Path(recipe['weapon_source']['file']);assert sha(weapon)==recipe['weapon_source']['sha256'];curve=extract_curve(rig,recipe,weapon,output);curve_path=output.with_suffix('.blade-curve.json');curve_path.write_text(json.dumps(curve,indent=2)+'\n')
    report={'status':'authored_fury_candidate_pending_raw_native_visual_review','source_sha256':sha(source),'output_sha256':sha(output),'author_tool_sha256':sha(__file__),'recipe_sha256':sha(args.recipe),'source':str(source),'blender':bpy.app.version_string,'preservation':preservation,'actions':reports,'actual_source_joins':guard_joins,'max_ik_reach_clamp_m':author.pose.max_reach_clamp,'minimum_shoulder_hand_distance_m':author.minimum_hand_distance,'minimum_anatomical_pole_margin_m':author.minimum_pole_margin,'minimum_axial_twist_denominator':author.minimum_twist_denominator,'actual_reimport_semantics':semantic_comparison(before,after),'blade_curve':{'file':curve_path.name,'sha256':sha(curve_path),'actual_weapon_sha256':sha(weapon)},'limitations':['Raw IK/sole/joins only; independent53-bone60Hz and midpoint audits required.','Actual skin, same-camera raster/continuous1x AV, real contact/terrain/hardware and AAA approval pending.']}
    output.with_suffix('.authoring.json').write_text(json.dumps(report,indent=2)+'\n');print('RUNEFALL_FURY_AUTHORED',output,flush=True)


if __name__=='__main__':main()
