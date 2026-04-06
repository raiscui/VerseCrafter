from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
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
    sys.modules[spec.name] = module
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


def test_explain_why_multi_gpu_generation_is_needed_reports_missing_video(tmp_path: Path) -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        nproc_per_node=2,
    )

    reason = module.explain_why_multi_gpu_generation_is_needed(
        args,
        output_root=tmp_path,
        active_preset_specs=[{"index": 5, "name": "clockwise"}],
    )

    assert reason is not None
    assert "torchrun --nproc-per-node=2" in reason
    assert "clockwise" in reason


def test_ensure_requested_worker_topology_or_raise_rejects_insufficient_visible_gpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_batch_module()

    monkeypatch.setattr(
        module,
        "probe_torch_cuda_runtime",
        lambda: {
            "torch_version": "2.3.1",
            "compiled_cuda": "12.1",
            "cuda_visible_devices": None,
            "cuda_available": True,
            "device_count": 1,
            "device_name_0": "NVIDIA A800-SXM4-80GB",
        },
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.ensure_requested_worker_topology_or_raise(
            required_reason="Step 6 将以 torchrun --nproc-per-node=2 启动",
            nproc_per_node=2,
            ulysses_degree=2,
            ring_degree=1,
        )

    message = str(exc_info.value)
    assert "多卡预检失败" in message
    assert "torch.cuda.device_count(): 1" in message
    assert "--nproc-per-node: 2" in message
    assert "都改成 1" in message


def test_ensure_requested_worker_topology_or_raise_allows_sufficient_visible_gpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_batch_module()

    monkeypatch.setattr(
        module,
        "probe_torch_cuda_runtime",
        lambda: {
            "torch_version": "2.3.1",
            "compiled_cuda": "12.1",
            "cuda_visible_devices": "0,1",
            "cuda_available": True,
            "device_count": 2,
            "device_name_0": "NVIDIA A800-SXM4-80GB",
        },
    )

    module.ensure_requested_worker_topology_or_raise(
        required_reason="Step 6 将以 torchrun --nproc-per-node=2 启动",
        nproc_per_node=2,
        ulysses_degree=2,
        ring_degree=1,
    )


def test_ensure_multi_gpu_generation_backend_or_raise_surfaces_real_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_batch_module()

    monkeypatch.setattr(
        module,
        "probe_multi_gpu_generation_backend",
        lambda: {
            "videox_fun_path": "/repo/third_party/VideoX-Fun",
            "fuser_module": "/repo/third_party/VideoX-Fun/videox_fun/dist/fuser.py",
            "backend": "xfuser",
            "get_sp_group_available": False,
            "long_ctx_attention_available": False,
            "import_error": "ImportError('cannot import name x from y')",
            "import_traceback": "Traceback ...",
        },
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.ensure_multi_gpu_generation_backend_or_raise(
            required_reason="Step 6 将以 torchrun --nproc-per-node=2 启动",
        )

    message = str(exc_info.value)
    assert "多卡预检失败" in message
    assert "xFuser 后端不可用" in message
    assert "ImportError('cannot import name x from y')" in message
    assert "Traceback ..." in message


def test_create_parser_accepts_known_horizontal_fov_flags() -> None:
    module = _load_batch_module()

    args = module.create_parser().parse_args(
        [
            "--input_image_path",
            "demo.png",
            "--output_root",
            "output",
            "--prompt",
            "test prompt",
            "--known_horizontal_fov_degrees",
            "90",
            "--disable_auto_known_intrinsics",
        ]
    )

    assert args.known_horizontal_fov_degrees == 90.0
    assert args.disable_auto_known_intrinsics is True


def test_build_moge_command_passes_known_horizontal_fov_to_step1() -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        python_bin="python",
        input_image_path="demo.png",
        moge_version="v2",
        device="cuda",
        moge_pretrained=None,
        moge_fp16=False,
    )
    override_plan = module.IntrinsicOverridePlan(
        mode="known_horizontal_fov",
        source="cli",
        horizontal_fov_degrees=90.0,
    )

    command = module.build_moge_command(args, Path("estimated_depth"), override_plan)

    assert "--fov_x" in command
    assert command[command.index("--fov_x") + 1] == "90.0"


def test_build_generation_command_can_force_single_gpu_runtime() -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        nproc_per_node=2,
        torchrun_bin="torchrun",
        python_bin="python",
        transformer_path="model/VerseCrafter",
        negative_prompt="neg",
        input_image_path="demo.png",
        num_inference_steps=60,
        sample_size="720,1280",
        ulysses_degree=2,
        ring_degree=1,
        guidance_scale=5.0,
        seed=2025,
        fps=24,
        gpu_memory_mode="model_cpu_offload",
    )

    command = module.build_generation_command(
        args,
        generation_prompt="prompt",
        rendering_maps_dir=Path("maps"),
        save_path=Path("videos"),
        nproc_per_node_override=1,
        ulysses_degree_override=1,
        ring_degree_override=1,
    )

    assert command[:2] == ["python", "inference/versecrafter_inference.py"]
    assert "--ulysses_degree" in command
    assert command[command.index("--ulysses_degree") + 1] == "1"
    assert command[command.index("--ring_degree") + 1] == "1"


def test_run_generation_command_with_fallback_retries_single_gpu(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_batch_module()
    args = SimpleNamespace(
        nproc_per_node=2,
        torchrun_bin="torchrun",
        python_bin="python",
        transformer_path="model/VerseCrafter",
        negative_prompt="neg",
        input_image_path="demo.png",
        num_inference_steps=60,
        sample_size="720,1280",
        ulysses_degree=2,
        ring_degree=1,
        guidance_scale=5.0,
        seed=2025,
        fps=24,
        gpu_memory_mode="model_cpu_offload",
    )

    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path) -> None:
        commands.append(command)
        if len(commands) == 1:
            raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(module, "run_command", fake_run_command)

    status, activated = module.run_generation_command_with_fallback(
        args,
        generation_prompt="prompt",
        rendering_maps_dir=tmp_path / "maps",
        save_path=tmp_path / "videos",
        runtime_nproc_per_node=2,
        runtime_ulysses_degree=2,
        runtime_ring_degree=1,
    )

    assert status == "completed_single_gpu_fallback"
    assert activated is True
    assert commands[0][0] == "torchrun"
    assert commands[1][0] == "python"
    assert commands[1][commands[1].index("--ulysses_degree") + 1] == "1"
    assert commands[1][commands[1].index("--ring_degree") + 1] == "1"


def test_run_command_injects_detected_torch_cuda_arch_list(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_batch_module()
    monkeypatch.delenv("TORCH_CUDA_ARCH_LIST", raising=False)
    monkeypatch.setattr(module, "detect_machine_cuda_arch_list", lambda: "12.0")

    captured: dict[str, object] = {}

    def fake_subprocess_run(command, cwd, check, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        captured["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    module.run_command(["python", "script.py"], cwd=Path("/tmp/demo"))

    assert captured["command"] == ["python", "script.py"]
    assert captured["cwd"] == "/tmp/demo"
    assert captured["check"] is True
    assert captured["env"]["TORCH_CUDA_ARCH_LIST"] == "12.0"
