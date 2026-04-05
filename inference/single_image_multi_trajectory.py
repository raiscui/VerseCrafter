from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any

import numpy as np

from single_image_multi_trajectory_lib import (
    DEFAULT_NUM_CIRCLES,
    DEFAULT_NUM_FRAMES,
    DEFAULT_RADIUS_X_FACTOR,
    DEFAULT_RADIUS_Y_FACTOR,
    PRESET_INDEX_CHOICES,
    build_generation_prompt,
    build_empty_gaussian_params_payload,
    build_normalized_intrinsic_from_horizontal_fov,
    convert_static_gaussian_json_to_trajectory,
    ensure_parent_dir,
    estimate_center_depth,
    find_generated_video,
    generate_blender_camera_trajectory,
    get_preset_run_specs,
    is_existing_nonempty_file,
    is_valid_render_output_dir,
    load_depth_and_intrinsic,
    resolve_translation_reference_depth,
    select_preset_run_specs,
    sync_depth_intrinsics_npz,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE_NAME = "manifest.json"
AUTO_KNOWN_3DSMAX_HORIZONTAL_FOV_DEGREES = 90.0
AUTO_KNOWN_3DSMAX_SERIES_PATTERN = re.compile(r"^(my|nt)\d", re.IGNORECASE)


@dataclass(frozen=True)
class IntrinsicOverridePlan:
    """描述本次运行对共享内参的期望来源."""

    mode: str
    source: str
    horizontal_fov_degrees: float | None = None
    matched_series_name: str | None = None


# ============================================================================
# Manifest helpers
# ============================================================================
def utc_now_iso() -> str:
    """返回 UTC ISO 时间戳."""

    return datetime.now(timezone.utc).isoformat()


def load_manifest(manifest_path: Path) -> dict[str, Any] | None:
    """读取已有 manifest.

    这里把 manifest 当成当前工作流的“外部记忆”.
    但 resume 时仍会结合真实文件状态再做二次校验,
    避免只看 JSON 把残缺输出误判为成功.
    """

    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Manifest exists but is invalid JSON: %s", manifest_path)
        return None


def save_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    """原子化写回 manifest."""

    manifest["updated_at"] = utc_now_iso()
    ensure_parent_dir(manifest_path)
    temp_path = manifest_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(manifest_path)


def build_manifest(
    args: argparse.Namespace,
    output_root: Path,
    preset_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    """初始化 manifest 基础结构."""

    trajectories: dict[str, Any] = {}
    for preset in preset_specs:
        index_text = str(preset["index"])
        preset_dir = output_root / index_text
        trajectories[index_text] = {
            "index": preset["index"],
            "name": preset["name"],
            "camera_motion_prompt": preset["camera_motion_prompt"],
            "generation_prompt": build_generation_prompt(args.prompt, preset["camera_motion_prompt"]),
            "movement_distance_range": preset["movement_distance_range"],
            "movement_distance": preset["movement_distance"],
            "center_depth": None,
            "translation_reference_depth": None,
            "directory": str(preset_dir),
            "trajectory_npz": str(preset_dir / "custom_camera_trajectory.npz"),
            "ellipsoid_json": str(preset_dir / "custom_3D_gaussian_trajectory.json"),
            "rendering_maps_dir": str(preset_dir / "rendering_4D_maps"),
            "generated_videos_dir": str(preset_dir / "generated_videos"),
            "generated_video_path": None,
            "trajectory_assets_status": "pending",
            "render_status": "pending",
            "generation_status": "pending",
            "status": "pending",
            "error": None,
        }

    return {
        "version": 1,
        "change": "add-versecrafter-single-image-multi-trajectory-script",
        "status": "running",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "input": {
            "input_image_path": str(Path(args.input_image_path).resolve()),
            "output_root": str(output_root.resolve()),
            "prompt": args.prompt,
            "object_prompt": args.object_prompt,
            "transformer_path": args.transformer_path,
        },
        "settings": {
            "camera_only": args.camera_only,
            "moge_version": args.moge_version,
            "moge_pretrained": args.moge_pretrained,
            "known_horizontal_fov_degrees": args.known_horizontal_fov_degrees,
            "disable_auto_known_intrinsics": args.disable_auto_known_intrinsics,
            "device": args.device,
            "sample_size": args.sample_size,
            "render_sample_size": args.render_sample_size,
            "num_inference_steps": args.num_inference_steps,
            "ulysses_degree": args.ulysses_degree,
            "ring_degree": args.ring_degree,
            "nproc_per_node": args.nproc_per_node,
            "guidance_scale": args.guidance_scale,
            "seed": args.seed,
            "fps": args.fps,
            "gpu_memory_mode": args.gpu_memory_mode,
            "render_background_point_limit": args.render_background_point_limit,
            "selected_preset_indices": None if args.preset_indices is None else list(args.preset_indices),
            "auto_center_depth_quantile": args.auto_center_depth_quantile,
            "auto_center_depth_center_crop_ratio": args.auto_center_depth_center_crop_ratio,
            "translation_reference_depth_scale": args.translation_reference_depth_scale,
            "total_movement_distance_factor": args.total_movement_distance_factor,
            "camera_rotation": args.camera_rotation,
            "radius_x_factor": args.radius_x_factor,
            "radius_y_factor": args.radius_y_factor,
            "num_circles": args.num_circles,
            "resume": args.resume,
        },
        "shared": {
            "directory": str((output_root / "shared").resolve()),
            "estimated_depth_dir": str((output_root / "shared" / "estimated_depth").resolve()),
            "foreground_masks_dir": str((output_root / "shared" / "foreground_masks").resolve()),
            "masks_dir": str((output_root / "shared" / "foreground_masks" / "masks").resolve()),
            "fitted_3d_gaussian_dir": str((output_root / "shared" / "fitted_3D_gaussian").resolve()),
            "depth_npz": str((output_root / "shared" / "estimated_depth" / "depth_intrinsics.npz").resolve()),
            "gaussian_json": str((output_root / "shared" / "fitted_3D_gaussian" / "gaussian_params.json").resolve()),
            "depth_status": "pending",
            "intrinsic_status": "pending",
            "intrinsic_mode": "pending",
            "intrinsic_source": "pending",
            "effective_horizontal_fov_degrees": None,
            "effective_intrinsic": None,
            "segmentation_status": "pending",
            "gaussian_status": "pending",
            "status": "pending",
            "error": None,
        },
        "trajectories": trajectories,
    }


# ============================================================================
# Runtime helpers
# ============================================================================
def parse_sample_size(sample_size: str) -> tuple[int, int]:
    """解析 `HxW` 文本."""

    parts = [part.strip() for part in sample_size.split(",")]
    if len(parts) != 2:
        raise ValueError(f"sample_size must be 'height,width', got: {sample_size}")
    return int(parts[0]), int(parts[1])


def validate_generation_sample_size(height: int, width: int) -> None:
    """验证最终生成尺寸是否满足 VerseCrafter 的块对齐要求.

    当前管线里的 GeoAda mask 编码会按 `16` 的倍数对高宽做分块.
    如果传入例如 `360,640`, 深层 reshape 才会抛出晦涩的 shape mismatch.
    这里提前拦截, 把错误收敛成可读的参数约束.
    """

    if height % 16 != 0 or width % 16 != 0:
        raise ValueError(
            "sample_size height and width must both be multiples of 16 for VerseCrafter generation; "
            f"got {height},{width}."
        )


def ensure_clean_path(path: Path, *, keep_if_missing: bool = True) -> None:
    """在非 resume 模式下清空旧目录或旧文件."""

    if keep_if_missing and not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def looks_like_known_3dsmax_series_name(name: str) -> bool:
    """判断名字是否匹配当前已知的 3ds Max 渲染系列.

    这里先只收 `my*` / `nt*` 这两类用户已经明确说明的系列.
    用正则约束到“前缀 + 数字”, 避免把普通单词误识别进来.
    """

    return bool(AUTO_KNOWN_3DSMAX_SERIES_PATTERN.match(name.strip().lower()))


def resolve_intrinsic_override_plan(
    args: argparse.Namespace,
    *,
    output_root: Path,
) -> IntrinsicOverridePlan:
    """解析这次运行应使用哪种共享内参来源."""

    if args.known_horizontal_fov_degrees is not None:
        return IntrinsicOverridePlan(
            mode="known_horizontal_fov",
            source="cli",
            horizontal_fov_degrees=float(args.known_horizontal_fov_degrees),
        )

    if args.disable_auto_known_intrinsics:
        return IntrinsicOverridePlan(
            mode="moge_predicted",
            source="auto_disabled",
        )

    candidate_names = [
        output_root.name,
        Path(args.input_image_path).parent.name,
    ]
    for candidate_name in candidate_names:
        if candidate_name and looks_like_known_3dsmax_series_name(candidate_name):
            return IntrinsicOverridePlan(
                mode="known_horizontal_fov",
                source="auto_series_my_nt",
                horizontal_fov_degrees=AUTO_KNOWN_3DSMAX_HORIZONTAL_FOV_DEGREES,
                matched_series_name=candidate_name,
            )

    return IntrinsicOverridePlan(
        mode="moge_predicted",
        source="moge_default",
    )


def sync_shared_intrinsics(
    *,
    depth_npz_path: Path,
    override_plan: IntrinsicOverridePlan,
) -> dict[str, Any]:
    """让共享 `depth_intrinsics.npz` 的 `intrinsic` 与本次策略保持一致."""

    horizontal_fov_degrees = (
        None
        if override_plan.mode != "known_horizontal_fov"
        else override_plan.horizontal_fov_degrees
    )
    sync_result = sync_depth_intrinsics_npz(
        depth_npz_path,
        horizontal_fov_degrees=horizontal_fov_degrees,
    )
    sync_result["plan_mode"] = override_plan.mode
    sync_result["plan_source"] = override_plan.source
    sync_result["matched_series_name"] = override_plan.matched_series_name
    return sync_result


def preview_shared_intrinsics(
    *,
    depth_npz_path: Path,
    override_plan: IntrinsicOverridePlan,
) -> dict[str, Any]:
    """只预览共享内参是否会变化, 不落盘."""

    depth_map, intrinsic = load_depth_and_intrinsic(depth_npz_path)
    with np.load(depth_npz_path) as data:
        stored_moge_intrinsic = (
            None
            if "moge_intrinsic" not in data.files
            else np.asarray(data["moge_intrinsic"], dtype=np.float32)
        )

    if override_plan.mode == "known_horizontal_fov":
        base_intrinsic = build_normalized_intrinsic_from_horizontal_fov(
            image_width=int(depth_map.shape[-1]),
            image_height=int(depth_map.shape[-2]),
            horizontal_fov_degrees=float(override_plan.horizontal_fov_degrees),
        )
        target_intrinsic = (
            np.repeat(base_intrinsic[None, :, :], intrinsic.shape[0], axis=0)
            if intrinsic.ndim == 3
            else base_intrinsic
        )
    else:
        target_intrinsic = intrinsic if stored_moge_intrinsic is None else stored_moge_intrinsic

    return {
        "changed": not np.allclose(intrinsic, target_intrinsic, atol=1e-6),
        "effective_intrinsic": target_intrinsic.astype(np.float32),
    }


def run_command(command: list[str], *, cwd: Path) -> None:
    """执行子命令并在失败时抛错.

    Context7 也确认了 `subprocess.run(..., check=True)` 是标准写法.
    这里统一收口, 便于 manifest 记录和日志排查.
    """

    logger.info("Running command: %s", shlex.join(command))
    subprocess.run(command, cwd=str(cwd), check=True)


def is_cuda_device(device_name: str) -> bool:
    """判断当前 device 字符串是否指向 CUDA."""

    normalized = device_name.strip().lower()
    return normalized == "cuda" or normalized.startswith("cuda:")


def probe_torch_cuda_runtime() -> dict[str, Any]:
    """读取当前 Python 进程里的 Torch CUDA 可用性.

    这里故意只做最小探测.
    目标不是替代完整诊断工具,
    而是在真正开跑前尽早发现“CUDA 根本不可初始化”的情况.
    """

    payload: dict[str, Any] = {}
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        payload["torch_import_error"] = repr(exc)
        return payload

    payload["torch_version"] = getattr(torch, "__version__", "unknown")
    payload["compiled_cuda"] = getattr(torch.version, "cuda", None)
    payload["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")

    try:
        payload["cuda_available"] = bool(torch.cuda.is_available())
    except Exception as exc:  # noqa: BLE001
        payload["cuda_available_error"] = repr(exc)

    try:
        payload["device_count"] = int(torch.cuda.device_count())
    except Exception as exc:  # noqa: BLE001
        payload["device_count_error"] = repr(exc)

    try:
        payload["device_name_0"] = torch.cuda.get_device_name(0)
    except Exception as exc:  # noqa: BLE001
        payload["device_name_0_error"] = repr(exc)

    return payload


def detect_mig_no_instance_hint() -> str | None:
    """检查 `nvidia-smi` 是否处于“MIG 已开但没有实例”的高风险状态."""

    nvidia_smi_bin = shutil.which("nvidia-smi")
    if nvidia_smi_bin is None:
        return None

    # 这里同时读取 summary 和 detail.
    # summary 里容易看到 "No MIG devices found", detail 里容易看到 MIG 是否 Enabled.
    summary_result = subprocess.run(
        [nvidia_smi_bin],
        check=False,
        capture_output=True,
        text=True,
    )
    detail_result = subprocess.run(
        [nvidia_smi_bin, "-q"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined_output = "\n".join(
        part
        for part in [
            summary_result.stdout,
            summary_result.stderr,
            detail_result.stdout,
            detail_result.stderr,
        ]
        if part
    )

    if (
        "MIG Mode" in combined_output
        and "Current                           : Enabled" in combined_output
        and "No MIG devices found" in combined_output
    ):
        return (
            "nvidia-smi 显示 GPU 已启用 MIG, 但当前没有任何 MIG device. "
            "这种状态下 CUDA workload 通常拿不到可执行设备. "
            "需要先创建 GPU instance / compute instance, 或关闭 MIG 后再重试."
        )

    return None


def explain_why_cuda_is_needed(
    args: argparse.Namespace,
    *,
    output_root: Path,
    active_preset_specs: list[dict[str, Any]],
) -> str | None:
    """判断这次运行是否真的需要 CUDA.

    这里特意把“是否需要 CUDA”拆成两类:
    1. Step 6 最终生成一定依赖 CUDA.
    2. Step 1/2/3/5 是否依赖 CUDA, 取决于 `--device`.
    这样就不会把“所有输出都已复用”的 resume 场景误判成必须要 GPU.
    """

    if not args.resume:
        return "resume 已关闭, 本次会重新执行 Step 6 最终视频生成, 而 VerseCrafter generation 依赖 CUDA"

    for preset in active_preset_specs:
        preset_dir = output_root / str(preset["index"])
        generated_videos_dir = preset_dir / "generated_videos"
        if find_generated_video(generated_videos_dir) is None:
            return (
                f"preset {preset['index']} ({preset['name']}) 缺少最终生成视频, "
                "本次会执行 Step 6 最终视频生成, 而 VerseCrafter generation 依赖 CUDA"
            )

    if not is_cuda_device(args.device):
        return None

    shared_dir = output_root / "shared"
    estimated_depth_dir = shared_dir / "estimated_depth"
    foreground_masks_dir = shared_dir / "foreground_masks"
    masks_dir = foreground_masks_dir / "masks"
    gaussian_output_dir = shared_dir / "fitted_3D_gaussian"
    depth_npz_path = estimated_depth_dir / "depth_intrinsics.npz"
    gaussian_json_path = gaussian_output_dir / "gaussian_params.json"

    if not is_existing_nonempty_file(depth_npz_path):
        return f"共享深度估计缺失, 本次会以 --device {args.device} 执行 Step 1"

    if args.camera_only:
        if not is_camera_only_mask_dir(masks_dir) or not is_camera_only_gaussian_json(gaussian_json_path):
            return f"camera-only 共享产物缺失, 本次会以 --device {args.device} 继续预处理阶段"
    else:
        if not has_mask_pngs(masks_dir):
            return f"前景分割结果缺失, 本次会以 --device {args.device} 执行 Step 2"
        if not is_existing_nonempty_file(gaussian_json_path):
            return f"3D Gaussian 拟合结果缺失, 本次会以 --device {args.device} 执行 Step 3"

    for preset in active_preset_specs:
        preset_dir = output_root / str(preset["index"])
        rendering_maps_dir = preset_dir / "rendering_4D_maps"
        generated_videos_dir = preset_dir / "generated_videos"
        existing_video = find_generated_video(generated_videos_dir)
        if existing_video is not None and not is_valid_render_output_dir(rendering_maps_dir):
            return (
                f"preset {preset['index']} ({preset['name']}) 缺少完整的 rendering_4D_maps, "
                f"本次会以 --device {args.device} 执行 Step 5"
            )

    return None


def explain_why_multi_gpu_generation_is_needed(
    args: argparse.Namespace,
    *,
    output_root: Path,
    active_preset_specs: list[dict[str, Any]],
) -> str | None:
    """判断这次运行是否真的会进入多进程 Step 6.

    这里不关心 Step 1~5.
    我们只回答一件事:
    当前这次执行里, 是否会真的启动 `torchrun --nproc-per-node > 1`
    去跑最终视频生成.
    """

    if args.nproc_per_node <= 1:
        return None

    for preset in active_preset_specs:
        preset_dir = output_root / str(preset["index"])
        generated_videos_dir = preset_dir / "generated_videos"
        if find_generated_video(generated_videos_dir) is None:
            return (
                f"preset {preset['index']} ({preset['name']}) 缺少最终生成视频, "
                f"本次会以 torchrun --nproc-per-node={args.nproc_per_node} 执行 Step 6"
            )

    return None


def build_cuda_preflight_error_message(
    *,
    requested_device: str,
    required_reason: str,
    probe_payload: dict[str, Any],
    mig_hint: str | None,
) -> str:
    """拼出更可读的 CUDA 预检报错."""

    lines = [
        "CUDA 预检失败: 当前工作流接下来需要可用的 CUDA, 但当前 Python / Torch 进程不能成功初始化 CUDA.",
        f"- 触发原因: {required_reason}",
        f"- 预处理参数 --device: {requested_device}",
        f"- torch 版本: {probe_payload.get('torch_version', 'unknown')}",
        f"- torch 编译 CUDA: {probe_payload.get('compiled_cuda', 'unknown')}",
        f"- CUDA_VISIBLE_DEVICES: {probe_payload.get('cuda_visible_devices', 'unset')}",
        f"- torch.cuda.is_available(): {probe_payload.get('cuda_available', probe_payload.get('cuda_available_error', 'unknown'))}",
        f"- torch.cuda.device_count(): {probe_payload.get('device_count', probe_payload.get('device_count_error', 'unknown'))}",
        f"- torch.cuda.get_device_name(0): {probe_payload.get('device_name_0', probe_payload.get('device_name_0_error', 'unknown'))}",
    ]

    if "torch_import_error" in probe_payload:
        lines.append(f"- torch 导入失败: {probe_payload['torch_import_error']}")

    if mig_hint is not None:
        lines.append(f"- MIG 提示: {mig_hint}")

    lines.extend(
        [
            "- 说明: 仅修改 --moge_pretrained 或 --moge_version 不会解决这里的失败, 因为错误发生在 CUDA 初始化阶段, 还没真正进入模型权重推理.",
            "- 建议: 先让当前环境出现一个可被 CUDA 使用的设备, 然后再重跑本批处理.",
        ]
    )
    return "\n".join(lines)


def ensure_cuda_runtime_ready_or_raise(
    *,
    requested_device: str,
    required_reason: str,
) -> None:
    """在真正起重流程前确认 CUDA 运行时可用."""

    probe_payload = probe_torch_cuda_runtime()
    if probe_payload.get("cuda_available") is True:
        return

    raise RuntimeError(
        build_cuda_preflight_error_message(
            requested_device=requested_device,
            required_reason=required_reason,
            probe_payload=probe_payload,
            mig_hint=detect_mig_no_instance_hint(),
        )
    )


def build_multi_gpu_preflight_error_message(
    *,
    required_reason: str,
    nproc_per_node: int,
    ulysses_degree: int,
    ring_degree: int,
    probe_payload: dict[str, Any],
) -> str:
    """拼出多卡 worker 拓扑不匹配时的清晰报错."""

    lines = [
        "多卡预检失败: 当前 Step 6 计划启动多进程 CUDA 推理, 但当前 Python / Torch 进程可见的本地 CUDA 设备数量不足.",
        f"- 触发原因: {required_reason}",
        f"- 请求的 torchrun --nproc-per-node: {nproc_per_node}",
        f"- 请求的 ulysses_degree * ring_degree: {ulysses_degree} * {ring_degree} = {ulysses_degree * ring_degree}",
        f"- CUDA_VISIBLE_DEVICES: {probe_payload.get('cuda_visible_devices', 'unset')}",
        f"- torch 版本: {probe_payload.get('torch_version', 'unknown')}",
        f"- torch 编译 CUDA: {probe_payload.get('compiled_cuda', 'unknown')}",
        f"- torch.cuda.is_available(): {probe_payload.get('cuda_available', probe_payload.get('cuda_available_error', 'unknown'))}",
        f"- torch.cuda.device_count(): {probe_payload.get('device_count', probe_payload.get('device_count_error', 'unknown'))}",
        f"- torch.cuda.get_device_name(0): {probe_payload.get('device_name_0', probe_payload.get('device_name_0_error', 'unknown'))}",
    ]

    visible_device_count = probe_payload.get("device_count")
    if isinstance(visible_device_count, int):
        lines.append(
            f"- 结论: 当前仅有 {visible_device_count} 张可见 CUDA 设备, "
            f"但请求了 {nproc_per_node} 个本地 worker. "
            f"当 local_rank >= {visible_device_count} 时, 对应进程会尝试访问不存在的 cuda:{visible_device_count} 及以上设备."
        )
    else:
        lines.append("- 结论: 当前无法可靠探测可见 CUDA 设备数量, 因而不能安全启动多进程 Step 6.")

    lines.extend(
        [
            "- 说明: 这不是 VerseCrafter checkpoint 本身损坏, 而是本地 worker 数超过了当前 Torch 实际可见的 GPU 数.",
            "- 建议1: 如果本机当前只有 1 张可见 GPU, 请把 --nproc_per_node、--ulysses_degree、--ring_degree 都改成 1.",
            "- 建议2: 如果你原本预期有多张 GPU, 先检查 CUDA_VISIBLE_DEVICES、容器 GPU 挂载、MIG 配置或调度器资源分配, 让 Torch 真正看到足够的本地 GPU 后再重试.",
        ]
    )
    return "\n".join(lines)


def ensure_requested_worker_topology_or_raise(
    *,
    required_reason: str,
    nproc_per_node: int,
    ulysses_degree: int,
    ring_degree: int,
) -> None:
    """在启动 Step 6 多进程前验证本地 worker 数是否可落到真实 GPU 上.

    这里专门拦截用户这次踩到的场景:
    `torch.cuda.is_available()` 为 True,
    但 `torch.cuda.device_count()` 仍小于 `--nproc-per-node`.
    这种情况下继续进入 FSDP, 最终只会在更深层报 `invalid device ordinal`.
    """

    if nproc_per_node <= 1:
        return

    probe_payload = probe_torch_cuda_runtime()
    visible_device_count = probe_payload.get("device_count")
    if isinstance(visible_device_count, int) and visible_device_count >= nproc_per_node:
        return

    raise RuntimeError(
        build_multi_gpu_preflight_error_message(
            required_reason=required_reason,
            nproc_per_node=nproc_per_node,
            ulysses_degree=ulysses_degree,
            ring_degree=ring_degree,
            probe_payload=probe_payload,
        )
    )


def has_mask_pngs(mask_dir: Path) -> bool:
    """检查 segmentation 的单体 mask 是否存在."""

    return mask_dir.is_dir() and any(mask_dir.glob("mask_*.png"))


def is_camera_only_mask_dir(mask_dir: Path) -> bool:
    """判断 mask 目录是否符合 camera-only 语义.

    camera-only 下允许目录存在,
    但不应残留任何前景 mask png.
    """

    return mask_dir.is_dir() and not any(mask_dir.glob("*.png"))


def is_camera_only_gaussian_json(path: Path) -> bool:
    """判断共享 Gaussian JSON 是否是 camera-only 的空对象版本."""

    if not is_existing_nonempty_file(path):
        return False

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    gaussian_params = payload.get("gaussian_params", {})
    num_objects = int(payload.get("num_objects", -1))
    obj_id_to_color_idx = payload.get("obj_id_to_color_idx", {})
    return num_objects == 0 and gaussian_params == {} and obj_id_to_color_idx == {}


def write_camera_only_shared_outputs(
    *,
    depth_npz_path: Path,
    masks_dir: Path,
    gaussian_json_path: Path,
) -> None:
    """为 camera-only 模式落地空 mask 与空 Gaussian 参数."""

    masks_dir.mkdir(parents=True, exist_ok=True)

    depth_map, intrinsic = load_depth_and_intrinsic(depth_npz_path)
    payload = build_empty_gaussian_params_payload(
        depth_shape=(int(depth_map.shape[0]), int(depth_map.shape[1])),
        intrinsic=intrinsic,
    )
    ensure_parent_dir(gaussian_json_path)
    gaussian_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_or_raise(condition: bool, message: str) -> None:
    """小工具: 条件不成立时抛清晰错误."""

    if not condition:
        raise RuntimeError(message)


def merge_manifest_defaults(existing: dict[str, Any] | None, fresh: dict[str, Any]) -> dict[str, Any]:
    """把已有 manifest 的可复用信息合并到新结构里."""

    if existing is None:
        return fresh

    merged = fresh
    merged["created_at"] = existing.get("created_at", fresh["created_at"])
    merged["status"] = existing.get("status", fresh["status"])

    existing_shared = existing.get("shared", {})
    merged["shared"].update({
        key: value
        for key, value in existing_shared.items()
        if key in merged["shared"] and value is not None
    })

    existing_trajectories = existing.get("trajectories", {})
    for index_text, trajectory_payload in merged["trajectories"].items():
        if index_text in existing_trajectories and isinstance(existing_trajectories[index_text], dict):
            for key, value in existing_trajectories[index_text].items():
                if key in trajectory_payload and value is not None:
                    trajectory_payload[key] = value

    return merged


def describe_command(command: list[str]) -> str:
    """把命令格式化成终端可读字符串."""

    return shlex.join(command)


def emit_dry_run_plan(
    args: argparse.Namespace,
    *,
    output_root: Path,
    manifest: dict[str, Any],
    preset_specs: list[dict[str, Any]],
    target_height: int,
    target_width: int,
) -> None:
    """打印本次批处理将执行的步骤和命令.

    dry-run 的目标不是模拟完整运行时状态,
    而是让用户在真正起重流程前看到:
    - 哪些共享步骤会复用
    - 每条轨迹会落到哪里
    - 每个阶段实际要执行什么命令
    """

    shared_dir = output_root / "shared"
    estimated_depth_dir = shared_dir / "estimated_depth"
    foreground_masks_dir = shared_dir / "foreground_masks"
    masks_dir = foreground_masks_dir / "masks"
    gaussian_output_dir = shared_dir / "fitted_3D_gaussian"
    depth_npz_path = estimated_depth_dir / "depth_intrinsics.npz"
    gaussian_json_path = gaussian_output_dir / "gaussian_params.json"
    override_plan = resolve_intrinsic_override_plan(args, output_root=output_root)

    print("=== Dry Run: single-image multi-trajectory batch ===")
    print(f"input_image_path: {Path(args.input_image_path).resolve()}")
    print(f"output_root: {output_root.resolve()}")
    print(f"resume: {args.resume}")
    print(f"camera_only: {args.camera_only}")
    print(f"selected_preset_indices: {'all' if args.preset_indices is None else args.preset_indices}")
    print(f"device: {args.device}")
    print(f"python_bin: {args.python_bin}")
    print(f"torchrun_bin: {args.torchrun_bin}")
    print(f"nproc_per_node: {args.nproc_per_node}")
    print("")

    depth_reused = args.resume and is_existing_nonempty_file(depth_npz_path)
    intrinsic_preview = None
    intrinsic_will_change = False
    if depth_reused:
        intrinsic_preview = preview_shared_intrinsics(
            depth_npz_path=depth_npz_path,
            override_plan=override_plan,
        )
        intrinsic_will_change = bool(intrinsic_preview["changed"])
    segmentation_reused = args.resume and (
        is_camera_only_mask_dir(masks_dir) if args.camera_only else has_mask_pngs(masks_dir)
    )
    gaussian_reused = args.resume and (
        is_camera_only_gaussian_json(gaussian_json_path) if args.camera_only else is_existing_nonempty_file(gaussian_json_path)
    )
    if intrinsic_will_change:
        gaussian_reused = False

    print("[Shared]")
    print(f"- depth: {'reuse' if depth_reused else 'run'} -> {depth_npz_path}")
    if not depth_reused:
        print(f"  command: {describe_command(build_moge_command(args, estimated_depth_dir))}")
    if override_plan.mode == "known_horizontal_fov":
        print(
            "- intrinsics: "
            f"{override_plan.mode} ({override_plan.horizontal_fov_degrees:.1f} deg horizontal FOV)"
        )
        if override_plan.source == "auto_series_my_nt":
            print(
                "  note: auto-matched known 3ds Max series"
                f" '{override_plan.matched_series_name}', so Step 1 output K will be rewritten"
            )
        else:
            print("  note: explicit CLI override will rewrite Step 1 output K")
    else:
        print("- intrinsics: moge_predicted")
        if override_plan.source == "auto_disabled":
            print("  note: auto known-intrinsics override is disabled for this run")

    if intrinsic_preview is not None:
        print(
            "  preview: current shared NPZ already "
            + ("matches" if not intrinsic_will_change else "differs from")
            + " the effective intrinsic strategy"
        )
        if intrinsic_will_change:
            print("  note: downstream Gaussian / render / video reuse will be invalidated by the new K")
    if args.camera_only:
        print(f"- segmentation: {'reuse' if segmentation_reused else 'camera_only_empty'} -> {masks_dir}")
        print("  note: skip foreground segmentation; keep mask dir empty so the whole image becomes rigid background")
        print(f"- gaussian: {'reuse' if gaussian_reused else 'camera_only_empty'} -> {gaussian_json_path}")
        print("  note: skip 3D Gaussian fitting; generate num_objects=0 placeholder JSON")
    else:
        print(f"- segmentation: {'reuse' if segmentation_reused else 'run'} -> {masks_dir}")
        if not segmentation_reused:
            print(f"  command: {describe_command(build_segmentation_command(args, foreground_masks_dir))}")
        print(f"- gaussian: {'reuse' if gaussian_reused else 'run'} -> {gaussian_json_path}")
        if not gaussian_reused:
            print(
                f"  command: {describe_command(build_gaussian_command(args, depth_npz_path=depth_npz_path, masks_dir=masks_dir, gaussian_output_dir=gaussian_output_dir))}"
            )

    center_depth_known = depth_reused
    center_depth = None
    translation_reference_depth = None
    if center_depth_known:
        depth_map, _ = load_depth_and_intrinsic(depth_npz_path)
        center_depth = estimate_center_depth(
            depth_map,
            depth_quantile=args.auto_center_depth_quantile,
            center_crop_ratio=args.auto_center_depth_center_crop_ratio,
            fallback_depth=1.0,
        )
        translation_reference_depth = resolve_translation_reference_depth(
            center_depth,
            args.translation_reference_depth_scale,
        )

    print("")
    print("[Trajectories]")
    for preset in preset_specs:
        index_text = str(preset['index'])
        preset_dir = output_root / index_text
        rendering_maps_dir = preset_dir / "rendering_4D_maps"
        generated_videos_dir = preset_dir / "generated_videos"
        existing_video = find_generated_video(generated_videos_dir)
        render_reused = args.resume and is_valid_render_output_dir(rendering_maps_dir)
        if intrinsic_will_change:
            render_reused = False
        generation_reused = args.resume and existing_video is not None
        if intrinsic_will_change:
            generation_reused = False
        generation_prompt = build_generation_prompt(args.prompt, preset["camera_motion_prompt"])

        print(f"- [{index_text}] {preset['name']}")
        print(f"  movement_distance: {preset['movement_distance']:.6f}")
        print(f"  camera_motion_prompt: {preset['camera_motion_prompt']}")
        print(f"  generation_prompt: {generation_prompt}")
        print(f"  preset_dir: {preset_dir}")
        print(f"  trajectory_assets: run -> {preset_dir / 'custom_camera_trajectory.npz'}")
        print(f"  static_gaussian_json: run -> {preset_dir / 'custom_3D_gaussian_trajectory.json'}")
        if center_depth_known:
            print(f"  center_depth: {center_depth:.6f}")
            print(f"  translation_reference_depth: {translation_reference_depth:.6f}")
        else:
            print("  center_depth: pending (requires depth estimation)")
            print("  translation_reference_depth: pending (requires depth estimation)")

        print(f"  render: {'reuse' if render_reused else 'run'} -> {rendering_maps_dir}")
        if not render_reused:
            print(
                f"    command: {describe_command(build_render_command(args, depth_npz_path=depth_npz_path, masks_dir=masks_dir, trajectory_npz=preset_dir / 'custom_camera_trajectory.npz', ellipsoid_json=preset_dir / 'custom_3D_gaussian_trajectory.json', output_dir=rendering_maps_dir, target_height=target_height, target_width=target_width))}"
            )

        print(f"  generation: {'reuse' if generation_reused else 'run'} -> {generated_videos_dir}")
        if generation_reused:
            print(f"    existing_video: {existing_video}")
        else:
            print(
                f"    command: {describe_command(build_generation_command(args, generation_prompt=generation_prompt, rendering_maps_dir=rendering_maps_dir, save_path=generated_videos_dir))}"
            )

    print("")
    print(f"manifest_path: {output_root / MANIFEST_FILE_NAME}")
    print(f"manifest_status_before_run: {manifest.get('status')}")


# ============================================================================
# Command builders
# ============================================================================
def build_moge_command(args: argparse.Namespace, estimated_depth_dir: Path) -> list[str]:
    """构造 Step 1 命令."""

    command = [
        args.python_bin,
        "inference/moge-v2_infer.py",
        "-i",
        args.input_image_path,
        "-o",
        str(estimated_depth_dir),
        "--maps",
        "--version",
        args.moge_version,
        "--device",
        args.device,
    ]
    if args.moge_pretrained is not None:
        command.extend(["--pretrained", args.moge_pretrained])
    if args.moge_fp16:
        command.append("--fp16")
    return command


def build_segmentation_command(args: argparse.Namespace, masks_output_dir: Path) -> list[str]:
    """构造 Step 2 命令."""

    return [
        args.python_bin,
        "inference/grounded_sam2_infer.py",
        "--image_path",
        args.input_image_path,
        "--text_prompt",
        args.object_prompt,
        "--output_dir",
        str(masks_output_dir),
        "--device",
        args.device,
        "--box_threshold",
        str(args.box_threshold),
        "--text_threshold",
        str(args.text_threshold),
        "--keep_topk",
        str(args.keep_topk),
        "--min_area_ratio",
        str(args.min_area_ratio),
        "--max_area_ratio",
        str(args.max_area_ratio),
    ]


def build_gaussian_command(
    args: argparse.Namespace,
    *,
    depth_npz_path: Path,
    masks_dir: Path,
    gaussian_output_dir: Path,
) -> list[str]:
    """构造 Step 3 命令."""

    command = [
        args.python_bin,
        "inference/fit_3D_gaussian.py",
        "--image_path",
        args.input_image_path,
        "--npz_path",
        str(depth_npz_path),
        "--masks_dir",
        str(masks_dir),
        "--output_dir",
        str(gaussian_output_dir),
        "--device",
        args.device,
    ]
    if args.disable_gaussian_visualization:
        command.append("--no_visualization")
    return command


def build_render_command(
    args: argparse.Namespace,
    *,
    depth_npz_path: Path,
    masks_dir: Path,
    trajectory_npz: Path,
    ellipsoid_json: Path,
    output_dir: Path,
    target_height: int,
    target_width: int,
) -> list[str]:
    """构造 Step 5 命令."""

    # 渲染步骤有自己的 PyTorch3D / CUDA 依赖边界.
    # 默认仍复用全局 python / device, 只有显式指定时才切到独立环境.
    render_python_bin = args.render_python_bin or args.python_bin
    render_device = args.render_device or args.device

    command = [
        render_python_bin,
        "inference/rendering_4D_control_maps.py",
        "--png_path",
        args.input_image_path,
        "--npz_path",
        str(depth_npz_path),
        "--mask_dir",
        str(masks_dir),
        "--trajectory_npz",
        str(trajectory_npz),
        "--ellipsoid_json",
        str(ellipsoid_json),
        "--output_dir",
        str(output_dir),
        "--device",
        render_device,
        "--point_size",
        str(args.point_size),
        "--fps",
        str(args.fps),
        "--render_batch_size",
        str(args.render_batch_size),
        "--target_height",
        str(target_height),
        "--target_width",
        str(target_width),
    ]
    if args.render_background_point_limit > 0:
        command.extend(
            [
                "--background_point_limit",
                str(args.render_background_point_limit),
            ]
        )
    if args.render_use_fp16:
        command.append("--use_fp16")
    if args.render_pin_memory:
        command.append("--pin_memory")
    return command


def build_generation_command(
    args: argparse.Namespace,
    *,
    generation_prompt: str,
    rendering_maps_dir: Path,
    save_path: Path,
) -> list[str]:
    """构造 Step 6 命令."""

    command: list[str]
    if args.nproc_per_node > 1:
        command = [
            args.torchrun_bin,
            f"--nproc-per-node={args.nproc_per_node}",
            "inference/versecrafter_inference.py",
        ]
    else:
        command = [
            args.python_bin,
            "inference/versecrafter_inference.py",
        ]

    command.extend(
        [
            "--transformer_path",
            args.transformer_path,
            "--save_path",
            str(save_path),
            "--rendering_maps_path",
            str(rendering_maps_dir),
            "--prompt",
            generation_prompt,
            "--negative_prompt",
            args.negative_prompt,
            "--input_image_path",
            args.input_image_path,
            "--num_inference_steps",
            str(args.num_inference_steps),
            "--sample_size",
            args.sample_size,
            "--ulysses_degree",
            str(args.ulysses_degree),
            "--ring_degree",
            str(args.ring_degree),
            "--guidance_scale",
            str(args.guidance_scale),
            "--seed",
            str(args.seed),
            "--fps",
            str(args.fps),
            "--gpu_memory_mode",
            args.gpu_memory_mode,
        ]
    )
    return command


# ============================================================================
# CLI
# ============================================================================
def create_parser() -> argparse.ArgumentParser:
    """定义 VerseCrafter 单图多轨迹批处理 CLI."""

    parser = argparse.ArgumentParser(
        description="Generate six deterministic camera-motion videos from one image in VerseCrafter."
    )
    parser.add_argument("--input_image_path", type=str, required=True, help="Path to the input image")
    parser.add_argument("--output_root", type=str, required=True, help="Root output directory for the batch run")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt used by VerseCrafter generation")
    parser.add_argument(
        "--object_prompt",
        type=str,
        default="person . car . dog . cat .",
        help="Grounded-SAM-2 text prompt used for foreground segmentation",
    )
    parser.add_argument(
        "--camera_only",
        action="store_true",
        help="Disable foreground segmentation / Gaussian fitting and treat the whole image as rigid background",
    )
    parser.add_argument(
        "--transformer_path",
        type=str,
        default="model/VerseCrafter",
        help="Path to VerseCrafter checkpoint directory or file",
    )
    parser.add_argument(
        "--negative_prompt",
        type=str,
        default=(
            "Bright tones, overexposed, static, blurred details, subtitles, style, works, "
            "paintings, images, static, overall gray, worst quality, low quality, JPEG "
            "compression residue, ugly, incomplete, extra fingers, poorly drawn hands, "
            "poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, "
            "still picture, messy background, three legs, many people in the background, "
            "walking backwards"
        ),
        help="Negative prompt passed to VerseCrafter inference",
    )
    parser.add_argument("--python_bin", type=str, default=sys.executable, help="Python interpreter used for child steps")
    parser.add_argument("--torchrun_bin", type=str, default="torchrun", help="torchrun executable used for Step 6")
    parser.add_argument("--device", type=str, default="cuda", help="Device used by preprocessing and rendering steps")
    parser.add_argument(
        "--render_python_bin",
        type=str,
        default=None,
        help="Optional Python interpreter used only for Step 5 rendering. Defaults to --python_bin.",
    )
    parser.add_argument(
        "--render_device",
        type=str,
        default=None,
        help="Optional device used only for Step 5 rendering. Defaults to --device.",
    )
    parser.add_argument("--moge_version", type=str, choices=["v1", "v2"], default="v2", help="MoGe model version")
    parser.add_argument(
        "--moge_pretrained",
        type=str,
        default=None,
        help="Optional local `model.pt` path or HF repo id passed through to moge-v2_infer.py --pretrained. Local paths must be readable by the current user.",
    )
    parser.add_argument(
        "--moge_fp16",
        action="store_true",
        help="Run MoGe depth estimation in FP16. Useful on newer GPUs where xformers fp32 attention kernels are unavailable.",
    )
    parser.add_argument("--sample_size", type=str, default="720,1280", help="Target sample size as 'height,width'")
    parser.add_argument(
        "--render_sample_size",
        type=str,
        default=None,
        help="Optional Step 5 render size as 'height,width'. Defaults to --sample_size and is useful for faster smoke tests.",
    )
    parser.add_argument(
        "--preset_indices",
        type=int,
        nargs="+",
        choices=PRESET_INDEX_CHOICES,
        default=None,
        help="Optional subset of preset indices to run, for example: --preset_indices 0 5 6 7",
    )
    parser.add_argument("--num_inference_steps", type=int, default=30, help="VerseCrafter sampling steps")
    parser.add_argument("--ulysses_degree", type=int, default=1, help="VerseCrafter ulysses degree")
    parser.add_argument("--ring_degree", type=int, default=1, help="VerseCrafter ring degree")
    parser.add_argument("--nproc_per_node", type=int, default=None, help="torchrun worker count; defaults to ulysses_degree * ring_degree")
    parser.add_argument("--guidance_scale", type=float, default=5.0, help="VerseCrafter guidance scale")
    parser.add_argument("--seed", type=int, default=2025, help="Random seed for final video generation")
    parser.add_argument("--fps", type=int, default=16, help="FPS used by rendering and final generation")
    parser.add_argument(
        "--gpu_memory_mode",
        type=str,
        default="model_cpu_offload_and_qfloat8",
        choices=[
            "model_full_load",
            "model_full_load_and_qfloat8",
            "model_cpu_offload",
            "model_cpu_offload_and_qfloat8",
            "sequential_cpu_offload",
        ],
        help="GPU memory strategy passed through to VerseCrafter inference; defaults to the single-GPU mode that was validated on A800-80GB",
    )

    parser.add_argument("--box_threshold", type=float, default=0.4, help="GroundingDINO box threshold")
    parser.add_argument("--text_threshold", type=float, default=0.25, help="GroundingDINO text threshold")
    parser.add_argument("--keep_topk", type=int, default=6, help="Keep top-K largest masks")
    parser.add_argument("--min_area_ratio", type=float, default=0.005, help="Minimum mask area ratio")
    parser.add_argument("--max_area_ratio", type=float, default=0.2, help="Maximum mask area ratio")
    parser.add_argument(
        "--disable_gaussian_visualization",
        action="store_true",
        help="Skip Gaussian overlay visualizations to save a little processing time",
    )

    parser.add_argument("--point_size", type=float, default=0.005, help="Point size used in Step 5 rendering")
    parser.add_argument("--render_batch_size", type=int, default=27, help="Batch size used in Step 5 rendering")
    parser.add_argument(
        "--render_background_point_limit",
        type=int,
        default=0,
        help="Optional background point limit for Step 5 smoke tests; 0 keeps all points",
    )
    parser.add_argument("--render_use_fp16", action="store_true", help="Enable FP16 rendering in Step 5")
    parser.add_argument("--render_pin_memory", action="store_true", help="Enable pinned memory in Step 5")

    parser.add_argument(
        "--auto_center_depth_quantile",
        type=float,
        default=0.2,
        help="Quantile used to estimate trajectory center depth from the depth map",
    )
    parser.add_argument(
        "--auto_center_depth_center_crop_ratio",
        type=float,
        default=0.5,
        help="Center crop ratio used for automatic center depth estimation",
    )
    parser.add_argument(
        "--translation_reference_depth_scale",
        type=float,
        default=0.95,
        help="Scale factor applied to center_depth when computing translation reference depth",
    )
    parser.add_argument(
        "--total_movement_distance_factor",
        type=float,
        default=1.5,
        help="Multiplier applied to the midpoint of each trajectory preset distance range",
    )
    parser.add_argument(
        "--camera_rotation",
        type=str,
        choices=["center_facing", "no_rotation", "trajectory_aligned"],
        default="center_facing",
        help="How the camera rotates while moving",
    )
    parser.add_argument("--radius_x_factor", type=float, default=DEFAULT_RADIUS_X_FACTOR, help="Orbit X radius factor")
    parser.add_argument("--radius_y_factor", type=float, default=DEFAULT_RADIUS_Y_FACTOR, help="Orbit Z radius factor after coordinate conversion")
    parser.add_argument("--num_circles", type=int, default=DEFAULT_NUM_CIRCLES, help="Orbit circle count for the orbit preset family")
    parser.add_argument("--num_frames", type=int, default=DEFAULT_NUM_FRAMES, help="Frame count for generated trajectories")

    parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=True,
        help="Reuse valid shared outputs and completed trajectories when rerunning (default: enabled)",
    )
    parser.add_argument(
        "--no_resume",
        dest="resume",
        action="store_false",
        help="Disable resume and rebuild outputs for this batch run",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print the planned steps and commands without executing child processes",
    )
    return parser


# ============================================================================
# Main flow
# ============================================================================
def main() -> None:
    """主执行流程."""

    args = create_parser().parse_args()
    if args.nproc_per_node is None:
        args.nproc_per_node = args.ulysses_degree * args.ring_degree
    if args.nproc_per_node <= 0:
        raise ValueError("nproc_per_node must be positive")
    if args.nproc_per_node != args.ulysses_degree * args.ring_degree:
        raise ValueError(
            "nproc_per_node must equal ulysses_degree * ring_degree for VerseCrafter distributed inference"
        )
    if args.num_frames != DEFAULT_NUM_FRAMES:
        raise ValueError(
            f"VerseCrafter current inference path is fixed to {DEFAULT_NUM_FRAMES} frames; got {args.num_frames}."
        )
    if args.known_horizontal_fov_degrees is not None and not 0.0 < args.known_horizontal_fov_degrees < 180.0:
        raise ValueError(
            "known_horizontal_fov_degrees must be in (0, 180) when provided"
        )

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    target_height, target_width = parse_sample_size(args.sample_size)
    validate_generation_sample_size(target_height, target_width)
    render_height, render_width = parse_sample_size(args.render_sample_size or args.sample_size)
    manifest_path = output_root / MANIFEST_FILE_NAME
    all_preset_specs = get_preset_run_specs(args.total_movement_distance_factor)
    active_preset_specs = select_preset_run_specs(all_preset_specs, args.preset_indices)
    if args.preset_indices is not None:
        args.preset_indices = [int(spec["index"]) for spec in active_preset_specs]
    manifest = merge_manifest_defaults(load_manifest(manifest_path), build_manifest(args, output_root, all_preset_specs))

    shared_dir = output_root / "shared"
    estimated_depth_dir = shared_dir / "estimated_depth"
    foreground_masks_dir = shared_dir / "foreground_masks"
    masks_dir = foreground_masks_dir / "masks"
    gaussian_output_dir = shared_dir / "fitted_3D_gaussian"
    depth_npz_path = estimated_depth_dir / "depth_intrinsics.npz"
    gaussian_json_path = gaussian_output_dir / "gaussian_params.json"

    if args.dry_run:
        emit_dry_run_plan(
            args,
            output_root=output_root,
            manifest=manifest,
            preset_specs=active_preset_specs,
            target_height=render_height,
            target_width=render_width,
        )
        return

    save_manifest(manifest_path, manifest)

    try:
        cuda_required_reason = explain_why_cuda_is_needed(
            args,
            output_root=output_root,
            active_preset_specs=active_preset_specs,
        )
        if cuda_required_reason is not None:
            ensure_cuda_runtime_ready_or_raise(
                requested_device=args.device,
                required_reason=cuda_required_reason,
            )
        multi_gpu_required_reason = explain_why_multi_gpu_generation_is_needed(
            args,
            output_root=output_root,
            active_preset_specs=active_preset_specs,
        )
        if multi_gpu_required_reason is not None:
            ensure_requested_worker_topology_or_raise(
                required_reason=multi_gpu_required_reason,
                nproc_per_node=args.nproc_per_node,
                ulysses_degree=args.ulysses_degree,
                ring_degree=args.ring_degree,
            )

        # ------------------------------------------------------------------
        # Shared step 1: depth estimation
        # ------------------------------------------------------------------
        depth_reused = args.resume and is_existing_nonempty_file(depth_npz_path)
        if not depth_reused:
            ensure_clean_path(estimated_depth_dir)
            run_command(build_moge_command(args, estimated_depth_dir), cwd=PROJECT_ROOT)
        validate_or_raise(
            is_existing_nonempty_file(depth_npz_path),
            f"Depth estimation output missing: {depth_npz_path}",
        )
        intrinsic_sync = sync_shared_intrinsics(
            depth_npz_path=depth_npz_path,
            override_plan=override_plan,
        )
        shared_intrinsic_changed = bool(intrinsic_sync["changed"])
        manifest["shared"]["depth_status"] = "reused" if depth_reused else "completed"
        if override_plan.mode == "known_horizontal_fov":
            manifest["shared"]["intrinsic_status"] = (
                "known_horizontal_fov_overridden" if shared_intrinsic_changed else "known_horizontal_fov_reused"
            )
        else:
            manifest["shared"]["intrinsic_status"] = (
                "moge_predicted_restored" if intrinsic_sync["restored_moge_intrinsic"] else "moge_predicted_reused"
            )
        manifest["shared"]["intrinsic_mode"] = intrinsic_sync["mode"]
        manifest["shared"]["intrinsic_source"] = override_plan.source
        manifest["shared"]["effective_horizontal_fov_degrees"] = intrinsic_sync["effective_horizontal_fov_degrees"]
        manifest["shared"]["effective_intrinsic"] = intrinsic_sync["effective_intrinsic"].tolist()
        manifest["shared"]["status"] = "running"
        manifest["shared"]["error"] = None
        save_manifest(manifest_path, manifest)

        # ------------------------------------------------------------------
        # Shared step 2: segmentation
        # ------------------------------------------------------------------
        if args.camera_only:
            segmentation_reused = args.resume and is_camera_only_mask_dir(masks_dir)
            gaussian_reused = (
                args.resume
                and not shared_intrinsic_changed
                and is_camera_only_gaussian_json(gaussian_json_path)
            )
            if not segmentation_reused or not gaussian_reused:
                ensure_clean_path(foreground_masks_dir)
                ensure_clean_path(gaussian_output_dir)
                write_camera_only_shared_outputs(
                    depth_npz_path=depth_npz_path,
                    masks_dir=masks_dir,
                    gaussian_json_path=gaussian_json_path,
                )
            validate_or_raise(
                is_camera_only_mask_dir(masks_dir),
                f"Camera-only workflow expects an empty mask directory under: {masks_dir}",
            )
            validate_or_raise(
                is_camera_only_gaussian_json(gaussian_json_path),
                f"Camera-only workflow expects num_objects=0 gaussian JSON under: {gaussian_json_path}",
            )
            manifest["shared"]["segmentation_status"] = "camera_only_reused" if segmentation_reused else "camera_only_empty"
            manifest["shared"]["gaussian_status"] = "camera_only_reused" if gaussian_reused else "camera_only_empty"
        else:
            segmentation_reused = args.resume and has_mask_pngs(masks_dir)
            if not segmentation_reused:
                ensure_clean_path(foreground_masks_dir)
                run_command(build_segmentation_command(args, foreground_masks_dir), cwd=PROJECT_ROOT)
            validate_or_raise(has_mask_pngs(masks_dir), f"Segmentation masks missing under: {masks_dir}")
            manifest["shared"]["segmentation_status"] = "reused" if segmentation_reused else "completed"
            save_manifest(manifest_path, manifest)

            # ------------------------------------------------------------------
            # Shared step 3: 3D Gaussian fitting
            # ------------------------------------------------------------------
            gaussian_reused = (
                args.resume
                and not shared_intrinsic_changed
                and is_existing_nonempty_file(gaussian_json_path)
            )
            if not gaussian_reused:
                ensure_clean_path(gaussian_output_dir)
                run_command(
                    build_gaussian_command(
                        args,
                        depth_npz_path=depth_npz_path,
                        masks_dir=masks_dir,
                        gaussian_output_dir=gaussian_output_dir,
                    ),
                    cwd=PROJECT_ROOT,
                )
            validate_or_raise(
                is_existing_nonempty_file(gaussian_json_path),
                f"Gaussian fitting output missing: {gaussian_json_path}",
            )
            gaussian_payload = json.loads(gaussian_json_path.read_text(encoding="utf-8"))
            num_objects = int(gaussian_payload.get("num_objects", 0))
            validate_or_raise(
                num_objects > 0,
                "Zero-object scenes are not supported by this workflow version. Gaussian fitting produced num_objects = 0.",
            )
            manifest["shared"]["gaussian_status"] = "reused" if gaussian_reused else "completed"

        manifest["shared"]["status"] = "completed"
        save_manifest(manifest_path, manifest)

        # ------------------------------------------------------------------
        # Shared depth statistics for all 6 trajectories
        # ------------------------------------------------------------------
        depth_map, _intrinsic = load_depth_and_intrinsic(depth_npz_path)
        center_depth = estimate_center_depth(
            depth_map,
            depth_quantile=args.auto_center_depth_quantile,
            center_crop_ratio=args.auto_center_depth_center_crop_ratio,
            fallback_depth=1.0,
        )
        translation_reference_depth = resolve_translation_reference_depth(
            center_depth,
            args.translation_reference_depth_scale,
        )
        manifest["shared"]["center_depth"] = center_depth
        manifest["shared"]["translation_reference_depth"] = translation_reference_depth
        save_manifest(manifest_path, manifest)

        any_trajectory_failed = False

        # ------------------------------------------------------------------
        # Per-trajectory steps
        # ------------------------------------------------------------------
        for preset in active_preset_specs:
            index_text = str(preset["index"])
            preset_dir = output_root / index_text
            trajectory_npz_path = preset_dir / "custom_camera_trajectory.npz"
            ellipsoid_json_path = preset_dir / "custom_3D_gaussian_trajectory.json"
            rendering_maps_dir = preset_dir / "rendering_4D_maps"
            generated_videos_dir = preset_dir / "generated_videos"
            trajectory_manifest = manifest["trajectories"][index_text]
            generation_prompt = build_generation_prompt(args.prompt, preset["camera_motion_prompt"])
            trajectory_manifest["camera_motion_prompt"] = preset["camera_motion_prompt"]
            trajectory_manifest["generation_prompt"] = generation_prompt
            trajectory_manifest["center_depth"] = center_depth
            trajectory_manifest["translation_reference_depth"] = translation_reference_depth
            save_manifest(manifest_path, manifest)

            try:
                existing_video = find_generated_video(generated_videos_dir)
                if (
                    args.resume
                    and not shared_intrinsic_changed
                    and existing_video is not None
                    and is_valid_render_output_dir(rendering_maps_dir)
                ):
                    trajectory_manifest["trajectory_assets_status"] = "reused"
                    trajectory_manifest["render_status"] = "reused"
                    trajectory_manifest["generation_status"] = "reused"
                    trajectory_manifest["generated_video_path"] = str(existing_video)
                    trajectory_manifest["status"] = "completed"
                    trajectory_manifest["error"] = None
                    save_manifest(manifest_path, manifest)
                    logger.info("Preset %s already completed, skipping due to resume.", preset["name"])
                    continue

                if not args.resume:
                    ensure_clean_path(preset_dir)
                preset_dir.mkdir(parents=True, exist_ok=True)

                # 1) 生成相机轨迹 npz
                blender_trajectory = generate_blender_camera_trajectory(
                    preset["name"],
                    movement_distance=preset["movement_distance"],
                    center_depth=center_depth,
                    translation_reference_depth=translation_reference_depth,
                    num_frames=args.num_frames,
                    camera_rotation=args.camera_rotation,
                    radius_x_factor=args.radius_x_factor,
                    radius_y_factor=args.radius_y_factor,
                    num_circles=args.num_circles,
                )
                np.savez(str(trajectory_npz_path), extrinsics=blender_trajectory.astype(np.float32))

                # 2) 生成静态多帧高斯轨迹 JSON
                convert_static_gaussian_json_to_trajectory(
                    gaussian_json_path,
                    ellipsoid_json_path,
                    num_frames=args.num_frames,
                )
                validate_or_raise(
                    is_existing_nonempty_file(trajectory_npz_path),
                    f"Failed to write trajectory NPZ: {trajectory_npz_path}",
                )
                validate_or_raise(
                    is_existing_nonempty_file(ellipsoid_json_path),
                    f"Failed to write ellipsoid trajectory JSON: {ellipsoid_json_path}",
                )
                trajectory_manifest["trajectory_assets_status"] = "completed"
                trajectory_manifest["error"] = None
                save_manifest(manifest_path, manifest)

                # 3) Render 4D control maps
                render_reused = (
                    args.resume
                    and not shared_intrinsic_changed
                    and is_valid_render_output_dir(rendering_maps_dir)
                )
                if not render_reused:
                    ensure_clean_path(rendering_maps_dir)
                    run_command(
                        build_render_command(
                            args,
                            depth_npz_path=depth_npz_path,
                            masks_dir=masks_dir,
                            trajectory_npz=trajectory_npz_path,
                            ellipsoid_json=ellipsoid_json_path,
                            output_dir=rendering_maps_dir,
                            target_height=render_height,
                            target_width=render_width,
                        ),
                        cwd=PROJECT_ROOT,
                    )
                validate_or_raise(
                    is_valid_render_output_dir(rendering_maps_dir),
                    f"Render output is incomplete: {rendering_maps_dir}",
                )
                trajectory_manifest["render_status"] = "reused" if render_reused else "completed"
                save_manifest(manifest_path, manifest)

                # 4) Final VerseCrafter generation
                existing_video = find_generated_video(generated_videos_dir)
                generation_reused = (
                    args.resume
                    and not shared_intrinsic_changed
                    and existing_video is not None
                )
                if not generation_reused:
                    ensure_clean_path(generated_videos_dir)
                    generated_videos_dir.mkdir(parents=True, exist_ok=True)
                    run_command(
                        build_generation_command(
                            args,
                            generation_prompt=generation_prompt,
                            rendering_maps_dir=rendering_maps_dir,
                            save_path=generated_videos_dir,
                        ),
                        cwd=PROJECT_ROOT,
                    )
                    existing_video = find_generated_video(generated_videos_dir)
                validate_or_raise(
                    existing_video is not None,
                    f"VerseCrafter generation did not produce generated_video_*.mp4 under: {generated_videos_dir}",
                )
                trajectory_manifest["generation_status"] = "reused" if generation_reused else "completed"
                trajectory_manifest["generated_video_path"] = str(existing_video)
                trajectory_manifest["status"] = "completed"
                trajectory_manifest["error"] = None
                save_manifest(manifest_path, manifest)
            except Exception as trajectory_error:  # noqa: BLE001
                any_trajectory_failed = True
                trajectory_manifest["status"] = "failed"
                trajectory_manifest["error"] = str(trajectory_error)
                save_manifest(manifest_path, manifest)
                logger.exception("Preset %s failed", preset["name"])
                continue

        manifest["status"] = "completed_with_errors" if any_trajectory_failed else "completed"
        save_manifest(manifest_path, manifest)
    except Exception as shared_error:  # noqa: BLE001
        manifest["status"] = "failed"
        manifest["shared"]["error"] = str(shared_error)
        save_manifest(manifest_path, manifest)
        logger.exception("Batch workflow failed before finishing all trajectories")
        raise


if __name__ == "__main__":
    main()
