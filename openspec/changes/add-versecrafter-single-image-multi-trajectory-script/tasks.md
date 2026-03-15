## 1. Orchestrator scaffolding and CLI contract

- [x] 1.1 Add the new `inference/single_image_multi_trajectory.py` entrypoint and expose the default trajectory tuning arguments required by the change
- [x] 1.2 Define the root output layout, numeric preset directory mapping, and manifest schema used by the batch workflow

## 2. Shared preprocessing orchestration

- [x] 2.1 Reuse the existing MoGe, Grounded-SAM-2, and 3D Gaussian fitting scripts as shared preprocessing stages that run once per scene
- [x] 2.2 Validate shared outputs and stop early when Gaussian fitting reports zero foreground objects

## 3. Deterministic trajectory generation

- [x] 3.1 Implement the fixed six-preset table with deterministic midpoint-based `movement_distance` calculation
- [x] 3.2 Implement automatic `center_depth` and `translation_reference_depth` resolution using the requested default depth heuristics
- [x] 3.3 Generate Blender-compatible camera trajectory matrices for `left`, `right`, `up`, `zoom_out`, `zoom_in`, and `clockwise`

## 4. Static Gaussian trajectory adaptation

- [x] 4.1 Convert `shared/fitted_3D_gaussian/gaussian_params.json` into per-preset `custom_3D_gaussian_trajectory.json` files using the multi-frame schema expected by the rendering step
- [x] 4.2 Write per-preset trajectory assets into `0/1/2/3/4/5` without duplicating the shared preprocessing directory

## 5. Per-preset rendering and final generation

- [x] 5.1 Invoke `rendering_4D_control_maps.py` independently for each preset directory and store its control maps under that preset
- [x] 5.2 Invoke `versecrafter_inference.py` independently for each preset directory and capture the generated video path in the batch metadata

## 6. Resume behavior, docs, and verification

- [x] 6.1 Implement manifest updates and resume checks so completed shared outputs and successful preset runs can be reused on rerun
- [x] 6.2 Add a smoke-test or documented verification command for the new workflow and update the relevant README or usage docs
