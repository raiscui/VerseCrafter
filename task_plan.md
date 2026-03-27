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

## [2026-03-25 10:19:21 UTC] 新任务启动: 等待 `demo_data/my6` 完成后接手启动 `demo_data/my7`

### 目标
- 确认上一轮 `demo_data/my6` 是否已经真正完成, 避免和新一轮 `demo_data/my7` 抢占同一组 GPU.
- 在 `my6` 完成后, 按用户给定参数启动 `demo_data/my7` 的单图多轨迹生成.
- 启动后核对进程和输出目录, 确认任务已经稳定进入运行状态.

### 阶段
- [ ] 阶段1: 回读上下文并确认 `my6` 当前真实状态
- [ ] 阶段2: 等待或确认 `my6` 结束
- [ ] 阶段3: 启动 `my7` 推理命令
- [ ] 阶段4: 核对 `my7` 运行状态并回写日志

### 关键问题
1. `my6` 当前是仍在正常运行, 还是父进程残留但真正的子任务已经退出.
2. `my7` 是否应该直接新开全量任务, 还是需要先确认输出目录下有没有残留中间产物.

### 现象
- 当前系统中仍存在 `my6` 的父进程:
  - `pixi run python inference/single_image_multi_trajectory.py ... --output_root demo_data/my6`
- `demo_data/my6/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 0-7 号镜头 `status = completed`
  - 8 号镜头 `render_status = completed`, 但 `generation_status = pending`
- `demo_data/my7` 当前只有输入图 `d.png`, 尚未开始生成.

### 当前假设
- 主假设: `my6` 还没有完成, 当前至少卡在 8 号镜头进入生成前后的某个阶段, 现在不能直接并发启动 `my7`.
- 备选解释: 也可能是子进程已经退出, 但父进程或 manifest 还没来得及收尾更新.
- 推翻主假设所需证据:
  - 如果当前系统里已经没有 `my6` 相关的有效子进程, 且 manifest 随后更新为 `completed`, 那就说明只是尾声收尾而不是仍在计算.

### 状态
**目前在阶段1**
- 已完成六文件回读.
- 正在核对 `my6` 的真实进程状态, 准备在它完成后立即启动 `my7`.

## [2026-03-25 10:20:12 UTC] `my6` 真实状态确认完成, 进入等待阶段

### 验证
- 动态证据:
  - 当前父进程 `140743` 仍在运行 `inference/single_image_multi_trajectory.py --output_root demo_data/my6`
  - 当前子进程 `231319` 正在执行:
    - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py`
    - 输出路径指向 `demo_data/my6/8/generated_videos`
  - `nvidia-smi` 当前显示:
    - GPU0 `100%`, `75117 / 81920 MiB`
    - GPU1 `100%`, `75117 / 81920 MiB`
- 静态证据:
  - `demo_data/my6/manifest.json` 顶层 `status = running`
  - 8 号镜头 `render_status = completed`, `generation_status = pending`

### 结论
- 上一条主假设成立.
- `my6` 当前仍在真实计算中, 不能与 `my7` 并发启动.

### 已完成
- [x] 阶段1: 回读上下文并确认 `my6` 当前真实状态

### 当前待办
- [x] 阶段1: 回读上下文并确认 `my6` 当前真实状态
- [ ] 阶段2: 等待或确认 `my6` 结束
- [ ] 阶段3: 启动 `my7` 推理命令
- [ ] 阶段4: 核对 `my7` 运行状态并回写日志

### 状态
**目前在阶段2**
- 已确认 `my6` 正在用双卡处理 8 号镜头生成阶段.
- 下一步等待它结束后立即启动 `my7`.

## [2026-03-25 10:35:47 UTC] 已建立自动接力等待会话

