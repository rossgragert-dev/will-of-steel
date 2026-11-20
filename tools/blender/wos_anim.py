"""Will of Steel: blade-led, body-driven keyframe animation engine (original hand-authored motion, not motion capture).

A clip is a list of keys. Each key sets any of these channels (unset channels inherit the previous key):
  knight:  pel_loc (local x, y=up, z=forward m), pel_rot (deg, local X=forward bend, Y=yaw(+left), Z=side bend),
           sp1, sp2, sp3, neck, head (deg, same axes), clav (protraction deg, lift deg) applied mirrored,
           foot_l / foot_r (ankle x, y, z, yaw deg; world), hilt (world m, right-hand grip point = sword hand_primary),
           blade (world dir to tip), edge (world hint for the true edge), pole_l / pole_r (world)
  arms:    sp3, clav, hilt, blade, edge, pole_l, pole_r   (first-person rig; same meanings)
Each key's `ease` shapes the segment that ENDS at it: linear | in (accelerate) | in3 | out (decelerate) | inout | hold.
Smooth channels use Catmull-Rom through the keys (periodic for loops). Feet use exact two-key interpolation so that
planted feet cannot drift, with a lift arc while stepping. Hands are solved by the rig's own IK on a single sword
frame (two-handed grip by construction). Forearm twist bones take 60% of the wrist roll (anti candy-wrapper).
The result is baked to FK (quaternions; pelvis also location) and constraints are muted for export.
"""
import bpy, math, json
from mathutils import Vector as V, Matrix, Quaternion, Euler
import wos_humanoid as H

FPS = 30
R_SWORD = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()   # sword local -> weapon_r bone local
SMOOTH = ("pel_loc", "pel_rot", "sp1", "sp2", "sp3", "neck", "head", "clav", "hilt", "blade", "edge", "pole_l", "pole_r")
FEET = ("foot_l", "foot_r")


def ease(kind, u):
    return {"linear": u, "in": u * u, "in3": u * u * u, "out": 1 - (1 - u) ** 2, "inout": u * u * (3 - 2 * u),
            "hold": 0.0}.get(kind, u * u * (3 - 2 * u))


def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


def resolve(keys):
    """Fill inherited channels so every key has every channel present in the first key."""
    out, cur = [], {}
    for k in keys:
        cur = {**cur, **{a: b for a, b in k.items() if a not in ("f", "ease")}}
        out.append({"f": k["f"], "ease": k.get("ease", "inout"), **{a: tuple(b) for a, b in cur.items()}})
    return out


def _monotone_param(ks, f):
    """C1-continuous, monotone map frame -> fractional key index (Fritsch-Carlson cubic through (key frame, index)).
    Speed varies smoothly between segments, so there is no stutter at keys; acceleration comes from key spacing."""
    xs = [k["f"] for k in ks]; n = len(xs)
    d = [1.0 / (xs[i + 1] - xs[i]) for i in range(n - 1)]          # secant slopes (index per frame)
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        m[i] = 0.0 if (ks[i]["ease"] == "hold" or ks[i + 1]["ease"] == "hold") else 2 * d[i - 1] * d[i] / (d[i - 1] + d[i])
    for i in range(n - 1):                                           # zero speed at holds
        if ks[i + 1]["ease"] == "hold":
            m[i] = m[i + 1] = 0.0
    i = max(j for j in range(n - 1) if xs[j] <= f)
    h = xs[i + 1] - xs[i]; t = (f - xs[i]) / h
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    s = h00 * i + h10 * h * m[i] + h01 * (i + 1) + h11 * h * m[i + 1]
    return i, min(1.0, max(0.0, s - i))


def sample(keys, f, loop=False):
    ks = keys
    if f <= ks[0]["f"]:
        return dict(ks[0])
    if f >= ks[-1]["f"]:
        return dict(ks[-1])
    i, w = _monotone_param(ks, f)
    a, b = ks[i], ks[i + 1]
    u = (f - a["f"]) / (b["f"] - a["f"])
    n = len(ks)
    if loop:
        prev = ks[i - 1] if i > 0 else ks[-2]
        nxt = ks[i + 2] if i + 2 < n else ks[1]
    else:
        prev = ks[max(i - 1, 0)]; nxt = ks[min(i + 2, n - 1)]
    out = {"f": f}
    for ch in a:
        if ch in ("f", "ease"):
            continue
        if ch in FEET:
            pa, pb = V(a[ch][:3]), V(b[ch][:3])
            ws = u * u * (3 - 2 * u) if b["ease"] != "hold" else 0.0
            p = pa.lerp(pb, ws)
            if (pb - pa).xy.length > 0.005:
                p.z += 0.045 * math.sin(math.pi * ws)          # step lift arc
            out[ch] = (p.x, p.y, p.z, a[ch][3] + (b[ch][3] - a[ch][3]) * ws)
        elif b["ease"] == "hold":
            out[ch] = a[ch]
        else:
            out[ch] = _cr(prev[ch], a[ch], b[ch], nxt[ch], w)
    return out


