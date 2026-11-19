"""Will of Steel v0.4.0: William's first-person arms. Original model, rig and materials.

Run: blender -b --factory-startup --python tools/blender/build_william_arms.py -- v001 [enemy.glb]
Outputs (new, versioned): GLB (rest pose, skinned), .blend, textures, POV renders for READY plus the five guards, report.

Rig: same arm naming as the humanoid standard (clavicle/upperarm/twist/forearm/twist/hand) plus fully articulated
fingers (index/middle/ring/pinky _01.._03, thumb_01.._03), IK/pole controls, weapon_r / grip_l sockets, and a
non-deforming `fp_eye` reference bone that the game camera aligns to. This rig is first-person only; the
third-person knight rigs contain no camera.
Space: Blender Z-up, William faces -Y, left = +X. Game camera space maps (x, y, z)_cam -> (-x, z, y)_blender
about fp_eye.
"""
import bpy, math, os, sys, json
from mathutils import Vector as V, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H
import wos_materials as M

ARGS = C.args()
VER = ARGS[0] if ARGS else "v001"
ENEMY = ARGS[1] if len(ARGS) > 1 else None
NAME = f"william_fp_arms_{VER}"
TEX = f"assets/v0.4.0/textures/{NAME}"
SWORD_GLB = "assets/v0.4.0/weapons/longsword_xva_v006.glb"
FOV_Y = 61.0                                   # main.js PerspectiveCamera(61, ...)
pi = math.pi


def nrm(v): return V(v).normalized()
def along(a, b, s): return V(a) + (V(b) - V(a)) * s


# ------------------------------------------------------------------ joints (left side; right mirrored)
J = {}
J["eye"] = V((0, -0.075, 1.675)); J["spine03"] = V((0, 0.012, 1.36)); J["neck"] = V((0, 0.02, 1.47))
J["clav"] = V((0.025, 0.0, 1.445)); J["shoulder"] = V((0.185, 0.025, 1.43))
U_UA = nrm((0.62, 0.02, -0.78)); J["elbow"] = J["shoulder"] + U_UA * 0.295
U_FA = nrm((0.60, -0.12, -0.79)); J["wrist"] = J["elbow"] + U_FA * 0.255
D = U_FA
N = nrm(V((-1, 0, 0)) - D * V((-1, 0, 0)).dot(D))            # palm normal (faces the thigh in rest)
W = nrm(V((0, -1, 0)) - D * V((0, -1, 0)).dot(D) - N * V((0, -1, 0)).dot(N))   # across the hand, toward the thumb
J["knuckle"] = J["wrist"] + D * 0.094
J["grip"] = J["wrist"] + D * 0.070 + N * 0.024
FINGERS = {  # name: (a along hand, b across, segment lengths, base radius)
    "index": (0.092, 0.027, (0.040, 0.025, 0.020), 0.0095),
    "middle": (0.096, 0.008, (0.044, 0.028, 0.021), 0.0098),
    "ring": (0.092, -0.011, (0.041, 0.027, 0.020), 0.0092),
    "pinky": (0.083, -0.028, (0.032, 0.020, 0.018), 0.0082),
}
TH0 = J["wrist"] + D * 0.022 + W * 0.020 + N * 0.010
TH_DIR = nrm(D * 0.55 + W * 0.75 + N * 0.35)
TH_LEN = (0.045, 0.032, 0.026)
EDGE_REST = nrm(V((D.x, 0, D.z)))
FRONT = (0, -1, 0)


def finger_points(name):
    a, b, lens, _ = FINGERS[name]
    p = J["wrist"] + D * a + W * b - N * 0.004
    d = nrm(D + W * b * 0.8)
    pts = [p]
    for L in lens:
        pts.append(pts[-1] + d * L)
    return pts


def thumb_points():
    pts = [TH0]
    for L in TH_LEN:
        pts.append(pts[-1] + TH_DIR * L)
    return pts


