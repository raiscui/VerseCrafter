from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import numpy as np


EXPECTED_PRESET_NAMES = [
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


def _write_nonempty_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_resume_smoke_skips_existing_outputs_and_completes(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "batch_output"
    shared_dir = output_root / "shared"
    estimated_depth_dir = shared_dir / "estimated_depth"
    foreground_masks_dir = shared_dir / "foreground_masks" / "masks"
    gaussian_output_dir = shared_dir / "fitted_3D_gaussian"

    estimated_depth_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        estimated_depth_dir / "depth_intrinsics.npz",
        depth=np.full((8, 8), 2.0, dtype=np.float16),
        intrinsic=np.eye(3, dtype=np.float16),
    )

    foreground_masks_dir.mkdir(parents=True, exist_ok=True)
    (foreground_masks_dir / "mask_01_object.png").write_bytes(b"mask")

    gaussian_output_dir.mkdir(parents=True, exist_ok=True)
    (gaussian_output_dir / "gaussian_params.json").write_text(
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
                "obj_id_to_color_idx": {"1": 0},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for preset_index in range(len(EXPECTED_PRESET_NAMES)):
        preset_dir = output_root / str(preset_index)
        render_dir = preset_dir / "rendering_4D_maps"
        generated_dir = preset_dir / "generated_videos"
        for file_name in [
            "background_RGB.mp4",
            "background_depth.mp4",
            "3D_gaussian_RGB.mp4",
            "3D_gaussian_depth.mp4",
            "merged_mask.mp4",
        ]:
            _write_nonempty_file(render_dir / file_name)
        _write_nonempty_file(generated_dir / "generated_video_0.mp4")

    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--resume",
    ]
    subprocess.run(command, cwd=str(Path(__file__).resolve().parents[1]), check=True)

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["shared"]["status"] == "skipped"
    assert sorted(int(index) for index in manifest["trajectories"].keys()) == list(range(len(EXPECTED_PRESET_NAMES)))
    for preset_index, preset_name in enumerate(EXPECTED_PRESET_NAMES):
        payload = manifest["trajectories"][str(preset_index)]
        assert payload["name"] == preset_name
        assert payload["camera_motion_prompt"]
        assert payload["generation_prompt"].startswith("test prompt")
        assert payload["status"] == "completed"
        assert payload["generation_status"] == "reused"
        assert payload["render_status"] == "reused"
        assert payload["generated_video_path"].endswith("generated_video_0.mp4")
    assert manifest["trajectories"]["0"]["generation_prompt"] == "test prompt. Camera is moving to the left."
    assert (
        manifest["trajectories"]["10"]["generation_prompt"]
        == "test prompt. Camera is moving to the left and slightly downward."
    )


def test_resume_smoke_skips_trajectory_when_final_video_exists_without_render_maps(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "batch_output"
    generated_dir = output_root / "0" / "generated_videos"
    _write_nonempty_file(generated_dir / "generated_video_0.mp4")

    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--resume",
        "--preset_indices",
        "0",
    ]
    subprocess.run(command, cwd=str(Path(__file__).resolve().parents[1]), check=True)

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    payload = manifest["trajectories"]["0"]
    assert manifest["status"] == "completed"
    assert manifest["shared"]["status"] == "skipped"
    assert payload["status"] == "completed"
    assert payload["trajectory_assets_status"] == "reused"
    assert payload["render_status"] == "reused"
    assert payload["generation_status"] == "reused"
    assert payload["generated_video_path"].endswith("generated_video_0.mp4")
    assert not (output_root / "0" / "rendering_4D_maps").exists()
    assert not (output_root / "shared").exists()


def test_dry_run_includes_safe_gpu_memory_mode_for_generation(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "dry_run_output"
    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--gpu_memory_mode model_cpu_offload_and_qfloat8" in result.stdout
    assert "- [6] clockwise_elliptical" in result.stdout
    assert "- [7] counterclockwise_1.5" in result.stdout
    assert "- [8] left_up" in result.stdout
    assert "- [11] right_down" in result.stdout
    assert "generation_prompt: test prompt. Camera is moving to the left." in result.stdout
    assert "generation_prompt: test prompt. Camera is moving to the right and slightly downward." in result.stdout
    assert "--prompt 'test prompt. Camera is moving to the left.'" in result.stdout


def test_camera_only_dry_run_skips_foreground_pipeline(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "camera_only_output"
    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--camera_only",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "camera_only: True" in result.stdout
    assert "camera_only_empty" in result.stdout
    assert "skip foreground segmentation" in result.stdout
    assert "num_objects=0 placeholder JSON" in result.stdout


def test_dry_run_can_limit_execution_to_selected_presets(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "subset_output"
    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--preset_indices",
        "11",
        "8",
        "0",
        "7",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_preset_indices: [0, 7, 8, 11]" in result.stdout
    assert "- [0] left" in result.stdout
    assert "- [7] counterclockwise_1.5" in result.stdout
    assert "- [8] left_up" in result.stdout
    assert "- [11] right_down" in result.stdout
    assert "generation_prompt: test prompt. Camera is moving to the left." in result.stdout
    assert "generation_prompt: test prompt. Camera is orbiting counterclockwise around the scene with a wider radius." in result.stdout
    assert "generation_prompt: test prompt. Camera is moving to the left and upward." in result.stdout
    assert "generation_prompt: test prompt. Camera is moving to the right and slightly downward." in result.stdout
    assert "--prompt 'test prompt. Camera is moving to the right and slightly downward.'" in result.stdout
    assert "- [1] right" not in result.stdout
    assert "- [2] up" not in result.stdout
    assert "- [10] left_down" not in result.stdout


def test_dry_run_auto_detects_my_series_and_announces_known_fov_override(tmp_path: Path) -> None:
    input_dir = tmp_path / "my7"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_image = input_dir / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "my7"
    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "- intrinsics: known_horizontal_fov (90.0 deg horizontal FOV)" in result.stdout
    assert "auto-matched known 3ds Max series 'my7'" in result.stdout


def test_dry_run_explicit_known_horizontal_fov_flows_into_step1_command(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "explicit_fov_output"
    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--known_horizontal_fov_degrees",
        "90",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "- intrinsics: known_horizontal_fov (90.0 deg horizontal FOV)" in result.stdout
    assert "--fov_x 90.0" in result.stdout


def test_known_horizontal_fov_dry_run_invalidates_legacy_reused_depth_without_matching_metadata(
    tmp_path: Path,
) -> None:
    input_image = tmp_path / "input.png"
    input_image.write_bytes(b"fake")

    output_root = tmp_path / "legacy_depth_output"
    estimated_depth_dir = output_root / "shared" / "estimated_depth"
    estimated_depth_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        estimated_depth_dir / "depth_intrinsics.npz",
        depth=np.full((8, 8), 2.0, dtype=np.float16),
        intrinsic=np.eye(3, dtype=np.float16),
    )
    preset_dir = output_root / "0"
    render_dir = preset_dir / "rendering_4D_maps"
    generated_dir = preset_dir / "generated_videos"
    for file_name in [
        "background_RGB.mp4",
        "background_depth.mp4",
        "3D_gaussian_RGB.mp4",
        "3D_gaussian_depth.mp4",
        "merged_mask.mp4",
    ]:
        _write_nonempty_file(render_dir / file_name)
    _write_nonempty_file(generated_dir / "generated_video_0.mp4")

    command = [
        sys.executable,
        "inference/single_image_multi_trajectory.py",
        "--input_image_path",
        str(input_image),
        "--output_root",
        str(output_root),
        "--prompt",
        "test prompt",
        "--known_horizontal_fov_degrees",
        "90",
        "--preset_indices",
        "0",
        "--dry_run",
    ]

    result = subprocess.run(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "- skipped: all selected trajectories already have generated_video_*.mp4" in result.stdout
    assert "- intrinsics: known_horizontal_fov (90.0 deg horizontal FOV)" in result.stdout
    assert "  render: reuse ->" in result.stdout
    assert "  generation: reuse ->" in result.stdout
