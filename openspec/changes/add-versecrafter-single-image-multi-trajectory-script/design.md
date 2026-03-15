## Context

VerseCrafter 当前的公开工作流是一个很典型的 6 步链路:

1. `moge-v2_infer.py` 估计深度与相机内参.
2. `grounded_sam2_infer.py` 提取前景对象 mask.
3. `fit_3D_gaussian.py` 拟合静态 3D Gaussian.
4. Blender 中手工编辑相机和物体轨迹.
5. `rendering_4D_control_maps.py` 渲染控制图.
6. `versecrafter_inference.py` 生成最终视频.

这条链路的瓶颈不在模型本身, 而在 Step 4 仍然依赖 Blender 人工操作. 对“同一张图快速比较多种镜头运动”这个需求来说, 手工导出 6 次轨迹既慢, 也不利于复现.

这次 change 的目标, 不是推翻现有 Step 1-6, 而是在 `inference/` 里补一个 VerseCrafter 原生的自动化入口. 它要做到两件事:

- 共享预处理只跑一次.
- 自动替代手工 Step 4, 为同一场景稳定产出 6 条固定相机轨迹, 再逐条完成 Step 5 和 Step 6.

已有代码的几个关键约束已经很明确:

- `rendering_4D_control_maps.py` 读取的 `custom_camera_trajectory.npz` 必须包含 `extrinsics`, 其语义是 Blender 坐标系下的 camera-to-world 矩阵. 渲染脚本会在内部做轴翻转并求逆, 转成 OpenCV 风格的 `w2c`.
- `fit_3D_gaussian.py` 输出的是单帧 `gaussian_params.json`.
- `rendering_4D_control_maps.py` 读取的却是多帧 `custom_3D_gaussian_trajectory.json`, 格式是 `metadata + frames`.
- `versecrafter_inference.py` 目前仍是 CLI-first 脚本, 文件顶层就会解析参数并启动模型加载, 并不适合作为可安全 import 的库函数来编排.

用户还给了很明确的行为约束:

- 输出子目录固定使用 `0/1/2/3/4/5`.
- 6 条轨迹固定为 `left/right/up/zoom_out/zoom_in/clockwise`.
- `movement_distance` 不做随机采样, 改为区间中值乘 `total_movement_distance_factor`.
- 下面 3 个参数作为新脚本的默认值:
  - `--auto_center_depth_quantile 0.2`
  - `--translation_reference_depth_scale 0.95`
  - `--total_movement_distance_factor 1.5`
- 第一版暂不支持 `num_objects == 0` 的纯背景自动链路.

## Goals / Non-Goals

**Goals:**
- 新增一个单入口 orchestrator, 从单张输入图出发, 自动串起 VerseCrafter 的 Step 1-6.
- 共享深度估计、分割和 3D Gaussian 拟合结果, 避免每条轨迹重复跑前处理.
- 生成 6 条固定、确定性的相机轨迹, 并保持与 Lyra `multi_trajectory` 相近的镜头语义.
- 自动生成 Blender 兼容的 `custom_camera_trajectory.npz` 与静态多帧 `custom_3D_gaussian_trajectory.json`.
- 为每条轨迹单独产出 control maps 和最终视频, 同时在根目录写出 `manifest.json`.
- 让 rerun 行为可恢复, 至少能复用已完成的共享预处理和已成功的轨迹目录.

**Non-Goals:**
- 不替换现有 `moge-v2_infer.py`、`grounded_sam2_infer.py`、`fit_3D_gaussian.py`、`rendering_4D_control_maps.py`、`versecrafter_inference.py` 的原始 CLI 入口.
- 不在第一版支持任意用户自定义轨迹编辑器, 也不重新实现 Blender UI.
- 不在第一版支持 `0 objects` 的纯背景 workflow.
- 不在第一版重构 VerseCrafter 推理为常驻服务或内存常驻 pipeline.
- 不为 Blender 手工工作流做迁移改造; 旧流程继续保留.

## Decisions

### 1. 使用“新 orchestrator + 少量 helper”的结构, 不直接改写现有 5 个脚本

