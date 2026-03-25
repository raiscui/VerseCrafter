## Why

当前单图多轨迹批处理只提供一个 `clockwise` 环绕镜头档位。用户如果想要更紧的顺时针环绕, 或者更大的逆时针环绕, 只能手动改全局半径参数并单独重跑, 这会破坏 preset 工作流的确定性和可复用性。

## What Changes

- 新增两个 orbit 镜头 preset: `clockwise_0.65` 和 `counterclockwise_1.5`.
- 两个新 preset 复用现有 `clockwise` 的圈数、朝向逻辑和确定性距离计算; 其中 `clockwise_0.65` 保持顺时针并把半径缩到当前 `clockwise` 的 `0.65` 倍, `counterclockwise_1.5` 则改为逆时针并把半径放大到 `1.5` 倍.
- 保持现有 preset 名称与索引稳定, `clockwise` 继续保留在原索引位置, 两个新 preset 追加到列表尾部并可通过 `--preset_indices` 选择.
- 更新用户可见的 preset 列表、批处理说明和回归测试, 让默认批处理与 dry-run 输出反映新增后的 preset 集合.

## Capabilities

### New Capabilities
- `clockwise-radius-variants`: 为单图多轨迹批处理提供一个更紧的顺时针 orbit 变体和一个更大的逆时针 orbit 变体, 并保证它们与基准 `clockwise` 共享相同的圈数、朝向与确定性距离计算。

### Modified Capabilities

## Impact

- `inference/single_image_multi_trajectory_lib.py`
- `inference/single_image_multi_trajectory.py`
- `tests/test_single_image_multi_trajectory_lib.py`
- `tests/test_single_image_multi_trajectory_smoke.py`
- `README.md`
