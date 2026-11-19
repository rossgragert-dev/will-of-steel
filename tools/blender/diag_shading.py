"""Diagnostic (read-only on sources): open a saved character .blend in memory, render one close-up under several
shading variants to isolate an artifact. Writes only new PNGs under previews/v0.4.0/diag/. Never saves the .blend.
Usage: blender -b --factory-startup --python tools/blender/diag_shading.py -- <rel .blend> <tag>
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import common as C

rel, tag = C.args()[:2]
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, rel), load_ui=False)
C.safe_prefs()
scene = bpy.context.scene
scene.cycles.samples = 24
cam = bpy.data.objects["cam_guard_detail_upper"]
steel = bpy.data.materials["aldren_steel"]
nt = steel.node_tree
bsdf = nt.nodes["Principled BSDF"]
nlink = [l for l in nt.links if l.to_socket == bsdf.inputs["Normal"]]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("aldren_")]


def shot(name):
    C.render_still(scene, cam, f"previews/v0.4.0/diag/{tag}_{name}.png", (500, 500))


shot("a_asis")
for l in nlink:
    nt.links.remove(l)                      # in-memory node link only; the .blend is never saved
shot("b_no_normalmap")
for o in meshes:
    for p in o.data.polygons:
        p.use_smooth = False
shot("c_flat")
bsdf.inputs["Metallic"].default_value = 0.0
for l in [l for l in nt.links if l.to_socket == bsdf.inputs["Roughness"]]:
    nt.links.remove(l)
bsdf.inputs["Roughness"].default_value = 0.6
shot("d_flat_matte")
print("WOS_DIAG done")
