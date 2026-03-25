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
