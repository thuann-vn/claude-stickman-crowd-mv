# Stick people for painted-3D shots (a 30 s music Short: one lonely figure in a crowded street).
# Real geometry inside the Blender set (the painted street hides them correctly, perspective is right):
#   limbs   = one mesh of thin 6-sided prisms for everybody, vertices rewritten every frame from mocap joints
#   heads   = spheres with a camera-space 3-tone shade + ink hull; each head takes the colour of the lamps / neon near it
#   shadows = the same limb mesh projected onto the ground from the nearest street lamp or lantern string (night) or along
#             the sun (book street), plus a soft contact blob
#   gaits   = 9 walk clips with their own cadence and stride (Xbot + Mesh2Motion CC0), 5 idles for people standing about;
#             ground speed = each clip's measured stance speed × cadence × size, so feet never slide
#   hero    = lighter head, sad code face, slumped slow walk; standing he breathes, shifts his weight, looks round
#   rain    = thin streaks falling through the night shots
# Lessons: a 2-key pose clip left running shakes the figure (hold it); nobody may shrink or fade inside the picture
# (walkers steer round the lens and off the lens→hero line; the loop wraps only behind the camera or > 30 m away).
# Use (after the set's materials became the projection):  setter = stick.make(globals(), "jp" | "book");  setter(shot id, frame)
import bpy, bmesh, json, math, os, random
import numpy as np
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gait
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))


def _c(a):  # three (x,y,z) → blender (−x, z, y): the figure faces +y
    a = np.array(a, dtype=np.float64); a = a.reshape(len(a), 14, 3)
    return a[:, :, [0, 2, 1]] * np.array([-1.0, 1.0, 1.0])


M2 = json.load(open(os.path.join(HERE, "m2m.json")))
if os.path.exists(os.path.join(HERE, "mocap.json")):   # optional: the studio's own standing/walk clips
    D = json.load(open(os.path.join(HERE, "mocap.json")))
else:                                                   # without it the hero stands with a Mesh2Motion idle
    D = {"walk": M2["walk"]["frames"], "herowalk": M2["walk"]["frames"], "stand": M2["idle-subtle"]["frames"]}
# name → (frames, loop seconds, ground speed m/s at rate 1 and size 1)   (speeds measured from the stance foot)
CL = {"xwalk": (_c(D["walk"]), 0.9667, 1.539), "hero": (_c(D["herowalk"]), 0.9667, 0.841), "herostand": (_c(D["stand"]), 2.5, 0.0)}
for k_, sp_ in (("walk", 0.894), ("walk-relaxed", 1.008), ("walk-female", 1.068), ("walk-formal", 0.882), ("walk-happy", 1.344), ("walk-large", 0.839), ("texting-walk", 0.902), ("walk-carry", 0.767),
                ("idle-subtle", 0), ("idle-a", 0), ("idle-listening", 0), ("idle-talkingphone", 0), ("idle-foldarms", 0)):
    CL[k_] = (_c(M2[k_]["frames"]), M2[k_]["dur"], sp_)
GAITS = [("xwalk", 0.2), ("walk", 0.13), ("walk-relaxed", 0.15), ("walk-female", 0.15), ("walk-formal", 0.08), ("walk-happy", 0.08), ("walk-large", 0.06), ("texting-walk", 0.11), ("walk-carry", 0.04)]
IDLES = ["idle-talkingphone", "idle-listening", "idle-a", "idle-foldarms", "idle-subtle"]
SEG = [(0, 1), (1, 3), (3, 4), (1, 5), (5, 6), (0, 7), (7, 8), (8, 9), (0, 10), (10, 11), (11, 12)]  # back, arms from the neck, legs from the hips, feet
HANDS = [(3, 4), (5, 6)]
FPS = 24
CUT = [0, 4.2, 8.3, 12.3, 16.4, 20.5, 24.3, 30.0]
K = 6


def cyc(arr, ph):
    n = len(arr); x = (ph % 1.0) * n; i = int(x) % n; k = x - int(x)
    return arr[i] * (1 - k) + arr[(i + 1) % n] * k


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


SLOT = {8: 6}          # shot id → lyric slot when it is not id − 1
SUB = 6                # time-lapse: sub-frames rendered per frame (post.py blends them into streaks)
LAPSE = 14.0           # how many times faster the crowd's time runs


def warp(tl):
    """crowd time in the time-lapse: real speed for half a second, then it runs away"""
    n = max(1, int(tl * 120)); h = tl / n
    return sum((1.0 + (LAPSE - 1.0) * ease(((k + 0.5) * h - 0.5) / 0.9)) * h for k in range(n))


