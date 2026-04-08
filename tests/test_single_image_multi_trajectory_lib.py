from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from inference.single_image_multi_trajectory_lib import (
    COORD_TRANSFORM_CV2BLENDER,
    build_generation_prompt,
    build_empty_gaussian_params_payload,
    build_normalized_intrinsic_from_horizontal_fov,
    convert_static_gaussian_json_to_trajectory,
    estimate_center_depth,
    generate_blender_camera_trajectory,
    get_preset_run_specs,
    make_blender_camera_to_world,
    select_preset_run_specs,
    sync_depth_intrinsics_npz,
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
        "clockwise_elliptical",
        "counterclockwise_1.5",
        "left_up",
        "right_up",
        "left_down",
        "right_down",
    ]
    assert np.allclose(
        [spec["movement_distance"] for spec in specs],
        [0.375, 0.375, 0.225, 0.525, 0.525, 0.75, 0.975, 0.75, 0.375, 0.375, 0.375, 0.375],
    )
    assert specs[0]["camera_motion_prompt"] == "Camera is moving to the left"
    assert specs[7]["camera_motion_prompt"] == "Camera is orbiting counterclockwise around the scene with a wider radius"
    assert specs[11]["camera_motion_prompt"] == "Camera is moving to the right and slightly downward"


def test_build_generation_prompt_appends_camera_motion_as_sentence() -> None:
    assert (
        build_generation_prompt("A cat is sitting on a chair", "Camera is moving to the left")
        == "A cat is sitting on a chair. Camera is moving to the left."
    )
    assert (
        build_generation_prompt("A cat is sitting on a chair.", "Camera is moving to the left")
        == "A cat is sitting on a chair. Camera is moving to the left."
    )


def test_select_preset_run_specs_normalizes_to_canonical_order() -> None:
    specs = get_preset_run_specs(1.5)

    selected = select_preset_run_specs(specs, [11, 8, 7, 0])

    assert [spec["index"] for spec in selected] == [0, 7, 8, 11]
    assert [spec["name"] for spec in selected] == ["left", "counterclockwise_1.5", "left_up", "right_down"]


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


