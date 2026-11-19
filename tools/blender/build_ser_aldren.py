"""Will of Steel v0.4.0: Ser Aldren, the master knight (balanced). Original model, rig and materials.

Run: blender -b --factory-startup --python tools/blender/build_ser_aldren.py -- v001
Outputs (all new, versioned): GLB (rest pose, skinned), .blend, textures, review renders, JSON report.

Style: mid-15th-century composite harness (Italian-influenced: rounded breastplate, sallet with visor and bevor,
lamed pauldrons, couters and poleyns with side wings, closed greaves, lamed sabatons, mitten gauntlets) worn over a
padded arming doublet, with mail at the skirt and armpits. Restrained, hand-finished steel. Nothing is copied from
any existing game.
"""
import bpy, math, os, sys, json
from mathutils import Vector as V, Matrix, Euler
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H
import wos_materials as M

VER = (C.args() or ["v001"])[0]
NAME = f"ser_aldren_{VER}"
TEX = f"assets/v0.4.0/textures/{NAME}"
SWORD_GLB = "assets/v0.4.0/weapons/longsword_xva_v006.glb"
pi = math.pi

# ------------------------------------------------------------------ skeleton (left side; right is mirrored)
def nrm(v): return V(v).normalized()

J = {}
J["pelvis"] = V((0, 0.0, 0.97)); J["spine01"] = V((0, 0.005, 1.07)); J["spine02"] = V((0, 0.01, 1.21))
J["spine03"] = V((0, 0.012, 1.36)); J["neck"] = V((0, 0.02, 1.47)); J["head"] = V((0, 0.015, 1.575))
J["head_top"] = V((0, 0.0, 1.78))
J["clav"] = V((0.025, 0.0, 1.445)); J["shoulder"] = V((0.185, 0.025, 1.43))
U_UA = nrm((0.62, 0.02, -0.78)); J["elbow"] = J["shoulder"] + U_UA * 0.30
U_FA = nrm((0.60, -0.12, -0.79)); J["wrist"] = J["elbow"] + U_FA * 0.255
J["knuckle"] = J["wrist"] + U_FA * 0.095; J["finger_mid"] = J["knuckle"] + U_FA * 0.045
J["finger_tip"] = J["finger_mid"] + U_FA * 0.040
PALM_N = nrm(V((-1, 0, 0)) - U_FA * V((-1, 0, 0)).dot(U_FA))      # palm faces the thigh
THUMB_DIR = nrm(U_FA * 0.5 + V((0, -1, 0)) * 0.8 + PALM_N * 0.3)
J["thumb0"] = J["wrist"] + U_FA * 0.025 + V((0, -0.022, 0)) + PALM_N * 0.01
J["thumb1"] = J["thumb0"] + THUMB_DIR * 0.045; J["thumb2"] = J["thumb1"] + THUMB_DIR * 0.035
J["grip"] = J["wrist"] + U_FA * 0.072 + PALM_N * 0.022         # centre of the closed fist
J["hip"] = V((0.092, 0.0, 0.935)); J["knee"] = V((0.100, -0.012, 0.505))
J["ankle"] = V((0.104, 0.025, 0.085)); J["ball"] = V((0.108, -0.105, 0.022)); J["toe"] = V((0.110, -0.175, 0.018))

FRONT = (0, -1, 0)
EDGE_REST = nrm(V((U_FA.x, 0, U_FA.z)))                          # true edge in line with the knuckles


