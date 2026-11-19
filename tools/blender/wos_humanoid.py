"""Will of Steel: reusable humanoid toolkit.

Conventions (Blender space, Z-up, metres). The character faces -Y, so its left side is +X.
glTF export converts this to Y-up with the character facing +Z.
- Bone names: lower_snake_case with _l / _r suffix. Deform bones carry use_deform=True. Controls (ik_*, pole_*)
  and sockets (weapon_r, grip_l) are non-deforming.
- Armour plates are rigid: 100% weight to one bone (or a fixed two-bone blend for flexible lames), then merged into
  per-slot skinned meshes, which keeps draw calls low on mobile. Cloth/body is smooth-skinned by distance to bones.
- Geometry is built for the LEFT side and mirrored to the right, with names swapped _l -> _r.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

V = Vector


# ---------------------------------------------------------------- 2D profiles (x = local lateral, y = local front)

def ellipse(rx, ry, n=16, a0=0.0, a1=2 * math.pi, closed=True, ridge=0.0, ridge_w=0.25, bulge=None):
    """CCW points on an ellipse arc. `ridge` adds a medial crest at the front (angle 90 deg).
    `bulge(a)` -> extra radial scale."""
    pts = []
    count = n if closed else n + 1
    for i in range(count):
        a = a0 + (a1 - a0) * i / n
        k = 1.0 + (bulge(a) if bulge else 0.0)
        x, y = rx * math.cos(a) * k, ry * math.sin(a) * k
        if ridge:
            d = math.atan2(math.sin(a - math.pi / 2), math.cos(a - math.pi / 2))
            y += ridge * math.exp(-(d / ridge_w) ** 2) * (1 if y >= 0 else 0)
        pts.append((x, y))
    return pts


def offset_inward(pts, t, closed):
    """Offset a CCW polyline inward by t (outward normal of CCW traversal is (dy, -dx))."""
    out, n = [], len(pts)
    for i in range(n):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1 = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = dy / L, -dx / L
        out.append((pts[i][0] - nx * t, pts[i][1] - ny * t))
    return out


# ---------------------------------------------------------------- frames along a path

def frames(centers, front_ref):
    """Per-centre orthonormal frames (X lateral, F front, T tangent) with X x F = T."""
    out, n = [], len(centers)
    for i, c in enumerate(centers):
        a = centers[max(i - 1, 0)]; b = centers[min(i + 1, n - 1)]
        T = (b - a).normalized()
        f = V(front_ref) if not callable(front_ref) else V(front_ref(i, T))
        F = (f - T * f.dot(T)).normalized()
        X = F.cross(T).normalized()
        out.append((c, X, F, T))
    return out


def place(fr, pts2d):
    c, X, F, T = fr
    return [c + X * x + F * y for x, y in pts2d]


# ---------------------------------------------------------------- slot builder (one skinned mesh per slot)

class Slot:
    def __init__(self, name, bones, materials):
        self.name = name
        self.bones = bones                       # ordered deform-bone names (vertex group order)
        self.gi = {b: i for i, b in enumerate(bones)}
        self.materials = materials               # list of bpy materials; parts refer by index
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.dl = self.bm.verts.layers.deform.verify()

    # -- low level
    def _verts(self, pts, weights):
        vs = []
        for p in pts:
            v = self.bm.verts.new(p)
            w = weights(p) if callable(weights) else weights
            for b, val in w.items():
                if val > 1e-4:
                    v[self.dl][self.gi[b]] = val
            vs.append(v)
        return vs

    def _quad(self, a, b, c, d, mat, uvs):
        try:
            f = self.bm.faces.new((a, b, c, d))
        except ValueError:
            return None
        f.material_index = mat
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    # -- lofts
    dens = 1   # extra Catmull-Rom rings inserted between each authored ring pair (smooth silhouettes)

    @staticmethod
    def densify(rings, m):
        if m <= 0 or len(rings) < 2:
            return rings
        R = [[V(p) for p in r] for r in rings]
        out = []
        for i in range(len(R) - 1):
            p0, p1, p2, p3 = R[max(i - 1, 0)], R[i], R[i + 1], R[min(i + 2, len(R) - 1)]
            out.append(p1)
            for k in range(1, m + 1):
                t = k / (m + 1)
                t2, t3 = t * t, t * t * t
                out.append([0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                            for a, b, c, d in zip(p0, p1, p2, p3)])
        out.append(R[-1])
        return out

    def loft(self, rings, mat, weights, closed=True, tile=0.5, cap0=False, cap1=False):
        """rings: list of lists of 3D points (equal counts), CCW about the travel direction for outward normals."""
        rings = self.densify(rings, self.dens)
        nR, n = len(rings), len(rings[0])
        # UVs in world metres / tile
        us = [0.0]
        for i in range(1, nR):
            c0 = sum(rings[i - 1], V()) / n; c1 = sum(rings[i], V()) / n
            us.append(us[-1] + (c1 - c0).length / tile)
        vs_uv = [0.0]
        r0 = rings[nR // 2]
        for j in range(1, n + 1):
            vs_uv.append(vs_uv[-1] + (V(r0[j % n]) - V(r0[j - 1])).length / tile)
        verts = [self._verts(r, weights) for r in rings]
        faces = []
        m = n if closed else n - 1
        for i in range(nR - 1):
            for j in range(m):
                j1 = (j + 1) % n
                f = self._quad(verts[i][j], verts[i][j1], verts[i + 1][j1], verts[i + 1][j], mat,
                               ((us[i], vs_uv[j]), (us[i], vs_uv[j + 1]), (us[i + 1], vs_uv[j + 1]), (us[i + 1], vs_uv[j])))
                if f: faces.append(f)
        if cap0 and closed:
            try:
                f = self.bm.faces.new(list(reversed(verts[0]))); f.material_index = mat; faces.append(f)
            except ValueError: pass
        if cap1 and closed:
            try:
                f = self.bm.faces.new(verts[-1]); f.material_index = mat; faces.append(f)
            except ValueError: pass
        return [v for r in verts for v in r], faces, verts

    def shell(self, centers, profiles, front_ref, mat, weights, thickness=0.003, closed=False, tile=0.5,
              cap0=False, cap1=False):
        """Thick armour shell lofted along `centers`. profiles[i] = CCW 2D points (open arc or closed ring)."""
        fr = frames([V(c) for c in centers], front_ref)
        if not closed:
            rings = []
            for f, p in zip(fr, profiles):
                inner = offset_inward(p, thickness, False)
                rings.append(place(f, p + list(reversed(inner))))
            allv, faces, R = self.loft(rings, mat, weights, closed=True, tile=tile)
            k = len(profiles[0])
            for ring, sign in ((R[0], -1), (R[-1], 1)):    # end walls between outer and inner arcs
                outer, inner = ring[:k], list(reversed(ring[k:]))
                for j in range(k - 1):
                    q = (outer[j], outer[j + 1], inner[j + 1], inner[j]) if sign > 0 else (outer[j], inner[j], inner[j + 1], outer[j + 1])
                    f = self._quad(*q, mat, ((0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)))
                    if f: faces.append(f)
            return allv, faces
        outer = [place(f, p) for f, p in zip(fr, profiles)]
        inner = [list(reversed(place(f, offset_inward(p, thickness, True)))) for f, p in zip(fr, profiles)]
        a, fa, RO = self.loft(outer, mat, weights, closed=True, tile=tile, cap0=cap0, cap1=cap1)
        b, fb, RI = ([], [], None) if (cap0 or cap1) else self.loft(inner, mat, weights, closed=True, tile=tile)
        faces = fa + fb
        if RI:
            n = len(RO[0])
            for ro, ri, sign in ((RO[0], RI[0], -1), (RO[-1], RI[-1], 1)):
                ri = list(reversed(ri))
                for j in range(n):
                    j1 = (j + 1) % n
                    q = (ro[j], ro[j1], ri[j1], ri[j]) if sign > 0 else (ro[j], ri[j], ri[j1], ro[j1])
                    f = self._quad(*q, mat, ((0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)))
                    if f: faces.append(f)
        return a + b, faces

    def tube(self, centers, radii, front_ref, mat, weights, n=12, tile=0.5, cap0=True, cap1=True, sq=1.0):
        """Smooth body/cloth tube. radii: list of (rx, ry) or float per centre."""
        fr = frames([V(c) for c in centers], front_ref)
        rings = []
        for f, r in zip(fr, radii):
            rx, ry = (r, r * sq) if isinstance(r, (int, float)) else r
            rings.append(place(f, ellipse(rx, ry, n)))
        a, faces, R = self.loft(rings, mat, weights, closed=True, tile=tile, cap0=cap0, cap1=cap1)
        return a, faces

    def mirror(self, verts, faces, swap):
        """Duplicate geometry mirrored across X=0, faces reversed, vertex groups swapped by `swap` dict of names."""
        idx = {}
        for v in verts:
            nv = self.bm.verts.new((-v.co.x, v.co.y, v.co.z))
            for gi, w in v[self.dl].items():
                nv[self.dl][self.gi[swap.get(self.bones[gi], self.bones[gi])]] = w
            idx[v] = nv
        for f in faces:
            if not f.is_valid:
                continue
            vs = [idx[l.vert] for l in reversed(f.loops) if l.vert in idx]
            if len(vs) != len(f.loops):
                continue
            try:
                nf = self.bm.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = f.material_index
            for nl, ol in zip(nf.loops, reversed(f.loops)):
                nl[self.uv].uv = ol[self.uv].uv

    def finish(self, armature, smooth=True, collection=None):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)   # in-memory vertex merge only
        before = [f.normal.copy() for f in self.bm.faces] if self.bm.faces else []
        self.bm.normal_update()
        before = [f.normal.copy() for f in self.bm.faces]
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)      # make every closed shell face outward
        self.bm.normal_update()
        self.flipped = sum(1 for f, n0 in zip(self.bm.faces, before) if f.normal.dot(n0) < 0)
        self.faces_total = len(self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.materials:
            me.materials.append(m)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        ob = bpy.data.objects.new(self.name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        for b in self.bones:
            ob.vertex_groups.new(name=b)
        ob.parent = armature
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = armature
        return ob


# ---------------------------------------------------------------- distance-based skin weights

def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length, t


def auto_weights(bone_segments, falloff=4.0, keep=3, twist=None):
    """Return weights(p) using inverse-distance^falloff to bone segments. bone_segments: {name: (head, tail)}.
    twist: {parent_bone: (twist_bone, t0, t1)}: shift weight to the twist bone along the parent's length."""
    segs = {k: (V(a), V(b)) for k, (a, b) in bone_segments.items()}

    def w(p):
        p = V(p)
        ds = []
        for k, (a, b) in segs.items():
            d, t = seg_dist(p, a, b)
            ds.append((d, k, t))
        ds.sort()
        dmin = ds[0][0]
        sel = [x for x in ds[:keep] if x[0] < dmin * 1.8 + 0.01]
        raw = {k: 1.0 / (d + 0.004) ** falloff for d, k, _ in sel}
        s = sum(raw.values())
        out = {k: v / s for k, v in raw.items()}
        if twist:
            for d, k, t in sel:
                if k in twist and k in out:
                    tb, t0, t1 = twist[k]
                    x = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
                    share = x * x * (3 - 2 * x)
                    out[tb] = out.get(tb, 0) + out[k] * share
                    out[k] *= (1 - share)
        return out
    return w


