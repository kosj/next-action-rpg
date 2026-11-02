"""Read-only exact UV mask preparation; no image decoding/editing or engine."""
from pathlib import Path
import argparse,hashlib,json,sys,math
import numpy as np
sys.path.insert(0,str(Path(__file__).parent));from audit_robe_repair import Asset
ROOT=Path(__file__).resolve().parents[3]

def raster(triangle,size=1024):
 points=triangle*size;lo=np.floor(points.min(axis=0)-.5).astype(int);hi=np.ceil(points.max(axis=0)-.5).astype(int);a,b,c=points
 denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
 if abs(denominator)<1e-12:return set()
 out=set()
 for y in range(max(0,lo[1]),min(size-1,hi[1])+1):
  for x in range(max(0,lo[0]),min(size-1,hi[0])+1):
   p=x+.5;q=y+.5;u=((b[1]-c[1])*(p-c[0])+(c[0]-b[0])*(q-c[1]))/denominator;v=((c[1]-a[1])*(p-c[0])+(a[0]-c[0])*(q-c[1]))/denominator
   if min(u,v,1-u-v)>=-1e-8:out.add((x,y))
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();asset=Asset(a.source);rest,_=asset.evaluate(None)
 specs=[{'id':'gray_front_cloth','faces':[3664,3669,3700,3668,3685,3686],'clone_top_left_offset_px':[35,0],'paint_enabled':True},{'id':'tiny_front_tail','faces':[3641,3666,3667],'clone_top_left_offset_px':[20,0],'paint_enabled':False},{'id':'normal_boundary_notch_2806','faces':[2806],'clone_top_left_offset_px':[-12,0],'paint_enabled':False},{'id':'normal_boundary_tail_3076','faces':[3076],'clone_top_left_offset_px':[0,8],'paint_enabled':False}]
 protected_joints={i for i,n in enumerate(asset.skin['joints'])if any(token in asset.doc['nodes'][n].get('name','')for token in ['Head','Neck','Hand','Thumb','Index','Middle','Ring','Pinky'])}
 protected_vertices=np.any(np.isin(asset.joints,list(protected_joints))&(asset.weights>.01),axis=1);patches=[]
 for spec in specs:
  core=set().union(*(raster(asset.uv[asset.tri[i]])for i in spec['faces']));allowed=set()
  for x,y in core:
   for dy in range(-2,3):
    for dx in range(-2,3):
     if dx*dx+dy*dy<=4 and 0<=x+dx<1024 and 0<=y+dy<1024:allowed.add((x+dx,y+dy))
  if not core:raise ValueError('Empty source UV patch')
  bbox=[min(x for x,y in allowed),min(y for x,y in allowed),max(x for x,y in allowed),max(y for x,y in allowed)];touched=[];protected=[]
  for ti,ids in enumerate(asset.tri):
   uv=asset.uv[ids]*1024
   if uv[:,0].max()<bbox[0] or uv[:,0].min()>bbox[2]+1 or uv[:,1].max()<bbox[1] or uv[:,1].min()>bbox[3]+1:continue
   if raster(asset.uv[ids]).intersection(allowed):
    touched.append(int(ti))
    if np.any(protected_vertices[ids]):protected.append(int(ti))
  if protected:raise ValueError('Mask overlaps protected face/hand UVs')
  vertex_ids=np.unique(asset.tri[touched].flatten())
  patches.append({**spec,'core_top_left_pixels':[list(p)for p in sorted(core,key=lambda p:(p[1],p[0]))],'allowed_top_left_pixels':[list(p)for p in sorted(allowed,key=lambda p:(p[1],p[0]))],'allowed_bbox_top_left_px':bbox,'touched_uv_triangles':touched,'protected_face_hand_uv_overlap':protected,'actual_rest_touched_cloth_bounds':{'min':rest[vertex_ids].min(axis=0).tolist(),'max':rest[vertex_ids].max(axis=0).tolist()}})
 report={'schema_version':1,'source_file':a.source.as_posix(),'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'dimensions':[1024,1024],'pixel_coordinates':'glTF image top-left pixel centres; Blender buffer row=1023-y','policy':'Only explicitly enabled patches; max2pixel dilation feather. All outside allowed pixels and ORM G/B unchanged exact. Inspect channel values before deciding AO.R/normal edit.','patches':patches,'tool_file':str(Path(__file__).relative_to(ROOT)),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps([{'id':x['id'],'core':len(x['core_top_left_pixels']),'allowed':len(x['allowed_top_left_pixels']),'protected_overlap':len(x['protected_face_hand_uv_overlap']),'bbox':x['allowed_bbox_top_left_px']}for x in patches]))

if __name__=='__main__':main()
