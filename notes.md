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

## [2026-03-25 13:12:09 UTC] `my7` 启动排查与修正

### 现象
- 用户提醒 `my6` 已经完成, 但 `my7` 目录仍只有 `d.png`, 没有 `manifest.json`.
- 系统中没有真实的 `my6` 或 `my7` 推理进程, 只剩上一轮挂起的等待脚本.

### 假设
- 主假设: 等待脚本中的 `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 把等待脚本自身也匹配进去了, 导致永远不放行.
- 备选解释: 等待脚本只是还没轮询到下一次检查.

### 验证
- 静态证据:
  - `demo_data/my6/manifest.json` 顶层 `status = completed`
  - 8-11 号镜头全部 `completed`
- 动态证据:
  - `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 当前只返回等待脚本本身
  - `ps -ef` 中没有真实的 `demo_data/my6` 推理进程
  - `demo_data/my7/manifest.json` 当时不存在

### 已验证结论
- 上一轮自动接力失败的直接原因, 是 `pgrep` 模式自匹配, 不是 `single_image_multi_trajectory.py` 没有接上.
- 停掉等待脚本后, 直接执行用户提供的 `my7` 命令即可正常启动.

### 启动后证据
- `demo_data/my7/manifest.json` 已创建, 顶层 `status = running`
- 0 号镜头:
  - `trajectory_assets_status = completed`
  - `render_status = pending`
  - `generation_status = pending`
- 会话日志显示:
  - `moge-v2_infer.py` 已完成深度估计
  - 当前正在执行 `rendering_4D_control_maps.py`
  - 日志已进入 `Rendering(mesh-batch) background`
- 当前 GPU 观测:
  - GPU0 `100%`, `10441 / 81920 MiB`
  - GPU1 `0%`, `4 / 81920 MiB`
- 解释:
  - 当前还在前置控制图渲染阶段, 单卡占用是正常现象
  - 后续进入 Step 6 时, 才会看到双卡 `torchrun`

## [2026-03-25 18:31:00 UTC] `pixi` 真实运行环境版本核对

### 现象
- 根仓库 `pixi.toml` 静态声明:
  - `pytorch = 2.3.1.*`
  - `torchvision = 0.18.1.*`
  - `torchaudio = 2.3.1.*`
  - `pytorch-cuda = 12.1.*`
- 但普通 `python3` 环境里此前看到的是:
  - `torch 2.6.0+cu126`
  - `import pytorch3d` 落到工作区本地 `pytorch3d/` 源码目录, 不是已安装发行版

### 假设
- 主假设: 项目预期使用的 `pixi` 环境中, 实际安装版本与 `pixi.toml` 一致.
- 备选解释: 也可能在 `bootstrap` 或后续 `pip install` 过程中发生了版本漂移.

### 验证
- 动态证据1: `pixi run --manifest-path /workspace/VerseCrafter/pixi.toml python -m pip show torch torchvision torchaudio pytorch3d`
  - `torch 2.3.1`
  - `torchvision 0.18.1`
  - `torchaudio 2.3.1`
  - `pytorch3d 0.7.9`
  - site-packages 均位于 `/workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages`
- 动态证据2: 在 `workdir=/workspace` 下执行 `pixi run ... python`
  - `sys.executable = /workspace/VerseCrafter/.pixi/envs/default/bin/python`
  - `torch.__version__ = 2.3.1`
  - `torch.version.cuda = 12.1`
  - `torch.cuda.is_available() = True`

## [2026-03-29 17:41:11 UTC] `nt1 -> nt2` 接力监督启动记录

### 现象
- 用户要求先监督当前 `demo_data/nt1` 的生成进度.
- 等 `nt1` 完成后, 立刻执行新的 `demo_data/nt2` 批处理命令.

### 当前假设
- 主假设: 当前正在运行的 `nt1` 就是用户要我接力的那一轮, 并且还没有完成.
- 备选解释: 也可能存在旧的残留等待脚本或孤儿子进程, 导致看起来像“还在跑”.

