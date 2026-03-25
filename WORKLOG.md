# 工作日志

## [2026-03-22 12:35:40 UTC] 任务名称: 将 7 号镜头从 `clockwise_1.5` 调整为逆时针轨迹

### 任务内容
- 将单图多轨迹批处理里的 7 号镜头从顺时针大半径 orbit, 改成逆时针大半径 orbit.
- 保持索引 `7` 不变, 同时同步修正用户可见名称、prompt、README、OpenSpec 与测试.

### 完成过程
- 先定位确认当前 canonical preset 中索引 `7` 确实对应 `clockwise_1.5`.
- 回读轨迹生成逻辑后, 没有给 7 号镜头单独打特判, 而是为 `TrajectoryPreset` 新增 `orbit_direction` 元数据.
- 将统一 orbit 公式改造成 `_generate_orbit_offsets_cv(...)`, 让半径倍率和顺/逆时针方向都由 preset 数据决定.
- 把索引 `7` 的名称和文案同步更新为:
  - `counterclockwise_1.5`
  - `Camera is orbiting counterclockwise around the scene with a wider radius`
- 同步更新:
  - `README.md`
  - `openspec/changes/add-clockwise-radius-variants/*`
  - `tests/test_single_image_multi_trajectory_lib.py`
  - `tests/test_single_image_multi_trajectory_smoke.py`
- 最后用 `py_compile`、`pytest` 和一段动态数值检查确认方向与半径都已正确变化.

### 总结感悟
- 这类镜头 preset 变更, 不能只盯着几何轨迹, 因为这个项目已经把 prompt 和 dry-run 也做成了用户承诺的一部分.
- 把 orbit 的方向也数据化之后, 后面再加顺/逆时针档位时会更自然, 不需要继续扩展名字分支.

## [2026-03-22 12:18:55 UTC] 任务名称: 解释 `demo_data/my4` 跑到 8 号镜头时为何仍只有 1 张 GPU 工作

### 任务内容
- 排查用户在 `demo_data/my4` 批处理运行中, 已进入 8 号镜头但仍只看到 1 张 GPU 工作的原因.
- 不修改代码, 先基于真实运行中的父子进程与 manifest 做证据核对.

### 完成过程
- 先回读历史上下文, 确认近期确实已经完成了多轨迹扩展和 prompt 补充, 且此前也做过多卡相关排查.
- 再读取当前父进程 `single_image_multi_trajectory.py` 与 8 号镜头子进程 `versecrafter_inference.py` 的 `/proc/<pid>/cmdline`.
- 验证到当前 8 号镜头的 Step 6 并没有走 `torchrun`, 而是直接以单进程方式运行.
- 同时核对 `demo_data/my4/manifest.json`, 发现当前记录的也是单卡设置:
  - `ulysses_degree = 1`
  - `ring_degree = 1`
  - `nproc_per_node = 1`
  - `num_inference_steps = 30`
- 因此将问题收敛为“当前真实运行参数与用户口头预期不一致”, 而不是“已经进入双卡步骤但第二张卡没有干活”.

### 总结感悟
- 对多卡任务, 最容易误导人的不是 GPU 本身, 而是“我以为自己跑的是哪条命令”与“系统里真正跑起来的是哪条命令”之间的偏差.
- 在这种场景里, 直接看 `/proc/<pid>/cmdline` 和实际子进程, 比只看终端历史或复制出来的命令更可靠.

## [2026-03-22 12:36:50 UTC] 任务名称: 将 `demo_data/my4` 的 8-11 号镜头按双卡参数重启

### 任务内容
- 复用 `demo_data/my4` 已完成的共享产物和前 0-7 号镜头结果.
- 只对 8-11 号镜头按双卡参数重启, 确认真正使用两张 A800.

### 完成过程
- 先核对脚本 `resume` 行为, 确认复跑同一 `output_root` 时会复用共享步骤和已完成镜头.
- 再检查 `manifest.json`, 确认当前待处理的是 8-11 号镜头.
- 用 `pixi run python` 验证:
  - `torch.cuda.device_count() = 2`
  - `xfuser` / `yunchang` 导入正常
- 先执行一轮 `--dry_run`, 确认 Step 6 命令已经明确拼成 `torchrun --nproc-per-node=2`.
- 随后正式启动双卡批处理, 参数聚焦为:
  - `--num_inference_steps 60`
  - `--gpu_memory_mode model_cpu_offload`
  - `--ulysses_degree 2`
  - `--ring_degree 1`
  - `--nproc_per_node 2`
  - `--preset_indices 8 9 10 11`
- 启动后立即验证进程树和运行日志, 确认:
  - 有 `torchrun`
  - 有两个 worker
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
- 最后用 `nvidia-smi` 复核到两张 A800 同时有显存占用和计算利用率.

### 总结感悟
- 真正把“双卡是否生效”说清楚, 最稳的是四件事一起看:
  - `dry_run` 组装出的命令
  - 实际进程树
  - 运行日志里的 rank -> device 映射
  - `nvidia-smi` 实时占用
