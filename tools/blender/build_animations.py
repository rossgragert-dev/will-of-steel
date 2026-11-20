"""Will of Steel v0.4.0 Phase C: author, bake and export the first longsword clip set (original keyframed motion,
inspired by German longsword technique: Pflug/vom Tag guards, Oberhau, diagonal Oberhaue from both sides,
roof parry, restrained deflection). Not motion capture.

Usage: blender -b --factory-startup --python tools/blender/build_animations.py -- <aldren|william> v001
Inputs (opened in memory, never saved over): source/blender/characters/ser_aldren_v007.blend,
source/blender/first-person/william_fp_arms_v004.blend, william_fp_guards_v005.json (revised parry).
Outputs (new): assets/v0.4.0/animations/<char>_clips_<ver>.glb (skeleton + animations only),
<char>_clips_<ver>.json (metadata + per-frame samples), source/blender/animations/<char>_anim_<ver>.blend (local).
"""
import bpy, os, sys, json, math
from mathutils import Vector as V, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import wos_humanoid as H
import wos_anim as A

CHAR, VER = (C.args() + ["aldren", "v001"])[:2] if len(C.args()) >= 2 else ("aldren", "v001")
N_ATTACK, F_CONTACT = 44, 24
ATTACK_PHASES = {"prepare": [0, 5], "windup": [5, 18], "attack": [18, 24], "follow_through": [24, 34], "recovery": [34, 44]}
ENGAGEMENT = {"guard_distance_m": 1.65, "contact_distance_m": 1.45, "attack_step_m": 0.20}


def n(*v):
    return tuple(V(v).normalized())


# ====================================================================== Ser Aldren (third person; faces -Y, right = -X)
READY_K = dict(pel_loc=(0, -0.05, 0), pel_rot=(7, -22, 0), sp1=(4, 8, 0), sp2=(3, 8, 0), sp3=(0, 4, 0), neck=(-6, 2, 0),
               head=(-4, 0, 0), clav=(0, -6), foot_l=(0.14, -0.25, 0.085, -12), foot_r=(-0.17, 0.23, 0.085, 40),
               hilt=(-0.03, -0.31, 1.03), blade=n(0, -0.8, 0.6), edge=(0, 0, -1), pole_r=(-0.55, 0.15, 0.85), pole_l=(0.55, 0.15, 0.85))
FL0, FR0 = READY_K["foot_l"], READY_K["foot_r"]


def k(f, ease="inout", **ch):
    return {"f": f, "ease": ease, **ch}


def recovery_tail(foot_l_fwd, foot_r_fwd):
    """Shared follow-through end and retreating recovery: rear foot back first, then lead foot; blade returns to Pflug."""
    return [
        k(36, "inout", hilt=(0.0, -0.40, 1.04), blade=n(0.03, -0.96, -0.22), edge=(0, 0, -1), pel_loc=(0, -0.065, 0.18),
          pel_rot=(8, -6, 0), sp1=(6, 2, 0), sp2=(4, 4, 0), sp3=(1, 3, 0), neck=(-8, 2, 0), clav=(4, -3),
          foot_l=foot_l_fwd, foot_r=foot_r_fwd, pole_r=(-0.55, 0.15, 0.85), pole_l=(0.55, 0.15, 0.85)),
        k(40, "inout", pel_loc=(0, -0.055, 0.10), foot_r=FR0, hilt=(-0.02, -0.34, 1.03), blade=n(0, -0.88, 0.42)),
        k(44, "inout", **READY_K),
    ]


