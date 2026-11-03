"""Author materially raised/back-shoulder two-hand heavy cuts on immutable14e5.

Blender4.3.2 only, new outputs only. Per-clip100/500Hz export and lossless live
GLB compaction preserve every untouched animation/static payload semantically.
No runtime/curve files are installed. Actual reimported markers author each LUT.
"""
import argparse,hashlib,json,math,struct,sys,tempfile
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_character_actions import PoseRig,frame_matrix,interpolate_transform,key_action,world_transform,skin_coordinates
from author_fury_actions import FuryAuthor,sword_markers
from author_sentinel_recovery import pose_at,compare
from author_weight_actions import shortest_rotation_degrees
from append_character_animations import append_animations,read_glb
from compact_glb_live_data import compact_document,semantic_fingerprints
from character_gait import _sole_samples,_sample_soles


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ease(x):
 if not math.isfinite(x):raise ValueError('Finite progress required')
 x=max(0.,min(1.,x));v=x*x*x*(x*(x*6-15)+10)
 if not -1e-12<=v<=1+1e-12:raise ValueError('Envelope beyond roundoff')
 return max(0.,min(1.,v))
def ramp(t,a,b):return ease((t-a)/(b-a))
def cubic(points,u):
 a,b,c,d=map(Vector,points);v=1-u
 return a*v**3+b*(3*v*v*u)+c*(3*v*u*u)+d*u**3


