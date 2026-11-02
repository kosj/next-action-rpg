"""Blender image-datablock clone paint restricted to verified robe UV pixels.

No PIL, atlas resynthesis, resampling or whole-model export. Original images are
loaded through Blender; only declared mask pixels/channels are cloned from an
adjacent ivory cloth patch. Outside pixels are checked exactly after PNG reload.
Changed PNGs alone are grafted into existing image indices/names in the GLB.
"""
import argparse
from array import array
from copy import deepcopy
import hashlib,json,math,struct,sys,tempfile
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]


def digest(data):return hashlib.sha256(data).hexdigest()


def read_glb(path):
 raw=path.read_bytes();size,kind=struct.unpack_from('<I4s',raw,12)
 if struct.unpack_from('<4sII',raw)!=(b'glTF',2,len(raw))or kind!=b'JSON':raise ValueError('GLB2 required')
 doc=json.loads(raw[20:20+size]);offset=20+size;length,kind=struct.unpack_from('<I4s',raw,offset)
 if kind!=b'BIN\0'or offset+8+length!=len(raw):raise ValueError('One embedded BIN required')
 return raw,doc,raw[offset+8:]


def rgba_at(values,x,y,width=1024,height=1024):
 index=((height-1-y)*width+x)*4
 return values[index:index+4]


def stats(values,pixels,offset=(0,0)):
 rows=[rgba_at(values,x+offset[0],y+offset[1])for x,y in pixels]
 return {'pixel_count':len(rows),'min_rgba':[min(row[i]for row in rows)for i in range(4)],'max_rgba':[max(row[i]for row in rows)for i in range(4)],'mean_rgba':[sum(row[i]for row in rows)/len(rows)for i in range(4)]}