### 已执行动作
- 已启动一个持续等待会话:
  - 当 `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 不再匹配时, 立即执行用户提供的 `demo_data/my7` 命令.
- 当前等待会话最近一次输出时间:
  - `2026-03-25 10:35:47 UTC`

### 额外观测
- `demo_data/my6/8/generated_videos/generated_video_0.mp4` 已经落盘.
- `manifest.json` 当前显示:
  - 8 号镜头 `completed`
  - 9 号镜头 `trajectory_assets_status = completed`
  - 9 号镜头 `render_status = completed`
  - 9 号镜头 `generation_status = pending`

### 当前待办
- [x] 阶段1: 回读上下文并确认 `my6` 当前真实状态
- [ ] 阶段2: 等待或确认 `my6` 结束
- [ ] 阶段3: 启动 `my7` 推理命令
- [ ] 阶段4: 核对 `my7` 运行状态并回写日志

### 状态
**目前在阶段2**
- `my6` 正常推进到 9 号镜头的生成前后阶段.
- `my7` 已进入自动接力等待, 无需人工再次敲命令.

## [2026-03-25 13:10:52 UTC] 发现自动接力脚本自匹配, 准备改为直接启动 `my7`

### 现象
- 用户提示 `my6` 已经做完, 需要查看 `my7`.
- 当前系统里没有任何真实的 `demo_data/my6` / `demo_data/my7` 推理进程.
- 只剩一个等待脚本进程 `242902`.
- `demo_data/my7` 仍只有输入图 `d.png`, 没有 `manifest.json`.

### 假设
- 主假设: 等待脚本里的 `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 把等待脚本自身也匹配进去了, 导致它一直认为 `my6` 还在运行.
- 备选解释: 也可能是 `my6` 虽然完成了, 但等待脚本还没跑到下一轮检查.

### 验证
- 静态证据:
  - `demo_data/my6/manifest.json` 顶层 `status = completed`
  - 8-11 号镜头全部 `completed`
- 动态证据:
  - `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 当前只返回等待脚本自身 `242902`
  - `ps -ef` 中没有真实的 `single_image_multi_trajectory.py --output_root demo_data/my6`
  - `demo_data/my7/manifest.json` 仍不存在

### 结论
- 主假设成立.
- 之前的自动接力没有真正开始 `my7`, 需要手动停止误挂脚本并直接启动 `my7`.

### 当前待办
- [x] 阶段1: 回读上下文并确认 `my6` 当前真实状态
- [x] 阶段2: 等待或确认 `my6` 结束
- [ ] 阶段3: 启动 `my7` 推理命令
- [ ] 阶段4: 核对 `my7` 运行状态并回写日志

### 状态
**目前在阶段3**
- 已确认 `my6` 完成.
- 正在停止误挂的等待脚本, 然后直接启动 `my7`.

## [2026-03-25 13:12:09 UTC] `my7` 已直接启动并完成首轮运行核对

### 验证
- 动态证据:
  - 当前父进程:
    - `pixi run python inference/single_image_multi_trajectory.py --output_root demo_data/my7`
  - 当前主 Python 进程:
    - `inference/single_image_multi_trajectory.py --output_root demo_data/my7`
  - 当前子进程:
    - `inference/rendering_4D_control_maps.py`
    - 输出目录指向 `demo_data/my7/0/rendering_4D_maps`
  - 运行日志已显示:
    - MoGe 深度估计完成
    - 已进入 `Rendering(mesh-batch) background`
- 静态证据:
  - `demo_data/my7/manifest.json` 已创建, 顶层 `status = running`
  - 0 号镜头当前:
    - `trajectory_assets_status = completed`
    - `render_status = pending`
    - `generation_status = pending`
  - `demo_data/my7/shared/estimated_depth/depth_intrinsics.npz` 已落盘
  - `demo_data/my7/shared/fitted_3D_gaussian/gaussian_params.json` 已落盘
- GPU 观测:
  - 当前为控制图渲染阶段, 观测到:
    - GPU0 `100%`, `10441 / 81920 MiB`
    - GPU1 `0%`, `4 / 81920 MiB`
  - 这与前置单卡阶段的预期一致, 还未进入后续双卡 `torchrun` 生成阶段

### 结论
- `my7` 已经真正开始运行, 不再是“等待中但没启动”的状态.
- 之前的问题是等待脚本自匹配, 不是项目推理脚本没有衔接能力.

### 已完成
- [x] 阶段1: 回读上下文并确认 `my6` 当前真实状态
- [x] 阶段2: 等待或确认 `my6` 结束
- [x] 阶段3: 启动 `my7` 推理命令
- [x] 阶段4: 核对 `my7` 运行状态并回写日志

### 状态
**任务已完成**
- `my7` 已由我直接启动.
- 当前处于 0 号镜头的控制图渲染阶段, 运行状态正常.

## [2026-03-25 13:13:05 UTC] 补充验证: `my7` 已推进到 0 号镜头双卡生成阶段

### 补充动态证据
- 会话日志已显示:
  - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py`
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
- 当前真实进程树包含:
  - 父进程 `single_image_multi_trajectory.py`
  - 中间层 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker
