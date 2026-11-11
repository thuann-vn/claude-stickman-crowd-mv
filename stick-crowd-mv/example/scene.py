# A 30 s music Short — the Japanese night street in the painted-3D style.
#   blender -b --factory-startup --python-exit-code 1 -P scene.py -- --stills      blockout stills → out/still_<id>.png (sent to Flow)
#   blender -b --factory-startup --python-exit-code 1 -P scene.py -- --proj        final frames from the paintings in out/paint
# The street runs along +y (x −3..3), a side street crosses at y 18..23, a gate stands at y 3, a big screen closes it at y 62.
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.claude/skills/painted-3d-short/tools"))
from p3d import *

ROAD = M("road", "#3c3f48", 0.6)
LINE = M("line", "#e6e6dc", 0.7)
BODY = [M("b%d" % i, c, 0.9) for i, c in enumerate(["#6f7480", "#8a7f74", "#565d6e", "#9a9388", "#4f5560", "#7d6f66", "#646c78"])]
SHUT = [M("sh%d" % i, c, 0.7) for i, c in enumerate(["#2c2f38", "#5a3a32", "#2f4a58", "#3d3f46"])]
GLASS = M("glass", "#9fd6f2", 0.3, 1.2, "#bfe6ff")
WINW = M("winw", "#ffe2a0", 0.4, 1.6, "#ffd98a")
WIND = M("wind", "#2a3146", 0.4)
NEON = [M("n%d" % i, c, 0.5, 3.0, c) for i, c in enumerate(["#ff3d7f", "#35e0ff", "#ffd23f", "#ff5a36", "#7dff6a", "#b06bff", "#ffffff", "#ff8a2a"])]
AWN = [M("aw%d" % i, c, 0.8) for i, c in enumerate(["#b5342f", "#1f4f8a", "#e9e2d0", "#2e7a55", "#d98a2a"])]
LANT = M("lant", "#ff4a32", 0.5, 3.0, "#ff5a36")
LANTW = M("lantw", "#fff0c8", 0.5, 3.0, "#ffe9b0")
POLE = M("pole", "#70747c", 0.8)
WIRE = M("wire", "#16181d", 0.6)
VEND = [M("v%d" % i, c, 0.4, 1.5, c) for i, c in enumerate(["#f4f6fa", "#e23a3a", "#2f6fd0"])]
GATE = M("gate", "#c8332b", 0.6)
DARK = M("dark", "#22252c", 0.6)
WHITE = M("white", "#f2f0ea", 0.6)
SCREEN = M("screen", "#ff7ab8", 0.4, 3.0, "#ff8fc4")
PLANT = M("plant", "#3f8f4a", 0.9)
POTM = M("pot", "#8a5a3c", 0.9)
LAMPH = M("lamph", "#fff3c4", 0.4, 4.0, "#ffe9a8")
CONE = M("cone", "#ff6a1a", 0.6)

b = B()
b.box(M("ground", "#2c2e35", 0.9), (420, 420, 0.2), (0, 0, -0.1))
b.box(ROAD, (6.6, 90, 0.04), (0, 30, 0.02))
b.box(ROAD, (60, 5.0, 0.04), (0, 20.5, 0.02))  # the side street
for s in (-1, 1):  # painted edge lines of the pedestrian street
    for y0, y1 in ((-12, 17.6), (23.4, 74)):
        b.box(LINE, (0.12, y1 - y0, 0.02), (s * 2.75, (y0 + y1) / 2, 0.05))
for yc in (16.4, 24.6):  # zebra crossings before and after the side street
    for i in range(9):
        b.box(LINE, (0.42, 2.0, 0.02), (-2.3 + i * 0.575, yc, 0.05))
for xc in (-4.6, 4.6):  # and across the side street
    for i in range(7):
        b.box(LINE, (2.0, 0.42, 0.02), (xc, 18.45 + i * 0.68, 0.05))

rh = random.Random(5)


