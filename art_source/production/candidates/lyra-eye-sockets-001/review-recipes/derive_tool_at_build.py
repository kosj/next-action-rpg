"""Derive ONE real eye-opening/socket candidate, preserving original source bytes.

The original painted-eye interior is cut from the skinned body's triangle
topology. New boundary attributes are barycentrically interpolated, shallow
inward lid walls are added, and separate curved globes sit behind the openings.
The body GLB keeps the entire original BIN prefix and appends geometry only.
This is an isolated modeling candidate; it is never copied into game assets.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

from derive_character_eyes import read_glb, accessor, source_geometry, Surface, srgb_to_linear, write_glb
from repair_character_weights import Skin


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cross2(a, b):
    return a[0]*b[1]-a[1]*b[0]


def convex_hull(points):
    points = sorted(set(map(tuple, points)))
    def half(sequence):
        result = []
        for point in sequence:
            while len(result) >= 2 and cross2(np.array(result[-1])-result[-2], np.array(point)-result[-1]) <= 1e-14:
                result.pop()
            result.append(point)
        return result
    return np.array(half(points)[:-1]+half(points[::-1])[:-1])


def clip_halfplane(polygon, tri_xy, start, end, inside):
    """Polygon vertices are original triangle barycentric coordinates."""
    if not polygon:
        return []
    result = []
    edge = end-start
    def signed(bary):
        value = cross2(edge, bary @ tri_xy-start)
        return value if inside else -value
    previous = polygon[-1]
    a = signed(previous)
    for current in polygon:
        b = signed(current)
        in_a, in_b = a >= -1e-14, b >= -1e-14
        if in_a != in_b:
            fraction = a/(a-b)
            result.append(previous+fraction*(current-previous))
        if in_b:
            result.append(current)
        previous, a = current, b
    # Remove adjacent copies introduced at an exact polygon corner.
    clean = []
    for point in result:
        if not clean or np.linalg.norm(point-clean[-1]) > 1e-9:
            clean.append(point)
    if len(clean) > 1 and np.linalg.norm(clean[0]-clean[-1]) <= 1e-9:
        clean.pop()
    return clean


def polygon_area(points):
    return sum(np.cross(points[i]-points[0], points[i+1]-points[0]) for i in range(1,len(points)-1))


def weld_topology(positions, faces, tolerance=1e-6):
    rounded = np.round(positions/tolerance).astype(np.int64)
    _, unique_indices, inverse = np.unique(rounded, axis=0, return_index=True, return_inverse=True)
    welded = inverse[np.asarray(faces)]
    edges = np.concatenate([welded[:,[0,1]], welded[:,[1,2]], welded[:,[2,0]]])
    keys, counts = np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    boundary_keys = {tuple(edge) for edge in keys[counts==1]}
    directed = [(int(a),int(b)) for a,b in edges if tuple(sorted((int(a),int(b)))) in boundary_keys]
    following = {}
    for a,b in directed:
        if a in following:
            raise ValueError("Ambiguous welded boundary branch")
        following[a] = b
    loops=[]
    while following:
        start=next(iter(following)); current=start; loop=[]
        while current in following:
            loop.append(int(unique_indices[current])); current=following.pop(current)
            if current==start:break
        if current!=start:
            raise ValueError("Open boundary chain")
        loops.append(loop)
    return {"weld_tolerance_m":tolerance,"welded_vertices":len(unique_indices),
            "boundary_edges":len(boundary_keys),"nonmanifold_edges":int((counts>2).sum()),
            "boundary_loops":loops}


def append_body(source_doc, source_binary, attributes, faces, wall_faces, output):
    document=copy.deepcopy(source_doc)
    binary=bytearray(source_binary)
    geometry=document['meshes'][0]['primitives'][0]
    new_attributes={}
    def add(array, kind, target, component):
        while len(binary)%4:binary.append(0)
        view=len(document['bufferViews'])
        document['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':array.nbytes,'target':target})
        binary.extend(array.tobytes())
        value={'bufferView':view,'componentType':component,'count':len(array),'type':kind}
        if kind=='VEC3' and component==5126:
            value.update(min=array.min(0).tolist(),max=array.max(0).tolist())
        document['accessors'].append(value)
        return len(document['accessors'])-1
    for name,array in attributes.items():
        source=source_doc['accessors'][geometry['attributes'][name]]
        array=np.asarray(array,dtype={5121:'u1',5123:'<u2',5126:'<f4'}[source['componentType']])
        new_attributes[name]=add(array,source['type'],34962,source['componentType'])
    component=5123 if len(attributes['POSITION'])<65536 else 5125
    dtype='<u2' if component==5123 else '<u4'
    main_indices=add(np.asarray(faces,dtype=dtype).reshape(-1),'SCALAR',34963,component)
    wall_indices=add(np.asarray(wall_faces,dtype=dtype).reshape(-1),'SCALAR',34963,component)
    geometry['attributes']=new_attributes;geometry['indices']=main_indices
    material=len(document.get('materials',[]))
    document.setdefault('materials',[]).append({'name':'NewEyelidInnerDepth','doubleSided':False,
        'pbrMetallicRoughness':{'baseColorFactor':[*srgb_to_linear((.27,.16,.13)),1],
                               'metallicFactor':0,'roughnessFactor':.57}})
    document['meshes'][0]['primitives'].append({'attributes':new_attributes,'indices':wall_indices,'material':material,'mode':4})
    document['buffers'][0]['byteLength']=len(binary)
    data=json.dumps(document,separators=(',',':')).encode();data+=b' '*(-len(data)%4)
    binary.extend(b'\0'*(-len(binary)%4))
    output.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(data)+len(binary))+struct.pack('<I4s',len(data),b'JSON')+data+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
    _,check,check_binary=read_glb(output)
    assert bytes(check_binary[:len(source_binary)])==bytes(source_binary)
    for field in ['animations','skins','nodes','images','textures','samplers']:
        assert check.get(field)==source_doc.get(field),field
    assert check['materials'][:len(source_doc.get('materials',[]))]==source_doc.get('materials',[])
    return {'original_bin_prefix_byte_exact':True,'all_animation_skin_node_image_texture_sampler_json_exact':True,
            'original_materials_exact':True,'source_bin_bytes':len(source_binary),'new_bin_bytes':len(check_binary)}


def make_eyes(eye_records, rigid_head, output):
    vertices=[]; colors=[]; faces=[]; labels=[]
    radius=.012; iris=.006; pupil=.0024; crown=.0008
    for record in eye_records:
        center=np.array(record['globe_center_source_world_y_up_m'])
        start=len(vertices);rows=32;segments=96
        # Polar axis is source glTF +Z, preserving the measured original gaze.
        for row in range(rows+1):
            phi=math.pi*row/rows
            for column in range(segments):
                theta=math.tau*column/segments;rho=radius*math.sin(phi)
                cap=crown*max(0,1-(rho/iris)**2)**2 if math.cos(phi)>0 else 0
                point=center+np.array([rho*math.cos(theta),rho*math.sin(theta),radius*math.cos(phi)+cap])
                vertices.append(point)
                if math.cos(phi)>0 and rho<pupil:
                    color=srgb_to_linear((.025,.03,.027))
                elif math.cos(phi)>0 and rho<iris:
                    variation=1+.16*math.sin(theta*41+rho*1200)*math.sin(theta*13+.4)
                    limbal=.48 if rho>iris-.0008 else 1
                    shadow=1-.22*max(0,math.sin(theta))
                    color=tuple(c*variation*limbal*shadow for c in srgb_to_linear((.20,.27,.24)))
                else:
                    shadow=1-.2*max(0,math.sin(theta))*max(0,math.cos(phi))
                    color=tuple(c*shadow for c in srgb_to_linear((.62,.64,.62)))
                colors.append((*color,1))
        for row in range(rows):
            for column in range(segments):
                a=start+row*segments+column;b=start+row*segments+(column+1)%segments;c=a+segments;d=b+segments
                for triangle in [(a,c,b),(b,c,d)]:
                    points=np.array([vertices[i] for i in triangle])
                    if np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))<1e-11:continue
                    middle=points.mean(0)-center;rho=np.linalg.norm(middle[:2])
                    label=2 if middle[2]>0 and rho<pupil else (1 if middle[2]>0 and rho<iris else 0)
                    faces.append(triangle);labels.append(label)
    vertices=np.array(vertices);normals=np.zeros_like(vertices)
    for face in faces:
        a,b,c=vertices[list(face)];normal=np.cross(b-a,c-a)
        for i in face:normals[i]+=normal
    size=np.linalg.norm(normals,axis=1)
    normals=np.divide(normals,size[:,None],out=np.broadcast_to([0.,0.,1.],normals.shape).copy(),where=size[:,None]>1e-12)
    local=(vertices-rigid_head[:3,3])@rigid_head[:3,:3];local_normals=normals@rigid_head[:3,:3]
    groups=[[face for face,label in zip(faces,labels) if label==material] for material in range(3)]
    write_glb(output,local,local_normals,colors,groups,True)
    # Verify physical closed-globe topology geometrically, including pole welds.
    topology=weld_topology(vertices,faces,tolerance=1e-7)
    if topology['boundary_edges'] or topology['nonmanifold_edges']:
        raise ValueError('Eye globe topology is not closed/manifold')
    return {'vertices':len(vertices),'triangles':len(faces),'radius_m':radius,'iris_radius_m':iris,
            'pupil_radius_m':pupil,'cornea_crown_m':crown,'topology':{k:v for k,v in topology.items() if k!='boundary_loops'}}


def derive(args):
    source=args.input.resolve(strict=True);output=args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Use a new/empty output directory')
    raw,document,binary=read_glb(source);source_sha=sha(raw)
    reference=json.loads(args.reference_review.read_text())
    if reference['source']['sha256']!=source_sha:raise ValueError('Camera reference source SHA differs')
    source_world,source_faces,full_head,rigid_head,scales=source_geometry(document,binary)
    skin=Skin(source)
    primitive=document['meshes'][0]['primitives'][0]
    original={name:accessor(document,binary,index) for name,index in primitive['attributes'].items()}
    if set(original)!={'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}:raise ValueError('Review unexpected source attributes explicitly')
    attributes={name:[row.copy() for row in array] for name,array in original.items()}
    world_rows=[row.copy() for row in source_world]
    count=len(source_world);rest_matrices=skin.transforms(None,0)
    original_topology=weld_topology(source_world,source_faces)
    if original_topology['boundary_edges'] or original_topology['nonmanifold_edges']:raise ValueError('Source is not welded watertight; do not create an unexplained extra boundary')
    camera=next(v for v in reference['views'] if v['shot']=='face_front')
    if reference['render']['size']!=640:raise ValueError('Measured aperture polygons require the original640px review')
    convert=np.array([[1.,0,0],[0,0,-1],[0,1,0]])
    camera_origin=np.array(camera['camera_position_blender'])@convert;pixel_m=camera['orthographic_scale_m']/640
    def ray(pixel):return camera_origin+np.array([(pixel[0]-320)*pixel_m,(320-pixel[1])*pixel_m,0])
    surface=Surface(source_world,source_faces)
    eyes=[{'name':'image_left','pixel_center':[216,276],'pixel_polygon':[[194,274],[201,267],[211,264],[223,265],[236,270],[242,276],[234,283],[222,288],[210,287],[201,282]]},
          {'name':'image_right','pixel_center':[405,276],'pixel_polygon':[[381,274],[389,269],[400,265],[412,266],[423,271],[427,276],[420,282],[408,286],[396,283],[387,279]]}]
    for eye in eyes:
        eye['polygon']=convex_hull([ray(pixel)[:2] for pixel in eye['pixel_polygon']])
        eye['surface_center'],_=surface.cast(ray(eye['pixel_center']))
    cache={};kept=[];changed_faces=[];removed_area=0.;dropped_weights=[]
    def append_bary(face,bary):
        positive=[(int(i),round(float(w),11)) for i,w in zip(face,bary) if w>1e-9]
        if len(positive)==1 and abs(positive[0][1]-1)<1e-8:return positive[0][0]
        key=tuple(sorted(positive))
        if key in cache:return cache[key]
        index=len(attributes['POSITION']);cache[key]=index
        for name in ['POSITION','NORMAL','TEXCOORD_0']:
            row=bary@original[name][face].astype(float)
            if name=='NORMAL':row/=np.linalg.norm(row)
            attributes[name].append(row)
        weights={}
        for i,amount in zip(face,bary):
            for joint,weight in zip(original['JOINTS_0'][i],original['WEIGHTS_0'][i]):
                weights[int(joint)]=weights.get(int(joint),0)+float(amount*weight)
        weights=sorted(weights.items(),key=lambda p:p[1],reverse=True);selected=weights[:4];total=sum(w for _,w in selected)
        dropped_weights.append(sum(w for _,w in weights[4:]))
        joints=[j for j,w in selected]+[0]*(4-len(selected));values=[w/total for j,w in selected]+[0]*(4-len(selected))
        attributes['JOINTS_0'].append(np.array(joints));attributes['WEIGHTS_0'].append(np.array(values))
        world_rows.append(bary@source_world[face])
        return index
    for face_index,face in enumerate(source_faces):
        points=source_world[face];selected=None
        normal=np.cross(points[1]-points[0],points[2]-points[0]);norm=np.linalg.norm(normal)
        if norm>1e-12 and normal[2]/norm>.25:
            for eye_index,eye in enumerate(eyes):
                polygon=eye['polygon']
                if np.max(abs(points[:,2]-eye['surface_center'][2]))>.02:continue
                if np.any(points[:,:2].max(0)<polygon.min(0)) or np.any(points[:,:2].min(0)>polygon.max(0)):continue
                if any(all(cross2(polygon[(i+1)%len(polygon)]-polygon[i],p[:2]-polygon[i])< -1e-14 for p in points) for i in range(len(polygon))):continue
                selected=eye_index;break
        if selected is None:kept.append(tuple(map(int,face)));continue
        polygon=eyes[selected]['polygon'];remaining=[np.eye(3)[i] for i in range(3)];outside=[]
        for i,start in enumerate(polygon):
            end=polygon[(i+1)%len(polygon)]
            piece=clip_halfplane(remaining,points[:,:2],start,end,False)
            if len(piece)>=3:outside.append(piece)
            remaining=clip_halfplane(remaining,points[:,:2],start,end,True)
            if not remaining:break
        area=np.linalg.norm(polygon_area(np.array([p@points for p in remaining])))/2 if len(remaining)>=3 else 0
        if area<1e-12:kept.append(tuple(map(int,face)));continue
        changed_faces.append(face_index);removed_area+=area
        for piece in outside:
            for i in range(1,len(piece)-1):
                bary=[piece[0],piece[i],piece[i+1]];world=np.array([p@points for p in bary])
                if np.linalg.norm(np.cross(world[1]-world[0],world[2]-world[0]))<1e-12:continue
                kept.append(tuple(append_bary(face,p) for p in bary))
    if not changed_faces:raise ValueError('No actual eye interior triangles were removed')
    # Convex subtraction partitions the outside along infinite clip planes.
    # Propagate their source-edge split points into neighboring triangles,
    # including coincident UV-seam vertices, to avoid geometric T-junctions.
    split_points=np.array(world_rows[count:])
    conforming_refinements=0;conforming_source_ids=[]
    original_face_ids={tuple(map(int,face)):i for i,face in enumerate(source_faces)}
    def interpolate_rows(indices,coefficients):
        index=len(attributes['POSITION'])
        for name in ['POSITION','NORMAL','TEXCOORD_0']:
            value=np.asarray(coefficients)@np.array([attributes[name][i] for i in indices],dtype=float)
            if name=='NORMAL':value/=np.linalg.norm(value)
            attributes[name].append(value)
        influences={}
        for i,amount in zip(indices,coefficients):
            for joint,weight in zip(attributes['JOINTS_0'][i],attributes['WEIGHTS_0'][i]):
                influences[int(joint)]=influences.get(int(joint),0)+float(amount*weight)
        influences=sorted(influences.items(),key=lambda pair:pair[1],reverse=True)[:4]
        total=sum(w for _,w in influences)
        attributes['JOINTS_0'].append(np.array([j for j,w in influences]+[0]*(4-len(influences))))
        attributes['WEIGHTS_0'].append(np.array([w/total for j,w in influences]+[0]*(4-len(influences))))
        world_rows.append(np.asarray(coefficients)@np.array([world_rows[i] for i in indices]))
        return index
    if len(split_points):
        conformed=[];limit_min=split_points.min(0)-1e-7;limit_max=split_points.max(0)+1e-7
        for face in kept:
            points=np.array([world_rows[i] for i in face])
            if np.any(points.max(0)<limit_min) or np.any(points.min(0)>limit_max):conformed.append(face);continue
            perimeter=[];split=False
            for edge_index in range(3):
                a,b=face[edge_index],face[(edge_index+1)%3];start=np.array(world_rows[a]);edge=np.array(world_rows[b])-start
                perimeter.append(a);length2=float(edge@edge)
                if length2<1e-18:continue
                parameters=(split_points-start)@edge/length2
                distances=np.linalg.norm(split_points-(start+parameters[:,None]*edge),axis=1)
                selected=sorted(float(t) for t,d in zip(parameters,distances) if 1e-7<t<1-1e-7 and d<1e-8)
                previous=None
                for t in selected:
                    if previous is not None and abs(t-previous)*math.sqrt(length2)<1e-8:continue
                    perimeter.append(interpolate_rows([a,b],[1-t,t]));previous=t;split=True
            if not split:conformed.append(face);continue
            center_index=interpolate_rows(face,[1/3]*3)
            for i in range(len(perimeter)):
                conformed.append((center_index,perimeter[i],perimeter[(i+1)%len(perimeter)]))
            conforming_refinements+=1
            if face in original_face_ids:conforming_source_ids.append(original_face_ids[face])
        kept=conformed
    cut_topology=weld_topology(np.array(world_rows),kept)
    if len(cut_topology['boundary_loops'])!=2 or cut_topology['nonmanifold_edges']:raise ValueError('Eye cuts must create exactly two unbranched boundaries')
    loops=sorted(cut_topology['boundary_loops'],key=lambda loop:np.array(world_rows)[loop,0].mean())
    walls=[];rim_records=[];depth=.0016
    def append_world_from(index,point,normal):
        joints=np.asarray(attributes['JOINTS_0'][index],dtype=int);weights=np.asarray(attributes['WEIGHTS_0'][index],dtype=float)
        matrix=np.einsum('i,ijk->jk',weights,rest_matrices[joints]);local=np.linalg.solve(matrix,np.r_[point,1])[:3]
        n=matrix[:3,:3].T@normal;n/=np.linalg.norm(n)
        new_index=len(attributes['POSITION'])
        for name in attributes:
            row=local if name=='POSITION' else (n if name=='NORMAL' else np.asarray(attributes[name][index]).copy())
            attributes[name].append(row)
        world_rows.append(point.copy());return new_index
    for eye,loop in zip(eyes,loops):
        center=eye['surface_center'];outer=np.array(world_rows)[loop]
        ring_indices=[]
        for fraction in [0.,.45,1.]:
            row=[]
            for index,point in zip(loop,outer):
                radial=point[:2]-center[:2];radial/=np.linalg.norm(radial)
                target=point.copy();target[:2]-=radial*.0002*fraction;target[2]-=depth*fraction
                normal=np.r_[-radial,.22];normal/=np.linalg.norm(normal)
                row.append(append_world_from(index,target,normal))
            ring_indices.append(row)
        for ring in range(2):
            for i in range(len(loop)):
                j=(i+1)%len(loop);a,b=ring_indices[ring][i],ring_indices[ring][j];c,d=ring_indices[ring+1][i],ring_indices[ring+1][j]
                walls.extend([(a,c,b),(b,c,d)])
        inner=np.array(world_rows)[ring_indices[-1]]
        rho2=((inner[:,:2]-center[:2])**2).sum(1);radius=.012
        if rho2.max()>=radius**2:raise ValueError('Aperture is too wide for the proposed12mm globe')
        globe_z=float(np.min(inner[:,2]-np.sqrt(radius**2-rho2))-.00065)
        globe_center=np.array([*center[:2],globe_z])
        eye['globe_center_source_world_y_up_m']=globe_center.tolist()
        rim_records.append({'name':eye['name'],'outer_vertices':loop,'inner_vertices':ring_indices[-1],
                            'outer_boundary_vertex_count':len(loop),'depth_m':depth,
                            'outer_min_source_world_m':outer.min(0).tolist(),'outer_max_source_world_m':outer.max(0).tolist(),
                            'globe_center_source_world_y_up_m':globe_center.tolist()})
    attributes={name:np.asarray(values,dtype=original[name].dtype) for name,values in attributes.items()}
    for name in original:assert attributes[name][:count].tobytes()==original[name].tobytes(),name
    combined=kept+walls;world_rows=np.array(world_rows)
    final_topology=weld_topology(world_rows,combined)
    if len(final_topology['boundary_loops'])!=2 or final_topology['nonmanifold_edges']:raise ValueError('Rims introduced extra/nonmanifold boundaries')
    output.mkdir(parents=True,exist_ok=True)
    body=output/'lyra-eye-sockets.glb';preserved=append_body(document,binary,attributes,kept,walls,body)
    eyes_path=output/'eyes.glb';eye_geometry=make_eyes(eyes,rigid_head,eyes_path)
    # Compare skinning against a rigid Head attachment over every exported key
    # and midpoint, but only for the small new inner-rim vertex set.
    animation={'status':'pending'}
    if args.audit_animation:
        inner=np.concatenate([r['inner_vertices'] for r in rim_records]);p=attributes['POSITION'][inner].astype(float)
        joints=attributes['JOINTS_0'][inner].astype(int);weights=attributes['WEIGHTS_0'][inner].astype(float)
        local_rest=(world_rows[inner]-rigid_head[:3,3])@rigid_head[:3,:3]
        head_joint=skin.names.index('Head');head_bind_inverse=np.linalg.inv(skin.inverse_binds[head_joint])
        worst=0.;worst_sample=None;sample_count=0;minimum_gap=float('inf');gap_sample=None
        for clip,time in skin.samples(True):
            matrices=skin.transforms(clip,time);posed=np.einsum('vkij,vj->vki',matrices[joints,:3,:3],p)+matrices[joints,:3,3]
            posed=np.einsum('vki,vk->vi',posed,weights)
            head=matrices[head_joint]@head_bind_inverse;rotation=head[:3,:3]/np.linalg.norm(head[:3,:3],axis=0)
            expected=local_rest@rotation.T+head[:3,3];error=np.linalg.norm(posed-expected,axis=1).max()
            if error>worst:worst=float(error);worst_sample={'clip':clip,'time_s':time}
            cursor=0
            for record in rim_records:
                n=len(record['inner_vertices']);rest_center=np.array(record['globe_center_source_world_y_up_m'])
                local_center=(rest_center-rigid_head[:3,3])@rigid_head[:3,:3];center=rotation@local_center+head[:3,3]
                gap=float((np.linalg.norm(posed[cursor:cursor+n]-center,axis=1)-.012).min());cursor+=n
                if gap<minimum_gap:minimum_gap=gap;gap_sample={'clip':clip,'time_s':time,'eye':record['name']}
            sample_count+=1
        animation={'status':'sampled_for_fit_review','schedule':'Every exported timestamp and interval midpoint',
                   'samples':sample_count,'clips':len(skin.animations),'inner_rim_head_rigid_error_max_m':worst,
                   'worst_error_sample':worst_sample,'minimum_inner_rim_to_globe_sphere_gap_m':minimum_gap,
                   'minimum_gap_sample':gap_sample,'limitations':'Finite schedule, no cornea bump collision or full-body deformation approval'}
    final={'status':'candidate_requires_reimport_visual_and_pose_review','runtime_adoption':'pending','aaa_approval':'pending',
           'source':{'path':str(source),'sha256':source_sha,'bytes':len(raw),'unchanged':sha(source.read_bytes())==source_sha},
           'tool_sha256':sha(Path(__file__).read_bytes()),'body':{'path':str(body),'sha256':sha(body.read_bytes()),'bytes':body.stat().st_size},
           'eyes':{'path':str(eyes_path),'sha256':sha(eyes_path.read_bytes()),'bytes':eyes_path.stat().st_size,**eye_geometry},
           'intentional_geometry_changes':{'original_triangles':len(source_faces),'original_vertices':count,
               'clipped_source_triangle_ids':changed_faces,'removed_eye_interior_area_m2':removed_area,
               'source_edge_conformity_refined_original_triangles':conforming_source_ids,
               'conforming_refinement_count':conforming_refinements,
               'remaining_and_clipped_surface_triangles':len(kept),'new_lid_wall_triangles':len(walls),
               'new_vertices':len(attributes['POSITION'])-count,'maximum_dropped_interpolated_weight':max(dropped_weights,default=0)},
           'preserved':{**preserved,'all_original_attribute_rows_byte_exact':True,
                        'all_non_eye_triangles_retained_with_original_indices':True},
           'topology':{'source':{k:v for k,v in original_topology.items() if k!='boundary_loops'},
                       'after_cut':{k:v for k,v in cut_topology.items() if k!='boundary_loops'},
                       'after_lid_walls':{k:v for k,v in final_topology.items() if k!='boundary_loops'},
                       'intentional_inner_socket_loops':rim_records},'animation_fit':animation,
           'attachment_contract':{'coordinate_system':'Original source glTF Head REST-local orthonormal basis; physical meters',
               'root_transform':'identity; direct glTF writer','required_socket_basis':np.eye(3).tolist(),
               'source_head_rest_world_matrix_y_up':full_head.tolist(),'source_head_rest_rigid_world_matrix_y_up':rigid_head.tolist(),
               'source_head_world_scale':scales.tolist()},
           'apertures':[{'name':e['name'],'pixel_center':e['pixel_center'],'pixel_polygon':e['pixel_polygon'],
                        'surface_center_source_world_y_up_m':e['surface_center'].tolist(),'globe_center_source_world_y_up_m':e['globe_center_source_world_y_up_m']} for e in eyes],
           'reference_review':str(args.reference_review),'pending':['Same-camera actual GLB reimport before/after','Side fit and head poses','Actual game and AAA visual acceptance']}
    if not final['source']['unchanged']:raise ValueError('Original source changed during derivation')
    (output/'derivation.json').write_text(json.dumps(final,indent=2)+'\n')
    # Adapter for the existing unchanged region renderer. Its source is the NEW
    # intentionally cut body; original immutable provenance remains above.
    fit={'source':{'sha256':final['body']['sha256']},'original_source':final['source'],
         'candidate':{'sha256':final['eyes']['sha256']},'attachment_contract':final['attachment_contract'],
         'fitting':{'maximum_front_direction_offset_m':.03,'fit_kind':'real opening with globe behind lid walls'},
         'note':'Nearest signed distances on a complete globe are not an outside-skin test; use socket/animation fit and actual renders.'}
    (output/'renderer-fit.json').write_text(json.dumps(fit,indent=2)+'\n')
    print(json.dumps({'body':final['body'],'eyes':final['eyes'],'geometry':final['intentional_geometry_changes'],'animation':animation},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--reference-review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--audit-animation',action='store_true')
    derive(parser.parse_args())


if __name__=='__main__':main()
