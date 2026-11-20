"""Shared, non-destructive helpers for Will of Steel Blender scripts.

Safety conventions (handoff §1):
- Every output path is new. `new_path()` raises if the file already exists, so nothing is overwritten.
- `save_version = 0` disables Blender's rolling .blend1 backups (which overwrite the previous backup).
- Scripts run with `-b --factory-startup`, so no user preferences are read or saved and autosave is off.
- No script calls any delete/remove filesystem API.
"""
import bpy, os, sys, json, hashlib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def args():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


def new_path(rel):
    p = os.path.join(REPO, rel)
    if os.path.exists(p):
        raise FileExistsError(f"Refusing to overwrite existing file: {p}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_prefs():
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.use_auto_save_temporary_files = False


def empty_scene():
    """Start from an empty in-memory scene. read_homefile only replaces data in memory; it never touches files on disk."""
    bpy.ops.wm.read_homefile(use_empty=True)
    safe_prefs()
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    return s


def save_image(img, rel):
    p = new_path(rel)
    img.filepath_raw = p
    img.file_format = "PNG"
    img.save()
    return p


def save_blend(rel):
    p = new_path(rel)
    bpy.ops.wm.save_as_mainfile(filepath=p, check_existing=True, copy=True)
    return p


def export_glb(rel, **kw):
    p = new_path(rel)
    opts = dict(filepath=p, export_format="GLB", export_yup=True, export_apply=True,
                export_extras=True, export_cameras=False, export_lights=False)
    opts.update(kw)
    bpy.ops.export_scene.gltf(**opts)
    return p


def write_json(rel, data):
    p = new_path(rel)
    with open(p, "x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return p


def set_engine(scene, samples=96):
    """Review renders use Cycles (CPU) with denoising. On this workstation (Radeon Pro W5500, no
    VK_KHR_dynamic_rendering) Eevee falls back to a degraded path whose reflections ignore roughness."""
    scene.render.engine = "CYCLES"
    c = scene.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_denoising = True
    c.use_adaptive_sampling = True
    c.max_bounces = 6
    scene.render.film_transparent = False
    return "CYCLES"


def preview_stage(scene, target=(0, 0, 0), radius=1.0, floor=False):
    """Studio stage for review renders: vertical-gradient world (dark floor, warm horizon, cool sky) plus
    key/fill/rim softboxes aimed at `target`. Everything goes in a 'preview_only' collection; call this after export."""
    import math
    from mathutils import Vector
    prev = bpy.data.collections.new("preview_only")
    scene.collection.children.link(prev)
    eng = set_engine(scene)
    w = bpy.data.worlds.new("preview_world"); scene.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
    ramp = nt.nodes.new("ShaderNodeValToRGB"); el = ramp.color_ramp.elements
    # overcast-courtyard gradient: warm stone ground bounce, bright hazy horizon, soft cool sky
    el[0].position, el[0].color = 0.30, (0.16, 0.145, 0.13, 1)
    el[1].position, el[1].color = 0.80, (0.62, 0.66, 0.72, 1)
    e2 = el.new(0.52); e2.color = (0.85, 0.80, 0.72, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"]); nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    T = Vector(target)

    def light(name, offset, energy, size):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy * radius ** 2; ld.size = size * radius
        o = bpy.data.objects.new(name, ld); o.location = T + Vector(offset) * radius
        o.rotation_euler = (T - o.location).to_track_quat("-Z", "Y").to_euler(); prev.objects.link(o)
    light("key", (-1.2, -2.2, 1.4), 260, 1.6)
    light("fill", (1.8, -1.6, 0.3), 90, 2.0)
    light("rim", (0.6, 2.2, 1.6), 220, 1.0)
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=20 * radius, location=(T.x, T.y, 0))
        fl = bpy.context.active_object; fl.name = "preview_floor"
        for c in fl.users_collection: c.objects.unlink(fl)  # unlinks from a collection in memory only
        prev.objects.link(fl)
        m = bpy.data.materials.new("preview_floor"); m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.28, 0.25, 1)
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
        fl.data.materials.append(m)
    scene.view_settings.view_transform = "AgX"
    return prev, eng


def look_cam(prev, name, loc, target, lens=50, ortho=None):
    from mathutils import Vector
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start = 0.01
    o = bpy.data.objects.new(name, cd); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    prev.objects.link(o)
    return o


def render_still(scene, cam, rel, res=(1080, 1080)):
    p = new_path(rel)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_stamp_filename = False   # never embed the local .blend path in published PNG metadata
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    return p