- `demo_data/my7/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 0 号镜头 `render_status = completed`
  - 0 号镜头 `generation_status = pending`

### 结论
- `my7` 已经顺利越过前置单卡阶段, 真正进入双卡生成.
- 当前运行链路正常.

## [2026-03-25 16:40:40 UTC] 新任务启动: 等 `my7` 完成后接手启动 `demo_data/my8`

### 目标
- 确认 `my7` 当前真实进度, 避免误以为已经接近结束.
- 在 `my7` 真正完成后, 按用户提供的参数启动 `demo_data/my8`.
- 这次使用不会自匹配的等待方式, 避免重复出现上一轮自动接力失效的问题.

### 阶段
- [ ] 阶段1: 核对 `my7` 当前状态与 `my8` 输入目录
- [ ] 阶段2: 建立基于真实 PID 的等待接力
- [ ] 阶段3: `my7` 结束后启动 `my8`
- [ ] 阶段4: 核对 `my8` 已进入运行态

### 现象
- 当前 `demo_data/my7/manifest.json` 顶层仍是 `status = running`.
- 已完成镜头:
  - 0, 1, 2, 3
- 当前镜头:
  - 4 号 `zoom_in`
  - `trajectory_assets_status = completed`
  - `render_status = completed`
  - `generation_status = pending`
- 当前真实进程:
  - 父进程 `290817` 为 `inference/single_image_multi_trajectory.py --output_root demo_data/my7`
  - 中间层 `331673` 为 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker 正在运行
- `demo_data/my8` 当前只有输入图 `e.png`, 尚未启动.

### 做出的决定
- 决定: 使用等待真实 PID `290817` 退出的方式做接力.
  - 理由: 这比按命令文本模糊搜索更稳, 不会把等待脚本自己匹配进去.
- 决定: 在启动 `my8` 前先额外检查一次 `my7/manifest.json` 是否为 `completed`.
  - 理由: 这样可以防止“进程异常退出但 manifest 还没完成”的情况被误当成正常结束.

### 当前待办
- [ ] 阶段1: 核对 `my7` 当前状态与 `my8` 输入目录
- [ ] 阶段2: 建立基于真实 PID 的等待接力
- [ ] 阶段3: `my7` 结束后启动 `my8`
- [ ] 阶段4: 核对 `my8` 已进入运行态

### 状态
**目前在阶段1**
- 已完成现场核对.
- 下一步建立基于真实 PID 的等待接力会话.

## [2026-03-25 16:42:30 UTC] 已建立基于真实 PID 的 `my8` 接力等待

### 已执行动作
- 已启动等待会话:
  - 监控 `my7` 主进程 PID `290817`
  - 当该 PID 退出后, 先检查 `demo_data/my7/manifest.json` 顶层状态
  - 仅当状态为 `completed` 时, 才启动 `demo_data/my8`
- 当前等待会话最近一次输出时间:
  - `2026-03-25 16:42:23 UTC`

### 额外观测
- `demo_data/my7/manifest.json` 当前未完成镜头为:
  - 4 `zoom_in`: `trajectory_assets_status = completed`, `render_status = completed`, `generation_status = pending`
  - 5-11 号镜头均尚未开始
- `nvidia-smi` 当前显示:
  - GPU0 `100%`, `75117 / 81920 MiB`
  - GPU1 `100%`, `75117 / 81920 MiB`

### 当前待办
- [x] 阶段1: 核对 `my7` 当前状态与 `my8` 输入目录
- [x] 阶段2: 建立基于真实 PID 的等待接力
- [ ] 阶段3: `my7` 结束后启动 `my8`
- [ ] 阶段4: 核对 `my8` 已进入运行态

### 状态
**目前在阶段2**
- `my7` 正在 4 号镜头双卡生成阶段.
- `my8` 已进入 PID 驱动的自动接力等待.

## [2026-03-25 18:28:00 UTC] 新任务启动: 确认 `pixi` 真实运行环境中的 `PyTorch` / `pytorch3d` 版本

### 目标
- 区分仓库配置声明的版本, 与 `pixi run python` 实际看到的安装版本.
- 避免仓库根目录下本地 `pytorch3d/` 源码目录污染导入结果.

### 当前待办
- [ ] 阶段1: 用 `pixi` 动态检查 `torch` / `pytorch3d` 实际安装状态
- [ ] 阶段2: 核对 `pip show` / `importlib.metadata` 与导入路径
- [ ] 阶段3: 汇总结论并回写日志

### 状态
**目前在阶段1**
- 已回读六文件上下文.
- 下一步进入 `pixi` 环境做动态验证.

## [2026-03-25 18:32:00 UTC] `pixi` 版本核对完成

### 已完成
- [x] 阶段1: 用 `pixi` 动态检查 `torch` / `pytorch3d` 实际安装状态
- [x] 阶段2: 核对 `pip show` / `importlib.metadata` 与导入路径
- [x] 阶段3: 汇总结论并回写日志

### 结论
- `pixi` 默认环境真实版本:
  - `PyTorch 2.3.1`
  - `torchvision 0.18.1`
  - `torchaudio 2.3.1`
  - `pytorch3d 0.7.9`
- `torch.version.cuda = 12.1`
- `torch.cuda.is_available() = True`

### 状态
**任务已完成**
- 已完成静态配置与动态环境的交叉核对.
- 可直接按 `pixi` 环境结论回答用户.

## [2026-03-26 03:05:10 UTC] 新任务启动: 等 `my8` 完成后接手启动 `demo_data/my9`

### 目标
- 确认 `my8` 当前真实运行状态, 避免误把“还在双卡生成”当成“快结束了”.
- 在 `my8` 真正完成后, 按用户提供的参数启动 `demo_data/my9`.
- 继续沿用 PID 驱动 + manifest 二次确认的接力方式, 避免等待脚本自匹配或异常退出误判.

### 阶段
- [ ] 阶段1: 回读上下文并核对 `my8` / `my9` 当前状态
- [ ] 阶段2: 建立基于真实 PID 的 `my9` 接力等待
- [ ] 阶段3: `my8` 完成后启动 `my9`
- [ ] 阶段4: 核对 `my9` 已进入运行态

### 现象
- 当前真实运行中的主进程:
  - `PID 412060`
  - `inference/single_image_multi_trajectory.py --output_root demo_data/my8`
- 当前正在执行的双卡生成:
  - 5 号镜头 `clockwise`
  - 中间层 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker 均在运行
- `demo_data/my8/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 5 号镜头 `trajectory_assets_status = completed`
  - 5 号镜头 `render_status = completed`
  - 5 号镜头 `generation_status = pending`
  - 6-11 号镜头尚未开始
