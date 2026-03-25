# 任务计划: 修改 7 号镜头 `clockwise_1.5` 为逆时针

## [2026-03-22 12:17:30 UTC] 新任务启动

### 目标
- 找到 7 号镜头对应的 preset / 配置定义.
- 把当前 `clockwise_1.5` 的运动方向改成逆时针.
- 同步修正相关描述、测试或文档, 并做最小验证.

### 阶段
- [ ] 阶段1: 续档后上下文重建与目标定位
- [ ] 阶段2: 修改 7 号镜头方向及相关描述
- [ ] 阶段3: 运行聚焦验证
- [ ] 阶段4: 回写日志并交付

### 关键问题
1. “7 号镜头”在当前代码里是 manifest 索引 `7`, 还是用户口头编号里的第 7 个镜头.
2. `clockwise_1.5` 的“改为逆时针”是只改几何轨迹方向, 还是连英文 prompt / README / 测试都要一起改.

### 备选方向
- 方案A: 最完整方案.
  - 同步修改轨迹几何、镜头提示文案、测试与可能受影响的文档.
- 方案B: 先满足当前需求.
  - 仅修改实际轨迹方向, 其它文案若未直接依赖则暂不动.

### 做出的决定
- 决定: 先按方案A检查.
  - 理由: 这个 preset 最近刚补过 `camera_motion_prompt`, 只改几何不改文案, 很容易留下“画面和 prompt 相反”的不一致.

### 状态
**目前在阶段1**
- 已完成六文件续档.
- 正在搜索 `clockwise_1.5` 与 7 号镜头的实际映射关系.

## [2026-03-22 12:24:30 UTC] 目标定位完成, 准备进入代码修改

### 现象
- 当前 canonical preset 列表里:
  - 索引 `7` 确实对应 `clockwise_1.5`
- 该 preset 目前和 `clockwise` / `clockwise_0.65` 一样, 都复用 `_generate_clockwise_offsets_cv(...)`.
- 当前差异只有:
  - 名称
  - prompt 文案
  - `orbit_radius_scale = 1.5`

### 做出的决定
- 决定: 不给索引 `7` 单独加硬编码分支.
  - 理由: 更稳的结构是把 orbit 的“方向”也做成 preset 元数据, 让环绕变体继续保持数据驱动.
- 决定: 将索引 `7` 的用户可见名称同步改成 `counterclockwise_1.5`.
  - 理由: 如果只改运动方向却继续保留 `clockwise_1.5` 这个名字, manifest、dry-run、README 和 prompt 都会与实际运动相反.
- 决定: README 与 OpenSpec 相关文档一起同步.
  - 理由: 这些文件已经明确写死了 `clockwise_1.5`, 不一起更新会留下规格漂移.

### 已完成
- [x] 阶段1: 续档后上下文重建与目标定位

### 状态
**目前在阶段2**
- 正在修改 orbit preset 元数据、7 号镜头名称/文案, 以及相关测试和说明文件.

## [2026-03-22 12:31:20 UTC] 代码与文档修改已落地, 准备验证

### 已修改
- `TrajectoryPreset` 已新增 orbit 方向元数据.
- 索引 `7` 已从 `clockwise_1.5` 调整为 `counterclockwise_1.5`.
- orbit 公式已改为同时受半径倍率和方向元数据控制.
- README、OpenSpec、lib/smoke 测试已同步更新.

### 验证计划
- 先做 `py_compile`, 确认修改后的 Python 文件没有语法问题.
- 再跑 `tests/test_single_image_multi_trajectory_lib.py` 与 `tests/test_single_image_multi_trajectory_smoke.py`.
- 如果测试失败, 先回看失败的是命名面还是几何方向面, 再决定是否继续修正.

### 已完成
- [x] 阶段2: 修改 7 号镜头方向及相关描述

### 状态
**目前在阶段3**
- 正在运行聚焦验证.

## [2026-03-22 12:35:40 UTC] 聚焦验证通过, 任务完成

### 验证
- `python3 -m py_compile inference/single_image_multi_trajectory_lib.py inference/single_image_multi_trajectory.py tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`
  - 结果: 通过
- `timeout 120s pixi run pytest tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py -q`
  - 结果: `16 passed in 0.96s`
- 动态数值核对:
  - `clockwise` 第 1 个非零采样点 `x,z = (-0.032950487, -0.05303301)`
  - `counterclockwise_1.5` 第 1 个非零采样点 `x,z = (-0.049425732, 0.079549514)`
  - 结论: `x` 保持 `1.5` 倍放大, `z` 变为 `-1.5` 倍, 说明半径扩大且方向已翻转为逆时针

