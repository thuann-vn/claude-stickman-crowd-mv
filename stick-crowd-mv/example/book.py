# Đường sách: a tree-lined book street, day and night. Run headless:
#   blender -b --factory-startup -P street.py -- --stills      (middle frame of every shot)
#   blender -b --factory-startup -P street.py -- --shots 1,2    (full frames of some shots)
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILLS = "--stills" in argv
PROJ = "--proj" in argv
ONLY = [int(x) for x in argv[argv.index("--shots") + 1].split(",")] if "--shots" in argv else None
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
OUT2 = OUT  # tall shots of the music Short
random.seed(7)
R = random.uniform

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


MATS = {}


def M(name, hexc=None, rough=0.85, emit=0.0, emit_hex=None):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = lin(hexc)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.25
    if emit or emit_hex:
        b.inputs["Emission Color"].default_value = lin(emit_hex or hexc)
        b.inputs["Emission Strength"].default_value = emit
    MATS[name] = m
    return m


def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


class B:
    """many primitives in one mesh, one material slot per colour"""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _place(self, verts, m, size, loc, rot, smooth):
        bm = self.bm
        bmesh.ops.scale(bm, vec=size, verts=verts)
        if rot != (0, 0, 0):
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot[0], 3, "X"), verts=verts)
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot[1], 3, "Y"), verts=verts)
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot[2], 3, "Z"), verts=verts)
        bmesh.ops.translate(bm, vec=loc, verts=verts)
        i = self.mi(m)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = i
            f.smooth = smooth

    def box(self, m, size, loc, rot=(0, 0, 0)):
        self._place(bmesh.ops.create_cube(self.bm, size=1)["verts"], m, size, loc, rot, False)

    def ball(self, m, size, loc, rot=(0, 0, 0), sub=2):
        self._place(bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=0.5)["verts"], m, size, loc, rot, True)

    def cyl(self, m, size, loc, rot=(0, 0, 0), top=1.0, seg=12):
        v = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=0.5, radius2=0.5 * top, depth=1)["verts"]
        self._place(v, m, size, loc, rot, True)

    def done(self, name, parent=None):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        return ob


FONT = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def text(body, loc, size, m, rz=0.0, tilt=0.0):
    c = bpy.data.curves.new("T_" + body[:8], "FONT")
    c.body, c.font, c.size = body, FONT, size
    c.align_x, c.align_y = "CENTER", "CENTER"
    c.extrude = 0.004
    c.space_line = 1.05
    c.materials.append(m)
    ob = bpy.data.objects.new("T_" + body[:8], c)
    ob.location = loc
    ob.rotation_euler = (math.radians(90) + tilt, 0, rz)
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------- palette
STONE = bpy.data.materials.new("stone")
STONE.use_nodes = True
nt = STONE.node_tree
bs = bsdf(STONE)
br = nt.nodes.new("ShaderNodeTexBrick")
tc = nt.nodes.new("ShaderNodeTexCoord")
nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 0.6
mixn = nt.nodes.new("ShaderNodeMix")
mixn.data_type = "RGBA"
mixn.blend_type = "MULTIPLY"
mixn.inputs["Factor"].default_value = 0.35
br.inputs["Color1"].default_value = lin("#d9bfa2")
br.inputs["Color2"].default_value = lin("#bfa088")
br.inputs["Mortar"].default_value = lin("#8a6f62")
br.inputs["Scale"].default_value = 1.6
br.inputs["Mortar Size"].default_value = 0.012
nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
nt.links.new(br.outputs["Color"], mixn.inputs["A"])
nt.links.new(nz.outputs["Color"], mixn.inputs["B"])
nt.links.new(mixn.outputs["Result"], bs.inputs["Base Color"])
bs.inputs["Roughness"].default_value = 0.8

WALLS = ["#f2c14e", "#f6dfa8", "#e9a0a0", "#8fc7c1", "#f0b25a", "#e8d3b0", "#d9896b"]
BOOKS = ["#d9413a", "#2f6fb5", "#f0b429", "#2e9b6a", "#8e4bb0", "#ef7d2d", "#f3ead7", "#1f3a5f", "#c2255c"]
LANT = ["#ff4b3a", "#ff9a2e", "#3fd0c0", "#ff6fa5", "#ffd84a", "#ff4b3a", "#7fe07a"]
book_m = [M("book" + c, c, 0.6) for c in BOOKS]
lant_m = [M("lant%d" % i, c, 0.5, 0.8) for i, c in enumerate(LANT)]
WOOD = M("wood", "#8a5a34")
DARKWOOD = M("darkwood", "#4a2f22")
TRUNK = M("trunk", "#5a3b2e", 0.95)
LEAF = [M("leaf0", "#3f8f3a", 0.9), M("leaf1", "#5fae3f", 0.9), M("leaf2", "#2f7440", 0.9), M("leaf3", "#8cc24a", 0.9)]
WHITE = M("white", "#fbf4e6")
GLASS = M("glass", "#33506b", 0.25, 0.0, "#ffd58a")
WINLIT = M("winlit", "#49627a", 0.3, 0.0, "#ffcf7a")
SHUT = M("shutter", "#2f7d6b")
ROOF = M("roof", "#b5553a")
METAL = M("metal", "#2b2b33", 0.5)
BULB = M("bulb", "#fff1c9", 0.4, 0.5, "#ffdf9a")
TXT_W = M("txtw", "#ffffff", 0.6, 0.6)
TXT_Y = M("txty", "#ffd23f", 0.6, 0.7)
RED = M("plast_red", "#e5372e", 0.35)
BLUE = M("plast_blue", "#2f62c9", 0.35)
SIGNBLUE = M("signblue", "#1f5fae", 0.6, 0.15)
SIGNRED = M("signred", "#c9302c", 0.6, 0.15)
BOARD = M("board", "#1f4a3a", 0.8)
CLOTH = [M("cloth0", "#2ba6a0", 0.9), M("cloth1", "#e9c24a", 0.9), M("cloth2", "#d95a4a", 0.9)]
AWN = [M("awn0", "#d94f3d", 0.9), M("awn1", "#2f8f83", 0.9), M("awn2", "#f0b429", 0.9), M("awn3", "#3b6fb5", 0.9)]
PLANTER = M("planter", "#c9632e")
CURB = M("curb", "#b8a79c")
SHOPDARK = M("shopdark", "#3a2c28", 0.9, 0.0, "#ffc978")

L = 84.0  # street length (y)

# ---------------------------------------------------------------- ground
g = B()
g.box(STONE, (9, L + 30, 0.2), (0, L / 2, -0.1))
for s in (-1, 1):
    g.box(CURB, (3.2, L + 30, 0.34), (s * 6.1, L / 2, -0.03))
g.box(M("far", "#d8c7b0"), (60, 2, 0.2), (0, L + 16, -0.1))
g.done("ground")