def bone_defs():
    b = []
    add = lambda n, h, t, p=None, d=True, r=FRONT, c=False: b.append(dict(name=n, head=h, tail=t, parent=p, deform=d, roll_to=r, connect=c))
    add("root", (0, 0, 0), (0, 0, 0.15), None, False, FRONT)
    add("pelvis", J["pelvis"], J["spine01"], "root")
    add("spine_01", J["spine01"], J["spine02"], "pelvis", c=True)
    add("spine_02", J["spine02"], J["spine03"], "spine_01", c=True)
    add("spine_03", J["spine03"], J["neck"], "spine_02", c=True)
    add("neck", J["neck"], J["head"], "spine_03", c=True)
    add("head", J["head"], J["head_top"], "neck", c=True)
    left = []
    L = lambda n, h, t, p=None, d=True, r=FRONT, c=False: left.append(dict(name=n, head=h, tail=t, parent=p, deform=d, roll_to=r, connect=c))
    L("clavicle_l", J["clav"], J["shoulder"], "spine_03")
    L("upperarm_l", J["shoulder"], J["elbow"], "clavicle_l", c=True)
    L("upperarm_twist_l", J["shoulder"], (J["shoulder"] + J["elbow"]) / 2, "upperarm_l")
    L("forearm_l", J["elbow"], J["wrist"], "upperarm_l", c=True)
    L("forearm_twist_l", (J["elbow"] + J["wrist"]) / 2, J["wrist"], "forearm_l")
    L("hand_l", J["wrist"], J["knuckle"], "forearm_l", r=PALM_N, c=True)
    L("fingers_01_l", J["knuckle"], J["finger_mid"], "hand_l", r=PALM_N, c=True)
    L("fingers_02_l", J["finger_mid"], J["finger_tip"], "fingers_01_l", r=PALM_N, c=True)
    L("thumb_01_l", J["thumb0"], J["thumb1"], "hand_l", r=PALM_N)
    L("thumb_02_l", J["thumb1"], J["thumb2"], "thumb_01_l", r=PALM_N, c=True)
    L("grip_l", J["grip"], J["grip"] + V((0, -0.08, 0)), "hand_l", False, EDGE_REST)   # socket: +Y blade, +Z true edge
    L("thigh_l", J["hip"], J["knee"], "pelvis")
    L("calf_l", J["knee"], J["ankle"], "thigh_l", c=True)
    L("foot_l", J["ankle"], J["ball"], "calf_l", r=(0, 0, 1), c=True)
    L("toe_l", J["ball"], J["toe"], "foot_l", r=(0, 0, 1), c=True)
    # controls (non-deforming, parented to root)
    L("ik_hand_l", J["wrist"], J["knuckle"], "root", False, PALM_N)
    L("pole_elbow_l", J["elbow"] + V((0.10, 0.35, 0)), J["elbow"] + V((0.10, 0.40, 0)), "root", False)
    L("ik_foot_l", J["ankle"], J["ball"], "root", False, (0, 0, 1))
    L("pole_knee_l", J["knee"] + V((0.03, -0.45, 0)), J["knee"] + V((0.03, -0.50, 0)), "root", False)
    for d in left:
        b.append(d)
        r = dict(d)
        r["name"] = d["name"][:-2] + "_r"
        if d["name"] == "grip_l":
            r["name"] = "weapon_r"
        mx = lambda p: V((-p[0], p[1], p[2]))
        r["head"], r["tail"] = mx(d["head"]), mx(d["tail"])
        r["roll_to"] = mx(d["roll_to"]) if d["roll_to"] is not None else None
        if d["parent"] and d["parent"].endswith("_l"):
            r["parent"] = d["parent"][:-2] + "_r"
        b.append(r)
    return b


BONES = bone_defs()
DEFORM = [b["name"] for b in BONES if b["deform"]]
SWAP = {}
for n in DEFORM:
    if n.endswith("_l"): SWAP[n] = n[:-2] + "_r"
    if n.endswith("_r"): SWAP[n] = n[:-2] + "_l"
SEGS = {b["name"]: (V(b["head"]), V(b["tail"])) for b in BONES if b["deform"]}
TWIST = {"upperarm_l": ("upperarm_twist_l", 0.5, 0.0), "forearm_l": ("forearm_twist_l", 0.35, 0.9),
         "upperarm_r": ("upperarm_twist_r", 0.5, 0.0), "forearm_r": ("forearm_twist_r", 0.35, 0.9)}
AUTO = H.auto_weights(SEGS, twist=TWIST)
AUTO_NOFINGER = H.auto_weights({k: v for k, v in SEGS.items() if not k.startswith(("fingers", "thumb"))}, twist=TWIST)


def along(a, b, s): return V(a) + (V(b) - V(a)) * s