# ---------------------------------------------------------------- armature

def build_armature(name, bones, collection=None):
    """bones: list of dicts {name, head, tail, parent, deform, roll_to (vector for bone Z axis) | None, connect}.
    Returns the armature object (rest pose)."""
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    (collection or bpy.context.scene.collection).objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b in bones:
        e = ad.edit_bones.new(b["name"])
        e.head, e.tail = V(b["head"]), V(b["tail"])
        if b.get("roll_to") is not None:
            e.align_roll(V(b["roll_to"]))
        e.use_deform = b.get("deform", True)
        if b.get("parent"):
            e.parent = eb[b["parent"]]
            e.use_connect = b.get("connect", False)
        eb[b["name"]] = e
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def add_ik(arm, chain_tip, target, pole, chain=2, pole_angle=-90.0):
    pb = arm.pose.bones[chain_tip]
    c = pb.constraints.new("IK")
    c.target = arm; c.subtarget = target
    if pole:
        c.pole_target = arm; c.pole_subtarget = pole; c.pole_angle = math.radians(pole_angle)
    c.chain_count = chain
    return c


def copy_rot(arm, bone, target):
    c = arm.pose.bones[bone].constraints.new("COPY_ROTATION")
    c.target = arm; c.subtarget = target
    c.target_space = c.owner_space = "WORLD"
    return c