def shop(s, y0, w, floors, k):
    """one building: s = side (−1 left, +1 right), front at x = s·3.3"""
    H = floors * 3.3
    xf, yc = s * 3.3, y0 + w / 2
    body = BODY[k % len(BODY)]
    b.box(body, (7.0, w - 0.08, H), (s * 6.8, yc, H / 2))
    # ground floor: a lit shop front, a shutter part, an awning, the long sign over it
    b.box(GLASS, (0.08, w * 0.56, 2.3), (xf - s * 0.03, yc - w * 0.12, 1.2))
    b.box(SHUT[k % len(SHUT)], (0.08, w * 0.24, 2.4), (xf - s * 0.03, yc + w * 0.32, 1.2))
    b.box(AWN[k % len(AWN)], (1.1, w * 0.84, 0.06), (xf - s * 0.5, yc, 2.75), (0, s * 0.3, 0))
    b.box(NEON[(k * 3) % len(NEON)], (0.12, w * 0.8, 0.62), (xf - s * 0.07, yc, 3.3))
    if k % 2 == 0:  # paper lanterns under the awning
        for j in range(3):
            b.cyl(LANT if j != 1 else LANTW, (0.34, 0.34, 0.46), (xf - s * 0.75, yc + (j - 1) * w * 0.26, 2.25), seg=10)
    # upper floors: window bands, some lit warm, some dark; air conditioners
    for f in range(1, floors):
        z = f * 3.3
        n = max(2, int(w / 1.5))
        for j in range(n):
            lit = rh.random() < 0.55
            b.box(WINW if lit else WIND, (0.08, w / n * 0.62, 1.5), (xf - s * 0.03, y0 + (j + 0.5) * w / n, z + 1.35))
        b.box(DARK, (0.25, w - 0.1, 0.12), (xf - s * 0.1, yc, z + 0.02))
        if rh.random() < 0.5:
            b.box(WHITE, (0.35, 0.8, 0.55), (xf - s * 0.2, y0 + w * 0.82, z + 0.45))
    # the vertical signs that stick out over the street (the look of a Japanese street)
    for j in range(rh.choice((1, 2, 2, 3))):
        hh = rh.uniform(2.4, 4.4)
        zc = rh.uniform(4.6, max(4.8, H - hh / 2 - 0.4))
        yy = y0 + rh.uniform(0.15, 0.85) * w
        b.box(NEON[(k + j * 2 + 1) % len(NEON)], (0.9, 0.14, hh), (xf - s * 0.62, yy, zc))
        b.box(DARK, (0.3, 0.06, 0.08), (xf - s * 0.12, yy, zc + hh * 0.3))
        b.box(DARK, (0.3, 0.06, 0.08), (xf - s * 0.12, yy, zc - hh * 0.3))
    # roof: a parapet, sometimes a billboard on a frame, sometimes a water tank
    b.box(DARK, (7.1, w - 0.04, 0.4), (s * 6.8, yc, H + 0.2))
    r = rh.random()
    if r < 0.4:
        b.box(NEON[(k * 5 + 2) % len(NEON)], (0.16, w * 0.8, 2.0), (xf + s * 0.4, yc, H + 1.9))
        for e in (-1, 1):
            b.box(DARK, (0.08, 0.08, 1.0), (xf + s * 0.4, yc + e * w * 0.3, H + 0.6))
    elif r < 0.65:
        b.cyl(POLE, (1.3, 1.3, 1.5), (s * 5.5, yc, H + 1.15))
    # things standing on the street in front
    if k % 3 == 0:
        b.box(VEND[k % 3], (0.75, 1.0, 1.85), (xf - s * 0.45, y0 + 0.75, 0.93))
        b.box(GLASS, (0.04, 0.8, 0.9), (xf - s * 0.84, y0 + 0.75, 1.25))
    if k % 4 == 1:
        b.box(POTM, (0.4, 0.4, 0.4), (xf - s * 0.4, y0 + w - 0.6, 0.2))
        b.ball(PLANT, (0.75, 0.75, 0.9), (xf - s * 0.4, y0 + w - 0.6, 0.85))
    if k % 5 == 2:  # an A-frame menu board
        b.box(WHITE, (0.5, 0.06, 0.9), (xf - s * 1.0, y0 + w * 0.5, 0.45), (0.25, 0, s * 0.4))


