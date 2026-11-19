"""Diagnostic (read-only): print min/mean/max of PNG textures, both on disk and as seen inside a saved .blend.
Usage: blender -b --factory-startup --python tools/blender/diag_texture_stats.py -- <rel .blend>"""
import bpy, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import common as C
rel = C.args()[0]
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, rel), load_ui=False)
for img in bpy.data.images:
    if not img.filepath or "steel" not in img.name:
        continue
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, 0]
    print(f"WOS_TEX {img.name} cs={img.colorspace_settings.name} file={os.path.basename(img.filepath)} "
          f"min={px.min():.3f} mean={px.mean():.3f} max={px.max():.3f}")
for m in bpy.data.materials:
    if "steel" in m.name:
        b = m.node_tree.nodes["Principled BSDF"]
        links = [(l.from_node.bl_idname, getattr(l.from_node, 'image', None) and l.from_node.image.name, l.to_socket.name) for l in m.node_tree.links]
        print("WOS_MAT", m.name, links)
