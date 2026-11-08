# Animation

## Keyframes

The **Timeline** dock holds the animation of the current tab:

- the frame range, frames per second, and play / pause (Ctrl+Alt+Space), next / previous frame (Alt+. /
  Alt+,);
- **◆ Camera** keys the viewport camera at the current frame; **◆ Parameters** keys every slider;
- in the **Parameters** dock, each slider's key button keys that one parameter (◇ not animated, ◈ animated,
  ◆ key here — click again to remove it);
- the strip shows one row per animated parameter (the camera has one row). Click or drag to scrub;
  right-click a key to change its interpolation (constant, linear, smooth) or delete it.

Scrubbing and playback apply the keys and rebuild only when the structure changes, so camera moves are
instant. The timeline is saved in the project (`.structura`).

## Expressions

In v2 scripts, `frame`, `time` (seconds) and `fps` can be used in any expression:

```
#version 2
{ ry (time * 45) } R          // a full turn every 8 s
rule R { 24 * { rz 15 x (1 + 0.2 * sin(time * 90)) } box }
```

## Rendering an animation

**Render ▸ Render Animation…** (or the button in the Timeline dock) renders each frame with the precision
renderer: choose the frame files (`frame.png` becomes `frame_0000.png` …), the range, the samples, and
optionally a video (MP4, WebM or GIF). Frames appear in the Render view as they finish; **Render ▸ Stop
Animation** cancels.

From the command line, `structura animate project.structura -o frames/f.png --video out.mp4` renders a
project's timeline (or `--frames 0:48` of a script using `frame` / `time`).