- `demo_data/my9` 当前只有输入图 `f.png`, 尚未启动.

### 做出的决定
- 决定: 监控 `my8` 主 Python 进程 `PID 412060` 的退出, 而不是按命令文本搜索.
  - 理由: 真实 PID 是最不容易误匹配的等待门闩.
- 决定: 只有在 `my8/manifest.json` 顶层状态为 `completed` 时, 才自动启动 `my9`.
  - 理由: 可以拦住“进程异常退出但结果未完成”的情况.

### 当前待办
- [ ] 阶段1: 回读上下文并核对 `my8` / `my9` 当前状态
- [ ] 阶段2: 建立基于真实 PID 的 `my9` 接力等待
- [ ] 阶段3: `my8` 完成后启动 `my9`
- [ ] 阶段4: 核对 `my9` 已进入运行态

### 状态
**目前在阶段1**
- 已完成现场核对.
- 下一步建立 `my8 -> my9` 的 PID 驱动接力等待.

## [2026-03-26 03:06:30 UTC] 已建立基于真实 PID 的 `my9` 接力等待

### 已执行动作
- 已启动等待会话:
  - 监控 `my8` 主进程 PID `412060`
  - 当该 PID 退出后, 先检查 `demo_data/my8/manifest.json` 顶层状态
  - 仅当状态为 `completed` 时, 才启动 `demo_data/my9`
