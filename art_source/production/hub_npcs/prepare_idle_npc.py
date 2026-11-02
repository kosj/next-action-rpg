"""Blender 4.3.2: normalize an immutable provider idle GLB for a stationary NPC.

blender -b --factory-startup --python art_source/production/hub_npcs/prepare_idle_npc.py -- \
  --recipe art_source/production/hub_npcs/erin.json

No rig rebind, retiming, root-motion removal, body remesh or image generation.
Only a uniform wrapper, an explicit 180-degree facing correction, a named idle,
a bind RESET, and a documented 1k normal-map derivative are produced.
"""
import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_character_candidate import (armature, export_options, glb_json, import_asset,
    reset_action, rest_bounds, without_helpers)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose_vertices(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    result = []
    for obj in objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        result.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return result


def bone_pose(rig):
    return {bone.name: (rig.matrix_world @ bone.matrix).copy() for bone in rig.pose.bones}


def bone_delta(first, last):
    position = angle = 0.0
    for name, a in first.items():
        b = last[name]
        position = max(position, (a.translation-b.translation).length)
        qa, qb = a.to_quaternion().normalized(), b.to_quaternion().normalized()
        angle = max(angle, 2*math.acos(min(1.0, abs(qa.dot(qb)))))
    return {'joint_position_max_m': position, 'joint_angle_shortest_max_rad': angle}


def resize_normal_maps(objects, limit, directory):
    processed, records = set(), []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        for material in obj.data.materials:
            if not material or not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.type != 'NORMAL_MAP':
                    continue
                for link in node.inputs['Color'].links:
                    image = getattr(link.from_node, 'image', None)
                    if image is None or image in processed:
                        continue
                    processed.add(image)
                    original = list(image.size)
                    if max(original) <= limit:
                        continue
                    if original[0] != original[1]:
                        raise ValueError('Only square generated tangent normal maps are supported')
                    image.colorspace_settings.name = 'Non-Color'
                    image.scale(limit, limit)
                    pixels = array('f', [0.0]) * (limit*limit*4)
                    image.pixels.foreach_get(pixels)
                    for i in range(0, len(pixels), 4):
                        x, y, z = (pixels[i+j]*2-1 for j in range(3))
                        norm = math.sqrt(x*x+y*y+z*z)
                        if norm < 1e-8:
                            x, y, z, norm = 0, 0, 1, 1
                        pixels[i:i+3] = array('f', ((x/norm+1)*.5, (y/norm+1)*.5, (z/norm+1)*.5))
                    image.pixels.foreach_set(pixels)
                    image.update()
                    image.filepath_raw = str(directory / (str(len(records))+'-normal.png'))
                    image.file_format = 'PNG'
                    image.save()
                    image.pack()
                    records.append({'image_name':image.name,'source_size':original,'derived_size':[limit,limit],
                        'operation':'linear non-color downsample; normalize tangent RGB vectors; lossless PNG'})
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', required=True, type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version[:3] != (4,3,2) or not bpy.app.background:
        raise ValueError('Use the verified Blender 4.3.2 background process')
    recipe_path=args.recipe.resolve(strict=True)
    recipe=json.loads(recipe_path.read_text())
    source=ROOT/recipe['source_idle']['file']
    if sha(source)!=recipe['source_idle']['sha256']:
        raise ValueError('Immutable idle source hash mismatch')
    output=ROOT/recipe['output_file'];report_path=output.with_suffix('.preparation.json')
    if output.exists() or report_path.exists():
        raise ValueError('Refuse to overwrite a previous candidate or its report')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps=30
    objects, actions=import_asset(source)
    rig=armature(objects,'idle source')
    objects, helpers=without_helpers(objects,rig)
    pose_actions=[a for a in actions if any(c.data_path.startswith('pose.bones[') for c in a.fcurves)]
    if len(pose_actions)!=1:
        raise ValueError('Expected exactly one provider skeletal idle action')
    action=pose_actions[0];action.name='idle';action.use_fake_user=True
    # The glTF importer attaches the original provider name as an NLA strip.
    # Export the explicitly named Action, without inheriting that stale label.
    rig.animation_data_create()
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
    start,end=map(float,action.frame_range)
    if end<=start:
        raise ValueError('Idle must have a positive source duration')
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.co.x-=start;key.handle_left.x-=start;key.handle_right.x-=start
        curve.update()
    duration=(end-start)/30
    rig.animation_data_create();rig.animation_data.action=action
    rig.data.pose_position='REST';bpy.context.view_layer.update()
    bounds=rest_bounds(objects)
    center=Vector(((bounds['min'][0]+bounds['max'][0])*.5,(bounds['min'][1]+bounds['max'][1])*.5,0))
    factor=recipe['height_m']/bounds['height']
    wrapper=bpy.data.objects.new('NPC_Normalized_MinusZ',None)
    bpy.context.scene.collection.objects.link(wrapper)
    for obj in [o for o in objects if o.parent not in objects]:
        world=obj.matrix_world.copy();obj.parent=wrapper;obj.matrix_world=world
    wrapper.matrix_world=(Matrix.Translation((0,0,-bounds['min'][2]*factor)) @
        Matrix.Rotation(math.pi,4,'Z') @ Matrix.Scale(factor,4) @ Matrix.Translation(-center))
    bpy.context.view_layer.update()
    normalized=rest_bounds(objects)
    rest_vertices=pose_vertices(objects)
    floor=min(v.z for v in rest_vertices)
    sole_ids={side:[i for i,v in enumerate(rest_vertices) if v.z<=floor+.025 and (v.x<0 if side=='left' else v.x>=0)] for side in ['left','right']}
    if not all(sole_ids.values()):raise ValueError('Both rest sole regions must contain vertices')
    rig.data.pose_position='POSE';rig.animation_data.action=action
    samples=[];poses=[];first_vertices=None
    for index in range(121):
        frame=(end-start)*index/120
        bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
        vertices=pose_vertices(objects)
        if first_vertices is None:first_vertices=vertices
        feet={}
        for side,ids in sole_ids.items():
            delta=max(math.hypot(vertices[i].x-first_vertices[i].x,vertices[i].y-first_vertices[i].y) for i in ids)
            feet[side]={'max_horizontal_displacement_from_idle_start_m':delta,'lowest_m':min(vertices[i].z for i in ids)}
        samples.append({'time_s':duration*index/120,'soles':feet})
        if index in [0,120]:poses.append(bone_pose(rig))
    idle_seam=bone_delta(poses[0],poses[1])
    reset_action(rig)
    rig.animation_data.action=action;bpy.context.scene.frame_set(0)
    expected_pose_points={}
    for fraction in [0.0,.25,.5,.75,1.0]:
        frame=(end-start)*fraction
        bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
        expected_pose_points[fraction]=pose_vertices(objects)
    bpy.context.scene.frame_set(0)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.npc-',dir=output.parent) as temp:
        directory=Path(temp)
        texture_records=resize_normal_maps(objects,recipe['texture_limit'],directory)
        staged=directory/output.name
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [wrapper,*objects]:obj.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.gltf(**export_options(staged))
        document=glb_json(staged)
        names=[a.get('name') for a in document.get('animations',[])]
        if sorted(names)!=['RESET','idle'] or not document.get('skins'):
            raise ValueError('Derivative must preserve exactly idle and RESET plus skin: '+repr(names))
        verified_objects,verified_actions=import_asset(staged)
        verified_rig=armature(verified_objects,'reimported derivative')
        verified_objects,_=without_helpers(verified_objects,verified_rig)
        verified_rig.data.pose_position='REST';bpy.context.view_layer.update()
        verified_bounds=rest_bounds(verified_objects)
        if abs(verified_bounds['height']-recipe['height_m'])>.0001 or abs(verified_bounds['min'][2])>.0001:
            raise ValueError('Exported derivative REST height or floor differs from normalized source')
        # Exporters may split vertices at seams. Compare actual point sets using
        # nearest neighbors in both directions instead of assuming vertex order.
        from mathutils.kdtree import KDTree
        # Blender prefixes imported Action names with the owning object. The
        # exported glTF clip names above are exact; locate this 10-second idle
        # by its preserved span instead of assuming Blender's internal label.
        verified_idle=[a for a in verified_actions
            if abs(float(a.frame_range[1]-a.frame_range[0])-(end-start))<.01]
        if len(verified_idle)!=1:
            raise ValueError('Reimported preserved-span idle is not unique: '+repr([a.name for a in verified_actions]))
        verified_rig.data.pose_position='POSE';verified_rig.animation_data.action=verified_idle[0]
        pose_errors=[]
        for fraction,expected in expected_pose_points.items():
            frame=(end-start)*fraction
            bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
            actual=pose_vertices(verified_objects)
            def distance(a,b):
                tree=KDTree(len(b))
                for index,point in enumerate(b):tree.insert(point,index)
                tree.balance()
                return max(tree.find(point)[2] for point in a)
            error=max(distance(expected,actual),distance(actual,expected))
            if error>.0001:raise ValueError('Reimported idle skin differs by more than 0.1mm')
            pose_errors.append({'fraction':fraction,'bidirectional_nearest_vertex_max_error_m':error})
        if sha(source)!=recipe['source_idle']['sha256']:
            raise ValueError('Source changed during preparation')
        report={'schema_version':1,'status':'normalized_idle_candidate_pending_visual_and_runtime_review',
            'source':recipe['source_idle'],'source_unchanged':True,'output_file':recipe['output_file'],
            'output_bytes':staged.stat().st_size,'output_sha256':sha(staged),
            'recipe_file':str(recipe_path.relative_to(ROOT)),'recipe_sha256':sha(recipe_path),
            'tool_file':str(Path(__file__).resolve().relative_to(ROOT)),'tool_sha256':sha(Path(__file__).resolve()),
            'base_utility_file':'tools/prepare_character_candidate.py','base_utility_sha256':sha(ROOT/'tools/prepare_character_candidate.py'),
            'blender':bpy.app.version_string,'bones':len(rig.data.bones),'clips':names,'idle_duration_s':duration,
            'time_base':{'source_start_s':start/30,'source_end_s':end/30,
                'common_time_translation_s':-start/30,'duration_preserved':True,'retiming':False},
            'normalization':{'uniform_scale':factor,'source_rest_bounds':bounds,'target_height_m':recipe['height_m'],
                'normalized_rest_bounds':normalized,'forward':'minus_z_after_wrapper_pi','source_forward':'plus_z',
                'reimported_rest_bounds':verified_bounds,
                'root_wrapper_matrix_blender':[list(row) for row in wrapper.matrix_world]},
            'normalized_source_to_reimported_idle_pose_checks':pose_errors,
            'textures':texture_records,'idle_seam':idle_seam,'sole_measurement':{
                'method':'Actual evaluated mesh vertices in the lowest 25mm rest band, split by rest X sign; 121 finite poses. This is not a foot IK or contact solver.',
                'region_vertex_counts':{k:len(v) for k,v in sole_ids.items()},'samples':samples},
            'excluded_helpers':helpers,'limitations':['121 finite idle samples are not continuous deformation approval',
                'REST height/floor is separate from actual animated sole heights/drift','No AAA, hardware, performance or actual-game visual approval']}
        temp_report=directory/report_path.name;temp_report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        os.link(staged,output)
        try:os.link(temp_report,report_path)
        except Exception:output.unlink();raise
    print(json.dumps({'output':recipe['output_file'],'sha256':report['output_sha256'],'bytes':report['output_bytes'],
        'bones':report['bones'],'clips':names,'duration_s':duration,'seam':idle_seam}))


if __name__=='__main__':main()