### 已完成
- [x] 阶段3: 运行聚焦验证
- [x] 阶段4: 回写日志并交付

### 状态
**任务已完成**
- 7 号镜头现在是 `counterclockwise_1.5`.
- 几何轨迹、prompt、dry-run、README、OpenSpec 与测试已保持一致.

## [2026-03-22 12:18:55 UTC] 新任务启动: 排查 `demo_data/my4` 跑到 8 号镜头时仍只见 1 张 GPU 工作

### 目标
- 解释为什么用户看到“已经跑到 8 号镜头”, 但 `nvidia-smi` 仍只有 1 张 GPU 在工作.
- 区分这是代码逻辑问题, 还是当前实际启动参数与预期不一致.
- 给出基于动态证据的结论, 避免把猜测当根因.

### 阶段
- [x] 阶段1: 回读上下文与历史验证
- [x] 阶段2: 核对当前父进程、子进程与 manifest
- [x] 阶段3: 形成现象 / 假设 / 验证 / 结论
- [ ] 阶段4: 回写日志并向用户交付

### 关键问题
1. 当前跑到 8 号镜头时, Step 6 实际上是不是双卡 `torchrun`.
2. 用户口头贴出的双卡参数, 是否真的进入了当前正在运行的这轮进程.

### 现象
- 当前系统里确实存在 `single_image_multi_trajectory.py` 父进程和 8 号镜头的 `versecrafter_inference.py` 子进程.
- 但当前子进程参数显示:
  - `--ulysses_degree 1`
  - `--ring_degree 1`
  - `--num_inference_steps 30`
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`
- 没有看到 `torchrun` 或 `--nproc_per_node 2`.

### 当前假设
- 主假设: 当前这一轮真正跑起来的命令并不是用户以为的双卡命令, 所以只看到 1 张 GPU 工作是符合真实运行参数的.
- 备选解释: 用户现在看的可能是更早启动的一轮旧单卡进程, 而不是刚才口头贴出的那条命令对应的运行.
- 推翻主假设所需证据:
  - 如果能找到当前 8 号镜头的实际 Step 6 是 `torchrun --nproc-per-node=2`, 那主假设就不成立.

### 状态
**目前在阶段4**
- 已完成动态核对, 结论倾向于“当前运行的是单卡参数进程”.
- 下一步把证据写入日志并给用户明确解释.

### 已完成
- [x] 阶段1: 回读上下文与历史验证
- [x] 阶段2: 核对当前父进程、子进程与 manifest
- [x] 阶段3: 形成现象 / 假设 / 验证 / 结论
- [x] 阶段4: 回写日志并向用户交付

## [2026-03-22 12:36:20 UTC] 新任务启动: 停止 `demo_data/my4` 当前单卡批处理并按双卡参数重启

### 目标
- 终止当前误用单卡参数的 `demo_data/my4` 批处理进程.
- 复用已有共享产物和已完成镜头, 用明确的双卡参数继续跑后续镜头.
- 启动后立即核对是否真的出现 `torchrun --nproc-per-node=2`.

### 阶段
- [ ] 阶段1: 复核 resume / manifest 行为
- [ ] 阶段2: 停止当前单卡父子进程
- [ ] 阶段3: 用双卡命令重启批处理
- [ ] 阶段4: 核对新进程是否为 `torchrun`

### 做出的决定
- 决定: 继续使用同一个 `output_root = demo_data/my4`.
  - 理由: 当前脚本在 `resume` 模式下会复用已有共享步骤和已完成镜头, 只重做未完成部分, 这是最省时也最稳的路径.
- 决定: 不保留当前单卡进程.
  - 理由: 它已经带着错误的 Step 6 参数运行, 继续等下去只会继续单卡完成后续镜头.

### 状态
**目前在阶段1**
- 已确认 `build_generation_command()` 在 `nproc_per_node > 1` 时会改走 `torchrun`.
- 下一步停止当前单卡进程并启动明确的双卡重跑.

## [2026-03-22 12:36:50 UTC] 双卡重启与验证完成

### 验证
- 当前已确认系统中不存在旧的单卡批处理残留进程.
- `pixi run python -c "import torch, xfuser, yunchang"` 验证结果:
  - `torch.cuda.is_available() = True`
  - `torch.cuda.device_count() = 2`
  - `xfuser` / `yunchang` 导入成功
- `--dry_run` 已明确打印:
  - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py`
