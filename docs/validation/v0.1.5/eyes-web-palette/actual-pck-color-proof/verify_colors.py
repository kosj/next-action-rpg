from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path('/workspace/.runefall-task/character-polish/eyes-web')
PROBE=ROOT/'color-probe'

def position_key(position):
    # Godot JSON decimal formatting can differ at the last double digit. The
    # 1e-12m key is far below these float32-position ULPs, not a fit tolerance.
    return tuple(round(value,12) for value in position)

def source(path):
    data=path.read_bytes()
    json_length=struct.unpack_from('<I',data,12)[0]
    document=json.loads(data[20:20+json_length])
    binary_start=20+json_length+8
    def accessor(index,width):
        entry=document['accessors'][index]
        assert entry['componentType']==5126
        view=document['bufferViews'][entry['bufferView']]
        start=binary_start+view.get('byteOffset',0)+entry.get('byteOffset',0)
        stride=view.get('byteStride',width*4)
        return [struct.unpack_from('<'+'f'*width,data,start+i*stride) for i in range(entry['count'])]
    primitive=document['meshes'][0]['primitives'][0]
    positions=accessor(primitive['attributes']['POSITION'],3)
    colors=accessor(primitive['attributes']['COLOR_0'],4)
    lookup=defaultdict(list)
    for position,color in zip(positions,colors):
        lookup[position_key(position)].append(color)
    return lookup,hashlib.sha256(data).hexdigest(),positions

native={name:json.loads((PROBE/f'{name}-pack-colors.json').read_text()) for name in ['reference','palette']}
paths={'reference':ROOT/'game/assets/models/production/lyra_eyes.glb',
       'palette':ROOT/'palette/game/assets/models/production/lyra_eyes.glb'}
sources={name:source(path) for name,path in paths.items()}
result={'scope':'Actual Web PCK remapped PackedScene color arrays compared with actual GLB COLOR_0; source colors match Godot RGBA8 floor quantization, not a visual-quality measurement.',
        'source_sha256':{name:record[1] for name,record in sources.items()},
        'packs_sha256':{name:record['pack_sha256'] for name,record in native.items()},
        'position_key_resolution_m':1e-12,
        'source_position_match_note':'Native ArrayMesh imported vertex compression changes float positions slightly. Nearest source vertex must be within2 micrometers; this is an import-color association, not a mesh-fit tolerance. Reference/palette expanded native triangle coordinates are separately byte-value identical.',
        'surfaces':[],'samples':[]}
for old,new in zip(native['reference']['surfaces'],native['palette']['surfaces']):
    # Godot can reorder vertices/indices when COLOR_0 changes. Verify the
    # expanded, ordered triangle coordinates instead of mistaking a reindex
    # for a geometry change or pairing unrelated color-array indices.
    old_corners=[old['rows'][index][:3] for index in old['indices']]
    new_corners=[new['rows'][index][:3] for index in new['indices']]
    assert old_corners==new_corners
    errors={}
    rgba8_errors={}
    position_errors={}
    for name,mesh in [('reference',old),('palette',new)]:
        assert mesh['vertex_colors_as_albedo']
        max_error=0
        max_position_error=0
        max_rgba8_error=0
        for row in mesh['rows']:
            nearest=min(sources[name][2],key=lambda point:math.dist(point,row[:3]))
            position_error=math.dist(nearest,row[:3])
            assert position_error < .000002,(name,position_error)
            max_position_error=max(max_position_error,position_error)
            choices=sources[name][0][position_key(nearest)]
            assert choices
            error=min(max(abs(a-b) for a,b in zip(row[3:],color)) for color in choices)
            max_error=max(max_error,error)
            quantized_error=min(max(abs(a-math.floor(b*255)/255) for a,b in zip(row[3:],color)) for color in choices)
            max_rgba8_error=max(max_rgba8_error,quantized_error)
        assert max_rgba8_error < 1e-7,(name,max_rgba8_error)
        errors[name]=max_error
        rgba8_errors[name]=max_rgba8_error
        position_errors[name]=max_position_error
    old_colors=defaultdict(list)
    for row in old['rows']:
        old_colors[position_key(row[:3])].append(row[3:])
    changed=[i for i,row in enumerate(new['rows']) if row[3:] not in old_colors[position_key(row[:3])]]
    assert changed
    result['surfaces'].append({'material':new['material'],'native_vertices':len(new['rows']),
        'changed_native_color_rows_by_position':len(changed),
        'native_vertex_index_order_same':old['indices']==new['indices'],
        'expanded_ordered_triangle_positions_exact':True,
        'max_source_to_import_position_quantization_m':position_errors,
        'max_source_to_RGBA8_channel_error':errors})
    result['surfaces'][-1]['max_imported_to_source_floor_RGBA8_error']=rgba8_errors
    for index in [changed[0],changed[-1]]:
        row=new['rows'][index]
        result['samples'].append({'material':new['material'],'palette_native_vertex':index,'position':row[:3],
            'reference_imported_RGBA_candidates':old_colors[position_key(row[:3])],
            'palette_imported_RGBA':row[3:],
            'palette_source_RGBA_candidates':sources['palette'][0][position_key(min(sources['palette'][2],key=lambda point:math.dist(point,row[:3]))) ]})
result['verdict']='The candidate colors are present in the actual exported Web PCK, not a stale d7d cache. Perceptual improvement requires separate image review.'
(PROBE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:result[key] for key in ['source_sha256','surfaces','verdict']},indent=2))
