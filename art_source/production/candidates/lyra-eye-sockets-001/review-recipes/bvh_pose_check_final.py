"""Reimport exact socket/body GLBs and test actual triangle intersections."""
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
import hashlib,json,math
from pathlib import Path

base=Path(__file__).resolve().parent
report=json.loads((base/'derivation.json').read_text())
eye_file=base/'surface-refit/eyes-web.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=1
bpy.ops.import_scene.gltf(filepath=str(base/'lyra-eye-sockets.glb'))
body=list(bpy.context.scene.objects)
helpers={b.custom_shape for o in body if o.type=='ARMATURE' for b in o.pose.bones if b.custom_shape}
body=[o for o in body if o not in helpers]
arm=next(o for o in body if o.type=='ARMATURE')
aliases={t.name:next(iter({s.action for s in t.strips if s.action})) for t in arm.animation_data.nla_tracks if any(s.action for s in t.strips)}
for track in arm.animation_data.nla_tracks:track.mute=True
arm.data.pose_position='POSE'
arm.animation_data.action=aliases['RESET']
bpy.context.scene.frame_set(int(aliases['RESET'].frame_range[0]))
bpy.context.view_layer.update()
for o in body:o.animation_data_clear()
bpy.context.view_layer.update()
rest=arm.matrix_world@arm.pose.bones['Head'].matrix.copy()
before=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(eye_file))
eyes=[o for o in bpy.context.scene.objects if o not in before]
roots=[o for o in eyes if o.parent not in eyes]
c=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
placement=c@Matrix(report['attachment_contract']['source_head_rest_rigid_world_matrix_y_up'])@c.inverted()
for o in roots:o.matrix_world=placement@o.matrix_world
eye_rest={o:o.matrix_world.copy() for o in roots}

def triangles(objects):
    verts=[];faces=[];graph=bpy.context.evaluated_depsgraph_get()
    for o in objects:
        if o.type!='MESH':continue
        evaluated=o.evaluated_get(graph);mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        start=len(verts);verts.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
        faces.extend(tuple(start+i for i in f.vertices) for f in mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return verts,faces,BVHTree.FromPolygons(verts,faces,all_triangles=True)

def cross_hit(a,b):
    for source,target in [(a,b),(b,a)]:
        for i in range(3):
            origin=source[i];edge=source[(i+1)%3]-origin;length=edge.length
            if length<1e-9:continue
            direction=edge/length
            hit=intersect_ray_tri(*target,direction,origin,True)
            if hit is None:continue
            distance=(hit-origin).dot(direction)
            if 1e-7<distance<length-1e-7:return True
    return False

results=[]
for name,yaw,pitch in [('rest',0,0),('yaw_left',-15,0),('yaw_right',15,0),('pitch_up',0,-10),('pitch_down',0,10)]:
    pivot=rest.translation
    rotation=Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(pitch),4,'X')
    target=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@rest
    arm.pose.bones['Head'].matrix=arm.matrix_world.inverted()@target
    bpy.context.view_layer.update();delta=(arm.matrix_world@arm.pose.bones['Head'].matrix)@rest.inverted()
    for o in roots:o.matrix_world=delta@eye_rest[o]
    bpy.context.view_layer.update()
    bv,bf,body_bvh=triangles(body);ev,ef,eye_bvh=triangles(eyes)
    pairs=body_bvh.overlap(eye_bvh)
    intersections=[]
    for bi,ei in pairs:
        a=[bv[i] for i in bf[bi]];b=[ev[i] for i in ef[ei]]
        if cross_hit(a,b):intersections.append([bi,ei])
    result={'pose':name,'yaw_degrees':yaw,'pitch_degrees':pitch,'bvh_broadphase_pairs':len(pairs),
            'noncoplanar_edge_triangle_intersection_pairs':len(intersections),'intersection_examples':intersections[:10]}
    results.append(result);print('POSE_BVH',name,result,flush=True)
output={'body_sha256':hashlib.sha256((base/'lyra-eye-sockets.glb').read_bytes()).hexdigest(),
        'eyes_sha256':hashlib.sha256((eye_file).read_bytes()).hexdigest(),
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'blender':bpy.app.version_string,
        'actual_glb_reimport':True,'samples':results,
        'limitations':['Five manual head poses; no continuous collision proof','BVH broadphase filtered by finite noncoplanar edge/triangle segment tests','Visual quality and full animation cornea collision require separate scope']}
(base/'surface-refit/bvh-pose-check.json').write_text(json.dumps(output,indent=2)+'\n')
print('BVH_POSES_FINISHED',flush=True)
