## ADDED Requirements

### Requirement: Stable clockwise preset catalog
单图多轨迹批处理 SHALL 提供 8 个 deterministic preset, canonical 顺序依次为 `left`, `right`, `up`, `zoom_out`, `zoom_in`, `clockwise`, `clockwise_0.65`, `clockwise_1.5`。现有 preset 的索引 `0..5` MUST 保持不变, 新增 preset MUST 追加为索引 `6` 和 `7`。

#### Scenario: Default preset catalog includes the two new clockwise variants
- **WHEN** 系统构建默认的 preset run specs
- **THEN** canonical preset 列表包含索引 `6` 的 `clockwise_0.65` 和索引 `7` 的 `clockwise_1.5`
- **AND** 索引 `5` 仍然对应原有的 `clockwise`

### Requirement: Clockwise radius variants preserve orbit semantics
系统 SHALL 将 `clockwise_0.65` 和 `clockwise_1.5` 作为 `clockwise` 的 orbit 半径变体来生成。它们 MUST 复用基准 `clockwise` 的运动距离、圈数、相机朝向逻辑与 Blender x-z 平面环绕语义, 仅把 orbit 半径分别缩放为基准 `clockwise` 的 `0.65` 倍和 `1.5` 倍。

#### Scenario: Smaller clockwise variant shrinks the orbit radius only
- **WHEN** 系统使用相同的 `movement_distance`, `center_depth`, `translation_reference_depth`, `num_frames`, `camera_rotation`, `radius_x_factor`, `radius_y_factor` 和 `num_circles` 分别生成 `clockwise` 与 `clockwise_0.65`
- **THEN** `clockwise_0.65` 的轨迹仍位于 Blender x-z 环绕平面, 并保持与基准 `clockwise` 相同的闭环拓扑
- **AND** `clockwise_0.65` 的最大轨道位移幅度等于基准 `clockwise` 的 `0.65` 倍

#### Scenario: Larger clockwise variant expands the orbit radius only
- **WHEN** 系统使用相同的 `movement_distance`, `center_depth`, `translation_reference_depth`, `num_frames`, `camera_rotation`, `radius_x_factor`, `radius_y_factor` 和 `num_circles` 分别生成 `clockwise` 与 `clockwise_1.5`
- **THEN** `clockwise_1.5` 的轨迹仍位于 Blender x-z 环绕平面, 并保持与基准 `clockwise` 相同的闭环拓扑
- **AND** `clockwise_1.5` 的最大轨道位移幅度等于基准 `clockwise` 的 `1.5` 倍

### Requirement: Preset subset selection includes the new clockwise variants
系统 SHALL 允许用户通过 `--preset_indices` 选择新的顺时针半径变体, 并且返回结果 MUST 继续按 canonical 索引顺序排列, 不能按用户输入顺序漂移。

#### Scenario: Selecting baseline and new clockwise variants preserves canonical order
- **WHEN** 用户请求 preset indices `[7, 0, 5, 6]`
- **THEN** 被选中的 preset 顺序为索引 `[0, 5, 6, 7]`
- **AND** 对应名称依次为 `left`, `clockwise`, `clockwise_0.65`, `clockwise_1.5`

#### Scenario: Dry-run lists the expanded preset set
- **WHEN** 用户在不传 `--preset_indices` 的情况下执行 batch dry-run
- **THEN** 计划轨迹列表中同时展示 `clockwise_0.65` 和 `clockwise_1.5`