# ------------------------------------------------------------------ body (padded doublet, hose, shoes, cap)
def build_body(mats):
    s = H.Slot("aldren_body", DEFORM, [mats["doublet"], mats["hose"], mats["leather"], mats["cap"], mats["mail"]])
    zs = [0.86, 0.92, 0.98, 1.05, 1.13, 1.21, 1.29, 1.36, 1.42, 1.47, 1.51]
    rr = [(0.15, 0.10), (0.165, 0.11), (0.165, 0.11), (0.15, 0.105), (0.15, 0.11), (0.165, 0.12), (0.175, 0.125),
          (0.175, 0.115), (0.150, 0.095), (0.095, 0.068), (0.058, 0.058)]   # slimmer under gorget/backplate
    s.tube([(0, 0.01, z) for z in zs], rr, FRONT, 0, AUTO_NOFINGER, n=20, tile=0.25)
    s.tube([(0, 0.02, 1.46), (0, 0.02, 1.53), (0, 0.018, 1.60)], [0.058, 0.055, 0.055], FRONT, 0, AUTO_NOFINGER, n=14, tile=0.25)
    hz = [1.555, 1.58, 1.62, 1.67, 1.71, 1.75, 1.78, 1.795]
    hr = [(0.05, 0.06), (0.07, 0.085), (0.078, 0.095), (0.08, 0.098), (0.079, 0.096), (0.07, 0.085), (0.05, 0.06), (0.02, 0.02)]
    s.tube([(0, 0.012, z) for z in hz], hr, FRONT, 3, {"head": 1.0}, n=16)
    # left arm sleeve + glove; leg hose + shoe (mirrored)
    arm_c = [along(J["clav"], J["shoulder"], 0.45), J["shoulder"], along(J["shoulder"], J["elbow"], 0.5), J["elbow"],
             along(J["elbow"], J["wrist"], 0.5), J["wrist"]]
    v1, f1 = s.tube(arm_c, [0.056, 0.060, 0.054, 0.046, 0.039, 0.032], FRONT, 0, AUTO_NOFINGER, n=14, tile=0.25, cap0=False)   # stays inside plates
    hand_c = [along(J["wrist"], J["knuckle"], -0.1), along(J["wrist"], J["knuckle"], 0.5), J["knuckle"], J["finger_mid"], J["finger_tip"]]
    v2, f2 = s.tube(hand_c, [(0.034, 0.028), (0.044, 0.020), (0.043, 0.017), (0.040, 0.015), (0.02, 0.01)],
                    lambda i, T: PALM_N, 2, AUTO, n=12, tile=0.2)
    v2b, f2b = s.tube([J["thumb0"], J["thumb1"], J["thumb2"]], [0.016, 0.013, 0.008], FRONT, 2, AUTO, n=8)
    leg_c = [V((0.075, 0.0, 1.0)), J["hip"], along(J["hip"], J["knee"], 0.5), J["knee"], along(J["knee"], J["ankle"], 0.4), J["ankle"]]
    v3, f3 = s.tube(leg_c, [0.085, 0.087, 0.072, 0.056, 0.058, 0.040], FRONT, 1, AUTO_NOFINGER, n=14, tile=0.25, cap0=False)
    foot_c = [J["ankle"] + V((0, 0.035, -0.02)), J["ankle"] + V((0, 0, -0.03)), J["ball"] + V((0, 0, 0.005)), J["toe"] + V((0, 0, 0.004))]
    v4, f4 = s.tube(foot_c, [(0.045, 0.05), (0.048, 0.045), (0.046, 0.025), (0.02, 0.012)], (0, 0, 1), 2, AUTO_NOFINGER, n=12)
    # mail sleeve at the armpit and mail skirt
    v5, f5 = s.tube([along(J["clav"], J["shoulder"], 0.6), J["shoulder"], along(J["shoulder"], J["elbow"], 0.42)],
                    [0.066, 0.071, 0.066], FRONT, 4, AUTO_NOFINGER, n=14, tile=0.12, cap0=False, cap1=False)
    for vs, fs in ((v1, f1), (v2, f2), (v2b, f2b), (v3, f3), (v4, f4), (v5, f5)):
        s.mirror(vs, fs, SWAP)
    s.tube([(0, 0.012, z) for z in (1.01, 0.95, 0.88, 0.80)], [(0.172, 0.125), (0.19, 0.145), (0.215, 0.17), (0.235, 0.19)],
           FRONT, 4, AUTO_NOFINGER, n=24, tile=0.12, cap0=False, cap1=False)
    return s


# ------------------------------------------------------------------ armour helpers
def rigid(*pairs):
    d = dict(zip(pairs[::2], pairs[1::2]))
    return d


def arc_profiles(radii, a0s, a1s, n, ridge=0.0, offs=None):
    out = []
    for i, (rx, ry) in enumerate(radii):
        a0 = a0s[i] if isinstance(a0s, list) else a0s
        a1 = a1s[i] if isinstance(a1s, list) else a1s
        p = H.ellipse(rx, ry, n, a0, a1, closed=False, ridge=ridge)
        if offs:
            ox, oy = offs[i]
            p = [(x + ox, y + oy) for x, y in p]
        out.append(p)
    return out


def ring_profiles(radii, n):
    return [H.ellipse(rx, ry, n) for rx, ry in radii]


def mirror_part(slot, fn):
    vs, fs = fn()
    slot.mirror(vs, fs, SWAP)


