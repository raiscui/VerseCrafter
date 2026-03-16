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
