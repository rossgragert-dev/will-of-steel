"""C.2: redesign William's first-person overhead (head, zone 5) parry for visibility without compromising grip,
reach or parry geometry. Opens the saved william_fp_arms_v004 scene in memory (rig, calibrated IK, viewmodel camera,
opponent at 2.3 m) and never saves over it. Mesh and rig are unchanged; the result is a new guard-pose set
(william_fp_guards_<ver>.json) plus POV renders and a side-by-side comparison with v004.

Parry geometry (hard constraints, all in William's camera space, metres, about the true eye):
  * blade crosses the vertical centre plane (x = 0) above the eye (y >= +0.04) and 0.15-0.75 m in front;
  * at least 0.25 m of blade lies left of centre (covers the line of a descending blow);
  * blade within 30 deg of horizontal; true edge faces up (toward the incoming strike);
  * both hands on the grip (IK wrist error <= 3 mm), elbows within limits (IK hinge 0-150 deg).
Usage: blender -b --factory-startup --python tools/blender/fp_parry_search.py -- v005
"""
import bpy, os, sys, json, math, itertools
import numpy as np
from mathutils import Vector as V, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H
import wos_fpview as FV

VER = (C.args() or ["v005"])[0]
SRC = "source/blender/first-person/william_fp_arms_v004.blend"
bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, SRC), load_ui=False)
C.safe_prefs()
scene = bpy.context.scene
arm = [o for o in bpy.data.objects if o.type == "ARMATURE" and "william" in o.name and o.name.endswith("_rig")][0]
arms_mesh = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
enemy = [o for o in bpy.data.objects if o.type == "MESH" and o.parent and o.parent.type == "ARMATURE" and o.parent != arm]
sword = [o for o in bpy.data.objects if o.name.startswith("longsword_xva") and o.parent is None][0]
secm = [o for o in bpy.data.objects if o.name.startswith("hand_secondary")][0]
bb = [o for o in bpy.data.objects if o.name.startswith("blade_base")][0]
bt = [o for o in bpy.data.objects if o.name.startswith("blade_tip")][0]
pov = bpy.data.objects["cam_pov"]
view = FV.View(pov)
EYE = V((0, -0.075, 1.675))
rest = lambda b: arm.data.bones[b].matrix_local
R = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()
clav_rest = {s: rest(f"clavicle_{s}").copy() for s in "lr"}
G4 = json.load(open(os.path.join(C.REPO, "assets/v0.4.0/first-person/william_fp_guards_v004.json")))


def cam2b(v): return V((-v[0], v[2], v[1]))
def b2cam(v): return V((-v[0], v[2], v[1]))


def bladeAxis(p):
    a, b, c = p
    return V((-math.cos(b) * math.sin(c), math.cos(a) * math.cos(c) - math.sin(a) * math.sin(b) * math.sin(c),
              math.sin(a) * math.cos(c) + math.cos(a) * math.sin(b) * math.sin(c)))


def set_clav(lift):
    for s, sx in (("l", 1), ("r", -1)):
        h = clav_rest[s].translation
        Rw = Matrix.Rotation(math.radians(lift), 4, V((0, -sx, 0))) @ Matrix.Rotation(math.radians(lift * 0.8), 4, V((0, 0, -sx)))
        H.set_pose_matrix(arm, f"clavicle_{s}", Matrix.Translation(h) @ Rw @ Matrix.Translation(-h) @ clav_rest[s])


POLES = {"down": (0.45, 0.35, -0.35), "wide": (0.65, 0.15, -0.05), "high": (0.60, 0.05, 0.20)}


def apply(hilt_cam, blade_b, edge_hint_b, lift, pole):
    set_clav(lift)
    blade = V(blade_b).normalized()
    e = V(edge_hint_b) - blade * V(edge_hint_b).dot(blade)
    edge = e.normalized() if e.length > 0.2 else V((0, 0, 1))
    G_r = EYE + cam2b(hilt_cam); G_l = G_r - blade * 0.14
    for side, sock, G in (("r", "weapon_r", G_r), ("l", "grip_l", G_l)):
        relm = rest(f"hand_{side}").inverted() @ rest(sock)
        H.set_pose_matrix(arm, f"ik_hand_{side}", arm.matrix_world @ (H.frame_matrix(G, blade, edge) @ relm.inverted()))
    px, py, pz = POLES[pole]
    H.set_pose_matrix(arm, "pole_elbow_r", Matrix.Translation(G_r + V((-px, py, pz))))
    H.set_pose_matrix(arm, "pole_elbow_l", Matrix.Translation(G_l + V((px, py, pz))))
    bpy.context.view_layer.update()
    sword.matrix_world = H.bone_world(arm, "weapon_r") @ R @ Matrix.Translation((0, 0, 0.05))
    bpy.context.view_layer.update()