def bone_defs():
    b = []
    add = lambda n, h, t, p=None, d=True, r=FRONT, c=False: b.append(dict(name=n, head=V(h), tail=V(t), parent=p, deform=d, roll_to=r, connect=c))
    add("root", (0, 0, 0), (0, 0, 0.15), None, False)
    add("spine_03", J["spine03"], J["neck"], "root")
    add("fp_eye", J["eye"], J["eye"] + V((0, -0.1, 0)), "spine_03", False, (0, 0, 1))
    left = []
    L = lambda n, h, t, p=None, d=True, r=FRONT, c=False: left.append(dict(name=n, head=V(h), tail=V(t), parent=p, deform=d, roll_to=r, connect=c))
    L("clavicle_l", J["clav"], J["shoulder"], "spine_03")
    L("upperarm_l", J["shoulder"], J["elbow"], "clavicle_l", c=True)
    L("upperarm_twist_l", J["shoulder"], along(J["shoulder"], J["elbow"], 0.5), "upperarm_l")
    L("forearm_l", J["elbow"], J["wrist"], "upperarm_l", c=True)
    L("forearm_twist_l", along(J["elbow"], J["wrist"], 0.5), J["wrist"], "forearm_l")
    L("hand_l", J["wrist"], J["knuckle"], "forearm_l", r=N, c=True)
    for f in FINGERS:
        pts = finger_points(f)
        for k in range(3):
            L(f"{f}_0{k + 1}_l", pts[k], pts[k + 1], "hand_l" if k == 0 else f"{f}_0{k}_l", r=N, c=k > 0)
    tp = thumb_points()
    for k in range(3):
        L(f"thumb_0{k + 1}_l", tp[k], tp[k + 1], "hand_l" if k == 0 else f"thumb_0{k}_l", r=N, c=k > 0)
    L("grip_l", J["grip"], J["grip"] + V((0, -0.08, 0)), "hand_l", False, EDGE_REST)
    L("ik_hand_l", J["wrist"], J["knuckle"], "root", False, N)
    L("pole_elbow_l", J["elbow"] + V((0.10, 0.35, 0)), J["elbow"] + V((0.10, 0.40, 0)), "root", False)
    mx = lambda p: V((-p[0], p[1], p[2]))
    for d in left:
        b.append(d)
        r = dict(d)
        r["name"] = "weapon_r" if d["name"] == "grip_l" else d["name"][:-2] + "_r"
        r["head"], r["tail"] = mx(d["head"]), mx(d["tail"])
        r["roll_to"] = mx(d["roll_to"]) if d["roll_to"] is not None else None
        if d["parent"] and d["parent"].endswith("_l"):
            r["parent"] = d["parent"][:-2] + "_r"
        b.append(r)
    return b


BONES = bone_defs()
DEFORM = [b["name"] for b in BONES if b["deform"]]
SWAP = {n: (n[:-2] + ("_r" if n.endswith("_l") else "_l")) for n in DEFORM if n.endswith(("_l", "_r"))}
SEGS = {b["name"]: (b["head"], b["tail"]) for b in BONES if b["deform"]}
TWIST = {"upperarm_l": ("upperarm_twist_l", 0.5, 0.0), "forearm_l": ("forearm_twist_l", 0.35, 0.9)}
ARM_W = H.auto_weights({k: v for k, v in SEGS.items() if not k.startswith(("index", "middle", "ring", "pinky", "thumb"))
                        and not k.endswith("_r")}, twist=TWIST)
HAND_SEGS = {k: v for k, v in SEGS.items() if k.endswith("_l") and (k.startswith(("index", "middle", "ring", "pinky", "thumb", "hand")) or k == "forearm_twist_l")}
HAND_W = H.auto_weights(HAND_SEGS, falloff=6.0, keep=2)