class DecisiveAuthor(FuryAuthor):
 def __init__(self,rig,recipe,idle_basis):
  super().__init__(rig,recipe);self.idle_basis=idle_basis;self.contracts=recipe['attacks']
 def limb(self,upper,lower,end,target,pole,end_rotation):
  if upper not in ('LeftArm','RightArm'):return PoseRig.limb(self.pose,upper,lower,end,target,pole,end_rotation)
  start=self.pose.matrix(upper).translation.copy();direction=(target-start).normalized();distance=(target-start).length;maximum=self.pose.length[upper]+self.pose.length[lower]-.0001
  self.minimum_hand_distance=min(self.minimum_hand_distance,distance)
  if distance>maximum:self.reach_issues.append({'time_s':self.current_time,'action':self.current_action,'bone':upper,'distance_m':distance,'maximum_m':maximum})
  side=-1 if upper=='RightArm'else 1;chest=self.pose.matrix('Spine2').to_quaternion()@self.pose.rest_world['Spine2'].to_quaternion().inverted();anatomical=chest@Vector((side*.46,-.16,-.36));old=pole-start;old-=direction*old.dot(direction);new=anatomical-direction*anatomical.dot(direction)
  if new.length<.04*self.ratio:raise ValueError('Anatomical elbow plane approaches singularity')
  self.minimum_pole_margin=min(self.minimum_pole_margin,new.length);plane=old.normalized().lerp(new.normalized(),self.loading)
  if plane.length<.05:raise ValueError('Elbow-plane interpolation approaches cancellation')
  PoseRig.limb(self.pose,upper,lower,end,target,start+plane.normalized()*self.ratio,end_rotation)
  # Geometry-only IK here. An explicit whole-action shaft transport below
  # assigns its axial orientation and exact source-idle endpoint closure.
  for bone in (upper,lower):
   matrix=self.pose.matrix(bone);axis=matrix.to_3x3().normalized().col[1].normalized();relation=self.pose.rest_world[bone].to_quaternion().inverted()@self.pose.rest_world[end].to_quaternion();relative=end_rotation@relation.inverted()@matrix.to_quaternion().inverted();denominator=math.hypot(relative.w,axis.dot(Vector((relative.x,relative.y,relative.z))))
   self.arm_metrics.append({'bone':bone,'time_s':self.current_time,'action':self.current_action,'legacy_closest_twist_denominator':denominator})
 def travel(self,t):
  c=self.contracts[self.current_action]
  return c.get('active_lunge_m_s',0)*max(0,min(c.get('active_s',0),t-c.get('startup_s',0)))
 def feet_decisive(self,t,name):
  if name=='charge':return self.feet(t,False)
  c=self.contracts[name];s=c['startup_s'];a=c['active_s'];r=c['recovery_s'];end=s+a;duration=s+a+r;travel=self.travel(t)
  for side,sign in [('Left',1),('Right',-1)]:
   rest=self.pose.rest_world[side+'Foot'];point=rest.translation.copy();lift=0.
   if side=='Left':
    first,last=.03,s-.04;step=ramp(t,first,last);recover_begin=end+min(.16,r*.32);recover_end=duration-.06;recover=ramp(t,recover_begin,recover_end)
    world_y=-.11+(c['front_plant_y_m']+.11)*step
    world_y+=(-c['active_lunge_m_s']*a-.11-c['front_plant_y_m'])*recover
    point.x=(.19+.05*step-.05*recover)*self.ratio
    if first<t<last:lift=.12*math.sin(math.pi*(t-first)/(last-first))**2
    if recover_begin<t<recover_end:lift=.07*math.sin(math.pi*(t-recover_begin)/(recover_end-recover_begin))**2
   else:
    first,last=s-.04,end+.04;follow=ramp(t,first,last);recover=ramp(t,end+r*.40,duration-.02)
    world_y=.10-c['active_lunge_m_s']*a*follow;point.x=(-.19-.04*follow+.04*recover)*self.ratio
    if first<t<last:lift=.11*math.sin(math.pi*(t-first)/(last-first))**2
   point.y=(world_y+travel)*self.ratio;point.z+=lift*self.ratio
   self.pose.limb(side+'UpLeg',side+'Leg',side+'Foot',point,Vector((sign*.13,-.9,.5))*self.ratio,rest.to_quaternion())
 def pose_slice(self,name,t,duration):
  self.current_action=name;self.current_time=t;self.pose.reset();baseline=self.guard['pelvis_drop_m']*self.ratio
  if name=='charge':
   loading=ease(t/.65);coil=pelvis=torso=settle=recover=0.;drop=baseline+.16*loading;hips=-6-49*loading;chest=-6-59*loading;lean=5+5*loading;shift=Vector((-.035,.045,0))*loading
  else:
   c=self.contracts[name];s=c['startup_s'];a=c['active_s'];r=c['recovery_s'];end=s+a
   if name=='charged_heavy':
    loading=1.;coil=ramp(t,0,.20);pelvis=ramp(t,.23,.44);torso=ramp(t,.285,.52);settle=ramp(t,end,end+.12);recover=ramp(t,end+.12,duration)
    drop=baseline+.16+.015*coil-.09*pelvis+.06*settle;hips=-55-5*coil+95*pelvis;chest=-65-10*coil+125*torso;lean=10+10*torso;shift=Vector((-.035+.105*pelvis,.045-.11*pelvis,0))
   else:
    loading=ease(t/s);coil=0.;pelvis=ramp(t,s-.07,end-.015);torso=ramp(t,s-.035,end);settle=ramp(t,end,end+.035);recover=ramp(t,end+.035,duration)
    drop=baseline+.14*loading-.075*pelvis+.04*settle;hips=-6-36*loading+72*pelvis;chest=-6-42*loading+88*torso;lean=5+5*loading+8*torso;shift=Vector((-.025*loading+.07*pelvis,.025*loading-.04*pelvis,0))
   drop=baseline+(drop-baseline)*(1-recover);hips=hips*(1-recover)-6*recover;chest=chest*(1-recover)-6*recover;lean=lean*(1-recover)+5*recover;shift*=1-recover
  self.loading=loading*(1-recover);self.body(drop,math.radians(hips),math.radians(lean));hip=self.pose.matrix('Hips').copy();hip.translation+=shift*self.ratio;self.pose.set_world('Hips',hip)
  for bone,weight in [('Spine',.20),('Spine1',.25),('Spine2',.25)]:self.pose.local_rotation(bone,Quaternion((0,1,0),math.radians(chest)*weight)@Quaternion((1,0,0),math.radians(lean)*weight))
  chest_delta=self.pose.matrix('Spine2').to_quaternion()@self.pose.rest_world['Spine2'].to_quaternion().inverted();chest_position=self.pose.matrix('Spine2').translation
  if name=='charge':shoulder_load=loading
  else:
   c=self.contracts[name];f=ramp(t,c['startup_s'],c['startup_s']+c['active_s']);shoulder_load=loading*(1-.8*f)*(1-recover)
  for side,sign in [('Left',1),('Right',-1)]:
   bone=side+'Shoulder';m=self.pose.matrix(bone);lift=Quaternion(chest_delta@Vector((0,-1,0)),math.radians(14)*shoulder_load*sign)
   self.pose.set_world(bone,world_transform(m.translation,lift@m.to_quaternion(),self.pose.scale))
  def relative(position,az,pitch):
   m=frame_matrix(Vector(position)*self.ratio,math.radians(az),math.radians(pitch));return world_transform(chest_position+chest_delta@m.translation,chest_delta@m.to_quaternion(),1)
  loaded=relative((-.06,.045,.42),-120,66);cutstart=relative((-.06,0,.40),-105,66);cutend=relative((.04,-.25,-.035),30,-42);through=relative((.015,-.25,-.015),35,-40)
  if name=='charge':grip=interpolate_transform(self.guard_grip(),loaded,loading)
  else:
   c=self.contracts[name];s=c['startup_s'];a=c['active_s'];end=s+a
   if t<s:
    if name=='charged_heavy':
     wind=relative((-.07,.06,.45),-125,68)
     grip=interpolate_transform(loaded,wind,coil)if t<.29 else interpolate_transform(wind,cutstart,ramp(t,.29,s))
    else:grip=interpolate_transform(self.guard_grip(),cutstart,loading)
   elif t<=end:
    u=(t-s)/a;f=u*u*(3-2*u);pos=cubic([(-.06,0,.40),(-.10,-.18,.45),(.03,-.36,.20),(.04,-.25,-.035)],f)*self.ratio
    rotation=cutstart.to_quaternion().slerp(cutend.to_quaternion(),f);grip=world_transform(chest_position+chest_delta@pos,rotation,1)
   else:
    through_end=end+(.12 if name=='charged_heavy'else .035);grip=interpolate_transform(cutend,through,ramp(t,end,through_end));grip=interpolate_transform(grip,self.guard_grip(),recover)
  self.feet_decisive(t,name);self.fingers();self.arms(grip,0)
  if (name in ['charge','heavy']and t==0)or(name in ['charged_heavy','heavy']and t>=duration):
   self.pose.basis={n:m.copy()for n,m in self.idle_basis.items()};self.pose.cache={}
  self.pose.apply();scale=self.pose.scale;comp=Matrix.Diagonal((1/scale,1/scale,1/scale,1));right=self.k_right.copy();right.translation/=scale;left=self.k_left.copy();left.translation/=scale
  actual=self.pose.matrix('RightHand')@right@comp;support=self.pose.matrix('LeftHand')@left@comp;expected=actual@Vector((0,self.socket['left_grasp_blade_axis_m'],0));tip=actual@Vector((0,1.19,0))
  return {'time_s':t,'right_grip_target_error_m':(actual.translation-grip.translation).length,'left_support_actual_error_m':(support.translation-expected).length,'left_support_requested_error_m':(support.translation-grip@Vector((0,self.socket['left_grasp_blade_axis_m'],0))).length,'blade_tip_height_m':tip.z,'virtual_actor_forward_m':self.travel(t)if name!='charge'else 0.,'hips_world_m':list(self.pose.matrix('Hips').translation),'chest_world_m':list(self.pose.matrix('Spine2').translation),'requested_hips_yaw_deg':hips,'requested_chest_yaw_deg':chest,'requested_pelvis_drop_m':drop,'loading':self.loading,'full_body_local':self.pose.values()}


