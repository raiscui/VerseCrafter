from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import torch


def _load_rendering_module():
    repo_root = Path(__file__).resolve().parents[1]
    inference_dir = repo_root / "inference"
    module_path = inference_dir / "rendering_4D_control_maps.py"

    if str(inference_dir) not in sys.path:
        sys.path.insert(0, str(inference_dir))

    spec = importlib.util.spec_from_file_location("rendering_4d_control_maps_test_module", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rendering_module_imports_without_kornia_runtime_dependency() -> None:
    # 这个断言锁住当前回归:
    # 即使环境里的 flash_attn 因 ABI 不匹配而不可导入,
    # 渲染脚本本身也不应该在模块导入阶段被无关依赖拖死.
    module = _load_rendering_module()

    assert hasattr(module, "depth_to_3d_v2_compatible")


def test_depth_to_3d_v2_compatible_projects_pixels_with_intrinsics() -> None:
    module = _load_rendering_module()

    depth = torch.tensor(
        [
            [2.0, 2.0],
            [2.0, 2.0],
        ],
        dtype=torch.float32,
    )
    intrinsic = torch.tensor(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=torch.float32,
    )

    points = module.depth_to_3d_v2_compatible(depth, intrinsic, normalize_points=False)

    expected = torch.tensor(
        [
            [[0.0, 0.0, 2.0], [2.0, 0.0, 2.0]],
            [[0.0, 2.0, 2.0], [2.0, 2.0, 2.0]],
        ],
        dtype=torch.float32,
    )

    assert points.shape == (2, 2, 3)
    assert torch.allclose(points, expected)