### 已做的最小验证
- 动态证据:
  - `ps -eo pid,ppid,etime,stat,cmd | rg "single_image_multi_trajectory|nt1|nt2|inference"`
  - 返回真实主进程:
    - `173232 pixi run python inference/single_image_multi_trajectory.py ... --output_root demo_data/nt1`
    - `173293 /workspace/VerseCrafter/.pixi/envs/default/bin/python inference/single_image_multi_trajectory.py ... --output_root demo_data/nt1`
  - 当前 Step 6 中间层:
    - `242526 torchrun --nproc-per-node=2 inference/versecrafter_inference.py ... --save_path demo_data/nt1/9/generated_videos`
  - 当前双 worker:
    - `242528 ... inference/versecrafter_inference.py ... demo_data/nt1/9/generated_videos`
    - `242529 ... inference/versecrafter_inference.py ... demo_data/nt1/9/generated_videos`

### 当前结论
- 已验证结论:
  - 当前 `nt1` 确实还在运行, 不是空等.
  - 当前已经进入 9 号镜头的双卡生成阶段.
- 仍待继续确认:
  - `nt1` 何时完成整个批处理.
  - 完成后 `nt2` 是否能无缝接上并顺利进入共享步骤或生成步骤.

## [2026-03-29 17:50:34 UTC] `nt1` 监督过程中的额外动态证据

### 现象
- `demo_data/nt1/manifest.json` 顶层 `updated_at` 停在 `2026-03-29T17:36:34.104398+00:00`.
- 但同一时间段内, `242528` / `242529` 两个 worker 一直维持:
  - `%CPU ≈ 101`
  - GPU 利用率 `100%`
  - 显存 `75117 MiB`

### 当前假设
- 主假设: Step 6 进行中时, `manifest` 不会持续回写心跳.
- 备选解释: 也可能是回写逻辑只在镜头完成后才统一更新.

### 额外验证
- `demo_data/nt1/7/generated_videos/generated_video_0.mp4`
  - 落盘时间: `17:00:28`
  - 对应控制图完成时间: `16:26:38`
  - Step 6 约耗时 `33-34` 分钟
- `demo_data/nt1/8/generated_videos/generated_video_0.mp4`
  - 落盘时间: `17:35:20`
  - 对应控制图完成时间: `17:01:40`
  - Step 6 约耗时 `33-34` 分钟
- `demo_data/nt1/9/generated_videos/` 当前仍为空, 与“9 号镜头还在生成”的现场观察一致.

### 当前结论
- 已验证结论:
  - 这条链路里, `manifest` 不是运行中心跳源.
  - 监督 `nt1` 时应优先看:
    - 主进程是否仍存活
    - `torchrun` / worker 是否仍在
    - GPU 占用是否持续
    - `generated_videos` 最终产物是否出现
- 推测:
  - 如果 9 号镜头维持与 7、8 号相近耗时, 它更可能在 `18:10` 左右完成, 而不是已经卡住.

## [2026-03-29 17:56:32 UTC] 后台门闩挂载验证

### 现象
- 继续在当前对话里同步等待 `nt1 -> nt2` 接力, 预计还需超过 1 小时.
- 需要把监督逻辑脱离当前会话, 否则对话结束后无法继续自动接力.

### 主假设
- 主假设: 只用普通 `nohup ... &` 还不够稳, 进程可能仍受当前命令会话生命周期影响.
- 备选解释: 也可能是后台脚本本身有语法或运行期错误.

### 验证
- 静态证据:
  - 新建 `demo_data/nt1_to_nt2_handoff.sh`
  - `bash -n demo_data/nt1_to_nt2_handoff.sh` 通过
- 动态证据1:
  - 普通 `nohup` 首次启动后, `runner.out` 只有:
    - `handoff-script-start nt1_pid=173293`
  - `pgrep -af 'nt1_to_nt2_handoff.sh|nt2_handoff'` 无存活进程
- 动态证据2:
  - `timeout 8s bash -x demo_data/nt1_to_nt2_handoff.sh 173293`
  - 已确认脚本逻辑本身正常, 能进入:
    - `kill -0 173293`
    - `print_nt1_summary`
    - `nvidia-smi`
    - `sleep 30`
- 动态证据3:
  - 改为 `setsid nohup ... </dev/null >/... 2>&1 &` 后, 新 PID `252616`
  - `ps -p 252616 -o pid,ppid,pgid,sid,etime,stat,cmd`
    - `PPID = 1`
    - `PGID = SID = 252616`
  - `runner.out` 已连续写入:
    - `17:55:07 nt1-alive`
    - `17:55:37 nt1-alive`

