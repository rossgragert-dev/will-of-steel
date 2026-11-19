"""Read-only probe v2: Blender version, glTF exporter, render engines, temp dir. Writes one new JSON file."""
import bpy, sys, json, addon_utils
out = sys.argv[sys.argv.index("--") + 1]
info = {
    "version": bpy.app.version_string,
    "background": bpy.app.background,
    "gltf_export_op": hasattr(bpy.ops.export_scene, "gltf"),
    "gltf_addon": [m.__name__ for m in addon_utils.modules() if "gltf" in m.__name__],
    "engines": [getattr(e, "bl_idname", e.__name__) for e in bpy.types.RenderEngine.__subclasses__()],
    "engine_enum": [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items],
    "tempdir": bpy.app.tempdir,
    "python": sys.version,
}
with open(out, "x") as f:
    json.dump(info, f, indent=2)