- 当前等待会话最近一次输出时间:
  - `2026-03-26 03:06:20 UTC`

### 额外观测
- `demo_data/my8/manifest.json` 当前未完成镜头为:
  - 5 `clockwise`: `trajectory_assets_status = completed`, `render_status = completed`, `generation_status = pending`
  - 6-11 号镜头尚未开始
- `nvidia-smi` 当前显示:
  - GPU0 `100%`, `75117 / 81920 MiB`
  - GPU1 `100%`, `75117 / 81920 MiB`

### 当前待办
- [x] 阶段1: 回读上下文并核对 `my8` / `my9` 当前状态
- [x] 阶段2: 建立基于真实 PID 的 `my9` 接力等待
- [ ] 阶段3: `my8` 完成后启动 `my9`
- [ ] 阶段4: 核对 `my9` 已进入运行态

### 状态
**目前在阶段2**
- `my8` 正在 5 号镜头双卡生成阶段.
- `my9` 已进入 PID 驱动的自动接力等待.

## [2026-03-26 08:07:57 UTC] `left_up` / `right_up` 注视目标偏移修复完成

### 验证
- 静态证据:
  - `TrajectoryPreset` 已新增 `center_facing_target_offset_scale_cv` 元数据
  - `left_up` 现在带有轻微左向 look-at 偏移
  - `right_up` 现在带有轻微右向 look-at 偏移
  - `generate_blender_camera_trajectory()` 在 `center_facing` 模式下, 会把该偏移叠加到默认中心目标点
- 动态证据:
  - `python3 -m py_compile inference/single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_lib.py`
    - 结果: 通过
  - `timeout 120s pixi run pytest tests/test_single_image_multi_trajectory_lib.py -q`
    - 结果: `13 passed in 0.16s`
  - `timeout 120s pixi run pytest tests/test_single_image_multi_trajectory_smoke.py -q`
    - 结果: `4 passed in 0.75s`
- 新增回归验证:
  - 已新增测试, 通过反推 `center_depth` 平面上的 look-at 交点 X 坐标
  - 验证 `left_up` 的目标点稳定小于 `0`
  - 验证 `right_up` 的目标点稳定大于 `0`
  - 同时验证普通 `left` / `right` 仍保持中心注视

### 结论
- 主假设成立.
- 问题确实不是平移轨迹本身, 而是 `center_facing` 目标点一直被统一锁在画面中心.
- 现在 `left_up` 会轻微看向左侧, `right_up` 会轻微看向右侧, 不再始终盯死中心.

### 已完成
- [x] 阶段1: 定位轨迹定义与 look-at 目标生成逻辑
- [x] 阶段2: 修改 `left_up` / `right_up` 的目标点策略
- [x] 阶段3: 补充或更新回归测试
- [x] 阶段4: 运行聚焦验证并回写日志

### 状态
**任务已完成**
- `left_up` / `right_up` 的注视目标偏移已修复并验证通过.


## [2026-03-26 07:59:42 UTC] 新任务启动: 调整 `left_up` / `right_up` 镜头的注视目标偏移

### 目标
- 修改 `left_up` / `right_up` 两个轨迹的 look-at 目标点, 让它们不再始终看向画面中心.
- 保持位移趋势仍然是“左上”与“右上”, 但镜头注视方向要分别略微偏向左侧与右侧.
- 增加回归验证, 防止这两个轨迹以后再次退回中心注视.

### 阶段
- [ ] 阶段1: 定位轨迹定义与 look-at 目标生成逻辑
- [ ] 阶段2: 修改 `left_up` / `right_up` 的目标点策略
- [ ] 阶段3: 补充或更新回归测试
- [ ] 阶段4: 运行聚焦验证并回写日志

