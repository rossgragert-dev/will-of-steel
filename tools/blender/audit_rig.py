"""Rig audit (read-only on sources): opens a saved character .blend in memory, reports hierarchy, deform bones,
constraints, joint limits, skin-weight health and socket orientation, then drives range-of-motion poses through the
rig's own IK and renders them. The .blend is never saved. Writes one new JSON report and new PNGs.

Usage: blender -b --factory-startup --python tools/blender/audit_rig.py -- <rel .blend> <tag> <knight|arms>
"""
import bpy, os, sys, json, math
from mathutils import Vector as V, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H

rel, tag, kind = C.args()[:3]
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, rel), load_ui=False)
C.safe_prefs()
scene = bpy.context.scene
key = "aldren" if kind == "knight" else "william"
arm = [o for o in bpy.data.objects if o.type == "ARMATURE" and key in o.name and o.name.endswith("_rig")][0]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
rep = {"blend": rel, "armature": arm.name, "bones": len(arm.data.bones)}

# ---- hierarchy / deform / constraints / limits
rep["deform_bones"] = [b.name for b in arm.data.bones if b.use_deform]
rep["non_deform_bones"] = [b.name for b in arm.data.bones if not b.use_deform]
rep["hierarchy"] = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
rep["constraints"] = {pb.name: [f"{c.type}->{getattr(c, 'subtarget', '')}" + (f" pole={c.pole_subtarget} {math.degrees(c.pole_angle):.0f}deg chain={c.chain_count}" if c.type == "IK" else "")
                                for c in pb.constraints] for pb in arm.pose.bones if pb.constraints}
rep["joint_limits"] = {pb.name: pb.get("wos_limit") for pb in arm.pose.bones if pb.get("wos_limit")}
rep["rolls_deg"] = {}
for b in arm.data.bones:
    if b.name.split("_")[0] in ("upperarm", "forearm", "hand", "thigh", "calf", "weapon", "grip"):
        M = b.matrix_local.to_3x3()
        rep["rolls_deg"][b.name] = {"y_axis": [round(x, 3) for x in M.col[1]], "z_axis": [round(x, 3) for x in M.col[2]]}

# ---- skin weights
wstats = {}
for o in meshes:
    names = {g.index: g.name for g in o.vertex_groups}
    over4 = unweighted = badsum = 0
    maxinf = 0
    for v in o.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-4 and arm.data.bones.get(names[g.group]) and arm.data.bones[names[g.group]].use_deform]
        n = len(ws); maxinf = max(maxinf, n)
        if n == 0: unweighted += 1
        if n > 4: over4 += 1
        if n and abs(sum(ws) - 1) > 0.02: badsum += 1
    wstats[o.name] = {"verts": len(o.data.vertices), "max_influences": maxinf, "verts_over_4_influences": over4,
                      "unweighted": unweighted, "sum_not_1": badsum}
rep["weights"] = wstats

# ---- sockets
def sock(name):
    b = arm.data.bones.get(name)
    if not b: return None
    M = b.matrix_local
    return {"head": [round(x, 4) for x in M.translation], "y_blade": [round(x, 3) for x in M.to_3x3().col[1]],
            "z_true_edge": [round(x, 3) for x in M.to_3x3().col[2]], "parent": b.parent.name}
rep["sockets"] = {n: sock(n) for n in ("weapon_r", "grip_l", "fp_eye")}

# ---- range-of-motion stress poses via the rig's own IK (hands on a shared sword frame)
rest = lambda b: arm.data.bones[b].matrix_local
def pose_sword(G_r, blade, edge, poles):
    blade = V(blade).normalized(); edge = V(edge); edge = (edge - blade * edge.dot(blade)).normalized()
    G_l = V(G_r) - blade * 0.14
    for side, s, G in (("r", "weapon_r", V(G_r)), ("l", "grip_l", G_l)):
        relm = rest(f"hand_{side}").inverted() @ rest(s)
        H.set_pose_matrix(arm, f"ik_hand_{side}", arm.matrix_world @ (H.frame_matrix(G, blade, edge) @ relm.inverted()))
    for side, p in poles.items():
        H.set_pose_matrix(arm, f"pole_elbow_{side}", Matrix.Translation(p))
    bpy.context.view_layer.update()

def elbow_deg(side):
    u = H.bone_world(arm, f"upperarm_{side}"); f = H.bone_world(arm, f"forearm_{side}")
    a = u.to_3x3().col[1]; b = f.to_3x3().col[1]
    return round(math.degrees(a.angle(b)), 1)

