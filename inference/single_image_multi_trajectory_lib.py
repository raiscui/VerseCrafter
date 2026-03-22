"""VerseCrafter 单图多轨迹批处理的核心纯函数.

这个模块故意保持“少副作用”.
这样单测可以直接覆盖:
- 轨迹 preset 与确定性距离
- 深度统计
- OpenCV -> Blender 坐标变换
- 相机轨迹矩阵生成
- 静态高斯 JSON 广播为多帧轨迹 JSON
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


# ============================================================================
# 坐标系常量
# ============================================================================
# OpenCV: X=right, Y=down, Z=forward
# Blender: X=right, Y=forward, Z=up
COORD_TRANSFORM_CV2BLENDER = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ],
    dtype=np.float32,
)

BLENDER_WORLD_UP = np.array([0.0, 0.0, 1.0], dtype=np.float32)
BLENDER_FORWARD_TARGET_UNIT = COORD_TRANSFORM_CV2BLENDER @ np.array([0.0, 0.0, 1.0], dtype=np.float32)
DEFAULT_NUM_FRAMES = 81
DEFAULT_FRAME_STEP = 1
DEFAULT_RADIUS_X_FACTOR = 0.15
DEFAULT_RADIUS_Y_FACTOR = 0.10
DEFAULT_NUM_CIRCLES = 2
LINEAR_DIAGONAL_UP_VERTICAL_SCALE = 0.6
LINEAR_DIAGONAL_DOWN_VERTICAL_SCALE = LINEAR_DIAGONAL_UP_VERTICAL_SCALE / 2.0


# ============================================================================
# 轨迹 preset
# ============================================================================
@dataclass(frozen=True)
class TrajectoryPreset:
    """固定轨迹 preset 定义."""

    index: int
    name: str
    movement_distance_range: tuple[float, float]
    kind: str
    camera_motion_prompt: str
    linear_direction_cv: tuple[float, float, float] | None = None
    orbit_radius_scale: float = 1.0


TRAJECTORY_PRESETS: tuple[TrajectoryPreset, ...] = (
    TrajectoryPreset(
        0,
        "left",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the left",
        linear_direction_cv=(-1.0, 0.0, 0.0),
    ),
    TrajectoryPreset(
        1,
        "right",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the right",
        linear_direction_cv=(1.0, 0.0, 0.0),
    ),
    TrajectoryPreset(
        2,
        "up",
        (0.1, 0.2),
        "linear",
        "Camera is moving upward",
        linear_direction_cv=(0.0, -1.0, 0.0),
    ),
    TrajectoryPreset(
        3,
        "zoom_out",
        (0.3, 0.4),
        "linear",
        "Camera is pulling back",
        linear_direction_cv=(0.0, 0.0, -1.0),
    ),
    TrajectoryPreset(
        4,
        "zoom_in",
        (0.3, 0.4),
        "linear",
        "Camera is moving forward",
        linear_direction_cv=(0.0, 0.0, 1.0),
    ),
    TrajectoryPreset(
        5,
        "clockwise",
        (0.4, 0.6),
        "orbit",
        "Camera is orbiting clockwise around the scene",
        orbit_radius_scale=1.0,
    ),
    TrajectoryPreset(
        6,
        "clockwise_0.65",
        (0.4, 0.6),
        "orbit",
        "Camera is orbiting clockwise around the scene with a tighter radius",
        orbit_radius_scale=0.65,
    ),
    TrajectoryPreset(
        7,
        "clockwise_1.5",
        (0.4, 0.6),
        "orbit",
        "Camera is orbiting clockwise around the scene with a wider radius",
        orbit_radius_scale=1.5,
    ),
    TrajectoryPreset(
        8,
        "left_up",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the left and upward",
        linear_direction_cv=(-1.0, -LINEAR_DIAGONAL_UP_VERTICAL_SCALE, 0.0),
    ),
    TrajectoryPreset(
        9,
        "right_up",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the right and upward",
        linear_direction_cv=(1.0, -LINEAR_DIAGONAL_UP_VERTICAL_SCALE, 0.0),
    ),
    TrajectoryPreset(
        10,
        "left_down",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the left and slightly downward",
        linear_direction_cv=(-1.0, LINEAR_DIAGONAL_DOWN_VERTICAL_SCALE, 0.0),
    ),
    TrajectoryPreset(
        11,
        "right_down",
        (0.2, 0.3),
        "linear",
        "Camera is moving to the right and slightly downward",
        linear_direction_cv=(1.0, LINEAR_DIAGONAL_DOWN_VERTICAL_SCALE, 0.0),
    ),
)

TRAJECTORY_PRESET_BY_NAME = {preset.name: preset for preset in TRAJECTORY_PRESETS}
PRESET_INDEX_CHOICES = tuple(preset.index for preset in TRAJECTORY_PRESETS)


# ============================================================================
# 通用工具
# ============================================================================
def _sorted_object_ids(values: Iterable[str]) -> list[str]:
    """按“数字优先”的顺序稳定排序 object id.

    JSON 里 object id 可能是字符串数字.
    这里统一转成可预测排序, 避免不同 Python 版本下输出顺序漂移.
    """

    def sort_key(value: str) -> tuple[int, Any]:
        text = str(value)
        return (0, int(text)) if text.isdigit() else (1, text)

    return sorted((str(value) for value in values), key=sort_key)


def ensure_parent_dir(path: Path) -> None:
    """确保目标文件的父目录存在."""

    path.parent.mkdir(parents=True, exist_ok=True)


def build_empty_gaussian_params_payload(
    *,
    depth_shape: tuple[int, int],
    intrinsic: np.ndarray,
) -> dict[str, Any]:
    """为 camera-only 模式构造空前景 Gaussian 参数.

    这里显式写出 `num_objects = 0`,
    让后续 Step 4/5/6 走“无前景对象”分支,
    而不是继续沿用 demo 风格的前景运动语义.
    """

    height, width = depth_shape
    return {
        "image_info": {
            "resolution": [int(width), int(height)],
            "depth_shape": [int(height), int(width)],
        },
        "camera_info": {
            "intrinsic": np.asarray(intrinsic, dtype=np.float32).tolist(),
            "extrinsic": np.eye(4, dtype=np.float32).tolist(),
        },
        "gaussian_params": {},
        "num_objects": 0,
        "obj_id_to_color_idx": {},
    }


def compute_movement_distance(distance_range: tuple[float, float], total_factor: float) -> float:
    """按“区间中值 × factor”计算确定性轨迹距离."""

    min_distance, max_distance = distance_range
    midpoint = (float(min_distance) + float(max_distance)) / 2.0
    return midpoint * float(total_factor)


def get_preset_run_specs(total_movement_distance_factor: float) -> list[dict[str, Any]]:
    """返回带最终距离的 canonical preset 运行规格."""

    specs: list[dict[str, Any]] = []
    for preset in TRAJECTORY_PRESETS:
        specs.append(
            {
                "index": preset.index,
                "name": preset.name,
                "kind": preset.kind,
                "camera_motion_prompt": preset.camera_motion_prompt,
                "movement_distance_range": list(preset.movement_distance_range),
                "movement_distance": compute_movement_distance(
                    preset.movement_distance_range,
                    total_movement_distance_factor,
                ),
            }
        )
    return specs


def select_preset_run_specs(
    preset_specs: list[dict[str, Any]],
    preset_indices: list[int] | None,
) -> list[dict[str, Any]]:
    """按固定 canonical 顺序筛选要执行的 preset.

    这里故意不按用户输入顺序执行.
    原因是目录编号和 manifest 都已经绑定了固定的 canonical 索引语义,
    因此筛选后仍按自然编号顺序运行更稳定.
    """

    if preset_indices is None:
        return list(preset_specs)

    normalized_indices = [int(index) for index in preset_indices]
    if len(set(normalized_indices)) != len(normalized_indices):
        raise ValueError(f"preset_indices must not contain duplicates, got {preset_indices}")

    selected_indices = set(normalized_indices)
    selected = [spec for spec in preset_specs if int(spec["index"]) in selected_indices]
    if len(selected) != len(normalized_indices):
        available = [int(spec["index"]) for spec in preset_specs]
        raise ValueError(
            f"preset_indices must be chosen from {available}, got {preset_indices}",
        )
    return selected


def build_generation_prompt(base_prompt: str, camera_motion_prompt: str) -> str:
    """把镜头动作描述稳定追加到用户原始 prompt 后面.

    这里统一收口 prompt 拼接规则,
    避免 manifest、dry-run 和真正的 Step 6 命令各自拼出不同文本.
    """

    base_text = base_prompt.strip()
    motion_text = camera_motion_prompt.strip()
    if not base_text:
        return f"{motion_text}."

    separator = " " if base_text.endswith((".", "!", "?", ";", ":")) else ". "
    if motion_text.endswith((".", "!", "?")):
        return f"{base_text}{separator}{motion_text}"
    return f"{base_text}{separator}{motion_text}."


# ============================================================================
# 深度统计
# ============================================================================
def load_depth_and_intrinsic(npz_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """读取 Step 1 产出的 `depth_intrinsics.npz`."""

    with np.load(npz_path) as data:
        depth = np.asarray(data["depth"], dtype=np.float32)
        intrinsic = np.asarray(data["intrinsic"], dtype=np.float32)
    return depth, intrinsic


def estimate_center_depth(
    depth_map: np.ndarray,
    *,
    depth_quantile: float = 0.2,
    center_crop_ratio: float = 0.5,
    fallback_depth: float = 1.0,
) -> float:
    """从深度图估计相机轨迹的 look-at center depth.

    这里对齐 Lyra 的核心思路:
    - 只在有效深度上做统计
    - 优先用中心裁剪区域
    - 如果中心裁剪没有有效值, 回退整图
    """

    if not 0.0 <= depth_quantile <= 1.0:
        raise ValueError(f"depth_quantile must be in [0, 1], got {depth_quantile}")
    if not 0.0 < center_crop_ratio <= 1.0:
        raise ValueError(f"center_crop_ratio must be in (0, 1], got {center_crop_ratio}")

    depth = np.asarray(depth_map, dtype=np.float32)
    if depth.ndim == 3:
        depth = depth[0]
    if depth.ndim != 2:
        raise ValueError(f"depth_map must be 2D or 3D, got shape {depth.shape}")

    valid_mask = np.isfinite(depth) & (depth > 0)
    if not np.any(valid_mask):
        return float(fallback_depth)

    selected_mask = valid_mask.copy()
    if center_crop_ratio < 1.0:
        height, width = depth.shape
        crop_height = max(1, int(round(height * center_crop_ratio)))
        crop_width = max(1, int(round(width * center_crop_ratio)))
        top = max(0, (height - crop_height) // 2)
        left = max(0, (width - crop_width) // 2)

        center_mask = np.zeros_like(valid_mask, dtype=bool)
        center_mask[top : top + crop_height, left : left + crop_width] = True
        center_valid_mask = valid_mask & center_mask
        if np.any(center_valid_mask):
            selected_mask = center_valid_mask

    selected_depths = depth[selected_mask]
    if selected_depths.size == 0:
        return float(fallback_depth)

    return float(np.quantile(selected_depths, depth_quantile))


def resolve_translation_reference_depth(center_depth: float, translation_reference_depth_scale: float) -> float:
    """根据 center depth 计算位移缩放参考深度."""

    return float(center_depth) * float(translation_reference_depth_scale)


# ============================================================================
# 坐标变换
# ============================================================================
def cv_vector_to_blender(vector: np.ndarray | list[float]) -> np.ndarray:
    """把 OpenCV 3D 向量变换到 Blender 坐标系."""

    vec = np.asarray(vector, dtype=np.float32).reshape(3)
    return COORD_TRANSFORM_CV2BLENDER @ vec


def cv_covariance_to_blender(covariance: np.ndarray | list[list[float]]) -> np.ndarray:
    """把 OpenCV 3D 协方差变换到 Blender 坐标系."""

    cov = np.asarray(covariance, dtype=np.float32).reshape(3, 3)
    return COORD_TRANSFORM_CV2BLENDER @ cov @ COORD_TRANSFORM_CV2BLENDER.T


# ============================================================================
# 相机轨迹生成
# ============================================================================
def _generate_linear_offsets_cv(
    *,
    direction_cv: tuple[float, float, float],
    movement_distance: float,
    translation_reference_depth: float,
    num_frames: int,
) -> np.ndarray:
    """按 Lyra 的线性轨迹公式生成 OpenCV 位移序列."""

    direction = np.asarray(direction_cv, dtype=np.float32).reshape(3)
    offsets: list[np.ndarray] = []
    for frame_index in range(num_frames):
        scalar = frame_index * movement_distance * translation_reference_depth / float(num_frames)
        # 线性 preset 的差异全部收进方向向量.
        # 这样新增平移动作时, 不需要继续扩展名字分支.
        offset_cv = direction * scalar
        offsets.append(offset_cv)

    return np.stack(offsets, axis=0)


def _generate_clockwise_offsets_cv(
    *,
    movement_distance: float,
    translation_reference_depth: float,
    num_frames: int,
    radius_x_factor: float,
    radius_y_factor: float,
    num_circles: int,
) -> np.ndarray:
    """按 Lyra 的 spiral/orbit 公式生成 OpenCV 位移序列."""

    radius_x = movement_distance * radius_x_factor
    radius_y = movement_distance * radius_y_factor
    theta_max = 2.0 * np.pi * float(num_circles)

    offsets: list[np.ndarray] = []
    for frame_index in range(num_frames):
        if num_frames == 1:
            theta = 0.0
        else:
            theta = theta_max * frame_index / float(num_frames - 1)

        x_offset = radius_x * (np.cos(theta) - 1.0) * translation_reference_depth
        y_offset = radius_y * np.sin(theta) * translation_reference_depth
        offset_cv = np.array([x_offset, y_offset, 0.0], dtype=np.float32)
        offsets.append(offset_cv)

    return np.stack(offsets, axis=0)


def make_blender_camera_to_world(position: np.ndarray, target: np.ndarray) -> np.ndarray:
    """由相机位置和 look-at 目标点生成 Blender camera-to-world 矩阵.

    Blender 相机的局部约定:
    - 相机朝向是局部 `-Z`
    - 相机上方向是局部 `+Y`

    因而 world 矩阵的三列可构造成:
    - 第 1 列: right
    - 第 2 列: up
    - 第 3 列: backward = -forward
    """

    position = np.asarray(position, dtype=np.float32).reshape(3)
    target = np.asarray(target, dtype=np.float32).reshape(3)

    forward = target - position
    forward_norm = float(np.linalg.norm(forward))
    if forward_norm < 1e-8:
        raise ValueError("Camera target is too close to camera position; cannot build a stable look-at matrix.")
    forward = forward / forward_norm

    world_up = BLENDER_WORLD_UP.copy()
    if abs(float(np.dot(forward, world_up))) > 0.999:
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    right = np.cross(forward, world_up)
    right_norm = float(np.linalg.norm(right))
    if right_norm < 1e-8:
        raise ValueError("Camera right vector collapsed while building Blender c2w matrix.")
    right = right / right_norm

    up = np.cross(right, forward)
    up_norm = float(np.linalg.norm(up))
    if up_norm < 1e-8:
        raise ValueError("Camera up vector collapsed while building Blender c2w matrix.")
    up = up / up_norm

    c2w = np.eye(4, dtype=np.float32)
    c2w[:3, 0] = right
    c2w[:3, 1] = up
    c2w[:3, 2] = -forward
    c2w[:3, 3] = position
    return c2w


def generate_blender_camera_trajectory(
    trajectory_name: str,
    *,
    movement_distance: float,
    center_depth: float,
    translation_reference_depth: float,
    num_frames: int = DEFAULT_NUM_FRAMES,
    camera_rotation: str = "center_facing",
    radius_x_factor: float = DEFAULT_RADIUS_X_FACTOR,
    radius_y_factor: float = DEFAULT_RADIUS_Y_FACTOR,
    num_circles: int = DEFAULT_NUM_CIRCLES,
) -> np.ndarray:
    """生成与 Blender 导出兼容的 `extrinsics` 序列.

    这里故意先在 OpenCV 坐标里沿用 Lyra 的轨迹定义,
    再统一变换到 Blender 坐标系.
    这样轨迹名语义和参考实现更一致.
    """

    if trajectory_name not in TRAJECTORY_PRESET_BY_NAME:
        raise ValueError(f"Unsupported trajectory name: {trajectory_name}")
    if camera_rotation not in {"center_facing", "no_rotation", "trajectory_aligned"}:
        raise ValueError(f"Unsupported camera rotation mode: {camera_rotation}")
    if num_frames <= 0:
        raise ValueError(f"num_frames must be positive, got {num_frames}")

    preset = TRAJECTORY_PRESET_BY_NAME[trajectory_name]

    # 所有 orbit 变体都复用同一条 `clockwise` 轨迹公式.
    # 差异只体现在半径倍率, 这样以后继续追加 orbit 档位时仍然只需要加数据.
    if preset.kind == "orbit":
        offsets_cv = _generate_clockwise_offsets_cv(
            movement_distance=movement_distance,
            translation_reference_depth=translation_reference_depth,
            num_frames=num_frames,
            radius_x_factor=radius_x_factor * preset.orbit_radius_scale,
            radius_y_factor=radius_y_factor * preset.orbit_radius_scale,
            num_circles=num_circles,
        )
    elif preset.kind == "linear":
        if preset.linear_direction_cv is None:
            raise ValueError(f"Linear trajectory preset is missing direction metadata: {trajectory_name}")
        offsets_cv = _generate_linear_offsets_cv(
            direction_cv=preset.linear_direction_cv,
            movement_distance=movement_distance,
            translation_reference_depth=translation_reference_depth,
            num_frames=num_frames,
        )
    else:
        raise ValueError(f"Unsupported trajectory kind: {preset.kind}")

    offsets_blender = offsets_cv @ COORD_TRANSFORM_CV2BLENDER.T
    target_blender = BLENDER_FORWARD_TARGET_UNIT * float(center_depth)

    matrices: list[np.ndarray] = []
    for position in offsets_blender:
        if camera_rotation == "center_facing":
            current_target = target_blender
        elif camera_rotation == "trajectory_aligned":
            current_target = target_blender + position * 2.0
        else:
            current_target = target_blender + position

        matrices.append(make_blender_camera_to_world(position, current_target))

    return np.stack(matrices, axis=0).astype(np.float32)


# ============================================================================
# 高斯 JSON 适配
# ============================================================================
def _build_static_gaussian_frame(
    gaussian_params: dict[str, Any],
    obj_id_to_color_idx: dict[str, int],
) -> list[dict[str, Any]]:
    """把单帧 OpenCV Gaussian 参数变成一帧 Blender 轨迹对象列表."""

    frame_objects: list[dict[str, Any]] = []
    for fallback_color_index, object_id in enumerate(_sorted_object_ids(gaussian_params.keys())):
        object_payload = gaussian_params[object_id]
        mean_blender = cv_vector_to_blender(object_payload["mean"])
        covariance_blender = cv_covariance_to_blender(object_payload["cov"])
        color_index = int(obj_id_to_color_idx.get(object_id, fallback_color_index))

        frame_objects.append(
            {
                "object_id": object_id,
                "color_index": color_index,
                "gaussian_3d": {
                    "mean": mean_blender.tolist(),
                    "covariance": covariance_blender.tolist(),
                },
            }
        )

    return frame_objects


def convert_static_gaussian_json_to_trajectory(
    gaussian_json_path: str | Path,
    output_json_path: str | Path,
    *,
    num_frames: int = DEFAULT_NUM_FRAMES,
    frame_step: int = DEFAULT_FRAME_STEP,
    description: str = "Programmatically generated static Gaussian trajectory",
) -> dict[str, Any]:
    """把 `gaussian_params.json` 广播成多帧 `custom_3D_gaussian_trajectory.json`.

    输出格式对齐 Blender 导出脚本和 Step 5 渲染器的实际输入契约.
    """

    source_path = Path(gaussian_json_path)
    output_path = Path(output_json_path)

    source_data = json.loads(source_path.read_text(encoding="utf-8"))
    gaussian_params = source_data.get("gaussian_params", {})
    obj_id_to_color_idx = {
        str(key): int(value) for key, value in source_data.get("obj_id_to_color_idx", {}).items()
    }

    static_frame_objects = _build_static_gaussian_frame(gaussian_params, obj_id_to_color_idx)
    frames: list[dict[str, Any]] = []
    for frame_index in range(0, num_frames, frame_step):
        frames.append(
            {
                "frame_index": frame_index,
                "objects": static_frame_objects,
            }
        )

    export_data = {
        "metadata": {
            "num_objects": len(static_frame_objects),
            "num_frames": num_frames,
            "frame_step": frame_step,
            "description": description,
            "obj_id_to_color_idx": obj_id_to_color_idx,
        },
        "frames": frames,
    }

    ensure_parent_dir(output_path)
    output_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return export_data


# ============================================================================
# 文件完整性检查
# ============================================================================
def is_existing_nonempty_file(path: str | Path) -> bool:
    """检查文件是否存在且非空."""

    file_path = Path(path)
    return file_path.is_file() and file_path.stat().st_size > 0


def is_valid_render_output_dir(render_output_dir: str | Path) -> bool:
    """判断 Step 5 的关键控制图视频是否完整."""

    required_files = (
        "background_RGB.mp4",
        "background_depth.mp4",
        "3D_gaussian_RGB.mp4",
        "3D_gaussian_depth.mp4",
        "merged_mask.mp4",
    )
    render_dir = Path(render_output_dir)
    return all(is_existing_nonempty_file(render_dir / file_name) for file_name in required_files)


def find_generated_video(save_dir: str | Path) -> Path | None:
    """返回 Step 6 目录下最新的生成视频路径."""

    video_dir = Path(save_dir)
    candidates = sorted(video_dir.glob("generated_video_*.mp4"))
    for candidate in candidates:
        if is_existing_nonempty_file(candidate):
            return candidate
    return None
