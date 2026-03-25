# 笔记

## [2026-03-22 12:17:30 UTC] 四文件摘要（用于续档后的持续学习）

### 任务目标（来自历史 `task_plan` / `WORKLOG`）
- 近期主要工作集中在 `single_image_multi_trajectory.py` 的多轨迹批处理、双卡预检、preset 扩展与 prompt 对齐.
- 最近一次与本任务直接相关的改动, 是新增轨迹变体并为每个 preset 增加 `camera_motion_prompt`.

### 关键决定（来自历史 `task_plan`）
- 轨迹的文本描述不再散落在命令构建处, 而是沉到 `TrajectoryPreset` 元数据里统一维护.
- 双卡是否生效, 需要区分当前运行阶段; Step 1/2/3/5 本来就是单卡, 只有 Step 6 才会走 `torchrun`.

### 关键发现（来自历史 `notes` / `ERRORFIX`）
- `clockwise_1.5` 已经存在, 而且 prompt 描述已经显式写成“clockwise around the scene with a wider radius”.
- manifest 轨迹键是字符串, 测试比较顺序时必须先转成整数, 否则会误判 `10` / `11`.

### 可复用点候选
- 轨迹几何和镜头文案必须一起维护, 否则生成 prompt 会和实际运动相互打架.
- 对批处理镜头 preset 的改动, 至少要跑 `py_compile` 与相关 `pytest` smoke / lib 测试.

### 是否需要固化到 `AGENTS.md` / docs / specs
- 暂无新的长期规则需要补充.
- 本次续档属于上下文维护, 不需要额外产出新 skill.

## [2026-03-22 12:35:40 UTC] 7 号镜头逆时针修改结论

### 现象
- 索引 `7` 原本叫 `clockwise_1.5`.
- 它过去只是在 `clockwise` 的基础上把 orbit 半径放大到 `1.5` 倍, 方向并没有变.

### 假设
- 如果用户要求“7 号镜头改为逆时针”, 最稳的实现不是硬编码单独分支.
- 更合适的办法是把 orbit 方向也收进 `TrajectoryPreset` 元数据.

### 验证与结论
- 静态证据:
  - `TrajectoryPreset` 新增 `orbit_direction`
  - orbit 生成改为统一走 `_generate_orbit_offsets_cv(...)`
  - 索引 `7` 改名为 `counterclockwise_1.5`
- 动态证据:
  - `clockwise` 第 1 个非零采样点 `x,z = (-0.032950487, -0.05303301)`
  - `counterclockwise_1.5` 第 1 个非零采样点 `x,z = (-0.049425732, 0.079549514)`
  - 比值分别为 `1.5` 与 `-1.5`
- 已验证结论:
  - 7 号镜头现在确实变成逆时针.
  - 同时仍保持更大半径这一语义.

## [2026-03-22 12:18:55 UTC] `demo_data/my4` 第 8 号镜头单卡现象的动态证据

### 现象
- 用户反馈: “已经跑到 8 号镜头了, 还是只显示 1 个 GPU 工作”.
- 这类现象不能直接等价成“代码没有启用双卡”, 因为前置步骤本来就大量是单卡.

### 动态证据
- 当前父进程:
  - `PID 84075`
  - `inference/single_image_multi_trajectory.py`
- 当前 8 号镜头 Step 6 子进程:
  - `PID 122250`
  - `inference/versecrafter_inference.py`
- 直接读取 `/proc/<pid>/cmdline` 后, 父进程实参只到:
  - `--moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/`
