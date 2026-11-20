"""Diagnostic (read-only): reproduce render_clips.py's opponent placement for William and print world distances.
Never saves. Usage: blender -b --factory-startup --python tools/blender/diag_fp_spacing.py"""
import bpy, os, sys, json, math
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H
meta = json.load(open(os.path.join(C.REPO, "assets/v0.4.0/animations/william_clips_v004.json")))
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, meta["blend_local"]), load_ui=False)
ameta = json.load(open(os.path.join(C.REPO, "assets/v0.4.0/animations/aldren_clips_v007.json")))
with bpy.data.libraries.load(os.path.join(C.REPO, ameta["blend_local"]), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("aldren_") or n == "ser_aldren_v008_rig"]
loaded = [o for o in dst.objects if o]
print("WOS_LOADED", [(o.name, o.type, o.parent.name if o.parent else None, tuple(round(v, 3) for v in o.matrix_world.translation)) for o in loaded])
rig = bpy.data.objects["ser_aldren_v008_rig"]
print("WOS_RIG_PARENT", rig.parent.name if rig.parent else None, "parent_type", rig.parent_type)
for o in loaded:
    print("WOS_MESH_PARENTING", o.name, o.parent.name if o.parent else None, [m.type + ":" + (m.object.name if getattr(m, "object", None) else "") for m in o.modifiers])
cam = bpy.data.objects["cam_pov"]
print("WOS_CAM", tuple(round(v, 3) for v in cam.matrix_world.translation))