class Rig:
    def __init__(self, arm, kind):
        self.arm, self.kind = arm, kind
        self.rest = lambda b: arm.data.bones[b].matrix_local
        self.sock_rel = {s: self.rest(f"hand_{s}").inverted() @ self.rest(k) for s, k in (("r", "weapon_r"), ("l", "grip_l"))}
        self.deform = [b.name for b in arm.data.bones if b.use_deform]
        self.has_legs = "thigh_l" in arm.data.bones

    def _rot(self, bone, deg):
        pb = self.arm.pose.bones[bone]; pb.rotation_mode = "XYZ"
        pb.rotation_euler = tuple(math.radians(x) for x in deg)

    def apply(self, p):
        a = self.arm
        if self.has_legs:
            pb = a.pose.bones["pelvis"]; pb.location = p["pel_loc"]
            self._rot("pelvis", p["pel_rot"])
            for b, ch in (("spine_01", "sp1"), ("spine_02", "sp2"), ("neck", "neck"), ("head", "head")):
                self._rot(b, p[ch])
        self._rot("spine_03", p["sp3"])
        prot, lift = p["clav"]
        self._rot("clavicle_l", (prot, 0, lift)); self._rot("clavicle_r", (prot, 0, -lift))
        if self.has_legs:
            for s in "lr":
                x, y, z, yaw = p[f"foot_{s}"]
                m = Matrix.Rotation(math.radians(yaw), 4, "Z") @ self.rest(f"foot_{s}").to_3x3().to_4x4()
                m.translation = V((x, y, z))
                H.set_pose_matrix(a, f"ik_foot_{s}", m)
                knee = V((x, y, 0.5)) + (V((0.05, -0.45, 0.0)) if s == "l" else V((-0.12, -0.55, 0.0)))
                H.set_pose_matrix(a, f"pole_knee_{s}", Matrix.Translation(knee))
        blade = V(p["blade"]).normalized()
        e = V(p["edge"]) - blade * V(p["edge"]).dot(blade)
        edge = e.normalized() if e.length > 1e-4 else V((0, 0, -1))
        G_r = V(p["hilt"]); G_l = G_r - blade * 0.14
        for s, G in (("r", G_r), ("l", G_l)):
            H.set_pose_matrix(a, f"ik_hand_{s}", a.matrix_world @ (H.frame_matrix(G, blade, edge) @ self.sock_rel[s].inverted()))
            H.set_pose_matrix(a, f"pole_elbow_{s}", Matrix.Translation(V(p[f"pole_{s}"])))
        for s in "lr":
            a.pose.bones[f"forearm_twist_{s}"].rotation_mode = "XYZ"
            a.pose.bones[f"forearm_twist_{s}"].rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        # drive forearm twist bones from the wrist roll (relative to rest)
        for s in "lr":
            fa = H.bone_world(a, f"forearm_{s}"); hd = H.bone_world(a, f"hand_{s}")
            q_rest = (self.rest(f"forearm_{s}").inverted() @ self.rest(f"hand_{s}")).to_quaternion()
            q_cur = (fa.inverted() @ hd).to_quaternion()
            qd = q_cur @ q_rest.inverted()
            ang = 2 * math.atan2(qd.y, qd.w)
            ang = math.atan2(math.sin(ang), math.cos(ang))
            a.pose.bones[f"forearm_twist_{s}"].rotation_euler = (0, 0.6 * ang, 0)
        bpy.context.view_layer.update()
        return blade, edge, G_r

    # ---- measurements (Blender world)
    def sword_matrix(self):
        return H.bone_world(self.arm, "weapon_r") @ R_SWORD @ Matrix.Translation((0, 0, 0.05))

    def measure(self, blade_len=0.92):
        a = self.arm
        S = self.sword_matrix()
        sec = S @ V((0, 0, -0.19))
        m = {"blade_base": S @ V((0, 0, 0)), "blade_mid": S @ V((0, 0, blade_len / 2)), "blade_tip": S @ V((0, 0, blade_len)),
             "edge_dir": (S.to_3x3() @ V((1, 0, 0))).normalized(),
             "grip_error_mm": (H.bone_world(a, "grip_l").translation - sec).length * 1000,
             "wrist_err_r_mm": (H.bone_world(a, "hand_r").translation - H.bone_world(a, "ik_hand_r").translation).length * 1000,
             "wrist_err_l_mm": (H.bone_world(a, "hand_l").translation - H.bone_world(a, "ik_hand_l").translation).length * 1000}
        for s in "lr":
            u = H.bone_world(a, f"upperarm_{s}").to_3x3().col[1]; f = H.bone_world(a, f"forearm_{s}").to_3x3().col[1]
            m[f"elbow_deg_{s}"] = math.degrees(u.angle(f))
            fa = H.bone_world(a, f"forearm_twist_{s}"); hd = H.bone_world(a, f"hand_{s}")
            q_rest = (self.rest(f"forearm_twist_{s}").inverted() @ self.rest(f"hand_{s}")).to_quaternion()
            qd = (fa.inverted() @ hd).to_quaternion() @ q_rest.inverted()
            ang = 2 * math.atan2(qd.y, qd.w)
            m[f"wrist_residual_twist_deg_{s}"] = math.degrees(math.atan2(math.sin(ang), math.cos(ang)))
        if self.has_legs:
            for s in "lr":
                m[f"foot_{s}"] = H.bone_world(a, f"toe_{s}").translation.copy()
            m["pelvis"] = H.bone_world(a, "pelvis").translation.copy()
        return m

    # ---- baking
    def capture(self):
        a = self.arm
        out = {}
        for b in self.deform:
            pb = a.pose.bones[b]
            ml = a.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL")
            loc, q, sc = ml.decompose()
            out[b] = (tuple(loc), tuple(q))
        return out