# ---------------------------------------------------------------- staging per shot
SHOTS = {
    "book": {
        1: dict(hero=((0.2, 3.1), (0, 1), "walk", 0.28), xw=2.3, yr=(-4.0, 36.0), n=46, bubble=1.15, stand=[(-2.5, 5.2, -1.2), (-2.45, 6.0, -2.0), (2.55, 9.5, 1.5), (2.5, 14.0, 1.7), (-2.6, 17.0, -1.4)]),
        2: dict(hero=((0.15, 16.6), (0, -1), "walk", 0.3), xw=2.2, yr=(5.0, 42.0), n=44, bubble=1.15, stand=[(-2.4, 13.5, -1.3), (-2.45, 14.3, -1.9), (2.3, 18.5, 1.4), (2.35, 23.0, 1.8)]),
    },
    "jp": {
        3: dict(hero=((0.0, 0.3), (0, 1), "walk", 0.28), xw=2.35, yr=(-7.0, 44.0), n=64, bubble=1.15, stand=[(-2.55, 6.5, -1.3), (-2.5, 7.3, -1.9), (2.55, 10.5, 1.5), (2.5, 15.2, 1.2)]),
        4: dict(hero=((-0.75, 15.9), (0.25, -0.97), "stand", 0.26), xw=2.35, yr=(8.0, 46.0), n=58, bubble=1.2, cross=14, stand=[(2.5, 15.4, 1.3), (2.55, 16.2, 2.0), (-2.6, 25.2, -1.4), (2.4, 26.4, 1.6)]),
        5: dict(hero=((0.05, 21.4), (0, 1), "stand", -0.42), xw=2.35, yr=(-6.0, 28.0), n=52, bubble=1.25, cross=8, stand=[(-2.5, 15.6, -1.5), (2.55, 14.8, 1.4), (2.5, 14.0, 2.0)]),
        6: dict(hero=((0.0, 20.6), (0, 1), "stand", 0.3), xw=2.4, yr=(5.0, 46.0), n=66, bubble=1.7, cross=26, stand=[(-2.6, 15.0, -1.4), (2.6, 16.0, 1.5), (-2.6, 25.5, -1.6), (2.55, 27.0, 1.3), (2.6, 27.8, 2.1)]),
        8: dict(hero=((0.05, 22.3), (0, 1), "stand", 0.12), xw=2.35, yr=(0.0, 40.0), n=62, bubble=1.2, cross=10, lapse=True, stand=[]),   # time-lapse ending
        7: dict(hero=((0.0, 31.2), (0, 1), "walk", 0.25), xw=2.35, yr=(24.0, 70.0), n=62, bubble=1.15, stand=[(-2.55, 34.0, -1.4), (-2.5, 34.8, -2.0), (2.55, 38.0, 1.5), (2.5, 44.0, 1.3)]),
    },
}
# lights: (x, y, z, colour, strength). Night: street lamps (warm), lantern strings (red-orange), shop neon (pink left, cyan right)
LAMPS = [(-2.45, 17.3, 4.7), (2.45, 23.7, 4.7), (2.45, -2.0, 4.7), (-2.45, 40.0, 4.7), (2.45, 49.0, 4.7)]
LIGHTS = {
    "jp": [(x, y, z, (1.0, 0.86, 0.6), 1.0) for x, y, z in LAMPS] + [(0.0, y, 3.9, (1.0, 0.42, 0.26), 0.8) for y in (9.5, 13.0, 30.0, 34.0, 41.0, 50.0)]
          + [(-2.9, y, 2.6, (1.0, 0.3, 0.62), 0.55) for y in (2, 12, 28, 38, 48, 58)] + [(2.9, y, 2.6, (0.25, 0.85, 1.0), 0.55) for y in (7, 15, 26, 33, 44, 54)],
    "book": [],
}
LOOK = {  # ink, crowd head (dark, base, rim), hero head (dark, base, rim), blob alpha, cast-shadow colour + alpha, ambient head tint
    "jp": dict(ink="#07070b", crowd=("#23252e", "#3d404c", "#8f95ad"), hero=("#8c8884", "#cfcac4", "#ffd9e6"), blob=0.3, cast=("#05050c", 0.4), amb=(0.16, 0.13, 0.26)),
    "book": dict(ink="#0b0907", crowd=("#33353c", "#4f525b", "#a9acb8"), hero=("#a09a92", "#e6e1d9", "#fff6e6"), blob=0.22, cast=("#3a2a66", 0.36), amb=(0.5, 0.36, 0.2)),
}
SUN = {1: (0.10, -0.80, -0.59), 2: (0.06, -0.90, -0.42)}  # book street: the way the sunlight travels (from the far end toward us, low)


