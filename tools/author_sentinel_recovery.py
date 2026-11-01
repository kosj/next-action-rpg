"""Guard-aligned Sentinel weight recovery, preserving the frozen hero author.

Run in Blender4.3.2 using the same --source/--recipe/--output CLI as the base.
Only the Sentinel limb solver is rebound to the original idle authoring solver.
Actual source-idle and exported-heavy-hit poses are independently reimported.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_weight_actions as base
from author_character_actions import PoseRig


class GuardAlignedSentinel(base.WeightAuthor):
    def __init__(self,rig,recipe):
        if recipe['profile']!='sentinel':raise ValueError('This wrapper authors Sentinel only')
        super().__init__(rig,recipe)
        self.pose.limb=PoseRig.limb.__get__(self.pose,PoseRig)
        # The continuous-plane pole is not used by this original solver.
        self.minimum_arm_pole_margin={'status':'not_applicable_original_idle_limb_solver'}


def pose_at(rig,clip,time,fps):
    matches=[a for a in bpy.data.actions if a.name==clip or a.name.startswith(clip+'_')]
    if len(matches)!=1:raise ValueError('Ambiguous clip '+clip)
    rig.animation_data_create();rig.animation_data.action=matches[0]
    frame=float(matches[0].frame_range[0])+time*fps
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
    bpy.context.view_layer.update()
    return {bone.name:{'world_m':list((rig.matrix_world@bone.matrix).translation),
        'local_quaternion_wxyz':list(bone.matrix_basis.to_quaternion())} for bone in rig.pose.bones}


def compare(reference,pose):
    if set(reference)!=set(pose):raise ValueError('Source/exported bone set differs')
    distances={bone:math.dist(reference[bone]['world_m'],pose[bone]['world_m']) for bone in reference}
    rotations={bone:base.shortest_rotation_degrees(reference[bone]['local_quaternion_wxyz'],pose[bone]['local_quaternion_wxyz']) for bone in reference}
    worst=max(distances,key=distances.get)
    return {'bone_count':len(reference),'max_joint_distance_m':max(distances.values()),
        'worst_position_bone':worst,'max_local_rotation_degrees':max(rotations.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    recipe=json.loads(args.recipe.read_text());fps=recipe['fps']
    if bpy.app.version[:3]!=(4,3,2) or not bpy.app.background:raise ValueError('Use Blender4.3.2 background')
    if recipe['profile']!='sentinel':raise ValueError('Sentinel recipe required')
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=fps
    bpy.ops.import_scene.gltf(filepath=str(args.source.resolve(strict=True)),import_pack_images=True)
    source_rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    idle=pose_at(source_rig,'idle',0,fps)
    base.WeightAuthor=GuardAlignedSentinel
    base.main()
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    samples={str(time):compare(idle,pose_at(rig,'heavy_hit',time,fps)) for time in [0,.4666666667,.48]}
    for time in ['0','0.48']:
        if samples[time]['max_joint_distance_m']>.001 or samples[time]['max_local_rotation_degrees']>.1:
            raise ValueError('Actual source idle endpoint mismatch: '+json.dumps(samples))
    if samples['0.4666666667']['max_joint_distance_m']>.02:
        raise ValueError('Actual source idle near-end exceeds20mm: '+json.dumps(samples))
    path=args.output.with_suffix('.authoring.json');report=json.loads(path.read_text())
    report['base_author_tool_sha256']=report['author_tool_sha256'];report['author_tool_sha256']=base.sha(__file__)
    report['entry_tool']='tools/author_sentinel_recovery.py';report['base_author_tool']='tools/author_weight_actions.py'
    report['limb_solver']='Original author_character_actions.PoseRig.limb, same arm poles and branch as actual preserved source idle; new weight pelvis/feet/braking retained.'
    report['actual_source_idle_join']={'scope':'Actual immutable source idle0 vs actual newly exported heavy_hit0/.4667/.48, all53 bones. This is not runtime blending, skin quality or AAA approval.',
        'source_sha256':base.sha(args.source),'samples':samples,'endpoint_position_limit_m':.001,
        'endpoint_rotation_limit_degrees':.1,'near_end_position_limit_m':.02,'passed':True}
    path.write_text(json.dumps(report,indent=2)+'\n')
    print('RUNEFALL_SENTINEL_SOURCE_IDLE_JOIN',json.dumps(samples),flush=True)


if __name__=='__main__':main()