def gl(v):
    """Blender Z-up -> glTF Y-up (x, z, -y)."""
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


ELBOW_MAX = 145.0


def solve_reach(rig, p, iters=12, init=None):
    """Apply p; if a hand cannot reach the grip or an elbow over-folds, translate the whole sword (both grips together)
    toward / away from that shoulder until valid. Returns (offset vector applied to the hilt, iterations used)."""
    a = rig.arm
    off = V(init) if init is not None else V((0, 0, 0))
    base = V(p["hilt"])
    for it in range(iters):
        q = dict(p); q["hilt"] = tuple(base + off)
        rig.apply(q); rig.apply(q)
        m = rig.measure()
        moved = False
        for s in "lr":
            sh = H.bone_world(a, f"upperarm_{s}").translation
            target = V(q["hilt"]) if s == "r" else V(q["hilt"]) - V(q["blade"]).normalized() * 0.14
            err = m[f"wrist_err_{s}_mm"]
            if err > 1.5:
                off += (sh - target).normalized() * (err / 1000 + 0.004)
                moved = True
            elif m[f"elbow_deg_{s}"] > ELBOW_MAX and off.length < 0.08:   # capped: never shove the sword far
                off += (target - sh).normalized() * 0.012 * (m[f"elbow_deg_{s}"] - ELBOW_MAX + 2) / 4
                moved = True
        if not moved:
            return off, it
    return off, iters


def bake_clip(rig, name, keys, frames, loop=False):
    ks = resolve(keys)
    corrections = []
    # pass 1: required sword correction per frame; pass 2: temporally smoothed (sigma 2.5 frames, periodic for loops)
    raw = [solve_reach(rig, sample(ks, f, loop))[0] for f in range(frames + 1)]
    sm = []
    for f in range(frames + 1):
        acc, wsum = V((0, 0, 0)), 0.0
        for d in range(-7, 8):
            g = f + d
            if loop:
                g %= frames
            elif g < 0 or g > frames:
                continue
            w = math.exp(-0.5 * (d / 2.5) ** 2)
            acc += raw[g] * w; wsum += w
        sm.append(acc / wsum)
    poses, samples = [], {k: [] for k in ("frames", "blade_base", "blade_mid", "blade_tip", "edge_dir", "grip_error_mm",
                                          "elbow_deg_l", "elbow_deg_r", "wrist_err_l_mm", "wrist_err_r_mm",
                                          "wrist_residual_twist_deg_l", "wrist_residual_twist_deg_r")}
    if rig.has_legs:
        samples.update({"foot_l": [], "foot_r": [], "pelvis": []})
    for f in range(frames + 1):
        p = sample(ks, f, loop)
        off, _ = solve_reach(rig, p, init=sm[f])   # smoothed correction + tiny residual; IK settles over repeated solves
        corrections.append(round(off.length * 1000, 1))
        m = rig.measure()
        poses.append(rig.capture())
        samples["frames"].append(f)
        for k in ("blade_base", "blade_mid", "blade_tip", "edge_dir"):
            samples[k].append(gl(m[k]))
        for k in ("grip_error_mm", "elbow_deg_l", "elbow_deg_r", "wrist_err_l_mm", "wrist_err_r_mm",
                  "wrist_residual_twist_deg_l", "wrist_residual_twist_deg_r"):
            samples[k].append(round(m[k], 2))
        if rig.has_legs:
            for k in ("foot_l", "foot_r", "pelvis"):
                samples[k].append(gl(m[k]))
    samples["reach_correction_mm"] = corrections
    return poses, samples


def write_action(rig, name, poses):
    a = rig.arm
    a.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    a.animation_data.action = act
    for f, pose in enumerate(poses):
        for b, (loc, q) in pose.items():
            pb = a.pose.bones[b]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion(q)
            pb.keyframe_insert("rotation_quaternion", frame=f, group=b)
            if b == "pelvis":
                pb.location = V(loc)
                pb.keyframe_insert("location", frame=f, group=b)
    a.animation_data.action = None
    return act


def mute_constraints(arm, mute=True):
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.enabled = not mute


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
