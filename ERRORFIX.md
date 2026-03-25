# 错误修复记录

## [2026-03-22 12:18:55 UTC] 问题: `demo_data/my4` 已跑到 8 号镜头但只见 1 张 GPU 工作

### 问题现象
- 用户预期当前运行应为双卡.
- 但在 `nvidia-smi` 中只看到 1 张 GPU 在工作.

### 原因判断
- 已验证结论不是“8 号镜头的双卡 Step 6 没有正确调度第二张卡”.
- 当前真实运行中的 8 号镜头 Step 6 本身就是单卡参数:
  - `--ulysses_degree 1`
  - `--ring_degree 1`
  - `--num_inference_steps 30`
  - 无 `torchrun`
- 因此只见 1 张 GPU 工作, 是当前实际运行参数导致的表现.

### 证据
- 读取 `/proc/84075/cmdline` 与 `/proc/122250/cmdline`.
- 读取 `demo_data/my4/manifest.json`.
- 三者都指向单卡配置, 且与用户口头贴出的双卡命令不一致.

### 修复/处置
- 本轮未改代码.
- 先向用户解释: 当前问题更像是命令启动层或运行轮次混淆, 不是代码在 8 号镜头阶段悄悄把双卡降成单卡.

### 后续验证建议
- 后续若要再次确认双卡是否生效, 应直接观察是否真的启动了:
  - `torchrun --nproc-per-node=2`
- 并在启动后立即读取实际父进程和子进程 `argv`, 避免继续把“预期命令”误当成“真实运行命令”.

## [2026-03-22 12:36:50 UTC] 问题: `demo_data/my4` 需要把 8-11 号镜头切回双卡继续跑

### 问题现象
- 原先那轮运行已经把 0-7 号镜头做完, 但 8-11 号镜头尚未完成.
- 用户需要继续后半段镜头, 并确保真正使用双卡.

### 处理方式
- 不新建 `output_root`, 继续使用 `demo_data/my4`.
- 借助默认 `resume` 机制, 只重启:
  - `--preset_indices 8 9 10 11`
- 并显式传入双卡参数:
  - `--ulysses_degree 2`
  - `--ring_degree 1`
  - `--nproc_per_node 2`

### 验证结果
- `--dry_run` 已显示会走 `torchrun --nproc-per-node=2`.
- 正式启动后已有:
  - `torchrun`
  - 两个 Step 6 worker
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
- `nvidia-smi` 也已同时看到两张卡都有占用.

## [2026-03-25 13:12:09 UTC] 问题: `my6` 已完成, 但自动接力没有把 `my7` 启动起来

### 问题现象
- 用户提示 `my6` 已经做完.
- 但 `demo_data/my7` 目录仍没有 `manifest.json`, 说明 `my7` 没有真正开始.
- 系统里没有真实的 `my6` 或 `my7` 推理进程, 只剩一个等待脚本.

### 原因判断
- 已验证结论:
  - 等待脚本使用了:
    - `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'`
  - 这条匹配规则把等待脚本自身命令行也匹配进去了.
  - 结果是脚本永远判断“`my6` 仍在运行”, 从而不会执行后面的 `my7` 启动命令.

### 证据
- `demo_data/my6/manifest.json` 顶层 `status = completed`, 且 8-11 号镜头全部完成.
- `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 当前只返回等待脚本本身.
- `demo_data/my7/manifest.json` 在修复前不存在.

### 修复/处置
- 停掉误挂的等待脚本.
- 直接按用户提供的参数手动启动 `demo_data/my7`.

### 验证结果
- `demo_data/my7/manifest.json` 已创建, 顶层 `status = running`.
- 当前会话日志显示:
  - MoGe 深度估计完成
  - 已进入 `rendering_4D_control_maps.py`
  - 已开始 `Rendering(mesh-batch) background`
- 当前 GPU 观测:
  - GPU0 `100%`
  - GPU1 `0%`
- 该现象与当前前置单卡阶段一致, 说明 `my7` 已正常开始执行.
