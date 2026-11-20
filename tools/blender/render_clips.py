"""D.2: render baked clips for review: Cycles stills at phase frames, and full-frame image sequences encoded to MP4
(normal speed and 25% slow motion by frame repetition). Opens the saved animation .blend in memory; never saves it.

Usage: blender -b --factory-startup --python tools/blender/render_clips.py -- <aldren|william> <anim ver> [clip,clip,...]
"""
import bpy, os, sys, json, math, glob
from mathutils import Vector as V, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H

ARGS = C.args()
CHAR, AVER = ARGS[0], ARGS[1]
ONLY = set(ARGS[2].split(",")) if len(ARGS) > 2 and ARGS[2] != "all" else None
OUT = f"previews/v0.4.0/animation/{CHAR}_{AVER}" + (f"_{ARGS[3]}" if len(ARGS) > 3 else "")
R_SWORD = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()
meta = json.load(open(os.path.join(C.REPO, f"assets/v0.4.0/animations/{CHAR}_clips_{AVER}.json")))
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, meta["blend_local"]), load_ui=False)
C.safe_prefs()
scene = bpy.context.scene
rig_name = [o.name for o in bpy.data.objects if o.type == "ARMATURE" and o.name.endswith("_rig") and CHAR.replace("william", "william_fp") in o.name.replace("ser_", "")][0]
arm = bpy.data.objects[rig_name]
sword = [o for o in bpy.data.objects if o.name.startswith("longsword_xva") and o.parent is None][0]
prev = [c for c in bpy.data.collections if c.name.startswith("preview_only")][0]
for tr in arm.animation_data.nla_tracks:
    tr.mute = True

opp = None
if CHAR == "william":
    # opponent: the native Ser Aldren rig + meshes with his baked clips, at the guard distance, facing William
    ameta = json.load(open(os.path.join(C.REPO, "assets/v0.4.0/animations/aldren_clips_v009.json")))
    with bpy.data.libraries.load(os.path.join(C.REPO, ameta["blend_local"]), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("aldren_") or n == "ser_aldren_v008_rig" or n.startswith("longsword_xva") or n in
                       ("hand_primary", "hand_secondary", "blade_base", "blade_mid", "blade_tip", "edge_true", "edge_false", "col_blade", "col_cross", "col_hilt",
                        "blade", "crossguard", "grip", "pommel", "pommel_peen")]
        dst.actions = [n for n in src.actions if n.startswith("aldren_")]
    holder = bpy.data.objects.new("opponent_root", None); scene.collection.objects.link(holder)
    loaded = [o for o in dst.objects if o]
    for o in loaded:
        scene.collection.objects.link(o)
    for o in loaded:
        # re-parent anything whose parent was not loaded into the scene (the rig's root empty), keeping world transform
        if o.parent is None or o.parent not in loaded:
            mw = o.matrix_world.copy(); o.parent = holder; o.matrix_world = mw
    for o in bpy.data.objects:                      # hide the static v006 preview opponent (kept, not deleted)
        if o.type == "MESH" and o.parent and o.parent.type == "ARMATURE" and o.parent.name not in (arm.name, "ser_aldren_v008_rig"):
            o.hide_render = True
    opp = bpy.data.objects["ser_aldren_v008_rig"]
    opp_sword = [o for o in dst.objects if o and o.name.startswith("longsword_xva") and o.parent == holder][0]
    holder.matrix_world = Matrix.Translation((0, -ameta["engagement"]["guard_distance_m"], 0)) @ Matrix.Rotation(math.pi, 4, "Z")
    if opp.animation_data:
        for tr in opp.animation_data.nla_tracks: tr.mute = True
    for pb in opp.pose.bones:
        for c in pb.constraints: c.enabled = False
    PAIR = {"william_idle_ready": ("aldren_idle_ready", 0), "william_attack_head": ("aldren_parry_head", -16),
            "william_attack_upper_left": ("aldren_idle_ready", 0), "william_attack_upper_right": ("aldren_idle_ready", 0),
            "william_parry_head": ("aldren_attack_head", 16), "william_deflect_head": ("aldren_attack_head", 24)}


def set_frame(clip, f):
    arm.animation_data.action = bpy.data.actions[clip]
    if hasattr(arm.animation_data, "action_slot") and bpy.data.actions[clip].slots:
        arm.animation_data.action_slot = bpy.data.actions[clip].slots[0]
    if opp is not None:
        oc, shift = PAIR[clip]
        opp.animation_data_create()
        opp.animation_data.action = bpy.data.actions[oc]
        if hasattr(opp.animation_data, "action_slot") and bpy.data.actions[oc].slots:
            opp.animation_data.action_slot = bpy.data.actions[oc].slots[0]
        ofr = max(0, min(int(bpy.data.actions[oc].frame_range[1]), f + shift))
    scene.frame_set(f)
    if opp is not None:
        # opponent evaluated at its own aligned frame: temporarily offset its action via NLA-free frame mapping
        opp.animation_data.action_extrapolation = "HOLD"
        opp.animation_data.action_blend_type = "REPLACE"
        opp.animation_data.action_influence = 1.0
        for pb in opp.pose.bones:
            pass
    bpy.context.view_layer.update()
    sword.matrix_world = H.bone_world(arm, "weapon_r") @ R_SWORD @ Matrix.Translation((0, 0, 0.05))
    if opp is not None:
        # sample opponent at its aligned frame by evaluating the action's fcurves directly on its pose bones
        act = bpy.data.actions[PAIR[clip][0]]
        ofr = max(0, min(act.frame_range[1], f + PAIR[clip][1]))
        scene.frame_set(int(ofr)); bpy.context.view_layer.update()
        om = H.bone_world(opp, "weapon_r").copy()
        snap = {pb.name: pb.matrix_basis.copy() for pb in opp.pose.bones}
        scene.frame_set(f); bpy.context.view_layer.update()
        opp.animation_data.action = None
        for n, mb in snap.items(): opp.pose.bones[n].matrix_basis = mb
        bpy.context.view_layer.update()
        opp_sword.matrix_world = H.bone_world(opp, "weapon_r") @ R_SWORD @ Matrix.Translation((0, 0, 0.05))
        bpy.context.view_layer.update()


