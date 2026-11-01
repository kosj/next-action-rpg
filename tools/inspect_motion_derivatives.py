"""Read actual glTF TRS/slerp FK; no Blender, engine, mesh or gameplay mutation.

Requires optional NumPy/SciPy art dependencies, never game runtime packages:
    python -m pip install -r tools/requirements-art.txt
    python tools/inspect_motion_derivatives.py OLD.glb NEW.glb --output audit.json

All skin joints are evaluated by default. A reference60Hz schedule describes
sampled raw-file poses, not actual engine execution or measured hardware FPS.
Use --interval START END to report a narrower raw-key interval and --times for
additional exact raw-FK samples, such as action-boundary neighbors.
"""
from pathlib import Path
import argparse, bisect, hashlib, importlib.metadata, json, math, struct, sys
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from append_character_animations import read_glb, _local_matrix

def angle(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return math.degrees(2*math.acos(min(1.,abs(float(np.dot(a,b)))/(np.linalg.norm(a)*np.linalg.norm(b)))))

def slerp(a,b,u):
    a=np.asarray(a,float);b=np.asarray(b,float)
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    dot=float(np.dot(a,b))
    if dot<0:b=-b;dot=-dot
    dot=min(1.,max(-1.,dot))
    if dot>.9995:
        q=a+(b-a)*u
        return (q/np.linalg.norm(q)).tolist()
    theta=math.acos(dot)
    return ((math.sin((1-u)*theta)*a+math.sin(u*theta)*b)/math.sin(theta)).tolist()

class GLB:
    def __init__(self,path,clip='charged_heavy'):
        self.path=Path(path);self.doc,self.binary=read_glb(self.path)
        self.parents={c:i for i,n in enumerate(self.doc['nodes']) for c in n.get('children',[])}
        self.names={n.get('name'):i for i,n in enumerate(self.doc['nodes'])}
        self.cache={}
        joint_indices=list(dict.fromkeys(index for skin in self.doc.get('skins',[]) for index in skin.get('joints',[])))
        self.bones=[self.doc['nodes'][index]['name'] for index in joint_indices]
        if not self.bones:raise ValueError('A named skin joint hierarchy is required')
        if len(set(self.bones))!=len(self.bones):raise ValueError('Skin joint names must be unique')
        matches=[a for a in self.doc.get('animations',[]) if a.get('name')==clip]
        if len(matches)!=1:raise ValueError('Expected exactly one requested clip: '+clip)
        animation=matches[0];self.clip=clip
        self.tracks=[];self.times=set()
        for channel in animation['channels']:
            sample=animation['samplers'][channel['sampler']]
            if sample.get('interpolation','LINEAR')!='LINEAR':raise ValueError('Only literal LINEAR glTF samples supported')
            times=[x[0] for x in self.accessor(sample['input'])];values=self.accessor(sample['output'])
            if not times or len(times)!=len(values) or not all(math.isfinite(t) for t in times) or any(b<=a for a,b in zip(times,times[1:])):
                raise ValueError('Animation keys must be finite and strictly increasing')
            node=channel['target']['node'];prop=channel['target']['path']
            if prop not in ['translation','rotation','scale'] or 'matrix' in self.doc['nodes'][node]:
                raise ValueError('Only animated TRS nodes without matrix overrides are supported')
            if not all(math.isfinite(v) for row in values for v in row):raise ValueError('Animation values must be finite')
            if prop=='rotation' and any(sum(v*v for v in row)<1e-20 for row in values):raise ValueError('Quaternion keys must be nonzero')
            self.tracks.append((channel['target']['node'],channel['target']['path'],times,values))
            self.times.update(times)
        self.duration=max(self.times)
    def accessor(self,index):
        if index not in self.cache:
            a=self.doc['accessors'][index];v=self.doc['bufferViews'][a['bufferView']]
            if a['componentType']!=5126 or 'sparse' in a:raise ValueError('Dense float glTF required')
            width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
            offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',width*4)
            self.cache[index]=[struct.unpack_from('<'+'f'*width,self.binary,offset+i*stride) for i in range(a['count'])]
        return self.cache[index]
    def pose(self,time):
        overrides={}
        for index,prop,times,values in self.tracks:
            if len(times)==1:
                overrides.setdefault(index,{})[prop]=values[0]
                continue
            i=max(0,min(len(times)-2,bisect.bisect_right(times,time)-1))
            u=max(0.,min(1.,(time-times[i])/(times[i+1]-times[i])))
            value=slerp(values[i],values[i+1],u) if prop=='rotation' else [a+(b-a)*u for a,b in zip(values[i],values[i+1])]
            overrides.setdefault(index,{})[prop]=value
        worlds={}
        def world(index):
            if index not in worlds:
                n={**self.doc['nodes'][index],**overrides.get(index,{})}
                local=np.asarray(_local_matrix(n),float)
                worlds[index]=world(self.parents[index])@local if index in self.parents else local
            return worlds[index]
        result={}
        for name in self.bones:
            index=self.names[name];m=world(index);basis=m[:3,:3]
            basis=basis/np.linalg.norm(basis,axis=0)
            q=Rotation.from_matrix(basis).as_quat().tolist()
            result[name]={'position_m':m[:3,3].tolist(),'global_quat_xyzw':q,'local_quat_xyzw':overrides.get(index,{}).get('rotation',self.doc['nodes'][index].get('rotation',[0,0,0,1]))}
        return result

def schedule_metrics(asset,times):
    poses=[asset.pose(t) for t in times]
    metrics={name:{} for name in asset.bones}
    for index,(left,right) in enumerate(zip(poses,poses[1:])):
        first,last=times[index:index+2];dt=last-first
        for name in asset.bones:
            a,b=left[name],right[name]
            values={'local_rotation_deg':angle(a['local_quat_xyzw'],b['local_quat_xyzw']),
                'global_rotation_deg':angle(a['global_quat_xyzw'],b['global_quat_xyzw']),
                'global_translation_m':math.dist(a['position_m'],b['position_m'])}
            for key,value in values.items():
                if value>metrics[name].get(key,{}).get('value',-1):metrics[name][key]={'value':value,'interval_s':[first,last],'per_second':value/dt}
    return metrics

def inspect(path,clip='charged_heavy',sample_hz=60.,interval=None,times=()):
    asset=GLB(path,clip)
    if any(t>asset.duration+1e-6 for t in times):raise ValueError('Additional sample time exceeds actual clip duration')
    raw=sorted(t for t in asset.times if interval is None or interval[0]-1e-7<=t<=interval[1]+1e-7)
    reference=sorted(set([i/sample_hz for i in range(math.ceil(asset.duration*sample_hz)+1) if i/sample_hz<=asset.duration]+[asset.duration]))
    return {'file':str(asset.path),'sha256':hashlib.sha256(asset.path.read_bytes()).hexdigest(),
        'scope':'Actual raw glTF FK/local-vs-global derivatives. No live imported engine, evaluated skin intersection, rendered silhouette, 1x visual or hardware approval.',
        'clip':clip,'duration_s':asset.duration,'bone_count':len(asset.bones),
        'raw_key_count':len(raw),'raw_key_interval_s':interval,'raw_key_metrics':schedule_metrics(asset,raw),
        'reference_sample_hz':sample_hz,'reference_sample_count':len(reference),
        'raw_fk_reference_full_clip':schedule_metrics(asset,reference),
        'additional_raw_fk_samples':[{'time_s':t,'bones':asset.pose(t)} for t in times]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--clip',default='charged_heavy');p.add_argument('--sample-hz',type=float,default=60.)
    p.add_argument('--interval',nargs=2,type=float,metavar=('START','END'));p.add_argument('--times',nargs='+',type=float,default=[])
    a=p.parse_args()
    if not math.isfinite(a.sample_hz) or not 0<a.sample_hz<=1000:p.error('--sample-hz must be finite in (0,1000]')
    if a.interval and (not all(math.isfinite(v) for v in a.interval) or a.interval[0]>a.interval[1]):p.error('Invalid --interval')
    if not all(math.isfinite(t) and t>=0 for t in a.times):p.error('--times must be finite and nonnegative')
    if a.output.resolve() in [path.resolve() for path in a.inputs]:p.error('Output must not overwrite an input')
    reports=[inspect(path,a.clip,a.sample_hz,a.interval,a.times) for path in a.inputs]
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'schema_version':1,'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256((ROOT/'tools/append_character_animations.py').read_bytes()).hexdigest(),'dependency_versions':{name:importlib.metadata.version(name) for name in ['numpy','scipy']},'scope':'Read-only raw glTF FK; reference schedule is not engine execution, skin/render/AV/hardware or AAA acceptance.','assets':reports},indent=2)+'\n')
    for r in reports:
        focus=[n for n in ['RightArm','RightForeArm','RightHand'] if n in r['raw_fk_reference_full_clip']]
        print(json.dumps({'file':r['file'],'sha256':r['sha256'],'clip':r['clip'],'bone_count':r['bone_count'],'raw_fk_reference_schedule':{n:r['raw_fk_reference_full_clip'][n] for n in focus}}))
