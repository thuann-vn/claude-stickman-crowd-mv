# Finishing pass for the music Short: out/f/s1..s8 (768×1376) → out/post/%04d.png (1080×1920).
# bloom on lamps and neon · vignette · film grain · a little colour fringe · handheld drift · punch-in + flash on every cut ·
# a small pulse of zoom and glow on the song's kick. Run: ~/.local/share/unmark-venv/bin/python post.py
import cv2, numpy as np, os, subprocess, math, sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
W, H, FPS = 1080, 1920, 24
NIGHT = {3, 4, 5, 6, 7, 8}
ORDER = [1, 2, 3, 4, 5, 6, 8]   # 8 = the time-lapse ending (in the slot of 7, "walking away", which is kept in scene.py)
SUB = {8: 6}                    # sub-frames per frame, blended into streaks


def frames():
    L = []
    for s in ORDER:
        d = os.path.join(OUT, "f", "s%d" % s); fs = sorted(f for f in os.listdir(d) if f.endswith(".png")); n = SUB.get(s, 1)
        gs = [[os.path.join(d, f) for f in fs[k:k + n]] for k in range(0, len(fs) - n + 1, n)]
        L += [(s, k, len(gs), g) for k, g in enumerate(gs)]
    return L


def kick(n):
    """0..1 per frame: how hard the low end of the song hits there"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "clip.m4a"), "-ac", "1", "-ar", "8000", "-af", "lowpass=f=140", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    hop = 8000 / FPS; e = np.array([np.sqrt(np.mean(a[int(i * hop):int((i + 1) * hop)] ** 2) + 1e-12) if int(i * hop) < len(a) else 0 for i in range(n)])
    base = np.convolve(e, np.ones(13) / 13, mode="same"); on = np.maximum(0, e - base * 1.15)
    on /= (np.percentile(on, 97) + 1e-9); on = np.minimum(on, 1.0)
    out = np.zeros(n); v = 0.0
    for i in range(n):   # fast attack, soft release
        v = max(on[i], v * 0.62); out[i] = v
    return out


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
R2 = ((XX - W / 2) / (W / 2)) ** 2 * 0.55 + ((YY - H / 2) / (H / 2)) ** 2
VIG = (1.0 - 0.3 * np.clip(R2 - 0.25, 0, None))[:, :, None].astype(np.float32)


def one(job):
    g, s, k, ns, path, pulse = job
    im = cv2.imread(path[0])
    if len(path) > 1:   # long exposure: the mean of the sub-frames (in roughly linear light, so lights leave bright streaks)
        acc = sum((cv2.imread(q).astype(np.float32) / 255.0) ** 2.2 for q in path) / len(path); im = (np.clip(acc, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    t = g / FPS; night = s in NIGHT
    # camera: slow handheld drift + punch-in at the cut + the kick
    cutk = max(0.0, 1 - k / 7.0) ** 2
    z = 1.035 + 0.022 * cutk + 0.010 * pulse
    dx = 5.5 * math.sin(2 * math.pi * t / 3.7 + s) + 2.5 * math.sin(2 * math.pi * t / 1.3 + 2 * s)
    dy = 4.5 * math.sin(2 * math.pi * t / 4.3 + 1.7 * s) + 2.0 * math.sin(2 * math.pi * t / 1.1 + s)
    rot = 0.16 * math.sin(2 * math.pi * t / 5.1 + s)
    if s in SUB: dx, dy, rot = dx * 0.25, dy * 0.25, rot * 0.25   # the time-lapse stands on a tripod
    h0, w0 = im.shape[:2]; sc = W / w0 * z
    M = cv2.getRotationMatrix2D((w0 / 2, h0 / 2), rot, sc); M[0, 2] += W / 2 - w0 / 2 + dx; M[1, 2] += H / 2 - h0 / 2 + dy
    im = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    # bloom: only what is really bright (lamps, lanterns, neon, sunlit sky)
    small = cv2.resize(im, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    lum = small.max(axis=2); thr = 0.74 if night else 0.86
    br = small * np.clip((lum - thr) / (1 - thr), 0, 1)[:, :, None]
    glow = cv2.GaussianBlur(br, (0, 0), 7) * 0.6 + cv2.GaussianBlur(br, (0, 0), 22) * 0.6
    glow = cv2.resize(glow, (W, H), interpolation=cv2.INTER_LINEAR)
    im = 1 - (1 - im) * (1 - np.clip(glow * ((0.75 if night else 0.4) + 0.3 * pulse), 0, 1))   # screen
    # colour fringe toward the edges
    b, gch, r = cv2.split(im)
    Mr = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1.0022); Mb = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 0.9978)
    r = cv2.warpAffine(r, Mr, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT); b = cv2.warpAffine(b, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    im = cv2.merge([b, gch, r])
    # grade: night a touch cooler in the shadows, day warm; gentle contrast
    im = np.clip((im - 0.5) * 1.06 + 0.5, 0, 1)
    if night: im[:, :, 0] = np.clip(im[:, :, 0] + 0.012 * (1 - im[:, :, 0]), 0, 1)
    im *= VIG
    im *= 1.0 + 0.22 * max(0.0, 1 - k / 4.0)                      # flash on the cut
    rng = np.random.default_rng(g)
    n_ = cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    im += (n_ * (0.028 if night else 0.02))[:, :, None] * (1.0 - 0.6 * im)   # grain, stronger in the dark
    cv2.imwrite(os.path.join(OUT, "post", "%04d.png" % g), np.clip(im * 255 + 0.5, 0, 255).astype(np.uint8), [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return g


if __name__ == "__main__":
    F = frames(); os.makedirs(os.path.join(OUT, "post"), exist_ok=True)
    for f in os.listdir(os.path.join(OUT, "post")): os.remove(os.path.join(OUT, "post", f))
    P = kick(len(F)); print("frames", len(F), "kick mean %.2f, frames over 0.5: %d" % (P.mean(), int((P > 0.5).sum())))
    jobs = [(g, s, k, ns, p, float(P[g])) for g, (s, k, ns, p) in enumerate(F)]
    if len(sys.argv) > 1: jobs = jobs[::int(sys.argv[1])]
    with Pool(6) as pool:
        for i, _ in enumerate(pool.imap_unordered(one, jobs, chunksize=4)):
            if i % 120 == 0: print(i, flush=True)
    print("@@post done")