# ------------------------------------------------------------------ torso harness
def build_torso(mats):
    s = H.Slot("aldren_torso", DEFORM, [mats["steel"], mats["leather"]])
    T = 0.0028
    zs = [1.02, 1.08, 1.15, 1.22, 1.29, 1.35, 1.40, 1.44]
    br = [(0.175, 0.135), (0.170, 0.142), (0.178, 0.152), (0.190, 0.160), (0.198, 0.163), (0.198, 0.153), (0.188, 0.138), (0.160, 0.118)]
    cut = [0, 0, 0, 0, 0.10, 0.38, 0.62, 0.80]                       # armholes and neck opening
    a0 = [-0.12 + c for c in cut]; a1 = [pi + 0.12 - c for c in cut]
    s.shell([(0, 0.0, z) for z in zs], arc_profiles(br, a0, a1, 28, ridge=0.007), FRONT, 0, rigid("spine_02", 1.0), T, tile=0.6)
    bk = [(0.175, 0.125), (0.170, 0.128), (0.176, 0.135), (0.188, 0.142), (0.196, 0.145), (0.196, 0.140), (0.186, 0.130), (0.16, 0.112)]
    s.shell([(0, 0.018, z) for z in zs], arc_profiles(bk, [pi - 0.1 + c * 0.6 for c in cut], [2 * pi + 0.1 - c * 0.6 for c in cut], 28),
            FRONT, 0, rigid("spine_02", 1.0), T, tile=0.6)
    # fauld (front) and culet (back): overlapping lames, rigid to spine/pelvis
    lames = [((1.055, 1.0), ("spine_01", 1.0)), ((1.01, 0.955), ("spine_01", 0.5, "pelvis", 0.5)), ((0.965, 0.91), ("pelvis", 1.0))]
    for k, ((zt, zb), w) in enumerate(lames):
        g = 0.012 * k
        rad = [(0.178 + g, 0.140 + g), (0.186 + g, 0.150 + g)]
        s.shell([(0, 0.0, zt), (0, 0.0, zb)], arc_profiles(rad, -0.05, pi + 0.05, 26), FRONT, 0, rigid(*w), T, tile=0.6)
        s.shell([(0, 0.018, zt), (0, 0.018, zb)], arc_profiles([(r[0], r[1] - 0.012) for r in rad], pi - 0.05, 2 * pi + 0.05, 26),
                FRONT, 0, rigid(*w), T, tile=0.6)
    # tassets (left, mirrored): hang from the lowest lame over the front of the thigh
    def tasset():
        c = [V((0.105, -0.005, 0.925)), V((0.11, -0.015, 0.84)), V((0.115, -0.025, 0.76))]
        prof = arc_profiles([(0.095, 0.150), (0.10, 0.152), (0.104, 0.150)], 0.55, 2.55, 14)
        prof = [[(x, y - 0.035) for x, y in p] for p in prof]
        return s.shell(c, prof, FRONT, 0, rigid("pelvis", 0.6, "thigh_l", 0.4), T, tile=0.5)
    mirror_part(s, tasset)
    # gorget: two lames
    s.shell([(0, 0.02, 1.425), (0, 0.02, 1.455), (0, 0.02, 1.48)], ring_profiles([(0.165, 0.135), (0.12, 0.10), (0.085, 0.08)], 28),
            FRONT, 0, rigid("spine_03", 1.0), T, closed=True, tile=0.5)
    s.shell([(0, 0.02, 1.47), (0, 0.02, 1.50), (0, 0.02, 1.535)], ring_profiles([(0.088, 0.082), (0.074, 0.072), (0.072, 0.070)], 24),
            FRONT, 0, rigid("neck", 1.0), T, closed=True, tile=0.5)
    # sword belt with buckle (leather), slung low on the hips
    belt_c = [(0, 0.01, 0.925), (0, 0.01, 0.955)]
    s.shell(belt_c, ring_profiles([(0.230, 0.194), (0.227, 0.191)], 32), FRONT, 1, rigid("pelvis", 1.0), 0.004, closed=True, tile=0.3)
    s.shell([(0, -0.201, 0.928), (0, -0.201, 0.952)], ring_profiles([(0.022, 0.006), (0.022, 0.006)], 8), (0, 0, 1), 0,
            rigid("pelvis", 1.0), 0.002, closed=True, cap0=True, cap1=True)
    return s


# ------------------------------------------------------------------ helmet: sallet, visor, bevor
def build_head(mats):
    s = H.Slot("aldren_helmet", DEFORM, [mats["steel"], mats["cap"]])
    T = 0.0025
    sk_z = [1.705, 1.74, 1.77, 1.80, 1.82, 1.835, 1.843]
    sk_r = [(0.113, 0.131), (0.114, 0.132), (0.108, 0.125), (0.093, 0.108), (0.070, 0.082), (0.042, 0.048), (0.010, 0.011)]
    d = 0.004
    s.shell([(0, 0.012, z) for z in sk_z], arc_profiles(sk_r, -pi / 2 + d, 3 * pi / 2 - d, 36, ridge=0.004), FRONT, 0,
            rigid("head", 1.0), T, tile=0.4)
    # tail sweeping back over the nape
    tz = [(0.016, 1.715), (0.03, 1.68), (0.055, 1.645), (0.085, 1.615)]
    tr = [(0.113, 0.131), (0.118, 0.136), (0.126, 0.144), (0.136, 0.152)]
    s.shell([(0, y, z) for y, z in tz], arc_profiles(tr, 3 * pi / 2 - 1.35, 3 * pi / 2 + 1.35, 20), FRONT, 0,
            rigid("head", 1.0), T, tile=0.4)
    # visor (below the eye slit at ~1.70) and bevor (chin/throat, rigid to the upper chest)
    # visor wraps to the cheeks (no exposed face at the sides); bevor overlaps it from below
    vz = [1.694, 1.67, 1.645, 1.615, 1.595]
    vr = [(0.118, 0.141), (0.120, 0.143), (0.118, 0.141), (0.113, 0.136), (0.109, 0.131)]
    s.shell([(0, 0.010, z) for z in vz], arc_profiles(vr, pi / 2 - 1.80, pi / 2 + 1.80, 28, ridge=0.006), FRONT, 0,
            rigid("head", 1.0), T, tile=0.4)
    bz = [(0.002, 1.640), (-0.002, 1.60), (-0.008, 1.55), (-0.018, 1.50), (-0.024, 1.47)]
    brr = [(0.122, 0.146), (0.112, 0.136), (0.102, 0.124), (0.125, 0.137), (0.150, 0.150)]
    s.shell([(0, y, z) for y, z in bz], arc_profiles(brr, pi / 2 - 1.85, pi / 2 + 1.85, 28, ridge=0.005), FRONT, 0,
            rigid("neck", 0.5, "spine_03", 0.5), T, tile=0.4)
    # padded liner visible through the eye slit
    s.tube([(0, 0.012, 1.69), (0, 0.012, 1.715)], [(0.108, 0.125), (0.109, 0.126)], FRONT, 1, rigid("head", 1.0), n=24, cap0=False, cap1=False)
    return s


