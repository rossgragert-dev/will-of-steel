"""First-person view scoring shared by the guard/parry searches and animation QA.

Rasterises meshes into a coarse portrait grid (36x64) from a camera with vertical FOV, so we can measure how much of
the opponent William's arms hide, and whether blade/hilt are on screen. Pure numpy; no rendering.
"""
import bpy, math
import numpy as np
from mathutils import Vector as V, Matrix

GW, GH = 36, 64
_cu, _cv = np.meshgrid((np.arange(GW) + 0.5) / GW, (np.arange(GH) + 0.5) / GH)
CELLS = np.stack([_cu.ravel(), _cv.ravel()], -1)


class View:
    def __init__(self, cam_obj, fov_y_deg=61.0, aspect=720 / 1280):
        self.cam = cam_obj
        self.ty = math.tan(math.radians(fov_y_deg) / 2)
        self.tx = self.ty * aspect

    def project(self, P):
        Mi = np.array(self.cam.matrix_world.inverted())
        Pv = P @ Mi[:3, :3].T + Mi[:3, 3]
        d = -Pv[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = 0.5 + 0.5 * (Pv[:, 0] / d) / self.tx
            v = 0.5 + 0.5 * (Pv[:, 1] / d) / self.ty
        return np.stack([u, v], -1), d

    def raster(self, objs):
        dg = bpy.context.evaluated_depsgraph_get()
        mask = np.zeros(GW * GH, bool)
        for o in objs:
            eo = o.evaluated_get(dg); me = eo.to_mesh()
            co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            Mw = np.array(eo.matrix_world); co = co @ Mw[:3, :3].T + Mw[:3, 3]
            me.calc_loop_triangles()
            tri = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
            eo.to_mesh_clear()
            uv, d = self.project(co); tri = tri.reshape(-1, 3)
            T = uv[tri[(d[tri] > 0.05).all(1)]]
            if not len(T):
                continue
            lo, hi = T.min(1), T.max(1)
            T = T[(hi[:, 0] > 0) & (lo[:, 0] < 1) & (hi[:, 1] > 0) & (lo[:, 1] < 1)]
            e0 = T[:, 1] - T[:, 0]; e1 = T[:, 2] - T[:, 0]
            T = T[np.abs(e0[:, 0] * e1[:, 1] - e0[:, 1] * e1[:, 0]) > 1e-10]
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

    def in_frame(self, P, margin=0.0):
        uv, d = self.project(np.asarray(P, float).reshape(-1, 3))
        return (d > 0.05) & (uv[:, 0] > margin) & (uv[:, 0] < 1 - margin) & (uv[:, 1] > margin) & (uv[:, 1] < 1 - margin)
