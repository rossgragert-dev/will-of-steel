"""Mobile export variant: re-export a saved character scene with WebP textures (glTF EXT_texture_webp, supported by
three.js GLTFLoader and iOS Safari 14+). Masters (PNG GLBs, PNG textures, .blend) are untouched; output is a new file.
Usage: blender -b --factory-startup --python tools/blender/export_mobile.py -- <rel .blend> <rel out .glb> [quality]
"""
import bpy, os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import common as C

src, out = C.args()[:2]
q = int(C.args()[2]) if len(C.args()) > 2 else 85
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, src), load_ui=False)
C.safe_prefs()
# export only the character: its armature and skinned meshes (not preview stage, cameras, imported swords/enemies)
rig = [o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.endswith("_rig") and not o.name.startswith("ser_aldren_v006")][0]
keep = {rig} | {o for o in bpy.data.objects if o.parent == rig and o.type == "MESH"} | ({rig.parent} if rig.parent else set())
for o in bpy.context.view_layer.objects:
    o.select_set(o in keep)
for pb in rig.pose.bones:                        # export in rest pose
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
glb = C.export_glb(out, use_selection=True, export_skins=True, export_animations=False,
                   export_image_format="WEBP", export_image_quality=q)
print("WOS_MOBILE", json.dumps({"glb": out, "bytes": os.path.getsize(glb), "sha256": C.sha256(glb), "quality": q}))
