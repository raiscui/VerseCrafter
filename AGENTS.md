# Repository Guidelines

## Project Structure & Module Organization
`versecrafter/` contains the reusable model and pipeline code. `inference/` holds step-by-step scripts for depth estimation, segmentation, 3D Gaussian fitting, control-map rendering, and final generation. `blender_addon/` packages the Blender UI and operators used by the guided workflow. Keep runtime configs in `config/`, sample inputs in `demo_data/`, and docs/media assets in `asset/`. Treat `third_party/` as vendored submodules; update them intentionally and keep submodule pointers in sync.

## Build, Test, and Development Commands
Create the environment with `conda create -n versecrafter python=3.11` and install dependencies with `pip install -r requirements.txt`. Initialize submodules before any setup: `git submodule update --init --recursive`. Common development entry points are `python api_server.py --port 8188 --num_gpus 8` for the REST workflow, `python model_server.py` for model serving, and `bash inference.sh` for the end-to-end script pipeline. To package the Blender addon, run `zip -r blender_addon.zip blender_addon/`.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and concise module-level constants in `UPPER_SNAKE_CASE`. Match established Blender naming such as `VERSECRAFTER_OT_*` operators and `VERSECRAFTER_PT_*` panels. Prefer small, pipeline-focused helpers over broad abstractions, and keep path/config examples aligned with the README.

## Testing Guidelines
There is no root `tests/` suite or lint config yet, so every change needs a focused smoke test. For inference changes, rerun the affected command from `README.md` or `inference.sh` against `demo_data/` and record the exact command in the PR. For Blender addon changes, verify install, connection test, trajectory export, and the touched panel or operator. When adding reusable logic, introduce `pytest` tests under a new `tests/` package using `test_<feature>.py`.

## Commit & Pull Request Guidelines
Recent history uses short, imperative commit subjects such as `update readme` and `update inference code`; keep that style, but make the scope specific. PRs should explain which workflow path changed (API server, script pipeline, Blender addon, or model code), list required checkpoints or hardware assumptions, and mention any submodule updates. Include screenshots or GIFs for UI changes and sample output paths for generation changes. Do not commit model weights, local absolute paths, or private server credentials.