### 现象
- 用户当前要求:
  - `left_up` 时镜头目标点要向水平左侧偏移
  - `right_up` 时镜头目标点要向水平右侧偏移
- 当前表现被用户观察为:
  - 虽然相机运动是左上 / 右上, 但镜头仍然始终看向画面中心

### 当前假设
- 主假设: 当前轨迹生成逻辑里, `left_up` / `right_up` 仍复用统一的 `center_facing` 注视目标, 没有给这两个斜向运动单独施加水平 look-at 偏移.
- 备选解释: 也可能是轨迹位置本身已经带了斜向位移, 但最终生成相机朝向时又被统一重新对准中心.
- 推翻主假设所需证据:
  - 如果代码里已经存在 `left_up` / `right_up` 的专属 look-at 目标配置, 那问题就不在 preset 数据, 而在后续朝向求解阶段.

### 状态
**目前在阶段1**
- 已完成六文件回读.
- 正在定位 `left_up` / `right_up` 对应的轨迹与相机朝向代码路径.

## [2026-03-26 14:44:50 UTC] 新任务启动: 等 `my9` 完成后接手启动 `demo_data/my10`

### 目标
- 确认 `my9` 当前真实运行状态, 避免重复启动或错误判断已完成.
- 在 `my9` 真正完成后, 按用户提供的更新后 `negative_prompt` 启动 `demo_data/my10`.
- 继续沿用真实 PID + manifest 完成态的接力方式, 保持接力稳定.

### 阶段
- [ ] 阶段1: 核对 `my9` / `my10` 当前状态
- [ ] 阶段2: 建立基于真实 PID 的 `my10` 接力等待
- [ ] 阶段3: `my9` 完成后启动 `my10`
- [ ] 阶段4: 核对 `my10` 已进入运行态

### 现象
- 当前真实运行中的主进程:
  - `PID 441051`
  - `inference/single_image_multi_trajectory.py --output_root demo_data/my9`
- 当前正在执行的双卡生成:
  - 7 号镜头 `counterclockwise_1.5`
  - 中间层 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker 均在运行