for s in (-1, 1):
    y, k = -12.0, (0 if s < 0 else 3)
    while y < 74:
        w = rh.choice((4.2, 5.0, 5.6, 6.4))
        if y < 18 <= y + w:  # stop at the side street
            w = 18 - y
        if 18 <= y < 23:
            y = 23.0
            continue
        fl = rh.choice((3, 4, 4, 5, 6, 7))
        if w >= 2.5:
            shop(s, y, w, fl, k)
        y += w
        k += 1
# the building with the big screen that closes the street
b.box(BODY[2], (26, 8, 26), (0, 80, 13))
b.box(DARK, (9.4, 0.3, 5.6), (0, 75.9, 9.2))
b.box(SCREEN, (8.8, 0.2, 5.0), (0, 75.75, 9.2))
for j, x in enumerate((-9.5, -6.3, 6.3, 9.5)):
    b.box(NEON[j * 2 % len(NEON)], (1.6, 0.2, 7.0), (x, 75.8, 9.5 + (j % 2) * 3))
for z in range(3, 24, 3):
    for x in range(-11, 12, 2):
        if abs(x) < 5 and 6 < z < 13:
            continue
        b.box(WINW if rh.random() < 0.5 else WIND, (1.2, 0.12, 1.6), (x, 75.9, z + 1.2))
# the far ends of the side street
for s in (-1, 1):
    b.box(BODY[(s + 2) % len(BODY)], (10, 9, 19), (s * 34, 20.5, 9.5))
    b.box(NEON[3 if s < 0 else 1], (0.2, 5.5, 3.0), (s * 28.9, 20.5, 8.0))
# the gate of the shopping street
for s in (-1, 1):
    b.cyl(GATE, (0.34, 0.34, 6.4), (s * 3.0, 3.0, 3.2), seg=12)
b.box(GATE, (7.4, 0.36, 0.5), (0, 3.0, 6.3))
b.box(DARK, (6.2, 0.2, 1.2), (0, 3.0, 5.25))
b.box(NEON[2], (5.6, 0.26, 0.9), (0, 3.0, 5.25))
# utility poles, crossbars, transformers, a thick tangle of wires along and across the street
POLES = [(-2.95, 7.5), (2.95, 14.0), (-2.95, 27.5), (2.95, 36.0), (-2.95, 46.0), (2.95, 56.0), (-2.95, 66.0)]
for x, y in POLES:
    b.cyl(POLE, (0.26, 0.26, 9.0), (x, y, 4.5), seg=10)
    b.box(POLE, (1.6, 0.1, 0.1), (x, y, 8.3))
    b.box(POLE, (1.2, 0.1, 0.1), (x, y, 7.6))
    b.cyl(POLE, (0.5, 0.5, 0.75), (x, y + 0.3, 6.9), seg=10)
for (x0, y0), (x1, y1) in zip(POLES, POLES[1:]):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    for off, z in ((-0.6, 8.2), (0.0, 8.2), (0.6, 8.2), (-0.4, 7.5), (0.4, 7.5), (0.1, 6.6)):
        b.box(WIRE, (0.035, L, 0.035), ((x0 + x1) / 2 + off * 0.5, (y0 + y1) / 2, z), (0, 0, -math.atan2(dx, dy)))
# strings of round lanterns across the street
for y in (9.5, 13.0, 30.0, 34.0, 41.0, 50.0):
    b.box(WIRE, (6.0, 0.03, 0.03), (0, y, 4.25))
    for j in range(9):
        b.ball(LANT if j % 2 == 0 else LANTW, (0.42, 0.42, 0.5), (-2.4 + j * 0.6, y, 3.95 - 0.25 * math.sin(j / 8 * math.pi)))
