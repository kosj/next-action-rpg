"""Author skeletal gameplay poses on a compatible immutable 53-bone body.

blender -b --factory-startup --python tools/author_character_actions.py -- \
  --source art_source/production/candidates/lyra-web-001/motion-library.glb \
  --recipe art_source/production/character_actions/lyra.json \
  --output build/art-candidates/character-integration/lyra-gameplay.glb

Only the source mesh, rest skeleton, skin and materials are reused. Every source
action is discarded. Runtime actions are keyed from analytical world-space IK
and authored semantic pose recipes; stock FCurves are never copied or sampled.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import traceback

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
BASIC = ['Root','Hips','Spine','Spine1','Spine2','Neck','Head']
LIMBS = [side+part for side in ['Left','Right'] for part in ['Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot','ToeBase']]
FINGERS = ['HandLoRA_Bip01_'+side+'_Finger'+str(finger)+suffix for side in ['L','R'] for finger in range(5) for suffix in ['', '1','2']]
REQUIRED = set(BASIC+LIMBS+FINGERS)
SOURCE_DIGEST = None
SOURCE_PATH = None


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            result.update(block)
    return result.hexdigest()


def smooth(value):
    x = min(1.0,max(0.0,value))
    return x*x*(3.0-2.0*x)


def hermite(a,b,va,vb,duration,time):
    u = min(1.0,max(0.0,time/duration))
    return (2*u**3-3*u*u+1)*a + (u**3-2*u*u+u)*duration*va + (-2*u**3+3*u*u)*b + (u**3-u*u)*duration*vb


def frame_matrix(position, azimuth, pitch):
    direction = Vector((math.sin(azimuth)*math.cos(pitch),-math.cos(azimuth)*math.cos(pitch),math.sin(pitch)))
    up = Vector((0,0,1))
    normal = up-direction*up.dot(direction)
    if normal.length < 0.001:
        normal = Vector((0,1,0))-direction*Vector((0,1,0)).dot(direction)
    normal.normalize()
    across = direction.cross(normal).normalized()
    result = Matrix((across,direction,normal)).transposed().to_4x4()
    result.translation = Vector(position)
    return result


def world_transform(position, rotation, scale):
    return Matrix.Translation(position)@rotation.to_matrix().to_4x4()@Matrix.Diagonal((scale,scale,scale,1.0))


class PoseRig:
    """Evaluate simple imported FK and solve limb targets without dependency updates."""
    def __init__(self,rig):
        self.rig = rig
        self.world = rig.matrix_world.copy()
        self.inverse = self.world.inverted()
        scales = self.world.to_scale()
        if max(scales)-min(scales)>0.00001 or min(scales)<=0:
            raise ValueError('Expected a positive uniform rig wrapper scale')
        self.scale = scales.x
        self.rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
        self.parents = {b.name:b.parent.name if b.parent else None for b in rig.data.bones}
        self.relative = {name:(self.rest[self.parents[name]].inverted()@matrix if self.parents[name] else matrix.copy()) for name,matrix in self.rest.items()}
        self.names = [b.name for b in rig.data.bones]
        self.rest_world = {name:self.world@matrix for name,matrix in self.rest.items()}
        self.length = {b.name:b.length*self.scale for b in rig.data.bones}
        self.max_reach_clamp = 0.0
        self.reset()

    def reset(self):
        self.basis = {name:Matrix.Identity(4) for name in self.names}
        self.cache = {}

    def load_current(self):
        self.basis = {name:self.rig.pose.bones[name].matrix_basis.copy() for name in self.names}
        self.cache = {}

    def pose(self,name):
        if name not in self.cache:
            parent = self.parents[name]
            self.cache[name] = (self.pose(parent) if parent else Matrix.Identity(4))@self.relative[name]@self.basis[name]
        return self.cache[name]

    def matrix(self,name):
        return self.world@self.pose(name)

    def local_rotation(self,name,rotation):
        self.basis[name] = rotation.to_matrix().to_4x4()
        self.cache = {}

    def set_world(self,name,matrix):
        parent = self.parents[name]
        parent_pose = self.pose(parent) if parent else Matrix.Identity(4)
        self.basis[name] = self.relative[name].inverted()@parent_pose.inverted()@self.inverse@matrix
        self.cache = {}

    def aim(self,name,start,end):
        reference = self.matrix(name)
        old_axis = reference.to_3x3().col[1].normalized()
        new_axis = (end-start).normalized()
        rotation = old_axis.rotation_difference(new_axis)@reference.to_quaternion()
        self.set_world(name,world_transform(start,rotation,self.scale))

    def limb(self,upper,lower,end,target,pole,end_rotation):
        start = self.matrix(upper).translation.copy()
        delta = target-start
        distance = delta.length
        first,second = self.length[upper],self.length[lower]
        maximum = first+second-0.0001
        minimum = abs(first-second)+0.0001
        actual_distance = min(maximum,max(minimum,distance))
        self.max_reach_clamp = max(self.max_reach_clamp,abs(actual_distance-distance))
        direction = delta.normalized()
        target = start+direction*actual_distance
        elbow_plane = pole-start-direction*(pole-start).dot(direction)
        if elbow_plane.length<0.0001:
            elbow_plane = direction.cross(Vector((0,0,1)))
        elbow_plane.normalize()
        along = (first*first-second*second+actual_distance*actual_distance)/(2*actual_distance)
        bend = math.sqrt(max(0.0,first*first-along*along))
        middle = start+direction*along+elbow_plane*bend
        self.aim(upper,start,middle)
        self.aim(lower,middle,target)
        self.set_world(end,world_transform(target,end_rotation,self.scale))

    def apply(self):
        for name in self.names:
            bone = self.rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.matrix_basis = self.basis[name]
        bpy.context.view_layer.update()

    def values(self):
        values = {}
        for name in self.names:
            location,rotation,scale = self.basis[name].decompose()
            values[name] = (list(location),list(rotation),list(scale))
        return values


def key_action(rig,name,samples,fps):
    action = bpy.data.actions.new(name)
    action.id_root = 'OBJECT'
    action.use_fake_user = True
    action['motion_authorship'] = 'RUNEFALL project-authored world IK; no copied source curves'
    for bone_name in samples[0][1]:
        previous = None
        for _,pose in samples:
            quaternion = Quaternion(pose[bone_name][1])
            if previous is not None and previous.dot(quaternion)<0.0:
                quaternion.negate()
                pose[bone_name][1][:] = list(quaternion)
            previous = quaternion
        escaped = json.dumps(bone_name)
        for part,property_name,count in [(0,'location',3),(1,'rotation_quaternion',4),(2,'scale',3)]:
            for axis in range(count):
                values = [(time*fps,pose[bone_name][part][axis]) for time,pose in samples]
                curve = action.fcurves.new('pose.bones['+escaped+'].'+property_name,index=axis,action_group=bone_name)
                curve.keyframe_points.add(len(values))
                curve.keyframe_points.foreach_set('co',[x for pair in values for x in pair])
                for key in curve.keyframe_points:key.interpolation = 'LINEAR'
    return action


def attack_contract(profile):
    sys.path.insert(0,str(ROOT/'tools'))
    from check_art_production import parse_attack_defaults,parse_attack_resource
    defaults = parse_attack_defaults(ROOT/'game/scripts/core/attack_data.gd')
    resources = ['enemy_attack'] if profile=='sentinel' else ['light_1','light_2','light_3','heavy']
    attacks = {name:parse_attack_resource(ROOT/'game/data'/(name+'.tres'),defaults) for name in resources}
    if profile!='sentinel':
        for index in range(3):
            attacks['skill_'+str(index+1)] = {**attacks['heavy'],'startup':0.16,'active':0.35,'recovery':0.28,'arc':160.0 if index==0 else 360.0,'lunge':13.0 if index==0 else 0.0}
    return attacks


class Author:
    def __init__(self,rig,recipe):
        self.pose = PoseRig(rig)
        self.rig = rig
        self.recipe = recipe
        self.height = recipe['height_m']
        self.ratio = self.height/1.82
        self.guard = recipe['guard']
        self.socket = recipe['weapon_socket']
        self.k_right = Matrix(self.socket['basis_columns']).transposed().to_4x4()
        self.k_right.translation = Vector(self.socket['offset_m'])*self.ratio
        self.k_left = Matrix(((0,0,-1),(1,0,0),(0,-1,0))).transposed().to_4x4()
        self.k_left.translation = Vector((0,self.socket['offset_m'][1],self.socket['offset_m'][2]))*self.ratio
        self.hip_rest = self.pose.rest_world['Hips'].translation.copy()
        self.armature = rig
        self.last_grip = None
        self.frame_metrics = {}

    def guard_grip(self):
        return frame_matrix(Vector(self.guard['grip_m'])*self.ratio,math.radians(self.guard['azimuth_deg']),math.radians(self.guard['pitch_deg']))

    def fingers(self,squeeze=0.0):
        for side in ['L','R']:
            for finger in range(5):
                for part,suffix in enumerate(['','1','2']):
                    name='HandLoRA_Bip01_'+side+'_Finger'+str(finger)+suffix
                    if finger==0:
                        rotation = Quaternion((1,0,0),-0.35-0.12*part)@Quaternion((0,0,1),(0.15 if side=='R' else -0.15))
                    else:
                        rotation = Quaternion((1,0,0),-self.recipe['finger_curl_rad'][part]-squeeze)
                    self.pose.local_rotation(name,rotation)

    def body(self,drop,yaw,lean):
        hip_rotation = Quaternion((0,0,1),yaw*0.30)@Quaternion((1,0,0),lean*0.25)@self.pose.rest_world['Hips'].to_quaternion()
        self.pose.set_world('Hips',world_transform(self.hip_rest+Vector((0,0,-drop)),hip_rotation,self.pose.scale))
        for name,weight in [('Spine',0.20),('Spine1',0.25),('Spine2',0.25)]:
            self.pose.local_rotation(name,Quaternion((0,1,0),yaw*weight)@Quaternion((1,0,0),lean*weight))
        self.pose.local_rotation('Neck',Quaternion((0,1,0),-yaw*0.30))
        self.pose.local_rotation('Head',Quaternion((0,1,0),-yaw*0.25))

    def arms(self,grip,free_left=0.0,left_target=None):
        right = grip@self.k_right.inverted()
        left_point = grip@Matrix.Translation((0,self.socket['left_grasp_blade_axis_m']*self.ratio,0))
        if left_target is None:
            free = self.guard_grip();free.translation = Vector((0.35,-0.12,1.20))*self.ratio
        else:
            free = left_target
        left_point = interpolate_transform(left_point,free,free_left)
        left = left_point@self.k_left.inverted()
        self.pose.limb('RightArm','RightForeArm','RightHand',right.translation,Vector((-0.60,0.05,1.15))*self.ratio,right.to_quaternion())
        self.pose.limb('LeftArm','LeftForeArm','LeftHand',left.translation,Vector((0.60,0.05,1.15))*self.ratio,left.to_quaternion())
        # Mount is expressed in physical metres; wrapper scale is compensated.
        local = self.k_right.copy();local.translation /= self.pose.scale
        actual = self.pose.matrix('RightHand')@local@Matrix.Diagonal((1/self.pose.scale,1/self.pose.scale,1/self.pose.scale,1))
        self.last_grip = actual
        self.frame_metrics = {'grip_target_error_m':(actual.translation-grip.translation).length,'blade_azimuth_deg':math.degrees(math.atan2(actual.to_3x3().col[1].x,-actual.to_3x3().col[1].y)),'blade_pitch_deg':math.degrees(math.asin(max(-1,min(1,actual.to_3x3().col[1].normalized().z))))}

    def planted_feet(self,lift=0.0):
        for side,sign in [('Left',1),('Right',-1)]:
            foot = self.pose.rest_world[side+'Foot']
            position = foot.translation.copy()
            position.x = sign*0.19*self.ratio
            position.y = (-0.11 if side=='Left' else 0.10)*self.ratio
            position.z += lift
            self.pose.limb(side+'UpLeg',side+'Leg',side+'Foot',position,Vector((sign*0.13,-0.9,0.5))*self.ratio,foot.to_quaternion())

    def pose_action(self,name,t,duration,attack=None):
        self.pose.reset()
        u=t/duration
        drop=self.guard['pelvis_drop_m']*self.ratio
        yaw=math.radians(-6)
        lean=math.radians(self.guard['lean_deg'])
        grip=self.guard_grip()
        free_left=0.0
        left_target=None
        foot_lift=0.0
        if name=='idle':
            breath=math.sin(2*math.pi*u)
            drop+=.0015*self.ratio*breath
            lean+=math.radians(.3)*breath
            grip.translation.z+=.002*self.ratio*breath
        if attack:
            startup,active,recovery = attack['startup'],attack['active'],attack['recovery']
            arc=math.radians(attack['arc'] if attack['arc']<359 else 150)
            omega=arc/active
            guard_angle=math.radians(self.guard['azimuth_deg'])
            if t<startup:
                theta=hermite(guard_angle,-arc/2,0,omega,startup,t)
                amount=smooth(t/startup)
            elif t<=startup+active:
                theta=-arc/2+omega*(t-startup);amount=1.0
            else:
                theta=hermite(arc/2,guard_angle,omega,0,recovery,t-startup-active)
                amount=1-smooth((t-startup-active)/recovery)
            pitch=math.radians(self.guard['pitch_deg'])*(1-amount)
            radial=Vector((math.sin(theta),-math.cos(theta),0))
            sweep=Vector((0,-0.04,1.12))*self.ratio+radial*(0.315*self.ratio)
            position=Vector(self.guard['grip_m']).lerp(sweep/self.ratio,amount)*self.ratio
            grip=frame_matrix(position,theta,pitch)
            yaw=math.radians(-6)*(1-amount)+theta*0.60*amount
            lean += math.radians(6 if name.startswith('light') else 10)*amount
            drop += (0.03 if name.startswith('light') else 0.06)*self.ratio*amount
            free_left=amount
            if name=='skill_3':
                phase=smooth(t/startup) if t<startup else (1-smooth((t-startup-active)/recovery) if t>startup+active else 1.0)
                raised=frame_matrix(Vector((-0.05,-0.36,1.52))*self.ratio,0,math.radians(75))
                impact=frame_matrix(Vector((-0.05,-0.38,1.20))*self.ratio,0,math.radians(-85))
                if t<startup:target=raised
                elif t<startup+active:target=interpolate_transform(raised,impact,smooth((t-startup)/(active*0.35)))
                else:target=impact
                grip=interpolate_transform(self.guard_grip(),target,phase)
                free_left=0.0;yaw=math.radians(-6);lean=math.radians(5+8*phase)
        elif name=='parry':
            amount=smooth(t/.05) if t<.05 else (1-smooth((t-.13)/.09) if t>.13 else 1)
            target=frame_matrix(Vector((-.03,-.43,1.30))*self.ratio,0,math.radians(65))
            grip=interpolate_transform(grip,target,amount)
        elif name=='hit':
            recoil=math.sin(math.pi*u)
            lean-=math.radians(14)*recoil;drop+=.02*self.ratio*recoil
            grip.translation += Vector((0,.035,-.025))*self.ratio*recoil
        elif name=='dodge':
            amount=math.sin(math.pi*u)**2
            drop+=.13*self.ratio*amount;lean+=math.radians(20)*amount
            foot_lift=.16*self.ratio*amount
            grip.translation += Vector((0,0,-.10))*self.ratio*amount
        elif name=='charge':
            # The runtime holds the last charge sample until release. Keep a
            # prepared pose there rather than pulsing back to the idle guard.
            amount=smooth(u)
            drop+=.045*self.ratio*amount;lean+=math.radians(4)*amount
            grip.translation.z += .045*self.ratio*amount
        elif name=='heal':
            amount=math.sin(math.pi*u)**2
            target=self.guard_grip();target.translation=Vector((.08,-.28,1.32))*self.ratio
            left_target=target;free_left=amount
            grip.translation.x-=.06*self.ratio*amount
        self.body(drop,yaw,lean)
        self.planted_feet(foot_lift)
        # Keep the reviewed grasp across actions. An extra charge squeeze drove
        # the fingertips farther into the hilt without adding useful readiness.
        self.fingers()
        if name=='death':
            amount=smooth(u)
            hip=self.pose.matrix('Hips')
            rotation=Quaternion((1,0,0),-math.pi/2*amount)
            hip_position=hip.translation.lerp(Vector((self.hip_rest.x,self.hip_rest.y,.20*self.ratio)),amount)
            self.pose.set_world('Hips',world_transform(hip_position,rotation@hip.to_quaternion(),self.pose.scale))
            fall=Matrix.Translation(hip_position)@rotation.to_matrix().to_4x4()@Matrix.Translation(-hip.translation)
            grip=fall@grip
            end=frame_matrix(Vector((-.22,.12,.25))*self.ratio,math.pi,0)
            grip=interpolate_transform(grip,end,amount)
            free_left=amount
            left_target=frame_matrix(Vector((.20,.28,.37))*self.ratio,math.pi,0)
        self.arms(grip,free_left,left_target)
        self.pose.apply()
        return self.frame_metrics.copy()

    def gait_upper_body(self,rig,seconds,state):
        self.pose.load_current()
        hip_yaw = float(rig.get('_gait_pelvis_yaw',0.0))
        for name in ['Spine','Spine1','Spine2']:
            self.pose.local_rotation(name,Quaternion((0,1,0),-hip_yaw/3.0)@Quaternion((1,0,0),math.radians(5.0)/3.0))
        self.pose.local_rotation('Neck',Quaternion())
        self.pose.local_rotation('Head',Quaternion())
        hip=self.pose.matrix('Hips').translation
        grip=self.guard_grip()
        grip.translation.z += hip.z-(self.hip_rest.z-self.guard['pelvis_drop_m']*self.ratio)
        self.fingers()
        self.arms(grip,0)
        self.pose.apply()


def interpolate_transform(a,b,weight):
    result=a.to_quaternion().slerp(b.to_quaternion(),weight).to_matrix().to_4x4()
    result.translation=a.translation.lerp(b.translation,weight)
    return result


def skin_coordinates(mesh):
    graph=bpy.context.evaluated_depsgraph_get();obj=mesh.evaluated_get(graph);data=obj.to_mesh()
    try:
        coordinates=np.empty(len(data.vertices)*3,dtype=np.float64)
        data.vertices.foreach_get('co',coordinates)
        coordinates=coordinates.reshape((-1,3))
        matrix=np.array(obj.matrix_world,dtype=np.float64)
        return coordinates@matrix[:3,:3].T+matrix[:3,3]
    finally:obj.to_mesh_clear()


def skin_bounds(mesh):
    points=skin_coordinates(mesh)
    return {'min':points.min(axis=0).tolist(),'max':points.max(axis=0).tolist()}


def main():
    global SOURCE_DIGEST,SOURCE_PATH
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not bpy.app.background or bpy.app.version[:3]!=(4,3,2):raise ValueError('Use isolated Blender 4.3.2 background process')
    source=args.source.resolve(strict=True);output=args.output.resolve();report_path=output.with_suffix('.authoring.json')
    if output.exists() or report_path.exists() or output==source or output.suffix.lower()!='.glb':raise ValueError('Separate new GLB/report outputs required; originals never overwritten')
    recipe=json.loads(args.recipe.read_text());SOURCE_PATH=source;SOURCE_DIGEST=sha(source)
    if SOURCE_DIGEST!=recipe['source_sha256']:raise ValueError('Source hash differs from the reviewed profile')
    fps=recipe['fps'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps;bpy.context.scene.render.fps_base=1.0
    bpy.ops.import_scene.gltf(filepath=str(source),import_pack_images=True)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    if set(rig.data.bones.keys())!=REQUIRED:raise ValueError('Incompatible 53-bone role set')
    helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape}
    body_objects=[o for o in bpy.context.scene.objects if o not in helpers]
    meshes=[o for o in body_objects if o.type=='MESH']
    if len(meshes)!=1:raise ValueError('Expected exactly one character body mesh')
    mesh=meshes[0];mesh.data.calc_loop_triangles()
    if len(mesh.data.loop_triangles)!=recipe['triangles']:raise ValueError('Unexpected source topology')
    if any(not b.use_inherit_rotation or b.inherit_scale!='FULL' for b in rig.data.bones):raise ValueError('Unsupported bone inheritance')
    discarded=[a.name for a in bpy.data.actions]
    for obj in body_objects:obj.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    rig.data.pose_position='POSE';rig.animation_data_create()
    author=Author(rig,recipe);attacks=attack_contract(recipe['profile'])
    durations={name:sum(a[k] for k in ['startup','active','recovery']) for name,a in attacks.items()}
    durations.update({'idle':1.60,'hit':.28,'death':1.10} if recipe['profile']=='sentinel' else {'idle':1.60,'dodge':.32,'parry':.22,'hit':.15,'charge':.65,'heal':.35,'death':1.10})
    rig.data.pose_position='REST';bpy.context.view_layer.update()
    rest_points=skin_coordinates(mesh)
    edges=np.array([tuple(edge.vertices) for edge in mesh.data.edges],dtype=np.int64)
    rest_lengths=np.linalg.norm(rest_points[edges[:,1]]-rest_points[edges[:,0]],axis=1)
    edges=edges[rest_lengths>=.002];rest_lengths=rest_lengths[rest_lengths>=.002]
    rig.data.pose_position='POSE'
    actions={};reports={}
    for name,duration in durations.items():
        count=round(duration*fps)
        samples=[];metrics=[];floor_values=[];edge_samples=[]
        for index in range(count+1):
            time=index/fps
            metric=author.pose_action(name,time,duration,attacks.get(name))
            points=skin_coordinates(mesh);floor=float(points[:,2].min());correction=max(0.0,-floor)
            if correction>.00001:
                hip=author.pose.matrix('Hips');hip.translation.z+=correction
                author.pose.set_world('Hips',hip);author.pose.apply()
                author.last_grip.translation.z+=correction
                points=skin_coordinates(mesh)
            floor_values.append(float(points[:,2].min()))
            if index%10==0 or index==count:
                ratios=np.linalg.norm(points[edges[:,1]]-points[edges[:,0]],axis=1)/rest_lengths
                edge_samples.append({'time':time,'max_edge_stretch_ratio':float(ratios.max()),'min_edge_length_ratio':float(ratios.min())})
            samples.append((time,author.pose.values()));metrics.append({'time':time,**metric,'floor_lift_m':correction})
        if name=='idle':
            import copy
            samples[-1]=(duration,copy.deepcopy(samples[0][1]))
        actions[name]=key_action(rig,name,samples,fps)
        active_metrics=[m for m in metrics if name in attacks and attacks[name]['startup']-1e-8<=m['time']<=attacks[name]['startup']+attacks[name]['active']+1e-8]
        reports[name]={'duration_seconds':duration,'authorship':'project-authored semantic IK','loop':name=='idle','loop_endpoint_max_channel_error':0.0 if name=='idle' else None,'samples':metrics,'max_grip_target_error_m':max(m['grip_target_error_m'] for m in metrics),'active_window':{'start':attacks[name]['startup'],'end':attacks[name]['startup']+attacks[name]['active'],'gameplay_arc_deg':attacks[name]['arc']} if name in attacks else None,'active_azimuth_deg':[m['blade_azimuth_deg'] for m in active_metrics],'minimum_skinned_floor_z_m':min(floor_values),'deformation_samples':edge_samples,'deformation_scope':'Actual evaluated mesh edges >=2mm at10Hz plus endpoints; ratios are measurements, not quality approval.'}
        print('AUTHORED',name,duration,flush=True)
    from character_gait import author_locomotion
    gait=author_locomotion(rig,recipe['height_m'],walk_speed=recipe['locomotion']['walk_speed'],run_speed=recipe['locomotion']['run_speed'],upper_body_callback=author.gait_upper_body,fps=fps,include_idle=False)
    actions.update(gait['actions']);reports.update(gait['reports'])
    for name,action in actions.items():
        action.name=name
        if action.name!=name:raise ValueError('Action-name collision: '+name)
    author.pose.reset();actions['RESET']=key_action(rig,'RESET',[(0.0,author.pose.values()),(1/fps,author.pose.values())],fps)
    expected=set(durations)|{'idle','walk','run','walk_back','walk_left','walk_right','RESET'}
    if set(actions)!=expected:raise ValueError('Action set does not match recipe')
    rig.animation_data.action=actions['idle'];bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in body_objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.authored-',dir=output.parent) as staging:
        staged=Path(staging)/output.name
        bpy.ops.export_scene.gltf(filepath=str(staged),export_format='GLB',use_selection=True,use_renderable=True,export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_optimize_animation_size=False,export_nla_strips=False,export_extras=True)
        from inspect_glb import inspect_glb
        inspection=inspect_glb(staged,require_skin=True,required_clips=sorted(expected),require_embedded=True)
        if not inspection['requirements_met'] or inspection['counts']['animations']!=len(expected):
            raise ValueError('Exported clip names/structure differ from authored action set')
        actual_durations={a['name']:a['duration_seconds'] for a in inspection['animations']}
        for name,duration in durations.items():
            if abs(actual_durations[name]-duration)>.0001:raise ValueError('Exported duration drift: '+name)
        if sha(source)!=SOURCE_DIGEST:raise ValueError('Original changed; refusing publication')
        report={'status':'authored_prototype_requires_visual_gameplay_review','source':{'file':source.name,'sha256':SOURCE_DIGEST,'unchanged':True},'profile':recipe['profile'],'blender':bpy.app.version_string,'source_actions_discarded':discarded,'source_fcurves_copied_or_sampled':0,'actions':reports,'expected_clips':sorted(expected),'root_motion':'No object translation or physics/gameplay tracks. Horizontal locomotion remains code-owned.','max_ik_reach_clamp_m':author.pose.max_reach_clamp,'finger_curl_rad':recipe['finger_curl_rad'],'weapon_socket':{**recipe['weapon_socket'],'rig_uniform_scale':author.pose.scale,'physical_offset_m':[v*author.ratio for v in recipe['weapon_socket']['offset_m']],'local_offset':[v*author.ratio/author.pose.scale for v in recipe['weapon_socket']['offset_m']],'weapon_child_uniform_scale':1/author.pose.scale},'output_sha256':sha(staged),'exported_durations_seconds':actual_durations,'structural_inspection':{k:inspection[k] for k in ['structurally_valid','requirements_met','counts']},'limitations':['Procedural prototype, not AAA or final anatomy/material/deformation approval.','No runtime crossfade: arbitrary locomotion-to-action and forced cancellations can change pose abruptly.','AoE skill2/3 volumes are rune effects, not physical blade-length coverage.']}
        staged_report=Path(staging)/report_path.name;staged_report.write_text(json.dumps(report,indent=2)+'\n')
        os.link(staged,output)
        try:os.link(staged_report,report_path)
        except Exception:output.unlink();raise
    print('RUNEFALL_AUTHORED_CHARACTER_OK',output,flush=True)


if __name__=='__main__':
    code=0
    try:main()
    except SystemExit as e:code=0 if e.code in (None,0) else 1
    except Exception:traceback.print_exc();code=1
    finally:
        if SOURCE_PATH is not None and sha(SOURCE_PATH)!=SOURCE_DIGEST:
            print('ERROR: source SHA changed',flush=True);code=1
        sys.stdout.flush();sys.stderr.flush()
    if code:os._exit(code)