def load_pixels(path,name):
 image=bpy.data.images.load(str(path),check_existing=False);image.name=name;image.colorspace_settings.name='Non-Color'
 if list(image.size)!=[1024,1024]:raise ValueError('Every referenced NPC map must remain1024x1024')
 values=array('f',[0.0])*(1024*1024*4);image.pixels.foreach_get(values)
 return image,values


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--mask',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--diagnose-only',action='store_true');p.add_argument('--patch',action='append');p.add_argument('--channels',nargs='+',choices=['albedo','ao','normal'],default=['albedo']);p.add_argument('--output',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 if bpy.app.version[:3]!=(4,3,2)or not bpy.app.background:raise ValueError('Blender4.3.2 background required')
 if a.output_dir.exists()or a.output and a.output.exists():raise ValueError('Refuse overwrite')
 a.output_dir.mkdir(parents=True)
 raw,doc,binary=read_glb(a.source);mask=json.loads(a.mask.read_text())
 if digest(raw)!=mask['source_sha256']or mask['dimensions']!=[1024,1024]:raise ValueError('Source/mask mismatch')
 material=doc['materials'][0];texture_ids={'albedo':material['pbrMetallicRoughness']['baseColorTexture']['index'],'ao':material['occlusionTexture']['index'],'normal':material['normalTexture']['index']}
 image_ids={role:doc['textures'][tid]['source']for role,tid in texture_ids.items()}
 if len(doc['images']) != 3 or len(set(image_ids.values())) != 3:raise ValueError('Exactly three distinct PBR maps required')
 selected=[patch for patch in mask['patches']if patch['id']in a.patch]if a.patch else [patch for patch in mask['patches']if patch['paint_enabled']]
 if not selected:raise ValueError('No explicitly selected robe patch')
 if any(patch['protected_face_hand_uv_overlap']for patch in selected):raise ValueError('Face/hand UV overlap')
 report={'schema_version':1,'status':'diagnosis_only'if a.diagnose_only else 'bounded_Blender_clone_candidate_visual_pending','source_file':a.source.as_posix(),'source_sha256':digest(raw),'mask_file':a.mask.as_posix(),'mask_sha256':digest(a.mask.read_bytes()),'dimensions':[1024,1024],'maps':{},'patches':[x['id']for x in selected],'explicit_channels':a.channels,'image_indices_and_names_before':[{'index':i,'name':image.get('name')}for i,image in enumerate(doc['images'])],'outside_mask_pixels_exact':True,'ORM_G_B_exact':True,'tool_file':str(Path(__file__).relative_to(ROOT)),'tool_sha256':digest(Path(__file__).read_bytes())}
 changed_images={}
 with tempfile.TemporaryDirectory(prefix='robe-blender-')as temporary:
  temp=Path(temporary)
  for role,ii in image_ids.items():
   image_doc=doc['images'][ii];view=doc['bufferViews'][image_doc['bufferView']];content=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];original=temp/(role+'-source.png');original.write_bytes(content)
   image,values=load_pixels(original,role+'-original');painted=array('f',values);allowed=set().union(*(set(map(tuple,patch['allowed_top_left_pixels']))for patch in selected))
   diagnosis={patch['id']:{'destination':stats(values,patch['core_top_left_pixels']),'adjacent_clone_source':stats(values,patch['core_top_left_pixels'],patch['clone_top_left_offset_px'])}for patch in mask['patches']}
   entry={'image_index':ii,'image_name':image_doc.get('name'),'source_png_sha256':digest(content),'diagnosis_encoded_channels':diagnosis,'channel_policy':{'albedo':'RGB only','ao':'R only; G roughness and B metallic unchanged','normal':'RGB vector clone, decoded blend then normalize only in mask'}[role],'painted':False}
   if not a.diagnose_only and role in a.channels:
    for patch in selected:
     core=set(map(tuple,patch['core_top_left_pixels']));dx,dy=patch['clone_top_left_offset_px']
     for x,y in patch['allowed_top_left_pixels']:
      if not 0 <= x+dx < 1024 or not 0 <= y+dy < 1024:raise ValueError('Clone source outside image')
      distance=0 if (x,y)in core else min(math.hypot(x-cx,y-cy)for cx,cy in core)
      alpha=1.0 if distance==0 else max(0.0,1-distance/3)**2
      old=rgba_at(values,x,y);clone=rgba_at(values,x+dx,y+dy);target=[old[i]*(1-alpha)+clone[i]*alpha for i in range(3)]
      if role=='normal':
       vector=[2*v-1 for v in target];length=math.sqrt(sum(v*v for v in vector))
       if length<1e-8:raise ValueError('Zero tangent-space clone normal')
       target=[(v/length+1)*.5 for v in vector]
      index=((1023-y)*1024+x)*4
      for channel in ([0]if role=='ao'else [0,1,2]):painted[index+channel]=target[channel]
    image.pixels.foreach_set(painted);image.update();image.filepath_raw=str(a.output_dir/(role+'-clone.png'));image.file_format='PNG';image.save()
    saved=Path(image.filepath_raw);reloaded,actual=load_pixels(saved,role+'-reloaded')
    before=bytes(max(0,min(255,round(v*255)))for v in values);after=bytes(max(0,min(255,round(v*255)))for v in actual)
    changed=[];outside=[];wrong_channels=[]
    for index in range(1024*1024):
     if before[index*4:index*4+4]!=after[index*4:index*4+4]:
      x=index%1024;y=1023-index//1024;changed.append([x,y])
      if (x,y)not in allowed:outside.append([x,y])
      if role=='ao'and before[index*4+1:index*4+4]!=after[index*4+1:index*4+4]:wrong_channels.append([x,y])
    if outside or wrong_channels:raise ValueError('PNG roundtrip changed outside-mask pixels or protected ORM channels')
    entry.update(painted=True,output_file=saved.name,output_png_sha256=digest(saved.read_bytes()),changed_pixel_count=len(changed),changed_top_left_pixels=changed,outside_mask_changed_pixels=outside,protected_ORM_G_B_changed_pixels=wrong_channels,after={patch['id']:stats(actual,patch['core_top_left_pixels'])for patch in selected})
    changed_images[ii]=saved.read_bytes()
   report['maps'][role]=entry
  if not a.diagnose_only:
   if not a.output:raise ValueError('An explicit separate GLB output is required')
   changed_doc=deepcopy(doc);new_binary=bytearray(binary)
   for ii,content in sorted(changed_images.items()):
    while len(new_binary)%4:new_binary.append(0)
    view={'buffer':0,'byteOffset':len(new_binary),'byteLength':len(content)};new_binary.extend(content);changed_doc['bufferViews'].append(view);changed_doc['images'][ii]['bufferView']=len(changed_doc['bufferViews'])-1
   changed_doc['buffers'][0]['byteLength']=len(new_binary)
   while len(new_binary)%4:new_binary.append(0)
   encoded=json.dumps(changed_doc,separators=(',',':'),ensure_ascii=False).encode();encoded+=b' '*((-len(encoded))%4)
   output=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(new_binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(new_binary),b'BIN\0')+new_binary
   for key in ['meshes','nodes','skins','animations','accessors','materials','textures','samplers','scenes','scene']:
    if changed_doc.get(key)!=doc.get(key):raise ValueError('Non-image source declaration changed')
   if bytes(new_binary[:len(binary)])!=binary:raise ValueError('Source BIN prefix altered during image graft')
   if [(i,x.get('name'))for i,x in enumerate(changed_doc['images'])]!=[(i,x.get('name'))for i,x in enumerate(doc['images'])]:raise ValueError('Image name/index roster changed')
   a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(output);report.update(output_file=a.output.as_posix(),output_sha256=digest(output),output_bytes=len(output),original_BIN_prefix_exact=True,geometry_skin_UV_clips_materials_exact=True,image_names_indices_preserved=True)
  if digest(a.source.read_bytes())!=digest(raw):raise ValueError('Source changed')
 (a.output_dir/'paint-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'output_sha256':report.get('output_sha256'),'maps':{role:{'painted':entry['painted'],'changed_pixels':entry.get('changed_pixel_count')}for role,entry in report['maps'].items()}}))


if __name__=='__main__':main()
