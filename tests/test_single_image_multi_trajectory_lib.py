from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from inference.single_image_multi_trajectory_lib import (
    COORD_TRANSFORM_CV2BLENDER,
    build_empty_gaussian_params_payload,
    convert_static_gaussian_json_to_trajectory,
    estimate_center_depth,
    generate_blender_camera_trajectory,
    get_preset_run_specs,
    make_blender_camera_to_world,
    select_preset_run_specs,
)


def test_get_preset_run_specs_uses_deterministic_midpoint_distances() -> None:
    specs = get_preset_run_specs(1.5)

    assert [spec["name"] for spec in specs] == [
        "left",
        "right",
        "up",
        "zoom_out",
        "zoom_in",
        "clockwise",
    ]
    assert np.allclose(
        [spec["movement_distance"] for spec in specs],
        [0.375, 0.375, 0.225, 0.525, 0.525, 0.75],
    )


def test_select_preset_run_specs_normalizes_to_canonical_order() -> None:
    specs = get_preset_run_specs(1.5)

    selected = select_preset_run_specs(specs, [5, 0, 3])

    assert [spec["index"] for spec in selected] == [0, 3, 5]
    assert [spec["name"] for spec in selected] == ["left", "zoom_out", "clockwise"]


def test_select_preset_run_specs_rejects_duplicate_indices() -> None:
    specs = get_preset_run_specs(1.5)

    try:
        select_preset_run_specs(specs, [0, 0])
    except ValueError as error:
        assert "must not contain duplicates" in str(error)
    else:
        raise AssertionError("expected duplicate preset indices to raise ValueError")


def test_estimate_center_depth_prefers_center_crop_quantile() -> None:
    depth = np.full((8, 8), 100.0, dtype=np.float32)
    center_patch = np.array(
        [
            [2.0, 3.0, 4.0, 5.0],
            [3.0, 4.0, 5.0, 6.0],
            [4.0, 5.0, 6.0, 7.0],
            [5.0, 6.0, 7.0, 8.0],
        ],
        dtype=np.float32,
    )
    depth[2:6, 2:6] = center_patch

    estimated = estimate_center_depth(depth, depth_quantile=0.2, center_crop_ratio=0.5)

    assert np.isclose(estimated, np.quantile(center_patch.reshape(-1), 0.2))


def test_make_blender_camera_to_world_matches_default_forward_direction() -> None:
    c2w = make_blender_camera_to_world(
        position=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        target=np.array([0.0, 1.0, 0.0], dtype=np.float32),
    )

    assert np.allclose(c2w[:3, 0], np.array([1.0, 0.0, 0.0], dtype=np.float32))
    assert np.allclose(c2w[:3, 1], np.array([0.0, 0.0, 1.0], dtype=np.float32))
    assert np.allclose(c2w[:3, 2], np.array([0.0, -1.0, 0.0], dtype=np.float32))


def test_generate_blender_camera_trajectory_preserves_expected_axis_mapping() -> None:
    common_kwargs = {
        "movement_distance": 0.5,
        "center_depth": 2.0,
        "translation_reference_depth": 1.0,
        "num_frames": 5,
    }

    left = generate_blender_camera_trajectory("left", **common_kwargs)
    right = generate_blender_camera_trajectory("right", **common_kwargs)
    up = generate_blender_camera_trajectory("up", **common_kwargs)
    zoom_in = generate_blender_camera_trajectory("zoom_in", **common_kwargs)
    zoom_out = generate_blender_camera_trajectory("zoom_out", **common_kwargs)

    assert left[-1, 0, 3] < 0
    assert right[-1, 0, 3] > 0
    assert np.isclose(up[-1, 1, 3], 0.0)
    assert up[-1, 2, 3] > 0
    assert zoom_in[-1, 1, 3] > 0
    assert zoom_out[-1, 1, 3] < 0


def test_clockwise_trajectory_orbits_in_blender_xz_plane() -> None:
    clockwise = generate_blender_camera_trajectory(
        "clockwise",
        movement_distance=0.75,
        center_depth=2.5,
        translation_reference_depth=1.0,
        num_frames=9,
    )

    translations = clockwise[:, :3, 3]
    assert np.allclose(translations[:, 1], 0.0, atol=1e-6)
    assert np.allclose(translations[0], translations[-1], atol=1e-6)
    assert np.max(np.abs(translations[:, 2])) > 0.0


def test_convert_static_gaussian_json_to_trajectory_repeats_frames_and_transforms_coords(tmp_path: Path) -> None:
    source_path = tmp_path / "gaussian_params.json"
    output_path = tmp_path / "custom_3D_gaussian_trajectory.json"
    source_path.write_text(
        json.dumps(
            {
                "gaussian_params": {
                    "1": {
                        "label": "car",
                        "mean": [1.0, 2.0, 3.0],
                        "cov": [[1.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 9.0]],
                    }
                },
                "num_objects": 1,
                "obj_id_to_color_idx": {"1": 7},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = convert_static_gaussian_json_to_trajectory(source_path, output_path, num_frames=3)

    assert payload["metadata"]["num_objects"] == 1
    assert payload["metadata"]["num_frames"] == 3
    assert len(payload["frames"]) == 3
    first_object = payload["frames"][0]["objects"][0]
    assert first_object["object_id"] == "1"
    assert first_object["color_index"] == 7
    assert np.allclose(first_object["gaussian_3d"]["mean"], [1.0, 3.0, -2.0])

    expected_cov = COORD_TRANSFORM_CV2BLENDER @ np.diag([1.0, 4.0, 9.0]) @ COORD_TRANSFORM_CV2BLENDER.T
    assert np.allclose(first_object["gaussian_3d"]["covariance"], expected_cov)
    saved_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_payload == payload


def test_convert_static_gaussian_json_to_trajectory_supports_camera_only_empty_foreground(tmp_path: Path) -> None:
    source_path = tmp_path / "gaussian_params.json"
    output_path = tmp_path / "custom_3D_gaussian_trajectory.json"
    source_path.write_text(
        json.dumps(
            build_empty_gaussian_params_payload(
                depth_shape=(720, 1280),
                intrinsic=np.eye(3, dtype=np.float32),
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = convert_static_gaussian_json_to_trajectory(source_path, output_path, num_frames=3)

    assert payload["metadata"]["num_objects"] == 0
    assert len(payload["frames"]) == 3
    assert all(frame["objects"] == [] for frame in payload["frames"])