- 当前子进程实参明确是单卡配置:
  - `--num_inference_steps 30`
  - `--ulysses_degree 1`
  - `--ring_degree 1`
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`
- 当前没有任何 `torchrun` 进程参与 8 号镜头的 Step 6.

### manifest 证据
- `demo_data/my4/manifest.json` 当前 `settings` 记录为:
  - `num_inference_steps = 30`
  - `ulysses_degree = 1`
  - `ring_degree = 1`
  - `nproc_per_node = 1`
  - `gpu_memory_mode = model_cpu_offload_and_qfloat8`
- 这些值与用户口头贴出的双卡命令不一致.

### 当前判断
- 已验证结论:
  - 现在这轮跑到 8 号镜头时, 真正执行中的 Step 6 是单卡进程, 不是双卡 `torchrun`.
  - 所以 `nvidia-smi` 只显示 1 张 GPU 工作, 与当前真实运行参数一致.
- 仍未完全确认的部分:
  - 为什么用户以为自己启动的是双卡命令.
- 候选假设:
  - 实际执行命令在 shell 中被换行或截断, 导致后半段双卡参数没有进入 `argv`.
  - 或者用户观察到的是更早一轮单卡进程.

## [2026-03-22 12:36:50 UTC] `demo_data/my4` 双卡重启后的动态证据

### 启动前验证
- `torch.cuda.device_count() = 2`
- `xfuser` / `yunchang` 可正常导入
- `--dry_run` 输出中, 8-11 号镜头的 Step 6 命令都已明确变成:
  - `torchrun --nproc-per-node=2 ... --ulysses_degree 2 --ring_degree 1`

### 启动后证据
- 当前父进程:
  - `pixi run python inference/single_image_multi_trajectory.py ... --num_inference_steps 60 --gpu_memory_mode model_cpu_offload --ulysses_degree 2 --ring_degree 1 --nproc_per_node 2 --preset_indices 8 9 10 11`
- 当前 Step 6 中间层:
  - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py ...`
- 当前 worker:
  - 两个 `python -u inference/versecrafter_inference.py ...`
- 运行日志明确打印:
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`

### GPU 观测
- `nvidia-smi --query-gpu=...` 当前返回:
  - GPU0: `45%`, `6959 / 81920 MiB`
  - GPU1: `44%`, `6959 / 81920 MiB`

### 当前结论
- 双卡已经真实生效.
- 这次不是“只有一张卡看起来忙”, 而是两张 A800 都已经进入当前 8 号镜头的生成阶段.

## [2026-03-24 17:44:33 UTC] 单图多轨迹离线复用缓存排查

### 现象
- 用户希望在 `pixi run python inference/single_image_multi_trajectory.py ...` 这条链路里, 快速跳过网络检查, 直接使用本地缓存模型.
- 用户当前命令已显式传入:
  - `--transformer_path model/VerseCrafter`
  - `--moge_pretrained /root/.cache/huggingface/hub/.../model.pt`
  - `--camera_only`

### 静态证据
- `single_image_multi_trajectory.py` 的 Step 1 只是在有需要时调用 `inference/moge-v2_infer.py`, 并把 `--moge_pretrained` 原样透传进去.
- 同文件默认 `resume=True`, 且若 `depth_intrinsics.npz` 已存在就会直接复用, 不会再跑 MoGe.
- `camera_only=True` 时会跳过真正的分割模型与 Gaussian 拟合, 只写空 mask / 空 Gaussian 占位结果.
- `versecrafter_inference.py` 把基座模型路径写死为本地目录 `model/Wan2.1-T2V-14B`, 同时优先从本地目录 `model/VerseCrafter` 加载 transformer.
- MoGe 的 `from_pretrained` 实现里, 如果传入路径 `Path(...).exists()` 为真, 会直接把它当本地 checkpoint, 只有不存在时才调用 `hf_hub_download`.

### 动态证据
- 当前文件系统里以下路径都真实存在:
  - `model/VerseCrafter`
  - `model/Wan2.1-T2V-14B`
  - `/root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`
- 在 `HF_HUB_OFFLINE=1` 下执行最小验证:
  - `AutoTokenizer.from_pretrained('model/Wan2.1-T2V-14B/google/umt5-xxl')` 成功
  - `import_model_class_by_version('v2').from_pretrained('<本地 model.pt>')` 成功
- 当前 `demo_data/my5` 已存在:
  - `shared/estimated_depth/depth_intrinsics.npz`
  - `shared/fitted_3D_gaussian/gaussian_params.json`
  因而继续用同一个 `--output_root demo_data/my5` 重跑时, Step 1~3 可直接走 resume 复用.

### 已验证结论
- 对你当前这条命令, 最快的离线做法不是改代码, 而是:
  - 保持所有模型参数都指向本地路径
  - 在命令前加 `HF_HUB_OFFLINE=1`
  - 继续复用同一个 `--output_root demo_data/my5`, 让默认 `resume` 跳过已完成的共享步骤
- 如果去掉 `--moge_pretrained`, `moge-v2_infer.py` 会退回默认 repo id (`Ruicheng/moge-2-vitl-normal`), 这时离线模式下会因为本地无缓存或无法联网而失败.