- `demo_data/my9/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 7 号镜头 `trajectory_assets_status = completed`
  - 7 号镜头 `render_status = completed`
  - 7 号镜头 `generation_status = pending`
  - 8-11 号镜头尚未开始
- `demo_data/my10` 当前只有输入图 `g.png`, 尚未启动.
- 用户为 `my10` 提供的新 `negative_prompt` 额外加入了:
  - `高反光`
  - `高光点`
  - `脏`

### 做出的决定
- 决定: 监控 `my9` 主 Python 进程 `PID 441051` 的退出.
  - 理由: 真实 PID 作为门闩最稳, 不会被等待脚本自己污染.
- 决定: 只有在 `my9/manifest.json` 顶层状态为 `completed` 时, 才自动启动 `my10`.
  - 理由: 可以拦住“进程退出但批处理未完成”的异常场景.
- 决定: `my10` 启动命令严格使用用户刚给的新版 `negative_prompt`.
  - 理由: 这次用户明确追加了新的负面约束, 不能沿用 `my9` 的旧参数.

### 当前待办
- [ ] 阶段1: 核对 `my9` / `my10` 当前状态
- [ ] 阶段2: 建立基于真实 PID 的 `my10` 接力等待
- [ ] 阶段3: `my9` 完成后启动 `my10`
- [ ] 阶段4: 核对 `my10` 已进入运行态

### 状态
**目前在阶段1**
- 已完成现场核对.
- 下一步建立 `my9 -> my10` 的 PID 驱动接力等待.

## [2026-03-26 14:46:09 UTC] 已建立基于真实 PID 的 `my10` 接力等待

### 已执行动作
- 已启动等待会话:
  - 监控 `my9` 主进程 PID `441051`
  - 当该 PID 退出后, 先检查 `demo_data/my9/manifest.json` 顶层状态
  - 仅当状态为 `completed` 时, 才启动 `demo_data/my10`
- 当前等待会话最近一次输出时间:
  - `2026-03-26 14:46:09 UTC`

### 额外观测
- `demo_data/my9/manifest.json` 当前未完成镜头为:
  - 7 `counterclockwise_1.5`: `trajectory_assets_status = completed`, `render_status = completed`, `generation_status = pending`
  - 8-11 号镜头尚未开始
- `my10` 启动时将使用用户刚给的新版 `negative_prompt`, 其中新增:
  - `高反光`
  - `高光点`
  - `脏`

### 当前待办
- [x] 阶段1: 核对 `my9` / `my10` 当前状态
- [x] 阶段2: 建立基于真实 PID 的 `my10` 接力等待
- [ ] 阶段3: `my9` 完成后启动 `my10`
- [ ] 阶段4: 核对 `my10` 已进入运行态

### 状态
**目前在阶段2**
- `my9` 正在 7 号镜头双卡生成阶段.
- `my10` 已进入 PID 驱动的自动接力等待.

## [2026-03-27 01:48:20 UTC] 新任务启动: 等当前批处理结束后接手新的 `my4` 命令

### 目标
- 核对当前批处理链路是否已从 `my9` 自动推进到 `my10`.
- 判断用户新给的 `my4` 命令是否具备可执行前提, 尤其是输入路径与输出目录是否存在.
- 在前提明确后, 决定是挂新接力还是等待用户修正路径.

### 阶段
- [ ] 阶段1: 回读上下文并核对 `my9` / `my10` / `my4` 当前状态
- [ ] 阶段2: 判断新命令是否具备可执行前提
- [ ] 阶段3: 若可执行则建立接力, 若不可执行则向用户请求最小澄清

### 现象
- `my9` 已经结束, 且上一轮接力已经把 `demo_data/my10` 自动启动.
- 当前真实运行中的主进程:
  - `PID 475666`
  - `inference/single_image_multi_trajectory.py --output_root demo_data/my10`
- 当前正在执行的双卡生成:
  - 9 号镜头 `right_up`
  - 中间层 `torchrun --nproc-per-node=2`
  - 两个 `versecrafter_inference.py` worker 均在运行
- `demo_data/my10/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 9 号镜头 `trajectory_assets_status = completed`
  - 9 号镜头 `render_status = completed`
  - 9 号镜头 `generation_status = pending`
  - 10-11 号镜头尚未开始
- 用户这次给的输入路径:
  - `demo_data/my4/a.png`
- 但当前工作区里:
  - 不存在 `demo_data/my4`
  - 也不存在任何 `a.png`

### 做出的决定
- 决定: 先不为这条 `my4` 命令挂接力.
  - 理由: 当前输入路径缺失, 直接挂接力只会在批处理结束后失败.
- 决定: 需要向用户确认正确输入路径.
  - 理由: 这是执行前提缺失, 不能靠猜测替代.

### 当前待办
- [x] 阶段1: 回读上下文并核对 `my9` / `my10` / `my4` 当前状态
- [x] 阶段2: 判断新命令是否具备可执行前提
- [ ] 阶段3: 若可执行则建立接力, 若不可执行则向用户请求最小澄清

### 状态
**目前在阶段3**
- 已确认 `my10` 正在运行.
- 已确认 `demo_data/my4/a.png` 缺失, 当前需要用户确认正确输入路径.

## [2026-03-27 01:57:26 UTC] `demo_data/my4/a.png` 已出现, 准备建立 `my10 -> my4` 接力

### 现象更新
- 当前 `demo_data/my4/a.png` 已存在.
- `demo_data/my4` 目录当前只有这一张输入图, 尚未产生 `manifest.json` 或中间产物.
- 当前真实运行中的主进程:
  - `PID 475666`
  - `inference/single_image_multi_trajectory.py --output_root demo_data/my10`
- `demo_data/my10/manifest.json` 当前显示:
  - 顶层 `status = running`
  - 10 号镜头 `left_down` 正在双卡生成
  - 11 号镜头尚未开始

### 结论更新
- 上一条“输入路径缺失”的阻塞已解除.
- 现在可以为用户新的 `demo_data/my4` 命令建立接力等待.

