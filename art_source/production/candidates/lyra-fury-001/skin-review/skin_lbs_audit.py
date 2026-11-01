"""Read-only multi-primitive skin comparison; execute only in assigned CPU lane."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
sys.path.insert(0,str(Path.cwd()/'tools'))
from append_character_animations import read_glb
from repair_character_weights import Skin

def skin_for(path,primitive_index):
    doc,binary=read_glb(path);s=Skin.__new__(Skin);s.path=Path(path);s.doc=doc;s.binary=memoryview(binary);s.cache={};s.primitive=doc['meshes'][0]['primitives'][primitive_index];s.attrs=s.primitive['attributes'];s.positions=s.accessor(s.attrs['POSITION']).astype(float);s.joints=s.accessor(s.attrs['JOINTS_0']).astype(int);s.weights=s.accessor(s.attrs['WEIGHTS_0']).astype(float);s.faces=s.accessor(s.primitive['indices']).reshape(-1,3).astype(int);s.skin=doc['skins'][0];s.joint_nodes=s.skin['joints'];s.names=[doc['nodes'][i]['name'] for i in s.joint_nodes];s.inverse_binds=s.accessor(s.skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);s.parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])};s.animations={a['name']:a for a in doc.get('animations',[])};return s

def posed_region(s,clip,t,indices):
    matrices=s.transforms(clip,t);j=s.joints[indices];p=s.positions[indices];w=s.weights[indices];transformed=np.einsum('vkij,vj->vki',matrices[j,:3,:3],p)+matrices[j,:3,3];return np.einsum('vki,vk->vi',transformed,w)

def metrics(old_path,new_path):
    doc,_=read_glb(old_path);other,_=read_glb(new_path);assert doc['meshes']==other['meshes'] and doc['skins']==other['skins']
    reports=[]
    for primitive in range(len(doc['meshes'][0]['primitives'])):
        a,b=skin_for(old_path,primitive),skin_for(new_path,primitive)
        arm=np.array([any(any(k in a.names[j] for k in ['Arm','Hand','Shoulder']) and w>.05 for j,w in zip(js,ws)) for js,ws in zip(a.joints,a.weights)])
        edges=np.unique(np.sort(np.concatenate((a.faces[:,[0,1]],a.faces[:,[1,2]],a.faces[:,[2,0]])),axis=1),axis=0);edges=edges[arm[edges].any(axis=1)];faces=a.faces[arm[a.faces].any(axis=1)]
        if not len(edges):continue
        indices=np.unique(np.concatenate((edges.ravel(),faces.ravel())));mapping=np.full(len(a.positions),-1);mapping[indices]=np.arange(len(indices));local_edges=mapping[edges];local_faces=mapping[faces]
        rest=posed_region(a,None,0,indices);rest_length=np.linalg.norm(rest[local_edges[:,1]]-rest[local_edges[:,0]],axis=1);valid=rest_length>.0001;rest_area=np.linalg.norm(np.cross(rest[local_faces[:,1]]-rest[local_faces[:,0]],rest[local_faces[:,2]]-rest[local_faces[:,0]]),axis=1)*.5
        old_max=np.full(len(edges),-np.inf);new_max=old_max.copy();new_max_time=[None]*len(edges);old_ratio=np.zeros(len(edges));new_ratio=old_ratio.copy();old_area_min=np.full(len(faces),np.inf);new_area_min=old_area_min.copy();samples=0
        for clip in ['charge','charged_heavy']:
            times=[]
            for s in [a,b]:
                for sampler in s.animations[clip]['samplers']:times.extend(s.accessor(sampler['input']).ravel())
            times=np.unique(times);times=np.unique(np.r_[times,(times[:-1]+times[1:])*.5])
            for t in times:
                pa,pb=posed_region(a,clip,float(t),indices),posed_region(b,clip,float(t),indices);samples+=1
                for p,maxima,ratio,area_min,isnew in [(pa,old_max,old_ratio,old_area_min,False),(pb,new_max,new_ratio,new_area_min,True)]:
                    length=np.linalg.norm(p[local_edges[:,1]]-p[local_edges[:,0]],axis=1);extension=length-rest_length;changed=extension>maxima;maxima[:]=np.maximum(maxima,extension);ratio[valid]=np.maximum(ratio[valid],length[valid]/rest_length[valid]);area=np.linalg.norm(np.cross(p[local_faces[:,1]]-p[local_faces[:,0]],p[local_faces[:,2]]-p[local_faces[:,0]]),axis=1)*.5;good=rest_area>1e-8;area_min[good]=np.minimum(area_min[good],area[good]/rest_area[good])
                    if isnew:
                        for i in np.flatnonzero(changed):new_max_time[i]={'clip':clip,'time_s':float(t)}
        change=new_max-old_max;top=np.argsort(change)[-12:][::-1];records=[]
        for i in top:
            if change[i]<=1e-6:continue
            edge=edges[i];row={'edge_index_in_region':int(i),'vertex_ids':edge.tolist(),'rest_length_mm':float(rest_length[i]*1000),'old_envelope_extension_mm':float(old_max[i]*1000),'new_envelope_extension_mm':float(new_max[i]*1000),'worsening_mm':float(change[i]*1000),'new_peak':new_max_time[i],'rest_vertices_world_m':rest[local_edges[i]].tolist(),'weights':[{a.names[j]:float(w) for j,w in zip(a.joints[v],a.weights[v]) if w>1e-6} for v in edge]};records.append(row)
        reports.append({'primitive':primitive,'samples_keys_and_midpoints':samples,'regional_vertices':len(indices),'regional_edges':len(edges),'regional_triangles':len(faces),'scope':'Edges with at least one arm/hand/shoulder-influenced vertex and adjacent triangles; no skin intersection/anatomical/visual approval.','old_max_absolute_extension_mm':float(old_max.max()*1000),'new_max_absolute_extension_mm':float(new_max.max()*1000),'old_p99_edge_ratio':float(np.quantile(old_ratio[valid],.99)),'new_p99_edge_ratio':float(np.quantile(new_ratio[valid],.99)),'old_max_ratio':float(old_ratio[valid].max()),'new_max_ratio':float(new_ratio[valid].max()),'new_collateral_edges_above1mm':int(np.count_nonzero(change>.001)),'old_min_triangle_area_ratio':float(old_area_min[rest_area>1e-8].min()),'new_min_triangle_area_ratio':float(new_area_min[rest_area>1e-8].min()),'largest_same_edge_envelope_worsening':records})
        print('PRIMITIVE_DONE',primitive,samples,file=sys.stderr,flush=True)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return {'scope':'Read-only actual raw glTF LBS at every source/candidate charge+charged key and midpoint, arm/hand/shoulder regions. Finite sampling is not continuous collision, skin intersection, visual, hardware or AAA approval.','source_sha256':sha(old_path),'candidate_sha256':sha(new_path),'audit_script_sha256':sha(__file__),'skin_helper_sha256':sha(Path.cwd()/'tools/repair_character_weights.py'),'primitives':reports}

if __name__=='__main__':
    result=metrics(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
