"""Sample actual reimported Web/reference triangles; measure front and hidden back."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
base=Path(__file__).resolve().parent.parent
d=json.loads((base/'surface-refit/refit.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=1
def load(path):
    before=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(path));objects=[o for o in bpy.context.scene.objects if o not in before]
    vertices=[];faces=[]
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data.calc_loop_triangles();start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in f.vertices) for f in obj.data.loop_triangles)
    return vertices,faces
high,hf=load(base/'surface-refit/eyes.glb');web,wf=load(base/'surface-refit/eyes-web.glb')
bvh=BVHTree.FromPolygons(high,hf,all_triangles=True)
c=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
head=Matrix(d['attachment_contract']['source_head_rest_rigid_world_matrix_y_up'])
centers=[Vector(e['globe_center_source_world_y_up_m']) for e in d['apertures']]
samples=[]
for face in wf:
    a,b,cpoint=[web[i] for i in face]
    samples.extend([(a+b+cpoint)/3,(a+b)/2,(b+cpoint)/2,(cpoint+a)/2])
samples.extend(web)
all_errors=[];front_errors=[]
for point in samples:
    distance=bvh.find_nearest(point)[3];all_errors.append(distance)
    world=head@(c.inverted()@point)
    center=min(centers,key=lambda p:(p-world).length)
    relative=world-center
    if relative.z>.0055:front_errors.append(distance)
report={'source_eye_sha256':hashlib.sha256((base/'surface-refit/eyes.glb').read_bytes()).hexdigest(),
        'web_eye_sha256':hashlib.sha256((base/'surface-refit/eyes-web.glb').read_bytes()).hexdigest(),
        'actual_glb_reimport':True,'reference_triangles':len(hf),'web_triangles':len(wf),
        'sample_count':len(samples),'visible_front_sample_count':len(front_errors),
        'sampled_web_to_reference_distance_max_m':max(all_errors),
        'sampled_visible_front_distance_max_m':max(front_errors),
        'sampled_visible_front_mean_m':sum(front_errors)/len(front_errors),
        'scope':'Vertices, triangle centroids and edge midpoints to reference BVH; front means source-world relative z>5.5mm',
        'limitations':'Finite one-way sample, not continuous Hausdorff bound. Occluded back is intentionally coarser. No hardware performance approval.'}
(base/'surface-refit/surface-error.json').write_text(json.dumps(report,indent=2)+'\n')
print('WEB_SURFACE_ERROR',json.dumps(report),flush=True)