enemy_mask = view.raster(enemy)
assert 0.02 < enemy_mask.mean() < 0.6, "implausible opponent raster"


def elbow(side):
    a = H.bone_world(arm, f"upperarm_{side}").to_3x3().col[1]; b = H.bone_world(arm, f"forearm_{side}").to_3x3().col[1]
    return math.degrees(a.angle(b))


def metrics(parry=True):
    err_r = (H.bone_world(arm, "hand_r").translation - H.bone_world(arm, "ik_hand_r").translation).length * 1000
    err_l = (H.bone_world(arm, "hand_l").translation - H.bone_world(arm, "ik_hand_l").translation).length * 1000
    am = view.raster(arms_mesh)
    occ = float((am & enemy_mask).sum()) / enemy_mask.sum()
    cover = float(am.mean())
    a, b = np.array(bb.matrix_world.translation), np.array(bt.matrix_world.translation)
    pts = a[None] + (b - a)[None] * np.linspace(0, 1, 21)[:, None]
    blade_vis = float(view.in_frame(pts).mean())
    # parry geometry in camera space about the true eye
    B = b2cam(bb.matrix_world.translation - EYE); Tt = b2cam(bt.matrix_world.translation - EYE)
    geo = {"ok": False}
    if B.x > 0 > Tt.x:
        u = B.x / (B.x - Tt.x); P = B + (Tt - B) * u
        elev = math.degrees(math.asin(max(-1, min(1, (Tt - B).normalized().y))))
        geo = {"cross_y": round(P.y, 3), "cross_z": round(P.z, 3), "left_of_centre_m": round(-Tt.x, 3), "elev_deg": round(elev, 1)}
        geo["ok"] = P.y >= 0.04 and -0.75 <= P.z <= -0.15 and -Tt.x >= 0.25 and abs(elev) <= 30
    m = dict(enemy_occluded=round(occ, 3), arm_screen_cover=round(cover, 3), wrist_r_mm=round(err_r, 1), wrist_l_mm=round(err_l, 1),
             blade_visible=round(blade_vis, 2), elbow_r_deg=round(elbow("r"), 1), elbow_l_deg=round(elbow("l"), 1), parry_geometry=geo)
    pen = 0.08 * max(0, err_r - 3) + 0.08 * max(0, err_l - 3) + 0.8 * max(0.0, 0.40 - blade_vis)
    if parry and not geo["ok"]:
        pen += 5.0
    m["cost"] = round(occ + 0.25 * cover + pen, 4)
    return m


def blade_dir(phi, e):  # camera space: tip to the left (-x), phi swings it forward, e raises it
    p, q = math.radians(phi), math.radians(e)
    return cam2b(V((-math.cos(p) * math.cos(q), math.sin(q), -math.sin(p) * math.cos(q))))


EDGE_UP = cam2b(V((0, 1, 0)))
results = []
best = None
coarse = itertools.product((0.06, 0.14, 0.22, 0.30), (-0.02, 0.06, 0.14), (-0.32, -0.40), (0, 20, 40), (0, 15), (0, 15), POLES)
for x, y, z, phi, e, lift, pole in coarse:
    apply((x, y, z), blade_dir(phi, e), EDGE_UP, lift, pole)
    m = metrics()
    cand = dict(hilt_cam_m=[x, y, z], phi=phi, elev=e, lift=lift, pole=pole, metrics=m)
    if best is None or m["cost"] < best["metrics"]["cost"]:
        best = cand