def aldren_clips():
    R = READY_K
    head = [k(0, **R),
            k(5, "inout", hilt=(-0.09, -0.22, 1.30), blade=n(-0.04, -0.35, 0.94), edge=(0, -1, 0), pel_loc=(0, -0.05, -0.02),
              pel_rot=(5, -26, 0), sp1=(3, 10, 0), sp2=(1, 10, 0), sp3=(-2, 6, 0), neck=(-6, 4, 0), clav=(2, 2),
              pole_r=(-0.62, 0.20, 1.05), pole_l=(0.55, 0.20, 1.05)),
            k(11, "inout", hilt=(-0.14, -0.16, 1.70), blade=n(0.02, 0.42, 0.91), edge=(0, -1, 0), pel_loc=(0, -0.06, -0.03),
              pel_rot=(4, -30, 0), sp1=(0, 12, 0), sp2=(-3, 12, 0), sp3=(-4, 8, 0), neck=(-4, 4, 0), clav=(4, 12),
              pole_r=(-0.70, 0.25, 1.35), pole_l=(0.45, 0.20, 1.30)),
            k(14, "out", hilt=(-0.14, -0.17, 1.71)),
            k(18, "in", hilt=(-0.11, -0.26, 1.74), blade=n(0.03, 0.80, 0.60), edge=(0, -1, 0.2), pel_loc=(0, -0.065, 0.06),
              pel_rot=(6, -18, 0), sp1=(3, 6, 0), sp2=(0, 4, 0), sp3=(-2, 2, 0), clav=(8, 14)),
            k(21, "in", hilt=(-0.07, -0.50, 1.72), blade=n(0.0, -0.12, 0.99), edge=(0, -1, 0), pel_loc=(0, -0.07, 0.13),
              pel_rot=(7, -6, 0), sp1=(6, 2, 0), sp2=(4, -2, 0), sp3=(2, -2, 0), neck=(-8, 2, 0), clav=(14, 10),
              pole_r=(-0.65, 0.10, 1.25), pole_l=(0.50, 0.10, 1.25)),
            k(24, "in", hilt=(-0.02, -0.62, 1.72), blade=n(0, -0.995, -0.10), edge=(0, -0.3, -1), pel_loc=(0, -0.08, 0.20),
              pel_rot=(9, 6, 0), sp1=(8, -4, 0), sp2=(6, -6, 0), sp3=(4, -4, 0), neck=(-12, 2, 0), clav=(18, 4),
              foot_l=(0.15, -0.45, 0.085, -8), pole_r=(-0.55, 0.0, 1.10), pole_l=(0.50, 0.0, 1.10)),
            k(29, "out", hilt=(0.04, -0.62, 1.22), blade=n(0.10, -0.60, -0.79), edge=(0, 0.4, -1), pel_loc=(0, -0.085, 0.22),
              pel_rot=(10, 10, 0), sp1=(10, -6, 0), sp2=(7, -8, 0), sp3=(4, -6, 0), neck=(-12, 0, 0), clav=(14, 0),
              foot_r=FR0, pole_r=(-0.50, 0.20, 0.85), pole_l=(0.50, 0.20, 0.85)),
            k(33, "inout", hilt=(0.05, -0.48, 1.04), blade=n(0.06, -0.78, -0.62), edge=(0, 0.5, -1), pel_loc=(0, -0.075, 0.21),
              pel_rot=(8, 2, 0), foot_r=(-0.17, 0.03, 0.085, 38))] + recovery_tail((0.15, -0.45, 0.085, -8), (-0.17, 0.03, 0.085, 38))
    ul = [k(0, **R),
          k(5, "inout", hilt=(-0.14, -0.28, 1.30), blade=n(-0.30, -0.30, 0.90), edge=(0.3, -1, 0), pel_loc=(0, -0.05, -0.02),
            pel_rot=(5, -28, 0), sp1=(3, 11, 0), sp2=(1, 11, -1), sp3=(-2, 7, -1), neck=(-6, 4, 0), clav=(2, 3),
            pole_r=(-0.66, 0.20, 1.05), pole_l=(0.50, 0.20, 1.05)),
          k(11, "inout", hilt=(-0.27, -0.22, 1.52), blade=n(-0.40, 0.40, 0.82), edge=(0.4, -1, 0), pel_loc=(0, -0.06, -0.03),
            pel_rot=(4, -34, 0), sp1=(0, 14, 0), sp2=(-3, 14, -2), sp3=(-4, 8, -3), neck=(-4, 6, 0), clav=(4, 10),
            pole_r=(-0.75, 0.25, 1.20), pole_l=(0.40, 0.20, 1.20)),
          k(14, "out", hilt=(-0.27, -0.23, 1.53)),
          k(18, "in", hilt=(-0.22, -0.26, 1.62), blade=n(-0.35, 0.75, 0.55), edge=(0.4, -1, 0.2), pel_loc=(0, -0.065, 0.06),
            pel_rot=(6, -20, 0), sp1=(3, 8, 0), sp2=(0, 6, -1), sp3=(-2, 3, -1), clav=(8, 12)),
          k(21, "in", hilt=(-0.14, -0.48, 1.62), blade=n(-0.60, -0.20, 0.77), edge=(0.6, -0.6, -0.3), pel_loc=(0, -0.07, 0.13),
            pel_rot=(7, -4, 0), sp1=(6, 2, 0), sp2=(4, 0, 0), sp3=(2, -1, 0), neck=(-8, 2, 0), clav=(14, 8),
            pole_r=(-0.70, 0.10, 1.15), pole_l=(0.45, 0.10, 1.15)),
          k(24, "in", hilt=(-0.08, -0.67, 1.62), blade=n(-0.26, -0.93, -0.26), edge=(0.7, 0, -0.7), pel_loc=(0, -0.08, 0.20),
            pel_rot=(9, 10, -2), sp1=(8, -4, 0), sp2=(6, -6, 0), sp3=(4, -4, 0), neck=(-12, 4, 0), clav=(16, 4),
            foot_l=(0.10, -0.45, 0.085, -14), pole_r=(-0.60, 0.0, 1.05), pole_l=(0.50, 0.0, 1.05)),
          k(29, "out", hilt=(0.10, -0.58, 1.18), blade=n(0.40, -0.55, -0.73), edge=(0.6, 0.3, -0.7), pel_loc=(0, -0.085, 0.22),
            pel_rot=(10, 16, 0), sp1=(10, -8, 0), sp2=(7, -10, 0), sp3=(4, -8, 0), neck=(-12, 0, 0), clav=(12, 0),
            foot_r=FR0, pole_r=(-0.45, 0.20, 0.85), pole_l=(0.55, 0.20, 0.85)),
          k(33, "inout", hilt=(0.10, -0.46, 1.02), blade=n(0.30, -0.72, -0.62), edge=(0.5, 0.5, -0.7), pel_loc=(0, -0.075, 0.21),
            pel_rot=(8, 6, 0), foot_r=(-0.19, 0.03, 0.085, 38))] + recovery_tail((0.10, -0.45, 0.085, -14), (-0.19, 0.03, 0.085, 38))
    ur = [k(0, **R),
          k(5, "inout", hilt=(0.04, -0.22, 1.30), blade=n(0.30, -0.30, 0.90), edge=(-0.3, -1, 0), pel_loc=(0, -0.05, -0.02),
            pel_rot=(5, -14, 0), sp1=(3, 2, 0), sp2=(1, 0, 1), sp3=(-2, -2, 1), neck=(-6, 0, 0), clav=(3, 3),
            pole_r=(-0.45, 0.15, 1.05), pole_l=(0.66, 0.20, 1.05)),
          k(11, "inout", hilt=(0.07, -0.17, 1.62), blade=n(0.42, 0.40, 0.81), edge=(-0.4, -1, 0), pel_loc=(0, -0.06, -0.03),
            pel_rot=(4, -6, 0), sp1=(0, -4, 0), sp2=(-3, -8, 2), sp3=(-4, -6, 3), neck=(-4, -2, 0), clav=(4, 10),
            pole_r=(-0.45, 0.10, 1.20), pole_l=(0.75, 0.25, 1.20)),
          k(14, "out", hilt=(0.07, -0.18, 1.63)),
          k(18, "in", hilt=(0.08, -0.26, 1.66), blade=n(0.35, 0.75, 0.55), edge=(-0.4, -1, 0.2), pel_loc=(0, -0.065, 0.06),
            pel_rot=(6, -14, 0), sp1=(3, -2, 0), sp2=(0, -4, 1), sp3=(-2, -3, 1), clav=(8, 12)),
          k(21, "in", hilt=(0.08, -0.48, 1.62), blade=n(0.60, -0.20, 0.77), edge=(-0.6, -0.6, -0.3), pel_loc=(0, -0.07, 0.13),
            pel_rot=(7, -14, 0), sp1=(6, -4, 0), sp2=(4, -4, 0), sp3=(2, -2, 0), neck=(-8, 0, 0), clav=(14, 8),
            pole_r=(-0.50, 0.10, 1.15), pole_l=(0.70, 0.10, 1.15)),
          k(24, "in", hilt=(0.0, -0.66, 1.62), blade=n(0.26, -0.93, -0.26), edge=(-0.7, 0, -0.7), pel_loc=(0, -0.08, 0.20),
            pel_rot=(9, -10, 2), sp1=(8, -6, 0), sp2=(6, -8, 0), sp3=(4, -6, 0), neck=(-12, -2, 0), clav=(16, 4),
            foot_l=(0.18, -0.44, 0.085, -10), pole_r=(-0.50, 0.0, 1.05), pole_l=(0.60, 0.0, 1.05)),
          k(29, "out", hilt=(-0.06, -0.62, 1.22), blade=n(-0.40, -0.55, -0.73), edge=(-0.6, 0.3, -0.7), pel_loc=(0, -0.085, 0.22),
            pel_rot=(10, -16, 0), sp1=(10, -4, 0), sp2=(7, -2, 0), sp3=(4, 0, 0), neck=(-12, 0, 0), clav=(12, 0),
            foot_r=FR0, pole_r=(-0.55, 0.20, 0.85), pole_l=(0.45, 0.20, 0.85)),
          k(33, "inout", hilt=(-0.08, -0.52, 1.04), blade=n(-0.30, -0.72, -0.62), edge=(-0.5, 0.5, -0.7), pel_loc=(0, -0.075, 0.21),
            pel_rot=(8, -10, 0), foot_r=(-0.15, 0.03, 0.085, 38))] + recovery_tail((0.18, -0.44, 0.085, -10), (-0.15, 0.03, 0.085, 38))
    PARRY = dict(hilt=(-0.08, -0.38, 1.66), blade=n(0.90, -0.30, 0.30), edge=(0, 0, 1), pel_loc=(0, -0.07, 0), pel_rot=(6, -14, 0),
                 sp1=(2, 6, 0), sp2=(-2, 4, 0), sp3=(-3, 2, 0), neck=(-8, 0, 0), clav=(6, 14),
                 pole_r=(-0.70, 0.05, 1.25), pole_l=(0.60, 0.0, 1.25))
    parry = [k(0, **R), k(7, "out", **PARRY), k(19, "hold", **PARRY), k(30, "inout", **R)]
    deflect = [k(0, **{**R, **PARRY}),
               k(2, "out", hilt=(-0.08, -0.35, 1.60), blade=n(0.88, -0.30, 0.18), pel_loc=(0, -0.085, 0.01), sp2=(-5, 3, 0), clav=(6, 12)),
               k(7, "out", hilt=(-0.09, -0.33, 1.58), blade=n(0.89, -0.28, 0.14), pel_loc=(0, -0.088, 0.012)),
               k(20, "inout", **PARRY)]
    idle = [k(0, **R),
            k(45, "inout", pel_loc=(0.004, -0.047, 0.0), sp2=(1.8, 8, 0), sp3=(-0.8, 4, 0), clav=(0, -4.5), head=(-4.5, 0, 0),
              hilt=(-0.03, -0.314, 1.038), blade=n(0.01, -0.79, 0.615)),
            k(90, "inout", **R)]
    return {
        "aldren_idle_ready": dict(keys=idle, frames=90, loop=True, kind="idle", zone=None, phases={}),
        "aldren_attack_head": dict(keys=head, frames=N_ATTACK, kind="attack", zone="head", contact=F_CONTACT,
                                   target=(0, -1.18, 1.70), phases=ATTACK_PHASES),
        "aldren_attack_upper_left": dict(keys=ul, frames=N_ATTACK, kind="attack", zone="upperLeft", contact=F_CONTACT,
                                         target=(-0.17, -1.35, 1.40), phases=ATTACK_PHASES),
        "aldren_attack_upper_right": dict(keys=ur, frames=N_ATTACK, kind="attack", zone="upperRight", contact=F_CONTACT,
                                          target=(0.17, -1.35, 1.40), phases=ATTACK_PHASES),
        "aldren_parry_head": dict(keys=parry, frames=30, kind="parry", zone="head", expected_contact=9,
                                  phases={"raise": [0, 7], "hold": [7, 19], "recover": [19, 30]}),
        "aldren_deflect_head": dict(keys=deflect, frames=20, kind="deflect", zone="head", expected_contact=0,
                                    phases={"impact": [0, 2], "absorb": [2, 7], "settle": [7, 20]}),
    }


