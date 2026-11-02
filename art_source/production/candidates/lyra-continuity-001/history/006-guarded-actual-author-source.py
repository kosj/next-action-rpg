"""Blender4.3.2: repair only three light clips' left elbow continuity.

Only LeftArm/LeftForeArm/LeftHand TRS channels are grafted; body, right-hand
weapon, all other channels/clips and original BIN bytes remain untouched.
The original-key repair and creative free-arm recipe are separate modes.
Creative mode deliberately changes the free left-hand targets, preserving
actual idle/start/end grasp. No gameplay, mesh, bind, weights or texture edits.
"""
import argparse,bisect,copy,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from append_character_animations import read_glb,_local_matrix
from audit_impact_curve import slerp

BONES=('LeftArm','LeftForeArm','LeftHand')
PROPERTIES={'translation':3,'rotation':4,'scale':3}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def smooth(x):
 x=max(0.,min(1.,x));return x*x*(3-2*x)


class Raw:
 def __init__(self,path):
  self.doc,self.binary=read_glb(path);self.parents={c:i for i,n in enumerate(self.doc['nodes'])for c in n.get('children',[])};self.names={n.get('name'):i for i,n in enumerate(self.doc['nodes'])};self.cache={};self.clips={}
  for animation in self.doc['animations']:
   # The bind RESET uses STEP and is copied untouched, never sampled here.
   if animation['name']=='RESET':continue
   tracks=[]
   for channel in animation['channels']:
    sample=animation['samplers'][channel['sampler']]
    if sample.get('interpolation','LINEAR')!='LINEAR':raise ValueError('Literal LINEAR source required')
    tracks.append((channel['target']['node'],channel['target']['path'],[r[0]for r in self.accessor(sample['input'])],self.accessor(sample['output'])))
   self.clips[animation['name']]=tracks
 def accessor(self,index):
  if index not in self.cache:
   a=self.doc['accessors'][index];view=self.doc['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
   if a['componentType']!=5126 or a.get('sparse'):raise ValueError('Dense float animation required')
   off=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',width*4)
   self.cache[index]=[struct.unpack_from('<'+'f'*width,self.binary,off+i*stride)for i in range(a['count'])]
  return self.cache[index]
 def at(self,clip,time):
  nodes=[dict(n)for n in self.doc['nodes']]
  for index,prop,times,values in self.clips[clip]:
   j=max(0,min(len(times)-2,bisect.bisect_right(times,time)-1));u=max(0.,min(1.,(time-times[j])/(times[j+1]-times[j])))
   nodes[index][prop]=slerp(values[j],values[j+1],u)if prop=='rotation'else [a+(b-a)*u for a,b in zip(values[j],values[j+1])]
  local={i:Matrix(_local_matrix(n))for i,n in enumerate(nodes)};world={}
  def get(i):
   if i not in world:world[i]=get(self.parents[i])@local[i]if i in self.parents else local[i]
   return world[i]
  for i in range(len(nodes)):get(i)
  return local,world
 def named(self,world,name):return world[self.names[name]]


def frame(first,last,normal):
 y=(last-first).normalized();z=normal-y*normal.dot(y)
 if z.length<1e-7:raise ValueError('Bone frame degeneracy')
 z.normalize();x=y.cross(z).normalized()
 return Matrix((x,y,z)).transposed().to_quaternion()


def compose(point,rotation,scale):
 m=rotation.to_matrix().to_4x4()
 for column in range(3):
  for row in range(3):m[row][column]*=scale[column]
 m.translation=point
 return m


def smoother(value):
 x=max(0.0,min(1.0,value))
 result=x*x*x*(x*(x*6.0-15.0)+10.0)
 if not math.isfinite(result)or result < -1e-12 or result > 1.0+1e-12:
  raise ValueError('Quintic envelope materially outside its mathematical unit range')
 return max(0.0,min(1.0,result))


def author_free_arm(raw,recipe):
 """Anatomical counterweight first; no original free-hand fidelity claim.

 Source glTF scene coordinates are +Y up/+Z forward, before the existing
 runtime PI correction. Original body and shoulder/clavicle tracks are read
 only. The free hand follows that body rather than staying fixed in world.
 """
 if set(recipe['clips'])!={'light_1','light_2','light_3'} or recipe['sample_hz']!=100:
  raise ValueError('Creative scope requires exactly three100Hz light clips')
 settings=recipe['natural_counterweight']
 if settings['coordinate_system']!='source_gltf_scene_y_up_plus_z_forward_before_runtime_pi':
  raise ValueError('Explicit source coordinate convention required')
 idle_local,idle=raw.at('idle',0)
 idle_up=raw.named(idle,'LeftArm');idle_lower=raw.named(idle,'LeftForeArm');idle_hand=raw.named(idle,'LeftHand')
 idle_chest=raw.named(idle,'Spine2').to_quaternion()
 idle_direction=(idle_hand.translation-idle_up.translation).normalized()
 idle_pole=idle_lower.translation-idle_up.translation
 idle_pole-=idle_direction*idle_pole.dot(idle_direction);idle_pole.normalize()
 normal=(idle_lower.translation-idle_up.translation).cross(idle_hand.translation-idle_lower.translation).normalized()
 offsets={'LeftArm':frame(idle_up.translation,idle_lower.translation,normal).inverted()@idle_up.to_quaternion(),
          'LeftForeArm':frame(idle_lower.translation,idle_hand.translation,normal).inverted()@idle_lower.to_quaternion()}
 free_pole=Vector(settings['free_elbow_pole_direction']).normalized()
 load_offset=Vector(settings['load_hand_offset_from_shoulder_m'])
 release_offset=Vector(settings['release_end_hand_offset_from_shoulder_m'])
 idle_offset=idle_hand.translation-idle_up.translation
 hand_relative_rotation=idle_lower.to_quaternion().inverted()@idle_hand.to_quaternion()
 bind_hand_local_rotation=Matrix(_local_matrix(raw.doc['nodes'][raw.names['LeftHand']])).to_quaternion()
 output={};metrics={}
 for clip,windows in recipe['clips'].items():
  keys=sorted(set(t for _,_,times,_ in raw.clips[clip]for t in times));duration=keys[-1]
  if abs(duration-sum(windows.values()))>1e-6:raise ValueError('Clip/gameplay timing mismatch')
  if any(b-a>.010001 for a,b in zip(keys,keys[1:])):raise ValueError('Original100Hz grid required')
  # Solve intended midpoint targets independently of the exported local TRS
  # interpolation. Only original100Hz keys are written to the derived GLB.
  dense=sorted(set(keys+[(a+b)*.5 for a,b in zip(keys,keys[1:])]))
  entries=[];minimum_projection=1.0;maximum_old_hand_deviation=0.0
  for t in dense:
   local,world=raw.at(clip,t);up=raw.named(world,'LeftArm');old_lower=raw.named(world,'LeftForeArm');old_hand=raw.named(world,'LeftHand')
   body_delta=raw.named(world,'Spine2').to_quaternion()@idle_chest.inverted()
   startup=windows['startup'];active_end=startup+windows['active']
   amount=smoother(t/startup) if t<startup else 1.0 if t<active_end else 1.0-smoother((t-active_end)/windows['recovery'])
   active_fraction=smoother((t-startup)/windows['active'])
   offset=load_offset.lerp(release_offset,active_fraction)
   guard=up.translation+body_delta@idle_offset
   free=up.translation+body_delta@offset
   target=guard.lerp(free,amount)
   direction=(target-up.translation).normalized();distance=(target-up.translation).length
   first=(old_lower.translation-up.translation).length;second=(old_hand.translation-old_lower.translation).length
   if distance>=first+second-.0001 or distance<=abs(first-second)+.0001:
    raise ValueError('Anatomical target outside unmodified arm reach; no clamp permitted')
   pole=body_delta@idle_pole.lerp(free_pole,amount)
   pole.normalize();pole-=direction*pole.dot(direction)
   minimum_projection=min(minimum_projection,pole.length)
   if pole.length<.2:raise ValueError('Anatomical direction approaches pole degeneracy')
   pole.normalize();along=(first*first-second*second+distance*distance)/(2*distance)
   height=math.sqrt(first*first-along*along)
   middle=up.translation+direction*along+pole*height
   normal=(middle-up.translation).cross(target-middle).normalized()
   changed={raw.names['LeftArm']:compose(up.translation,frame(up.translation,middle,normal)@offsets['LeftArm'],up.to_scale()),
            raw.names['LeftForeArm']:compose(middle,frame(middle,target,normal)@offsets['LeftForeArm'],old_lower.to_scale()),
            raw.names['LeftHand']:compose(target,idle_hand.to_quaternion(),old_hand.to_scale())}
   maximum_old_hand_deviation=max(maximum_old_hand_deviation,(target-old_hand.translation).length)
   entries.append((t,local,world,changed))
  closures={}
  for bone,end in [('LeftArm','LeftForeArm'),('LeftForeArm','LeftHand')]:
   index=raw.names[bone];end_index=raw.names[end];transported=[];axes=[];previous_axis=None;previous_q=None
   for t,local,world,changed in entries:
    axis=(changed[end_index].translation-changed[index].translation).normalized()
    q=changed[index].to_quaternion() if previous_q is None else previous_axis.rotation_difference(axis)@previous_q
    q.normalize();transported.append(q);axes.append(axis);previous_axis=axis;previous_q=q
   delta=entries[-1][3][index].to_quaternion()@transported[-1].inverted();delta.normalize()
   if delta.w<0:delta.negate()
   sine=Vector((delta.x,delta.y,delta.z)).dot(axes[-1]);closure=2*math.atan2(sine,delta.w)
   residual=(Vector((delta.x,delta.y,delta.z))-axes[-1]*sine).length
   if residual>1e-5:raise ValueError('Natural endpoint closure is not axial')
   closures[bone]={'angle_degrees':math.degrees(closure),'nonaxial_quaternion_vector_norm':residual}
   for (t,local,world,changed),q,axis in zip(entries,transported,axes):
    old=changed[index];q=Quaternion(axis,closure*smoother(t/duration))@q
    changed[index]=compose(old.translation,q,old.to_scale())
  rows=[];targets=[];minimum_below_shoulder=math.inf
  for t,local,world,changed in entries:
   hand_index=raw.names['LeftHand'];lower=changed[raw.names['LeftForeArm']];hand=changed[hand_index]
   wrist_relative=hand_relative_rotation
   if settings.get('wrist_policy')=='blend_actual_bind_only_when_free':
    startup=windows['startup'];active_end=startup+windows['active']
    free_amount=smoother(t/startup) if t<startup else 1.0 if t<active_end else 1.0-smoother((t-active_end)/windows['recovery'])
    wrist_relative=hand_relative_rotation.slerp(bind_hand_local_rotation,free_amount)
   hand_q=lower.to_quaternion()@wrist_relative
   changed[hand_index]=compose(hand.translation,hand_q,hand.to_scale())
   below=changed[raw.names['LeftArm']].translation.y-lower.translation.y
   minimum_below_shoulder=min(minimum_below_shoulder,below)
   actor_rotation=Quaternion((0,1,0),math.pi)@hand_q
   targets.append({'time_s':t,'is_source_key':t in keys,'hand_position_m':list(hand.translation),
                   'hand_rotation_xyzw':[hand_q.x,hand_q.y,hand_q.z,hand_q.w],
                   'actor_hand_position_m':[-hand.translation.x,hand.translation.y+.025,-hand.translation.z],
                   'actor_hand_rotation_xyzw':[actor_rotation.x,actor_rotation.y,actor_rotation.z,actor_rotation.w],
                   'elbow_position_m':list(lower.translation),'shoulder_position_m':list(changed[raw.names['LeftArm']].translation),
                   'source_hand_position_m':list(raw.named(world,'LeftHand').translation),
                   'elbow_below_shoulder_m':below})
   if t not in keys:continue
   samples={}
   for name in BONES:
    index=raw.names[name];parent=raw.parents[index]
    matrix=changed.get(parent,world[parent]).inverted()@changed[index]
    if t==keys[0]or t==keys[-1]:matrix=local[index]
    location,rotation,scale=matrix.decompose();rotation.normalize()
    samples[name]={'translation':list(location),'rotation':[rotation.x,rotation.y,rotation.z,rotation.w],'scale':list(scale)}
   rows.append(samples)
  if minimum_below_shoulder<settings['minimum_elbow_below_shoulder_m']:
   raise ValueError('Free counterguard raises elbow outside the declared lower envelope')
  output[clip]={'times':keys,'rows':rows}
  metrics[clip]={'keys':len(keys),'duration_s':duration,'target_coordinate_system':settings['coordinate_system'],
                 'maximum_desired_hand_deviation_from_original_m':maximum_old_hand_deviation,
                 'minimum_elbow_below_shoulder_m':minimum_below_shoulder,
                 'minimum_projected_unit_pole_norm':minimum_projection,'direction_norm_units':'dimensionless',
                 'bone_axial_closure':closures,'target_samples':targets,
                 'hand_policy':('Deliberately new free-hand world targets; quintic free-phase blend from actual idle-grasp wrist local to actual static/bind wrist local; exact original start/end grasp' if settings.get('wrist_policy')=='blend_actual_bind_only_when_free' else 'Deliberately new free-hand world targets; source-idle wrist-local orientation retained; exact original start/end grasp')}
 return output,metrics


def author(raw,recipe):
 if recipe.get('creative_free_arm'):return author_free_arm(raw,recipe)
 idle_local,idle=raw.at('idle',0);a=raw.named(idle,'LeftArm');b=raw.named(idle,'LeftForeArm');h=raw.named(idle,'LeftHand');chest=raw.named(idle,'Spine2').to_quaternion()
 n=(b.translation-a.translation).cross(h.translation-b.translation).normalized()
 offsets={'LeftArm':frame(a.translation,b.translation,n).inverted()@a.to_quaternion(),'LeftForeArm':frame(b.translation,h.translation,n).inverted()@b.to_quaternion()}
 idle_direction=(h.translation-a.translation).normalized();base=b.translation-a.translation;base-=idle_direction*base.dot(idle_direction);base.normalize()
 output={};metrics={}
 for clip,windows in recipe['clips'].items():
  source_times=sorted(set(t for index,prop,times,values in raw.clips[clip]for t in times));duration=source_times[-1]
  if abs(duration-sum(windows.values()))>1e-6:raise ValueError('Clip/gameplay timing mismatch')
  for previous,current in zip(source_times,source_times[1:]):
   if current-previous>.010001:raise ValueError('Original key grid is coarser than100Hz')
  # Transport in the moving chest frame instead of projecting a fixed vector
  # through its near-axis direction. Explicitly close the resulting holonomy;
  # the final pole is the original authored end pole, not a late frame snap.
  entries=[];transported=[];previous_direction=None;previous_pole=None
  for t in source_times:
   local,world=raw.at(clip,t);up=raw.named(world,'LeftArm');lower=raw.named(world,'LeftForeArm');hand=raw.named(world,'LeftHand')
   current_chest=raw.named(world,'Spine2').to_quaternion();direction=(hand.translation-up.translation).normalized();chest_direction=current_chest.inverted()@direction
   if previous_direction is None:
    pole=lower.translation-up.translation;pole-=direction*pole.dot(direction);pole=current_chest.inverted()@pole.normalized()
   else:
    pole=previous_direction.rotation_difference(chest_direction)@previous_pole
    pole-=chest_direction*pole.dot(chest_direction);pole.normalize()
   entries.append((t,local,world,current_chest,chest_direction));transported.append(pole.copy());previous_direction=chest_direction.copy();previous_pole=pole.copy()
  last=entries[-1];end_up=raw.named(last[2],'LeftArm');end_lower=raw.named(last[2],'LeftForeArm');end_hand=raw.named(last[2],'LeftHand');end_direction=(end_hand.translation-end_up.translation).normalized()
  end_pole=end_lower.translation-end_up.translation;end_pole-=end_direction*end_pole.dot(end_direction);end_pole=last[3].inverted()@end_pole.normalized();last_direction=last[4]
  closure=math.atan2(last_direction.dot(transported[-1].cross(end_pole)),transported[-1].dot(end_pole))
  rows=[];world_rows=[];maximum_orthogonality=0.0
  for (t,local,world,current_chest,chest_direction),transport in zip(entries,transported):
   up=raw.named(world,'LeftArm');lower=raw.named(world,'LeftForeArm');hand=raw.named(world,'LeftHand');start=up.translation;target=hand.translation;delta=target-start;distance=delta.length;direction=delta.normalized()
   first=(lower.translation-start).length;second=(target-lower.translation).length
   along=(first*first-second*second+distance*distance)/(2*distance);height=math.sqrt(max(0.,first*first-along*along))
   if height<1e-5:raise ValueError('Source arm approaches straight/fold singularity')
   startup=windows['startup'];active_end=startup+windows['active']
   load=smooth(t/startup) if t<startup else 1.0 if t<active_end else 1.0-smooth((t-active_end)/windows['recovery'])
   bias=math.radians(recipe.get('pole_load_bias_degrees',{}).get(clip,0.0))*load
   closed=Quaternion(chest_direction,closure*smooth(t/duration)+bias)@transport
   pole=current_chest@closed;pole.normalize();maximum_orthogonality=max(maximum_orthogonality,abs(pole.dot(direction)))
   middle=start+direction*along+pole*height
   normal=(middle-start).cross(target-middle).normalized()
   new_up=compose(start,frame(start,middle,normal)@offsets['LeftArm'],up.to_scale())
   new_lower=compose(middle,frame(middle,target,normal)@offsets['LeftForeArm'],lower.to_scale())
   changed={raw.names['LeftArm']:new_up,raw.names['LeftForeArm']:new_lower,raw.names['LeftHand']:hand.copy()}
   world_rows.append((t,local,world,changed))
   samples={}
   for name in BONES:
    index=raw.names[name];parent=raw.parents[index];matrix=(changed.get(parent,world[parent])).inverted()@changed[index]
    # Endpoints retain the original authored local rows exactly.
    if t==source_times[0]or t==source_times[-1]:matrix=local[index]
    location,rotation,scale=matrix.decompose();rotation.normalize();samples[name]={'translation':list(location),'rotation':[rotation.x,rotation.y,rotation.z,rotation.w],'scale':list(scale)}
   rows.append(samples)
  axial_closure={}
  if recipe.get('orientation_policy')=='per-shaft minimum rotation with smooth endpoint closure':
   # Bone centers keep the continuous elbow solution above. Independently
   # transport each shaft's orientation, so its plane does not force axial
   # rotation into the upper arm and an opposite wrist compensation.
   for bone,end in [('LeftArm','LeftForeArm'),('LeftForeArm','LeftHand')]:
    index=raw.names[bone];end_index=raw.names[end];transported_q=[];axes=[];previous_axis=None;previous_q=None
    for t,local,world,changed in world_rows:
     axis=(changed[end_index].translation-changed[index].translation).normalized()
     q=changed[index].to_quaternion() if previous_q is None else previous_axis.rotation_difference(axis)@previous_q
     q.normalize();transported_q.append(q);axes.append(axis);previous_axis=axis;previous_q=q
    desired=world_rows[-1][3][index].to_quaternion();delta=desired@transported_q[-1].inverted();delta.normalize()
    if delta.w<0:delta.negate()
    axis=axes[-1];sine=Vector((delta.x,delta.y,delta.z)).dot(axis);closure_q=2*math.atan2(sine,delta.w)
    perpendicular=(Vector((delta.x,delta.y,delta.z))-axis*sine).length
    if perpendicular>1e-5:raise ValueError('Endpoint closure is not purely axial')
    axial_closure[bone]={'closure_angle_degrees':math.degrees(closure_q),'end_closure_nonaxial_quaternion_vector_norm':perpendicular}
    previous_twist=None;twist_angles=[]
    for (t,local,world,changed),q,axis in zip(world_rows,transported_q,axes):
     old=changed[index];q=Quaternion(axis,closure_q*smooth(t/duration))@q
     if bone=='LeftForeArm':
      reference=changed[raw.names['LeftHand']].to_quaternion()@raw.named(idle,'LeftHand').to_quaternion().inverted()@raw.named(idle,'LeftForeArm').to_quaternion()
      relative=reference@q.inverted();relative.normalize()
      if relative.w<0:relative.negate()
      twist=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(axis),relative.w)
      if previous_twist is not None:
       while twist-previous_twist>math.pi:twist-=2*math.pi
       while twist-previous_twist<-math.pi:twist+=2*math.pi
      previous_twist=twist;twist_angles.append(math.degrees(twist))
      q=Quaternion(axis,twist*recipe.get('forearm_hand_twist_fraction',0.0))@q
     changed[index]=compose(old.translation,q,old.to_scale())
    if twist_angles:axial_closure[bone]['reference_hand_twist_range_degrees']=[min(twist_angles),max(twist_angles)]
   rows=[]
   for t,local,world,changed in world_rows:
    samples={}
    for name in BONES:
     index=raw.names[name];parent=raw.parents[index];matrix=(changed.get(parent,world[parent])).inverted()@changed[index]
     if t==source_times[0]or t==source_times[-1]:matrix=local[index]
     location,rotation,scale=matrix.decompose();rotation.normalize();samples[name]={'translation':list(location),'rotation':[rotation.x,rotation.y,rotation.z,rotation.w],'scale':list(scale)}
    rows.append(samples)
  output[clip]={'times':source_times,'rows':rows};metrics[clip]={'keys':len(source_times),'duration_s':duration,'pole_policy':'chest-local parallel transport with smooth explicit end-pole holonomy compensation','closure_angle_degrees':math.degrees(closure),'pole_load_bias_degrees':recipe.get('pole_load_bias_degrees',{}).get(clip,0.0),'maximum_unit_direction_orthogonality_abs_dot':maximum_orthogonality,'direction_norm_units':'dimensionless; no physical pole clearance asserted','orientation_policy':recipe.get('orientation_policy','bend-plane frame'),'bone_axial_closure':axial_closure,'forearm_hand_twist_fraction':recipe.get('forearm_hand_twist_fraction',0.0)}
 return output,metrics