def build_mesh(mats):
    s = H.Slot("william_arms", DEFORM, [mats["gambeson"], mats["steel"], mats["leather"]])
    sh, el, wr = J["shoulder"], J["elbow"], J["wrist"]
    parts = []
    # quilted gambeson sleeve (padded, slightly baggy at the upper arm)
    c = [along(J["clav"], sh, 0.4), sh, along(sh, el, 0.35), along(sh, el, 0.75), el, along(el, wr, 0.35), along(el, wr, 0.7), wr - D * 0.035]
    r = [0.060, 0.068, 0.066, 0.060, 0.055, 0.050, 0.044, 0.039]
    parts.append(s.tube(c, r, FRONT, 0, ARM_W, n=20, tile=0.22, cap0=False, cap1=True))
    # couter (elbow cop) with a small rolled edge
    cc = [el - U_UA * 0.055, el - U_UA * 0.02, el + U_FA * 0.015, el + U_FA * 0.05]
    cr = [(0.058, 0.058), (0.066, 0.066), (0.066, 0.066), (0.055, 0.055)]
    prof = [H.ellipse(rx, ry, 18, -pi / 2 - 1.9, -pi / 2 + 1.9, closed=False) for rx, ry in cr]
    parts.append(s.shell(cc, prof, FRONT, 1, {"upperarm_l": 0.5, "forearm_l": 0.5}, 0.0026, tile=0.35))
    # vambrace: two-plate closed tube with medial ridge and rolled ends, two straps with buckles
    vc = [el + D * 0.050, el + D * 0.10, el + D * 0.16, el + D * 0.215, el + D * 0.238]
    vr = [(0.052, 0.054), (0.051, 0.052), (0.046, 0.046), (0.041, 0.040), (0.040, 0.039)]
    prof = [H.ellipse(rx, ry, 24, ridge=0.003) for rx, ry in vr]
    w_v = {"forearm_twist_l": 0.6, "forearm_l": 0.4}
    parts.append(s.shell(vc, prof, FRONT, 1, w_v, 0.0028, closed=True, tile=0.35))
    for u in (0.048, 0.236):
        rr = 0.0545 if u < 0.1 else 0.0415
        parts.append(s.shell([el + D * u, el + D * (u + 0.008)], [H.ellipse(rr + 0.002, rr + 0.003, 24)] * 2, FRONT, 1, w_v, 0.004,
                             closed=True, tile=0.2))
    fr = H.frames([el + D * 0.05, el + D * 0.2], FRONT)[0]
    out_dir = fr[1]                                     # outer side of the forearm
    for u in (0.085, 0.19):
        rr = 0.053 - (u - 0.085) * 0.10
        parts.append(s.shell([el + D * u, el + D * (u + 0.017)], [H.ellipse(rr + 0.005, rr + 0.006, 24)] * 2, FRONT, 2, w_v, 0.002,
                             closed=True, tile=0.15))
        bpos = el + D * (u + 0.0085) + out_dir * (rr + 0.009)
        parts.append(s.shell([bpos - D * 0.011, bpos + D * 0.011], [H.ellipse(0.009, 0.0035, 8)] * 2, lambda i, t: out_dir, 1,
                             w_v, 0.002, closed=True, cap0=True, cap1=True))
    # leather glove: flared cuff, palm, fingers, thumb
    gc = [wr - D * 0.055, wr - D * 0.015, wr + D * 0.012]
    parts.append(s.shell(gc, [H.ellipse(0.054, 0.052, 20), H.ellipse(0.043, 0.038, 20), H.ellipse(0.040, 0.030, 20)],
                         lambda i, t: -N, 2, HAND_W, 0.0025, closed=True, tile=0.2))
    hc = [wr + D * 0.0, wr + D * 0.03, wr + D * 0.065, J["knuckle"] - D * 0.002]
    hr = [(0.034, 0.022), (0.041, 0.019), (0.044, 0.018), (0.043, 0.016)]
    parts.append(s.tube(hc, hr, lambda i, t: -N, 2, HAND_W, n=16, tile=0.15))
    for f, (a, b, lens, r0) in FINGERS.items():
        pts = finger_points(f)
        c = [pts[0] - D * 0.006, pts[0] + (pts[1] - pts[0]) * 0.5, pts[1], pts[1] + (pts[2] - pts[1]) * 0.5, pts[2], pts[2] + (pts[3] - pts[2]) * 0.6, pts[3]]
        rr = [r0, r0 * 0.93, r0 * 0.97, r0 * 0.86, r0 * 0.88, r0 * 0.78, r0 * 0.55]
        parts.append(s.tube(c, [(x, x * 0.88) for x in rr], lambda i, t: -N, 2, HAND_W, n=8, tile=0.1))
    tp = thumb_points()
    c = [tp[0], tp[1], along(tp[1], tp[2], 0.5), tp[2], along(tp[2], tp[3], 0.6), tp[3]]
    parts.append(s.tube(c, [0.016, 0.0125, 0.0115, 0.0112, 0.0102, 0.006], lambda i, t: -N, 2, HAND_W, n=8, tile=0.1))
    for vs, fs in parts:
        s.mirror(vs, fs, SWAP)
    return s