### 当前结论
- 已验证结论:
  - 脚本逻辑本身没问题.
  - 在当前工具环境里, 想让后台监督真正脱离会话, 需要使用:
    - `setsid`
    - `nohup`
    - `</dev/null`
  - 现在这条后台门闩已经独立存活, 后续会继续等待 `nt1` 并接力启动 `nt2`.

## [2026-03-30 00:56:52 UTC] `nt2 -> nt3` 接力监督启动记录

### 现象
- 上一轮后台门闩已经把 `nt1` 接到了 `nt2`.
- 当前真实运行中的批处理不再是 `nt1`, 而是 `demo_data/nt2`.
- 用户现在要求继续监督当前生成程序, 并在其完成后自动启动 `demo_data/nt3`.

### 已做的最小验证
- 动态证据:
  - `demo_data/nt1/manifest.json` 顶层 `status = completed`
  - 当前活跃主进程:
    - `276596 /workspace/VerseCrafter/.pixi/envs/default/bin/python inference/single_image_multi_trajectory.py ... --output_root demo_data/nt2`
  - 当前 Step 6 中间层:
    - `334719 torchrun --nproc-per-node=2 ... --save_path demo_data/nt2/9/generated_videos`
  - 当前双 worker:
    - `334721 ... demo_data/nt2/9/generated_videos`
    - `334722 ... demo_data/nt2/9/generated_videos`
- `demo_data/nt2/manifest.json` 当前摘要:
  - `status = running`
  - `generation_completed = 0-8`
  - `inflight = 9`
  - `pending = 10, 11`
- `demo_data/nt3` 当前只有:
  - `demo_data/nt3/c.png`
  - 尚无 `manifest.json`

### 处置
- 没有去热修改仍在运行的 `demo_data/nt1_to_nt2_handoff.sh`.
- 新建独立脚本:
  - `demo_data/nt2_to_nt3_handoff.sh`
- 挂载方式继续采用上一轮已验证可靠的:
  - `setsid`
  - `nohup`
  - `</dev/null`

### 动态验证
- 后台门闩 PID:
  - `340573`
- `ps -p 340573 -o pid,ppid,pgid,sid,etime,stat,cmd`
  - `PPID = 1`
  - `PGID = SID = 340573`
- `demo_data/nt3_handoff_runner.out` 已连续写入:
  - `00:56:12 nt2-alive`
  - `00:56:42 nt2-alive`

### 当前结论
- 已验证结论:
  - 当前真正需要监督的是 `nt2`, 不是旧的 `nt1`.
  - 新的 `nt2 -> nt3` 门闩已经独立存活.
  - 后续它会在 `nt2` 完成后自动启动用户提供的 `nt3` 命令.
  - `pytorch3d.__file__ = /workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages/pytorch3d/__init__.py`
  - `pytorch3d.__version__ = 0.7.9`
- 补充动态证据3: 在仓库根目录直接用系统 `python3`
  - `import pytorch3d` 命中 `/workspace/VerseCrafter/pytorch3d`
  - `__file__ = None`
  - `__version__` 不存在
  - `importlib.metadata.version('pytorch3d')` 也拿不到发行版元数据

### 已验证结论
- 项目当前 `pixi` 默认环境里的真实版本是:
  - `PyTorch 2.3.1`
  - `torchvision 0.18.1`
  - `torchaudio 2.3.1`
  - `pytorch3d 0.7.9`
- `pytorch3d` 在 `pixi` 环境里已经正确装入 site-packages.
- 之前看到的 `torch 2.6.0+cu126` 是系统/外部 Python 环境, 不是这个项目的 `pixi` 环境.

## [2026-03-26 08:07:57 UTC] `left_up` / `right_up` 注视目标偏移修复

### 现象
- 用户观察到:
  - `left_up` / `right_up` 的机位位移方向是对的
  - 但镜头注视点仍然始终看向画面中心
- 用户期望:
  - `left_up` 要略微看向左侧
  - `right_up` 要略微看向右侧
  - 偏移不要太大, 但要有明确方向感

### 假设
- 主假设: 问题不在 diagonal 轨迹位移本身, 而在 `center_facing` 模式把所有 preset 的目标点统一锁定为同一个中心点.
- 备选解释: 也可能 preset 已经带有专属注视目标, 但后续 `make_blender_camera_to_world()` 之前又被统一改回中心.