def transport_arm_frames(author,clips):
 """Explicit axial authoring, not a fallback division near singularity.

 Preserve every solved joint centre and hand world pose. Per-shaft minimal
 rotation transports an initial physical frame; its residual axial holonomy
 is closed smoothly against the actual source-idle end orientation.
 """
 entries=[];offset=0.;boundaries=[]
 for name,values in clips:
  boundaries.append((name,len(entries),len(values)))
  for t,local in values:
   author.pose.basis={bone:Matrix.LocRotScale(Vector(v[0]),Quaternion(v[1]),Vector(v[2]))for bone,v in local.items()};author.pose.cache={};world={bone:author.pose.matrix(bone).copy()for bone in author.pose.names};entries.append([offset+t,name,t,local,world,{}])
  offset+=values[-1][0]
 report={};duration=entries[-1][0]
 for side in ('Left','Right'):
  for bone,end in [(side+'Arm',side+'ForeArm'),(side+'ForeArm',side+'Hand')]:
   transported=[];previous_axis=previous_q=None
   for combined,name,t,local,world,changed in entries:
    axis=(world[end].translation-world[bone].translation).normalized();q=world[bone].to_quaternion()if previous_q is None else previous_axis.rotation_difference(axis)@previous_q;q.normalize();transported.append((axis,q));previous_axis=axis;previous_q=q
   desired=entries[-1][4][bone].to_quaternion();axis=transported[-1][0];delta=desired@transported[-1][1].inverted();delta.normalize()
   if delta.w<0:delta.negate()
   sine=Vector((delta.x,delta.y,delta.z)).dot(axis);residual=(Vector((delta.x,delta.y,delta.z))-axis*sine).length
   if residual>1e-5:raise ValueError('Shaft endpoint closure is not axial: '+str((bone,residual)))
   closure=2*math.atan2(sine,delta.w);report[bone]={'closure_degrees':math.degrees(closure),'nonaxial_residual_norm':residual}
   for entry,(axis,q)in zip(entries,transported):
    rotation=Quaternion(axis,closure*ease(entry[0]/duration))@q;entry[5][bone]=world_transform(entry[4][bone].translation,rotation,author.pose.scale)
 for combined,name,t,local,world,changed in entries:
  author.pose.basis={bone:Matrix.LocRotScale(Vector(v[0]),Quaternion(v[1]),Vector(v[2]))for bone,v in local.items()};author.pose.cache={}
  for side in ('Left','Right'):
   for part in ('Arm','ForeArm'):author.pose.set_world(side+part,changed[side+part])
   author.pose.set_world(side+'Hand',world[side+'Hand'])
  local.clear();local.update(author.pose.values())
 return {'policy':'Per-shaft minimum-rotation world frame; quintic actual-idle axial closure across contiguous actions; hands/world joint centres preserved','duration_s':duration,'bones':report}