# ====================================================================== William (first person; camera space about the eye)
EYE = V((0, -0.075, 1.675))
def cam2b(v): return V((-v[0], v[2], v[1]))
POLE_RULE = {"down": (0.45, 0.35, -0.35), "wide": (0.65, 0.15, -0.05), "high": (0.60, 0.05, 0.20)}


def bladeAxis(p):
    a, b, c = p
    return (-math.cos(b) * math.sin(c), math.cos(a) * math.cos(c) - math.sin(a) * math.sin(b) * math.sin(c),
            math.sin(a) * math.cos(c) + math.cos(a) * math.sin(b) * math.sin(c))


def wk(f, ease="inout", hilt=None, blade=None, edge=None, clav=None, sp3=None, pole=None):
    """Key in William camera space -> world-space channels."""
    out = {"f": f, "ease": ease}
    if hilt is not None: out["hilt"] = tuple(EYE + cam2b(hilt))
    if blade is not None: out["blade"] = tuple(cam2b(V(blade).normalized()))
    if edge is not None: out["edge"] = tuple(cam2b(edge))
    if clav is not None: out["clav"] = clav
    if sp3 is not None: out["sp3"] = sp3
    if pole is not None:
        out["_pole"] = pole
    return out


def finalize_poles(keys):
    """Resolve named elbow-pole rules into world positions from each key's hilt/blade."""
    cur = {}
    for kk in keys:
        cur.update({a: b for a, b in kk.items() if a not in ("f", "ease")})
        rule = POLE_RULE[cur.get("_pole", "down")]
        G_r = V(cur["hilt"]); G_l = G_r - V(cur["blade"]) * 0.14
        kk["pole_r"] = tuple(G_r + V((-rule[0], rule[1], rule[2])))
        kk["pole_l"] = tuple(G_l + V((rule[0], rule[1], rule[2])))
    for kk in keys:
        kk.pop("_pole", None)
    return keys


