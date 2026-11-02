"""Blender4.3.2: repair only three light clips' left elbow continuity.

Actual immutable source world hand targets at100Hz are preserved. Only
LeftArm/LeftForeArm/LeftHand TRS channels are grafted; body, right-hand weapon,
all other channels/clips and original BIN bytes remain untouched. Bad old
parent/child interpolation excursions are measured separately, not preserved
as an anatomical target. No gameplay, mesh, bind, weights or texture edits.
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


def author(raw,recipe):
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
 if a.output.exists()or a.output.with_suffix('.authoring.json').exists():raise ValueError('New candidate output required')
 if sha(source)!=recipe['source_sha256']:raise ValueError('Immutable source hash mismatch')
 raw=Raw(source);authored,metrics=author(raw,recipe);a.output.parent.mkdir(parents=True,exist_ok=True);proof=graft(raw,authored,a.output)
 report={'schema_version':1,'status':'first_continuity_candidate_pending_independent_raw_skin_native_raster_review','source_file':str(source),'source_sha256':sha(source),'output_file':str(a.output),'output_sha256':sha(a.output),'tool_file':__file__,'tool_sha256':sha(__file__),'recipe_file':str(a.recipe),'recipe_sha256':sha(a.recipe),'blender':bpy.app.version_string,'preservation':proof,'clips':metrics,'left_hand_policy':'Original100Hz worldkeytargets exact; old parent/child midpoint excursion is intentionally replaced by continuous target interpolation and must be measured separately.','limitations':['No engine, skin, visual, native alignment, hardware or AAA approval']}
 if sha(source)!=recipe['source_sha256']:raise ValueError('Source changed during authoring')
 a.output.with_suffix('.authoring.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output_sha256':report['output_sha256'],'new_BIN_bytes':proof['new_BIN_bytes'],'clips':metrics}))


if __name__=='__main__':main()
