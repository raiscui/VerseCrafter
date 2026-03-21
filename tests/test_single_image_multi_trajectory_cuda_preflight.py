from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


def _load_batch_module():
    repo_root = Path(__file__).resolve().parents[1]
    inference_dir = repo_root / "inference"
    module_path = inference_dir / "single_image_multi_trajectory.py"

    if str(inference_dir) not in sys.path:
        sys.path.insert(0, str(inference_dir))

    spec = importlib.util.spec_from_file_location("single_image_multi_trajectory_test_module", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_nonempty_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_explain_why_cuda_is_needed_reports_generation_when_video_missing(tmp_path: Path) -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        resume=True,
        device="cpu",
        camera_only=True,
    )

    reason = module.explain_why_cuda_is_needed(
        args,
        output_root=tmp_path,
        active_preset_specs=[{"index": 0, "name": "left"}],
    )

    assert reason is not None
    assert "Step 6" in reason
    assert "left" in reason


def test_explain_why_cuda_is_needed_skips_when_resume_outputs_are_complete(tmp_path: Path) -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        resume=True,
        device="cpu",
        camera_only=True,
    )

    preset_dir = tmp_path / "0"
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

    reason = module.explain_why_cuda_is_needed(
        args,
        output_root=tmp_path,
        active_preset_specs=[{"index": 0, "name": "left"}],
    )

    assert reason is None


def test_ensure_cuda_runtime_ready_or_raise_surfaces_mig_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_batch_module()

    monkeypatch.setattr(
        module,
        "probe_torch_cuda_runtime",
        lambda: {
            "torch_version": "2.3.1",
            "compiled_cuda": "12.1",
            "cuda_available": False,
            "device_count": 1,
            "device_name_0_error": "RuntimeError('No CUDA GPUs are available')",
        },
    )
    monkeypatch.setattr(
        module,
        "detect_mig_no_instance_hint",
        lambda: "MIG 已开启, 但没有任何 MIG device.",
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.ensure_cuda_runtime_ready_or_raise(
            requested_device="cuda",
            required_reason="Step 6 最终视频生成依赖 CUDA",
        )

    message = str(exc_info.value)
    assert "CUDA 预检失败" in message
    assert "MIG 已开启" in message
    assert "--moge_pretrained" in message