def stills_frames(c):
    if c["kind"] == "attack":
        return {"windup": 11, "acceleration": 21, "contact": c["contact_frame"], "follow_through": 29, "recovery": 40}
    if c["kind"] == "parry":
        return {"ready": 0, "raise": c["phases"]["raise"][1] // 2, "hold": c["phases"]["hold"][0] + 2, "recover": (c["phases"]["recover"][0] + c["frame_end"]) // 2}
    if c["kind"] == "deflect":
        return {"impact": 1, "absorb": 4, "settle": 12, "end": c["frame_end"]}
    return {"ready": 0, "breath_in": 45}


# cameras
eng = C.set_engine(scene)
if CHAR == "aldren":
    cams = {"front34": C.look_cam(prev, "rv_front34", (-1.8, -2.7, 1.45), (0, -0.35, 1.10), lens=42),
            "side": C.look_cam(prev, "rv_side", (-3.1, -0.45, 1.20), (0, -0.45, 1.05), lens=40)}
    res = (640, 800)
else:
    cams = {"pov": bpy.data.objects["cam_pov"]}
    res = (540, 960)

report = {"char": CHAR, "anim_version": AVER, "engine": eng, "stills": {}, "videos": {}}
for clip, c in meta["clips"].items():
    if ONLY and clip not in ONLY:
        continue
    # stills (Cycles 32 spp + denoise)
    scene.cycles.samples = 32
    for ph, f in stills_frames(c).items():
        set_frame(clip, f)
        for cn, cam in cams.items():
            p = C.render_still(scene, cam, f"{OUT}/stills/{clip}_{cn}_{f:02d}_{ph}.png", res)
            report["stills"].setdefault(clip, []).append(os.path.relpath(p, C.REPO).replace("\\", "/"))
    # full sequence (Cycles 8 spp + denoise, half res) -> MP4 at 100% and 25%
    scene.cycles.samples = 8
    cam_name, cam = next(iter(cams.items()))
    seq_dir = f"{OUT}/frames/{clip}_{cam_name}"
    for f in range(c["frame_end"] + 1):
        set_frame(clip, f)
        C.render_still(scene, cam, f"{seq_dir}/{f:04d}.png", (480, 600) if CHAR == "aldren" else (360, 640))
    report["videos"][clip] = {"frames": seq_dir}

# encode videos in a separate scene via the sequencer (MP4 / H.264)
vs = bpy.data.scenes.new("video")
vs.sequence_editor_create()
sed = vs.sequence_editor
coll = sed.strips if hasattr(sed, "strips") else sed.sequences
for clip, info in report["videos"].items():
    files = sorted(glob.glob(os.path.join(C.REPO, info["frames"], "*.png")))
    if not files:
        continue
    for label, fps, fps_base in (("100pct", 30, 1.0), ("25pct", 30, 4.0)):
        for s in list(coll):
            coll.remove(s) if hasattr(coll, "remove") else None    # sequencer strip removal in memory only (no files touched)
        st = coll.new_image(name=clip, filepath=files[0], channel=1, frame_start=1)
        for fp in files[1:]:
            st.elements.append(os.path.basename(fp))
        vs.frame_start, vs.frame_end = 1, len(files)
        vs.render.fps, vs.render.fps_base = fps, fps_base
        im = bpy.data.images.load(files[0])
        vs.render.resolution_x, vs.render.resolution_y = im.size[0], im.size[1]
        vs.render.resolution_percentage = 100
        isf = vs.render.image_settings
        if hasattr(isf, "media_type"):
            isf.media_type = "VIDEO"
        isf.file_format = "FFMPEG"
        vs.render.ffmpeg.format = "MPEG4"; vs.render.ffmpeg.codec = "H264"; vs.render.ffmpeg.constant_rate_factor = "HIGH"
        target = C.new_path(f"{OUT}/video/{clip}_{label}.mp4")
        vs.render.filepath = target
        vs.render.use_sequencer = True
        bpy.context.window_manager  # noqa
        with bpy.context.temp_override(scene=vs):
            bpy.ops.render.render(animation=True, scene=vs.name)
        produced = [p for p in glob.glob(os.path.join(os.path.dirname(target), "*.mp4")) if os.path.basename(p).startswith(f"{clip}_{label}")]
        report["videos"][clip][label] = [os.path.relpath(p, C.REPO).replace("\\", "/") for p in produced]
C.write_json(f"{OUT}/render_report_{CHAR}.json", report)
print("WOS_RENDERS", json.dumps({k: len(v) for k, v in report["stills"].items()}), json.dumps(report["videos"]))