# ------------------------------------------------------------------ arms (left; mirrored)
def build_arms(mats):
    s = H.Slot("aldren_arms", DEFORM, [mats["steel"], mats["leather"]])
    T = 0.0026
    sh, el, wr = J["shoulder"], J["elbow"], J["wrist"]

    def pauldron():
        vs, fs = [], []
        c = [sh - U_UA * 0.07 + V((0, 0, 0.012)), sh - U_UA * 0.02 + V((0, 0, 0.012)), sh + U_UA * 0.035, sh + U_UA * 0.085]
        r = [(0.036, 0.048), (0.076, 0.082), (0.084, 0.089), (0.080, 0.085)]
        a, f = s.shell(c, arc_profiles(r, -1.95, 1.95, 22, offs=[(0.012, 0), (0.012, 0), (0.008, 0), (0.004, 0)]), FRONT, 0,
                       rigid("clavicle_l", 0.55, "upperarm_l", 0.45), T, tile=0.4)
        vs += a; fs += f
        for k in range(3):
            u0 = 0.075 + k * 0.024
            rr = 0.079 - k * 0.005
            a, f = s.shell([sh + U_UA * u0, sh + U_UA * (u0 + 0.03)], arc_profiles([(rr, rr + 0.004), (rr - 0.002, rr + 0.002)], -1.7, 1.7, 18),
                           FRONT, 0, rigid("upperarm_l", 1.0) if k else rigid("clavicle_l", 0.3, "upperarm_l", 0.7), T, tile=0.4)
            vs += a; fs += f
        return vs, fs

    def rerebrace():
        c = [sh + U_UA * 0.14, sh + U_UA * 0.20, sh + U_UA * 0.255]
        a, f = s.shell(c, ring_profiles([(0.066, 0.064), (0.062, 0.060), (0.058, 0.057)], 20), FRONT, 0, rigid("upperarm_l", 1.0), T,
                       closed=True, tile=0.4)
        b, g = s.shell([sh + U_UA * 0.18, sh + U_UA * 0.198], ring_profiles([(0.0690, 0.0670), (0.0680, 0.0660)], 20), FRONT, 1,
                       rigid("upperarm_l", 1.0), 0.002, closed=True, tile=0.2)
        return a + b, f + g

    def couter():
        c = [el - U_UA * 0.06, el - U_UA * 0.025, el + U_FA * 0.012, el + U_FA * 0.05]
        r = [(0.056, 0.056), (0.066, 0.066), (0.067, 0.067), (0.054, 0.054)]
        a, f = s.shell(c, arc_profiles(r, -pi / 2 - 2.0, -pi / 2 + 2.0, 20), FRONT, 0, rigid("upperarm_l", 0.5, "forearm_l", 0.5), T, tile=0.4)
        # fan wing on the outer side
        X = H.frames([el - U_UA * 0.02, el + U_FA * 0.02], FRONT)[0][1]
        wc = [el + X * 0.058, el + X * 0.068]
        b, g = s.tube(wc, [(0.050, 0.042), (0.046, 0.038)], lambda i, t: V(FRONT), 0, rigid("upperarm_l", 0.5, "forearm_l", 0.5), n=18)
        return a + b, f + g

    def vambrace():
        c = [el + U_FA * 0.045, el + U_FA * 0.12, el + U_FA * 0.20, el + U_FA * 0.235]
        a, f = s.shell(c, ring_profiles([(0.050, 0.052), (0.047, 0.048), (0.040, 0.039), (0.037, 0.036)], 20), FRONT, 0,
                       rigid("forearm_twist_l", 0.6, "forearm_l", 0.4), T, closed=True, tile=0.4)
        vs, fs = a, f
        for u in (0.08, 0.18):
            rad = 0.0505 - (u - 0.08) * 0.09
            b, g = s.shell([el + U_FA * u, el + U_FA * (u + 0.016)], ring_profiles([(rad + 0.005, rad + 0.006)] * 2, 20), FRONT, 1,
                           rigid("forearm_twist_l", 0.6, "forearm_l", 0.4), 0.002, closed=True, tile=0.2)
            vs += b; fs += g
        return vs, fs

    def gauntlet():
        back = lambda i, t: -PALM_N
        cuff = [wr - U_FA * 0.065, wr - U_FA * 0.02, wr + U_FA * 0.02]
        a, f = s.shell(cuff, ring_profiles([(0.052, 0.050), (0.045, 0.042), (0.044, 0.033)], 20), back, 0, rigid("hand_l", 1.0), T,
                       closed=True, tile=0.3)
        vs, fs = a, f
        hp = [wr + U_FA * 0.015, wr + U_FA * 0.055, J["knuckle"] + U_FA * 0.005]
        b, g = s.shell(hp, arc_profiles([(0.046, 0.030), (0.048, 0.028), (0.047, 0.026)], 0.25, pi - 0.25, 14), back, 0,
                       rigid("hand_l", 1.0), T, tile=0.3)
        vs += b; fs += g
        for k in range(4):                                       # mitten finger lames
            u0 = k * 0.021
            bone = "fingers_01_l" if k < 2 else "fingers_02_l"
            base = J["knuckle"] + U_FA * (u0 - 0.004)
            b, g = s.shell([base, base + U_FA * 0.025], arc_profiles([(0.046 - k * 0.002, 0.024), (0.045 - k * 0.002, 0.022)], 0.2, pi - 0.2, 14),
                           back, 0, rigid(bone, 1.0), T, tile=0.3)
            vs += b; fs += g
        b, g = s.shell([J["thumb0"] + THUMB_DIR * 0.01, J["thumb1"], J["thumb2"]], arc_profiles([(0.019, 0.017), (0.017, 0.016), (0.013, 0.012)], -0.3, pi + 0.3, 10),
                       back, 0, lambda p: {"thumb_01_l": 0.6, "thumb_02_l": 0.4}, T, tile=0.3)
        return vs + b, fs + g

    for fn in (pauldron, rerebrace, couter, vambrace, gauntlet):
        mirror_part(s, fn)
    return s