def bladeAxis(p):  # rig-poses.js bladeAxis, camera space
    a, b, c = p
    return V((-math.cos(b) * math.sin(c), math.cos(a) * math.cos(c) - math.sin(a) * math.sin(b) * math.sin(c),
              math.sin(a) * math.cos(c) + math.cos(a) * math.sin(b) * math.sin(c)))


def cam2b(v): return V((-v[0], v[2], v[1]))


# guard name -> (blade Euler from rig-poses.js, hilt position in camera space [m]; reachable, centre kept clear)
GUARDS = {
    "ready":       ((-.62, 0, -.02), (0.10, -0.26, -0.40)),
    "head_5":      ((-.22, 0, 1.50), (0.14, -0.02, -0.38)),
    "upperLeft_4": ((-.34, 0, .12), (-0.14, -0.14, -0.40)),
    "upperRight_3": ((-.34, 0, -.12), (0.20, -0.14, -0.40)),
    "lowerLeft_1": ((-.36, 0, 2.80), (-0.10, -0.32, -0.38)),
    "lowerRight_2": ((-.36, 0, -2.80), (0.18, -0.32, -0.38)),
}
# Viewmodel camera (proposal, needs approval before game integration): set back behind the true eye and pitched
# down so chest-height hands are in frame in portrait, while the opponent stays fully visible.
VIEW_BACK, VIEW_UP, VIEW_PITCH = 0.20, 0.02, 12.0


