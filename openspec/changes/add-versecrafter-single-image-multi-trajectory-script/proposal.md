## Why

VerseCrafter 当前的脚本工作流默认把 Step 4 的相机与物体轨迹编辑交给 Blender 手工完成. 这让“同一张图批量生成多条不同相机运动视频”变得低效、难复现, 也不适合快速做镜头对比实验. 现在需要一个 VerseCrafter 原生的自动化入口, 把单图输入、共享预处理、固定 6 条相机轨迹和批量视频生成串成一条可重复执行的脚本流程.

## What Changes

- 新增一个 VerseCrafter 单图多轨迹批处理脚本入口, 自动串起深度估计、分割、3D Gaussian 拟合、轨迹生成、4D control map 渲染和最终视频生成.
- 内置 6 条固定相机运动 preset: `left`, `right`, `up`, `zoom_out`, `zoom_in`, `clockwise`.
- 使用确定性的轨迹距离策略, 由 preset 区间中值乘 `total_movement_distance_factor` 得到最终 `movement_distance`, 不做随机采样.
- 输出目录保持 `0/1/2/3/4/5` 六个数字子目录, 并在根目录生成 `manifest.json` 记录轨迹名、距离、中心深度与执行状态.
- 自动生成与 Blender 导出兼容的 `custom_camera_trajectory.npz` 和静态多帧 `custom_3D_gaussian_trajectory.json`, 用来替代手工 Step 4.
- 第一版对 `0 objects` 场景采用 fail-fast, 明确提示当前 workflow 需要至少一个前景对象.

## Capabilities

### New Capabilities
- `single-image-multi-trajectory-generation`: 允许用户从单张输入图出发, 通过一个 VerseCrafter 原生脚本一次生成 6 条固定相机轨迹的视频结果, 并复用共享预处理结果.

### Modified Capabilities
- 无.

## Impact

- 受影响代码主要集中在 `inference/` 目录, 包括新的 orchestrator 脚本、轨迹生成/静态高斯轨迹适配辅助模块, 以及对现有渲染与生成脚本的调用编排.
- 会新增一种稳定的输出目录约定和根级 `manifest.json` 元数据文件.
- 会影响 README / 脚本用法文档, 因为仓库将新增一个不依赖 Blender 手工编辑的相机多轨迹工作流入口.
- 不引入新的外部模型依赖, 但会复用当前 MoGe、Grounded-SAM-2、3D Gaussian 拟合、4D control map 渲染与 VerseCrafter 推理链路.
