import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path('tools').resolve()))
from derive_character_eyes import read_glb,accessor
from repair_character_weights import Skin
import numpy as np
base=Path(__file__).resolve().parent
source=Skin(Path('art_source/production/candidates/lyra-gameplay-001/source.glb'))
raw,g,b=read_glb(base/'lyra-eye-sockets.glb');prim=g['meshes'][0]['primitives'][0]
p=accessor(g,b,prim['attributes']['POSITION']).astype(float);j=accessor(g,b,prim['attributes']['JOINTS_0']).astype(int);w=accessor(g,b,prim['attributes']['WEIGHTS_0']).astype(float)
mat=source.transforms(None,0);world=np.einsum('vkij,vj->vki',mat[j,:3,:3],p)+mat[j,:3,3];world=np.einsum('vki,vk->vi',world,w)
used=np.unique(np.concatenate([accessor(g,b,q['indices']).ravel() for q in g['meshes'][0]['primitives']]))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(base/'lyra-eye-sockets.glb'))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
aliases={t.name:next(iter({s.action for s in t.strips if s.action})) for t in arm.animation_data.nla_tracks if any(s.action for s in t.strips)}
for track in arm.animation_data.nla_tracks:track.mute=True
arm.animation_data.action=None
results=[]
for mode in ['REST','POSE_IDENTITY','POSE_RESET']:
    arm.data.pose_position='REST' if mode=='REST' else 'POSE'
    if mode=='POSE_IDENTITY':
        for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    if mode=='POSE_RESET':
        arm.animation_data.action=aliases['RESET'];bpy.context.scene.frame_set(int(aliases['RESET'].frame_range[0]))
    bpy.context.view_layer.update();points=[]
    for o in meshes:
        ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points.extend(ev.matrix_world@v.co for v in m.vertices);ev.to_mesh_clear()
    tree=KDTree(len(points))
    for i,v in enumerate(points):tree.insert(v,i)
    tree.balance();errors=np.array([tree.find(Vector((world[i,0],-world[i,2],world[i,1])))[2] for i in used])
    result={'mode':mode,'used_source_vertices':len(used),'bpy_vertices':len(points),'max_nearest_vertex_error_m':float(errors.max()),
            'p99_nearest_vertex_error_m':float(np.quantile(errors,.99)),
            'head_pose_world_blender':[list(row) for row in arm.matrix_world@arm.pose.bones['Head'].matrix],
            'head_data_rest_world_blender':[list(row) for row in arm.matrix_world@arm.data.bones['Head'].matrix_local]}
    results.append(result);print('POSE_SPACE',mode,result,flush=True)
report={'body_sha256':hashlib.sha256(raw).hexdigest(),'original_sha256':hashlib.sha256(source.raw).hexdigest(),'modes':results}
(base/'pose-space-check.json').write_text(json.dumps(report,indent=2)+'\n')
