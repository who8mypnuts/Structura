# Command line

`structura` is the command-line companion of the app. Every command prints `--help`.

| Command | Purpose | Example |
|---------|---------|---------|
| `FILE…` | Open scripts or projects in the app (`structura` alone starts it) | `structura tree.es` |
| `lint FILE` | Check a script (exit 1 on errors) | `structura lint tree.es` |
| `build FILE` | Build and report counts; `--dump` writes the scene arrays | `structura build tree.es --seed 4` |
| `render FILE -o IMG` | Render a still | `structura render tree.es -o tree.exr --size 1920x1080 --samples 512 --denoise auto --aovs` |
| `export FILE -o OUT` | Export (format from the extension, or `--format`); `--preset` uses options saved in the app | `structura export tree.es -o tree.usdz --option up=z` |
| `template FILE -o OUT` | Export with a Structure Synth render template | `structura template tree.es --template Sunflow-Colored -o tree.sc` |
| `animate FILE -o PAT` | Render frames (a project's timeline, or `--frames A:B`) and a video | `structura animate spin.structura -o f/f.png --video spin.mp4` |
| `convert FILE --to v2` | Migrate a 1.5 script; prints notes and a diff | `structura convert old.es -o new.es` |
| `run FILE` | Run a `#javascript` movie script | `structura run movie.es --allow-execute` |
| `doctor` | Show the Qt platform, OpenGL (also XWayland) and compute devices | `structura doctor` |
| `devices` | List the compute devices and the one `auto` picks | `structura devices` |
| `theme list / check / import` | Installed themes; contrast check of a theme file; import VS Code or Base16 themes | `structura theme import MyTheme.json` |
| `warmup` | Compile the kernels ahead of time | `structura warmup --device cuda` |

Common options: `--seed N`, `--param NAME=VALUE` (sliders), `--device auto|cuda|opencl|wgpu|cpu`.
`render` also takes `--integrator`, `--view`, `--exposure`, `--frame` (fit the structure), `--noise-threshold`,
`--time-limit`, `--tag-presets`, `--no-embed-script`, and `--report FILE` (repeatable: `.pdf .html .md .txt .json
.csv .odt`), which writes the same render report as the app.

## Python

```python
import structura.api as st

scene = st.build("tree.es", seed=4, params={"SIZE": 0.8})
st.render(scene, "tree.png", device="cpu", samples=64, width=800, height=600)
st.export(scene, "tree.glb")
```