def wrist_twist_deg(side):
    f = H.bone_world(arm, f"forearm_{side}").to_3x3(); h = H.bone_world(arm, f"hand_{side}").to_3x3()
    # twist = rotation of hand Z about the forearm axis relative to forearm Z
    ax = f.col[1].normalized()
    z1 = (f.col[2] - ax * f.col[2].dot(ax)).normalized(); z2 = (h.col[2] - ax * h.col[2].dot(ax)).normalized()
    return round(math.degrees(math.atan2(ax.dot(z1.cross(z2)), z1.dot(z2))), 1)

def measures():
    out = {}
    for s in "lr":
        out[f"wrist_err_{s}_mm"] = round((H.bone_world(arm, f"hand_{s}").translation - H.bone_world(arm, f"ik_hand_{s}").translation).length * 1000, 1)
        out[f"elbow_{s}_deg"] = elbow_deg(s)
        out[f"wrist_twist_{s}_deg"] = wrist_twist_deg(s)
        if arm.pose.bones.get(f"upperarm_{s}"):
            out[f"shoulder_elev_{s}_deg"] = round(math.degrees(math.asin(max(-1, min(1, H.bone_world(arm, f"upperarm_{s}").to_3x3().col[1].z)))), 1)
    return out

POSES = {}
if kind == "knight":
    POSES = {  # character faces -Y; right hand = -X
        "vom_tag_high": ((-0.16, -0.05, 1.70), (0.10, 0.45, 0.89), (-1, 0, 0), {"r": (-0.6, 0.3, 1.2), "l": (0.5, 0.2, 1.2)}),
        "overhead_parry": ((-0.22, -0.30, 1.72), (0.95, -0.15, 0.25), (0, 0, 1), {"r": (-0.6, 0.0, 1.2), "l": (0.6, 0.0, 1.2)}),
        "diag_windup_right": ((-0.30, 0.02, 1.55), (-0.55, 0.55, 0.62), (-0.5, -0.5, 0.2), {"r": (-0.7, 0.2, 1.0), "l": (0.4, 0.2, 1.0)}),
        "diag_followthrough_left": ((0.22, -0.30, 0.88), (0.55, -0.45, -0.70), (0.4, 0.4, -0.4), {"r": (-0.2, 0.3, 0.8), "l": (0.6, 0.3, 0.8)}),
        "low_guard_lunge": ((-0.05, -0.45, 0.95), (0.0, -0.95, -0.30), (0, 0, -1), {"r": (-0.5, 0.2, 0.8), "l": (0.5, 0.2, 0.8)}),
    }
else:
    eye = V((0, -0.075, 1.675))
    POSES = {
        "fp_high_windup": (eye + V((-0.18, 0.02, 0.10)), (0.15, 0.6, 0.78), (-1, 0, 0), {"r": eye + V((-0.6, 0.2, -0.1)), "l": eye + V((0.5, 0.2, -0.1))}),
        "fp_overhead_parry": (eye + V((-0.18, -0.36, 0.06)), (0.95, -0.25, 0.15), (0, 0, 1), {"r": eye + V((-0.7, 0.0, -0.1)), "l": eye + V((0.6, 0.0, -0.1))}),
        "fp_diag_follow": (eye + V((0.10, -0.40, -0.42)), (0.6, -0.5, -0.62), (0.4, 0.4, -0.4), {"r": eye + V((-0.3, 0.3, -0.6)), "l": eye + V((0.6, 0.3, -0.6))}),
    }
rom = {}
prev = None
cams = {}
for name, (G, blade, edge, poles) in POSES.items():
    pose_sword(G, blade, edge, {k: V(v) for k, v in poles.items()})
    pose_sword(G, blade, edge, {k: V(v) for k, v in poles.items()})
    rom[name] = measures()
    if prev is None:
        prev, eng = C.preview_stage(scene, target=(0, 0, 1.2 if kind == "knight" else 1.45), radius=1.4, floor=(kind == "knight"))
        scene.cycles.samples = 32
        tgt = (0, 0, 1.15) if kind == "knight" else (0, -0.35, 1.45)
        cams["a"] = C.look_cam(prev, "audit_cam_a", (-1.9, -2.3, 1.55) if kind == "knight" else (-0.9, -1.2, 1.7), tgt, lens=50)
        cams["b"] = C.look_cam(prev, "audit_cam_b", (-2.8, 0.4, 1.3) if kind == "knight" else (0.9, -1.0, 1.5), tgt, lens=50)
    for cn, cam in cams.items():
        C.render_still(scene, cam, f"previews/v0.4.0/rig_audit/{tag}_{name}_{cn}.png", (640, 800))
rep["rom_poses"] = rom
C.write_json(f"docs/asset-pipeline/rig_audit_{tag}.json", rep)
print("WOS_AUDIT", json.dumps({"weights": wstats, "rom": rom, "sockets": rep["sockets"]}))