# ------------------------------------------------------------------ legs (left; mirrored)
def build_legs(mats):
    s = H.Slot("aldren_legs", DEFORM, [mats["steel"], mats["leather"]])
    T = 0.0028
    hp, kn, an = J["hip"], J["knee"], J["ankle"]
    UT = (kn - hp).normalized(); UC = (an - kn).normalized()

    def cuisse():
        c = [hp + UT * 0.05, hp + UT * 0.16, hp + UT * 0.28, kn - UT * 0.06]
        r = [(0.096, 0.096), (0.090, 0.092), (0.080, 0.082), (0.068, 0.070)]
        a, f = s.shell(c, arc_profiles(r, -0.9, pi - 0.35, 22, ridge=0.004), FRONT, 0, rigid("thigh_l", 1.0), T, tile=0.4)
        vs, fs = a, f
        for u in (0.14, 0.27):
            rad = 0.092 - (u - 0.14) * 0.09
            b, g = s.shell([hp + UT * u, hp + UT * (u + 0.018)], ring_profiles([(rad + 0.007, rad + 0.009)] * 2, 22), FRONT, 1,
                           rigid("thigh_l", 1.0), 0.002, closed=True, tile=0.2)
            vs += b; fs += g
        return vs, fs

    def poleyn():
        c = [kn - UT * 0.065, kn - UT * 0.02, kn + UC * 0.025, kn + UC * 0.065]
        r = [(0.068, 0.070), (0.074, 0.080), (0.073, 0.078), (0.062, 0.064)]
        a, f = s.shell(c, arc_profiles(r, pi / 2 - 1.75, pi / 2 + 1.75, 20, ridge=0.006), FRONT, 0, rigid("thigh_l", 0.5, "calf_l", 0.5), T, tile=0.4)
        wc = [kn + V((0.068, -0.01, 0)), kn + V((0.078, -0.01, 0))]
        b, g = s.tube(wc, [(0.045, 0.050), (0.040, 0.045)], lambda i, t: V((0, 0, 1)), 0, rigid("thigh_l", 0.5, "calf_l", 0.5), n=18)
        return a + b, f + g

    def greave():
        c = [kn + UC * 0.06, kn + UC * 0.13, kn + UC * 0.22, kn + UC * 0.32, an - UC * 0.02]
        r = [(0.058, 0.060), (0.063, 0.068), (0.060, 0.064), (0.047, 0.050), (0.044, 0.048)]
        a, f = s.shell(c, ring_profiles(r, 22), FRONT, 0, rigid("calf_l", 1.0), T, closed=True, tile=0.4)
        vs, fs = a, f
        for u in (0.10, 0.30):
            k = 0.0645 if u < 0.2 else 0.050
            b, g = s.shell([kn + UC * u, kn + UC * (u + 0.016)], ring_profiles([(k + 0.005, k + 0.007)] * 2, 22), FRONT, 1,
                           rigid("calf_l", 1.0), 0.002, closed=True, tile=0.2)
            vs += b; fs += g
        return vs, fs

    def sabaton():
        up = (0, 0, 1)
        vs, fs = [], []
        path = [J["ankle"] + V((0, 0.02, -0.035)), J["ankle"] + V((0, -0.03, -0.045)), J["ball"] + V((0, 0.03, 0.005)), J["ball"] + V((0, -0.005, 0.0)),
                J["toe"] + V((0, 0.01, 0.0)), J["toe"] + V((0, -0.012, -0.004))]
        rads = [(0.055, 0.062), (0.054, 0.055), (0.050, 0.040), (0.047, 0.033), (0.036, 0.024), (0.018, 0.014)]
        for k in range(len(path) - 1):
            bone = "foot_l" if k < 3 else "toe_l"
            a, f = s.shell([path[k], path[k + 1] + (path[k + 1] - path[k]) * 0.18], arc_profiles([rads[k], rads[k + 1]], 0.15, pi - 0.15, 16),
                           up, 0, rigid(bone, 1.0), T, tile=0.3)
            vs += a; fs += f
        return vs, fs

    for fn in (cuisse, poleyn, greave, sabaton):
        mirror_part(s, fn)
    return s


