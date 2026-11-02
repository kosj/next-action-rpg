"""Read-only finite hand-vertex to actual runtime broadblade surface distance.
The conservative triangle-edge bound can prove separation; a negative bound
is inconclusive, never a collision claim. No engine or renderer is launched.
"""
from pathlib import Path
import json,sys,math,hashlib,heapq,time,argparse
import numpy as np
sys.path.insert(0,str(Path.cwd()/'tools'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from append_character_animations import read_glb
from skin_lbs_audit import skin_for

def accessor(doc,binary,index):
 a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];width={'VEC3':3,'SCALAR':1}[a['type']];dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];size=np.dtype(dtype).itemsize
 return np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',size*width),size)).copy()
def bbox_distance(points,lo,hi):return np.square(np.maximum(np.maximum(lo-points,points-hi),0)).sum(axis=1)
def closest_pairs(points,tri):
 # Every point/triangle pair in one bounded leaf. Plane projection is accepted
 # only inside the triangle; otherwise the closest of its three edge segments.
 a=tri[:,0];ab=tri[:,1]-a;ac=tri[:,2]-a;p=points[:,None,:];ap=p-a
 aa=(ab*ab).sum(1);bb=(ab*ac).sum(1);cc=(ac*ac).sum(1);pa=(ap*ab).sum(2);pc=(ap*ac).sum(2);det=aa*cc-bb*bb
 u=np.divide(pa*cc-pc*bb,det,out=np.zeros_like(pa),where=abs(det)>1e-24);v=np.divide(pc*aa-pa*bb,det,out=np.zeros_like(pa),where=abs(det)>1e-24)
 normal=np.cross(ab,ac);nn=(normal*normal).sum(1);height=np.divide((ap*normal).sum(2),nn,out=np.zeros_like(pa),where=nn>1e-24)
 plane=p-height[:,:,None]*normal;inside=(u>=0)&(v>=0)&(u+v<=1)&(nn>1e-24)
 best=np.full(pa.shape,np.inf);location=np.zeros((*pa.shape,3))
 for first,last in [(0,1),(1,2),(2,0)]:
  start=tri[:,first];edge=tri[:,last]-start;den=(edge*edge).sum(1);f=np.clip(np.divide(((p-start)*edge).sum(2),den,out=np.zeros_like(pa),where=den>1e-24),0,1);q=start+f[:,:,None]*edge;d=((p-q)**2).sum(2);pick=d<best;best[pick]=d[pick];location[pick]=q[pick]
 d=((p-plane)**2).sum(2);pick=inside&(d<best);best[pick]=d[pick];location[pick]=plane[pick]
 return best,location
