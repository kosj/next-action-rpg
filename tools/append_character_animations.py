"""Append reviewed Blender animation accessors without re-exporting body data.

Only animations/accessors/bufferViews and the embedded buffer length may change.
Every original BIN byte, mesh, skin, material, image and node stays untouched.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', data)
    if magic != 0x46546c67 or version != 2 or length != len(data):
        raise ValueError('Expected a complete GLB2')
    size, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4e4f534a:
        raise ValueError('Expected JSON first')
    document = json.loads(data[20:20+size])
    offset = 20+size
    size, kind = struct.unpack_from('<II', data, offset)
    if kind != 0x004e4942:
        raise ValueError('Expected embedded BIN')
    return document, data[offset+8:offset+8+size]


def _local_matrix(node):
    if 'matrix' in node:
        return [[node['matrix'][c*4+r] for c in range(4)] for r in range(4)]
    x,y,z,w = node.get('rotation',[0,0,0,1])
    scale=node.get('scale',[1,1,1]);position=node.get('translation',[0,0,0])
    rotation=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
        [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
        [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
    return [[rotation[r][c]*scale[c] for c in range(3)]+[position[r]] for r in range(3)]+[[0,0,0,1]]


def append_animations(source_path, animation_path, output_path, expected_names):
    source, original_bin = read_glb(source_path)
    exported, exported_bin = read_glb(animation_path)
    if len(source.get('buffers',[])) != 1 or source['buffers'][0].get('uri'):
        raise ValueError('Source must have one embedded buffer')
    target = copy.deepcopy(source)
    binary = bytearray(original_bin)
    original_nodes = {}
    for index,node in enumerate(source['nodes']):
        name = node.get('name')
        if name:
            if name in original_nodes:
                raise ValueError('Ambiguous source node name: '+name)
            original_nodes[name] = index
    exported_parents = {child:index for index,node in enumerate(exported['nodes']) for child in node.get('children',[])}
    source_parents = {child:index for index,node in enumerate(source['nodes']) for child in node.get('children',[])}
    mapping = {}
    for animation in exported.get('animations',[]):
        for channel in animation['channels']:
            index = channel['target']['node']
            node = exported['nodes'][index]
            name = node.get('name')
            if name not in original_nodes:
                raise ValueError('Animation target has no unique source node: '+str(name))
            mapped = original_nodes[name]
            left,right = _local_matrix(node),_local_matrix(source['nodes'][mapped])
            if max(abs(left[r][c]-right[r][c]) for r in range(4) for c in range(4)) > 1e-5:
                raise ValueError('Animation rest basis differs from source: '+name)
            p1,p2 = exported_parents.get(index),source_parents.get(mapped)
            n1 = exported['nodes'][p1].get('name') if p1 is not None else None
            n2 = source['nodes'][p2].get('name') if p2 is not None else None
            if n1 != n2:
                raise ValueError('Animation parent differs from source: '+name)
            mapping[index] = mapped
    names = {a.get('name') for a in exported.get('animations',[])}
    if names != set(expected_names):
        raise ValueError('Exported motion-only action set differs: '+str(names))
    view_map, accessor_map = {},{}
    def accessor(index):
        if index in accessor_map:
            return accessor_map[index]
        value = copy.deepcopy(exported['accessors'][index])
        if 'sparse' in value or value['componentType'] != 5126:
            raise ValueError('Only dense float animation accessors are supported')
        view_index = value['bufferView']
        if view_index not in view_map:
            view = copy.deepcopy(exported['bufferViews'][view_index])
            if view['buffer'] != 0:
                raise ValueError('Expected one animation BIN')
            while len(binary)%4:
                binary.append(0)
            start = view.get('byteOffset',0)
            payload = exported_bin[start:start+view['byteLength']]
            if len(payload) != view['byteLength']:
                raise ValueError('Truncated animation bufferView')
            view['byteOffset'] = len(binary)
            binary.extend(payload)
            view_map[view_index] = len(target['bufferViews'])
            target['bufferViews'].append(view)
        value['bufferView'] = view_map[view_index]
        accessor_map[index] = len(target['accessors'])
        target['accessors'].append(value)
        return accessor_map[index]
    new_actions = []
    for animation in exported['animations']:
        value = copy.deepcopy(animation)
        for sampler in value['samplers']:
            if sampler.get('interpolation','LINEAR') != 'LINEAR':
                raise ValueError('Expected baked linear motion')
            sampler['input'] = accessor(sampler['input'])
            sampler['output'] = accessor(sampler['output'])
        for channel in value['channels']:
            channel['target']['node'] = mapping[channel['target']['node']]
        new_actions.append(value)
    replaced = [a['name'] for a in target['animations'] if a['name'] in names]
    retained = [a for a in target['animations'] if a['name'] not in names]
    target['animations'] = retained+new_actions
    target['buffers'][0]['byteLength'] = len(binary)
    payload = json.dumps(target,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    payload += b' '*((-len(payload))%4)
    binary.extend(b'\0'*((-len(binary))%4))
    output = Path(output_path)
    if output.exists():
        raise ValueError('Never overwrite candidate GLBs')
    output.write_bytes(struct.pack('<III',0x46546c67,2,28+len(payload)+len(binary))+
        struct.pack('<II',len(payload),0x4e4f534a)+payload+
        struct.pack('<II',len(binary),0x004e4942)+binary)
    check,check_bin = read_glb(output)
    immutable = ['nodes','meshes','skins','materials','images','textures','samplers','scenes','scene']
    for key in immutable:
        if check.get(key) != source.get(key):
            raise ValueError('Unexpected body/source mutation: '+key)
    if check_bin[:len(original_bin)] != original_bin:
        raise ValueError('Original BIN prefix differs')
    return {'body_json_exact':immutable,'original_bin_prefix_exact':True,
        'source_sha256':hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
        'source_bytes':Path(source_path).stat().st_size,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'output_bytes':output.stat().st_size,'retained_animation_names':[a['name'] for a in retained],
        'replaced_animation_names':replaced,'authored_animation_names':sorted(names),
        'rest_basis_tolerance':1e-5,'source_unchanged':True}