# ------------------------------------------------------------------ build
def main():
    scene = C.empty_scene()
    mats = {
        "steel": M.make("aldren_steel", "steel", TEX, seed=1450),
        "mail": M.make("aldren_mail", "mail", TEX, seed=1451),
        "doublet": M.make("aldren_doublet", "cloth", TEX, seed=1452, tint=(0.13, 0.15, 0.21), lines=8),
        "hose": M.make("aldren_hose", "cloth", TEX, seed=1453, tint=(0.20, 0.10, 0.08), lines=1),
        "leather": M.make("aldren_leather", "leather", TEX, seed=1454),
        "cap": M.flat("aldren_cap", (0.05, 0.045, 0.04), 0.9),
    }
    root = bpy.data.objects.new(NAME, None); scene.collection.objects.link(root)
    arm = H.build_armature(f"{NAME}_rig", BONES)
    arm.parent = root
    root["wos_asset"] = NAME
    root["wos_convention"] = "metres; glTF +Y up, character faces +Z; weapon_r: +Y blade, +Z true edge, hand_primary at bone head"

    slots = [build_body(mats), build_torso(mats), build_head(mats), build_arms(mats), build_legs(mats)]
    objs = [sl.finish(arm) for sl in slots]
    import bmesh
    for ob in objs:                                       # hard edges on plate rims, smooth elsewhere
        bm = bmesh.new(); bm.from_mesh(ob.data)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(65):
                e.smooth = False
        bm.to_mesh(ob.data); bm.free()

    # IK constraints, joint limits (kept in the .blend for animators; validated below)
    for side in "lr":
        H.add_ik(arm, f"forearm_{side}", f"ik_hand_{side}", f"pole_elbow_{side}")
        H.copy_rot(arm, f"hand_{side}", f"ik_hand_{side}")
        H.add_ik(arm, f"calf_{side}", f"ik_foot_{side}", f"pole_knee_{side}")
        H.copy_rot(arm, f"foot_{side}", f"ik_foot_{side}")
        H.hinge_limits(arm, f"forearm_{side}", 0, 150)
        H.hinge_limits(arm, f"calf_{side}", -150, 0)
    bpy.context.view_layer.update()

    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    glb = C.export_glb(f"assets/v0.4.0/characters/{NAME}.glb", export_animations=False, export_skins=True,
                       export_image_format="AUTO", use_selection=False)

    # ---------------- guard pose (posta di donna / pflug-like middle guard), driven through the rig's own IK
    def rot(pb, x=0, y=0, z=0):
        b = arm.pose.bones[pb]; b.rotation_mode = "XYZ"; b.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
    pel = arm.pose.bones["pelvis"]; pel.location = (0, -0.05, 0)
    rot("pelvis", 7, -22, 0); rot("spine_01", 4, 8, 0); rot("spine_02", 3, 8, 0); rot("spine_03", 0, 4, 0)
    rot("neck", -6, 2, 0); rot("head", -4, 0, 0)
    rot("clavicle_l", 0, 0, -6); rot("clavicle_r", 0, 0, 6)
    for side in "lr":
        rot(f"fingers_01_{side}", 78); rot(f"fingers_02_{side}", 72); rot(f"thumb_01_{side}", 35); rot(f"thumb_02_{side}", 25)
    bpy.context.view_layer.update()

    blade = V((0.0, -0.80, 0.60)).normalized()
    edge = (V((0, 0, -1)) - blade * V((0, 0, -1)).dot(blade)).normalized()
    G_r = V((-0.03, -0.31, 1.03)); G_l = G_r - blade * 0.14
    rest = lambda b: arm.data.bones[b].matrix_local
    for side, sock, G in (("r", "weapon_r", G_r), ("l", "grip_l", G_l)):
        rel = rest(f"hand_{side}").inverted() @ rest(sock)
        hand_m = H.frame_matrix(G, blade, edge) @ rel.inverted()
        H.set_pose_matrix(arm, f"ik_hand_{side}", arm.matrix_world @ hand_m)
    H.set_pose_matrix(arm, "pole_elbow_r", Matrix.Translation((-0.55, 0.15, 0.85)))
    H.set_pose_matrix(arm, "pole_elbow_l", Matrix.Translation((0.55, 0.15, 0.85)))
    for side, ank, yaw in (("l", V((0.14, -0.25, 0.085)), -12), ("r", V((-0.17, 0.23, 0.085)), 40)):
        m = Matrix.Rotation(math.radians(yaw), 4, "Z") @ rest(f"foot_{side}").to_3x3().to_4x4()
        m.translation = ank
        H.set_pose_matrix(arm, f"ik_foot_{side}", m)
    H.set_pose_matrix(arm, "pole_knee_l", Matrix.Translation((0.20, -0.75, 0.55)))
    H.set_pose_matrix(arm, "pole_knee_r", Matrix.Translation((-0.35, -0.45, 0.55)))

    # calibrate IK pole angles: choose the angle that puts the elbow/knee nearest its pole-plane side
    def calib(tip, pole):
        c = [k for k in arm.pose.bones[tip].constraints if k.type == "IK"][0]
        best = None
        for ang in range(-180, 180, 15):
            c.pole_angle = math.radians(ang); bpy.context.view_layer.update()
            joint = H.bone_world(arm, tip).translation
            d = (joint - H.bone_world(arm, pole).translation).length
            if best is None or d < best[0]: best = (d, ang)
        c.pole_angle = math.radians(best[1]); bpy.context.view_layer.update()
        return best[1]
    poles = {t: calib(t, p) for t, p in (("forearm_r", "pole_elbow_r"), ("forearm_l", "pole_elbow_l"),
                                          ("calf_l", "pole_knee_l"), ("calf_r", "pole_knee_r"))}
    err = {}
    for side in "lr":
        err[f"wrist_{side}_mm"] = round((H.bone_world(arm, f"hand_{side}").translation - H.bone_world(arm, f"ik_hand_{side}").translation).length * 1000, 2)
        err[f"ankle_{side}_mm"] = round((H.bone_world(arm, f"foot_{side}").translation - H.bone_world(arm, f"ik_foot_{side}").translation).length * 1000, 2)

    # attach the sword to weapon_r (convention: sword local +Z blade, +X true edge, hand_primary at z=-0.05)
    bpy.ops.import_scene.gltf(filepath=os.path.join(C.REPO, SWORD_GLB))
    sword = [o for o in bpy.data.objects if o.name.startswith("longsword_xva") and o.parent is None][0]
    R = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()
    sword.matrix_world = H.bone_world(arm, "weapon_r") @ R @ Matrix.Translation((0, 0, 0.05))
    bpy.context.view_layer.update()
    sec = [o for o in bpy.data.objects if o.name.startswith("hand_secondary")][0].matrix_world.translation
    err["left_hand_on_grip_mm"] = round((sec - H.bone_world(arm, "grip_l").translation).length * 1000, 2)

    # ---------------- review renders
    prev, eng = C.preview_stage(scene, target=(0, 0, 1.0), radius=1.6, floor=True)
    scene.cycles.samples = 64
    out = f"previews/v0.4.0/{NAME}"
    cams = [("guard_front34", (-1.55, -2.45, 1.45), (0, -0.05, 1.05), 50, (900, 1350)),
            ("guard_side", (-3.2, -0.05, 1.10), (0, -0.05, 1.0), 50, (900, 1350)),
            ("guard_back34", (1.9, 2.4, 1.6), (0, 0, 1.05), 50, (900, 1350)),
            ("guard_detail_upper", (-0.75, -1.25, 1.55), (0, -0.12, 1.30), 60, (1000, 1000)),
            ("player_pov_portrait", (0.0, -2.35, 1.66), (0, 0, 1.25), 26, (720, 1280))]
    renders = []
    for nm, loc, tgt, lens, res in cams:
        cam = C.look_cam(prev, f"cam_{nm}", loc, tgt, lens=lens)
        renders.append(C.render_still(scene, cam, f"{out}_{nm}.png", res))

    blend = C.save_blend(f"source/blender/characters/{NAME}.blend")
    report = {"asset": NAME, "blender": bpy.app.version_string, "engine": eng, "triangles": tris,
              "slots": {o.name: {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons), "materials": [m.name for m in o.data.materials]} for o in objs},
              "draw_calls_est": sum(len(o.data.materials) for o in objs),
              "normals_fixed": {sl.name: f"{sl.flipped}/{sl.faces_total}" for sl in slots},
              "bones": len(arm.data.bones), "deform_bones": len(DEFORM),
              "ik_pole_angles_deg": poles, "ik_errors": err,
              "glb": os.path.relpath(glb, C.REPO), "glb_sha256": C.sha256(glb), "glb_bytes": os.path.getsize(glb),
              "blend": os.path.relpath(blend, C.REPO), "renders": [os.path.relpath(r, C.REPO) for r in renders]}
    C.write_json(f"assets/v0.4.0/characters/{NAME}.report.json", report)
    print("WOS_REPORT", json.dumps(report))


main()