def graft(raw,authored,path):
 doc=copy.deepcopy(raw.doc);binary=bytearray(raw.binary)
 def accessor(rows,kind):
  while len(binary)%4:binary.append(0)
  start=len(binary);width={'SCALAR':1,'VEC3':3,'VEC4':4}[kind];flat=[v for row in rows for v in row]
  if not all(math.isfinite(v)for v in flat):raise ValueError('Nonfinite authored values')
  data=struct.pack('<'+'f'*len(flat),*flat);binary.extend(data);view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(data)})
  value={'bufferView':view,'componentType':5126,'count':len(rows),'type':kind}
  if kind=='SCALAR':value.update(min=[min(flat)],max=[max(flat)])
  doc['accessors'].append(value);return len(doc['accessors'])-1
 for animation in doc['animations']:
  name=animation.get('name')
  if name not in authored:continue
  rows=authored[name];time_accessor=accessor([[t]for t in rows['times']],'SCALAR');changed=0
  for channel in animation['channels']:
   bone=doc['nodes'][channel['target']['node']].get('name');prop=channel['target']['path']
   if bone not in BONES:continue
   values=[row[bone][prop]for row in rows['rows']];output=accessor(values,'VEC4'if prop=='rotation'else'VEC3');channel['sampler']=len(animation['samplers']);animation['samplers'].append({'input':time_accessor,'output':output,'interpolation':'LINEAR'});changed+=1
  if changed!=9:raise ValueError('Expected exactlynine left-arm TRS channels')
 if bytes(binary[:len(raw.binary)])!=raw.binary:raise ValueError('Source BIN prefix changed')
 for key in ['nodes','meshes','skins','materials','images','textures','samplers','scenes','scene']:
  if doc.get(key)!=raw.doc.get(key):raise ValueError('Source static payload declaration changed')
 for old,new in zip(raw.doc['animations'],doc['animations']):
  if old['name']not in authored and old!=new:raise ValueError('Unrelated clip changed')
  if old['name']in authored:
   for a,b in zip(old['channels'],new['channels']):
    if raw.doc['nodes'][a['target']['node']].get('name')not in BONES and a!=b:raise ValueError('Unrelated bone channel changed')
 doc['buffers'][0]['byteLength']=len(binary)
 while len(binary)%4:binary.append(0)
 encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();encoded+=b' '*((-len(encoded))%4);data=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
 path.write_bytes(data)
 return {'source_BIN_prefix_exact':True,'static_payload_declarations_exact':True,'unrelated_clips_exact':True,'unchanged_bone_channels_in_three_clips_exact':True,'changed_bones':list(BONES),'changed_clips':list(authored),'new_BIN_bytes':len(binary)-len(raw.binary)}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);recipe=json.loads(a.recipe.read_text());source=Path(recipe['source_file'])
 if bpy.app.version[:3]!=(4,3,2)or not bpy.app.background:raise ValueError('Blender4.3.2 background required')
 if a.output.exists()or a.output.with_suffix('.authoring.json').exists()or a.output.with_suffix('.targets.json').exists():raise ValueError('New candidate output required')
 if sha(source)!=recipe['source_sha256']:raise ValueError('Immutable source hash mismatch')
 raw=Raw(source);authored,metrics=author(raw,recipe);a.output.parent.mkdir(parents=True,exist_ok=True);proof=graft(raw,authored,a.output)
 report={'schema_version':1,'status':'first_continuity_candidate_pending_independent_raw_skin_native_raster_review','source_file':str(source),'source_sha256':sha(source),'output_file':str(a.output),'output_sha256':sha(a.output),'tool_file':__file__,'tool_sha256':sha(__file__),'recipe_file':str(a.recipe),'recipe_sha256':sha(a.recipe),'blender':bpy.app.version_string,'preservation':proof,'clips':metrics,'left_hand_policy':('Deliberately reauthored FREE left-hand world targets and orientation; actual source idle/start/end grasp preserved. New key/mid targets and source deviations are explicit in each clip target_samples.' if recipe.get('creative_free_arm') else 'Original100Hz worldkeytargets exact; old parent/child midpoint excursion is intentionally replaced by continuous target interpolation and must be measured separately.'),'limitations':['No engine, skin, visual, native alignment, hardware or AAA approval']}
 if sha(source)!=recipe['source_sha256']:raise ValueError('Source changed during authoring')
 if recipe.get('creative_free_arm'):
  target_table={'schema_version':1,'scope':'Deliberately new FREE left-hand semantic targets, evaluated at original100Hz keys and their independent analytic midpoints. Not original-key fidelity, gameplay mutation or visual approval.',
                'coordinate_system':'actor_y_up_minus_z_forward','units':'metres; radians only where explicitly labeled','time_units':'source_clip_seconds','floor_offset_m':.025,
                'source_coordinate_system':'source_gltf_scene_y_up_plus_z_forward_before_runtime_pi',
                'conversion':{'position':'[-raw_x,raw_y+0.025,-raw_z]','rotation':'Quaternion(axis=[0,1,0],angle_radians=PI) * raw_world_rotation','offset_already_in_actor_coordinates':True},
                'source_metadata':{'asset_path':str(a.output),'sha256':sha(a.output),'parent_path':str(source),'parent_sha256':sha(source),'recipe_path':str(a.recipe),'recipe_sha256':sha(a.recipe),'tool_sha256':sha(__file__)},
                'clips':{name:{'duration_s':row['duration_s'],'key_hz':100,'midpoint_targets_included':True,'samples':row['target_samples']}for name,row in metrics.items()}}
  a.output.with_suffix('.targets.json').write_text(json.dumps(target_table,indent=2)+'\n')
 a.output.with_suffix('.authoring.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output_sha256':report['output_sha256'],'new_BIN_bytes':proof['new_BIN_bytes'],'clips':{name:{key:value for key,value in row.items()if key!='target_samples'}for name,row in metrics.items()}}))


if __name__=='__main__':main()