def william_clips():
    g5 = json.load(open(os.path.join(C.REPO, "assets/v0.4.0/first-person/william_fp_guards_v005.json")))["guards"]
    ready_blade = bladeAxis((-.62, 0, -.02))
    RD = dict(hilt=(0.20, -0.34, -0.40), blade=ready_blade, edge=(0, 0, -1), clav=(0, 0), sp3=(0, 0, 0), pole="down")
    hd = g5["head_5"]
    PR = dict(hilt=tuple(hd["hilt_cam_m"]), blade=tuple(hd["blade_dir_cam"]), edge=(0, 1, 0), clav=(0, hd["clavicle_lift_deg"]),
              sp3=(0, 0, 0), pole=hd["elbow_pole"])
    tail = [wk(34, "inout", hilt=(0.04, -0.38, -0.40), blade=(0.0, -0.6, -0.8), edge=(0, -1, 0), clav=(6, 0), sp3=(1, 2, 0), pole="down"),
            wk(44, "inout", **RD)]
    head = [wk(0, **RD),
            wk(5, "inout", hilt=(0.22, -0.18, -0.38), blade=(0.06, 0.85, -0.52), edge=(0, 0, -1), clav=(2, 6), sp3=(0, -4, 0)),
            wk(11, "inout", hilt=(0.24, 0.04, -0.24), blade=(0.04, 0.80, 0.60), edge=(0, 0, -1), clav=(4, 16), sp3=(-2, -10, 0), pole="high"),
            wk(14, "out", hilt=(0.24, 0.045, -0.245)),
            wk(18, "in", hilt=(0.14, 0.04, -0.28), blade=(0.02, 0.55, 0.83), clav=(8, 16), sp3=(-2, -6, 0)),
            wk(20, "in", hilt=(0.08, 0.02, -0.34), blade=(0.0, 1.0, 0.05), edge=(0, 0, -1), clav=(14, 12), sp3=(2, 0, 0), pole="wide"),
            wk(22, "linear", hilt=(0.06, 0.0, -0.38), blade=(0.0, 0.55, -0.83), edge=(0, 0, -1), clav=(16, 9), sp3=(3, 3, 0)),
            wk(24, "in", hilt=(0.04, 0.0, -0.40), blade=(0.0, -0.12, -0.99), edge=(0, -1, 0), clav=(18, 6), sp3=(4, 6, 0)),
            wk(29, "out", hilt=(-0.02, -0.28, -0.44), blade=(-0.12, -0.80, -0.58), edge=(0, -0.6, 0.6), clav=(12, 2), pole="down")] + tail
    ul = [wk(0, **RD),
          wk(5, "inout", hilt=(0.26, -0.16, -0.36), blade=(0.40, 0.75, -0.50), edge=(-1, 0, -0.3), clav=(2, 6), sp3=(0, -5, 0)),
          wk(11, "inout", hilt=(0.30, 0.02, -0.24), blade=(0.55, 0.62, 0.55), edge=(-0.7, -0.3, -0.6), clav=(4, 14), sp3=(-2, -12, 0), pole="high"),
          wk(14, "out", hilt=(0.30, 0.025, -0.245)),
          wk(18, "in", hilt=(0.20, 0.04, -0.28), blade=(0.45, 0.40, 0.80), clav=(8, 14), sp3=(-2, -8, 0)),
          wk(20, "in", hilt=(0.10, 0.0, -0.36), blade=(0.70, 0.70, 0.10), edge=(-0.7, -0.7, 0), clav=(14, 10), sp3=(2, 0, 0), pole="wide"),
          wk(22, "linear", hilt=(0.06, -0.02, -0.38), blade=(0.13, 0.75, -0.64), edge=(-0.7, -0.7, 0), clav=(16, 8), sp3=(3, 4, 0)),
          wk(24, "in", hilt=(0.02, -0.06, -0.40), blade=(-0.55, 0.15, -0.82), edge=(-0.6, -0.8, 0), clav=(18, 6), sp3=(4, 8, 0)),
          wk(29, "out", hilt=(-0.14, -0.28, -0.42), blade=(-0.70, -0.45, -0.55), edge=(-0.3, -0.9, 0.3), clav=(12, 2), pole="down")] + tail
    ur = [wk(0, **RD),
          wk(5, "inout", hilt=(0.02, -0.16, -0.38), blade=(-0.40, 0.75, -0.50), edge=(1, 0, -0.3), clav=(2, 6), sp3=(0, 5, 0)),
          wk(11, "inout", hilt=(-0.08, 0.02, -0.28), blade=(-0.55, 0.62, 0.55), edge=(0.7, -0.3, -0.6), clav=(4, 14), sp3=(-2, 10, 0), pole="wide"),
          wk(14, "out", hilt=(-0.08, 0.025, -0.285)),
          wk(18, "in", hilt=(-0.04, 0.04, -0.30), blade=(-0.45, 0.40, 0.80), clav=(8, 14), sp3=(-2, 6, 0)),
          wk(20, "in", hilt=(0.02, 0.0, -0.36), blade=(-0.70, 0.70, 0.10), edge=(0.7, -0.7, 0), clav=(14, 10), sp3=(2, 0, 0)),
          wk(22, "linear", hilt=(0.04, -0.02, -0.38), blade=(-0.13, 0.75, -0.64), edge=(0.7, -0.7, 0), clav=(16, 8), sp3=(3, -4, 0)),
          wk(24, "in", hilt=(0.06, -0.06, -0.40), blade=(0.55, 0.15, -0.82), edge=(0.6, -0.8, 0), clav=(18, 6), sp3=(4, -8, 0)),
          wk(29, "out", hilt=(0.24, -0.28, -0.42), blade=(0.70, -0.45, -0.55), edge=(0.3, -0.9, 0.3), clav=(12, 2), pole="down")] + tail
    parry = [wk(0, **RD), wk(6, "out", **PR), wk(18, "hold", **PR), wk(28, "inout", **RD)]
    ph = PR["hilt"]; pb = V(PR["blade"])
    hit = (pb - V((0, 0.12, 0))).normalized()
    deflect = [wk(0, **PR), wk(2, "out", hilt=(ph[0], ph[1] - 0.04, ph[2] + 0.02), blade=tuple(hit)),
               wk(7, "out", hilt=(ph[0], ph[1] - 0.05, ph[2] + 0.025), blade=tuple((pb - V((0, 0.15, 0))).normalized())),
               wk(20, "inout", **PR)]
    idle = [wk(0, **RD), wk(45, "inout", hilt=(0.20, -0.328, -0.405), clav=(0, 2.5), sp3=(-1.5, 0, 0)), wk(90, "inout", **RD)]
    clips = {
        "william_idle_ready": dict(keys=idle, frames=90, loop=True, kind="idle", zone=None, phases={}),
        "william_attack_head": dict(keys=head, frames=N_ATTACK, kind="attack", zone="head", contact=F_CONTACT, phases=ATTACK_PHASES),
        "william_attack_upper_left": dict(keys=ul, frames=N_ATTACK, kind="attack", zone="upperLeft", contact=F_CONTACT, phases=ATTACK_PHASES),
        "william_attack_upper_right": dict(keys=ur, frames=N_ATTACK, kind="attack", zone="upperRight", contact=F_CONTACT, phases=ATTACK_PHASES),
        "william_parry_head": dict(keys=parry, frames=28, kind="parry", zone="head", expected_contact=8,
                                   phases={"raise": [0, 6], "hold": [6, 18], "recover": [18, 28]}),
        "william_deflect_head": dict(keys=deflect, frames=20, kind="deflect", zone="head", expected_contact=0,
                                     phases={"impact": [0, 2], "absorb": [2, 7], "settle": [7, 20]}),
    }
    for c in clips.values():
        c["keys"] = finalize_poles(c["keys"])
        for kk in c["keys"]:
            kk.setdefault("sp3", None) if False else None
    return clips