# street lamps and traffic lights at the crossing, a couple of cones
for x, y in ((-2.9, 17.3), (2.9, 23.7), (2.9, -2.0), (-2.9, 40.0), (2.9, 49.0)):
    b.cyl(POLE, (0.14, 0.14, 4.6), (x, y, 2.3), seg=8)
    b.ball(LAMPH, (0.5, 0.5, 0.5), (x - (0.45 if x > 0 else -0.45), y, 4.7))
    b.box(POLE, (0.5, 0.06, 0.06), (x - (0.22 if x > 0 else -0.22), y, 4.6))
for x, y in ((2.95, 17.4), (-2.95, 23.6)):
    b.cyl(DARK, (0.16, 0.16, 3.4), (x, y, 1.7), seg=8)
    b.box(DARK, (0.34, 0.3, 0.9), (x, y, 3.3))
    b.box(NEON[4], (0.2, 0.05, 0.2), (x, y - 0.17 * (1 if y < 20 else -1), 3.1))
    b.box(NEON[3], (0.2, 0.05, 0.2), (x, y - 0.17 * (1 if y < 20 else -1), 3.5))
for x, y in ((2.2, 25.6), (2.45, 26.3)):
    b.cyl(CONE, (0.3, 0.3, 0.6), (x, y, 0.3), top=0.2, seg=10)
b.done("set")

outdoor(sun_dir=(-0.35, -0.45, 0.82), energy=2.6, color=(0.85, 0.9, 1.0), sky="#5a6aa0", strength=0.9)
start()

FPS = 24
CUT = [0, 4.2, 8.3, 12.3, 16.4, 20.5, 24.3, 30.0]            # the lyric lines of 0:56.6–1:26.6
NFR = [round(CUT[i + 1] * FPS) - round(CUT[i] * FPS) for i in range(7)]
# id: (camera pos, target, lens, dolly forward m, frames, [(frames folder, painting)])   — shots 1, 2 are the book street (other file)
SHOTS = {
    3: ((0.4, -3.6, 1.7), (0.0, 30.0, 4.4), 21, 0.9, NFR[2] * 6, [("s3", "3")]),      # into the street through the gate
    4: ((-2.0, 12.3, 1.5), (1.7, 24.0, 2.7), 26, 0.5, NFR[3] * 6, [("s4", "4")]),     # at the crossing
    5: ((0.5, 25.9, 0.85), (-0.3, 18.0, 3.4), 30, 0.25, NFR[4] * 6, [("s5", "5")]),   # low, looking back at him
    6: ((0.3, 8.6, 8.6), (0.0, 21.0, 0.4), 24, 0.6, NFR[5] * 6, [("s6", "6")]),       # from high up, down on the crossing
    7: ((0.0, 27.2, 1.65), (0.0, 62.0, 4.6), 30, 0.9, NFR[6], [("s7", "7")]),     # behind him, walking away up the street
    # 8 = the time-lapse ending: painted once with a very wide lens looking up the street; stick.py turns the render camera
    # (28 mm) inside that picture from street level up to the sky, and renders SUB sub-frames per frame (post.py blends them)
    8: ((0.2, 26.9, 1.45), (0.0, 16.9, 5.09), 14, 0.0, NFR[6] * 6, [("s8", "8")]),
}
if os.environ.get("NTEST"):  # quick look: a few frames per shot
    SHOTS = {k: v[:4] + (int(os.environ["NTEST"]),) + v[5:] for k, v in SHOTS.items()}
if os.path.exists(os.path.join(HERE, "stick.py")) and PROJ:
    sys.path.insert(0, HERE)
    import stick
    render(SHOTS, [stick.make(globals(), "jp")])
else:
    render(SHOTS)