**决定**
- 新增一个总入口脚本, 放在 `inference/single_image_multi_trajectory.py`.
- 再配两个轻量 helper:
  - 一个负责轨迹 preset、距离计算和相机位姿生成.
  - 一个负责把 `gaussian_params.json` 适配成静态多帧 `custom_3D_gaussian_trajectory.json`.

**为什么这样做**
- 现有几个 step 脚本已经稳定工作, 但大多是 CLI-first 设计, 例如 `versecrafter_inference.py` 在 import 时就解析参数并启动主逻辑. 直接把它们硬改成库接口, 会把这次需求升级成“整条推理链重构”.
- 用户这次要的是一个 VerseCrafter 版本的批处理入口. 最稳的路线是用 orchestrator 串现有脚本, 只把新需求集中在“轨迹生成”和“文件适配”两块新增代码里.

**备选方案**
- 方案 A: 直接 import 现有 step 的内部函数, 在单进程内完成整条流水线.
  - 优点: 未来可复用性更强, 也更容易做模型复用优化.
  - 缺点: 需要先把多个脚本改造成可 import 的库模块, 改动面大, 风险也大.
- 方案 B: 新增 orchestrator, 通过 `python3` 子进程复用现有 CLI.
  - 选择 B, 因为它对现有仓库侵入最小, 也更符合这次 change 的范围.

### 2. 共享预处理结果统一落到根目录 `shared/`, 每条轨迹只保留自己的轨迹和生成产物

**决定**
- 新工作流的根输出目录形如:

```text
<output_root>/
  manifest.json
  shared/
    estimated_depth/
      depth_intrinsics.npz
    foreground_masks/
      ...
    fitted_3D_gaussian/
      gaussian_params.json
  0/
    custom_camera_trajectory.npz
    custom_3D_gaussian_trajectory.json
    rendering_4D_maps/
      *.mp4
    generated_videos/
      generated_video_0.mp4
  1/
  2/
  3/
  4/
  5/
```

**为什么这样做**
- 用户要求顶层轨迹目录必须是数字. 那么共享产物如果混进 `0..5` 之一, 结构会很别扭, 也不利于恢复执行.
- `shared/` 把“场景级一次性产物”和“轨迹级重复产物”分开后, manifest 也更好表达.

**备选方案**
- 把深度、mask、Gaussian 拟合结果复制到每个轨迹目录.
  - 拒绝原因: 浪费磁盘, 也会让 rerun 很难判断哪些内容是真正共享的.
- 继续沿用 demo 里的 `camera_object_0` 命名.
  - 拒绝原因: 用户已经明确要求顶层目录固定为纯数字 `0..5`.

### 3. 轨迹枚举遵循 Lyra 的 6 条 preset, 但坐标映射以 VerseCrafter / Blender 兼容性为准

**决定**
- 轨迹表固定如下:

| idx | name | Lyra 区间 | 中值 | 默认最终距离(×1.5) | VerseCrafter 中的 Blender 实际位移 |
| --- | --- | --- | ---: | ---: | --- |
| 0 | left | [0.2, 0.3] | 0.25 | 0.375 | `x` 负方向 |
| 1 | right | [0.2, 0.3] | 0.25 | 0.375 | `x` 正方向 |
| 2 | up | [0.1, 0.2] | 0.15 | 0.225 | `z` 正方向 |
| 3 | zoom_out | [0.3, 0.4] | 0.35 | 0.525 | `y` 负方向 |
| 4 | zoom_in | [0.3, 0.4] | 0.35 | 0.525 | `y` 正方向 |
| 5 | clockwise | [0.4, 0.6] | 0.50 | 0.750 | 围绕目标点做顺时针 orbit |

- `movement_distance` 的计算公式固定为:
  - `midpoint(base_range) * total_movement_distance_factor`
  - 第一版不做随机采样.
- `clockwise` 的 orbit 参数沿用 Lyra 文档里的默认思路:
  - `radius_x_factor = 0.15`
  - `radius_y_factor = 0.10`
  - `num_circles = 2`

