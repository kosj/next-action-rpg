"""Author only the charged-heavy slice; graft motion into immutable old GLBs.

Run with verified Blender4.3.2. Existing body bytes and unrelated animations
are copied directly from the source GLB, not re-exported from Blender.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_character_actions import Author, frame_matrix, interpolate_transform, key_action, smooth, world_transform
from append_character_animations import append_animations, read_glb
from audit_impact_curve import audit_curve
from character_gait import _sole_samples, _sample_soles


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ramp(t,start,end):
    return smooth((t-start)/(end-start))


class ImpactAuthor(Author):
    def __init__(self,rig,recipe):
        super().__init__(rig,recipe)
        self.reach_issues=[]
        self.arm_plane_signs={}
        original_limb=self.pose.limb
        def tracked_limb(upper,lower,end,target,pole,rotation):
            # The inherited near-body pole crosses the charged trajectory's
            # shoulder→hand axis. A forward/outboard elbow plane keeps both
            # arms on a continuous IK branch throughout the diagonal sweep.
            if upper in ('RightArm','LeftArm'):
                side=-1 if upper=='RightArm' else 1
                pole=Vector((side*.75,-.45,1.15))*self.ratio
            distance=(target-self.pose.matrix(upper).translation).length
            maximum=self.pose.length[upper]+self.pose.length[lower]-.0001
            if distance>maximum+.00001:
                self.reach_issues.append({'action':self.current_action,'time_s':self.current_time,
                    'limb':upper,'requested_m':distance,'maximum_m':maximum,'excess_m':distance-maximum,
                    'target_m':list(target)})
            if upper in ('RightArm','LeftArm'):
                start=self.pose.matrix(upper).translation.copy()
                direction=(target-start).normalized()
                plane=pole-start-direction*(pole-start).dot(direction)
                if plane.length<.02*self.ratio:
                    raise ValueError('Impact elbow pole approaches singular axis')
                plane.normalize()
                first,second=self.pose.length[upper],self.pose.length[lower]
                actual=min(maximum,max(abs(first-second)+.0001,distance))
                self.pose.max_reach_clamp=max(self.pose.max_reach_clamp,abs(actual-distance))
                target=start+direction*actual
                along=(first*first-second*second+actual*actual)/(2*actual)
                middle=start+direction*along+plane*math.sqrt(max(0,first*first-along*along))
                normal=direction.cross(plane).normalized()
                for bone,a,b in [(upper,start,middle),(lower,middle,target)]:
                    # Give both links a continuous explicit plane normal.
                    # Chained shortest-arc aim can introduce opposing twist
                    # branches whose exact hand targets hide midpoint errors.
                    if bone not in self.arm_plane_signs:
                        self.arm_plane_signs[bone]=1 if self.pose.rest_world[bone].to_3x3().col[0].dot(normal)>=0 else -1
                    x=normal*self.arm_plane_signs[bone];y=(b-a).normalized();z=x.cross(y).normalized()
                    orientation=Matrix((x,y,z)).transposed().to_quaternion()
                    self.pose.set_world(bone,world_transform(a,orientation,self.pose.scale))
                self.pose.set_world(end,world_transform(target,rotation,self.pose.scale))
                return
            return original_limb(upper,lower,end,target,pole,rotation)
        self.pose.limb=tracked_limb

    def loaded(self):
        return frame_matrix(Vector((-.26,-.12,1.48))*self.ratio,math.radians(-65),math.radians(65))

    @staticmethod
    def travel(t):
        return 3.2*max(0.0,min(.18,t-.34))

    def feet(self,t,charged=False):
        travel = self.travel(t) if charged else 0.0
        for side,sign in [('Left',1),('Right',-1)]:
            rest = self.pose.rest_world[side+'Foot']
            point = rest.translation.copy()
            point.x = sign*.19*self.ratio
            lift = 0.0
            if charged and side=='Left':
                # Step BEFORE the active displacement; keep this world anchor
                # through impact while code advances the actor by0.576m.
                step = ramp(t,.04,.30)
                world_y = -.11+(-.52+.11)*step
                if .04<t<.30:
                    lift = .12*math.sin(math.pi*(t-.04)/.26)**2
                if t>.70:
                    world_y += (-.576-.11+.52)*ramp(t,.70,.98)
                    if t<.98:lift = .07*math.sin(math.pi*(t-.70)/.28)**2
            elif charged:
                follow = ramp(t,.38,.66)
                world_y = .10-.576*follow
                if .38<t<.66:lift = .11*math.sin(math.pi*(t-.38)/.28)**2
            else:
                world_y = -.11 if side=='Left' else .10
            point.y = (world_y+travel)*self.ratio
            point.z += lift*self.ratio
            self.pose.limb(side+'UpLeg',side+'Leg',side+'Foot',point,
                Vector((sign*.13,-.9,.5))*self.ratio,rest.to_quaternion())

    def pose_slice(self,name,t,duration):
        self.current_action=name;self.current_time=t
        self.pose.reset()
        baseline=self.guard['pelvis_drop_m']*self.ratio
        lean=math.radians(self.guard['lean_deg'])
        yaw=math.radians(-6)
        grip=self.guard_grip()
        torso_yaw=yaw
        free_left=0.0
        if name=='charge':
            amount=smooth(t/duration)
            grip=interpolate_transform(grip,self.loaded(),amount)
            drop=baseline+.08*self.ratio*amount
            yaw=math.radians(-6-28*amount)
            torso_yaw=math.radians(-6-36*amount)
            lean+=math.radians(3)*amount
        elif name=='charged_heavy':
            # The first pose equals the held charge endpoint. Pelvis, torso,
            # then blade accelerate at separate times instead of one scalar.
            coil=ramp(t,0,.22)
            pelvis=ramp(t,.26,.43)
            torso=ramp(t,.30,.49)
            strike=smooth(max(0.0,min(1.0,(t-.34)/.18))**2)
            recover=ramp(t,.66,1.06)
            loaded=self.loaded()
            coiled=frame_matrix(Vector((-.30,-.06,1.52))*self.ratio,math.radians(-85),math.radians(72))
            release=frame_matrix(Vector((-.22,-.28,1.42))*self.ratio,math.radians(-85),math.radians(50))
            end=frame_matrix(Vector((.24,-.14,1.10))*self.ratio,math.radians(85),math.radians(-45))
            if t<.22:grip=interpolate_transform(loaded,coiled,coil)
            elif t<.34:grip=interpolate_transform(coiled,release,ramp(t,.22,.34))
            elif t<=.52:
                # Exact signed horizontal projection remains -85→+85 while
                # the visible blade also descends on a diagonal.
                position=release.translation.lerp(end.translation,strike)
                grip=frame_matrix(position,math.radians(-85+170*strike),math.radians(50-95*strike))
            else:
                follow=frame_matrix(Vector((.23,-.10,1.08))*self.ratio,math.radians(94),math.radians(-42))
                grip=interpolate_transform(end,follow,ramp(t,.52,.66))
                grip=interpolate_transform(grip,self.guard_grip(),recover)
            yaw=math.radians((-34-6*coil+76*pelvis)*(1-recover)-6*recover)
            torso_yaw=math.radians((-42-6*coil+100*torso)*(1-recover)-6*recover)
            drop=baseline+self.ratio*(.08+.03*pelvis)*(1-recover)
            lean=math.radians(8+12*torso)*(1-recover)+math.radians(self.guard['lean_deg'])*recover
        elif name=='heavy_hit':
            recoil=ramp(t,0,.075)*(1-ramp(t,.16,.48))
            drop=baseline+.065*self.ratio*recoil
            yaw=math.radians(-6-18*recoil)
            torso_yaw=math.radians(-6-26*recoil)
            lean-=math.radians(25)*recoil
            grip.translation+=Vector((.025,.10,-.04))*self.ratio*recoil
            grip=interpolate_transform(grip,frame_matrix(grip.translation,math.radians(-28),math.radians(25)),recoil)
            free_left=.35*recoil
        else:
            raise ValueError('Unknown slice action '+name)
        self.body(drop,yaw,lean)
        for bone,weight in [('Spine',.20),('Spine1',.25),('Spine2',.25)]:
            self.pose.local_rotation(bone,Quaternion((0,1,0),torso_yaw*weight)@Quaternion((1,0,0),lean*weight))
        self.feet(t,name=='charged_heavy')
        self.fingers()
        self.arms(grip,free_left)
        self.pose.apply()
        left_target=grip.copy()
        left_target.translation=grip@Vector((0,self.socket['left_grasp_blade_axis_m']*self.ratio,0))
        local_left=self.k_left.copy();local_left.translation/=self.pose.scale
        left_actual=self.pose.matrix('LeftHand')@local_left@Matrix.Diagonal((1/self.pose.scale,1/self.pose.scale,1/self.pose.scale,1))
        tip=grip@Vector((0,self.socket['blade_tip_from_grip_m']*self.ratio,0))
        return {**self.frame_metrics,'left_support_error_m':(left_actual.translation-left_target.translation).length,
            'virtual_actor_forward_m':self.travel(t) if name=='charged_heavy' else 0.0,
            'actual_grip_blender_world_m':list(self.last_grip.translation),
            'actual_tip_blender_world_m':list(self.last_grip@Vector((0,self.socket['blade_tip_from_grip_m']*self.ratio,0))),
            'blade_tip_z_m':tip.z,'pelvis_rotation':list(self.pose.matrix('Hips').to_quaternion()),
            'chest_rotation':list(self.pose.matrix('Spine2').to_quaternion()),'grip_direction':list(grip.to_3x3().col[1].normalized())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--recipe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not bpy.app.background or bpy.app.version[:3]!=(4,3,2):
        raise ValueError('Use Blender4.3.2 background')
    source=args.source.resolve(strict=True);output=args.output.resolve()
    report_path=output.with_suffix('.authoring.json')
    if output.exists() or report_path.exists() or source==output:
        raise ValueError('New separate output required')
    recipe=json.loads(args.recipe.read_text());digest=sha(source)
    if digest!=recipe['source_sha256']:raise ValueError('Source digest differs')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=recipe['fps'];bpy.context.scene.render.fps_base=1.0
    bpy.ops.import_scene.gltf(filepath=str(source),import_pack_images=True)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape}
    objects=[o for o in bpy.context.scene.objects if o not in helpers]
    meshes=[o for o in objects if o.type=='MESH']
    if len(meshes)!=1:raise ValueError('Expected one source body object')
    mesh=meshes[0];mesh.data.calc_loop_triangles()
    if len(mesh.data.loop_triangles)!=recipe['triangles']:raise ValueError('Unexpected body topology')
    for obj in objects:obj.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    rig.data.pose_position='REST';bpy.context.view_layer.update()
    from author_character_actions import skin_coordinates
    floor=float(skin_coordinates(mesh)[:,2].min())
    sole_samples=_sole_samples(rig,meshes,floor)
    rig.data.pose_position='POSE';rig.animation_data_create()
    author=ImpactAuthor(rig,recipe)
    durations={'charge':.65,'charged_heavy':1.06} if recipe['profile']=='lyra' else {'heavy_hit':.48}
    actions={};reports={};fps=recipe['fps']
    for name,duration in durations.items():
        rows=[];samples=[]
        for index in range(round(duration*fps)+1):
            time=index/fps
            metrics=author.pose_slice(name,time,duration)
            soles=_sample_soles(sole_samples)
            translation=Vector((0,-metrics['virtual_actor_forward_m']*author.ratio,0))
            metrics['time_s']=time
            metrics['soles_world']={side:[list(p+translation) for p in points] for side,points in soles.items()}
            rows.append(metrics);samples.append((time,author.pose.values()))
        actions[name]=key_action(rig,name,samples,fps)
        reports[name]={'duration_s':duration,'sample_hz':fps,'samples':rows,
            'max_right_grip_error_m':max(r['grip_target_error_m'] for r in rows),
            'max_left_support_error_m':max(r['left_support_error_m'] for r in rows) if name!='heavy_hit' else None,
            'minimum_blade_tip_height_m':min(r['blade_tip_z_m'] for r in rows)}
        if name=='charged_heavy':
            planted=[r for r in rows if .30-1e-8<=r['time_s']<=.52+1e-8]
            anchor=planted[0]['soles_world']['Left']
            drift=max((Vector(p)-Vector(q)).length for r in planted for p,q in zip(r['soles_world']['Left'],anchor))
            reports[name]['front_foot_active_world_drift_m']=drift
            reports[name]['front_foot_plant_interval_s']=[.30,.52]
            reports[name]['nominal_actor_travel_m']=.576
            reports[name]['gameplay_hull']='Charged-only authoritative3D blade segment, length1.19m/radius0.12m, shared smooth(f^2) azimuth/pitch/grip curve; reach1.5m is metadata, not capsule extent'
            reports[name]['physics_contract']={'startup_s':.34,'active_s':.18,'recovery_s':.54,
                'sweep_progress':'3*f^4-2*f^6','actor_local_grip_start_m':[.22,1.445,-.28],
                'actor_local_grip_end_m':[-.24,1.125,-.14],'azimuth_deg':[-85,85],
                'pitch_deg':[50,-45],'blade_length_m':1.19,'blade_radius_m':.12,
                'floor_offset_m':.025,'resource_reach_hint_m':1.5}
            if drift>.01:raise ValueError('Front planted sole drifts over10mm: '+str(drift))
        if name!='heavy_hit' and reports[name]['max_left_support_error_m']>.001:
            raise ValueError('Two-hand target error over1mm')
        if reports[name]['max_right_grip_error_m']>.001:
            print('IMPACT_REACH_FAILURE',json.dumps(sorted(author.reach_issues,key=lambda r:r['excess_m'],reverse=True)[:8]),flush=True)
            raise ValueError('Right-hand grip error over1mm')
        print('IMPACT_AUTHORED',name,duration,flush=True)
    if author.pose.max_reach_clamp>.001:
        print('IMPACT_REACH_FAILURE',json.dumps(sorted(author.reach_issues,key=lambda r:r['excess_m'],reverse=True)[:8]),flush=True)
        raise ValueError('IK target outside measured reach: '+str(author.pose.max_reach_clamp))
    rig.animation_data.action=next(iter(actions.values()));bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.impact-',dir=output.parent) as staging:
        motion=Path(staging)/'motion.glb'
        bpy.ops.export_scene.gltf(filepath=str(motion),export_format='GLB',use_selection=True,use_renderable=True,
            export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',
            export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,
            export_frame_step=1,export_optimize_animation_size=False,export_nla_strips=False,export_extras=True)
        preservation=append_animations(source,motion,output,actions)
    interpolated=audit_curve(output,recipe) if recipe['profile']=='lyra' else None
    if interpolated is not None and not interpolated['passed']:
        output.with_suffix('.interpolation-failed.json').write_text(json.dumps(interpolated,indent=2)+'\n')
        raise ValueError('Actual exported key/midpoint FK gate failed: '+str({k:v for k,v in interpolated.items() if k!='samples'}))
    if sha(source)!=digest:raise ValueError('Source file changed')
    report={'status':'authored_slice_requires_actual_runtime_visual_review','source':str(source),
        'author_tool_sha256':sha(__file__),'graft_tool_sha256':sha(Path(__file__).with_name('append_character_animations.py')),
        'pose_library_sha256':sha(Path(__file__).with_name('author_character_actions.py')),
        'interpolation_audit_tool_sha256':sha(Path(__file__).with_name('audit_impact_curve.py')),
        'recipe_sha256':sha(args.recipe),
        'recipe':str(args.recipe),'profile':recipe['profile'],'blender':bpy.app.version_string,
        'preservation':preservation,'actions':reports,'interpolation_audit':interpolated,'max_ik_reach_clamp_m':author.pose.max_reach_clamp,
        'limitations':['Analytical character slice, not AAA approval.','Finite sampled foot/grip metrics are not anatomical or continuous collision approval.',
            'Independent same-phase runtime marker/physical capsule validation remains required.','Terrain adaptation and final all-state transition review remain pending.']}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('RUNEFALL_IMPACT_AUTHORED',output,flush=True)


if __name__=='__main__':
    main()
