# Procedural stick-figure walk in 3D (the method of the studio's what-if act.tsx gait(), made for line figures):
# feet are PLANTED (a stance foot stays on its spot while the body passes over it), hips ride high over the stance leg and
# low at the double support, arms hang from the neck and swing as pendulums against the legs, the head stays calm.
# Mocap on a line figure looked messy (elbows wide, noisy hands); this gives clean readable poses and any speed without sliding.
# Joints (14): Hips, Neck, Head, LElbow, LHand, RElbow, RHand, LKnee, LAnkle, LToe, RKnee, RAnkle, RToe, Spine2. Faces +y, z up.
import math, random
import numpy as np

L1, L2, AH, FOOT, TORSO, A1, A2 = 0.45, 0.45, 0.075, 0.17, 0.50, 0.34, 0.27


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def spec(kind, rr=None):
    rr = rr or random.Random(1); u = rr.uniform
    if kind == "hero":   # slumped, slow, small steps, arms hanging, head down
        return dict(stride=0.92, stance=0.67, lift=0.045, bob=0.012, lean=0.17, arm=0.10, elbow=0.12, head=0.42, sway=0.012, slump=0.05, v=0.72, drop=0.02)
    if kind == "stroll":
        return dict(stride=u(1.0, 1.15), stance=0.65, lift=0.055, bob=0.02, lean=u(0.02, 0.05), arm=u(0.16, 0.26), elbow=0.22, head=u(-0.03, 0.1), sway=0.016, slump=0.0, v=u(0.78, 0.98), drop=0.0)
    if kind == "brisk":
        return dict(stride=u(1.5, 1.62), stance=0.6, lift=0.085, bob=0.032, lean=u(0.1, 0.14), arm=u(0.5, 0.66), elbow=0.6, head=0.05, sway=0.01, slump=0.0, v=u(1.6, 1.85), drop=0.0)
    return dict(stride=u(1.22, 1.42), stance=0.62, lift=0.07, bob=0.026, lean=u(0.05, 0.08), arm=u(0.3, 0.46), elbow=0.36, head=u(-0.02, 0.08), sway=0.013, slump=0.0, v=u(1.12, 1.42), drop=0.0)


def _ik(hip, ank, sx):
    d = ank - hip; n = float(np.linalg.norm(d)); m = min(n, (L1 + L2) * 0.999)
    if n > m: ank = hip + d * (m / n); d = ank - hip
    a = (L1 * L1 - L2 * L2 + m * m) / (2 * m); h = math.sqrt(max(0.0, L1 * L1 - a * a))
    ax = d / m; fwd = np.array([sx * 0.06, 1.0, 0.0]); fwd = fwd - ax * float(fwd @ ax); fwd /= max(1e-6, float(np.linalg.norm(fwd)))
    return hip + ax * a + fwd * h, ank


def pose(d, g):
    """d = distance walked (m, figure of size 1). Returns joints (14,3) with the hips over x=0, y=0."""
    S, st = g["stride"], g["stance"]; J = np.zeros((14, 3))
    reach = st / 2 * S; hz0 = AH + math.sqrt(max(0.05, (L1 + L2) ** 2 - reach ** 2)) * 0.975 - g["drop"]
    pL = (d / S + st - 0.05) % 1.0
    top = AH + (L1 + L2) * 0.972 - g["drop"] * 2          # over the stance leg the knee is almost straight
    hz = hz0 + max(0.0, top - hz0) * g.get("rise", 0.8) * (1 + math.cos(4 * math.pi * (pL - st / 2))) / 2
    hip = np.array([-g["sway"] * math.cos(2 * math.pi * (pL - st / 2)), 0.0, hz]); J[0] = hip
    rel = {}
    for sx, off, kn, an, to in ((-1, st - 0.05, 7, 8, 9), (1, st + 0.45, 10, 11, 12)):
        p = (d / S + off) % 1.0
        if p < st:
            y = (st / 2 - p) * S; heel = ease((p / st - 0.7) / 0.3); z = AH + 0.075 * heel; y += 0.03 * heel
            toe = np.array([sx * 0.085, y + FOOT * math.cos(0.45 * heel) , 0.02]); toe[1] = y - 0.03 * heel + FOOT
        else:
            s = (p - st) / (1 - st); y = (st / 2 - p) * S + S * ease(s) + 0.03 * (1 - s); z = AH + 0.075 * (1 - ease(s * 2.2)) + g["lift"] * math.sin(math.pi * s)
            a = -0.75 * math.sin(math.pi * min(1.0, s * 1.5)) * (1 - ease((s - 0.55) / 0.3)) + 0.32 * ease((s - 0.6) / 0.3) * (1 - ease((s - 0.93) / 0.07) * 0.6)
            toe = np.array([sx * 0.085, y + FOOT * math.cos(a), max(0.02, z - AH * 0.7 + FOOT * math.sin(a))])
        ank = np.array([sx * 0.07, y, z]); J[kn], J[an] = _ik(hip, ank, sx); J[to] = toe + (J[an] - ank)
        rel[sx] = max(-1.2, min(1.2, y / (S * 0.35)))
    ln = g["lean"]; up = np.array([0.0, math.sin(ln), math.cos(ln)])
    J[1] = hip + up * TORSO; J[13] = hip + up * TORSO * 0.6 + np.array([0, -g["slump"], 0]); J[1][1] += g["slump"] * 0.6
    hd = ln + g["head"] + 0.02 * math.sin(4 * math.pi * pL); J[2] = J[1] + np.array([0.0, math.sin(hd), math.cos(hd)]) * 0.2
    for sx, el, ha in ((-1, 3, 4), (1, 5, 6)):
        ang = -rel[sx] * g["arm"] + ln * 0.3; a2 = ang + g["elbow"] * (0.55 + 0.45 * max(0.0, -rel[sx])) + 0.1
        J[el] = J[1] + A1 * np.array([sx * 0.26, math.sin(ang) * 0.965, -math.cos(ang) * 0.965]); J[ha] = J[el] + A2 * np.array([sx * 0.04, math.sin(a2), -math.cos(a2)])
    return J