- 正式启动后, 当前真实进程树已经变成:
  - 父进程 `single_image_multi_trajectory.py`
  - 中间 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker
- 运行日志已打印:
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
- `nvidia-smi` 当前观测:
  - GPU0: `util=45%`, `mem=6959 MiB`
  - GPU1: `util=44%`, `mem=6959 MiB`

### 已完成
- [x] 阶段1: 复核 resume / manifest 行为
- [x] 阶段2: 停止当前单卡父子进程
- [x] 阶段3: 用双卡命令重启批处理
- [x] 阶段4: 核对新进程是否为 `torchrun`

### 状态
**任务已完成**
- `demo_data/my4` 已按双卡参数重新启动.
- 当前正在处理 8 号镜头的 Step 6, 且两张 A800 都已实际参与计算.

## [2026-03-24 17:44:33 UTC] 新任务启动: 跳过网络检查并直接复用本地模型缓存

### 目标
- 找到 `inference/single_image_multi_trajectory.py` 这一链路里哪些模型加载点会触发联网检查.
- 区分当前问题是 Hugging Face Hub 的在线检查, 还是脚本内部主动下载.
- 给出最快可执行的离线运行方式, 优先不改代码.

### 阶段
- [ ] 阶段1: 回读上下文并定位相关脚本/下载逻辑
- [ ] 阶段2: 形成现象 / 假设 / 验证路径
- [ ] 阶段3: 给出可直接执行的离线方案
- [ ] 阶段4: 回写日志与建议

### 关键问题
1. `--transformer_path model/VerseCrafter` 是否已经完全本地化, 还是内部仍会去 Hub 补充其它组件.
2. 当前最可能触发联网的点是 MoGe 权重、diffusers/transformers 的 `from_pretrained`, 还是 `huggingface_hub` 的 HEAD / metadata 检查.

### 备选方向
- 方案A: 最稳方案.
  - 定位所有 `from_pretrained` / `hf_hub_download` 调用点, 明确需要的离线环境变量和本地路径传法.
- 方案B: 先求快速可跑.
  - 如果代码已经主要走本地目录, 就直接给出 `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` / `HF_DATASETS_OFFLINE=1` 这类最小命令覆盖.

### 做出的决定
- 决定: 先按方案A核对代码路径, 再输出方案B式的最短命令.
  - 理由: 这样可以避免把通用 Hugging Face 经验误套到本项目, 结果用户一跑仍然会在别的组件上联网.

### 状态
**目前在阶段1**
- 已完成六文件回读.
- 正在定位多轨迹脚本、底层推理脚本以及模型加载实现中的联网入口.

## [2026-03-24 18:00:55 UTC] 离线排查完成, 准备交付

### 现象
- 用户想快速跳过联网检查, 直接使用本地缓存模型.

### 假设
- 主假设: 当前命令本身已经基本走本地模型, 真正需要补的是 Hugging Face 的离线开关与 `resume` 复用.
- 备选解释: 仍有某个子组件把本地路径误判成 repo id, 从而继续访问网络.

### 验证
- 静态验证:
  - `single_image_multi_trajectory.py` Step 1 仅在共享深度缺失时调用 `moge-v2_infer.py`, 且默认 `resume=True`.
  - `camera_only=True` 时跳过真实分割模型与 Gaussian 拟合.
  - `versecrafter_inference.py` 主模型路径为本地 `model/Wan2.1-T2V-14B`, 并优先从本地目录 `model/VerseCrafter` 读 transformer.
  - MoGe `from_pretrained` 若传入路径存在, 直接读本地 checkpoint; 仅路径不存在时才走 `hf_hub_download`.
- 动态验证:
  - `HF_HUB_OFFLINE=1` 下, 本地 tokenizer 与本地 MoGe checkpoint 都能成功加载.
  - `demo_data/my5` 已存在共享 `depth_intrinsics.npz` 与 `gaussian_params.json`, 可直接复用.

### 结论
- 当前主假设成立.
- 最快方案是继续使用本地路径, 在命令前加 `HF_HUB_OFFLINE=1`, 并复用同一个 `--output_root demo_data/my5`.
- 若省略 `--moge_pretrained`, 则会回退到默认 Hub repo id, 离线模式下可能失败.

### 已完成
- [x] 阶段1: 回读上下文并定位相关脚本/下载逻辑
- [x] 阶段2: 形成现象 / 假设 / 验证路径
- [x] 阶段3: 给出可直接执行的离线方案
- [x] 阶段4: 回写日志与建议

### 状态
**任务已完成**
- 已拿到静态证据、动态验证结果与可直接执行的离线命令.