def test_build_normalized_intrinsic_from_horizontal_fov_uses_centered_square_pixel_model() -> None:
    intrinsic = build_normalized_intrinsic_from_horizontal_fov(
        image_width=1920,
        image_height=1080,
        horizontal_fov_degrees=90.0,
    )

    assert np.allclose(
        intrinsic,
        np.array(
            [
                [0.5, 0.0, 0.5],
                [0.0, 960.0 / 1080.0, 0.5],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        ),
        atol=1e-6,
    )


def test_sync_depth_intrinsics_npz_can_override_and_restore_original_moge_intrinsic(tmp_path: Path) -> None:
    npz_path = tmp_path / "depth_intrinsics.npz"
    original_intrinsic = np.array(
        [
            [0.43408203, 0.0, 0.5],
            [0.0, 0.7714844, 0.5],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float16,
    )
    np.savez_compressed(
        npz_path,
        depth=np.full((1536, 2730), 2.0, dtype=np.float16),
        intrinsic=original_intrinsic,
    )

    override_result = sync_depth_intrinsics_npz(
        npz_path,
        horizontal_fov_degrees=90.0,
    )
    expected_override = build_normalized_intrinsic_from_horizontal_fov(
        image_width=2730,
        image_height=1536,
        horizontal_fov_degrees=90.0,
    )

    assert override_result["mode"] == "known_horizontal_fov"
    assert override_result["changed"] is True
    assert override_result["stored_moge_intrinsic"] is True
    assert np.allclose(override_result["effective_intrinsic"], expected_override, atol=5e-4)

    with np.load(npz_path) as overridden:
        assert "moge_intrinsic" in overridden.files
        assert np.allclose(overridden["intrinsic"], expected_override.astype(np.float16), atol=5e-4)
        assert np.allclose(overridden["moge_intrinsic"], original_intrinsic, atol=5e-4)

    restore_result = sync_depth_intrinsics_npz(
        npz_path,
        horizontal_fov_degrees=None,
    )

    assert restore_result["mode"] == "moge_predicted"
    assert restore_result["changed"] is True
    assert restore_result["restored_moge_intrinsic"] is True
    assert np.allclose(restore_result["effective_intrinsic"], original_intrinsic.astype(np.float32), atol=5e-4)

    with np.load(npz_path) as restored:
        assert np.allclose(restored["intrinsic"], original_intrinsic, atol=5e-4)
        assert np.allclose(restored["moge_intrinsic"], original_intrinsic, atol=5e-4)


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


def test_linear_trajectory_lead_in_holds_then_catches_up_to_original_path() -> None:
    common_kwargs = {
        "movement_distance": 0.5,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
    }

    baseline = generate_blender_camera_trajectory(
        "left",
        **common_kwargs,
        lead_in_frames=0,
        hold_frames=0,
    )
    eased = generate_blender_camera_trajectory(
        "left",
        **common_kwargs,
        lead_in_frames=5,
        hold_frames=2,
    )

    baseline_x = np.abs(baseline[:, 0, 3])
    eased_x = np.abs(eased[:, 0, 3])

    # 前两帧完全 hold 住, 开头不要立刻出现明显横向视差.
    assert np.isclose(eased_x[0], 0.0, atol=1e-6)
    assert np.isclose(eased_x[1], 0.0, atol=1e-6)

    # lead-in 期间的位移要明显小于原始轨迹, 但始终保持单调前进.
    assert eased_x[2] < baseline_x[2]
    assert eased_x[3] < baseline_x[3]
    assert eased_x[4] < baseline_x[4]
    assert np.all(np.diff(eased_x[:6]) >= -1e-6)

    # 到第 5 帧后要追平原始轨迹, 不要把整条镜头都拖慢.
    assert np.allclose(eased[5:, :3, 3], baseline[5:, :3, 3], atol=1e-6)


def test_generate_blender_camera_trajectory_defaults_to_no_lead_in() -> None:
    common_kwargs = {
        "movement_distance": 0.5,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
    }

    default_trajectory = generate_blender_camera_trajectory("left", **common_kwargs)
    explicit_no_lead_in = generate_blender_camera_trajectory(
        "left",
        **common_kwargs,
        lead_in_frames=0,
        hold_frames=0,
    )

    assert np.allclose(default_trajectory, explicit_no_lead_in, atol=1e-6)


def test_orbit_trajectory_lead_in_reduces_early_arc_motion_without_changing_tail() -> None:
    common_kwargs = {
        "movement_distance": 0.75,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
        "num_circles": 1,
    }

    baseline = generate_blender_camera_trajectory(
        "clockwise",
        **common_kwargs,
        lead_in_frames=0,
        hold_frames=0,
    )
    eased = generate_blender_camera_trajectory(
        "clockwise",
        **common_kwargs,
        lead_in_frames=5,
        hold_frames=2,
    )

    baseline_translations = baseline[:, :3, 3]
    eased_translations = eased[:, :3, 3]

    baseline_norm = np.linalg.norm(baseline_translations, axis=1)
    eased_norm = np.linalg.norm(eased_translations, axis=1)

    # orbit 同样应该在开头先稳一下, 再慢慢进入弧线.
    assert np.allclose(eased_translations[0], np.zeros(3, dtype=np.float32), atol=1e-6)
    assert np.allclose(eased_translations[1], np.zeros(3, dtype=np.float32), atol=1e-6)
    assert eased_norm[2] < baseline_norm[2]
    assert eased_norm[3] < baseline_norm[3]

    # 追平点之后要完全回到原轨迹, 保持尾段时长和构图不变.
    assert np.allclose(eased_translations[5:], baseline_translations[5:], atol=1e-6)


def test_orbit_radius_variants_preserve_scale_and_direction_metadata() -> None:
    common_kwargs = {
        "movement_distance": 0.75,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
        "num_circles": 1,
    }

    baseline = generate_blender_camera_trajectory("clockwise", **common_kwargs)
    smaller = generate_blender_camera_trajectory("clockwise_elliptical", **common_kwargs)
    wider_counterclockwise = generate_blender_camera_trajectory("counterclockwise_1.5", **common_kwargs)

    baseline_translations = baseline[:, :3, 3]
    smaller_translations = smaller[:, :3, 3]
    wider_counterclockwise_translations = wider_counterclockwise[:, :3, 3]

    assert np.allclose(smaller_translations[:, 1], 0.0, atol=1e-6)
    assert np.allclose(wider_counterclockwise_translations[:, 1], 0.0, atol=1e-6)

    # `clockwise_elliptical` 现在不只是半径变化,
    # 还带着更小的 orbit_direction, 所以不能再按逐帧等比例去比.
    # 这里改为验证“半径倍率”和“顺/逆时针方向”这两个真正稳定的契约.
    assert np.max(np.linalg.norm(smaller_translations, axis=1)) > np.max(np.linalg.norm(baseline_translations, axis=1))
    assert np.max(np.linalg.norm(wider_counterclockwise_translations, axis=1)) > np.max(np.linalg.norm(smaller_translations, axis=1))
    assert np.max(np.abs(smaller_translations[:, 0])) > np.max(np.abs(baseline_translations[:, 0]))
    assert np.max(np.abs(wider_counterclockwise_translations[:, 0])) > np.max(np.abs(smaller_translations[:, 0]))
    assert np.max(np.abs(smaller_translations[:, 2])) > np.max(np.abs(baseline_translations[:, 2]))
    assert np.max(np.abs(wider_counterclockwise_translations[:, 2])) > np.max(np.abs(smaller_translations[:, 2]))
    # 默认轨迹现在不再自动做 lead-in, 所以可以直接检查早期采样点的方向.
    assert baseline_translations[2, 2] < 0.0
    assert smaller_translations[2, 2] < 0.0
    assert wider_counterclockwise_translations[2, 2] > 0.0


def test_diagonal_linear_variants_preserve_horizontal_and_vertical_scales() -> None:
    common_kwargs = {
        "movement_distance": 0.5,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
    }

    left = generate_blender_camera_trajectory("left", **common_kwargs)
    right = generate_blender_camera_trajectory("right", **common_kwargs)
    up = generate_blender_camera_trajectory("up", **common_kwargs)
    left_up = generate_blender_camera_trajectory("left_up", **common_kwargs)
    right_up = generate_blender_camera_trajectory("right_up", **common_kwargs)
    left_down = generate_blender_camera_trajectory("left_down", **common_kwargs)
    right_down = generate_blender_camera_trajectory("right_down", **common_kwargs)

    left_translations = left[:, :3, 3]
    right_translations = right[:, :3, 3]
    up_translations = up[:, :3, 3]
    left_up_translations = left_up[:, :3, 3]
    right_up_translations = right_up[:, :3, 3]
    left_down_translations = left_down[:, :3, 3]
    right_down_translations = right_down[:, :3, 3]

    assert np.allclose(left_up_translations[:, 1], 0.0, atol=1e-6)
    assert np.allclose(right_up_translations[:, 1], 0.0, atol=1e-6)
    assert np.allclose(left_down_translations[:, 1], 0.0, atol=1e-6)
    assert np.allclose(right_down_translations[:, 1], 0.0, atol=1e-6)

    assert np.allclose(left_up_translations[:, 0], left_translations[:, 0], atol=1e-6)
    assert np.allclose(right_up_translations[:, 0], right_translations[:, 0], atol=1e-6)
    assert np.allclose(left_down_translations[:, 0], left_translations[:, 0], atol=1e-6)
    assert np.allclose(right_down_translations[:, 0], right_translations[:, 0], atol=1e-6)

    assert np.allclose(left_up_translations[:, 2], up_translations[:, 2] * 0.6, atol=1e-6)
    assert np.allclose(right_up_translations[:, 2], up_translations[:, 2] * 0.6, atol=1e-6)
    assert np.allclose(left_down_translations[:, 2], -up_translations[:, 2] * 0.8, atol=1e-6)
    assert np.allclose(right_down_translations[:, 2], -up_translations[:, 2] * 0.8, atol=1e-6)

    assert left_up_translations[-1, 2] > 0.0
    assert right_up_translations[-1, 2] > 0.0
    assert left_down_translations[-1, 2] < 0.0
    assert right_down_translations[-1, 2] < 0.0


def test_left_up_and_right_up_shift_center_facing_look_at_horizontally() -> None:
    common_kwargs = {
        "movement_distance": 0.5,
        "center_depth": 2.5,
        "translation_reference_depth": 1.0,
        "num_frames": 9,
    }

    left = generate_blender_camera_trajectory("left", **common_kwargs)
    right = generate_blender_camera_trajectory("right", **common_kwargs)
    left_up = generate_blender_camera_trajectory("left_up", **common_kwargs)
    right_up = generate_blender_camera_trajectory("right_up", **common_kwargs)

    def infer_target_x(matrices: np.ndarray) -> np.ndarray:
        positions = matrices[:, :3, 3]
        forwards = -matrices[:, :3, 2]

        # 这些 linear preset 都盯向 `y = center_depth` 这一张前方平面.
        # 因而可以通过射线与该平面的交点, 反推出实际 look-at 目标点的 X 偏移.
        target_scales = (common_kwargs["center_depth"] - positions[:, 1]) / forwards[:, 1]
        inferred_targets = positions + forwards * target_scales[:, None]
        return inferred_targets[:, 0]

    left_target_x = infer_target_x(left)
    right_target_x = infer_target_x(right)
    left_up_target_x = infer_target_x(left_up)
    right_up_target_x = infer_target_x(right_up)

    # `left` / `right` 现在也带有轻微水平注视偏移, 目的是让镜头语言更自然.
    assert np.allclose(left_target_x, -0.075, atol=1e-6)
    assert np.allclose(right_target_x, 0.075, atol=1e-6)
    assert np.all(left_up_target_x < -1e-6)
    assert np.all(right_up_target_x > 1e-6)

    # 偏移要能看出来, 但不能大到把目标点直接甩到极端侧面.
    assert np.max(np.abs(left_up_target_x)) < np.max(np.abs(left_up[:, 0, 3]))
    assert np.max(np.abs(right_up_target_x)) < np.max(np.abs(right_up[:, 0, 3]))


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