class Tree:
 def __init__(self,tri,ids):
  self.tri=tri;self.nodes=[];self.root=self.build(np.asarray(ids,int))
 def build(self,ids):
  points=self.tri[ids];lo=points.min((0,1));hi=points.max((0,1));i=len(self.nodes);self.nodes.append(None)
  if len(ids)<=8:self.nodes[i]=(lo,hi,ids,None,None)
  else:
   centers=points.mean(1);axis=np.argmax(np.ptp(centers,axis=0));order=ids[np.argsort(centers[:,axis])];mid=len(order)//2;l=self.build(order[:mid]);r=self.build(order[mid:]);self.nodes[i]=(lo,hi,None,l,r)
  return i
 def query(self,points):
  best=math.inf;answer=None;queue=[(0.,self.root,np.arange(len(points)))];serial=0
  while queue:
   bound,index,eligible=heapq.heappop(queue)
   if bound>=best:continue
   lo,hi,ids,left,right=self.nodes[index]
   d=bbox_distance(points[eligible],lo,hi);eligible=eligible[d<best]
   if not len(eligible):continue
   if ids is not None:
    dd,location=closest_pairs(points[eligible],self.tri[ids]);ij=np.unravel_index(np.argmin(dd),dd.shape);value=float(dd[ij])
    if value<best:best=value;answer=(int(eligible[ij[0]]),int(ids[ij[1]]),location[ij].tolist())
   else:
    for child in [left,right]:
     cl,ch,*_=self.nodes[child];bd=float(bbox_distance(points[eligible],cl,ch).min())
     if bd<best:heapq.heappush(queue,(bd,child,eligible))
  return math.sqrt(best),answer

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--body',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 start=time.monotonic();root=Path.cwd();body=args.body.resolve(strict=True);weapon=root/'game/assets/models/production/rune_greatsword_geometry.glb';doc,bin=read_glb(weapon);p=doc['meshes'][0]['primitives'][0];vertices=accessor(doc,bin,p['attributes']['POSITION']);faces=accessor(doc,bin,p['indices']).reshape(-1,3);tri=vertices[faces]
 geometry_node=next(n for n in doc['nodes']if n.get('name')=='CanonicalGeometry');assert set(geometry_node)=={'mesh','name'}
 blade=np.flatnonzero(tri[:,:,1].max(1)>.16);hilt=np.flatnonzero(tri[:,:,1].min(1)<=.16);trees={'blade':Tree(tri,blade),'hilt_and_guard':Tree(tri,hilt)}
 grip=json.loads((root/'game/data/character_grips.json').read_text())['hero'];basis=np.array(grip['basis_columns']).reshape(3,3).T;offset=np.array(grip['offset_m'])
 skin=skin_for(body,0);hand=np.array([any((skin.names[j]=='LeftHand'or skin.names[j].startswith('HandLoRA_Bip01_L_'))and w>.05 for j,w in zip(js,ws))for js,ws in zip(skin.joints,skin.weights)]);hand_faces=skin.faces[hand[skin.faces].any(1)];indices=np.unique(hand_faces);mapping=np.full(len(skin.positions),-1);mapping[indices]=np.arange(len(indices));local_faces=mapping[hand_faces];right=skin.names.index('RightHand');inverse_bind_inverse=np.linalg.inv(skin.inverse_binds[right]);rows=[]
 for clip in ['light_1','light_2','light_3']:
  tt=np.unique(np.concatenate([skin.accessor(x['input']).ravel()for x in skin.animations[clip]['samplers']]));times=np.unique(np.r_[tt,(tt[:-1]+tt[1:])*.5]);startup=.18 if clip=='light_3'else .13;active=.22 if clip=='light_3'else .17;duration=float(tt[-1]);recovery=duration-startup-active
  for t in times:
   matrices=skin.transforms(clip,float(t));j=skin.joints[indices];w=skin.weights[indices];pos=skin.positions[indices];posed=np.einsum('vki,vk->vi',np.einsum('vkij,vj->vki',matrices[j,:3,:3],pos)+matrices[j,:3,3],w)
   hand_world=matrices[right]@inverse_bind_inverse;scale=np.linalg.norm(hand_world[:3,0]);socket=np.eye(4);socket[:3,:3]=basis/scale;socket[:3,3]=offset/scale;transform=np.linalg.inv(hand_world@socket);local=posed@transform[:3,:3].T+transform[:3,3]
   edges=np.concatenate([local[local_faces[:,b]]-local[local_faces[:,a]]for a,b in [(0,1),(1,2),(2,0)]]);max_edge=float(np.linalg.norm(edges,axis=1).max())
   record={'clip':clip,'time_s':float(t),'hand_region_max_triangle_edge_m':max_edge,'surfaces':{}}
   for name,tree in trees.items():
    distance,answer=tree.query(local);point_index,triangle_index,closest=answer
    record['surfaces'][name]={'minimum_sampled_vertex_surface_distance_m':distance,'conservative_entire_hand_triangle_surface_clearance_lower_bound_m':distance-max_edge,'hand_vertex':int(indices[point_index]),'weapon_triangle':triangle_index,'hand_point_weapon_local_m':local[point_index].tolist(),'closest_weapon_point_m':closest}
   rows.append(record)
  print('CLEARANCE_CLIP_DONE',clip,len(times),flush=True)
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 result={'schema_version':1,'scope':'Actual raw glTF LBS hand/finger+wrist-boundary region against actual runtime HERO broadblade replacement triangles, with the production hand socket and uniform-scale cancellation. All original keys+midpoints only. Not engine, continuous collision, visual crowding, AV or AAA approval. Distances are unsigned sampled-vertex/surface distances. The edge-length lower bound is conservative for the entire selected hand triangular surface; negative means inconclusive, not proven penetration. Expected start/end source-grasp contact is retained and not excluded from reports.','audit_script_sha256':sha(__file__),'skin_helper_sha256':sha(Path(__file__).parent/'skin_lbs_audit.py'),'candidate_sha256':sha(body),'actual_runtime_weapon_geometry_sha256':sha(weapon),'runtime_grip_sha256':sha(root/'game/data/character_grips.json'),'coordinate_system':'weapon_local_metres; rigid transform invariance from source_glTF raw scene; runtime PI/floor do not change distances','hand_region_definition':'All triangles incident to a vertex with LeftHand or left-digit influence>.05, including boundary vertices','hand_vertices':len(indices),'hand_triangles':len(hand_faces),'weapon_triangles':len(tri),'partition':'blade any triangle above localY.16; hilt/guard any triangle at/below.16; overlapping boundary triangles are deliberately counted in both','elapsed_s':time.monotonic()-start,'samples':rows}
 for name in trees:
  result['minimum_'+name]=min(rows,key=lambda r:r['surfaces'][name]['minimum_sampled_vertex_surface_distance_m'])
  active=[r for r in rows if (.18 if r['clip']=='light_3'else .13)-1e-7<=r['time_s']<=((.18+.22)if r['clip']=='light_3'else .13+.17)+1e-7]
  result['minimum_active_'+name]=min(active,key=lambda r:r['surfaces'][name]['minimum_sampled_vertex_surface_distance_m'])
 out=args.output;out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items()if k.startswith('minimum_')or k in ['elapsed_s','hand_vertices','hand_triangles']}),flush=True)
if __name__=='__main__':main()