### 当前待办
- [x] 阶段1: 回读上下文并核对 `my9` / `my10` / `my4` 当前状态
- [x] 阶段2: 判断新命令是否具备可执行前提
- [ ] 阶段3: 若可执行则建立接力, 若不可执行则向用户请求最小澄清

### 状态
**目前在阶段3**
- `my10` 正在运行.
- `demo_data/my4/a.png` 已就绪, 下一步建立 `my10 -> my4` 的 PID 驱动接力等待.

## [2026-03-27 01:59:52 UTC] 接力监控继续中: 等待 `my10` 完成后启动 `my4`

### 现象
- 已回读最新的 `task_plan.md`、`notes.md`、`WORKLOG.md`、`LATER_PLANS.md`、`EPIPHANY_LOG.md`、`ERRORFIX.md`.
- 当前接力仍由等待会话 `97910` 负责.
- 最新动态轮询输出显示:
  - `[wait 2026-03-27 01:59:52 UTC] demo_data/my10(pid=475666) 仍在运行, 继续等待...`
- 目前还没有看到 `my10` 退出后的 `manifest` 二次确认结果.

### 当前假设
- 主假设: `my10` 仍处于正常运行中的后半段镜头生成阶段, 因此接力尚未放行.
- 备选解释: `my10` 可能已经接近结束, 但当前轮询窗口还没有刷新到下一次状态切换.

### 验证计划
- 继续轮询等待会话 `97910`.
- 一旦出现 `start ... demo_data/my10 已完成, 开始启动 demo_data/my4`, 立刻核对:
  - 真实进程树里是否已有 `demo_data/my4`
  - `demo_data/my4/manifest.json` 是否创建
  - `demo_data/my4` 是否开始落盘共享产物
- 如果 `my10` 退出但 `manifest.status != completed`, 立即停止接力判断并按异常场景汇报.

### 状态
**目前在接力监控阶段**
- `my10` 仍在运行.
- 下一步继续等待 `97910` 给出放行或异常结果.

## [2026-03-27 02:25:53 UTC] `my10 -> my4` 接力仍在等待, 已确认自动启动门闩正常挂起

### 现象
- 等待会话 `97910` 持续输出:
  - `[wait 2026-03-27 02:25:53 UTC] demo_data/my10(pid=475666) 仍在运行, 继续等待...`
- `demo_data/my10/manifest.json` 的当前关键状态为:
  - 顶层 `status = running`
  - `10 left_down`: `trajectory_assets_status = completed`, `render_status = completed`, `generation_status = pending`
  - `11 right_down`: `trajectory_assets_status = pending`, `render_status = pending`, `generation_status = pending`
- 真实进程树仍存在:
  - `single_image_multi_trajectory.py` 主进程 `475666`
  - `torchrun --nproc-per-node=2` 子进程 `611884`
  - 两个 `versecrafter_inference.py` worker `611886` / `611887`
- 动态资源证据:
  - `nvidia-smi` 显示两张卡都处于 `100%` 利用率
  - 显存均为 `75117 / 81920 MiB`
- 10 号镜头目录下已存在:
  - `custom_3D_gaussian_trajectory.json`
  - `custom_camera_trajectory.npz`
  - `rendering_4D_maps/*.mp4`
- 但 `demo_data/my10/10/generated_videos` 目前仍未见成品文件落盘.

### 当前假设
- 主假设: `my10` 当前仍在 10 号镜头的最终生成阶段, 只是耗时较长, 尚未完成到可切换 11 号镜头或结束批处理的时点.
- 备选解释: 也可能在最终视频落盘前存在较长尾声阶段, 导致 `generated_videos` 暂时为空, 但并未影响计算继续进行.

### 已验证结论
- 目前没有证据表明 `my10` 已完成.
- 目前也没有证据表明它已经异常卡死.
- `my4` 的自动启动门闩已经挂好, 但尚未被放行.

### 状态
**目前仍在接力等待阶段**
- 继续等待 `my10` 退出且 `manifest.status = completed`.
- 满足条件后会自动启动 `demo_data/my4`.
