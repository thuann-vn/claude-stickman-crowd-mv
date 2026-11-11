---
name: stick-crowd-mv
description: Make a vertical music Short (about 30 s) where one stick figure stands or walks alone in a crowded hand-painted 3D street - Blender blockout, image-model repaint projected back on the set, a code-animated crowd of 100-200 stick people (planted-foot walk, umbrellas, phones, lamp light, cast shadows, rain), a time-lapse ending and a finishing pass cut to the song. Use on top of the painted-3d-short skill when people must walk through the painted world.
---

# Stick crowd MV (painted 3D + code crowd)

Worked example in `example/`: "the lonely one in the crowd" — 2 shots in a Vietnamese book street (day, dusk), 4 shots in a
rainy Japanese shopping street at night, and a time-lapse ending where the camera turns up to the sky. 30 s, 720 frames, 24 fps.

This skill sits on top of **painted-3d-short** (https://github.com/thuann-vn/claude-painted-3d-shorts): its `p3d.py` builds the
blockout, renders the stills, projects the paintings and calls your setters every frame. Read that skill first. This one adds
people.

## Files

- `tools/stick.py` — the crowd. `setter = stick.make(globals(), "<location>")`, pass it to `render(SHOTS, [setter])`.
- `tools/gait.py` — the walk (numpy only, testable without Blender).
- `tools/post.py` — finishing pass over the rendered frames.
- `example/scene.py`, `example/book.py` — the two sets and their shots. `example/jobs.json` — the repaint prompts.
  `example/paint/` — the paintings. `example/m2m.json` — idle clips (Mesh2Motion, CC0).

## Order of work

1. Song first: cut the 30 s you want, find the lyric-line times, cut the shots on them (`CUT` in scene.py and stick.py).
2. Blockout + stills + repaint + projection exactly as in painted-3d-short. No people in the paintings.
3. Stage each shot in `SHOTS` of stick.py: hero start, direction, `walk` or `stand`, face pitch, lane half-width, bubble radius,
   people standing at the edges, side-street walkers (`cross`).
4. Test single frames: `NTEST=2 STICK_OFF=<frame> blender -b --factory-startup -P scene.py -- --proj --shots 4`. Look at them.
5. Full render (3 Blender processes at most), `post.py`, join with ffmpeg + the song clip.
6. Measure before you call it smooth: mean absolute difference between consecutive frames per shot; max ÷ median above ~2
   means something popped (find the frame, look at it).

## How the people are built (stick.py)

- Real geometry inside the set, so the painted street hides them correctly. Limbs of everybody = ONE mesh of 6-sided prisms whose
  vertices are rewritten every frame (numpy → `foreach_set`). Heads = spheres with a camera-space 3-tone cel shader + inverted
  hull. 200 people render in well under a second a frame in EEVEE.
- The head centre sits on the neck line (`neck + dir × radius × 0.86`), or the head floats off the body.
- Light: a list of lamps per location (position, colour, strength). Each head gets the sum as its object colour; normalise by
  the largest channel, do not clamp (clamping turns everything white). Cast shadow = the same limb mesh projected onto the
  ground from the nearest overhead lamp (length clamped), or along the sun in daylight; plus a soft contact blob.
- Umbrellas (rain): an 8-panel dome object per person, colour from the object colour, a third of them clear vinyl; the right
  arm is re-posed to hold the shaft; the canopy throws a round shadow. The hero has none.
- Phones: left hand to the ear, a thin slab against the cheek that glows at night.
- Rain: a box of thin camera-facing quads in front of the lens, at least 1.9 m away.

## The walk (gait.py)

Mocap on a line figure looks messy (arms rooted at the neck spread wide, hands are noisy). The walk is procedural instead:

- Feet are planted: a stance foot stays on its spot while the body passes over it; position on the ground comes from the
  distance walked, so any speed is slide-free (measured: < 0.2 mm a frame).
- Hips ride high over the stance leg and low at double support; 2-bone leg IK with the knee forward.
- Arms hang from the neck close to the body and swing against the legs; the head stays calm.
- Specs: `normal`, `stroll`, `brisk` (stride, cadence, arm swing, lean differ per person) and `hero` (short steps, head down,
  arms hanging). Real cadences: stroll 80–105 steps/min, normal 105–125, brisk 125–140.

## Crowd rules that were paid for

- **One straight lane per walker for the whole shot.** Steering during the shot (round the hero, round the lens) makes people
  dash sideways. Instead, before the shot starts, simulate each walker over the shot and move his lane aside once if he would
  enter the hero's empty circle, pass close to the lens, or stand between the lens and the hero.
- **The loop must wrap out of sight.** Fill the street from ~6 m behind the camera to ~50 m ahead and fade only at the wrap.
  A wrap inside the picture is a person jumping to another place.
- Never shrink or fade a person inside the picture.
- Density that reads as "crowded": 2–2.7 people per metre of a 6 m wide street.
- A pose clip with two keys left looping makes the figure shake: hold it (`timeScale = 0`).
- A standing person is never still: breathing, a slow shift of weight, the face turning.
- Couples walk abreast with the same spec, half a cycle apart.

## Time-lapse shot

- Paint ONE very wide picture (14 mm, aimed ~20° up). The render camera (28 mm) only TURNS inside it, from the hero up to the
  sky. A pure turn has no parallax, so the projection holds over a 36° tilt.
- The crowd's clock runs 14× faster after half a second (`warp()`), the hero stays on real time.
- Render 6 sub-frames per frame; post.py averages them in linear light, so people become streaks and lights stay bright.
- The setter may overwrite the camera rotation and lens: p3d calls `look()` first, then the setters.

## Finishing pass (post.py)

Bloom on what is really bright, vignette, grain (stronger in the dark), a little colour fringe, slow handheld drift (not on the
time-lapse), punch-in + flash on each cut, and a small pulse of zoom and glow on the song's kick (low band of the audio,
frame by frame). Keep every effect small; together they are enough.

## Rights

Use music you have the rights to. The example was cut to a commercial song for a private test; the audio is not in this repo.