**为什么这样做**
- 用户要求轨迹名、编号和强度区间对齐 Lyra.
- 但 VerseCrafter 渲染端读取的是 Blender c2w 矩阵. 如果把 Lyra 的“x/y/z 语义”原封不动套进 Blender 坐标, 镜头的视觉结果会偏掉.
- 因此这里保留 Lyra 的“镜头意图”, 但在 VerseCrafter 中把它映射到 Blender 可直接消费的位姿空间.

**备选方案**
- 完全字面照抄 Lyra 的轴定义, 例如 `up -> y negative`, `zoom -> z axis`.
  - 拒绝原因: 这是假设两边轨迹都处在同一坐标语义下, 但 VerseCrafter 最终要写 Blender c2w, 渲染阶段又会做轴翻转, 直接照搬很容易导致画面运动方向和人类预期相反.
- 随机采样 `movement_distance`.
  - 拒绝原因: 用户明确要求距离固定, 不随机.

### 4. `center_depth` 和 `translation_reference_depth` 的估计逻辑对齐 Lyra 的自动中心深度思路

**决定**
- 从 `shared/estimated_depth/depth_intrinsics.npz` 读取深度图.
- 默认在有效深度的中心裁剪区域上取分位数估计 `center_depth`:
  - `mode = center_crop`
  - `depth_quantile = 0.2`
  - `center_crop_ratio = 0.5`
  - `fallback_depth = 1.0`
- `translation_reference_depth` 默认按下面公式得到:
  - `translation_reference_depth = center_depth * 0.95`
- `total_movement_distance_factor` 默认是 `1.5`.

**为什么这样做**
- Lyra 中这三个参数的职责是分开的:
  - `center_depth` 决定相机 look-at 的前后位置.
  - `translation_reference_depth` 只影响位移尺度, 不改变 look-at 中心本身.
  - `total_movement_distance_factor` 决定 preset 运动幅度整体放大多少.
- 用户明确点名要这三个参数作为新脚本默认值, 所以 VerseCrafter 版必须保留同样的调节语义, 而不是只照抄参数名.

**备选方案**
- 固定 `center_depth = 1.0`.
  - 拒绝原因: 这会退回旧式固定中心深度行为, 对不同景深场景不稳定.
- 直接把 `translation_reference_depth` 写死成常数.
  - 拒绝原因: 同一常数在近景和远景上会表现成完全不同的运动幅度.

### 5. 相机轨迹文件直接写 Blender c2w, 静态高斯轨迹 JSON 由程序广播成多帧格式

**决定**
- 每条轨迹目录都生成:
  - `custom_camera_trajectory.npz`
  - `custom_3D_gaussian_trajectory.json`
- 相机轨迹文件的 `extrinsics` 直接写 Blender 坐标系下的 `[T, 4, 4] camera-to-world` 矩阵.
- 高斯轨迹适配器读取 `shared/fitted_3D_gaussian/gaussian_params.json`, 把每个对象的单帧 `mean/covariance` 广播到所有帧, 生成渲染脚本可读的 `metadata + frames` 结构.

**为什么这样做**
- 这是和现有 Step 5 契约最贴合的方式. 自动脚本产出的文件只要满足 Blender 导出语义, `rendering_4D_control_maps.py` 就不需要改格式.
- 静态场景下, 前景 3D Gaussian 在帧间不动是完全合理的第一版假设.

**备选方案**
- 改 `rendering_4D_control_maps.py`, 让它直接接受单帧 `gaussian_params.json`.
  - 拒绝原因: 这会改动现有渲染入口的文件契约, 风险大于收益.
- 直接在新脚本里构造渲染端内部的 OpenCV `w2c`.
  - 拒绝原因: 这会绕过当前已经稳定的 Blender 导出语义, 后续更难排查坐标问题.

### 6. Orchestrator 采用“共享阶段失败即终止, 单轨迹失败不中断整批”的执行策略

**决定**
- 共享阶段包含 Step 1-3:
  - 深度估计
  - 前景分割
  - 3D Gaussian 拟合
- 共享阶段任一步失败, 整个批处理直接终止.
- 单轨迹阶段包含:
  - 轨迹文件生成
  - control maps 渲染
  - 最终视频生成
- 某一条轨迹失败时:
  - 记录错误到 `manifest.json`
  - 保留已经生成的中间文件
  - 继续执行其他轨迹