def hinge_limits(arm, bone, min_deg, max_deg, axis="x"):
    """Hinge joint (elbow/knee): bend only about one local axis within limits; recorded for the manifest."""
    pb = arm.pose.bones[bone]
    for ax in "xyz":
        setattr(pb, f"lock_ik_{ax}", ax != axis)
    setattr(pb, f"use_ik_limit_{axis}", True)
    setattr(pb, f"ik_min_{axis}", math.radians(min_deg))
    setattr(pb, f"ik_max_{axis}", math.radians(max_deg))
    pb["wos_limit"] = f"{axis}:{min_deg}:{max_deg}"


def set_pose_matrix(arm, bone, world_matrix):
    pb = arm.pose.bones[bone]
    pb.matrix = arm.matrix_world.inverted() @ world_matrix
    bpy.context.view_layer.update()


def bone_world(arm, bone):
    return arm.matrix_world @ arm.pose.bones[bone].matrix


def rest_world(arm, bone):
    return arm.matrix_world @ arm.data.bones[bone].matrix_local


def frame_matrix(origin, y_axis, z_hint):
    """Matrix whose local +Y = y_axis and local +Z ~ z_hint (bone convention)."""
    Y = V(y_axis).normalized()
    Z = (V(z_hint) - Y * V(z_hint).dot(Y)).normalized()
    X = Y.cross(Z)
    m = Matrix((X, Y, Z)).transposed().to_4x4()
    m.translation = V(origin)
    return m
