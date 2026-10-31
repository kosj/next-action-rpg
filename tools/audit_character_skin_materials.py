"""Read GLB atlas/UV evidence; optionally split an explicitly reviewed face mask.

Images are decoded and sampled only, never painted, resized, baked or written.
Audit mode never creates a model. Candidate mode keeps the original BIN prefix
and geometry attributes exact; only primitive index grouping/material JSON is
appended. Every result remains pending neutral/game visual review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent))
from derive_character_eyes import read_glb,accessor
from repair_character_weights import Skin


def sha(data):return hashlib.sha256(data).hexdigest()


def sample(image,uv):
    """Bilinear level0 glTF UV (top-left image origin), repeat default sampler."""
    height,width=image.shape[:2];p=np.mod(uv,1)*[width,height]-.5
    x0=np.floor(p[:,0]).astype(int);y0=np.floor(p[:,1]).astype(int)
    tx=(p[:,0]-x0)[:,None];ty=(p[:,1]-y0)[:,None]
    a=image[y0%height,x0%width];b=image[y0%height,(x0+1)%width]
    c=image[(y0+1)%height,x0%width];d=image[(y0+1)%height,(x0+1)%width]
    return ((1-ty)*((1-tx)*a+tx*b)+ty*((1-tx)*c+tx*d))/255


def distribution(values):
    a=np.asarray(values)
    if not len(a):return {'samples':0}
    return {'samples':len(a),'min':float(a.min()),'p10':float(np.quantile(a,.1)),
            'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),
            'max':float(a.max()),'mean':float(a.mean())}


def inside(points,polygon):
    result=np.ones(points.shape[:-1],dtype=bool)
    for i,start in enumerate(polygon):
        edge=polygon[(i+1)%len(polygon)]-start;relative=points-start
        result&=edge[0]*relative[...,1]-edge[1]*relative[...,0]>=-1e-12
    return result


def data(source,original):
    raw,document,binary=read_glb(source);skin=Skin(original)
    for field in ['nodes','skins','animations','images','textures','samplers']:
        if document.get(field)!=skin.doc.get(field):raise ValueError('Unexpected source preservation difference: '+field)
    p=document['meshes'][0]['primitives'][0];attrs={name:accessor(document,binary,index) for name,index in p['attributes'].items()}
    pos=attrs['POSITION'].astype(float);j=attrs['JOINTS_0'].astype(int);w=attrs['WEIGHTS_0'].astype(float)
    matrices=skin.transforms(None,0);v=np.einsum('vkij,vj->vki',matrices[j,:3,:3],pos)+matrices[j,:3,3]
    world=np.einsum('vki,vk->vi',v,w);faces=accessor(document,binary,p['indices']).reshape(-1,3).astype(int)
    images=[];image_records=[]
    for img in document['images']:
        view=document['bufferViews'][img['bufferView']];offset=view.get('byteOffset',0)
        payload=bytes(binary[offset:offset+view['byteLength']]);decoded=Image.open(io.BytesIO(payload));decoded.load()
        images.append(np.asarray(decoded.convert('RGB'),dtype=float))
        image_records.append({'name':img.get('name'),'pixels':list(decoded.size),'bytes':len(payload),'sha256':sha(payload)})
    return raw,document,binary,attrs,world,faces,images,image_records


def audit(args):
    output=args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Use a new/empty audit output')
    source=args.input_body.resolve(strict=True);original=args.original.resolve(strict=True)
    raw,g,binary,a,world,faces,images,image_records=data(source,original)
    material=g['materials'][g['meshes'][0]['primitives'][0].get('material',0)];pbr=material.get('pbrMetallicRoughness',{})
    def image_for(texture_info):return images[g['textures'][texture_info['index']]['source']]
    normal=image_for(material['normalTexture']);orm=image_for(pbr['metallicRoughnessTexture']);albedo=image_for(pbr['baseColorTexture'])
    bary=np.array([[1/3]*3,[.8,.1,.1],[.1,.8,.1],[.1,.1,.8],[.5,.5,0],[.5,0,.5],[0,.5,.5]])
    points=np.einsum('sk,fkj->fsj',bary,world[faces]);uv=np.einsum('sk,fkj->fsj',bary,a['TEXCOORD_0'][faces]);flat=uv.reshape(-1,2)
    rgb=sample(albedo,flat).reshape(len(faces),-1,3);packed=sample(orm,flat).reshape(len(faces),-1,3);n=sample(normal,flat).reshape(len(faces),-1,3)*2-1
    n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    normal_tilt=np.degrees(np.arccos(np.clip(n[:,:,2],-1,1)))
    tri=world[faces];face_normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);face_normal/=np.maximum(np.linalg.norm(face_normal,axis=1,keepdims=True),1e-12)
    # Default/rest skin transform is near identity in this recorded source.
    vertex_normal=a['NORMAL'][faces].astype(float);vertex_normal/=np.maximum(np.linalg.norm(vertex_normal,axis=2,keepdims=True),1e-12)
    shading_angle=np.degrees(np.arccos(np.clip((vertex_normal*face_normal[:,None,:]).sum(2),-1,1)))
    boxes={
      'forehead_core':[-.028,.028,1.704,1.725,.075,.15],
      'nose_core':[-.012,.012,1.635,1.682,.105,.155],
      'left_cheek_core':[-.052,-.026,1.625,1.660,.075,.145],
      'right_cheek_core':[.027,.053,1.625,1.660,.075,.145],
      'chin_core':[-.022,.024,1.590,1.613,.075,.135],
      'armor_chest':[-.095,.095,1.290,1.450,.075,.29],
      'hair_crown':[-.075,.075,1.758,1.820,-.045,.12]}
    stats={}
    for name,box in boxes.items():
        selected=(points[:,:,0]>=box[0])&(points[:,:,0]<=box[1])&(points[:,:,1]>=box[2])&(points[:,:,1]<=box[3])&(points[:,:,2]>=box[4])&(points[:,:,2]<=box[5])&(face_normal[:,2,None]>.15)
        ids=np.flatnonzero(selected.any(1))
        stats[name]={'box_source_gltf_world_y_up_m':box,'sample_count':int(selected.sum()),'triangle_ids':ids.tolist(),
            'effective_metallic_B':distribution(packed[:,:,2][selected]*pbr.get('metallicFactor',1)),
            'effective_roughness_G':distribution(packed[:,:,1][selected]*pbr.get('roughnessFactor',1)),
            'occlusion_R':distribution(packed[:,:,0][selected]),'normal_map_tangent_tilt_degrees':distribution(normal_tilt[selected]),
            'geometric_vertex_normal_to_face_normal_degrees':distribution(shading_angle[ids].ravel()),
            'albedo_srgb_mean':rgb[selected].mean(0).tolist() if selected.any() else None}
    polygon=np.array([[-.024,1.591],[.026,1.591],[.054,1.615],[.065,1.655],[.062,1.701],[.044,1.731],[.014,1.737],[-.012,1.736],[-.043,1.731],[-.060,1.703],[-.064,1.661],[-.052,1.621]])
    domain=inside(tri[:,:,:2],polygon).all(1)&(tri[:,:,2].min(1)>.07)&(tri[:,:,2].max(1)<.16)&(face_normal[:,2]>.15)
    warm=(rgb[:,:,0]>rgb[:,:,1]*1.08+1.5/255)&(rgb[:,:,1]>rgb[:,:,2]*1.03)
    certain=domain&warm.all(1);uncertain=domain&~warm.all(1)
    proposed=np.flatnonzero(certain)
    per_triangle=[]
    for i in np.flatnonzero(domain):
        per_triangle.append({'triangle_id':int(i),'source_vertex_indices':faces[i].tolist(),'world_vertices_m':tri[i].tolist(),
          'uv':a['TEXCOORD_0'][faces[i]].tolist(),'albedo_mean_srgb':rgb[i].mean(0).tolist(),
          'metallic_median':float(np.median(packed[i,:,2])),'roughness_median':float(np.median(packed[i,:,1])),
          'all_samples_warm_skin_color':bool(warm[i].all()),'proposed_selection':bool(certain[i])})
    output.mkdir(parents=True,exist_ok=True)
    mask={'status':'pending_ownership_review','source_sha256':sha(raw),'primitive':0,
          'selector':'All3vertices inside explicit face polygon/front-depth; all7 level0 albedo samples warm. Conservative proposal, not semantic ground truth.',
          'source_gltf_world_y_up_polygon_xy_m':polygon.tolist(),'front_depth_m':[.07,.16],
          'proposed_skin_triangle_ids':proposed.tolist(),'uncertain_triangle_ids':np.flatnonzero(uncertain).tolist(),
          'triangle_records':per_triangle,'excluded':'Separate eye GLB, inner-lid primitive1, outside face polygon; hair ownership remains reviewable uncertainty'}
    (output/'proposed-skin-mask.json').write_text(json.dumps(mask,indent=2)+'\n')
    report={'status':'quantitative_read_only_audit','source':{'path':str(source),'sha256':sha(raw),'bytes':len(raw)},
      'original_archive':{'path':str(original),'sha256':sha(original.read_bytes())},'material_json':material,
      'effective_gltf_defaults':{'metallicFactor':pbr.get('metallicFactor',1),'roughnessFactor':pbr.get('roughnessFactor',1),'normalScale':material['normalTexture'].get('scale',1)},
      'map_channels':'glTF metallicRoughness uses G=roughness,B=metallic; occlusionR; maps sampled as linear data; basecolor sRGB',
      'sampling':'Seven deterministic barycentric level0 bilinear UV samples per triangle; repeat; glTF top-left image convention; not pixel editing or camera mip simulation',
      'images':image_records,'regions':stats,'proposed_mask_triangles':len(proposed),'uncertain_mask_triangles':int(uncertain.sum()),
      'no_candidate_generated':True,'original_and_input_unchanged':sha(source.read_bytes())==sha(raw),
      'tool_sha256':sha(Path(__file__).read_bytes()),
      'limits':['Spatial/color mask is a conservative proposal and requires visual ownership review','Normal-map tilt and mesh normal angles do not alone identify the cause of faceting','Neutral and actual game previews required for any material derivative; AAA pending']}
    (output/'material-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'source':report['source'],'defaults':report['effective_gltf_defaults'],'regions':stats,
                      'proposed_mask_triangles':len(proposed),'uncertain_mask_triangles':int(uncertain.sum())},indent=2))


def render_ownership(args):
    """In-memory 3D diagnostic material assignment; no source/model save."""
    import bpy
    from mathutils import Vector
    import render_glb_review as shared
    source=args.input_body.resolve(strict=True);output=args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Use a new ownership output')
    mask=json.loads(args.review_mask.read_text());raw=source.read_bytes()
    if sha(raw)!=mask['source_sha256']:raise ValueError('Ownership source SHA changed')
    _,g,_,_,world,faces,_,_=data(source,args.original.resolve(strict=True))
    selected=mask['proposed_skin_triangle_ids']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source),import_pack_images=True)
    imported=list(bpy.context.scene.objects)
    helpers={bone.custom_shape for obj in imported if obj.type=='ARMATURE' for bone in obj.pose.bones if bone.custom_shape}
    for helper in helpers:helper.hide_render=True
    imported=[obj for obj in imported if obj not in helpers]
    for obj in imported:
        obj.animation_data_clear()
        if obj.type=='ARMATURE':obj.data.pose_position='REST'
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
    meshes=[obj for obj in imported if obj.type=='MESH']
    if len(meshes)!=1:raise ValueError('Expected one body mesh excluding importer helpers')
    obj=meshes[0]
    if len(obj.data.polygons)!=sum(g['accessors'][p['indices']]['count']//3 for p in g['meshes'][0]['primitives']):raise ValueError('Polygon order contract changed')
    evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh();mapping_error=0.
    try:
        for index in selected:
            actual=[evaluated.matrix_world@mesh.vertices[i].co for i in mesh.polygons[index].vertices]
            expected=[Vector((p[0],-p[2],p[1])) for p in world[faces[index]]]
            mapping_error=max(mapping_error,max(min((p-q).length for q in actual) for p in expected))
    finally:evaluated.to_mesh_clear()
    if mapping_error>1e-5:raise ValueError('Blender polygon IDs do not match source ownership IDs')
    debug=bpy.data.materials.new('DiagnosticOnly_SelectedSkinOwnership');debug.use_nodes=True
    shader=debug.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.015,.55,.08,1);shader.inputs['Metallic'].default_value=0;shader.inputs['Roughness'].default_value=.9
    obj.data.materials.append(debug);slot=len(obj.data.materials)-1
    for index in selected:obj.data.polygons[index].material_index=slot
    lower,upper,size,center,_=shared.asset_bounds(imported,graph);span=max(size)
    scene=shared.configure_scene(640,8);scene.render.threads_mode='FIXED';scene.render.threads=1
    shared.neutral_floor(center,lower.z-span*.002,span)
    camera_data=bpy.data.cameras.new('OwnershipCamera');camera_data.type='ORTHO';camera_data.clip_start=.001;camera_data.clip_end=100
    camera=bpy.data.objects.new('OwnershipCamera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
    for name,power,width,offset in [('Key',500,1.5,(-1.5,-2.2,2.3)),('Fill',250,2,(2,-1.5,1.2)),('Rim',650,1.2,(0,2,2))]:
        light=shared.area_light(name,power*span*span,width*span);light.location=center+Vector(offset)*span;shared.aim(light,center)
    views={}
    for path in args.camera_reports:
        for view in json.loads(path.read_text())['views']:views[view['shot']]=view
    output.mkdir(parents=True,exist_ok=True);records=[]
    for name in ['face_front','face_side']:
        view=views[name];camera.location=view['camera_position_blender'];camera.rotation_euler=view['camera_rotation_euler'];camera_data.ortho_scale=view['orthographic_scale_m']
        scene.render.filepath=str(output/(name+'.png'));bpy.ops.render.render(write_still=True)
        records.append({'shot':name,'file':name+'.png','sha256':sha((output/(name+'.png')).read_bytes())})
    report={'status':'ownership_diagnostic_for_human_review','source_sha256':sha(raw),'source_unchanged':sha(source.read_bytes())==sha(raw),
      'selected_triangles':selected,'selected_count':len(selected),'uncertain_kept_original':mask['uncertain_triangle_ids'],
      'polygon_mapping_error_max_m':mapping_error,'images':records,'render_threads':1,
      'scope':'3D diagnostic material in isolated Blender memory; no source images/model written; no visual/AAA approval'}
    (output/'ownership-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('OWNERSHIP_REVIEW_RENDERED',output,flush=True)


def candidate(args):
    source=args.input_body.resolve(strict=True);output=args.output.resolve();mask=json.loads(args.review_mask.read_text())
    if mask.get('status')!='reviewed_ownership_for_isolated_trial':raise ValueError('Candidate requires explicit reviewed ownership status')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Use a new candidate output')
    raw,g,binary=read_glb(source)
    if sha(raw)!=mask['source_sha256']:raise ValueError('Reviewed mask source differs')
    selected=np.array(mask['proposed_skin_triangle_ids'],dtype=int);p=g['meshes'][0]['primitives'][0];old=accessor(g,binary,p['indices']).reshape(-1,3)
    if len(np.unique(selected))!=len(selected) or selected.min()<0 or selected.max()>=len(old):raise ValueError('Invalid reviewed triangle IDs')
    if set(selected).intersection(mask.get('uncertain_triangle_ids',[])):raise ValueError('Uncertain border triangles may not be selected')
    keep=np.ones(len(old),dtype=bool);keep[selected]=False
    document=copy.deepcopy(g);payload=bytearray(binary)
    component=g['accessors'][p['indices']]['componentType'];dtype={5123:'<u2',5125:'<u4'}[component]
    def append(values):
        while len(payload)%4:payload.append(0)
        values=np.asarray(values,dtype=dtype).reshape(-1);view=len(document['bufferViews'])
        document['bufferViews'].append({'buffer':0,'byteOffset':len(payload),'byteLength':values.nbytes,'target':34963});payload.extend(values.tobytes())
        document['accessors'].append({'bufferView':view,'componentType':component,'count':len(values),'type':'SCALAR'});return len(document['accessors'])-1
    old_material=p.get('material',0);skin_material=copy.deepcopy(g['materials'][old_material]);skin_material['name']='ReviewedFaceDielectricTrial'
    skin_material.setdefault('pbrMetallicRoughness',{})['metallicFactor']=0
    new_material=len(document['materials']);document['materials'].append(skin_material)
    document['meshes'][0]['primitives'][0]['indices']=append(old[keep])
    new_primitive=copy.deepcopy(p);new_primitive['indices']=append(old[selected]);new_primitive['material']=new_material;document['meshes'][0]['primitives'].append(new_primitive)
    document['buffers'][0]['byteLength']=len(payload);header=json.dumps(document,separators=(',',':')).encode();header+=b' '*(-len(header)%4);payload.extend(b'\0'*(-len(payload)%4))
    output.mkdir(parents=True,exist_ok=True);path=output/'lyra-skin-dielectric.glb'
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(payload))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(payload),b'BIN\0')+payload)
    result,check,check_bin=read_glb(path)
    assert bytes(check_bin[:len(binary)])==bytes(binary)
    for field in ['animations','skins','nodes','images','textures','samplers']:assert check.get(field)==g.get(field),field
    assert check['materials'][:len(g['materials'])]==g['materials']
    assert check['meshes'][0]['primitives'][1]==g['meshes'][0]['primitives'][1]
    restored=np.concatenate([accessor(check,check_bin,q['indices']).reshape(-1,3) for q in [check['meshes'][0]['primitives'][0],check['meshes'][0]['primitives'][-1]]])
    assert sorted(map(tuple,restored.tolist()))==sorted(map(tuple,old.tolist()))
    for q in check['meshes'][0]['primitives']:assert q['attributes']==p['attributes']
    comparison=copy.deepcopy(skin_material);comparison['name']=g['materials'][old_material]['name'];comparison['pbrMetallicRoughness'].pop('metallicFactor')
    assert comparison==g['materials'][old_material]
    report={'status':'isolated_material_trial_pending_neutral_and_game_review','runtime_adoption':'pending','aaa_approval':'pending',
      'source':{'path':str(source),'sha256':sha(raw),'bytes':len(raw),'unchanged':sha(source.read_bytes())==sha(raw)},
      'candidate':{'path':str(path),'sha256':sha(result),'bytes':len(result),'triangles':sum(check['accessors'][q['indices']]['count']//3 for q in check['meshes'][0]['primitives']),'surfaces':len(check['meshes'][0]['primitives'])},
      'ownership_mask':{'path':str(args.review_mask),'sha256':sha(args.review_mask.read_bytes()),'triangle_ids':selected.tolist(),'uncertain_kept_original':mask.get('uncertain_triangle_ids',[])},
      'change':'Duplicate original PBR material; metallicFactor0 ONLY (plus descriptive name); roughness/normal/albedo/AO/maps unchanged',
      'preserved':{'original_BIN_prefix_byte_exact':True,'original_attributes_bindings_byte_exact':True,'oriented_triangle_multiset_exact':True,'new_eyelid_primitive136_unchanged':True,'all_animation_rest_skin_weights_UV_images_textures_unchanged':True,'original_materials_exact':True},
      'tool_sha256':sha(Path(__file__).read_bytes()),'pending':['Boundary/ownership and ordinary-material neutral comparison','Actual same-camera Game/Web comparison','Final art acceptance']}
    (output/'candidate-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['candidate'],indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-body',type=Path,required=True)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--review-mask',type=Path)
    parser.add_argument('--render-ownership',action='store_true')
    parser.add_argument('--derive-candidate',action='store_true')
    parser.add_argument('--camera-reports',type=Path,nargs='+')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.render_ownership:render_ownership(args)
    elif args.derive_candidate:candidate(args)
    else:audit(args)


if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
