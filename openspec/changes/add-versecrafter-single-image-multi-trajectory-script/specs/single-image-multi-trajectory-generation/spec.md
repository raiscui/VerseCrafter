## ADDED Requirements

### Requirement: Shared preprocessing SHALL run once per input scene
The system SHALL perform depth estimation, foreground mask extraction, and 3D Gaussian fitting once for a batch run, and SHALL reuse those shared outputs for all six trajectory generations derived from the same input image.

#### Scenario: Shared preprocessing is reused across all trajectories
- **WHEN** a user starts a single-image multi-trajectory batch with a valid image and output directory
- **THEN** the system creates one shared set of depth, mask, and Gaussian fitting artifacts for the scene
- **THEN** all six trajectory runs use that same shared artifact set instead of recomputing it per trajectory

#### Scenario: Shared preprocessing failure aborts the batch
- **WHEN** any shared preprocessing stage fails before trajectory generation begins
- **THEN** the system stops the batch before rendering or final video generation starts for any trajectory

### Requirement: The batch SHALL generate exactly six deterministic camera presets
The system SHALL generate exactly six preset trajectories named `left`, `right`, `up`, `zoom_out`, `zoom_in`, and `clockwise`. The output directories for these presets SHALL be fixed to `0`, `1`, `2`, `3`, `4`, and `5`. For each preset, `movement_distance` SHALL be computed deterministically as the midpoint of the preset range multiplied by `total_movement_distance_factor`.

#### Scenario: Numeric directories map to fixed preset names
- **WHEN** the batch run completes trajectory setup
- **THEN** the root output directory contains exactly six preset directories named `0`, `1`, `2`, `3`, `4`, and `5`
- **THEN** those directories map to `left`, `right`, `up`, `zoom_out`, `zoom_in`, and `clockwise` in that order

#### Scenario: Default distances are deterministic
- **WHEN** the user does not override `total_movement_distance_factor`
- **THEN** the system uses the default factor `1.5`
- **THEN** the resulting preset distances are `0.375`, `0.375`, `0.225`, `0.525`, `0.525`, and `0.750`

### Requirement: Automatic trajectory scaling SHALL use the requested default depth heuristics
The system SHALL estimate `center_depth` from the predicted depth map using center-crop depth statistics, and SHALL derive `translation_reference_depth` from `center_depth`. When the user does not override these settings, the defaults SHALL be `auto_center_depth_quantile=0.2`, `translation_reference_depth_scale=0.95`, and `total_movement_distance_factor=1.5`.

#### Scenario: Default depth heuristics are applied
- **WHEN** the user runs the batch command without overriding the trajectory scaling arguments
- **THEN** the system estimates `center_depth` using the default center-crop quantile value `0.2`
- **THEN** the system sets `translation_reference_depth` to `center_depth * 0.95`

#### Scenario: Effective depth values are exposed for inspection
- **WHEN** the system resolves `center_depth` and `translation_reference_depth` for a batch run
- **THEN** it records the resolved values in the batch metadata so the user can inspect the actual trajectory scaling inputs

### Requirement: The system SHALL emit Blender-compatible camera trajectories and static multi-frame Gaussian trajectories
For each preset directory, the system SHALL generate `custom_camera_trajectory.npz` containing Blender-coordinate camera-to-world matrices under the `extrinsics` key. It SHALL also generate `custom_3D_gaussian_trajectory.json` in the multi-frame format required by `rendering_4D_control_maps.py` by broadcasting the fitted static Gaussian parameters across all frames.

#### Scenario: Rendering step can directly consume generated trajectory assets
- **WHEN** the system prepares a preset directory for control-map rendering
- **THEN** that directory contains a `custom_camera_trajectory.npz` file with an `extrinsics` array
- **THEN** that directory also contains a `custom_3D_gaussian_trajectory.json` file in the `metadata + frames` structure expected by the rendering script

#### Scenario: Static Gaussian parameters are repeated across the full video length
- **WHEN** the system converts fitted Gaussian parameters into a trajectory JSON for a static scene
- **THEN** each output frame entry contains the same per-object Gaussian mean and covariance values unless the user supplied a different object-motion source

### Requirement: Each preset SHALL render and generate outputs independently while reporting batch status
For each of the six preset directories, the system SHALL render control maps and run VerseCrafter video generation independently. The root output directory SHALL include a `manifest.json` file that records preset name mappings, resolved movement distances, trajectory depth values, stage status, output paths, and errors.

#### Scenario: One preset failure does not discard the others
- **WHEN** rendering or final video generation fails for one preset after the shared preprocessing stage has succeeded
- **THEN** the system records that preset as failed in `manifest.json`
- **THEN** the remaining presets continue running

#### Scenario: Successful preset outputs are discoverable from the manifest
- **WHEN** a preset finishes rendering and final video generation successfully
- **THEN** `manifest.json` records the preset name, numeric directory, and generated video output path for that preset

### Requirement: Unsupported zero-object scenes SHALL fail fast with an explicit error
If the fitted Gaussian result contains zero foreground objects, the system SHALL stop before trajectory rendering begins and SHALL report that the first version of this workflow requires at least one foreground object.

#### Scenario: Zero-object scene is rejected before rendering
- **WHEN** the shared Gaussian fitting output reports `num_objects = 0`
- **THEN** the system terminates the batch before creating trajectory rendering outputs
- **THEN** the error message states that zero-object scenes are not supported by this workflow version
