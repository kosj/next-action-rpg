"""Author full-body loading, weight transfer and braking; preserve published inputs.

Run with verified Blender4.3.2. Existing body bytes and unrelated animations
are copied directly from the source GLB, not re-exported from Blender.
"""
import argparse
import bisect
import copy
import hashlib
import json
import math
import struct
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_character_actions import Author, frame_matrix, interpolate_transform, key_action, smooth, world_transform
from append_character_animations import append_animations, read_glb, _local_matrix
from audit_impact_curve import audit_curve, multiply, slerp
from character_gait import _sole_samples, _sample_soles


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ramp(t,start,end):
    return smooth((t-start)/(end-start))


def shortest_rotation_degrees(left,right):
    a=Quaternion(left).normalized();b=Quaternion(right).normalized()
    return math.degrees(2*math.acos(min(1.0,abs(sum(x*y for x,y in zip(a,b))))))


SEMANTIC_TIMES={'charge':[0,.325,.65],
    'charged_heavy':[0,.20,.30,.34,.43,.475,.52,.64,.80,1.06],
    'heavy_hit':[0,.04,.08,.16,.24,.32,.48]}


def actual_clip_semantics(rig,name,fps):
    actions=[a for a in bpy.data.actions if a.name==name or a.name.startswith(name+'_')]
    if len(actions)!=1:raise ValueError('Ambiguous semantic clip '+name)
    rig.data.pose_position='POSE';rig.animation_data_create();rig.animation_data.action=actions[0]
    start=float(actions[0].frame_range[0]);rows=[]
    for time in SEMANTIC_TIMES[name]:
        frame=start+time*fps;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
        bpy.context.view_layer.update()
        matrices={b:rig.matrix_world@rig.pose.bones[b].matrix for b in ['Hips','Spine2','LeftUpLeg','LeftLeg','LeftFoot','RightUpLeg','RightLeg','RightFoot']}
        flex={}
        for side in ['Left','Right']:
            hip=matrices[side+'UpLeg'].translation;knee=matrices[side+'Leg'].translation;foot=matrices[side+'Foot'].translation
            flex[side]=180-math.degrees((hip-knee).angle(foot-knee))
        rows.append({'time_s':time,'hips_m':list(matrices['Hips'].translation),
            'hips_quaternion_wxyz':list(matrices['Hips'].to_quaternion()),
            'chest_m':list(matrices['Spine2'].translation),'chest_quaternion_wxyz':list(matrices['Spine2'].to_quaternion()),
            'knee_flexion_deg':flex})
    return rows


def semantic_comparison(before,after):
    result={}
    for name,rows in after.items():
        delta=[]
        for old,new in zip(before[name],rows):
            hip=Vector(new['hips_m'])-Vector(old['hips_m'])
            def angle(key):return shortest_rotation_degrees(old[key],new[key])
            delta.append({'time_s':new['time_s'],'hips_delta_m':list(hip),
                'hips_orientation_delta_deg':angle('hips_quaternion_wxyz'),
                'chest_orientation_delta_deg':angle('chest_quaternion_wxyz'),
                'knee_flexion_delta_deg':{side:new['knee_flexion_deg'][side]-old['knee_flexion_deg'][side] for side in ['Left','Right']}})
        result[name]={'before_actual_clip':before[name],'after_actual_clip':rows,'delta':delta}
    return result