- 第一版提供 `--resume` 语义, 默认开启:
  - 已存在且校验通过的 `shared/` 产物不重复跑.
  - 已完成视频生成的轨迹目录默认跳过.

**为什么这样做**
- 共享阶段失败时继续往下没有意义, 因为 6 条轨迹都会依赖这批结果.
- 单轨迹失败通常是局部问题, 例如某次渲染或生成中断, 不应该让另外 5 条都白跑.
- 默认 `resume` 可以让长任务恢复更自然, 尤其是 Step 6 耗时长的时候.

**备选方案**
- 任何轨迹失败都立刻停止整批.
  - 拒绝原因: 对批量对比实验很不友好.
- 不做恢复能力, 每次都全量重跑.
  - 拒绝原因: 会明显放大 Step 1-3 的重复成本.

### 7. 根目录 `manifest.json` 作为批处理状态的单一事实来源

**决定**
- 根目录生成 `manifest.json`, 至少记录:
  - 输入参数摘要
  - 共享阶段输出路径
  - 6 条轨迹的 `idx -> name` 映射
  - 每条轨迹的 `movement_distance`
  - `center_depth`
  - `translation_reference_depth`
  - 当前阶段状态
  - 视频输出路径
  - 错误信息和时间戳

**为什么这样做**
- 顶层目录用了纯数字, 人眼不容易直接看出 `0` 到底是哪条轨迹.
- 有 manifest 后, rerun、失败定位和结果对比都会简单很多.

**备选方案**
- 不写 manifest, 只靠目录命名和日志.
  - 拒绝原因: 机器不可读, 恢复执行也难以稳定判断状态.

## Risks / Trade-offs

- [现有 step 脚本以 CLI 为主, 进程间编排开销更高] → 第一版接受子进程开销, 先保证低侵入和稳定性. 等工作流稳定后, 再考虑把 Step 5/6 抽成可 import 的库接口.
- [Blender 坐标和 Lyra 轨迹坐标语义不完全一致, 方向映射容易写反] → 在实现阶段为 6 条 preset 补充最小回归测试, 重点校验 `left/right/up/zoom_in/zoom_out` 的首尾位移方向和 `clockwise` 的轨迹封闭性.
- [自动中心深度在极端深度图上可能退化] → 保留 `fallback_depth=1.0`, 并把 `center_depth`、`translation_reference_depth` 实际值写入 manifest 方便复查.
- [零对象场景直接失败会限制可用性] → 第一版明确 fail-fast 并给出错误提示, 作为后续迭代项再讨论纯背景分支.
- [resume 判断如果只看文件存在, 可能误把残缺输出当成功] → 实现时对关键文件做最小完整性检查, 例如 JSON 可解析、核心 mp4 文件存在且非零大小.

## Migration Plan

1. 在 `inference/` 新增 orchestrator 和 helper 文件.
2. 在不改坏现有 Step 1-6 CLI 的前提下, 先接通单图共享预处理.
3. 接着补齐 6 条轨迹生成与静态 Gaussian trajectory 适配.
4. 再串上 Step 5 和 Step 6, 形成一条完整的批处理命令.
5. 更新 README 或相关文档, 给出 VerseCrafter 版的单图 6 轨迹示例命令.
6. 用 `demo_data/` 做一次 smoke test, 校验目录结构、manifest 和视频输出.

**Rollback**
- 这次变更不修改现有数据格式和旧工作流.
- 如果需要回滚, 只需移除新增脚本、辅助模块和文档入口即可.
- 旧的 Blender 手工工作流不会受影响.

## Open Questions

- 第一版是否需要暴露 `--trajectory_indices` 一类参数, 允许只跑部分 preset? 当前设计默认固定跑 6 条, 这更贴合用户需求, 但后续很可能会需要局部重跑入口.
- `manifest.json` 是否要额外记录每条轨迹对应的视频首帧缩略图路径? 这不是实现主线, 但对后续做批量比对会很方便.
- 长远看, 是否要把 `rendering_4D_control_maps.py` 和 `versecrafter_inference.py` 抽成可 import 的库接口, 减少 orchestrator 的进程切换成本? 这个问题先记录, 不纳入本次 change.