def extract_curve(rig,clip,contract,fps,weapon,output,recipe):
 action=next(x for x in bpy.data.actions if x.name==clip);rig.animation_data.action=action;start=float(action.frame_range[0]);markers=sword_markers(weapon);scale=rig.matrix_world.to_scale().x;socket=Matrix(recipe['weapon_socket']['basis_columns']).transposed().to_4x4();socket.translation=Vector(recipe['weapon_socket']['offset_m'])/scale;comp=Matrix.Diagonal((1/scale,1/scale,1/scale,1));rows=[]
 for i in range(round(contract['active_s']/.002)+1):
  t=contract['startup_s']+i*.002;frame=start+t*fps;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();matrix=rig.matrix_world@rig.pose.bones['RightHand'].matrix@socket@comp
  def actor(p):
   v=matrix@p;return [-v.x,v.z+.025,v.y]
  rows.append({'time_s':round(t,6),'grip':actor(markers['GripOrigin']),'tip':actor(markers['BladeTip'])})
 if max(abs(math.dist(x['grip'],x['tip'])-1.19)for x in rows)>.0001:raise ValueError('Actual blade length contract failed')
 return {'schema_version':1,'coordinate_system':'actor_y_up_minus_z_forward','floor_offset_m':.025,'blade_length_m':1.19,'active_start_s':contract['startup_s'],'active_duration_s':contract['active_s'],'sample_step_s':.002,'source_metadata':{'asset_path':str(output),'sha256':sha(output)},'samples':rows}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);recipe=json.loads(a.recipe.read_text());source=a.source.resolve(strict=True);output=a.output.resolve();fps=500
 if bpy.app.version[:3]!=(4,3,2)or not bpy.app.background:raise ValueError('Blender4.3.2 required')
 if output.exists()or output.with_suffix('.authoring.json').exists():raise ValueError('New output only')
 if sha(source)!=recipe['source_sha256']:raise ValueError('Immutable14e5 source mismatch')
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps;bpy.ops.import_scene.gltf(filepath=str(source),import_pack_images=True);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');idle=pose_at(rig,'idle',0,fps);idle_basis={b.name:b.matrix_basis.copy()for b in rig.pose.bones}
 helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape};objects=[o for o in bpy.context.scene.objects if o not in helpers];meshes=[o for o in objects if o.type=='MESH']
 if len(meshes)!=1:raise ValueError('Actual single body mesh required')
 for o in objects:o.animation_data_clear()
 for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
 rig.data.pose_position='REST';bpy.context.view_layer.update();floor=float(skin_coordinates(meshes[0])[:,2].min());soles=_sole_samples(rig,meshes,floor);rig.data.pose_position='POSE';rig.animation_data_create();author=DecisiveAuthor(rig,recipe,idle_basis);actions={};reports={}
 for name in ['charge','charged_heavy','heavy']:
  c=recipe['attacks'][name];duration=c['duration_s'];hz=c['sample_hz'];rows=[];values=[]
  if name in ['charge','heavy']:author.previous_axial={}
  for index in range(round(duration*hz)+1):
   t=index/hz
   try:r=author.pose_slice(name,t,duration)
   except Exception as e:
    print('DECISIVE_FAILURE',json.dumps({'action':name,'time_s':t,'error':str(e),'reach_issues':author.reach_issues[-6:],'arm_metrics':author.arm_metrics[-6:]}),flush=True);raise
   rows.append({k:v for k,v in r.items()if k!='full_body_local'});translation=Vector((0,-r['virtual_actor_forward_m'],0));rows[-1]['soles_nominal_world']={side:[list(p+translation)for p in pp]for side,pp in _sample_soles(soles).items()};values.append((t,r['full_body_local']))
   if max(r['right_grip_target_error_m'],r['left_support_actual_error_m'],author.pose.max_reach_clamp)>.001:
    print('DECISIVE_REACH_FAILURE',json.dumps({'row':rows[-1],'clamp':author.pose.max_reach_clamp,'issues':author.reach_issues[-6:]}),flush=True);raise ValueError('Existing1mm authored key grip/reach gate failed')
  reports[name]={'duration_s':duration,'sample_hz':hz,'authored_keys':len(values),'samples':rows};actions[name]=values;print('DECISIVE_GEOMETRY_READY',name,len(values),flush=True)
 transport={'charge_charged':transport_arm_frames(author,[(n,actions[n])for n in ['charge','charged_heavy']]),'heavy':transport_arm_frames(author,[('heavy',actions['heavy'])])}
 for name,values in list(actions.items()):
  worst=max((shortest_rotation_degrees(x[1][b][1],y[1][b][1])/(y[0]-x[0]),b,x[0],y[0])for x,y in zip(values,values[1:])for b in x[1])
  if worst[0]>2700:raise ValueError('Existing2700deg/s authored-local gate failed: '+str((name,worst)))
  reports[name]['maximum_authored_local_deg_s']=worst;actions[name]=key_action(rig,name,values,fps);print('DECISIVE_ACTION_READY',name,len(values),worst,flush=True)
 output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='.decisive-',dir=output.parent)as directory:
  work=Path(directory);stage=source;grafts=[]
  for number,(name,action)in enumerate(actions.items()):
   rig.animation_data.action=action;bpy.context.scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT')
   for o in objects:o.select_set(True)
   bpy.context.view_layer.objects.active=rig;motion=work/(name+'.glb');step=fps//recipe['attacks'][name]['sample_hz']
   bpy.ops.export_scene.gltf(filepath=str(motion),export_format='GLB',use_selection=True,use_renderable=True,export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_nla_strips_merged_animation_name=name,export_anim_single_armature=False,export_force_sampling=True,export_frame_range=False,export_frame_step=step,export_optimize_animation_size=False,export_nla_strips=False,export_extras=True)
   exported,bin_data=read_glb(motion)
   if len(exported['animations'])!=1 or exported['animations'][0]['name']!=name:raise ValueError('Per-action export ambiguity')
   for sample in exported['animations'][0]['samplers']:
    accessor=exported['accessors'][sample['input']];view=exported['bufferViews'][accessor['bufferView']];offset=view.get('byteOffset',0)+accessor.get('byteOffset',0);count=accessor['count'];last=struct.unpack_from('<f',bin_data,offset+(count-1)*4)[0]
    if count!=round(recipe['attacks'][name]['duration_s']*recipe['attacks'][name]['sample_hz'])+1 or abs(last-recipe['attacks'][name]['duration_s'])>1e-6:raise ValueError('Per-action export sampling/duration differs from declared profile')
   next_stage=work/('stage-'+str(number)+'.glb');grafts.append(append_animations(stage,motion,next_stage,[name]));stage=next_stage
  graft_fingerprints=semantic_fingerprints(stage);source_fingerprints=semantic_fingerprints(source);compaction=compact_document(stage,output);selected_fingerprints=semantic_fingerprints(output)
  if graft_fingerprints!=selected_fingerprints:raise ValueError('Compaction changed actual semantic snapshot')
  for field in ['static_json_sha256','mesh_skin_sha256','images']:
   if source_fingerprints[field]!=selected_fingerprints[field]:raise ValueError('Static semantic payload changed: '+field)
  untouched={n:x for n,x in source_fingerprints['clips'].items()if n not in actions}
  if any(selected_fingerprints['clips'][n]!=x for n,x in untouched.items()):raise ValueError('Untouched clip semantic bytes changed')
  lineage={'source_sha256':sha(source),'output_sha256':sha(output),'static_semantic_exact':True,'untouched_clips':untouched,'selected_untouched_clips':{n:selected_fingerprints['clips'][n]for n in untouched},'source_light_clips':{n:source_fingerprints['clips'][n]for n in ['light_1','light_2','light_3']},'selected_light_clips':{n:selected_fingerprints['clips'][n]for n in ['light_1','light_2','light_3']},'graft_semantic_snapshot_sha256':graft_fingerprints['semantic_sha256'],'selected_semantic_snapshot_sha256':selected_fingerprints['semantic_sha256'],'compaction':compaction,'original_bin_prefix_identity_not_claimed_after_compaction':True};output.with_suffix('.lineage.json').write_text(json.dumps(lineage,indent=2)+'\n')
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps;bpy.ops.import_scene.gltf(filepath=str(output),import_pack_images=True);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');joins={'charge0':compare(idle,pose_at(rig,'charge',0,fps)),'charged_end':compare(idle,pose_at(rig,'charged_heavy',1.06,fps)),'heavy0':compare(idle,pose_at(rig,'heavy',0,fps)),'heavy_end':compare(idle,pose_at(rig,'heavy',.86,fps))};held=pose_at(rig,'charge',.65,fps);joins['held_to_release']=compare(held,pose_at(rig,'charged_heavy',0,fps))
 if any(x['max_joint_distance_m']>.001 or x['max_local_rotation_degrees']>.1 for x in joins.values()):raise ValueError('Actual source-idle/held join failed: '+str(joins))
 curves={}
 for name in ['charged_heavy','heavy']:
  data=extract_curve(rig,name,recipe['attacks'][name],fps,Path(recipe['weapon_source']['file']),output,recipe);path=output.with_suffix('.'+name+'-curve.json');path.write_text(json.dumps(data,indent=2)+'\n');curves[name]={'file':path.name,'sha256':sha(path)}
 report={'status':'authored_decisive_candidate_pending_independent_raw_skin_native_visual_review','source_sha256':sha(source),'output_sha256':sha(output),'author_tool_sha256':sha(__file__),'recipe_sha256':sha(a.recipe),'blender':bpy.app.version_string,'graft_stages':grafts,'compaction':compaction,'lineage_file':output.with_suffix('.lineage.json').name,'actions':reports,'actual_reimport_source_joins':joins,'max_reach_clamp_m':author.pose.max_reach_clamp,'minimum_shoulder_hand_distance_m':author.minimum_hand_distance,'minimum_anatomical_pole_margin_m':author.minimum_pole_margin,'explicit_axial_transport':transport,'legacy_decomposition_diagnostics':author.arm_metrics,'curves':curves,'limits':{'key_grip_reach_m':.001,'raw_native_marker_m':.003,'all53bone_deg_s':2700},'limitations':['No native/runtime/visual/skin/terrain/hardware/AAA approval','LUT is new and derived from actual reimported body; old charged curve identity is not claimed','Compaction rewrites accessor/view indices and BIN layout losslessly; original BIN prefix/body JSON identity not claimed']};output.with_suffix('.authoring.json').write_text(json.dumps(report,indent=2)+'\n');print('DECISIVE_CANDIDATE_AUTHORED',output,sha(output),flush=True)

if __name__=='__main__':main()
