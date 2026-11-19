"""Will of Steel: original procedural PBR texture and material library (numpy-generated, no third-party images).

Every material is glTF-compatible: Principled BSDF with Base Color / Roughness image textures and an optional
Normal Map node. Textures are generated deterministically from fixed seeds and saved as new PNG files.
"""
import bpy, numpy as np
import common as C

_cache = {}


def _blur(a, k):
    """Periodic (tileable) Gaussian blur via FFT; k ~ sigma in pixels. k=0 returns the input."""
    if k <= 0:
        return a
    H, W = a.shape
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.fftfreq(W)[None, :]
    g = np.exp(-2 * (np.pi * k) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def _noise(rng, S, octaves=((1, .5), (3, .8), (8, 1.2))):
    n = np.zeros((S, S))
    for k, amp in octaves:
        n += _blur(rng.normal(0, 1, (S, S)), k) * amp
    return n / (np.std(n) + 1e-6)


def _normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.concatenate([n * 0.5 + 0.5, np.ones(h.shape + (1,))], -1)


def _rgba(gray_or_rgb):
    a = np.asarray(gray_or_rgb, dtype=np.float32)
    if a.ndim == 2:
        a = np.stack([a, a, a], -1)
    return np.concatenate([a, np.ones(a.shape[:2] + (1,), np.float32)], -1)


def _img(name, rgba, noncolor, outdir):
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    if noncolor:   # must precede the pixel write: changing colour space regenerates (clears) a generated image
        img.colorspace_settings.name = "Non-Color"
    data = np.ascontiguousarray(rgba, dtype=np.float32).ravel()
    img.pixels.foreach_set(data)
    check = np.empty(len(data), dtype=np.float32); img.pixels.foreach_get(check)
    if abs(float(check[0::4].mean()) - float(data[0::4].mean())) > 0.02:
        raise RuntimeError(f"texture {name} lost its pixels before saving")
    C.save_image(img, f"{outdir}/{name}.png")
    return img


# ---------------- texture generators ----------------

def steel_worn(rng, S=1024):
    """Hand-finished armour steel: hammer-planished low-frequency variation, polishing streaks, fine scratches,
    darker oxidised grime in low areas. Returns (basecolor, roughness, height)."""
    plan = _noise(rng, S, ((6, 1.0), (16, 1.0)))
    streak = np.repeat(_blur(rng.normal(0, 1, (S, 1)), 2), S, 1) * 0.6 + _blur(rng.normal(0, 1, (S, S)), 1) * 0.15
    scratch = np.zeros((S, S))
    for _ in range(900):
        x0, y0, L = rng.integers(0, S), rng.integers(0, S), rng.integers(10, 90)
        ang = rng.uniform(0, np.pi)
        xs = (x0 + np.arange(L) * np.cos(ang)).astype(int) % S
        ys = (y0 + np.arange(L) * np.sin(ang)).astype(int) % S
        scratch[ys, xs] += rng.uniform(0.4, 1.0)
    scratch = np.clip(_blur(scratch, 0) , 0, 1)
    grime = np.clip(_noise(rng, S, ((10, 0.7), (3, 0.5))) * 0.35 - 0.05, 0, 1) ** 2   # fine, sparse oxidation
    pits = (rng.random((S, S)) > 0.9985).astype(float)
    pits = np.clip(_blur(pits, 1) * 6, 0, 1)
    base = 0.50 + 0.010 * plan + 0.010 * streak + 0.05 * scratch - 0.12 * grime - 0.20 * pits
    col = np.stack([base * 0.99, base * 0.98, base * 0.96], -1)
    rough = np.clip(0.33 + 0.025 * plan + 0.03 * streak + 0.18 * grime + 0.08 * scratch + 0.3 * pits, 0.24, 0.85)   # satin, not chrome
    return col, rough, plan * 0.08 + scratch * 0.15 - pits


def cloth_quilted(rng, S=512, tint=(0.36, 0.30, 0.24), lines=6):
    """Linen/wool gambeson: woven grain plus quilting channels (vertical, along the limb)."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    weave = (np.sin(xx * S * np.pi * 0.5) * np.sin(yy * S * np.pi * 0.5)) * 0.5
    grain = _noise(rng, S, ((1, .6), (4, .6)))
    seam = np.abs(((xx * lines) % 1) - 0.5) * 2           # 0 at seam centre
    puff = np.clip(seam, 0, 1) ** 0.5                       # padded channels between stitch lines
    height = puff * 1.0 + weave * 0.08 + grain * 0.04
    shade = 0.80 + 0.20 * puff + 0.04 * grain
    col = np.stack([shade * tint[0], shade * tint[1], shade * tint[2]], -1)
    rough = np.clip(0.86 + 0.05 * grain, 0.7, 0.98)
    return col, rough, height


def mail_rings(rng, S=512, rings=16):
    """Riveted mail: staggered interlinked rings. Gaps are dark; ring tops are bright, slightly oiled."""
    yy, xx = np.mgrid[0:S, 0:S] / S * rings
    h = np.zeros((S, S))
    for ox, oy in ((0, 0), (0.5, 0.5)):
        cx = (xx + ox) % 1 - 0.5
        cy = ((yy + oy) % 1 - 0.5) * 1.15
        r = np.sqrt(cx ** 2 + cy ** 2)
        h = np.maximum(h, np.clip(1 - np.abs(r - 0.36) / 0.1, 0, 1))
    h = h ** 0.7
    grain = _noise(rng, S, ((2, 1.0),)) * 0.05
    base = 0.08 + 0.42 * h + grain
    col = np.stack([base * 0.95, base * 0.93, base * 0.90], -1)
    rough = np.clip(0.75 - 0.35 * h + grain, 0.3, 0.9)
    return col, rough, h


def leather(rng, S=512, tint=(0.30, 0.17, 0.09)):
    grain = _noise(rng, S, ((1, 0.7), (3, 0.6), (10, 0.5)))
    cracks = np.clip(np.abs(_noise(rng, S, ((2, 1.0),))) < 0.08, 0, 1) * 1.0
    shade = 0.85 + 0.08 * grain - 0.15 * cracks
    col = np.stack([shade * tint[0], shade * tint[1], shade * tint[2]], -1)
    rough = np.clip(0.62 + 0.08 * grain + 0.1 * cracks, 0.4, 0.92)
    return col, rough, grain * 0.3 - cracks * 0.5


# ---------------- materials ----------------

def make(name, kind, outdir, seed=1415, metal=0.0, normal_strength=2.0, tint=None, lines=6):
    key = (name, outdir)
    if key in _cache:
        return _cache[key]
    rng = np.random.default_rng(seed)
    if kind == "steel":
        col, rough, h = steel_worn(rng); metal = 1.0; normal_strength = 0.5
    elif kind == "cloth":
        col, rough, h = cloth_quilted(rng, tint=tint or (0.36, 0.30, 0.24), lines=lines)
    elif kind == "mail":
        col, rough, h = mail_rings(rng); metal = 1.0; normal_strength = 6.0
    elif kind == "leather":
        col, rough, h = leather(rng, tint=tint or (0.30, 0.17, 0.09))
    else:
        raise ValueError(kind)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = metal
    bc = nt.nodes.new("ShaderNodeTexImage"); bc.image = _img(f"{name}_basecolor", _rgba(col), False, outdir)
    rg = nt.nodes.new("ShaderNodeTexImage"); rg.image = _img(f"{name}_roughness", _rgba(rough), True, outdir)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(rg.outputs["Color"], bsdf.inputs["Roughness"])
    # Steel gets no normal map: diag_shading.py (v003) showed it caused sawtooth artifacts on the lofted plates,
    # and polished plate reads through roughness/colour variation anyway (one texture fewer on mobile).
    if kind != "steel":
        nm = nt.nodes.new("ShaderNodeTexImage"); nm.image = _img(f"{name}_normal", _normal_from_height(h, normal_strength), True, outdir)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    _cache[key] = m
    return m


def flat(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m