def main():
    scene = C.empty_scene()
    mats = {"gambeson": M.make("william_gambeson", "cloth", TEX, seed=1460, tint=(0.40, 0.34, 0.26), lines=7),
            "steel": M.make("william_steel", "steel", TEX, seed=1461),
            "leather": M.make("william_leather", "leather", TEX, seed=1462, tint=(0.24, 0.14, 0.08))}
    root = bpy.data.objects.new(NAME, None); scene.collection.objects.link(root)
    root["wos_asset"] = NAME
    root["wos_convention"] = "first-person only; align game camera to bone fp_eye; weapon_r +Y blade, +Z true edge"
    arm = H.build_armature(f"{NAME}_rig", BONES); arm.parent = root
    slot = build_mesh(mats)
    ob = slot.finish(arm)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(65):
            e.smooth = False
    bm.to_mesh(ob.data); bm.free()
    for side in "lr":
        H.add_ik(arm, f"forearm_{side}", f"ik_hand_{side}", f"pole_elbow_{side}")
        H.copy_rot(arm, f"hand_{side}", f"ik_hand_{side}")
        H.hinge_limits(arm, f"forearm_{side}", 0, 150)
    bpy.context.view_layer.update()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    glb = C.export_glb(f"assets/v0.4.0/first-person/{NAME}.glb", export_animations=False, export_skins=True, export_image_format="AUTO")

    # ---------------- review: sword in both hands, every guard at the game's portrait FOV
    bpy.ops.import_scene.gltf(filepath=os.path.join(C.REPO, SWORD_GLB))
    sword = [o for o in bpy.data.objects if o.name.startswith("longsword_xva") and o.parent is None][0]
    secm = [o for o in bpy.data.objects if o.name.startswith("hand_secondary")][0]
    if ENEMY:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(C.REPO, ENEMY))
        new_roots = [o for o in set(bpy.data.objects) - before if o.parent is None]
        grp = bpy.data.objects.new("enemy_preview_root", None); scene.collection.objects.link(grp)
        for o in new_roots:
            mw = o.matrix_world.copy(); o.parent = grp; o.matrix_world = mw
        grp.matrix_world = Matrix.Translation((0, -2.3, 0)) @ Matrix.Rotation(pi, 4, "Z")   # face the player (+Y)
    for side in "lr":
        for f in FINGERS:
            for k, ang in enumerate((62, 78, 48)):
                b = arm.pose.bones[f"{f}_0{k + 1}_{side}"]; b.rotation_mode = "XYZ"; b.rotation_euler = (math.radians(ang), 0, 0)
        for k, ang in enumerate((18, 30, 28)):
            b = arm.pose.bones[f"thumb_0{k + 1}_{side}"]; b.rotation_mode = "XYZ"; b.rotation_euler = (math.radians(ang), 0, 0)
    rest = lambda b: arm.data.bones[b].matrix_local
    R = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()
    prev, eng = C.preview_stage(scene, target=(0, -0.6, 1.3), radius=1.4, floor=True)
    scene.cycles.samples = 48
    eye = J["eye"]
    cd = bpy.data.cameras.new("cam_pov"); cd.sensor_fit = "VERTICAL"; cd.angle_y = math.radians(FOV_Y); cd.clip_start = 0.05
    pov = bpy.data.objects.new("cam_pov", cd); prev.objects.link(pov)
    pov.rotation_euler = (math.radians(90 - VIEW_PITCH), 0, pi)              # look along -Y, pitched down
    pov.location = eye + V((0, VIEW_BACK, VIEW_UP))
    out = f"previews/v0.4.0/{NAME}"
    renders, checks = [], {}
    import numpy as np
    bpy.context.view_layer.update()

    # ---- screen-space raster (portrait 9:16) used to score how much of the opponent the arms hide
    GW, GH = 36, 64
    cu, cv = np.meshgrid((np.arange(GW) + 0.5) / GW, (np.arange(GH) + 0.5) / GH)
    CELLS = np.stack([cu.ravel(), cv.ravel()], -1)
    ty = math.tan(math.radians(FOV_Y) / 2); tx = ty * 720 / 1280

    def project(P):                        # world (N,3) -> (N,2) in [0,1], depth (N,)
        Mi = np.array(pov.matrix_world.inverted())
        Pv = P @ Mi[:3, :3].T + Mi[:3, 3]
        d = -Pv[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = 0.5 + 0.5 * (Pv[:, 0] / d) / tx
            v = 0.5 + 0.5 * (Pv[:, 1] / d) / ty
        return np.stack([u, v], -1), d

    def raster(objs):
        dg = bpy.context.evaluated_depsgraph_get()
        mask = np.zeros(GW * GH, bool)
        for o in objs:
            eo = o.evaluated_get(dg); me = eo.to_mesh()
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            Mw = np.array(eo.matrix_world); co = co @ Mw[:3, :3].T + Mw[:3, 3]
            me.calc_loop_triangles()
            tri = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
            eo.to_mesh_clear()
            uv, d = project(co); tri = tri.reshape(-1, 3)
            ok = (d[tri] > 0.05).all(1)
            T = uv[tri[ok]]
            lo, hi = T.min(1), T.max(1)
            T = T[(hi[:, 0] > 0) & (lo[:, 0] < 1) & (hi[:, 1] > 0) & (lo[:, 1] < 1)]
            e0 = T[:, 1] - T[:, 0]; e1 = T[:, 2] - T[:, 0]
            T = T[np.abs(e0[:, 0] * e1[:, 1] - e0[:, 1] * e1[:, 0]) > 1e-10]     # drop zero-area triangles
            for s in range(0, len(T), 1500):
                t = T[s:s + 1500]
                A = t[:, 0]; v0 = t[:, 1] - A; v1 = t[:, 2] - A
                d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
                den = d00 * d11 - d01 * d01
                v2 = CELLS[:, None, :] - A[None]
                d20 = (v2 * v0[None]).sum(2); d21 = (v2 * v1[None]).sum(2)
                b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den
                mask |= ((b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)).any(1)
        return mask

    enemy_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.parent and o.parent.type == "ARMATURE" and o.parent != arm]
    enemy_mask = raster(enemy_objs) if enemy_objs else np.zeros(GW * GH, bool)
    # sanity: the A-posed opponent at 2.3 m covers a modest central area, never the whole frame
    if not (0.02 < enemy_mask.mean() < 0.6):
        raise RuntimeError(f"enemy raster coverage {enemy_mask.mean():.3f} is implausible; scoring would be invalid")
    checks["enemy_screen_cover"] = round(float(enemy_mask.mean()), 3)
    bb = [o for o in bpy.data.objects if o.name.startswith("blade_base")][0]
    bt = [o for o in bpy.data.objects if o.name.startswith("blade_tip")][0]

    # ---- pose application
    clav_rest = {s: arm.data.bones[f"clavicle_{s}"].matrix_local.copy() for s in "lr"}

    def set_clav(lift):
        for s, sx in (("l", 1), ("r", -1)):
            h = clav_rest[s].translation
            Rw = (Matrix.Rotation(math.radians(lift), 4, V((0, -sx, 0))) @           # raise
                  Matrix.Rotation(math.radians(lift * 0.8), 4, V((0, 0, -sx))))       # protract (forward)
            H.set_pose_matrix(arm, f"clavicle_{s}", Matrix.Translation(h) @ Rw @ Matrix.Translation(-h) @ clav_rest[s])

    POLES = {"down": (0.45, 0.35, -0.35), "wide": (0.65, 0.15, -0.05)}

    def apply(p, hilt_cam, lift, pole):
        set_clav(lift)
        blade = cam2b(bladeAxis(p)).normalized()
        fwd = V((0, -1, 0)); edge = fwd - blade * fwd.dot(blade)
        edge = edge.normalized() if edge.length > 0.2 else V((0, 0, 1))
        G_r = eye + cam2b(hilt_cam); G_l = G_r - blade * 0.14
        for side, sock, G in (("r", "weapon_r", G_r), ("l", "grip_l", G_l)):
            rel = rest(f"hand_{side}").inverted() @ rest(sock)
            H.set_pose_matrix(arm, f"ik_hand_{side}", arm.matrix_world @ (H.frame_matrix(G, blade, edge) @ rel.inverted()))
        px, py, pz = POLES[pole]
        H.set_pose_matrix(arm, "pole_elbow_r", Matrix.Translation(G_r + V((-px, py, pz))))
        H.set_pose_matrix(arm, "pole_elbow_l", Matrix.Translation(G_l + V((px, py, pz))))
        bpy.context.view_layer.update()
        sword.matrix_world = H.bone_world(arm, "weapon_r") @ R @ Matrix.Translation((0, 0, 0.05))
        bpy.context.view_layer.update()

    def metrics():
        err_r = (H.bone_world(arm, "hand_r").translation - H.bone_world(arm, "ik_hand_r").translation).length * 1000
        err_l = (H.bone_world(arm, "hand_l").translation - H.bone_world(arm, "ik_hand_l").translation).length * 1000
        am = raster([ob])
        occ = float((am & enemy_mask).sum()) / max(1, enemy_mask.sum())
        cover = float(am.mean())
        a, b = np.array(bb.matrix_world.translation), np.array(bt.matrix_world.translation)
        pts = a[None] + (b - a)[None] * np.linspace(0, 1, 21)[:, None]
        uv, d = project(pts)
        inside = (d > 0.05) & (uv[:, 0] > 0) & (uv[:, 0] < 1) & (uv[:, 1] > 0) & (uv[:, 1] < 1)
        huv, hd = project(np.array(H.bone_world(arm, "weapon_r").translation)[None])
        hilt_in = bool(hd[0] > 0.05 and 0.02 < huv[0, 0] < 0.98 and 0.02 < huv[0, 1] < 0.98)
        blade_vis = float(inside.mean())
        cost = (occ + 0.25 * cover + 0.08 * max(0, err_r - 3) + 0.08 * max(0, err_l - 3)
                + (0 if hilt_in else 0.6) + 0.8 * max(0.0, 0.45 - blade_vis))
        return dict(cost=round(cost, 4), enemy_occluded=round(occ, 3), arm_screen_cover=round(cover, 3),
                    wrist_r_mm=round(err_r, 1), wrist_l_mm=round(err_l, 1), blade_visible=round(blade_vis, 2), hilt_in_frame=hilt_in)

    # calibrate IK pole angles once (ready guard)
    apply(GUARDS["ready"][0], GUARDS["ready"][1], 0, "down")
    for tip, pole in (("forearm_r", "pole_elbow_r"), ("forearm_l", "pole_elbow_l")):
        c = [k for k in arm.pose.bones[tip].constraints if k.type == "IK"][0]
        best = None
        for ang in range(-180, 180, 15):
            c.pole_angle = math.radians(ang); bpy.context.view_layer.update()
            d = (H.bone_world(arm, tip).translation - H.bone_world(arm, pole).translation).length
            if best is None or d < best[0]: best = (d, ang)
        c.pole_angle = math.radians(best[1])
        checks[f"pole_{tip}"] = best[1]

    # ---- readability-first search per guard (blade angle fixed = guard identity from rig-poses.js)
    chosen = {}
    for g, (p, hilt0) in GUARDS.items():
        best = None
        for dx in (-0.10, -0.05, 0.0, 0.05, 0.10):
            for dy in (-0.08, -0.04, 0.0, 0.04, 0.08):
                for dz in (-0.04, 0.0, 0.04):
                    hc = (hilt0[0] + dx, hilt0[1] + dy, hilt0[2] + dz)
                    for lift in (0, 12):
                        for pole in POLES:
                            apply(p, hc, lift, pole)
                            m = metrics()
                            if best is None or m["cost"] < best[0]["cost"]:
                                best = (m, hc, lift, pole)
        m, hc, lift, pole = best
        apply(p, hc, lift, pole)
        apply(p, hc, lift, pole)    # second pass lets IK settle from the chosen start
        m = metrics()
        m["left_hand_on_grip_mm"] = round((secm.matrix_world.translation - H.bone_world(arm, "grip_l").translation).length * 1000, 1)
        chosen[g] = {"blade_euler_rig_poses": list(p), "hilt_cam_m": [round(x, 3) for x in hc], "clavicle_lift_deg": lift,
                     "elbow_pole": pole, "elbow_pole_offset": POLES[pole], "metrics": m}
        checks[g] = m
        print("WOS_GUARD", g, json.dumps(chosen[g]))
        renders.append(C.render_still(scene, pov, f"{out}_pov_{g}.png", (720, 1280)))
    C.write_json(f"assets/v0.4.0/first-person/william_fp_guards_{VER}.json",
                 {"source": NAME, "camera_space": "three.js camera space relative to fp_eye; metres",
                  "viewmodel_camera": {"back_m": VIEW_BACK, "up_m": VIEW_UP, "pitch_down_deg": VIEW_PITCH, "fov_y_deg": FOV_Y},
                  "guards": chosen})
    # model inspection view (ready pose), outside the head
    bpy.ops.object.select_all(action="DESELECT")
    g = "ready"; p, hilt_cam = GUARDS[g]
    side_cam = C.look_cam(prev, "cam_inspect", (-0.85, -0.95, 1.55), (-0.05, -0.30, 1.30), lens=50)
    blade = cam2b(bladeAxis(p)).normalized()
    renders.append(C.render_still(scene, side_cam, f"{out}_inspect_last_pose.png", (1000, 1000)))
    blend = C.save_blend(f"source/blender/first-person/{NAME}.blend")
    report = {"asset": NAME, "blender": bpy.app.version_string, "engine": eng, "triangles": tris,
              "materials": [m.name for m in ob.data.materials], "bones": len(arm.data.bones), "deform_bones": len(DEFORM),
              "fov_y_deg": FOV_Y, "viewmodel_camera": {"back_m": VIEW_BACK, "up_m": VIEW_UP, "pitch_down_deg": VIEW_PITCH},
              "checks": checks, "enemy_preview": ENEMY,
              "normals_fixed": f"{slot.flipped}/{slot.faces_total}",
              "glb": os.path.relpath(glb, C.REPO), "glb_sha256": C.sha256(glb), "glb_bytes": os.path.getsize(glb),
              "blend": os.path.relpath(blend, C.REPO), "renders": [os.path.relpath(r, C.REPO) for r in renders]}
    C.write_json(f"assets/v0.4.0/first-person/{NAME}.report.json", report)
    print("WOS_REPORT", json.dumps(report))


main()