- 只看其中一项, 都很容易误判.

## [2026-03-24 18:00:55 UTC] 任务名称: 排查单图多轨迹命令如何跳过联网检查并直接复用本地缓存

### 任务内容
- 排查 `inference/single_image_multi_trajectory.py` 这条链路里哪些模型加载点可能触发联网.
- 判断当前用户命令能否在不改代码的情况下直接走离线缓存.

### 完成过程
- 回读六文件上下文, 确认近期多轨迹与双卡逻辑的历史改动, 避免把旧问题和本次离线诉求混在一起.
- 逐段检查:
  - `inference/single_image_multi_trajectory.py`
  - `inference/versecrafter_inference.py`
  - `inference/moge-v2_infer.py`
  - MoGe 安装包里的 `from_pretrained` 实现
- 确认当前链路中:
  - VerseCrafter transformer 走本地目录 `model/VerseCrafter`
  - VerseCrafter base model 走本地目录 `model/Wan2.1-T2V-14B`
  - MoGe 在传入本地 `model.pt` 时不会走 `hf_hub_download`
- 做了最小动态验证:
  - `HF_HUB_OFFLINE=1` 下成功加载本地 tokenizer
  - `HF_HUB_OFFLINE=1` 下成功加载本地 MoGe checkpoint
- 额外检查 `demo_data/my5`, 确认共享深度和 camera-only 的共享产物已经存在, 可直接靠默认 `resume` 复用.

### 总结感悟
- 这类“明明给了缓存路径, 为什么还联网”的问题, 很多时候不是模型真要重新下载, 而是没有把“本地路径是否真实存在”和“库的离线开关”一起确认.
- 对这个项目来说, 最省事的路径是双保险:
  - 所有模型参数显式走本地路径
  - 命令前加 `HF_HUB_OFFLINE=1`
  - 不要换 `output_root`, 直接吃 `resume` 的共享产物

## [2026-03-25 13:12:09 UTC] 任务名称: 在 `my6` 完成后接手启动 `demo_data/my7`

### 任务内容
- 确认 `demo_data/my6` 是否真正完成.
- 检查上一轮挂起的自动接力是否真的已经把 `demo_data/my7` 启动起来.
- 若未启动, 直接按用户提供的参数手动启动 `demo_data/my7`, 并核对运行状态.

### 完成过程
- 先回读 `task_plan.md`, 再检查进程、`demo_data/my6/manifest.json` 与 `demo_data/my7` 目录状态.
- 验证到 `my6` 实际已经全部完成, 但系统中只剩一个等待脚本, 没有真实的 `my7` 推理进程.
- 进一步用 `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 证实:
  - 等待脚本把自己也匹配进去了
  - 所以一直错误地判断 `my6` 仍在运行
- 停掉误挂的等待脚本后, 直接按用户原命令启动 `my7`.
- 启动后立刻核对:
  - `demo_data/my7/manifest.json` 已创建
  - `shared/estimated_depth/*` 已落盘
  - `shared/fitted_3D_gaussian/gaussian_params.json` 已落盘
  - 当前子进程正在执行 `rendering_4D_control_maps.py`
  - 当前日志已进入 0 号镜头背景渲染

### 总结感悟
- 对这种“等待某个进程结束再接力”的脚本, 只靠 `pgrep -af` 这种基于命令行全文匹配的写法很危险.
- 如果匹配模式被脚本自己的命令行文本包含进去, 就会出现“目标早就结束了, 但等待脚本还在无限等待”的假象.
- 这次 `my7` 已经真正启动, 但当前还是前置单卡阶段, 还没到后面的双卡生成段.

## [2026-03-25 18:33:10 UTC] 任务名称: 核对 `pixi` 默认环境中的 `PyTorch` / `pytorch3d` 真实版本

### 任务内容
- 在不只依赖静态配置的前提下, 动态确认项目默认 `pixi` 环境里真实安装的 `torch` / `torchvision` / `torchaudio` / `pytorch3d` 版本.
- 额外区分普通系统 `python3` 与项目 `pixi` 环境的差异, 避免被本地源码目录误导.

### 完成过程
- 先回读六文件上下文, 避免把此前“系统 Python 版本”和“项目环境版本”混在一起.
- 再用 `pixi run --manifest-path ... python -m pip show ...` 读取安装元数据.
- 接着用 `pixi run ... python` 动态验证:
  - `sys.executable`
  - `torch.__version__`
  - `torch.version.cuda`
  - `torch.cuda.is_available()`
  - `pytorch3d.__file__` 与 `pytorch3d.__version__`
- 最后补做一轮对照验证, 确认普通 `python3` 在仓库根目录下会把本地 `pytorch3d/` 源码目录当成可导入模块, 从而误导版本判断.

### 总结感悟
- 查 Python 包真实版本时, `pip show`、`importlib.metadata` 和模块 `__file__` 要一起看, 单看 `import` 是否成功不够稳.
- 这个仓库里真正应该信任的运行环境是 `pixi` 默认环境, 不是外部系统 Python.
