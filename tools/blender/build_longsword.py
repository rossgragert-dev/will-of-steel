"""Will of Steel v0.4.0: original longsword, type XVa blade with XVIIIb-style hilt proportions.

Run (headless):
  blender -b --factory-startup --python tools/blender/build_longsword.py -- v001

Attachment convention, Blender space (Z-up); in parentheses, glTF/Three.js space (Y-up):
  origin   = centre of the crossguard, where the blade base meets the hilt
  +Z (+Y)  = towards the tip
  +X (+X)  = true (leading) edge
  ±Y (∓Z)  = blade flats
  Hands: hand_primary sits just below the cross, hand_secondary near the pommel; grip axis = -Z.
Units: metres. All outputs are new versioned files; existing files are never overwritten.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import common as C
import numpy as np

VER = (C.args() or ["v001"])[0]
NAME = f"longsword_xva_{VER}"

# ---------------- dimensions (m) ----------------
BLADE_L = 0.920
BLADE_W0, BLADE_W_MID, BLADE_W_TIP = 0.050, 0.034, 0.016   # at 0, 0.5, 0.92 of length, then the point
BLADE_T0, BLADE_T_TIP = 0.0078, 0.0030                     # distal taper
CROSS_HALF = 0.122
GRIP_L = 0.235
POMMEL_R, POMMEL_T = 0.029, 0.024


def loft(name, rings, cap_start=True, cap_end=True, uv_u=None):
    """Connect consecutive rings of equal vertex count with quads. Returns the object."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    uv = bm.loops.layers.uv.new("UVMap")
    for i in range(len(vs) - 1):
        for j in range(n):
            a, b = vs[i][j], vs[i][(j + 1) % n]
            c, d = vs[i + 1][(j + 1) % n], vs[i + 1][j]
            if a is d:
                continue
            f = bm.faces.new((a, b, c, d))
            u0 = uv_u[i] if uv_u else i / (len(vs) - 1)
            u1 = uv_u[i + 1] if uv_u else (i + 1) / (len(vs) - 1)
            for loop, (u, v) in zip(f.loops, ((u0, j / n), (u0, (j + 1) / n), (u1, (j + 1) / n), (u1, j / n))):
                loop[uv].uv = (u, v)
    if cap_start:
        bm.faces.new(list(reversed(vs[0])))
    if cap_end:
        bm.faces.new(vs[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)  # merges coincident mesh vertices in memory, not files
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def lerp(a, b, t):
    return a + (b - a) * t


def blade():
    rings, us = [], []
    N = 28
    for i in range(N + 1):
        s = i / N
        z = s * BLADE_L
        if s <= 0.5:
            w = lerp(BLADE_W0, BLADE_W_MID, s / 0.5)
        elif s <= 0.92:
            w = lerp(BLADE_W_MID, BLADE_W_TIP, (s - 0.5) / 0.42)
        else:  # acute, slightly convex point
            k = (s - 0.92) / 0.08
            w = BLADE_W_TIP * (1 - k) ** 0.8
        t = lerp(BLADE_T0, BLADE_T_TIP, s ** 0.9) * (1 if s < 0.97 else max(0.05, (1 - s) / 0.03))
        hw, ht = max(w / 2, 1e-5), max(t / 2, 1e-5)
        # flattened diamond, secondary edge bevel, and a shallow fuller on the forte (fades out by 45% length)
        e = 0.82
        fw = 0.22 * hw                                        # fuller half-width
        flat_at = lambda x: ht * 0.35 + (ht - ht * 0.35) * (1 - x / (hw * e))  # diamond surface height at |x|
        depth = 0.45 * ht * max(0.0, min(1.0, (0.45 - s) / 0.12)) * min(1.0, s / 0.035) if s < 0.45 else 0.0
        fy = flat_at(fw)
        cy = ht - depth
        up = [(hw, 0), (hw * e, ht * 0.35), (fw, fy), (0, cy), (-fw, fy), (-hw * e, ht * 0.35)]
        dn = [(-hw, 0), (-hw * e, -ht * 0.35), (-fw, -fy), (0, -cy), (fw, -fy), (hw * e, -ht * 0.35)]
        rings.append([(x, y, z) for x, y in up + dn])
        us.append(s)
    # close the point on a single vertex
    rings[-1] = [(0, 0, BLADE_L)] * 12
    ob = loft("blade", rings, cap_start=True, cap_end=False, uv_u=us)
    return ob


def crossguard():
    rings, N = [], 40
    for i in range(N + 1):
        x = lerp(-CROSS_HALF, CROSS_HALF, i / N)
        a = abs(x) / CROSS_HALF
        sm = lambda t: t * t * (3 - 2 * t)                     # smoothstep: no kinks
        blk = 1 - sm(min(a / 0.30, 1))                          # central block (écusson) weight; covers grip ±0.017 m
        tm = sm(max(0, (a - 0.80) / 0.20))                      # flared terminal weight
        h = 0.0115 + 0.0115 * blk + 0.0055 * tm
        d = 0.0110 + 0.0320 * blk + 0.0030 * tm                # block deep enough to enclose the oval grip
        z0 = -h * (0.55 + 0.40 * blk)                           # block extends down over the chappe
        # gentle downward drop toward the terminals (forged, not ruler-straight)
        drop = -0.006 * a ** 2
        rings.append([(x, -d / 2, z0 + drop), (x, d / 2, z0 + drop), (x, d / 2, z0 + h + drop), (x, -d / 2, z0 + h + drop)])
    ob = loft("crossguard", rings)
    return ob


def grip():
    rings, N, seg = [], 30, 14
    for i in range(N + 1):
        s = i / N
        z = -0.011 - s * (GRIP_L - 0.001)   # top tucked inside the crossguard block
        r = 0.0148 - 0.0022 * math.sin(math.pi * s) + 0.0016 * s     # waisted, swelling to the pommel
        if abs(s - 0.12) < 0.02 or abs(s - 0.88) < 0.02:              # leather-bound cord risers
            r += 0.0012
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            ring.append((r * 1.08 * math.cos(a), r * 0.92 * math.sin(a), z))  # oval: indexes the edge
        rings.append(ring)
    return loft("grip", rings)


def pommel():
    """Wheel pommel: a disc whose axis runs along Y (faces aligned with the blade flats), with a raised central boss
    on each face and a small tang peen at the bottom."""
    z0 = -0.012 - GRIP_L
    R, T = POMMEL_R, POMMEL_T
    zc = z0 - R + 0.002          # wheel centre; top rim sits just into the grip end
    prof = [(0.0001, -T / 2 - 0.003), (0.011, -T / 2 - 0.003), (0.013, -T / 2 - 0.0005), (R * 0.80, -T / 2 + 0.0015),
            (R * 0.97, -T / 2 + 0.005), (R, -T / 2 + 0.008), (R, T / 2 - 0.008), (R * 0.97, T / 2 - 0.005),
            (R * 0.80, T / 2 - 0.0015), (0.013, T / 2 + 0.0005), (0.011, T / 2 + 0.003), (0.0001, T / 2 + 0.003)]
    seg, rings = 32, []
    for r, y in prof:
        rings.append([(r * math.cos(2 * math.pi * j / seg), y, zc + r * math.sin(2 * math.pi * j / seg)) for j in range(seg)])
    wheel = loft("pommel", rings, cap_start=False, cap_end=False)
    # tang peen: short tapered stub below the wheel
    pr = [[(rr * math.cos(2 * math.pi * j / 10), rr * math.sin(2 * math.pi * j / 10), zz) for j in range(10)]
          for rr, zz in ((0.006, zc - R + 0.003), (0.0055, zc - R - 0.004), (0.003, zc - R - 0.0065))]
    peen = loft("pommel_peen", pr, cap_start=False)
    peen.parent = wheel
    peen.location = (0, 0, 0)
    return wheel


# ---------------- textures (generated, original) ----------------
rng = np.random.default_rng(1404)


def tex(name, w, h, rgba):
    img = bpy.data.images.new(name, w, h, alpha=True)
    if "roughness" in name:   # must precede the pixel write (changing colour space clears a generated image)
        img.colorspace_settings.name = "Non-Color"
    data = np.ascontiguousarray(rgba, dtype=np.float32).ravel()
    img.pixels.foreach_set(data)
    check = np.empty(len(data), dtype=np.float32); img.pixels.foreach_get(check)
    if abs(float(check[0::4].mean()) - float(data[0::4].mean())) > 0.02:
        raise RuntimeError(f"texture {name} lost its pixels")
    return img


def blade_textures():
    W, H = 1024, 128   # u = along blade, v = around section
    u = np.linspace(0, 1, W)[None, :]
    v = np.linspace(0, 1, H)[:, None]
    # Lengthwise grinding streaks: variation across v, smoothed along u
    streak = rng.normal(0, 1, (H, 1)) * 0.5 + rng.normal(0, 1, (H, W // 64)).repeat(64, 1)[:, :W] * 0.15
    streak = np.repeat(streak[:, :1], W, 1) * 0.7 + streak * 0.3
    rough = 0.40 + 0.045 * streak          # satin (hand-finished) rather than mirror polish
    # sparse fine scratches (short diagonal-ish lines)
    for _ in range(260):
        x0, y0 = rng.integers(0, W), rng.integers(0, H)
        L = rng.integers(8, 60)
        dy = rng.uniform(-0.25, 0.25)
        for k in range(L):
            x, y = (x0 + k) % W, int(y0 + k * dy) % H
            rough[y, x] += rng.uniform(0.06, 0.14)
    # edge sharpening bands: secondary bevel brighter/smoother (v ≈ 0, 0.5, 1)
    edge = np.exp(-((np.minimum(v, np.abs(v - 0.5)) % 0.5) / 0.03) ** 2)
    edge = np.maximum(edge, np.exp(-((1 - v) / 0.03) ** 2))
    rough = rough - 0.08 * edge
    # mild dulling and grime near the cross (handling)
    rough += 0.10 * np.exp(-u / 0.06)
    rough = np.clip(rough, 0.26, 0.75)
    base = 0.60 + 0.025 * streak - 0.08 * np.exp(-u / 0.05) + 0.03 * edge
    col = np.stack([base * 0.98, base * 0.98, base * 1.0, np.ones_like(base)], -1)
    rgh = np.stack([rough, rough, rough, np.ones_like(rough)], -1)
    return tex(f"{NAME}_blade_basecolor", W, H, col), tex(f"{NAME}_blade_roughness", W, H, rgh)


def leather_texture():
    S = 256
    n = rng.normal(0, 1, (S, S))
    # cheap multi-octave smoothing via box blur in numpy
    def blur(a, k):
        return sum(np.roll(np.roll(a, i, 0), j, 1) for i in range(-k, k + 1) for j in range(-k, k + 1)) / (2 * k + 1) ** 2
    grain = blur(n, 1) * 0.6 + blur(n, 4) * 1.4
    # diagonal wrap seams (spiral binding)
    yy, xx = np.mgrid[0:S, 0:S] / S
    seam = (np.abs(((xx * 3 + yy * 8) % 1) - 0.5) < 0.025).astype(float)
    b = 0.16 + 0.03 * grain - 0.05 * seam
    col = np.stack([b * 1.0, b * 0.62, b * 0.38, np.ones_like(b)], -1)
    r = np.clip(0.62 + 0.06 * grain + 0.1 * seam, 0.4, 0.9)
    return tex(f"{NAME}_leather_basecolor", S, S, col), tex(f"{NAME}_leather_roughness", S, S, np.stack([r, r, r, np.ones_like(r)], -1))


def pbr(name, base=None, rough=None, base_rgb=(0.5, 0.5, 0.5), rough_v=0.4, metal=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True   # closed meshes: export single-sided (cheaper on mobile)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Base Color"].default_value = (*base_rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough_v
    if base:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = base
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if rough:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = rough   # already Non-Color (set in tex())
        nt.links.new(t.outputs["Color"], bsdf.inputs["Roughness"])
    return m


def marker(name, loc, parent, **props):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS" if not props else "SPHERE"
    e.empty_display_size = 0.02
    e.location = loc
    e.parent = parent
    for k, v in props.items():
        e[k] = v
    bpy.context.scene.collection.objects.link(e)
    return e


def build():
    scene = C.empty_scene()
    root = bpy.data.objects.new(NAME, None)
    root.empty_display_type = "PLAIN_AXES"
    scene.collection.objects.link(root)
    root["wos_asset"] = NAME
    root["wos_convention"] = "origin=cross centre; +Y(glTF)=tip; +X=true edge; metres"

    parts = {"blade": blade(), "crossguard": crossguard(), "grip": grip(), "pommel": pommel()}
    bc, br = blade_textures()
    lc, lr = leather_texture()
    steel = pbr("wos_blade_steel", bc, br)
    hilt_steel = pbr("wos_hilt_steel", base_rgb=(0.36, 0.35, 0.34), rough_v=0.48)
    leather = pbr("wos_grip_leather", lc, lr, metal=0.0, rough_v=0.7)
    for k, ob in parts.items():
        ob.parent = root
        ob.data.materials.append({"blade": steel, "grip": leather}.get(k, hilt_steel))
        for ch in ob.children:
            if ch.type == "MESH" and not ch.data.materials:
                ch.data.materials.append(hilt_steel)
        if k == "blade":
            for p in ob.data.polygons:
                p.use_smooth = False
        else:
            ob.data.shade_smooth() if hasattr(ob.data, "shade_smooth") else None

    # ---- named markers (exported as glTF nodes) ----
    marker("hand_primary", (0, 0, -0.050), root)
    marker("hand_secondary", (0, 0, -0.190), root)
    marker("blade_base", (0, 0, 0.0), root)
    marker("blade_mid", (0, 0, BLADE_L * 0.5), root)
    marker("blade_tip", (0, 0, BLADE_L), root)
    marker("edge_true", (BLADE_W_MID / 2, 0, BLADE_L * 0.5), root)
    marker("edge_false", (-BLADE_W_MID / 2, 0, BLADE_L * 0.5), root)
    # ---- simplified collision volumes (metadata on empties; consumers build their own shapes) ----
    marker("col_blade", (0, 0, 0.0), root, wos_collider="capsule", wos_to="blade_tip", wos_radius=0.012)
    marker("col_cross", (0, 0, -0.004), root, wos_collider="box", wos_half=[CROSS_HALF, 0.006, 0.010])
    marker("col_hilt", (0, 0, -0.012), root, wos_collider="capsule", wos_to_offset=[0, 0, -GRIP_L - 2 * POMMEL_R], wos_radius=0.03)

    # ---- save textures, export GLB ----
    tdir = f"assets/v0.4.0/textures/{NAME}"
    for img in (bc, br, lc, lr):
        C.save_image(img, f"{tdir}/{img.name}.png")
    glb = C.export_glb(f"assets/v0.4.0/weapons/{NAME}.glb", export_image_format="AUTO")

    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
               for o in bpy.data.objects if o.type == "MESH")

    # ---- preview renders (helpers created after export, so they are never in the GLB) ----
    mid = (BLADE_L - GRIP_L - 2 * POMMEL_R) / 2
    prev, eng = C.preview_stage(scene, target=(0, 0, mid), radius=1.0)
    side = C.look_cam(prev, "cam_side", (0, -3, mid), (0, 0, mid), ortho=1.32)
    edge = C.look_cam(prev, "cam_edge", (3, 0, mid), (0, 0, mid), ortho=1.32)
    hilt = C.look_cam(prev, "cam_hilt", (0.30, -0.40, 0.10), (0, 0, -0.08), lens=60)
    tip = C.look_cam(prev, "cam_forte_three_quarter", (-0.30, -0.80, 0.16), (0, 0, 0.22), lens=50)
    out = f"previews/v0.4.0/{NAME}"
    renders = [C.render_still(scene, side, f"{out}_side.png", (600, 1200)),
               C.render_still(scene, edge, f"{out}_edge.png", (600, 1200)),
               C.render_still(scene, hilt, f"{out}_hilt.png", (1000, 1000)),
               C.render_still(scene, tip, f"{out}_three_quarter.png", (1000, 1000))]

    blend = C.save_blend(f"source/blender/weapons/{NAME}.blend")
    report = {"asset": NAME, "engine": eng, "triangles": tris, "glb": os.path.relpath(glb, C.REPO),
              "glb_sha256": C.sha256(glb), "glb_bytes": os.path.getsize(glb), "blend": os.path.relpath(blend, C.REPO),
              "renders": [os.path.relpath(r, C.REPO) for r in renders],
              "dimensions_m": {"blade": BLADE_L, "grip": GRIP_L, "cross_span": CROSS_HALF * 2,
                               "overall": round(BLADE_L + 0.012 + GRIP_L + 2 * POMMEL_R + 0.0045, 4)},
              "blender": bpy.app.version_string}
    C.write_json(f"assets/v0.4.0/weapons/{NAME}.report.json", report)
    print("WOS_REPORT", report)


build()
