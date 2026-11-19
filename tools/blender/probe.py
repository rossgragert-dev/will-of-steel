"""Read-only probe: reports Blender version and glTF exporter availability.
Writes a single new JSON file to the path given after `--`."""
import bpy, sys, json, addon_utils
out = sys.argv[sys.argv.index("--") + 1]
info = {
    "version": bpy.app.version_string,
    "background": bpy.app.background,
    "gltf_export_op": hasattr(bpy.ops.export_scene, "gltf"),
    "gltf_addon": [m.__name__ for m in addon_utils.modules() if "gltf" in m.__name__],
    "engines": [e.bl_idname for e in bpy.types.RenderEngine.__subclasses__()],
    "tempdir": bpy.app.tempdir,
    "python": sys.version,
}
with open(out, "x") as f:  # "x" = fail rather than overwrite
    json.dump(info, f, indent=2)