### 验证
- 静态证据:
  - `generate_blender_camera_trajectory()` 中原先统一使用:
    - `target_blender = BLENDER_FORWARD_TARGET_UNIT * center_depth`
  - 循环内 `camera_rotation == "center_facing"` 时直接使用这个固定中心点
  - `left_up` / `right_up` 之前只有 `linear_direction_cv`, 没有任何 look-at 偏移元数据
- 修改策略:
  - 为 `TrajectoryPreset` 增加 `center_facing_target_offset_scale_cv`
  - 仅给:
    - `left_up = (-0.35, 0.0, 0.0)`
    - `right_up = (0.35, 0.0, 0.0)`
  - 实际偏移量按:
    - `movement_distance * translation_reference_depth * scale_vector`
  - 再统一通过 `cv_vector_to_blender()` 转到 Blender 坐标
- 动态证据:
  - 新增测试通过反推 `y = center_depth` 平面上的视线交点
  - 验证:
    - `left_up` 的推导目标点 `x < 0`
    - `right_up` 的推导目标点 `x > 0`
    - `left` / `right` 仍保持 `x = 0`

### 已验证结论
- 主假设成立.
- 需要分开建模的其实是两件事:
  - 相机“走向哪里”
  - 相机“看向哪里”
- 这次修复后:
  - diagonal up 的位移语义保持不变
  - 但 look-at 目标点不再被迫锁死到中心
- 额外收获:
  - 原有两个测试本身已经与当前代码漂移:
    - orbit 变体测试忽略了 `orbit_direction`
    - `left_down` / `right_down` 仍按旧的 `0.3` 垂直比例断言
  - 已一并修正为匹配当前真实元数据语义

## [2026-03-29 15:28:46 UTC] 六文件摘要(用于决定如何沉淀知识)

- 任务目标(task_plan.md):
  - 近期上下文主要围绕 `single_image_multi_trajectory.py` 的多轨迹批处理, 双卡验证, 自动接力, 离线运行, 轨迹语义修复, 以及完成后自动关机.
- 关键决定(task_plan.md):
  - 多卡是否真的生效, 要用真实进程 / `torchrun` / `manifest` 三者交叉确认.
  - 自动接力和自动关机都不能再依赖命令行模糊匹配, 要改成 PID 驱动并结合 `manifest` 完成态.
  - 当前 `task_plan.md` 已超过 1000 行, 需要在本轮持续学习后续档.