def make(G, loc):
    col, cam, lin = G["col"], G["cam"], G["lin"]
    CODE = G.get("CODE_OBS")
    L = LOOK[loc]
    NMAX = 200   # the hero (index 0) + everybody else

    def emission(name, hexc, alpha=1.0, cull=False):
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
        for n_ in list(nt.nodes): nt.nodes.remove(n_)
        o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = lin(hexc) if isinstance(hexc, str) else hexc
        if alpha < 1.0:
            tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = alpha
            nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs["Surface"])
            try: m.surface_render_method = "BLENDED"
            except Exception: m.blend_method = "BLEND"
        else:
            nt.links.new(e.outputs[0], o.inputs["Surface"])
        m.use_backface_culling = cull
        return m

    def headmat(name, dark, base, rim, vary=0.0):
        """camera-space cel shade (dark crescent left + below, a rim on the right) + the object's colour = the light falling on it"""
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
        for n_ in list(nt.nodes): nt.nodes.remove(n_)
        N = nt.nodes.new; lk = nt.links.new
        o = N("ShaderNodeOutputMaterial"); e = N("ShaderNodeEmission"); geo = N("ShaderNodeNewGeometry"); vt = N("ShaderNodeVectorTransform")
        vt.vector_type = "NORMAL"; vt.convert_from = "WORLD"; vt.convert_to = "CAMERA"; lk(geo.outputs["Normal"], vt.inputs[0])
        sp = N("ShaderNodeSeparateXYZ"); lk(vt.outputs[0], sp.inputs[0]); oi = N("ShaderNodeObjectInfo")
        sock = lambda v_: isinstance(v_, bpy.types.NodeSocket)

        def mth(op, a, b=None):
            n_ = N("ShaderNodeMath"); n_.operation = op
            for k_, v_ in ((0, a), (1, b)):
                if v_ is None: continue
                if sock(v_): lk(v_, n_.inputs[k_])
                else: n_.inputs[k_].default_value = v_
            return n_.outputs[0]

        def d2(cx, cy):
            dx = mth("SUBTRACT", sp.outputs["X"], cx); dy = mth("SUBTRACT", sp.outputs["Y"], cy)
            return mth("ADD", mth("MULTIPLY", dx, dx), mth("MULTIPLY", dy, dy))

        def mix(kind, fac, a, b):
            n_ = N("ShaderNodeMix"); n_.data_type = "RGBA"; n_.blend_type = kind
            for k_, v_ in ((0, fac), (6, a), (7, b)):
                if sock(v_): lk(v_, n_.inputs[k_])
                elif k_ == 0: n_.inputs[k_].default_value = v_
                else: n_.inputs[k_].default_value = tuple(v_)
            return n_.outputs[2]

        lit = mth("LESS_THAN", d2(0.11, 0.10), 0.89 * 0.89)
        rimm = mth("MULTIPLY", mth("MULTIPLY", mth("GREATER_THAN", d2(-0.085, 0.06), 0.93 * 0.93), mth("GREATER_THAN", sp.outputs["X"], 0.12)), lit)
        c = mix("MIX", lit, lin(dark), lin(base))
        if vary > 0:
            fac = mth("ADD", mth("MULTIPLY", oi.outputs["Random"], vary), 1.0 - vary * 0.5); cv = N("ShaderNodeCombineXYZ")
            for k_ in range(3): lk(fac, cv.inputs[k_])
            c = mix("MULTIPLY", 1.0, c, cv.outputs[0])
        tint = oi.outputs["Color"]
        wb = tuple(min(1.0, v_ + 0.3) for v_ in lin(base)[:3]) + (1.0,)
        c = mix("ADD", mth("MULTIPLY", lit, 0.65), c, mix("MULTIPLY", 1.0, tint, wb))   # the lit side takes the lamp's colour
        rimc = mix("ADD", 1.0, mix("MULTIPLY", 1.0, lin(rim), (0.45, 0.45, 0.45, 1)), tint)      # the rim is the light itself
        c = mix("MIX", rimm, c, rimc)
        lk(c, e.inputs["Color"]); lk(e.outputs[0], o.inputs["Surface"])
        return m

    def add(ob):
        col.objects.link(ob); ob.visible_shadow = False
        if CODE is not None: CODE.append(ob)
        return ob

    INK = emission("stick_ink", L["ink"])
    NS = len(SEG) + len(HANDS) + 1       # + the umbrella's shaft
    VF = NS * 2 * K                      # limb vertices of one figure
    faces = []
    for s_ in range(NMAX * NS):
        b0 = s_ * 2 * K
        for k_ in range(K):
            faces.append((b0 + k_, b0 + (k_ + 1) % K, b0 + K + (k_ + 1) % K, b0 + K + k_))
    me = bpy.data.meshes.new("stick_limbs"); me.from_pydata([(0, 0, -5)] * (NMAX * VF), [], faces); me.materials.append(INK)
    limbs = add(bpy.data.objects.new("stick_limbs", me))
    ang = np.arange(K) * (2 * math.pi / K); CA, SA = np.cos(ang), np.sin(ang)
    # cast shadows: the limb mesh again (flattened on the ground) + a disc for each head
    HD = 10
    cfaces = list(faces) + [tuple(NMAX * VF + f * HD + k_ for k_ in range(HD)) for f in range(NMAX)]
    cme = bpy.data.meshes.new("stick_cast"); cme.from_pydata([(0, 0, -5)] * (NMAX * VF + NMAX * HD), [], cfaces); cme.materials.append(emission("stick_castm", L["cast"][0], L["cast"][1]))
    cast = add(bpy.data.objects.new("stick_cast", cme))
    hang = np.arange(HD) * (2 * math.pi / HD)
    # soft contact blob
    SV = 10
    sme = bpy.data.meshes.new("stick_blob")
    sme.from_pydata([(0, 0, -5)] * (NMAX * (SV + 1)), [], [(f * (SV + 1), f * (SV + 1) + 1 + k_, f * (SV + 1) + 1 + (k_ + 1) % SV) for f in range(NMAX) for k_ in range(SV)])
    sme.materials.append(emission("stick_blobm", "#05060a", L["blob"]))
    blob = add(bpy.data.objects.new("stick_blob", sme))
    sang = np.arange(SV) * (2 * math.pi / SV)

    def sphere(name, flip=False):
        m_ = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0)
        for f in bm.faces: f.smooth = True
        if flip: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(m_); bm.free(); return m_
    sph, hullm = sphere("stick_head"), sphere("stick_hull", True)
    sph.materials.append(headmat("stick_crowd_head", *L["crowd"], vary=0.5))
    hero_me = sph.copy(); hero_me.materials.clear(); hero_me.materials.append(headmat("stick_hero_head", *L["hero"]))
    hullm.materials.append(emission("stick_hullm", L["ink"], cull=True))
    heads = [add(bpy.data.objects.new("stick_head%d" % i, hero_me if i == 0 else sph)) for i in range(NMAX)]
    hulls = [add(bpy.data.objects.new("stick_hull%d" % i, hullm)) for i in range(NMAX)]

    # ---- umbrellas (rainy night): an 8-panel canopy per person, colour from the object colour, ink hull; the hero has none
    UMB = loc == "jp"
    def dome(name, flip=False):
        m_ = bpy.data.meshes.new(name); bm = bmesh.new(); top = bm.verts.new((0, 0, 0.40)); r1, r2 = [], []
        for k_ in range(8):
            a_ = k_ * math.pi / 4; r1.append(bm.verts.new((math.cos(a_) * 0.62, math.sin(a_) * 0.62, 0.27))); r2.append(bm.verts.new((math.cos(a_), math.sin(a_), 0.0)))
        for k_ in range(8):
            j_ = (k_ + 1) % 8; bm.faces.new((top, r1[k_], r1[j_])); bm.faces.new((r1[k_], r2[k_], r2[j_], r1[j_]))
        if flip: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(m_); bm.free(); return m_
    def umbmat(name, alpha):
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
        for n_ in list(nt.nodes): nt.nodes.remove(n_)
        N = nt.nodes.new; lk = nt.links.new
        o = N("ShaderNodeOutputMaterial"); e = N("ShaderNodeEmission"); geo = N("ShaderNodeNewGeometry"); oi = N("ShaderNodeObjectInfo"); sp = N("ShaderNodeSeparateXYZ"); lk(geo.outputs["Normal"], sp.inputs[0])
        def mth(op, a, b):
            n_ = N("ShaderNodeMath"); n_.operation = op
            for k_, v_ in ((0, a), (1, b)):
                if isinstance(v_, bpy.types.NodeSocket): lk(v_, n_.inputs[k_])
                else: n_.inputs[k_].default_value = v_
            return n_.outputs[0]
        sh = mth("ADD", mth("ADD", mth("MULTIPLY", sp.outputs["Z"], 0.3), 0.68), mth("MULTIPLY", sp.outputs["X"], 0.14))   # panels differ in tone
        sh = mth("MULTIPLY", sh, mth("SUBTRACT", 1.0, mth("MULTIPLY", geo.outputs["Backfacing"], 0.5)))                    # the underside is darker
        mx = N("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0; lk(oi.outputs["Color"], mx.inputs[6]); cv = N("ShaderNodeCombineXYZ")
        for k_ in range(3): lk(sh, cv.inputs[k_])
        lk(cv.outputs[0], mx.inputs[7]); lk(mx.outputs[2], e.inputs["Color"])
        if alpha < 1.0:
            tr = N("ShaderNodeBsdfTransparent"); ms = N("ShaderNodeMixShader"); ms.inputs[0].default_value = alpha
            lk(tr.outputs[0], ms.inputs[1]); lk(e.outputs[0], ms.inputs[2]); lk(ms.outputs[0], o.inputs["Surface"])
            try: m.surface_render_method = "BLENDED"
            except Exception: m.blend_method = "BLEND"
        else:
            lk(e.outputs[0], o.inputs["Surface"])
        m.use_backface_culling = False
        return m
    umbs, umbhulls = [], []
    if UMB:
        d_op, d_cl, d_hull = dome("stick_umb"), dome("stick_umb_clear"), dome("stick_umb_hull", True)
        d_op.materials.append(umbmat("stick_umbm", 1.0)); d_cl.materials.append(umbmat("stick_umbclear", 0.5)); d_hull.materials.append(emission("stick_umbhullm", L["ink"], cull=True))
        PAL = [(0.02, 0.025, 0.05), (0.02, 0.025, 0.05), (0.55, 0.03, 0.05), (0.8, 0.45, 0.04), (0.03, 0.27, 0.25), (0.8, 0.2, 0.38), (0.75, 0.75, 0.82), (0.14, 0.08, 0.42), (0.04, 0.1, 0.4)]
        UCOL = []
        for i in range(NMAX):
            ru = random.Random(7000 + i); clear = ru.random() < 0.36
            UCOL.append(((0.86, 0.9, 1.0) if clear else ru.choice(PAL), ru.uniform(0.47, 0.58), ru.uniform(-0.12, 0.12), ru.uniform(-0.1, 0.1)))
            umbs.append(add(bpy.data.objects.new("stick_umb%d" % i, d_cl if clear else d_op))); umbhulls.append(add(bpy.data.objects.new("stick_umbh%d" % i, d_hull)))

    # ---- the hero's face: flat ink shapes on the sphere, looking +y (az = sideways, el = up)
    def onball(az, el, r=1.012):
        return (math.sin(az) * math.cos(el) * r, math.cos(az) * math.cos(el) * r, math.sin(el) * r)

    def facemesh(name, polys):
        v, f = [], []
        for pts in polys:
            b0 = len(v); v += [onball(a, e) for a, e in pts]; f.append(tuple(range(b0, b0 + len(pts))))
        m_ = bpy.data.meshes.new(name); m_.from_pydata(v, [], f); m_.materials.append(INK); return add(bpy.data.objects.new(name, m_))

    def stroke(p, w, n=10):
        (a0, e0), (a1, e1), (a2, e2) = p; top, bot = [], []
        for i in range(n + 1):
            t = i / n; ca, ce = 2 * a1 - (a0 + a2) / 2, 2 * e1 - (e0 + e2) / 2
            a = (1 - t) ** 2 * a0 + 2 * t * (1 - t) * ca + t * t * a2; e = (1 - t) ** 2 * e0 + 2 * t * (1 - t) * ce + t * t * e2
            ww = w * (0.55 + 0.45 * math.sin(math.pi * t)); top.append((a, e + ww / 2)); bot.append((a, e - ww / 2))
        return top + bot[::-1]
    brows = [stroke([(s * 0.5, 0.33), (s * 0.3, 0.42), (s * 0.12, 0.47)], 0.07) for s in (-1, 1)]
    mouth = [stroke([(-0.11, -0.47), (0.0, -0.44), (0.11, -0.47)], 0.05)]
    eyes_open, eyes_shut = [], []
    for s in (-1, 1):
        ca, ce = s * 0.3, 0.0
        eyes_open.append([(ca + 0.09 * math.cos(t), min(ce + 0.045, ce + 0.115 * math.sin(t))) for t in [i * 2 * math.pi / 20 for i in range(20)]])
        eyes_open.append(stroke([(ca - 0.13, ce + 0.05), (ca, ce + 0.055), (ca + 0.13, ce + 0.05)], 0.045))
        eyes_shut.append(stroke([(ca - 0.13, ce + 0.02), (ca, ce - 0.03), (ca + 0.13, ce + 0.02)], 0.05))
    face_open = facemesh("stick_face_open", brows + mouth + eyes_open)
    face_shut = facemesh("stick_face_shut", brows + mouth + eyes_shut)

    # ---- rain (night shots): thin pale streaks, turned to the camera
    NR = 360 if loc == "jp" else 0
    rain = None
    if NR:
        rme = bpy.data.meshes.new("stick_rain"); rme.from_pydata([(0, 0, -5)] * (NR * 4), [], [(i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 3) for i in range(NR)])
        rme.materials.append(emission("stick_rainm", "#cfe0ff", 0.3)); rain = add(bpy.data.objects.new("stick_rain", rme))
        rr_ = np.random.default_rng(11); RU = rr_.random((NR, 4))  # sideways, depth, start height, speed variation
        rco = np.zeros((NR * 4, 3)); RS = np.array([0.07, 0.0, -1.0]); RS /= np.linalg.norm(RS)

    co = np.zeros((NMAX * VF, 3)); cco = np.zeros((NMAX * VF + NMAX * HD, 3)); sco = np.zeros((NMAX * (SV + 1), 3))
    REF = np.array([0.31, 0.47, 0.83])
    LS = LIGHTS[loc]
    LP = np.array([l[:3] for l in LS]) if LS else np.zeros((0, 3)); LC = np.array([l[3] for l in LS]) if LS else np.zeros((0, 3)); LW = np.array([l[4] for l in LS]) if LS else np.zeros(0)
    AMB = np.array(L["amb"])

    # ---- the cast of each shot (fixed for the shot; positions are pure functions of time)
    CAST = {}
    names, wts = [g[0] for g in GAITS], [g[1] for g in GAITS]
    RNG = {}; CX0 = {}; DENS = 2.7 if loc == "jp" else 2.1   # people per metre of street

    def build(sid, S, y0, y1, nn):
        rr = random.Random(100 + sid); people = []
        while len(people) < nn:
            clip = rr.choices(names, wts)[0]; rate = rr.uniform(0.92, 1.1); sc = rr.uniform(0.88, 1.05)
            g_ = gait.spec(rr.choices(("normal", "stroll", "brisk"), (0.55, 0.27, 0.18))[0], rr)
            p = dict(kind="walk", clip=clip, x=rr.uniform(-S["xw"], S["xw"]), y=rr.uniform(y0, y1), d=rr.choice((1, -1)), rate=rate, sc=sc, ph=rr.random(), axis=1, g=g_, v=g_["v"] * sc, phone=rr.random() < 0.15)
            people.append(p)
            if rr.random() < 0.3 and len(people) < nn and clip not in ("texting-walk", "walk-carry"):  # a couple: two abreast, same pace
                people.append(dict(p, x=p["x"] + (0.95 if loc == "jp" else 0.56) * (1 if p["x"] < 0 else -1), ph=p["ph"] + 0.5))
        for _ in range(int(S.get("cross", 0) * 1.6)):
            clip = rr.choices(names, wts)[0]
            g_ = gait.spec(rr.choices(("normal", "stroll", "brisk"), (0.55, 0.27, 0.18))[0], rr); sc = rr.uniform(0.9, 1.05)
            people.append(dict(kind="walk", clip=clip, x=rr.uniform(18.9, 22.2), y=rr.uniform(-32.0, 32.0), d=rr.choice((1, -1)), rate=1.0, sc=sc, ph=rr.random(), axis=0, g=g_, v=g_["v"] * sc, phone=False))
        for j, (sx, sy, syaw) in enumerate(S.get("stand", ())):  # people standing about at the edges: on the phone, chatting, waiting
            people.append(dict(kind="stand", clip=IDLES[(j + sid) % len(IDLES)], x=sx, y=sy, yaw=syaw, sc=rr.uniform(0.9, 1.04), ph=rr.random(), phone=(j % 2 == 0)))
        return people

    GONE = np.array([0.0, 0.0, -9.0])
    pme = bpy.data.meshes.new("stick_phone"); pf = []
    for i in range(NMAX):
        b = i * 8; pf += [(b, b + 1, b + 3, b + 2), (b + 4, b + 6, b + 7, b + 5), (b, b + 4, b + 5, b + 1), (b + 2, b + 3, b + 7, b + 6), (b, b + 2, b + 6, b + 4), (b + 1, b + 5, b + 7, b + 3)]
    pme.from_pydata([(0, 0, -5)] * (NMAX * 8), [], pf); pme.materials.append(emission("stick_phonem", "#b9dcff" if loc == "jp" else "#1b1c22"))   # glows at night
    phones = add(bpy.data.objects.new("stick_phone", pme)); pco = np.zeros((NMAX * 8, 3))
    HERO_G = gait.spec("hero")

    def place(i, J, x, y, yaw, sc, rad, hr, show, sun, umb=False, phone=False):
        """joints J (14,3) of a figure facing +y → world; writes limbs, head, hull, blob and cast shadow of figure i"""
        b0 = i * VF; hb = NMAX * VF + i * HD
        if show <= 0.01:
            co[b0:b0 + VF] = GONE; cco[b0:b0 + VF] = GONE; cco[hb:hb + HD] = GONE; sco[i * (SV + 1):(i + 1) * (SV + 1)] = GONE
            heads[i].scale = hulls[i].scale = (0, 0, 0)
            if umbs: umbs[i].scale = umbhulls[i].scale = (0, 0, 0)
            pco[i * 8:i * 8 + 8] = GONE
            return None
        if phone:   # on a call: the left hand holds the phone to the ear, elbow out in front
            J = J.copy(); sl = 1.0 if J[3, 0] >= J[1, 0] else -1.0; hk = hr / max(sc, 1e-6)
            J[3] = J[1] + np.array([sl * 0.27, 0.13, -0.2]); J[4] = J[1] + np.array([sl * (hk + 0.035), 0.03, hk * 0.62])
        if umb:   # the right arm holds the umbrella up in front of the chest
            J = J.copy(); sx = 1.0 if J[5, 0] >= J[1, 0] else -1.0
            J[5] = J[1] + np.array([sx * 0.25, 0.06, -0.40]); J[6] = J[1] + np.array([sx * 0.17, 0.21, -0.22])
        c, s = math.cos(yaw), math.sin(yaw)
        Wd = np.empty_like(J); Wd[:, 0] = x + (J[:, 0] * c - J[:, 1] * s) * sc; Wd[:, 1] = y + (J[:, 0] * s + J[:, 1] * c) * sc; Wd[:, 2] = J[:, 2] * sc
        nk = Wd[2] - Wd[1]; nk /= max(1e-6, np.linalg.norm(nk)); hc = Wd[1] + nk * (hr * 0.86)   # the neck line runs into the head
        if umb:
            ucol, uR, utx, uty = UCOL[i]; uR *= sc
            uc = np.array([Wd[6][0] * 0.5 + hc[0] * 0.5, Wd[6][1] * 0.5 + hc[1] * 0.5, hc[2] + hr + 0.07 * sc]); utop = uc + np.array([0, 0, 0.4 * uR])
            for o_, k_ in ((umbs[i], 1.0), (umbhulls[i], 1.045)):
                o_.location = uc; o_.scale = (uR * k_ * show,) * 3; o_.rotation_euler = (utx, uty, yaw)
        elif umbs:
            umbs[i].scale = umbhulls[i].scale = (0, 0, 0)
        sa, sb = (Wd[6] - np.array([0, 0, 0.09 * sc]), utop) if umb else (Wd[6], Wd[6] + np.array([0, 0, 1e-4]))
        A = np.array([Wd[a] for a, b in SEG] + [Wd[b] for a, b in HANDS] + [sa]); Bp = np.array([Wd[b] for a, b in SEG] + [Wd[b] + (Wd[b] - Wd[a]) / max(1e-6, np.linalg.norm(Wd[b] - Wd[a])) * 0.075 * sc for a, b in HANDS] + [sb])
        dv = Bp - A; ln = np.linalg.norm(dv, axis=1, keepdims=True); dv = dv / np.maximum(ln, 1e-6)
        u = np.cross(dv, REF); u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-6); v = np.cross(dv, u)
        r = np.full((NS, 1, 1), rad * show); r[len(SEG):len(SEG) + 2] *= 1.9; r[-1] *= 0.8 if umb else 0.0
        ring = (u[:, None, :] * CA[None, :, None] + v[:, None, :] * SA[None, :, None]) * r
        P = np.concatenate([A[:, None, :] + ring, Bp[:, None, :] + ring], axis=1).reshape(-1, 3)
        co[b0:b0 + VF] = P
        if phone:   # the phone: a thin slab against the ear, standing up along the cheek
            pc = Wd[4] + np.array([0, 0, 0.055 * sc]); fw_ = np.array([-s, c, 0.0]); lat = np.array([c, s, 0.0]); upv = np.array([0.0, 0.0, 1.0]) * 0.985 + fw_ * 0.17
            k8 = 0
            for a_ in (-1, 1):
                for b_ in (-1, 1):
                    for c_ in (-1, 1):
                        pco[i * 8 + k8] = pc + upv * (a_ * 0.075 * sc * show) + fw_ * (b_ * 0.036 * sc * show) + lat * (c_ * 0.008 * sc * show); k8 += 1
        else:
            pco[i * 8:i * 8 + 8] = GONE
        nk = Wd[2] - Wd[1]; nk /= max(1e-6, np.linalg.norm(nk)); hc = Wd[1] + nk * (hr * 0.86)   # the neck line runs into the head
        heads[i].location = hc; heads[i].scale = (hr * show,) * 3; hulls[i].location = hc; hulls[i].scale = (hr * 1.075 * show,) * 3
        q0 = i * (SV + 1); sco[q0] = (Wd[0][0], Wd[0][1], 0.045); sco[q0 + 1:q0 + 1 + SV, 0] = Wd[0][0] + np.cos(sang) * 0.3 * sc * show; sco[q0 + 1:q0 + 1 + SV, 1] = Wd[0][1] + np.sin(sang) * 0.23 * sc * show; sco[q0 + 1:q0 + 1 + SV, 2] = 0.045
        # ---- light on the head + the cast shadow
        base = np.array([Wd[0][0], Wd[0][1], 0.05]); hring = hc[None, :] + np.stack([np.cos(hang), np.zeros(HD), np.sin(hang)], 1) * hr
        if umb: hring = uc[None, :] + np.stack([np.cos(hang), np.sin(hang), np.zeros(HD)], 1) * uR   # the canopy's round shadow
        Q = None
        if sun is not None:
            tint = AMB
            sd = np.array(sun); Q = P + sd[None, :] * ((P[:, 2:3] - 0.05) / -sd[2]); Hq = hring + sd[None, :] * ((hring[:, 2:3] - 0.05) / -sd[2])
        elif len(LP):
            dl = LP - hc[None, :]; dist = np.linalg.norm(dl, axis=1); w = LW / (1.0 + (dist / 2.6) ** 2)
            tint = AMB + (LC * w[:, None]).sum(0) * 1.5
            near = np.where(LP[:, 2] > 3.5, np.hypot(LP[:, 0] - hc[0], LP[:, 1] - hc[1]), 1e9); j = int(near.argmin())
            if near[j] < 11.0:   # the nearest overhead lamp / lantern string throws his shadow
                Lp = LP[j]; turn = np.array([hc[1] - Lp[1], -(hc[0] - Lp[0]), 0.0]); turn /= max(1e-6, np.linalg.norm(turn))  # head disc faces the lamp
                if not umb: hring = hc[None, :] + (turn[None, :] * np.cos(hang)[:, None] + np.array([0, 0, 1.0])[None, :] * np.sin(hang)[:, None]) * hr
                Q = Lp[None, :] + (P - Lp[None, :]) * ((Lp[2] - 0.05) / np.maximum(Lp[2] - P[:, 2:3], 0.4)); Hq = Lp[None, :] + (hring - Lp[None, :]) * ((Lp[2] - 0.05) / np.maximum(Lp[2] - hring[:, 2:3], 0.4))
                far_ = np.linalg.norm(Hq.mean(0)[:2] - base[:2]); f_ = ease((11.0 - near[j]) / 4.0)
                if far_ > 3.4: f_ *= 3.4 / far_   # a far lamp would throw the shadow across the whole street: keep it short
                if f_ < 1.0: Q = base[None, :] + (Q - base[None, :]) * f_; Hq = base[None, :] + (Hq - base[None, :]) * f_
        else:
            tint = AMB
        if Q is None:
            cco[b0:b0 + VF] = GONE; cco[hb:hb + HD] = GONE
        else:
            Q[:, 2] = 0.05; Hq[:, 2] = 0.05; cco[b0:b0 + VF] = Q; cco[hb:hb + HD] = Hq
        t_ = tint / max(1.0, float(tint.max())); heads[i].color = (float(t_[0]), float(t_[1]), float(t_[2]), 1.0)
        if umb:
            uc_ = np.minimum(1.0, np.array(ucol) * (0.5 + 0.9 * t_) + 0.05 * t_); umbs[i].color = (float(uc_[0]), float(uc_[1]), float(uc_[2]), 1.0)
        return hc

    def setter(sid, i):
        on = sid in SHOTS[loc]
        for ob in [limbs, cast, blob, phones, face_open, face_shut] + heads + hulls + umbs + umbhulls + ([rain] if rain else []):
            ob.hide_render = not on
        if not on:
            return
        S = SHOTS[loc][sid]; lapse = S.get("lapse", False); slot = SLOT.get(sid, sid - 1); dur = CUT[slot + 1] - CUT[slot]
        tl = (i / SUB if lapse else i) / FPS + int(os.environ.get("STICK_OFF", "0")) / FPS; t = CUT[slot] + tl  # STICK_OFF: test one frame at another time
        tc = CUT[slot] + (warp(tl) if lapse else tl)   # the crowd's clock
        if lapse:   # the render camera turns inside the wide painting: from him up to the sky (a pure turn, so the painting holds)
            k_ = ease((tl - 1.0) / (dur - 1.5)); pit = math.radians(2.0 + 36.0 * k_)
            cam.rotation_euler = (math.pi / 2 + pit, 0.0, math.pi + math.radians(1.2)); cam.data.lens = 28.0 + 3.0 * (1 - k_)
            bpy.context.view_layer.update()
        sun = SUN.get(sid) if loc == "book" else None
        (hx, hy), (dx, dy), mode, pitch = S["hero"]
        dn = math.hypot(dx, dy); dx, dy = dx / dn, dy / dn
        yaw = math.atan2(-dx, dy); lookyaw = 0.0
        if mode == "walk":
            dist = HERO_G["v"] * tl; hx, hy = hx + dx * dist, hy + dy * dist; J = gait.pose(dist + 0.2, HERO_G)
        else:
            arr, T, _ = CL["herostand"]; J = cyc(arr, t / T).copy()
            # a standing person is never still: breathing, a slow shift of weight from foot to foot, the head drifting round
            br = math.sin(2 * math.pi * 0.27 * t); sway = 0.034 * math.sin(2 * math.pi * t / 6.4 + 0.7) + 0.012 * math.sin(2 * math.pi * t / 2.9)
            up = [1, 2, 3, 4, 5, 6, 13]
            J[up, 2] += 0.007 * br; J[up, 1] += 0.004 * br
            J[[0], 0] += sway; J[up, 0] += sway * 0.62; J[[7, 10], 0] += sway * 0.45
            lookyaw = 0.32 * math.sin(2 * math.pi * t / 5.3 + 1.1) * ease((tl - 0.3) / 1.2)
        hc = place(0, J, hx, hy, yaw, 1.0, 0.0125, 0.172, 1.0, sun)
        blink = any(b <= t < b + 0.17 for b in (2.6, 6.4, 10.1, 14.2, 18.9, 22.8, 27.2))
        M_ = Matrix.Translation(Vector(hc)) @ Matrix.Rotation(yaw + lookyaw, 4, "Z") @ Matrix.Rotation(-pitch, 4, "X") @ Matrix.Scale(0.172, 4)
        face_open.matrix_world = M_; face_shut.matrix_world = M_; face_open.hide_render = blink; face_shut.hide_render = not blink
        cx, cy, cz = cam.location; low = cz < 4.0
        fw = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1)); fl = math.hypot(fw.x, fw.y) or 1.0; fwd_x, fwd_y = fw.x / fl, fw.y / fl
        if sid not in CAST:   # the street is filled from behind the camera to ~50 m ahead, so the loop never wraps in view
            a0, a1 = S["yr"]
            if fwd_y >= 0: a0, a1 = min(a0, cy - 6.0), max(a1, cy + 50.0)
            else: a0, a1 = min(a0, cy - 50.0), max(a1, cy + 6.0)
            RNG[sid] = (a0, a1); CX0[sid] = cx
            CAST[sid] = build(sid, S, a0, a1, min(int((a1 - a0) * DENS), NMAX - 2 - int(S.get("cross", 0) * 1.6) - len(S.get("stand", ()))))
            # Every walker keeps ONE straight lane for the whole shot. Whoever would walk through the hero's empty circle, pass
            # close to the lens or stand between the lens and him gets his lane moved aside once, here, before the shot starts
            # (steering during the shot made people dash sideways).
            y0, y1 = RNG[sid]; span = y1 - y0; LWd = 0.95 if UMB else 0.65; CWd = 2.3 if UMB else 1.25; Rb = S["bubble"] * (1.3 if UMB else 1.0); Rc = 1.25 if UMB else 1.0
            if lapse: CWd, LWd = 1.1, 0.75   # in the time-lapse people streak past the lens: that is the look
            (hx0, hy0), (ddx, ddy), mode0, _p = S["hero"]; dn0 = math.hypot(ddx, ddy); ddx, ddy = ddx / dn0, ddy / dn0
            keep = []
            for p in CAST[sid]:
                if p["kind"] != "walk": keep.append(p); continue
                iv = []
                for k_ in range(int(dur / 0.1) + 3):
                    tr = k_ * 0.1; tt = CUT[slot] + (warp(tr) if lapse else tr)
                    dh = HERO_G["v"] * tr if mode0 == "walk" else 0.0; hxx, hyy = hx0 + ddx * dh, hy0 + ddy * dh
                    if p["axis"] == 1:
                        py = y0 + ((p["y"] - y0 + p["d"] * p["v"] * tt) % span)
                        if abs(py - hyy) < Rb * 1.5: iv.append((hxx - Rb, hxx + Rb))
                        if low and abs(py - cy) < 4.0: iv.append((cx - CWd, cx + CWd))
                        if low and abs(hyy - cy) > 0.5:
                            q = (py - cy) / (hyy - cy)
                            if -0.15 < q < 1.1:
                                xc = cx + (hxx - cx) * max(0.0, min(1.0, q)); iv.append((xc - LWd, xc + LWd))
                    else:
                        px = -32.0 + ((p["y"] + 32.0 + p["d"] * p["v"] * tt) % 64.0)
                        if abs(px - hxx) < Rc * 1.5: iv.append((hyy - Rc, hyy + Rc))
                lo_, hi_ = (-2.95, 2.95) if p["axis"] == 1 else (18.6, 22.5)
                ok = [c_ for c_ in [p["x"]] + [a_ - 0.01 for a_, b_ in iv] + [b_ + 0.01 for a_, b_ in iv] if lo_ <= c_ <= hi_ and all(not (a_ < c_ < b_) for a_, b_ in iv)]
                if ok: p["x"] = min(ok, key=lambda c_: abs(c_ - p["x"])); keep.append(p)
            print("@@cast", sid, len(CAST[sid]), "kept", len(keep), RNG[sid]); CAST[sid] = keep
        y0, y1 = RNG[sid]; span = y1 - y0
        for k, p in enumerate(CAST[sid]):
            n = k + 1; arr, T, v0 = CL[p["clip"]]
            if p["kind"] == "stand":
                place(n, cyc(arr, tc / T + p["ph"]), p["x"], p["y"], p["yaw"], p["sc"], 0.0115, 0.166 * p["sc"], 1.0, sun, UMB, p["phone"]); continue
            v = p["v"]; Jw = gait.pose(v * tc / p["sc"] + p["ph"] * p["g"]["stride"], p["g"])
            if p["axis"] == 1:
                u_ = ((p["y"] - y0 + p["d"] * v * tc) % span); py = y0 + u_; px = p["x"]; pyaw = 0.0 if p["d"] > 0 else math.pi
                edge = min(u_, span - u_)
            else:
                u_ = ((p["y"] + 32.0 + p["d"] * v * tc) % 64.0); px = -32.0 + u_; py = p["x"]; pyaw = -math.pi / 2 if p["d"] > 0 else math.pi / 2
                edge = min(u_, 64.0 - u_)
            show = ease(edge / 1.2)   # only where the loop wraps: behind the camera or ~50 m away
            place(n, Jw, px, py, pyaw, p["sc"], 0.0115, 0.166 * p["sc"], show, sun, UMB, p["phone"])
        for n in range(len(CAST[sid]) + 1, NMAX):
            place(n, CL["xwalk"][0][0], 0, 0, 0, 1, 0.01, 0.16, 0.0, sun)
        me.vertices.foreach_set("co", co.ravel()); me.update()
        cme.vertices.foreach_set("co", cco.ravel()); cme.update()
        pme.vertices.foreach_set("co", pco.ravel()); pme.update()
        sme.vertices.foreach_set("co", sco.ravel()); sme.update()
        if rain:  # a box of rain in front of the camera, each streak a thin quad turned to the lens, falling ~9 m/s
            side = np.array([fwd_y, -fwd_x, 0.0]); fwd = np.array([fwd_x, fwd_y, 0.0])
            depth = 1.9 + RU[:, 1] * 26.0
            cen = np.array([cx, cy, 0.0])[None, :] + fwd[None, :] * depth[:, None] + side[None, :] * ((RU[:, 0] - 0.5) * (4.0 + depth * 0.75))[:, None]
            cen[:, 2] = (RU[:, 2] * 10.0 - (8.5 + RU[:, 3] * 2.0) * t) % 10.0
            view = cen - np.array([cx, cy, cz])[None, :]; wv = np.cross(np.tile(RS, (NR, 1)), view); wv /= np.maximum(np.linalg.norm(wv, axis=1, keepdims=True), 1e-6)
            hw = (0.006 + 0.0006 * depth)[:, None] * wv; hl = RS[None, :] * (0.22 + 0.1 * RU[:, 3])[:, None]
            rco[0::4] = cen - hl - hw; rco[1::4] = cen - hl + hw; rco[2::4] = cen + hl + hw; rco[3::4] = cen + hl - hw
            rain.data.vertices.foreach_set("co", rco.ravel()); rain.data.update()

    return setter