print("WOS_COARSE", json.dumps(best))
b0 = best
for dx, dy, dz, dp, de in itertools.product((-0.03, 0, 0.03), (-0.03, 0, 0.03), (-0.03, 0, 0.03), (-10, 0, 10), (-7, 0, 7)):
    hc = [b0["hilt_cam_m"][0] + dx, b0["hilt_cam_m"][1] + dy, b0["hilt_cam_m"][2] + dz]
    apply(hc, blade_dir(b0["phi"] + dp, b0["elev"] + de), EDGE_UP, b0["lift"], b0["pole"])
    m = metrics()
    if m["cost"] < best["metrics"]["cost"]:
        best = dict(hilt_cam_m=[round(v, 3) for v in hc], phi=b0["phi"] + dp, elev=b0["elev"] + de, lift=b0["lift"], pole=b0["pole"], metrics=m)
apply(best["hilt_cam_m"], blade_dir(best["phi"], best["elev"]), EDGE_UP, best["lift"], best["pole"])
apply(best["hilt_cam_m"], blade_dir(best["phi"], best["elev"]), EDGE_UP, best["lift"], best["pole"])
best["metrics"] = metrics()
best["metrics"]["left_hand_on_grip_mm"] = round((secm.matrix_world.translation - H.bone_world(arm, "grip_l").translation).length * 1000, 1)
print("WOS_BEST", json.dumps(best))

out = f"previews/v0.4.0/william_fp_arms_{VER}"
renders = [C.render_still(scene, pov, f"{out}_pov_head_5.png", (720, 1280))]
insp = C.look_cam([c for c in bpy.data.collections if c.name.startswith("preview_only")][0], "cam_parry_inspect",
                  (-0.95, -1.05, 1.75), (-0.05, -0.30, 1.70), lens=45)
renders.append(C.render_still(scene, insp, f"{out}_inspect_head_5.png", (1000, 1000)))

# v004 head guard re-measured with the same metric (baseline) and lower-right regression check
def replay(g):
    d = G4["guards"][g]
    apply(d["hilt_cam_m"], cam2b(bladeAxis(d["blade_euler_rig_poses"])).normalized(), cam2b(V((0, 0, -1))) * -1 if False else V((0, -1, 0)),
          d["clavicle_lift_deg"], d["elbow_pole"])
    apply(d["hilt_cam_m"], cam2b(bladeAxis(d["blade_euler_rig_poses"])).normalized(), V((0, -1, 0)), d["clavicle_lift_deg"], d["elbow_pole"])
    return metrics(parry=(g == "head_5"))
baseline = {"head_5_v004": replay("head_5"), "lowerRight_2_v004": replay("lowerRight_2")}

# side-by-side comparison image (v004 | v005), composed from the two actual renders
def load(p):
    im = bpy.data.images.load(os.path.join(C.REPO, p))
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    return a
A = load("previews/v0.4.0/william_fp_arms_v004_pov_head_5.png"); Bm = load(f"{out}_pov_head_5.png")
gap = np.ones((A.shape[0], 16, 4), np.float32) * np.array([0.1, 0.1, 0.1, 1], np.float32)
comp = np.concatenate([A, gap, Bm], 1)
img = bpy.data.images.new("cmp", comp.shape[1], comp.shape[0], alpha=True)
img.pixels.foreach_set(comp.ravel())
renders.append(C.save_image(img, f"{out}_compare_head_5_v004_vs_{VER}.png"))

guards = json.loads(json.dumps(G4["guards"]))
guards["head_5"] = {"blade_dir_cam": [round(v, 4) for v in b2cam(blade_dir(best["phi"], best["elev"]))],
                    "blade_euler_rig_poses": None, "edge_hint_cam": [0, 1, 0], "hilt_cam_m": best["hilt_cam_m"],
                    "clavicle_lift_deg": best["lift"], "elbow_pole": best["pole"], "elbow_pole_offset": POLES[best["pole"]],
                    "metrics": best["metrics"], "note": "v005 redesign: hanging/roof parry, hilt high right, blade across the brow"}
C.write_json(f"assets/v0.4.0/first-person/william_fp_guards_{VER}.json",
             {"source": "william_fp_arms_v004 (mesh and rig unchanged)", "derived_from": "william_fp_guards_v004.json",
              "camera_space": G4["camera_space"], "viewmodel_camera": G4["viewmodel_camera"], "guards": guards,
              "baseline_same_metric": baseline})
print("WOS_PARRY", json.dumps({"best": best, "baseline": baseline, "renders": renders}))
