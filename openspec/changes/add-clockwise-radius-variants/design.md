## Context

当前单图多轨迹批处理把 preset 目录编号、manifest 键和值班输出都绑定在固定的 canonical preset 列表上。现有 orbit 逻辑只有一个 `clockwise` 分支, 它通过 `_generate_orbit_offsets_cv(...)` 结合全局 `radius_x_factor` / `radius_y_factor` 生成环绕位移。

这次需求不是新增一个可自由配置的轨迹系统, 而是在现有 deterministic preset 工作流里补两个用户可直接选择的 orbit 档位。因此设计重点不是“做出更多参数”, 而是“在不破坏现有 preset 索引和语义的前提下, 把半径和方向差异一起收进 preset 元数据”。

## Goals / Non-Goals

**Goals:**
- 为单图多轨迹批处理增加 `clockwise_0.65` 和 `counterclockwise_1.5` 两个具名 orbit preset。
- 保持现有 `clockwise` 的索引、语义、运动距离和用户使用方式不变。
- 让新增 preset 自动进入 canonical 列表、subset 选择、dry-run 展示、manifest 命名和测试覆盖。
- 用数据驱动的方式表达 orbit 半径倍率和方向, 避免把更多特殊分支堆进轨迹生成逻辑。

**Non-Goals:**
- 不引入任意半径的自由输入参数或新的自定义轨迹 DSL。
- 不改变 `left` / `right` / `up` / `zoom_out` / `zoom_in` 的行为。
- 不调整现有 `clockwise` 的默认运动距离区间、圈数默认值或相机朝向语义。
- 不修改 Blender 手工编辑工作流或 Step 1~6 的其他处理链路。

## Decisions

### 1. 在 preset 元数据中显式保存 orbit 半径倍率和方向
- 决定: 为 orbit preset 增加与名称解耦的半径倍率和方向元数据, 由 `clockwise = (1.0, 顺时针)`, `clockwise_0.65 = (0.65, 顺时针)`, `counterclockwise_1.5 = (1.5, 逆时针)` 表达差异。
- 理由: 这能把“名字”和“几何行为”分开, 让后续继续加 orbit 变体时仍然只是加数据项, 而不是继续堆 `if trajectory_name == ...`.
- 备选方案: 直接解析 preset 名字里的数字后缀.
  - 放弃原因: 名字解析会把用户可见命名绑定成隐藏协议, 也更容易让未来命名调整牵一发动全身。
- 备选方案: 在 `generate_blender_camera_trajectory(...)` 里继续新增两个硬编码分支.
  - 放弃原因: 特殊情况会继续扩散, 违背这次“改良胜过新增”的目标。

### 2. 复用现有 `clockwise` 的运动距离, 只改变 orbit 元数据
- 决定: 两个新 preset 继续使用现有 `clockwise` 的 `movement_distance_range`, 只在 orbit 位移计算时按 preset 元数据同步调整半径与方向。
- 理由: 用户需求是“6 号更紧, 7 号更大且改成逆时针”, 不是要求不同的总运动距离。复用现有 movement distance 才能保持“只改 orbit 语义, 其它都没变”。
- 备选方案: 通过修改 `movement_distance_range` 来间接拉大或缩小轨迹.
  - 放弃原因: 这会同时影响位移尺度和其它推导量, 不再是纯粹的半径倍率语义。

### 3. 保持现有索引稳定, 新 preset 追加到尾部
- 决定: 继续保留 `left..clockwise` 的现有索引 `0..5`, 新增 `clockwise_0.65 = 6`, `counterclockwise_1.5 = 7`.
- 理由: 现有测试、`--preset_indices`, 输出目录和用户脚本都已经依赖这些固定编号。追加比重排更安全。
- 备选方案: 把两个新 orbit preset 插到 `clockwise` 前后并整体重排.
  - 放弃原因: 会破坏已有索引语义, 带来不必要的兼容性回归。

### 4. 用回归测试锁定“目录顺序 + 半径比例 + 用户可见列表”
- 决定: 同时补三类测试:
  - preset 列表与 deterministic movement distance 测试
  - orbit 半径 / 方向测试
  - dry-run / subset 输出测试
- 理由: 这次变化跨越“数据定义 + 轨迹几何 + 用户可见输出”, 只测其中一层不够稳。

## Risks / Trade-offs

- [命名扩张] → 如果未来继续增加更多 orbit 档位, preset 名单会变长. 缓解: 把尺度差异抽成元数据, 让扩展仍保持数据驱动。
- [行为误改] → 如果实现时误动了原有 `clockwise` 的默认倍率或方向, 用户历史结果会漂移. 缓解: 用比例测试、方向测试和稳定索引测试同时锁住基准行为。
- [文档偏移] → 代码变成 8 个 preset 后, README 若仍写 6 个会误导用户. 缓解: 把 README 更新列入同一批任务与验证范围。

## Migration Plan

- 代码层没有持久化数据迁移需求。
- 新版本开始, 默认全量批处理会从 6 条 preset 扩展到 8 条, 其中索引 `7` 的名称与语义更新为 `counterclockwise_1.5`。
- 旧输出目录 `0..5` 和旧 `--preset_indices 0 5` 用法继续有效。
- 如需回滚, 只需移除新增 preset 元数据、对应测试和文档改动, 不涉及数据格式迁移。

## Open Questions

- 当前没有阻塞实现的开放问题。