- 关键发现(notes.md):
  - `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 会把等待脚本自己匹配进去, 导致“目标已结束但永远不放行”.
  - 在仓库根目录直接用系统 `python3` 检查 `pytorch3d` 时, 顶层源码目录会伪装成可导入模块, 容易误判安装状态.
  - `left_up` / `right_up` 的回归说明, 轨迹 preset 需要把“位移语义”和“注视语义”分开建模.
- 实际变更(WORKLOG.md):
  - 已完成对多卡排查, 离线缓存复用, 自动接力失败原因, `pixi` 真实版本核对, 注视目标偏移修复, 异常中断清理, 以及自动关机门闩的落盘记录.
- 暂缓事项 / 后续方向(LATER_PLANS.md):
  - 仍值得后续补强的方向有两个:
    - 在批处理入口显式打印并落盘“最终生效参数”.
    - 在父进程异常退出时回收 Step 6 worker, 并把 `manifest` 写成明确的中止状态.
- 错误与根因(ERRORFIX.md):
  - “8 号镜头只见 1 张 GPU 工作”不是多卡逻辑失效, 而是那一轮实际就跑成了单卡.
  - “`my6` 完成但 `my7` 没接上”不是推理链路故障, 而是 `pgrep -af` 自匹配导致等待脚本永远不放行.
- 重大风险 / 灾难点 / 重要规律(EPIPHANY_LOG.md):
  - 长链路批处理一旦存在自动接力, “当前真正活着的是谁”必须重新用真实进程和 `manifest` 核对, 不能沿用旧心智模型.
  - 只看聊天里复制的命令, 不足以证明系统里真的按那条命令运行.
- 可复用点候选:
  - shell 等待脚本里, 不要把 `pgrep -af` 当成完成判据. 对非子进程等待, 优先记录目标 PID 并用 `kill -0` 轮询, 再配合状态文件二次确认.
  - 这个仓库里做依赖版本核对时, 必须优先使用 `pixi run python` / `pip show`, 不要在仓库根目录信任系统 `python3 import pytorch3d`.
  - 轨迹 preset 的建模和测试, 要同时覆盖“相机走向哪里”和“相机看向哪里”.
- 最适合写到哪里:
  - shell 等待自匹配问题 -> 新的跨项目 `self-learning.*` skill.
  - `pixi` / `pytorch3d` 版本核对约定 -> 根 `AGENTS.md` 和 `README.md`.
  - 自动接力与异常回收的后续工程 -> 继续保留在 `LATER_PLANS.md`.
- 需要同步的现有 `docs/` / `specs/` / plan 文档:
  - 仓库中没有 `docs/` 或 `specs/` 目录.
  - 已检查根 `AGENTS.md`, `README.md`, `task_plan.md`, `LATER_PLANS.md`.
- 是否需要新增或更新 `docs/` / `specs` / plan 文档:
  - 是.
  - 更新 `AGENTS.md` 和 `README.md`, 记录 `pixi` 环境版本核对约定.
  - `LATER_PLANS.md` 已覆盖未落地的流程改良项, 本轮无需新增计划条目.
- 是否提取/更新 skill:
  - 是.
  - 新增 `self-learning.shell-pgrep-self-match-wait-loop`, 因为它是跨项目可复用, 且这次已经有静态和动态证据闭环.

## [2026-04-05 06:11:21 UTC] `nt1` 视频最开始几帧跳动/质量差原因排查

### 现象
- 用户给出的 `single_image_multi_trajectory.py` 命令生成视频时, 最开始几帧容易出现跳动或质量明显差于后续帧.
- 这类问题不能直接说成“轨迹错了”或“模型坏了”, 需要先确认异常发生在控制图阶段还是最终扩散阶段.

### 主假设
- 主假设: 开头几帧的不稳定, 主要来自最终视频扩散阶段的首帧锚定方式.
- 更具体地说, 当前实现会把第一路 RGB control 的第 0 帧强行换成原始输入图, 但第 1 帧仍然直接使用渲染控制图.
- 如果“原图”和“渲染图第 1 帧”之间域差太大, 模型开场就会遇到一个很陡的条件跳变.

### 备选假设
- 备选假设: 相机轨迹或 control map 在第 0 -> 1 帧本身就不平滑, 所以前几帧抖动是前置资产阶段造成的.

### 静态证据
- `inference/versecrafter_inference.py`
  - `input_video_mask[:,:,0] = 0.0`
  - `control_videos[0][:,:,0] = img_latent.squeeze(2)`
  说明推理时确实对第 0 帧做了特判.
- `versecrafter/pipeline/pipeline_wan_versecrafter.py`
  - `geoada_encode_multi_frames(...)` 只有在 `ref_images` 不为 `None` 时, 才会额外 prepend 参考图 latent.
  - 当前这条命令没有传 `subject_ref_images`, 所以并没有“多帧强参考图”这层更稳的锚定.
- `inference/single_image_multi_trajectory_lib.py`
  - 轨迹从 `frame_index = 0` 开始立即进入正常位移公式, 并没有开场 hold 住几帧.
  - 线性位移: `scalar = frame_index * movement_distance * translation_reference_depth / num_frames`
  - orbit 位移: `theta = ... * frame_index / (num_frames - 1)`

### 动态证据
- 我对 `demo_data/nt1` 已完成轨迹的 `background_RGB.mp4` 与 `generated_video_0.mp4` 做了前几帧像素差统计.
- 关键比较不是“渲染 control 的 0->1”, 而是“实际喂给模型的第 0 帧输入图 -> 第 1 帧渲染 control”.
- 代表性结果:
  - 轨迹 `0(left)`: `input -> ctrl1 = 22.56`, `gen0 -> gen1 = 22.68`
  - 轨迹 `1(right)`: `input -> ctrl1 = 22.79`, `gen0 -> gen1 = 22.03`
  - 轨迹 `8(left_up)`: `input -> ctrl1 = 31.22`, `gen0 -> gen1 = 26.00`
  - 对比同一轨迹原始 control 视频自身的 `ctrl0 -> ctrl1` 只有 `3.38 / 3.33 / 4.28`
- 对 `nt1` 的 11 条已完成轨迹计算后:
  - `input -> ctrl1` 与 `gen0 -> gen1` 的相关系数为 `0.9828`

### 已验证结论
- 备选假设不成立为主因:
  - control 视频自身的 `0 -> 1` 在很多轨迹里并不大, 不能单独解释生成视频开头的巨大跳变.
- 当前更强的已验证结论是:
  - 问题主要出在最终生成阶段的“首帧真图锚定 + 第 1 帧立刻切到渲染 control”这个条件断层.
  - 轨迹从第 1 帧就开始运动, 又进一步放大了这种断层.
  - 因为没有额外的 `subject_ref_images` 多帧参考锚定, 模型只能靠这一个首帧替换来维持一致性, 所以前几帧更容易抖.

### 当前判断
- 这更像是当前 I2V/control 设计的边界问题, 不是单纯某个 preset 写错.
- 对开头几帧最有效的改善方向, 应优先考虑:
  - 让前几帧做 ease-in / hold, 不要第 1 帧就切出明显视差
  - 不只替换第 0 帧, 而是把输入图逐步混到前 `N` 帧 control 中
  - 或补一条真正的参考图 latent 路径, 而不是只靠第 0 帧替换

## [2026-04-05 06:44:34 UTC] `008693b52aa74367afb34d183046fecf88100bdc` 与首帧特判历史溯源

### 现象
- 用户要求确认 `008693b52aa74367afb34d183046fecf88100bdc` 是否和“第 0 帧特殊处理”有关.
- 还要判断这段逻辑是 raiscui 后来改出来的, 还是更早就已经存在.

### 静态证据
- `git show --stat --summary 008693b52aa74367afb34d183046fecf88100bdc`
  - 结果显示该 commit 只有:
    - `README.md | 19 insertions`
  - 没有改 `inference/versecrafter_inference.py`
- `git blame -L 403,419 inference/versecrafter_inference.py`
  - `input_video_mask[:,:,0] = 0.0`
  - `control_videos[0][:,:,0] = img_latent.squeeze(2)`
  这两行都归属于 `5f599ed6bedbffb1136d18fdf6c4fd113c96cc85`
- `git log -S 'control_videos[0][:,:,0] = img_latent.squeeze(2)'`
  - 首次出现提交也是 `5f599ed...`
- `git log -S 'input_video_mask[:,:,0] = 0.0'`
  - 首次出现提交同样是 `5f599ed...`

### 历史对比证据
- `git diff 5f599ed..d4261ba -- inference/versecrafter_inference.py`
  - raiscui 的 `d4261ba5057be1f0fcf4a05de7529310349199c5` 的确改过这个文件
  - 但改动集中在:
    - `--negative_prompt`
    - `--gpu_memory_mode`
    - `fsdp_dit`
    - `teacache_offload`
  - 没有改动首帧特判这段逻辑
- 直接查看 `5f599ed` 版本文件对应片段, 已经能看到:
  - `input_video_mask[:,:,0] = 0.0`
  - `control_videos[0][:,:,0] = img_latent.squeeze(2)`

### 已验证结论
- `008693b52aa74367afb34d183046fecf88100bdc` 与这段首帧特判逻辑无关.
- 这段逻辑不是 raiscui 后来引入的.
- 它在 `5f599ed6bedbffb1136d18fdf6c4fd113c96cc85` 初始提交里就已经存在.
- raiscui 后续提交虽然改过 `inference/versecrafter_inference.py`, 但没有碰这段代码.

## [2026-04-05 06:50:15 UTC] “为什么现在更明显” 的放大因素排序

### 现象
- 已确认首帧特判本身是旧逻辑.
- 当前需要进一步判断: 为什么在用户这条 `single_image_multi_trajectory.py --camera_only` 命令里, 这个老问题会更明显.

### 候选因素逐项验证

#### 候选A: 多轨迹链路从第 1 帧立即开始运动
- 静态证据:
  - `single_image_multi_trajectory_lib.py` 的线性轨迹:
    - `scalar = frame_index * movement_distance * translation_reference_depth / num_frames`
  - orbit 轨迹:
    - `theta = ... * frame_index / (num_frames - 1)`
  - 说明第 0 帧静止, 第 1 帧立刻进入正常位移, 没有开场 hold/ease-in.
- 历史证据:
  - `inference/single_image_multi_trajectory.py` 与 `inference/single_image_multi_trajectory_lib.py` 都是 raiscui 的 `d4261ba...` 新增文件.
- 动态证据:
  - 在 `nt1` 里, 左移/右移/左上这类“第 1 帧视差更明显”的轨迹, `gen0 -> gen1` 跳变最大.
  - 这和之前统计到的 `input -> ctrl1` 强相关吻合.
- 结论:
  - 这是当前最强的放大器.

#### 候选B: `camera_only` 把整张图都当 rigid background
- 静态证据:
  - `single_image_multi_trajectory.py` 明确写着:
    - `Disable foreground segmentation / Gaussian fitting and treat the whole image as rigid background`
    - `keep mask dir empty so the whole image becomes rigid background`
  - `build_background()` 在 mask 为空时, 会把整张图都并入背景点云.
  - 同时 Gaussian 分支变成 `num_objects = 0`, 对应 `3D_gaussian_RGB` / depth 约束为空.
- 动态证据:
  - 当前工作区里能直接比较到的批处理样本几乎全是 `camera_only=True`.
  - 在这些样本里, `input -> ctrl1` 与 `gen0 -> gen1` 的跨样本相关系数仍达到 `0.9951`.
  - 说明 `camera_only` 不是单独的充分条件, 因为同样都是 `camera_only`, 严重程度差异依然很大.
- 当前判断:
  - `camera_only` 更像次级放大器.
  - 它会让“render 第 1 帧”和“原图”之间的域差更依赖背景重建质量, 在近景物体多、遮挡强的场景更容易把老问题放大.
  - 但现有证据还不足以说“只要 camera_only 就一定明显”.

#### 候选C: `fsdp_dit=True` / `teacache_offload=True`
- 静态证据:
  - `fsdp_dit` 的注释是“Use FSDP to save more GPU memory in multi gpus”.
  - `teacache_offload` 的注释是“offload TeaCache tensors to cpu to save a little bit of GPU memory”.
  - `TeaCache` 启用时还显式:
    - `skip the first {num_skip_start_steps} steps`
  - `wan_transformer3d.py` 里 `teacache.cnt < teacache.num_skip_start_steps` 时, 会强制 `should_calc = True`.
- 当前判断:
  - 这两项更像部署/缓存策略.
  - 现有静态证据看不出它们会专门把“视频前几帧”变差.
  - 尤其 `teacache_offload` 只改缓存放在哪, 没改阈值和前几步跳过逻辑.
- 结论:
  - 目前没有足够证据把它们列为主要放大器.

#### 候选D: `negative_prompt`
- 静态证据:
  - raiscui 的改动只是让 `negative_prompt` 可以从命令行传入.
  - 当前用户命令本身显式提供了 `--negative_prompt`, 所以现在实际生效的是用户自己的文本, 不是 raiscui 改过的默认值.
- 当前判断:
  - 负面提示词当然会影响整体风格和稳定性偏好.
  - 但目前没有证据显示它是“开头第 0 -> 1 帧硬切换”的主因.

### 综合结论
- 最强放大器:
  - raiscui 引入的多轨迹用法本身, 尤其是“第 1 帧立刻运动, 没有开场 hold/ease-in”.
- 次级放大器:
  - `camera_only`, 因为它把场景整体简化成 rigid background, 会在某些场景显著增大 `input -> ctrl1` 的 render 域差.
- 目前证据弱:
  - `fsdp_dit`
  - `teacache_offload`
  - `negative_prompt` 支持本身

### 最终判断
- 更准确的说法不是“raiscui 改坏了首帧特判”.
- 而是:
  - 老的首帧特判一直在.
  - raiscui 新增的多轨迹 + `camera_only` 使用场景, 更容易把这个老问题暴露和放大.

## [2026-04-05 07:18:09 UTC] 轨迹前段 hold/ease-in 修复实现

### 设计目标
- 不去改推理阶段的首帧特判, 先从更低风险的轨迹输入侧下手.
- 让前几帧位移更慢, 但不要拖慢整条镜头, 要在短时间内追平原始轨迹.

### 实现方案
- 在 `single_image_multi_trajectory_lib.py` 新增:
  - `DEFAULT_LEAD_IN_FRAMES = 5`
  - `DEFAULT_LEAD_IN_HOLD_FRAMES = 2`
- 新增 `_build_lead_in_frame_indices(...)`
  - 前 `hold_frames` 帧保持 `0`
  - `hold_frames..lead_in_frames` 之间用二次缓入曲线重映射到同一个终点
  - `lead_in_frames` 之后恢复原始帧索引
- 线性与 orbit 轨迹都统一改为使用这组“虚拟帧索引”.
- 这样做的效果是:
  - 开头更稳
  - 第 5 帧后追平原轨迹
  - 不需要改外层脚本命令接口

### 验证结果
- 动态数值检查:
  - `left` baseline 位移:
    - `[0.055556, 0.111111, 0.166667, 0.222222, 0.277778, ...]`
  - `left` eased 位移:
    - `[0.0, 0.017361, 0.069444, 0.15625, 0.277778, ...]`
  - `clockwise` baseline 前段位移范数:
    - `[0.062436, 0.135208, 0.199237, 0.225, 0.199237, ...]`
  - `clockwise` eased 前段位移范数:
    - `[0.0, 0.018533, 0.079929, 0.189354, 0.199237, ...]`
- 已验证结论:
  - 这次实现确实让前几帧更慢.
  - 同时在第 5 帧后回到原轨迹, 没把整条镜头都拖长.

## [2026-04-05 11:44:38 UTC] 3ds Max `FOV 90°` 与单图多轨迹内参覆盖方案

### 现象
- 用户说明 `my` 和 `nt` 系列输入图来自 3ds Max 渲染, 使用 `FOV 90°`.
- 当前 `single_image_multi_trajectory.py` 的共享内参来自 Step 1 `moge-v2_infer.py`.
- `depth_intrinsics.npz` 中的 `intrinsic` 随后会被:
  - camera-only 空 Gaussian JSON 继承
  - `fit_3D_gaussian.py` 读取并继续写入 `gaussian_params.json`
  - `rendering_4D_control_maps.py` 读取并用于最终 control map 渲染

### 静态证据
- `moge-v2_infer.py`
  - `np.savez_compressed(..., depth=..., intrinsic=...)`
- `single_image_multi_trajectory.py`
  - Step 1 之后直接复用 `shared/estimated_depth/depth_intrinsics.npz`
  - camera-only 分支会从该 NPZ 读取 `intrinsic`, 生成空 Gaussian JSON
  - 非 camera-only 分支会把该 NPZ 传给 `fit_3D_gaussian.py`
- `fit_3D_gaussian.py`
  - 会从 NPZ 读取 `intrinsic`, 再按分辨率反归一化
- `rendering_4D_control_maps.py`
  - 会从 NPZ 读取 `intrinsic`, 再构造 `PerspectiveCameras(focal_length, principal_point)`

### 动态 / 数据证据
- 现有样本 `demo_data/my7/shared/estimated_depth/depth_intrinsics.npz`:
  - `intrinsic = [[0.434082, 0, 0.5], [0, 0.771484, 0.5], [0, 0, 1]]`
  - 分辨率 `2730 x 1536`
  - 反归一化后:
    - `fx ≈ 1185.04`
    - `fy ≈ 1185.00`
    - `cx = 1365`
    - `cy = 768`
- 若按“水平 FOV = 90° + 主点居中 + 方形像素”重建 K:
  - `fx = fy = width / 2 = 1365`
  - 归一化后:
    - `fx_norm = 0.5`
    - `fy_norm = 1365 / 1536 = 0.888672`
    - `cx_norm = cy_norm = 0.5`
- 说明当前预测内参与“已知 FOV 90°”并不相同.

### 外部资料
- Autodesk 官方文档:
  - 3ds Max 相机 `.fov` 属性默认是 horizontal FOV
  - `fovType` 可切换 horizontal / vertical / diagonal
  - 官方文档还写明 `Horizontal (The default.)`
- 这意味着, 在没有额外反证时, 把用户说的 “3ds Max FOV 90°” 按“水平 FOV 90°”解释是当前最稳妥的口径.

### 当前结论
- 主假设目前得到较强静态证据支持:
  - 对 `my` / `nt` 这类已知真值相机输入, 应优先覆盖共享 `depth_intrinsics.npz` 的 `intrinsic`, 而不是继续使用 MoGE 估计 K.
- 最佳覆盖点:
  - Step 1 之后, Step 2/3 之前
  - 这样 camera-only / Gaussian / render 都能自动保持一致
- 仍需注意的备选解释:
  - Blender 里用于展示的相机对象目前只按 `fx` 设 FOV, 没完整消费 `fy/cx/cy`
  - 所以后续如果“Blender 视图看起来不对, 但最终生成改善了”, 不应误判这次覆盖策略失败
