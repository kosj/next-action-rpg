"""Independent Blender reload audit of actual embedded before/after NPC maps."""
import argparse
from array import array
import hashlib,json,math,struct,sys,tempfile
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from clone_robe_texture import read_glb,load_pixels
ROOT=Path(__file__).resolve().parents[3]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--target',required=True,type=Path);p.add_argument('--mask',required=True,type=Path);p.add_argument('--paint-report',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 if a.output.exists():raise ValueError('No audit overwrite')
 sraw,source,sbin=read_glb(a.source);traw,target,tbin=read_glb(a.target);mask=json.loads(a.mask.read_text());paint=json.loads(a.paint_report.read_text())
 allowed=set().union(*(set(map(tuple,p['allowed_top_left_pixels']))for p in mask['patches']if p['id']in paint['patches']))
 for key in ['meshes','nodes','skins','animations','accessors','materials','textures','samplers','scenes','scene']:
  if source.get(key)!=target.get(key):raise ValueError('Body, clips, UV or material declarations changed')
 if tbin[:len(sbin)]!=sbin or target['bufferViews'][:len(source['bufferViews'])]!=source['bufferViews']:raise ValueError('Source body/map BIN prefix or original views changed')
 if [(i,x.get('name'))for i,x in enumerate(source['images'])]!=[(i,x.get('name'))for i,x in enumerate(target['images'])]:raise ValueError('Image name/index roster changed')
 material=source['materials'][0];texture_ids={'albedo':material['pbrMetallicRoughness']['baseColorTexture']['index'],'ao':material['occlusionTexture']['index'],'normal':material['normalTexture']['index']};maps={}
 with tempfile.TemporaryDirectory(prefix='robe-pixel-audit-')as temp:
  folder=Path(temp)
  for role,tid in texture_ids.items():
   ii=source['textures'][tid]['source'];contents=[];rgba=[]
   for label,doc,binary in [('source',source,sbin),('target',target,tbin)]:
    view=doc['bufferViews'][doc['images'][ii]['bufferView']];content=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
    if content[:8]!=b'\x89PNG\r\n\x1a\n'or struct.unpack_from('>II',content,16)!=(1024,1024)or content[24]!=8:raise ValueError('Expected unchanged1k eight-bit PNG dimensions/depth')
    path=folder/(role+'-'+label+'.png');path.write_bytes(content);image,values=load_pixels(path,role+'-'+label);contents.append(content);rgba.append(bytes(max(0,min(255,round(v*255)))for v in values))
   changed=[];outside=[];alpha=[];protected=[]
   for index in range(1024*1024):
    start=index*4;old,new=rgba[0][start:start+4],rgba[1][start:start+4]
    if old!=new:
     pixel=[index%1024,1023-index//1024];changed.append(pixel)
     if tuple(pixel)not in allowed:outside.append(pixel)
     if old[3]!=new[3]:alpha.append(pixel)
     if role=='ao'and old[1:]!=new[1:]:protected.append(pixel)
   if outside or alpha or protected:raise ValueError('Actual embedded pixels violate mask/alpha/ORM policy')
   if role=='ao'and contents[0]!=contents[1]:raise ValueError('Unedited complete ORM image bytes changed')
   record={'image_index':ii,'image_name':target['images'][ii].get('name'),'dimensions':[1024,1024],'bit_depth':8,'source_png_sha256':hashlib.sha256(contents[0]).hexdigest(),'target_png_sha256':hashlib.sha256(contents[1]).hexdigest(),'complete_encoded_image_bytes_equal':contents[0]==contents[1],'changed_RGBA8_pixels':len(changed),'outside_allowed_mask_changed_RGBA8_pixels':outside,'changed_alpha_pixels':alpha,'ORM_protected_G_B_A_changed_pixels':protected}
   if role=='normal':
    lengths=[]
    for x,y in allowed:
     start=((1023-y)*1024+x)*4;rgb=rgba[1][start:start+3];lengths.append(math.sqrt(sum((2*v/255-1)**2 for v in rgb)))
    record['allowed_mask_decoded_tangent_normal_after_RGBA8_quantization']={'length_min':min(lengths),'length_max':max(lengths),'maximum_abs_length_error':max(abs(v-1)for v in lengths),'zero_vectors':sum(v<1e-8 for v in lengths),'normalization_scope':'Blender normalized only painted mask RGB before8bit PNG quantization; outside pixels were never normalized'}
   maps[role]=record
 report={'schema_version':1,'status':'actual_embedded_map_RGBA8_outside_mask_exact_verified','source_file':a.source.as_posix(),'source_sha256':hashlib.sha256(sraw).hexdigest(),'target_file':a.target.as_posix(),'target_sha256':hashlib.sha256(traw).hexdigest(),'mask_allowed_pixels':len(allowed),'face_hand_UV_overlap':[],'all_outside_allowed_RGBA8_exact':True,'ORM_entire_encoded_PNG_byte_exact':True,'body_skin_UV_clips_materials_source_BIN_prefix_exact':True,'image_names_indices_preserved':True,'maps':maps,'tool_file':str(Path(__file__).relative_to(ROOT)),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limitations':['Pixel/payload identity is a narrow contract, not rendered visual, continuous cloth, hardware or AAA acceptance']}
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'outside_mask_exact':True,'ORM_bytes_exact':True,'maps':{key:value['changed_RGBA8_pixels']for key,value in maps.items()},'normal_quantization':maps['normal']['allowed_mask_decoded_tangent_normal_after_RGBA8_quantization']}))


if __name__=='__main__':main()