def camera_advance(frames):
    """Suggested first-person step-in curve (m) for attacks: 0 -> 0.20 by contact, held, eased back by the end."""
    out = []
    for f in range(frames + 1):
        if f <= 16: a = 0.0
        elif f <= 24: u = (f - 16) / 8; a = 0.20 * u * u * (3 - 2 * u)
        elif f <= 30: a = 0.20
        else: u = (f - 30) / (frames - 30); a = 0.20 * (1 - u * u * (3 - 2 * u))
        out.append(round(a, 4))
    return out


# ====================================================================== main
def main():
    if CHAR == "aldren":
        src, rig_key, clips, model = "source/blender/characters/ser_aldren_v008.blend", "ser_aldren_v008_rig", aldren_clips(), \
            "assets/v0.4.0/characters/ser_aldren_v008.glb"
        kind = "knight"
    else:
        src, rig_key, clips, model = "source/blender/first-person/william_fp_arms_v004.blend", "william_fp_arms_v004_rig", william_clips(), \
            "assets/v0.4.0/first-person/william_fp_arms_v004.glb"
        kind = "arms"
    bpy.ops.wm.open_mainfile(filepath=os.path.join(C.REPO, src), load_ui=False)
    C.safe_prefs()
    arm = bpy.data.objects[rig_key]
    rig = A.Rig(arm, kind)
    meta, baked = {}, {}
    for name, c in clips.items():
        poses, samples = A.bake_clip(rig, name, c["keys"], c["frames"], loop=c.get("loop", False))
        baked[name] = poses
        mx = lambda key: round(max(samples[key]), 2)
        qa = {"grip_error_mm_max": mx("grip_error_mm"), "wrist_err_mm_max": max(mx("wrist_err_l_mm"), mx("wrist_err_r_mm")),
              "elbow_deg_range": [round(min(samples["elbow_deg_l"] + samples["elbow_deg_r"]), 1), mx("elbow_deg_l") if mx("elbow_deg_l") > mx("elbow_deg_r") else mx("elbow_deg_r")],
              "wrist_residual_twist_deg_max": round(max(abs(x) for x in samples["wrist_residual_twist_deg_l"] + samples["wrist_residual_twist_deg_r"]), 1)}
        entry = {"character": CHAR, "animation": name, "kind": c["kind"], "game_zone": c["zone"], "loop": bool(c.get("loop")),
                 "fps": A.FPS, "frame_start": 0, "frame_end": c["frames"], "duration_s": round(c["frames"] / A.FPS, 4),
                 "phases": c["phases"], "contact_frame": c.get("contact"),
                 "contact_normalized": round(c["contact"] / c["frames"], 4) if c.get("contact") else None,
                 "expected_contact_frame": c.get("expected_contact"), "qa": qa, "samples": samples}
        if kind == "knight":
            pel = [V((p[0], -p[2], p[1])) for p in samples["pelvis"]]
            off = [p - pel[0] for p in pel]
            entry["root_motion"] = {"mode": "in_place", "note": "pelvis-driven step-in/step-back; no root-bone translation",
                                    "pelvis_max_offset_m": A.gl(V((max(abs(o.x) for o in off), max(abs(o.y) for o in off), max(abs(o.z) for o in off)))),
                                    "net_displacement_m": A.gl(off[-1])}
            # foot planting: horizontal drift while a foot is down (toe height < 3 cm)
            drift = 0.0
            for s in ("foot_l", "foot_r"):
                pts = samples[s]; run = None
                for p in pts:
                    if p[1] < 0.03:
                        if run is None: run = p
                        drift = max(drift, math.hypot(p[0] - run[0], p[2] - run[2]))
                    else:
                        run = None
            entry["qa"]["planted_foot_drift_mm"] = round(drift * 1000, 2)
            if c.get("target"):
                f = c["contact"]
                b0, b1 = V(samples["blade_base"][f]), V(samples["blade_tip"][f])
                t = V(A.gl(c["target"]))
                ab = b1 - b0; s_ = max(0, min(1, (t - b0).dot(ab) / ab.length_squared))
                entry["contact_target_gl"] = A.gl(c["target"])
                entry["qa"]["contact_target_miss_m"] = round((b0 + ab * s_ - t).length, 3)
                entry["qa"]["contact_blade_fraction"] = round(s_, 2)
        else:
            entry["root_motion"] = {"mode": "in_place", "note": "first-person arms; camera not animated (fp_eye rest transform)",
                                    "pelvis_max_offset_m": [0, 0, 0], "net_displacement_m": [0, 0, 0]}
            if c["kind"] == "attack":
                entry["camera_advance_m"] = camera_advance(c["frames"])
        meta[name] = entry
        print("WOS_CLIP", name, json.dumps(qa), json.dumps({k: entry["qa"].get(k) for k in ("planted_foot_drift_mm", "contact_target_miss_m")}))

    # write actions, push to NLA tracks, mute constraints (export bakes FK only)
    A.reset_pose(arm)
    acts = {name: A.write_action(rig, name, poses) for name, poses in baked.items()}
    A.mute_constraints(arm, True)
    for name, act in acts.items():
        tr = arm.animation_data.nla_tracks.new(); tr.name = name
        st = tr.strips.new(name, 0, act)
        if hasattr(st, "action_slot") and act.slots:
            st.action_slot = act.slots[0]
    arm.animation_data.action = None
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, 90
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = A.FPS, 1.0   # GLB key times must be frame/30 s
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    glb = C.export_glb(f"assets/v0.4.0/animations/{CHAR}_clips_{VER}.glb", use_selection=True, export_skins=False,
                       export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
                       export_def_bones=False, export_frame_step=1, export_materials="NONE")
    blend = C.save_blend(f"source/blender/animations/{CHAR}_anim_{VER}.blend")
    out = {"version": VER, "character": CHAR, "model": model, "clips_glb": os.path.relpath(glb, C.REPO).replace("\\", "/"),
           "glb_sha256": C.sha256(glb), "glb_bytes": os.path.getsize(glb), "blend_local": os.path.relpath(blend, C.REPO).replace("\\", "/"),
           "fps": A.FPS, "engagement": ENGAGEMENT, "clips": meta,
           "weapon": {"model": "assets/v0.4.0/weapons/longsword_xva_v006.glb", "socket": "weapon_r", "off_hand_socket": "grip_l",
                      "convention": "weapon_r bone: +Y blade, +Z true edge, hand_primary at bone head; sword glTF axes: +Y blade, +X true edge"},
           "authoring": "original hand-authored keyframes (not motion capture); blade-led two-handed IK, baked to FK"}
    C.write_json(f"assets/v0.4.0/animations/{CHAR}_clips_{VER}.json", out)
    print("WOS_DONE", json.dumps({"glb": out["clips_glb"], "bytes": out["glb_bytes"]}))


main()