# ---------------------------------------------------------------- buildings
bd = B()
ab = B()
signs = []
for s in (-1, 1):
    y = -6.0
    k = 0
    while y < L + 8:
        w = R(6.5, 9.5)
        h = R(8.5, 13.5)
        wall = M("wall" + WALLS[(k + (s > 0) * 3) % len(WALLS)], WALLS[(k + (s > 0) * 3) % len(WALLS)], 0.9)
        x0 = s * 7.7
        cy = y + w / 2
        bd.box(wall, (8, w - 0.08, h), (s * 11.7, cy, h / 2))
        bd.box(WHITE, (8.3, w, 0.35), (s * 11.7, cy, h + 0.1))
        bd.box(ROOF, (8.0, w - 0.3, 0.5), (s * 11.9, cy, h + 0.5))
        bd.box(WHITE, (0.16, w, 0.22), (x0, cy, 3.85))
        # shop front on the ground floor
        bd.box(SHOPDARK, (0.12, w - 1.6, 2.7), (x0, cy, 1.5))
        aw = AWN[k % 4]
        bd.box(aw, (1.9, w - 1.0, 0.1), (x0 - s * 0.9, cy, 3.05), (0, s * 0.32, 0))
        for q in range(int((w - 1.0) / 0.45)):
            ab.ball(BULB, (0.1, 0.1, 0.1), (x0 - s * 1.82, y + 0.6 + q * 0.45, 2.72), sub=1)
        sm = SIGNBLUE if k % 2 else SIGNRED
        bd.box(sm, (0.12, w - 2.4, 0.62), (x0 - s * 0.08, cy, 3.6))
        signs.append((s, x0 - s * 0.16, cy, k))
        # windows
        n = max(2, int(w // 2.4))
        for fl in range(int((h - 4.6) // 2.6) + 1):
            z = 5.6 + fl * 2.6
            if z + 1.1 > h:
                break
            for i in range(n):
                wy = y + (i + 0.5) * w / n
                lit = WINLIT if random.random() < 0.55 else GLASS
                bd.box(WHITE, (0.14, 1.26, 1.86), (x0, wy, z))
                bd.box(lit, (0.18, 1.02, 1.62), (x0, wy, z))
                bd.box(WHITE, (0.2, 0.06, 1.62), (x0, wy, z))
                for e in (-1, 1):
                    bd.box(SHUT, (0.1, 0.42, 1.7), (x0 - s * 0.1, wy + e * 0.86, z))
                bd.box(WHITE, (0.5, 1.5, 0.1), (x0 - s * 0.15, wy, z - 0.98))
        y += w
        k += 1
bd.done("buildings")
ab.done("awnbulbs")
NAMES = ["NHÀ SÁCH", "SÁCH CŨ", "CÀ PHÊ SÁCH", "TRUYỆN TRANH", "SÁCH THIẾU NHI", "VĂN HỌC", "SÁCH NGOẠI VĂN", "TIỆM SÁCH NHỎ"]
for s, x, y, k in signs:
    if -2 < y < 60:
        text(NAMES[(k * 3 + (s > 0)) % len(NAMES)], (x, y, 3.6), 0.34, TXT_W, rz=math.radians(90 if s < 0 else -90))

# ---------------------------------------------------------------- trees
# old street trees: flared root, thick crooked trunk arching over the street, forking limbs, foliage in many leafy clumps
tr = B()
lf = B()
BARK2 = M("bark2", "#4a3024", 0.95)
TREE_Y = [3 + i * 7.0 for i in range(12)]
rt = random.Random(11)
RT = rt.uniform


def limb(b, m, p1, p2, r1, r2, seg=8):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    e = d.to_track_quat("Z", "Y").to_euler("XYZ")
    b.cyl(m, (r1 * 2, r1 * 2, d.length * 1.04), (p1 + p2) / 2, (e.x, e.y, e.z), top=r2 / r1, seg=seg)
    b.ball(m, (r2 * 2, r2 * 2, r2 * 2), p2, sub=1)


def clump(c, r, n):
    for _ in range(n):
        q = RT(0.55, 1.0) * r
        o = Vector((RT(-1, 1), RT(-1, 1), RT(-0.45, 0.7))) * r * 0.9
        lf.ball(LEAF[rt.choice([0, 0, 1, 1, 2, 3])], (q * 1.25, q * 1.25, q * RT(0.7, 0.95)), c + o, (RT(0, 3), RT(0, 3), 0), sub=2)


for s in (-1, 1):
    for i, ty in enumerate(TREE_Y):
        # the same random draws as the first version, so everything built after the trees stays where it was
        ty += R(-0.6, 0.6) + (1.8 if s > 0 else 0)
        x = s * 4.05
        lean = -s * R(0.10, 0.2)
        ht = R(5.6, 6.6)
        for a in (-0.9, 0.2, 1.0):
            R(2.4, 3.3)
        for j in range(17):
            R(1.3, 2.5), R(0.55, 0.8), R(-1.6, 3.4), R(-3.4, 3.4), R(1.0, 3.6), R(0, 3), R(0, 3)
            random.randrange(4)
        # trunk: 5 pieces along a bent line that arches in over the street
        r0 = RT(0.3, 0.38)
        pts = [Vector((x, ty, 0))]
        for k in range(1, 6):
            h = ht * k / 5
            pts.append(Vector((x + math.sin(lean) * h * (0.7 + 0.5 * k / 5) + RT(-0.12, 0.12), ty + RT(-0.16, 0.16), h)))
        tr.cyl(TRUNK, (r0 * 3.6, r0 * 3.6, 0.55), (x, ty, 0.2), top=0.5, seg=10)  # root flare
        for k in range(5):
            ra, rb = r0 * (1 - 0.09 * k), r0 * (1 - 0.09 * (k + 1))
            limb(tr, TRUNK if k % 2 else BARK2, pts[k], pts[k + 1], ra, rb, 10)
        limb(tr, WHITE, pts[0] + (pts[1] - pts[0]) * 0.05, pts[0] + (pts[1] - pts[0]) * 0.85, r0 * 1.06, r0 * 0.99, 10)  # painted base
        tr.cyl(METAL, (1.7, 1.7, 0.05), (x, ty, 0.03), seg=16)
        top = pts[5]
        # 4 main limbs fork from the top, biased toward the street; each forks again
        for b_ in range(4):
            az = -s * RT(-0.5, 1.1) + (b_ - 1.5) * 1.25  # around the vertical; 0 = toward the street
            el = RT(0.5, 0.95)
            d1 = Vector((-s * math.cos(az) * math.sin(el), math.sin(az) * math.sin(el), math.cos(el)))
            L1 = RT(1.5, 2.3)
            m1 = top + d1 * L1 + Vector((0, 0, RT(0.0, 0.3)))
            limb(tr, TRUNK, top, m1, r0 * 0.46, r0 * 0.32, 7)
            for f_ in (-1, 1):
                d2 = (d1 + Vector((RT(-0.5, 0.5), f_ * RT(0.35, 0.8), RT(0.1, 0.6)))).normalized()
                e2 = m1 + d2 * RT(1.1, 1.8)
                limb(tr, BARK2, m1, e2, r0 * 0.3, r0 * 0.16, 6)
                clump(e2 + Vector((0, 0, 0.5)), RT(1.0, 1.35), 5)
            clump(m1 + Vector((0, 0, 1.1)), RT(1.1, 1.5), 4)
        # one lower side branch
        hb = pts[3] + (pts[4] - pts[3]) * 0.5
        eb = hb + Vector((-s * RT(0.9, 1.5), RT(-1.3, 1.3), RT(1.1, 1.7)))
        limb(tr, TRUNK, hb, eb, r0 * 0.3, r0 * 0.15, 6)
        clump(eb + Vector((0, 0, 0.9)), RT(0.9, 1.2), 4)
        clump(top + Vector((-s * 0.8, 0, 3.0)), RT(1.4, 1.8), 6)  # crown
tr.done("trunks")
lf.done("leaves")

# ---------------------------------------------------------------- lantern strings
lanterns = []
lights = []
wm = B()
for i in range(15):
    y = 5.5 + i * 4.6
    z0 = R(4.7, 5.3)
    sag = R(0.5, 0.9)
    pts = [Vector((-4.0 + 8.0 * t / 16, y, z0 - sag * math.sin(math.pi * t / 16))) for t in range(17)]
    cu = bpy.data.curves.new("wire", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(16)
    for p, v in zip(sp.points, pts):
        p.co = (*v, 1)
    cu.bevel_depth = 0.012
    cu.materials.append(METAL)
    col.objects.link(bpy.data.objects.new("wire", cu))
    for j in range(5):
        p = pts[2 + j * 3]
        b = B()
        m = lant_m[(i * 2 + j) % len(lant_m)]
        r = R(0.42, 0.6)
        b.ball(m, (r, r, r * 0.86), (0, 0, -0.34 - r * 0.43), sub=3)
        b.cyl(METAL, (0.16, 0.16, 0.08), (0, 0, -0.34))
        b.cyl(METAL, (0.16, 0.16, 0.08), (0, 0, -0.34 - r * 0.86))
        b.cyl(METAL, (0.015, 0.015, 0.34), (0, 0, -0.17))
        b.cyl(TXT_Y, (0.03, 0.03, 0.3), (0, 0, -0.5 - r * 0.86), seg=6)
        ob = b.done("lantern")
        ob.location = p
        lanterns.append((ob, R(0, 6.28), R(0.05, 0.11)))
    # fairy bulbs on a second, lower wire
    for t in range(1, 16):
        if t % 3:
            wm.ball(BULB, (0.09, 0.09, 0.09), pts[t] + Vector((0, 0, -0.06)), sub=1)
    ld = bpy.data.lights.new("lanternlight", "POINT")
    ld.color = (1.0, 0.62, 0.3)
    ld.shadow_soft_size = 0.6
    ld.use_shadow = i % 3 == 0
    lo = bpy.data.objects.new("lanternlight", ld)
    lo.location = (R(-1, 1), y, z0 - sag - 0.6)
    col.objects.link(lo)
    lights.append(ld)
wm.done("bulbs")

# street lamps
lp = B()
for s in (-1, 1):
    for y in (9, 30, 51, 72):
        yy = y + (s > 0) * 10
        lp.cyl(METAL, (0.12, 0.12, 3.4), (s * 4.6, yy, 1.7), seg=8)
        lp.ball(BULB, (0.36, 0.36, 0.42), (s * 4.6, yy, 3.55))
        lp.cyl(METAL, (0.44, 0.44, 0.07), (s * 4.6, yy, 3.8), seg=8)
lp.done("lamps")

# ---------------------------------------------------------------- stalls, books, props
st = B()


def books_row(b, x, y, z, length, along="y", hmin=0.2, hmax=0.3, depth=0.2):
    p = 0.0
    while p < length:
        t = R(0.03, 0.07)
        h = R(hmin, hmax)
        m = book_m[random.randrange(len(book_m))]
        if along == "y":
            b.box(m, (depth, t, h), (x, y + p + t / 2, z + h / 2), (R(-0.05, 0.05), 0, 0))
        else:
            b.box(m, (t, depth, h), (x + p + t / 2, y, z + h / 2), (0, R(-0.05, 0.05), 0))
        p += t + 0.004


def stack(b, x, y, z, n, rz=0.0):
    for i in range(n):
        m = book_m[random.randrange(len(book_m))]
        t = R(0.035, 0.06)
        b.box(m, (R(0.2, 0.26), R(0.28, 0.34), t), (x + R(-0.015, 0.015), y + R(-0.015, 0.015), z + t / 2), (0, 0, rz + R(-0.3, 0.3)))
        z += t
    return z


def stall(s, y, k):
    x = s * 5.1
    st.box(CLOTH[k % 3], (1.3, 3.0, 0.8), (x, y, 0.54))  # table with cloth
    for i in range(7):
        stack(st, x + R(-0.4, 0.35), y - 1.25 + i * 0.42, 0.94, random.randint(2, 7))
    # shelf behind
    sx = s * 6.35
    st.box(DARKWOOD, (0.06, 3.1, 2.3), (sx + s * 0.16, y, 1.29))
    for e in (-1, 1):
        st.box(WOOD, (0.36, 0.06, 2.3), (sx, y + e * 1.55, 1.29))
    for r in range(5):
        z = 0.2 + r * 0.5
        st.box(WOOD, (0.36, 3.1, 0.05), (sx, y, z))
        books_row(st, sx - s * 0.02, y - 1.5, z + 0.025, 3.0, hmin=0.26, hmax=0.4, depth=0.24)
    st.box(WOOD, (0.36, 3.1, 0.05), (sx, y, 2.44))
    # parasol
    st.cyl(WOOD, (0.06, 0.06, 2.9), (x + s * 0.5, y + 1.7, 1.6), seg=6)
    st.cyl(AWN[(k + 1) % 4], (3.4, 3.4, 0.5), (x + s * 0.5, y + 1.7, 3.0), top=0.04, seg=10)


for i, y in enumerate([8.5, 15.5, 29.5, 36.5, 50.5, 57.5]):
    stall(-1, y + 0.3, i)
    stall(1, y + 2.2, i + 1)

# hero book table for the close-up (shot 4): left side
HERO = Vector((-3.3, 22.4, 0))
st.box(CLOTH[0], (1.1, 2.4, 0.78), (HERO.x, HERO.y, 0.39))
HERO_TOP = 0.0
for i, n in enumerate([6, 9, 4, 7, 5]):
    z_top = stack(st, HERO.x + 0.18, HERO.y - 0.9 + i * 0.45, 0.78, n)
    if i == 2:
        HERO_TOP = z_top
st.box(WOOD, (0.3, 2.4, 0.04), (HERO.x - 0.36, HERO.y, 1.1))
st.box(WOOD, (0.04, 2.4, 0.9), (HERO.x - 0.52, HERO.y, 1.2))
books_row(st, HERO.x - 0.36, HERO.y - 1.15, 0.78, 2.3, hmin=0.24, hmax=0.3, depth=0.2)
books_row(st, HERO.x - 0.36, HERO.y - 1.15, 1.12, 2.3, hmin=0.24, hmax=0.34, depth=0.2)
st.box(WHITE, (0.02, 0.46, 0.3), (HERO.x + 0.56, HERO.y - 0.6, 0.52))
text("10K", (HERO.x + 0.575, HERO.y - 0.6, 0.52), 0.17, M("txtred", "#d9302c", 0.6, 0.3), rz=math.radians(90))

# plastic table + stools + cups (shot 3): right side
PT = Vector((2.4, 14.7, 0))


def plastic_table(c, m, top, h, legs=0.03):
    st.box(m, (top, top, 0.04), (c.x, c.y, h))
    for ex in (-1, 1):
        for ey in (-1, 1):
            st.box(m, (legs, legs, h), (c.x + ex * top * 0.4, c.y + ey * top * 0.4, h / 2), (ey * 0.07, -ex * 0.07, 0))


plastic_table(PT, RED, 0.72, 0.62, 0.04)
for dx, dy in ((0.75, 0.15), (-0.2, 0.8), (-0.75, -0.25), (0.25, -0.8)):
    plastic_table(PT + Vector((dx, dy, 0)), BLUE, 0.34, 0.36)
CUP = M("cup", "#fff6e6", 0.4)
COFFEE = M("coffee", "#4a2a18", 0.3)
for dx, dy in ((0.14, 0.1), (-0.16, -0.08)):
    st.cyl(CUP, (0.085, 0.085, 0.13), (PT.x + dx, PT.y + dy, 0.705), top=1.25)
    st.cyl(COFFEE, (0.09, 0.09, 0.012), (PT.x + dx, PT.y + dy, 0.768))
stack(st, PT.x - 0.02, PT.y + 0.24, 0.64, 3, 0.4)
# a parked bicycle-ish cart? keep it simple: second table set further on
plastic_table(Vector((-2.3, 40, 0)), RED, 0.72, 0.62, 0.04)
for dx, dy in ((0.7, 0.1), (-0.6, 0.4)):
    plastic_table(Vector((-2.3 + dx, 40 + dy, 0)), BLUE, 0.34, 0.36)

# benches + planters
for s, y in ((1, 19.0), (-1, 33), (1, 45), (-1, 61)):
    x = s * 3.3
    for i in range(3):
        st.box(WOOD, (0.14, 1.7, 0.05), (x + (i - 1) * 0.17, y, 0.46))
    for i in range(2):
        st.box(WOOD, (0.05, 1.7, 0.13), (x + s * 0.28, y, 0.66 + i * 0.2))
    for e in (-1, 1):
        st.box(METAL, (0.5, 0.06, 0.46), (x, y + e * 0.75, 0.23))
        st.box(METAL, (0.05, 0.06, 0.5), (x + s * 0.3, y + e * 0.75, 0.7))
    for e in (-1, 1):
        py = y + e * 1.6
        st.box(PLANTER, (0.6, 0.6, 0.5), (x, py, 0.25))
        for j in range(4):
            st.ball(LEAF[j % 4], (0.42, 0.42, 0.36), (x + R(-0.14, 0.14), py + R(-0.14, 0.14), 0.62 + R(0, 0.12)), sub=1)
        st.ball(M("flower", "#ff7aa8", 0.6), (0.12, 0.12, 0.12), (x + 0.1, py - 0.1, 0.86), sub=1)
        st.ball(M("flower2", "#ffd84a", 0.6), (0.11, 0.11, 0.11), (x - 0.12, py + 0.08, 0.84), sub=1)

# A-frame sign + cat (shots 6): right of centre
AF = Vector((1.9, 20.6, 0))
tilt = 0.2
st.box(BOARD, (0.95, 0.05, 1.25), (AF.x, AF.y, 0.64), (-tilt, 0, 0))
st.box(WOOD, (1.05, 0.04, 1.35), (AF.x, AF.y + 0.02, 0.66), (-tilt, 0, 0))
st.box(WOOD, (1.05, 0.04, 1.35), (AF.x, AF.y + 0.36, 0.66), (tilt, 0, 0))
text("SÁCH CŨ\nĐỒNG GIÁ\n33K", (AF.x, AF.y - 0.04, 0.66), 0.215, TXT_Y, tilt=-tilt)

# scooters
def scooter(x, y, m, d=1):
    for e in (-1, 1):
        st.cyl(METAL, (0.44, 0.44, 0.13), (x, y + e * 0.62 * d, 0.22), (0, math.pi / 2, 0), seg=14)
        st.cyl(WHITE, (0.2, 0.2, 0.15), (x, y + e * 0.62 * d, 0.22), (0, math.pi / 2, 0), seg=10)
    st.ball(m, (0.52, 1.05, 0.6), (x, y - 0.38 * d, 0.5))
    st.box(m, (0.4, 0.7, 0.08), (x, y + 0.15 * d, 0.3))
    st.box(m, (0.5, 0.09, 0.8), (x, y + 0.52 * d, 0.66), (-0.2 * d, 0, 0))
    st.ball(m, (0.5, 0.3, 0.3), (x, y + 0.62 * d, 0.36))
    st.cyl(METAL, (0.04, 0.04, 0.62), (x, y + 0.44 * d, 1.08), (0, math.pi / 2, 0), seg=6)
    st.ball(BULB, (0.16, 0.12, 0.16), (x, y + 0.56 * d, 0.98), sub=1)
    st.box(DARKWOOD, (0.34, 0.62, 0.1), (x, y - 0.32 * d, 0.83))


TEAL = M("scoot_teal", "#4fb8ad", 0.35)
scooter(-2.5, 13.2, TEAL, -1)
scooter(3.15, 16.5, TEAL, -1)
scooter(2.9, 27.5, M("scoot_red", "#d8402f", 0.35), 1)
scooter(-2.7, 37.0, TEAL, 1)

# vertical banners on poles + round signs
for k, (sd_, y, word) in enumerate([(-1, 9.5, "THIẾU NHI"), (1, 13.0, "NGOẠI VĂN"), (-1, 23.5, "VĂN HỌC"), (1, 26.0, "THIẾU NHI"), (-1, 38.0, "NGOẠI VĂN"), (1, 41.0, "VĂN HỌC")]):
    x = sd_ * 3.55
    st.cyl(METAL, (0.09, 0.09, 4.3), (x, y, 2.15), seg=8)
    bm_ = SIGNBLUE if k % 2 == 0 else SIGNRED
    st.box(bm_, (0.72, 0.05, 2.5), (x - sd_ * 0.48, y, 3.0))
    text("\n".join(word.replace(" ", "")), (x - sd_ * 0.48, y - 0.04, 3.0), 0.27, TXT_W)
for sd_, y in ((-1, 16.5), (1, 20.5), (-1, 31.0), (1, 34.0)):
    x = sd_ * 3.7
    st.cyl(METAL, (0.07, 0.07, 3.0), (x, y, 1.5), seg=8)
    st.cyl(SIGNBLUE, (0.9, 0.9, 0.06), (x, y, 3.2), (math.pi / 2, 0, 0), seg=20)
    st.cyl(WHITE, (0.98, 0.98, 0.04), (x, y + 0.01, 3.2), (math.pi / 2, 0, 0), seg=20)
    text("SÁCH", (x, y - 0.045, 3.2), 0.2, TXT_W)

# wire with paper tags, for the sun-through-leaves shot
TAGM = [M("tag0", "#f0c85a", 0.8), M("tag1", "#6fa8dc", 0.8), M("tag2", "#f3e2b8", 0.8), M("tag3", "#e9a05a", 0.8)]
for q in range(21):
    t0 = q / 20
    px, py, pz = -1.6 + 6.2 * t0, 27.1 + 0.9 * t0, 4.75 - 0.9 * t0 - 0.35 * math.sin(math.pi * t0)
    st.ball(METAL, (0.05, 0.05, 0.05), (px, py, pz), sub=1)
    if q in (7, 9, 11, 13):
        st.cyl(METAL, (0.012, 0.012, 0.22), (px, py, pz - 0.11), seg=5)
        st.box(TAGM[(q // 2) % 4], (0.3, 0.012, 0.44), (px, py, pz - 0.42), (0, R(-0.4, 0.4), R(-0.5, 0.5)))
st.done("props")

# fallen leaves
fl = B()
LEAFY = [M("fall0", "#e2b13c", 0.8), M("fall1", "#c9562c", 0.8), M("fall2", "#8cc24a", 0.8)]
for i in range(260):
    fl.box(LEAFY[i % 3], (R(0.08, 0.14), R(0.05, 0.08), 0.004), (R(-4.3, 4.3), R(0, 70), 0.004), (0, 0, R(0, 3.1)))
fl.done("fallen")

# cat card
img = bpy.data.images.load(os.path.join(HERE, "cat.png")) if os.path.exists(os.path.join(HERE, "cat.png")) else bpy.data.images.new("cat", 8, 8, alpha=True)  # optional cut-out picture
cm = bpy.data.materials.new("cat")
cm.use_nodes = True
cb = bsdf(cm)
ti = cm.node_tree.nodes.new("ShaderNodeTexImage")
ti.image = img
cm.node_tree.links.new(ti.outputs["Color"], cb.inputs["Base Color"])
cm.node_tree.links.new(ti.outputs["Alpha"], cb.inputs["Alpha"])
cm.node_tree.links.new(ti.outputs["Color"], cb.inputs["Emission Color"])
cb.inputs["Emission Strength"].default_value = 0.25
cb.inputs["Roughness"].default_value = 1
cb.inputs["Specular IOR Level"].default_value = 0
CH = 0.62
cme = bpy.data.meshes.new("cat")
w2 = CH * 600 / 760 / 2
cme.from_pydata([(-w2, 0, 0), (w2, 0, 0), (w2, 0, CH), (-w2, 0, CH)], [], [(0, 1, 2, 3)])
uv = cme.uv_layers.new()
for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
    uv.data[i].uv = c
cme.materials.append(cm)
cat = bpy.data.objects.new("cat", cme)
cat.location = (0.75, 20.2, 0.0)
col.objects.link(cat)

# ---------------------------------------------------------------- light + world
sd = bpy.data.lights.new("sun", "SUN")
sun = bpy.data.objects.new("sun", sd)
col.objects.link(sun)
SUN_DIR = Vector((0.22, 1.0, 0.62)).normalized()  # toward the sun: low, down the street
sun.rotation_euler = (-SUN_DIR).to_track_quat("-Z", "Y").to_euler()
sd.angle = math.radians(2.5)
# sun disc + glow far down the street
sb = B()
SUNM = M("sundisc", "#fff2c0", 1, 30, "#ffe6a0")
sb.ball(SUNM, (26, 26, 26), (0, 0, 0))
sundisc = sb.done("sundisc")
sundisc.visible_shadow = False
hb = B()
hb.ball(lant_m[0], (1.25, 1.25, 1.08), (0, 0, 0), sub=3)
hb.cyl(METAL, (0.5, 0.5, 0.14), (0, 0, 0.54))
hb.cyl(METAL, (0.5, 0.5, 0.14), (0, 0, -0.54))
hb.cyl(TXT_Y, (0.07, 0.07, 0.9), (0, 0, -1.0), seg=6)
hb.cyl(METAL, (0.02, 0.02, 1.2), (0, 0, 1.1), seg=6)
hero_lantern = hb.done("hero_lantern")
hero_lantern.location = (0, 30, 15)
db = B()
db.ball(WHITE, (1500, 1500, 1500), (0, 40, 0), sub=3)
dome = db.done("dome")
dome.hide_render = not PROJ
dome.visible_shadow = False

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = next(n for n in wn.nodes if n.type == "BACKGROUND")
out = next(n for n in wn.nodes if n.type == "OUTPUT_WORLD")
# haze lives in a box around the street (a world volume would block the sun and sky in EEVEE)
fm = bpy.data.materials.new("fog")
fm.use_nodes = True
fnt = fm.node_tree
for n in list(fnt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        fnt.nodes.remove(n)
vs = fnt.nodes.new("ShaderNodeVolumeScatter")
vs.inputs["Anisotropy"].default_value = 0.55
fnt.links.new(vs.outputs["Volume"], next(n for n in fnt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
fb = B()
fb.box(fm, (30, 150, 22), (0, 55, 11))
fogbox = fb.done("fogbox")

cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
col.objects.link(cam)
scene.camera = cam
cam_d.clip_start, cam_d.clip_end = 0.05, 3000

# ---------------------------------------------------------------- render settings
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 768, 1376  # tall
scene.render.image_settings.file_format = "PNG"
scene.render.fps = 24
ee = scene.eevee
ee.taa_render_samples = 24 if STILLS else 32
for k, v in dict(use_shadows=True, use_raytracing=True, use_volumetric_shadows=True, volumetric_end=160.0,
                 volumetric_tile_size="4", volumetric_samples=96, use_gtao=True, shadow_ray_count=2, shadow_step_count=6).items():
    try:
        setattr(ee, k, v)
    except Exception as e:
        print("eevee setting skipped", k, e)
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
except TypeError as e:
    print("look", e)


def set_time(mode):
    """day | dusk | night"""
    P = {
        "day": dict(sun=6.5, sunc=(1.0, 0.78, 0.5), sky="#8fc6ee", skys=0.55, fog=0.005, fogc=(1.0, 0.85, 0.62), lant=0.25, lamp=0.5, win=0.02, bulb=0.5, shop=0.1, disc=60, expo=-0.15),
        "blue": dict(sun=0.5, sunc=(0.6, 0.6, 1.0), sky="#3b3f8f", skys=0.9, fog=0.006, fogc=(0.8, 0.75, 1.0), lant=0.6, lamp=25, win=0.5, bulb=2, shop=0.4, disc=0, expo=0.0),
        "dusk": dict(sun=2.2, sunc=(1.0, 0.5, 0.25), sky="#e58a5a", skys=0.7, fog=0.008, fogc=(1.0, 0.7, 0.5), lant=1.3, lamp=70, win=1.0, bulb=3, shop=0.5, disc=26, expo=-0.1),
        "night": dict(sun=0.22, sunc=(0.45, 0.55, 1.0), sky="#1b2550", skys=0.35, fog=0.008, fogc=(0.75, 0.7, 1.0), lant=1.7, lamp=150, win=1.6, bulb=5, shop=0.45, disc=0, expo=0.1),
    }[mode]
    sdir = Vector((0.25, 1.0, 0.1)).normalized() if mode == "dusk" else SUN_DIR
    sun.rotation_euler = (-sdir).to_track_quat("-Z", "Y").to_euler()
    sundisc.location = sdir * 400
    sd.energy = P["sun"]
    sd.color = P["sunc"]
    bg.inputs["Color"].default_value = lin(P["sky"])
    bg.inputs["Strength"].default_value = P["skys"]
    vs.inputs["Density"].default_value = P["fog"]
    vs.inputs["Color"].default_value = (*P["fogc"], 1)
    for m in lant_m:
        bsdf(m).inputs["Emission Strength"].default_value = P["lant"]
    for ld in lights:
        ld.energy = P["lamp"]
    for m in (WINLIT,):
        bsdf(m).inputs["Emission Strength"].default_value = P["win"]
    bsdf(GLASS).inputs["Emission Strength"].default_value = P["win"] * 0.08
    bsdf(BULB).inputs["Emission Strength"].default_value = P["bulb"]
    bsdf(SHOPDARK).inputs["Emission Strength"].default_value = P["shop"]
    bsdf(SUNM).inputs["Emission Strength"].default_value = P["disc"]
    sundisc.hide_render = P["disc"] == 0
    bsdf(cm).inputs["Emission Strength"].default_value = 0.25 if mode == "day" else 0.5
    scene.view_settings.exposure = P["expo"]


def look(pos, tgt, lens, roll=0.0):
    cam.location = pos
    q = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    cam.rotation_euler.rotate_axis("Z", roll)
    cam_d.lens = lens


def mix(a, b, t):
    return [x + (y - x) * t for x, y in zip(a, b)]


# id, time, (pos0, pos1), (tgt0, tgt1), lens, dof (focus point, fstop) or None
SHOTS = [
    (1, "day", ((0.3, -1.0, 1.7), (0.3, -1.0, 1.7)), ((0, 30, 3.6), (0, 30, 3.6)), 20, None),
    (2, "dusk", ((-0.9, 9.0, 1.3), (-0.9, 9.0, 1.3)), ((0.5, 30, 2.8), (0.5, 30, 2.8)), 27, None),
]
# every shot is a pure dolly forward from the painted (projection) camera, so no unpainted edge comes into view
DOLLY = {1: 0.9, 2: 0.5}
W_, H_ = scene.render.resolution_x, scene.render.resolution_y

# projection pass: the Flow-painted frame of each shot is projected from that shot's middle camera onto the 3D set
projector = bpy.data.objects.new("projector", None)
col.objects.link(projector)
pm = bpy.data.materials.new("proj")
pm.use_nodes = True
pn = pm.node_tree
for n_ in list(pn.nodes):
    pn.nodes.remove(n_)
po = pn.nodes.new("ShaderNodeOutputMaterial")
pe = pn.nodes.new("ShaderNodeEmission")
pt = pn.nodes.new("ShaderNodeTexImage")
pt.extension = "EXTEND"
pc = pn.nodes.new("ShaderNodeTexCoord")
pc.object = projector
sx_ = pn.nodes.new("ShaderNodeSeparateXYZ")
cx_ = pn.nodes.new("ShaderNodeCombineXYZ")


def mth(op, a, b):
    n_ = pn.nodes.new("ShaderNodeMath")
    n_.operation = op
    for k_, v_ in ((0, a), (1, b)):
        if isinstance(v_, (int, float)):
            n_.inputs[k_].default_value = v_
        else:
            pn.links.new(v_, n_.inputs[k_])
    return n_.outputs[0]


pn.links.new(pc.outputs["Object"], sx_.inputs[0])
negz = mth("MULTIPLY", sx_.outputs["Z"], -1.0)
ku = pn.nodes.new("ShaderNodeValue")
kv = pn.nodes.new("ShaderNodeValue")
u_ = mth("ADD", mth("MULTIPLY", mth("DIVIDE", sx_.outputs["X"], negz), ku.outputs[0]), 0.5)
v_ = mth("ADD", mth("MULTIPLY", mth("DIVIDE", sx_.outputs["Y"], negz), kv.outputs[0]), 0.5)
pn.links.new(u_, cx_.inputs[0])
pn.links.new(v_, cx_.inputs[1])
pn.links.new(cx_.outputs[0], pt.inputs["Vector"])
pn.links.new(pt.outputs["Color"], pe.inputs["Color"])
pn.links.new(pe.outputs[0], po.inputs["Surface"])
if PROJ:
    for ob_ in bpy.data.objects:  # everything on the set takes the projected painting
        if ob_.type in ("MESH", "CURVE", "FONT"):
            if not ob_.data.materials:
                ob_.data.materials.append(pm)
            for k_ in range(len(ob_.data.materials)):
                ob_.data.materials[k_] = pm
    fogbox.hide_render = True
    sundisc.hide_render = True
    scene.view_settings.look = "None"
    ee.taa_render_samples = 16

# frames per shot at 24 fps (15 s in all); shots a Muse clip replaces still get a short projected version as a fallback
FR = {1: 101, 2: 98}
if os.environ.get("NTEST"):
    FR = {k: int(os.environ["NTEST"]) for k in FR}
KEEP = {}
gf = 0

# falling leaves, animated by code (made after the material swap, so they keep their own flat colours)
LEAF_SHOTS = {1: (2, 24), 2: (2, 24), 4: (0.5, 7), 9: (2, 24), 12: (3, 26)}  # shot: leaves fall between these distances ahead
leafmats = []
for k_, c_ in enumerate(["#f2c230", "#e8892c", "#d9b13a", "#c9d24a"]):
    lm = bpy.data.materials.new("leafc%d" % k_)
    lm.use_nodes = True
    for n_ in list(lm.node_tree.nodes):
        lm.node_tree.nodes.remove(n_)
    lo_ = lm.node_tree.nodes.new("ShaderNodeOutputMaterial")
    le_ = lm.node_tree.nodes.new("ShaderNodeEmission")
    le_.inputs["Color"].default_value = lin(c_)
    lm.node_tree.links.new(le_.outputs[0], lo_.inputs["Surface"])
    leafmats.append((lm, le_))
leaves = []
for k_ in range(70):
    me_ = bpy.data.meshes.new("fleaf")
    a_, b_ = R(0.07, 0.11), R(0.035, 0.05)
    me_.from_pydata([(-a_, 0, 0), (-a_ * 0.2, b_, 0.01), (a_, 0, 0), (-a_ * 0.2, -b_, 0.01)], [], [(0, 1, 2, 3)])
    me_.materials.append(leafmats[k_ % 4][0])
    ob_ = bpy.data.objects.new("fleaf", me_)
    col.objects.link(ob_)
    ob_.visible_shadow = False
    leaves.append((ob_, R(0, 1), R(0, 1), R(0, 1), R(0, 6.28), R(0.6, 1.0)))


# a book whose cover blows open and whose pages flip, animated by code (shot 5); the spine is on the far side
def flat(name, hexc):
    m_ = bpy.data.materials.new(name)
    m_.use_nodes = True
    for n_ in list(m_.node_tree.nodes):
        m_.node_tree.nodes.remove(n_)
    o_ = m_.node_tree.nodes.new("ShaderNodeOutputMaterial")
    e_ = m_.node_tree.nodes.new("ShaderNodeEmission")
    e_.inputs["Color"].default_value = lin(hexc)
    m_.node_tree.links.new(e_.outputs[0], o_.inputs["Surface"])
    return m_


def slab(name, x1, hw, z0, z1, mats):
    """a box from the hinge (x = 0) toward the camera; faces: top, bottom, sides"""
    me_ = bpy.data.meshes.new(name)
    v_ = [(0, -hw, z0), (x1, -hw, z0), (x1, hw, z0), (0, hw, z0), (0, -hw, z1), (x1, -hw, z1), (x1, hw, z1), (0, hw, z1)]
    f_ = [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me_.from_pydata(v_, [], f_)
    for m_ in mats:
        me_.materials.append(m_)
    for k_, p_ in enumerate(me_.polygons):
        p_.material_index = min(k_, len(mats) - 1)
    ob_ = bpy.data.objects.new(name, me_)
    col.objects.link(ob_)
    ob_.visible_shadow = False
    return ob_


BK = Vector((HERO.x + 0.18 - 0.125, HERO.y, HERO_TOP))
INK = flat("bk_ink", "#2a2320")
block = slab("bk_block", 0.25, 0.165, 0.0, 0.035, [flat("bk_p0", "#f6edd6"), flat("bk_navy", "#22386e"), flat("bk_edge", "#e2d5b4")])
block.location = BK
cover = slab("bk_cover", 0.262, 0.172, 0.0, 0.007, [flat("bk_navy2", "#2b4a8c"), flat("bk_navy3", "#22386e"), INK])
cover.location = BK + Vector((-0.004, 0, 0.036))
pages = []
for k_ in range(11):
    c_ = ["#f8f0da", "#efe4c6", "#f4ead0", "#e9dcb9"][k_ % 4]
    pg = slab("bk_page%d" % k_, 0.245 - 0.002 * k_, 0.16, 0.0, 0.0012, [flat("bk_pg%d" % k_, c_), flat("bk_pgb%d" % k_, "#eadfc0"), INK])
    pg.location = BK + Vector((0, 0, 0.0352 + 0.0001 * (11 - k_)))
    pages.append(pg)


LINEM = flat("bk_line", "#9a8c70")


def lines(parent, x1, z0, z1):
    b_ = B()
    for j_ in range(8):
        w_ = 0.26 if j_ % 3 else 0.2
        b_.box(LINEM, (0.006, w_, z1 - z0), (0.035 + j_ * (x1 - 0.06) / 8, (w_ - 0.26) / 2, (z0 + z1) / 2))
    o_ = b_.done("bk_lines")
    o_.parent = parent
    o_.visible_shadow = False
    return o_


extras = [lines(block, 0.25, 0.0352, 0.0356)]
endp = slab("bk_endpaper", 0.25, 0.16, -0.0012, -0.0002, [flat("bk_end", "#e6d9b6")])
endp.parent = cover
extras.append(endp)
for pg in pages:
    extras.append(lines(pg, 0.24, -0.0005, 0.0017))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def set_book(sid, i):
    on = PROJ and sid == 5
    for ob_ in [block, cover] + pages + extras:
        ob_.hide_render = not on
    if not on:
        return
    cover.rotation_euler = (0, -math.radians(118) * ease((i - 3) / 9) - math.radians(4) * math.sin(max(0, i - 12) * 0.5) * math.exp(-max(0, i - 12) * 0.15), 0)
    for k_, pg in enumerate(pages):
        a_ = ease((i - 9 - 2.1 * k_) / 8)
        flut = math.radians(5) * math.sin(i * 0.9 + k_) * a_ * (1 - a_) * 4
        pg.rotation_euler = (0, -(math.radians(113 - 1.6 * k_) * a_ + flut), 0)


def set_leaves(sid, cam_y, tsec):
    on = PROJ and sid in LEAF_SHOTS
    for ob_, u_, v_, w_, ph_, sp_ in leaves:
        ob_.hide_render = not on
        if not on:
            continue
        lo_, hi_ = LEAF_SHOTS[sid]
        z_ = (6.5 * w_ - sp_ * 0.9 * tsec) % 6.5
        ob_.location = (-3.8 + 7.6 * u_ + 0.3 * math.sin(2.1 * tsec + ph_), cam_y + lo_ + (hi_ - lo_) * v_ + 0.15 * math.sin(1.3 * tsec + ph_), z_ + 0.03)
        ob_.rotation_euler = (ph_ + 3.1 * tsec, 2 * ph_ + 2.3 * tsec, 4.0 * tsec + ph_) if z_ > 0.08 else (0, 0, ph_)
    for lm_, le_ in leafmats:
        le_.inputs["Strength"].default_value = 0.35 if sid in (9, 12) else 1.0


# ---- one hero leaf for the close-ups, flying in the picture plane of the shot's painted camera
def cam_point(sid, lens, u, v, z):
    """world point seen at picture position (u, v) (0..1, v from the bottom) at distance z from the painted camera"""
    ku_, kv_ = lens / 36.0, lens / 36.0 * W_ / H_
    return KEEP[sid] @ Vector(((u - 0.5) * z / ku_, (v - 0.5) * z / kv_, -z))


def poly(name, pts, m_, z=0.0):
    me_ = bpy.data.meshes.new(name)
    me_.from_pydata([(x_, y_, z) for x_, y_ in pts], [], [list(range(len(pts)))])
    me_.materials.append(m_)
    return me_


LEAFPTS = [(0, 1.0), (0.2, 0.72), (0.5, 0.62), (0.4, 0.36), (0.66, 0.1), (0.36, 0.02), (0.3, -0.34), (0.08, -0.2), (0.03, -0.75),
           (-0.03, -0.75), (-0.08, -0.2), (-0.3, -0.34), (-0.36, 0.02), (-0.66, 0.1), (-0.4, 0.36), (-0.5, 0.62), (-0.2, 0.72)]
hleaf = bpy.data.objects.new("hleaf", poly("hleaf", LEAFPTS, flat("hl_fill", "#f4c22b")))
hink = bpy.data.objects.new("hleaf_ink", poly("hleaf_ink", [(x_ * 1.16, y_ * 1.1) for x_, y_ in LEAFPTS], flat("hl_ink", "#7a4a12"), -0.02))
hvein = bpy.data.objects.new("hleaf_vein", poly("hleaf_vein", [(-0.025, -0.3), (0.025, -0.3), (0.012, 0.8), (-0.012, 0.8)], flat("hl_vein", "#c8891a"), 0.02))
for o_ in (hleaf, hink, hvein):
    col.objects.link(o_)
    o_.visible_shadow = False
hink.parent = hleaf
hvein.parent = hleaf
# shot: distance, start and landing picture positions, landing frame, size (m), resting tilt, stays after landing
HERO = {
    3: dict(z=1.85, a=(0.44, 1.08), b=(0.52, 0.395), land=20, size=0.085, rest=(1.3, 0.0, 0.6), stay=True),
    7: dict(z=2.1, a=(0.33, 1.08), b=(0.25, 0.60), land=15, size=0.075, rest=(1.15, 0.0, 1.45), stay=False),
    11: dict(z=2.1, a=(0.40, 1.08), b=(0.45, 0.05), land=22, size=0.07, rest=(1.25, 0.0, 1.5), stay=False),
}


def set_hero(sid, lens, i):
    h_ = HERO.get(sid) if PROJ else None
    on = bool(h_) and (i <= h_["land"] or h_["stay"])
    for o_ in (hleaf, hink, hvein):
        o_.hide_render = not on
    if not on:
        return
    f_ = min(1.0, i / h_["land"])
    air = 1.0 - f_
    u_ = h_["a"][0] + (h_["b"][0] - h_["a"][0]) * f_ + 0.045 * math.sin(f_ * 9.0) * air
    v_ = h_["a"][1] + (h_["b"][1] - h_["a"][1]) * (0.35 * f_ + 0.65 * f_ * f_) + 0.02 * math.cos(f_ * 9.0) * air
    rx, ry, rz = h_["rest"]
    e_ = Euler((rx + 2.6 * air * math.sin(f_ * 7.0), ry + 1.1 * math.sin(f_ * 9.0) * air, rz + 3.0 * air), "XYZ")
    m_ = KEEP[sid].copy()
    m_.translation = cam_point(sid, lens, u_, v_, h_["z"])
    hleaf.matrix_world = m_ @ e_.to_matrix().to_4x4() @ Matrix.Scale(h_["size"], 4)


# ---- paper tags of shot 6: cut out of the painting (tags.py) and swung by code in front of the tag-free painting
TAGS = []
tagf = os.path.join(OUT, "tags.json")
if PROJ and os.path.exists(tagf):
    import json
    tm = bpy.data.materials.new("tagsprite")
    tm.use_nodes = True
    tn = tm.node_tree
    for n_ in list(tn.nodes):
        tn.nodes.remove(n_)
    to_ = tn.nodes.new("ShaderNodeOutputMaterial")
    te_ = tn.nodes.new("ShaderNodeEmission")
    tt_ = tn.nodes.new("ShaderNodeBsdfTransparent")
    tx_ = tn.nodes.new("ShaderNodeMixShader")
    ti_ = tn.nodes.new("ShaderNodeTexImage")
    ti_.image = bpy.data.images.load(os.path.join(OUT, "paint", "s6_tags.png"))
    ti_.extension = "CLIP"
    tn.links.new(ti_.outputs["Color"], te_.inputs["Color"])
    tn.links.new(ti_.outputs["Alpha"], tx_.inputs["Fac"])
    tn.links.new(tt_.outputs[0], tx_.inputs[1])
    tn.links.new(te_.outputs[0], tx_.inputs[2])
    tn.links.new(tx_.outputs[0], to_.inputs["Surface"])
    try:
        tm.surface_render_method = "BLENDED"
    except Exception:
        tm.blend_method = "BLEND"
    for k_, t_ in enumerate(json.load(open(tagf))):
        TAGS.append((t_, k_))


def build_tags(lens):
    """quads in the painted camera's space, each hinged at the top of its tag"""
    out_ = []
    ku_, kv_ = lens / 36.0, lens / 36.0 * W_ / H_
    for t_, k_ in TAGS:
        z_ = 0.3 + 0.002 * k_
        loc = lambda u, v: Vector(((u - 0.5) * z_ / ku_, (v - 0.5) * z_ / kv_, -z_))
        piv = loc(t_["pu"], t_["pv"])
        c_ = [(t_["u0"], t_["v0"]), (t_["u1"], t_["v0"]), (t_["u1"], t_["v1"]), (t_["u0"], t_["v1"])]
        me_ = bpy.data.meshes.new("tag")
        me_.from_pydata([tuple(loc(u, v) - piv) for u, v in c_], [], [(0, 1, 2, 3)])
        uvl = me_.uv_layers.new()
        for q_, (u, v) in enumerate(c_):
            uvl.data[q_].uv = (u, v)
        me_.materials.append(tm)
        ob_ = bpy.data.objects.new("tag", me_)
        col.objects.link(ob_)
        ob_.visible_shadow = False
        out_.append((ob_, piv, k_))
    return out_


TAGOBS = None


def set_tags(sid, lens, i):
    global TAGOBS
    if not TAGS:
        return
    if TAGOBS is None:
        TAGOBS = build_tags(35)
    for ob_, piv, k_ in TAGOBS:
        ob_.hide_render = sid != 6
        if sid != 6:
            continue
        ts = i / 24
        a_ = math.radians(9) * math.sin(2 * math.pi * ts / 1.3 + k_ * 1.1)
        b_ = math.radians(13) * math.sin(2 * math.pi * ts / 1.7 + k_ * 0.7)
        # the cut-outs ride on the moving camera, very close to the lens, so no leaf geometry can cover them
        ob_.matrix_world = Matrix.LocRotScale(cam.location, cam.rotation_euler, None) @ Matrix.Translation(piv) @ Matrix.Rotation(a_, 4, "Z") @ Matrix.Rotation(b_, 4, "Y")


# extra paintings of the same frame (Flow edits): rendered as extra passes and cross-faded in build.py
PASSES = {6: [("s6", "6c")], 7: [("s7a", "7a"), ("s7", "7")], 8: [("s8", "8"), ("s8n", "8n")], 9: [("s9", "9"), ("s9n", "9n")],
          11: [("s11c", "11c"), ("s11b", "11b")]}


def set_proj(sid, mat, lens):
    projector.matrix_world = mat
    pt.image = bpy.data.images.load(os.path.join(OUT2, "paint", "s%s.jpg" % sid))
    ku.outputs[0].default_value = lens / 36.0 * (1 if W_ >= H_ else H_ / W_)  # the 36 mm sensor lies along the longer side
    kv.outputs[0].default_value = lens / 36.0 * (W_ / H_ if W_ >= H_ else 1)


STICK = None
if PROJ and os.path.exists(os.path.join(os.path.dirname(OUT2), "stick.py")):
    sys.path.insert(0, os.path.dirname(OUT2))
    import stick
    STICK = stick.make(globals(), "book")
for sid, mode, (p0, p1), (t0, t1), lens, dof in SHOTS:
    SUBF = 6 if (PROJ and not STILLS) else 1   # sub-frames per frame: the crowd is a time-lapse, post.py blends them
    N = FR[sid] * SUBF
    hero_lantern.hide_render = sid != 8
    pm_, tm_ = Vector(mix(p0, p1, 0.5)), Vector(mix(t0, t1, 0.5))
    fw = (tm_ - pm_).normalized() * DOLLY[sid]
    p0, p1, t0, t1 = pm_, pm_ + fw, tm_, tm_ + fw
    look(p0, t0, lens)
    bpy.context.view_layer.update()
    KEEP[sid] = cam.matrix_world.copy()
    if ONLY and sid not in ONLY:
        continue
    if sid in (7, 11):  # the cat card turns to the camera
        d = Vector(p0) - cat.location
        cat.rotation_euler = (0, 0, math.atan2(d.y, d.x) + math.pi / 2)
        if PROJ:  # the painted cat is bigger than the blockout card: a wide card at the cat's depth carries all of it
            cat.scale = (2.4, 1, 1.9)
    passes = PASSES.get(sid, [("s%d" % sid, sid)]) if PROJ else [("s%d" % sid, sid)]
    if PROJ:
        scene.view_settings.exposure = 0
        sundisc.hide_render = True
        cam_d.dof.use_dof = bool(dof)
    else:
        set_time(mode)
        cam_d.dof.use_dof = False
    for folder, src in passes:
        if PROJ:
            set_proj(src, KEEP[sid], lens)
        for i in ([0] if STILLS else range(N)):
            t = 0.0 if STILLS else i / (N - 1)
            pos = mix(p0, p1, t)
            look(pos, mix(t0, t1, t), lens)
            fi = i // SUBF
            set_leaves(sid, p0[1], i / SUBF / 24)
            set_book(sid, fi)
            set_hero(sid, lens, fi)
            set_tags(sid, lens, fi)
            if STICK:
                STICK(sid, i)
            if dof:
                cam_d.dof.focus_distance = (Vector(dof[0]) - Vector(pos)).length
                cam_d.dof.aperture_fstop = dof[1]
            scene.render.filepath = os.path.join(OUT2, "still_%d.png" % sid if STILLS else "f/%s/%03d.png" % (folder, i))
            bpy.ops.render.render(write_still=True)
    gf += N
print("@@done", gf)
