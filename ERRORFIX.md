# 错误修复记录

## [2026-03-16 03:31:00 UTC] 问题: `demo_data/my3` 双卡 Step 6 报 `xfuser is not installed`

### 问题现象
- `single_image_multi_trajectory.py` 已成功完成深度估计与 4D 控制图渲染.
- 最终 `torchrun --nproc-per-node=2 inference/versecrafter_inference.py` 失败.
- 关键报错:
  - `RuntimeError: xfuser is not installed.`

### 原因
- 当前 Pixi 环境缺少 VerseCrafter 多卡运行时依赖:
  - `xfuser`
  - `yunchang`
- 同时, 默认 `moge_version=v2` 会走 `Ruicheng/moge-2-vitl-normal`, 若网络慢或无代理, 会在深度阶段卡住.

### 修复
- 显式指定本地深度模型:
  - `--moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`
- 安装多卡依赖:
  - `pixi run pip install xfuser==0.4.2 yunchang==0.6.2 --progress-bar off -i https://mirrors.aliyun.com/pypi/simple/`
- 复用已有 `rendering_4D_maps` 直接重跑 Step 6.

### 验证
- `xfuser` 与 `yunchang` 已可导入.
- 10 步采样已成功完成.
- 输出视频:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos/generated_video_0.mp4`
- `ffprobe` 验证结果:
  - `width=1280`
  - `height=720`
  - `nb_frames=81`
  - `duration=5.0625`
  - `r_frame_rate=16/1`

## [2026-03-16 04:17:00 UTC] 经验: `my3` 的步数对比测试不要重跑整链路

### 问题现象
- 用户只想看 `num_inference_steps` 从 `10` 提升到 `60` 的结果.
- 如果直接重跑整条 `single_image_multi_trajectory.py` 链路, 会重复耗费时间在深度估计和 4D 控制图渲染上.

### 原因
- 对这类“同一输入图、同一轨迹、同一控制图, 仅调整采样步数”的对比任务, 真正变化只发生在 Step 6.

### 修复
- 复用:
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps`
- 只重跑:
  - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py ... --num_inference_steps 60`
- 新结果另存到:
  - `generated_videos_steps60_compare/`

### 验证
- 60 步视频已成功生成:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare/generated_video_0.mp4`

## [2026-03-21 13:22:00 UTC] 问题: `my4` 单图多轨迹在 Step 1 前后报 `No CUDA GPUs are available`

### 问题现象
- `single_image_multi_trajectory.py` 原先会直接执行:
  - `inference/moge-v2_infer.py ... --device cuda`
- 实际运行时在 PyTorch CUDA 初始化阶段失败:
  - `RuntimeError: No CUDA GPUs are available`
- 即使显式传入 `--moge_pretrained` 与 `--moge_version v2`, 报错也完全不变.

### 原因
- 物理 GPU 存在, 但当前环境并没有可被 CUDA workload 使用的设备实例.
- 动态证据:
  - `nvidia-smi` 能看到 `NVIDIA A800-SXM4-80GB`
  - `torch.cuda.is_available() == False`
  - `torch.cuda.device_count() == 1`
  - `torch.cuda.get_device_name(0)` 报 `No CUDA GPUs are available`
- 静态 / 外部资料线索:
  - `nvidia-smi` 显示 `MIG Mode: Enabled`
  - 同时显示 `No MIG devices found`
  - NVIDIA MIG User Guide 说明: 没有创建 GPU / Compute instance 时, CUDA workload 不能在该 GPU 上运行.

### 修复
- 没有把问题掩盖成 CPU fallback.
- 改为在 `single_image_multi_trajectory.py` 入口增加 CUDA 预检:
  - 先判断这次运行是否真的需要 CUDA
  - 如果需要, 就在真正起重流程前探测 Torch CUDA 状态
  - 探测失败时直接输出清晰报错, 并附带 MIG 提示
- 同时新增单测覆盖上述逻辑.

### 验证
- `pixi run pytest tests/test_single_image_multi_trajectory_cuda_preflight.py tests/test_single_image_multi_trajectory_smoke.py -q`
  - 输出: `7 passed in 0.84s`
- 真实命令复跑后, 已不再先掉进 `moge-v2_infer.py` 深栈.
- 新输出会直接说明:
  - 当前工作流为什么需要 CUDA
  - Torch 当前看到的 CUDA 状态
  - `MIG 已启用但没有实例` 的定位提示
