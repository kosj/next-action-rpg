"""Readonly stdlib glTF FK audit at every active key and interval midpoint.

This evaluates actual exported local TRS/quaternion interpolation. Analytical
hand targets alone cannot detect opposing parent/child rotations between keys.
"""
import bisect
import copy
import math
import struct
from pathlib import Path

from append_character_animations import read_glb, _local_matrix


def multiply(left,right):
    return [[sum(left[r][k]*right[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def point(matrix,position):
    return [sum(matrix[r][c]*position[c] for c in range(3))+matrix[r][3] for r in range(3)]


def slerp(left,right,amount):
    dot=sum(a*b for a,b in zip(left,right))
    if dot<0:
        right=[-v for v in right];dot=-dot
    dot=min(1,max(-1,dot))
    if dot>.9995:
        result=[a+(b-a)*amount for a,b in zip(left,right)]
        length=math.sqrt(sum(v*v for v in result))
        return [v/length for v in result]
    angle=math.acos(dot);den=math.sin(angle)
    return [(math.sin((1-amount)*angle)*a+math.sin(amount*angle)*b)/den for a,b in zip(left,right)]


def audit_curve(path,recipe):
    document,binary=read_glb(path)
    animation=next(a for a in document['animations'] if a['name']=='charged_heavy')
    cache={}
    def accessor(index):
        if index not in cache:
            a=document['accessors'][index];view=document['bufferViews'][a['bufferView']]
            width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
            offset=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',width*4)
            cache[index]=[struct.unpack_from('<'+'f'*width,binary,offset+i*stride) for i in range(a['count'])]
        return cache[index]
    tracks=[];key_times=set()
    max_joint_step=0;worst_joint=None
    for channel in animation['channels']:
        sampler=animation['samplers'][channel['sampler']]
        times=[r[0] for r in accessor(sampler['input'])];values=accessor(sampler['output'])
        target=channel['target'];tracks.append((target['node'],target['path'],times,values));key_times.update(times)
        if target['path']=='rotation' and document['nodes'][target['node']]['name'] in ['RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand']:
            for index,(left,right) in enumerate(zip(values,values[1:])):
                norm=math.sqrt(sum(v*v for v in left)*sum(v*v for v in right))
                dot=min(1,abs(sum(a*b for a,b in zip(left,right))/norm))
                degrees=math.degrees(2*math.acos(dot))
                if degrees>max_joint_step:
                    max_joint_step=degrees;worst_joint={'bone':document['nodes'][target['node']]['name'],'interval_s':[times[index],times[index+1]]}
    parents={c:i for i,node in enumerate(document['nodes']) for c in node.get('children',[])}
    hand=next(i for i,node in enumerate(document['nodes']) if node.get('name')=='RightHand')
    def world_at(time):
        nodes=copy.deepcopy(document['nodes'])
        for index,property_name,times,values in tracks:
            left=max(0,min(len(times)-2,bisect.bisect_right(times,time)-1))
            amount=max(0,min(1,(time-times[left])/(times[left+1]-times[left])))
            nodes[index][property_name]=slerp(values[left],values[left+1],amount) if property_name=='rotation' else [a+(b-a)*amount for a,b in zip(values[left],values[left+1])]
        globals={}
        def world(index):
            if index not in globals:
                local=_local_matrix(nodes[index]);globals[index]=multiply(world(parents[index]),local) if index in parents else local
            return globals[index]
        matrix=world(hand)
        inherited=math.sqrt(sum(matrix[r][0]**2 for r in range(3)))
        columns=recipe['weapon_socket']['basis_columns'];offset=recipe['weapon_socket']['offset_m']
        socket=[[columns[c][r]/inherited for c in range(3)]+[offset[r]/inherited] for r in range(3)]+[[0,0,0,1]]
        # Gameplay's single PI facing correction; capsule-floor offset belongs
        # to the ACTOR frame, not the inverse visual child transform.
        facing=[[-1,0,0,0],[0,1,0,.025],[0,0,-1,0],[0,0,0,1]]
        return multiply(facing,multiply(matrix,socket))
    ordered=sorted(key_times);schedule=sorted(set(ordered+[(a+b)/2 for a,b in zip(ordered,ordered[1:])]+[.34+.18*f for f in [0,.1,.25,.5,.75,.9,1]]))
    rows=[]
    for time in schedule:
        if not .34-1e-7<=time<=.52+1e-7:continue
        f=max(0,min(1,(time-.34)/.18));progress=(f*f)**2*(3-2*f*f)
        az=math.radians(-85+170*progress);pitch=math.radians(50-95*progress)
        expected_grip=[.22-.46*progress,1.445-.32*progress,-.28+.14*progress]
        expected_tip=[expected_grip[i]+1.19*v for i,v in enumerate([-math.sin(az)*math.cos(pitch),math.sin(pitch),-math.cos(az)*math.cos(pitch)])]
        matrix=world_at(time);actual_grip=point(matrix,[0,0,0]);actual_tip=point(matrix,[0,1.19,0])
        rows.append({'time_s':time,'grip_error_m':math.dist(actual_grip,expected_grip),'tip_error_m':math.dist(actual_tip,expected_tip)})
    max_grip=max(row['grip_error_m'] for row in rows);max_tip=max(row['tip_error_m'] for row in rows)
    return {'scope':'Actual exported glTF local TRS/slerp FK at every active key and midpoint plus runtime fractions; canonical1.19m blade, no Godot optimizer/terrain/visual/AAA approval.',
        'active_samples':len(rows),'max_grip_error_m':max_grip,'max_tip_error_m':max_tip,
        'max_arm_joint_key_step_degrees':max_joint_step,'worst_joint_step':worst_joint,
        'grip_limit_m':.003,'tip_limit_m':.003,'joint_step_limit_degrees':45,
        'passed':max_grip<.003 and max_tip<.003 and max_joint_step<45,'samples':rows}