def actual_joint_motion(path):
    """Independent raw-glTF FK, including key midpoints and a60Hz schedule."""
    document,binary=read_glb(path);animation=next(a for a in document['animations'] if a['name']=='charged_heavy');cache={}
    def accessor(index):
        if index not in cache:
            a=document['accessors'][index];view=document['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
            offset=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',width*4)
            cache[index]=[struct.unpack_from('<'+'f'*width,binary,offset+i*stride) for i in range(a['count'])]
        return cache[index]
    tracks=[];keys=set()
    for channel in animation['channels']:
        sampler=animation['samplers'][channel['sampler']];times=[v[0] for v in accessor(sampler['input'])]
        tracks.append((channel['target']['node'],channel['target']['path'],times,accessor(sampler['output'])));keys.update(times)
    parents={c:i for i,n in enumerate(document['nodes']) for c in n.get('children',[])}
    names=['RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand'];indices={n['name']:i for i,n in enumerate(document['nodes']) if n.get('name') in names}
    def at(time):
        nodes=copy.deepcopy(document['nodes']);world={}
        for i,prop,times,values in tracks:
            j=max(0,min(len(times)-2,bisect.bisect_right(times,time)-1));u=max(0,min(1,(time-times[j])/(times[j+1]-times[j])))
            nodes[i][prop]=slerp(values[j],values[j+1],u) if prop=='rotation' else [a+(b-a)*u for a,b in zip(values[j],values[j+1])]
        def matrix(i):
            if i not in world:
                local=_local_matrix(nodes[i]);world[i]=multiply(matrix(parents[i]),local) if i in parents else local
            return world[i]
        return {name:[matrix(indices[name])[r][3] for r in range(3)] for name in names}
    ordered=sorted(keys);schedules={'key_and_midpoint':sorted(set(ordered+[(a+b)/2 for a,b in zip(ordered,ordered[1:])])),
        'sixty_hz':sorted(set([i/60 for i in range(math.floor(1.06*60)+1)]+[1.06]))};report={}
    for label,times in schedules.items():
        poses=[at(t) for t in times];result={}
        for name in names:
            intervals=[{'start_s':a,'end_s':b,'displacement_m':math.dist(pa[name],pb[name]),'m_s':math.dist(pa[name],pb[name])/(b-a)} for a,b,pa,pb in zip(times,times[1:],poses,poses[1:])]
            result[name]={'maximum_speed':max(intervals,key=lambda r:r['m_s']),'maximum_displacement':max(intervals,key=lambda r:r['displacement_m'])}
        report[label]={'samples':len(times),'joints':result}
    return report


class WeightAuthor(Author):
    def __init__(self,rig,recipe):
        super().__init__(rig,recipe)
        self.reach_issues=[]
        self.arm_plane_signs={}
        self.minimum_arm_pole_margin={'distance_m':float('inf')}
        original_limb=self.pose.limb
        def tracked_limb(upper,lower,end,target,pole,rotation):
            # The inherited near-body pole crosses the charged trajectory's
            # shoulder→hand axis. A forward/outboard elbow plane keeps both
            # arms on a continuous IK branch throughout the diagonal sweep.
            if upper in ('RightArm','LeftArm'):
                side=-1 if upper=='RightArm' else 1
                # Preserve the published active arm solution. Added weight
                # comes from loading, stance/catch and braking; do not force
                # a new elbow roll against the immutable blade trajectory.
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
                if plane.length<self.minimum_arm_pole_margin['distance_m']:
                    self.minimum_arm_pole_margin={'distance_m':plane.length,'bone':upper,'action':self.current_action,'time_s':self.current_time}
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
        hit=self.current_action=='heavy_hit'
        for side,sign in [('Left',1),('Right',-1)]:
            rest = self.pose.rest_world[side+'Foot']
            point = rest.translation.copy()
            point.x = sign*.19*self.ratio
            lift = 0.0
            if charged and side=='Left':
                # Step BEFORE the active displacement; keep this world anchor
                # through impact while code advances the actor by0.576m.
                step = ramp(t,.04,.30)
                point.x=(.19+.05*step-.05*ramp(t,.70,.98))*self.ratio
                world_y = -.11+(-.52+.11)*step
                if .04<t<.30:
                    lift = .12*math.sin(math.pi*(t-.04)/.26)**2
                if t>.70:
                    world_y += (-.576-.11+.52)*ramp(t,.70,.98)
                    if t<.98:lift = .07*math.sin(math.pi*(t-.70)/.28)**2
            elif charged:
                follow = ramp(t,.30,.56)
                point.x=(-.19-.04*follow+.04*ramp(t,.72,1.04))*self.ratio
                world_y = .10-.576*follow
                if .30<t<.56:lift = .11*math.sin(math.pi*(t-.30)/.26)**2
            elif hit:
                # Local stagger placement only. Resolved collision recoil can
                # stop at a wall or point sideways; never infer its displacement
                # from a nominal motor time/distance inside the animation.
                if side=='Right':
                    step=ramp(t,.03,.26);recover=ramp(t,.29,.48)
                    world_y=.10+.09*step*(1-recover)
                    point.x=(-.19-.035*step*(1-recover))*self.ratio
                    if .03<t<.26:lift=.085*math.sin(math.pi*(t-.03)/.23)**2
                    if .29<t<.48:lift=.045*math.sin(math.pi*(t-.29)/.19)**2
                else:
                    brace=ramp(t,.06,.20)*(1-ramp(t,.30,.48))
                    world_y=-.11-.04*brace
                    point.x=(.19+.025*brace)*self.ratio
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
        hip_shift=Vector((0,0,0))
        if name=='charge':
            amount=smooth(t/duration)
            grip=interpolate_transform(grip,self.loaded(),amount)
            drop=baseline+.15*self.ratio*amount
            yaw=math.radians(-6-54*amount)
            torso_yaw=math.radians(-6-46*amount)
            lean+=math.radians(8)*amount
            hip_shift=Vector((-.045,.06,0))*self.ratio*amount
        elif name=='charged_heavy':
            # The first pose equals the held charge endpoint. Pelvis, torso,
            # then blade accelerate at separate times instead of one scalar.
            coil=ramp(t,0,.22)
            pelvis=ramp(t,.20,.41)
            torso=ramp(t,.28,.49)
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
            settle=ramp(t,.52,.64)
            yaw=math.radians((-60-12*coil+114*pelvis)*(1-recover)-6*recover)
            torso_yaw=math.radians((-52-8*coil+112*torso)*(1-recover)-6*recover)
            drop=baseline+self.ratio*(.15+.035*coil-.075*pelvis+.060*settle)*(1-recover)
            lean=math.radians(13+7*torso)*(1-recover)+math.radians(self.guard['lean_deg'])*recover
            # Deep/offset load drives into a centered stance. Late-active
            # shoulders stay near the proven old path rather than crossing
            # the fixed grip and compensating with extreme forearm twist.
            hip_shift=Vector((-.045*(1-pelvis),.06*(1-pelvis),0))*self.ratio*(1-recover)
            # Blend smoothly to the exact published torso/shoulder path by
            # active start and keep it throughout active. Earlier experimental
            # body excursions required excessive opposing arm/wrist twist.
            published=ramp(t,.25,.34)*(1-ramp(t,.52,.60))
            old_pelvis=ramp(t,.26,.43);old_torso=ramp(t,.30,.49)
            old_yaw=math.radians((-34-6*coil+76*old_pelvis)*(1-recover)-6*recover)
            old_chest=math.radians((-42-6*coil+100*old_torso)*(1-recover)-6*recover)
            old_drop=baseline+self.ratio*(.08+.03*old_pelvis)*(1-recover)
            old_lean=math.radians(8+12*old_torso)*(1-recover)+math.radians(self.guard['lean_deg'])*recover
            yaw=yaw*(1-published)+old_yaw*published;torso_yaw=torso_yaw*(1-published)+old_chest*published
            drop=drop*(1-published)+old_drop*published;lean=lean*(1-published)+old_lean*published
            hip_shift*=1-published
        elif name=='heavy_hit':
            recoil=ramp(t,0,.07)*(1-ramp(t,.11,.37))
            brace=ramp(t,.06,.20)*(1-ramp(t,.30,.48))
            drop=baseline+self.ratio*(.07*recoil+.10*brace)
            yaw=math.radians(-6-18*recoil+8*brace)
            torso_yaw=math.radians(-6-26*recoil+14*brace)
            lean+=math.radians(-30*recoil+20*brace)
            hip_shift=Vector((.025*brace,.035*recoil-.065*brace,0))*self.ratio
            grip.translation+=(Vector((.025,.14,-.08))*recoil+Vector((-.015,-.04,-.06))*brace)*self.ratio
            grip=interpolate_transform(grip,frame_matrix(grip.translation,math.radians(-32),math.radians(22)),recoil)
            free_left=.35*recoil
        else:
            raise ValueError('Unknown slice action '+name)
        self.body(drop,yaw,lean)
        hip=self.pose.matrix('Hips').copy();hip.translation+=hip_shift
        self.pose.set_world('Hips',hip)
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
            'chest_rotation':list(self.pose.matrix('Spine2').to_quaternion()),'grip_direction':list(grip.to_3x3().col[1].normalized()),
            'hips_world_m':list(self.pose.matrix('Hips').translation),
            'chest_world_m':list(self.pose.matrix('Spine2').translation),
            'knees_world_m':{side:list(self.pose.matrix(side+'Leg').translation) for side in ['Left','Right']},
            'feet_world_m':{side:list(self.pose.matrix(side+'Foot').translation) for side in ['Left','Right']},
            'assumed_runtime_recoil_compensation_m':0.0,
            'pelvis_shift_m':list(hip_shift),'pelvis_drop_m':drop,'pelvis_yaw_input_deg':math.degrees(yaw),
            'chest_yaw_input_deg':math.degrees(torso_yaw),'body_lean_input_deg':math.degrees(lean)}


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
    durations={'charge':.65,'charged_heavy':1.06} if recipe['profile']=='lyra' else {'heavy_hit':.48}
    before={name:actual_clip_semantics(rig,name,recipe['fps']) for name in durations}
    for obj in objects:obj.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    rig.data.pose_position='REST';bpy.context.view_layer.update()
    from author_character_actions import skin_coordinates
    floor=float(skin_coordinates(mesh)[:,2].min())
    sole_samples=_sole_samples(rig,meshes,floor)
    rig.data.pose_position='POSE';rig.animation_data_create()
    author=WeightAuthor(rig,recipe)
    actions={};reports={};fps=recipe['fps']
    boundaries={};continuity={}
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
        maximum=0;worst=None
        for a,b in zip(samples,samples[1:]):
            for bone in a[1]:
                angle=shortest_rotation_degrees(a[1][bone][1],b[1][bone][1])
                if angle>maximum:maximum=angle;worst={'bone':bone,'interval_s':[a[0],b[0]]}
        if maximum>45:raise ValueError('Joint discontinuity over45deg: '+str(worst))
        continuity[name]={'max_joint_key_step_degrees':maximum,'worst':worst,'limit_degrees':45}
        boundaries[name]={'first':samples[0][1],'last':samples[-1][1]}
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
            reports[name]['gameplay_hull']='Full display/IK marker segment1.19m; gameplay sharp subset begins0.18 (length0.9758m), radius0.12m trimmed to sharp endpoints; same smooth(f^2) full-marker curve. Reach1.5m is metadata, not capsule extent.'
            reports[name]['physics_contract']={'startup_s':.34,'active_s':.18,'recovery_s':.54,
                'sweep_progress':'3*f^4-2*f^6','actor_local_grip_start_m':[.22,1.445,-.28],
                'actor_local_grip_end_m':[-.24,1.125,-.14],'azimuth_deg':[-85,85],
                'pitch_deg':[50,-45],'blade_length_m':1.19,'blade_radius_m':.12,
                'floor_offset_m':.025,'resource_reach_hint_m':1.5,'blade_damage_start_fraction':.18,
                'sharp_damage_length_m':.9758}
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
    if recipe['profile']=='lyra':
        def boundary_error(a,b):
            return max(max(abs(x-y) for x,y in zip(a[name][0],b[name][0])) for name in a),max(shortest_rotation_degrees(a[name][1],b[name][1]) for name in a)
        joins={'charge_hold_to_release':boundary_error(boundaries['charge']['last'],boundaries['charged_heavy']['first']),
            'recovery_to_guard':boundary_error(boundaries['charge']['first'],boundaries['charged_heavy']['last'])}
    else:
        a=boundaries['heavy_hit']['first'];b=boundaries['heavy_hit']['last']
        joins={'recovery_to_guard':(max(max(abs(x-y) for x,y in zip(a[n][0],b[n][0])) for n in a),max(shortest_rotation_degrees(a[n][1],b[n][1]) for n in a))}
    if any(position>1e-5 or angle>.1 for position,angle in joins.values()):raise ValueError('Full-body clip join differs: '+str(joins))
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
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps
    bpy.ops.import_scene.gltf(filepath=str(output),import_pack_images=True)
    new_rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    after={name:actual_clip_semantics(new_rig,name,fps) for name in durations}
    report={'status':'authored_weight_recovery_candidate_requires_runtime_visual_review','source':str(source),
        'author_tool_sha256':sha(__file__),'graft_tool_sha256':sha(Path(__file__).with_name('append_character_animations.py')),
        'pose_library_sha256':sha(Path(__file__).with_name('author_character_actions.py')),
        'interpolation_audit_tool_sha256':sha(Path(__file__).with_name('audit_impact_curve.py')),
        'recipe_sha256':sha(args.recipe),
        'recipe':str(args.recipe),'profile':recipe['profile'],'blender':bpy.app.version_string,
        'preservation':preservation,'actions':reports,'interpolation_audit':interpolated,'max_ik_reach_clamp_m':author.pose.max_reach_clamp,
        'joint_continuity':continuity,'full_body_join_position_m_and_rotation_deg':joins,
        'actual_reimport_semantics':semantic_comparison(before,after),
        'minimum_arm_pole_margin':author.minimum_arm_pole_margin,
        'actual_glb_joint_motion':{'scope':'Actual raw glTF FK world-joint displacement at keys/midpoints and60Hz, not actual rendered60fps performance or visual approval.',
            'before':actual_joint_motion(source),'after':actual_joint_motion(output)} if recipe['profile']=='lyra' else None,
        'limitations':['Analytical character slice, not AAA approval.','Finite sampled foot/grip metrics are not anatomical or continuous collision approval.',
            'Independent same-phase runtime marker/physical capsule validation remains required.','Terrain adaptation and final all-state transition review remain pending.']}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('RUNEFALL_IMPACT_AUTHORED',output,flush=True)


if __name__=='__main__':
    main()
