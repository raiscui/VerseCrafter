from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
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
    build_empty_gaussian_params_payload,
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
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE_NAME = "manifest.json"


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
            "device": args.device,
            "sample_size": args.sample_size,
            "num_inference_steps": args.num_inference_steps,
            "ulysses_degree": args.ulysses_degree,
            "ring_degree": args.ring_degree,
            "nproc_per_node": args.nproc_per_node,
            "guidance_scale": args.guidance_scale,
            "seed": args.seed,
            "fps": args.fps,
            "gpu_memory_mode": args.gpu_memory_mode,
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


def ensure_clean_path(path: Path, *, keep_if_missing: bool = True) -> None:
    """在非 resume 模式下清空旧目录或旧文件."""

    if keep_if_missing and not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


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
    segmentation_reused = args.resume and (
        is_camera_only_mask_dir(masks_dir) if args.camera_only else has_mask_pngs(masks_dir)
    )
    gaussian_reused = args.resume and (
        is_camera_only_gaussian_json(gaussian_json_path) if args.camera_only else is_existing_nonempty_file(gaussian_json_path)
    )

    print("[Shared]")
    print(f"- depth: {'reuse' if depth_reused else 'run'} -> {depth_npz_path}")
    if not depth_reused:
        print(f"  command: {describe_command(build_moge_command(args, estimated_depth_dir))}")
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
        generation_reused = args.resume and existing_video is not None

        print(f"- [{index_text}] {preset['name']}")
        print(f"  movement_distance: {preset['movement_distance']:.6f}")
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
                f"    command: {describe_command(build_generation_command(args, rendering_maps_dir=rendering_maps_dir, save_path=generated_videos_dir))}"
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

    command = [
        args.python_bin,
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
        args.device,
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
    if args.render_use_fp16:
        command.append("--use_fp16")
    if args.render_pin_memory:
        command.append("--pin_memory")
    return command


def build_generation_command(
    args: argparse.Namespace,
    *,
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
            args.prompt,
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
    parser.add_argument("--moge_version", type=str, choices=["v1", "v2"], default="v2", help="MoGe model version")
    parser.add_argument(
        "--moge_pretrained",
        type=str,
        default=None,
        help="Optional local or HF path passed through to moge-v2_infer.py --pretrained",
    )
    parser.add_argument("--sample_size", type=str, default="720,1280", help="Target sample size as 'height,width'")
    parser.add_argument(
        "--preset_indices",
        type=int,
        nargs="+",
        choices=range(6),
        default=None,
        help="Optional subset of preset indices to run, for example: --preset_indices 0 5",
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
    parser.add_argument("--num_circles", type=int, default=DEFAULT_NUM_CIRCLES, help="Orbit circle count for clockwise preset")
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

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    target_height, target_width = parse_sample_size(args.sample_size)
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
            target_height=target_height,
            target_width=target_width,
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
        manifest["shared"]["depth_status"] = "reused" if depth_reused else "completed"
        manifest["shared"]["status"] = "running"
        manifest["shared"]["error"] = None
        save_manifest(manifest_path, manifest)

        # ------------------------------------------------------------------
        # Shared step 2: segmentation
        # ------------------------------------------------------------------
        if args.camera_only:
            segmentation_reused = args.resume and is_camera_only_mask_dir(masks_dir)
            gaussian_reused = args.resume and is_camera_only_gaussian_json(gaussian_json_path)
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
            gaussian_reused = args.resume and is_existing_nonempty_file(gaussian_json_path)
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
            trajectory_manifest["center_depth"] = center_depth
            trajectory_manifest["translation_reference_depth"] = translation_reference_depth
            save_manifest(manifest_path, manifest)

            try:
                existing_video = find_generated_video(generated_videos_dir)
                if args.resume and existing_video is not None and is_valid_render_output_dir(rendering_maps_dir):
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
                render_reused = args.resume and is_valid_render_output_dir(rendering_maps_dir)
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
                            target_height=target_height,
                            target_width=target_width,
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
                generation_reused = args.resume and existing_video is not None
                if not generation_reused:
                    ensure_clean_path(generated_videos_dir)
                    generated_videos_dir.mkdir(parents=True, exist_ok=True)
                    run_command(
                        build_generation_command(
                            args,
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
