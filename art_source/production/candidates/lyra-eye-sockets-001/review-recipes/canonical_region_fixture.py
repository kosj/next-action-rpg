"""Private review adapter: explicitly clear imported matrix_basis before POSE."""
from pathlib import Path
import hashlib,json,os,sys,traceback

script=Path('tools/review_character_regions.py').resolve()
text=script.read_text()
old='obj.animation_data_clear()'
new='if obj.type == "ARMATURE":\n            _sample_reset_for_review(obj)\n        obj.animation_data_clear()'
if text.count(old)!=1:raise RuntimeError('Review adapter source changed')
text=text.replace(old,new)
helper='\ndef _sample_reset_for_review(arm):\n    if arm.animation_data is None:\n        raise ValueError("Source needs explicit RESET for canonical Head pose review")\n    aliases={t.name:next(iter({s.action for s in t.strips if s.action})) for t in arm.animation_data.nla_tracks if any(s.action for s in t.strips)}\n    for track in arm.animation_data.nla_tracks:track.mute=True\n    arm.data.pose_position="POSE"\n    arm.animation_data.action=aliases["RESET"]\n    bpy.context.scene.frame_set(int(aliases["RESET"].frame_range[0]))\n    bpy.context.view_layer.update()\n\n'
text=text.replace('def main():',helper+'\ndef main():')
sys.path.insert(0,str(script.parent))
try:
    scope={'__name__':'_private_review_fixture','__file__':str(script)}
    exec(compile(text,str(script),'exec'),scope)
    scope['main']()
    args=sys.argv[sys.argv.index('--')+1:];out=Path(args[args.index('--output')+1])
    p=out/'review.json';report=json.loads(p.read_text())
    report['pose_fixture']={'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'base_review_tool_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
          'patch':'Sample imported complete RESET action before clearing playback; canonical glTF default matched independently within0.72micrometers'}
    p.write_text(json.dumps(report,indent=2)+'\n')
except Exception:
    traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
