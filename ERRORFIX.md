# 错误修复记录
## [2026-03-15 04:03:00 UTC] 问题: pixi install-pytorch3d 任务使用 Bash if 导致解析失败

### 问题现象
- 执行 `pixi run --manifest-path pixi.toml install-pytorch3d` 时, 在任务真正开始 clone / install 前就报错:
  - `failed to parse shell script`
  - `Unsupported reserved word`
- 报错位置指向 `if [ ! -d pytorch3d ]; then`.

### 原因分析
- 静态证据:
  - `pixi.toml` 中 `install-pytorch3d` 任务使用了 Bash 风格 `if ... then ... fi`.
  - Pixi 官方文档说明任务默认运行在 `deno_task_shell`, 这是有限的 bourne-shell 实现.
- 动态证据:
  - 直接执行原任务可稳定复现同款报错.
  - 最小实验表明 `test -d foo || echo missing` 可以, 但 Bash `if` 不行.
  - 最小实验还表明多行命令之间需要显式 `&&` / `||` 连接, 不能把普通换行当 Bash 脚本分号.

### 修复方式
- 将任务从:
  - `if [ ! -d pytorch3d ]; then ... fi`
- 改为:
  - `git clone https://github.com/facebookresearch/pytorch3d.git pytorch3d || test -d pytorch3d`
  - 下一行 `&& python -m pip install --no-build-isolation ./pytorch3d`

### 修复后的行为
- 如果 `pytorch3d/` 不存在, 会执行 clone, 成功后继续安装.
- 如果 `pytorch3d/` 已存在, clone 失败后 `test -d pytorch3d` 返回成功, 继续安装.
- 如果 clone 因网络或权限等原因失败, 且目录也不存在, 任务会保持失败, 不会被静默吞掉.

### 验证记录
- `pixi run --manifest-path pixi.toml --dry-run install-pytorch3d`
  - 成功输出新任务命令, 无解析错误.
- `pixi task list --manifest-path pixi.toml`
  - 成功列出 `install-pytorch3d`.

## [2026-03-15 11:12:00 UTC] 问题: VerseCrafter 单图多轨迹真实测试连续暴露 Step 5 编码、Step 6 导入和单卡 OOM 三类阻塞

### 问题现象
- 第一轮真实测试在 `rendering_4D_control_maps.py` 写 mp4 时崩溃:
  - `torchvision.io.write_video`
  - `TypeError: an integer is required`
- 修掉后, 第二轮真实测试在 Step 6 初始化时报:
  - `ModuleNotFoundError: No module named 'librosa'`
- 再修掉后, Step 6 单卡采样在 A800 80GB 上报:
  - `torch.cuda.OutOfMemoryError`

### 原因分析
- Step 5:
  - 当前 `torchvision` / `PyAV` 组合在 `write_video` 路径上不兼容.
- Step 6 导入:
  - `videox_fun.models.__init__` 在包初始化时强制导入音频编码器模块.
  - 这些模块依赖 `librosa`, 但 VerseCrafter 当前相机轨迹生成链路并不需要音频编码器.
- Step 6 OOM:
  - `versecrafter_inference.py` 原来把 `GPU_memory_mode` 固定成 `model_full_load`.
  - 实际动态验证表明:
    - `model_full_load` 和 `model_cpu_offload` 都不够.
    - `model_cpu_offload_and_qfloat8` 才能在当前 A800 80GB 上稳定跑通 720p / 10 step.

### 修复方式
- Step 5:
  - `save_video_from_frames()` 改用 `cv2.VideoWriter`.
- Step 6 导入:
  - 在 `third_party/VideoX-Fun/videox_fun/models/__init__.py` 中把
    - `FantasyTalkingAudioEncoder`
    - `WanAudioEncoder`
  改成可选依赖导入, 缺 `librosa` 时暴露清晰占位错误, 但不阻塞非音频工作流.
- Step 6 OOM:
  - 给 `inference/versecrafter_inference.py` 新增 `--gpu_memory_mode`.
  - 给 `inference/single_image_multi_trajectory.py` 透传同名参数.
  - 将批处理默认值改成 `model_cpu_offload_and_qfloat8`.
- 验证环境:
  - `pixi.toml` 补入 `pytest`.
  - 新增 `tests/test_videox_fun_optional_audio_import.py`.
  - 扩展 `tests/test_single_image_multi_trajectory_smoke.py` 验证默认显存模式透传.

### 验证记录
- `python3 -m py_compile inference/rendering_4D_control_maps.py`
- 最小 smoke: `save_video_from_frames()` 写 mp4 后再 `read_video()` 读回, 成功.
- `pixi install`
- `pixi run python -m pytest tests/test_single_image_multi_trajectory_smoke.py tests/test_single_image_multi_trajectory_lib.py tests/test_videox_fun_optional_audio_import.py`
  - 结果: `9 passed`
- 真实 GPU 动态验证:
  - `model_cpu_offload` -> OOM
  - `model_cpu_offload_and_qfloat8` -> 成功输出 `demo_data/my/0/generated_videos/generated_video_0.mp4`
- 批处理 resume 验证:
  - 已连续成功产出 `0`、`1`、`2` 三条视频.

### 后续提醒
- 若未来恢复 `videox_fun.models` 的全量强导入, `librosa` 问题会再次出现.
- 若单卡默认值又被改回非 qfloat8 模式, 当前这类 720p 多控制视频推理很可能重新 OOM.

## [2026-03-15 13:52:30 UTC] 问题: 新场景首次运行被 MoGe 默认远程权重拉取拖慢, 且 `--moge_pretrained` 误传目录会直接失败

### 问题现象
- 在 `demo_data/my2/10000.png` 的新场景验证中, Step 1 默认使用:
  - `Ruicheng/moge-2-vitl-normal`
- 终端进度条长期停在:
  - `model.pt: 0.00/1.32G`
- 但检查 Xet 日志后发现字节数其实在持续增长.
- 随后尝试用本地缓存快照绕过下载时, 第一版命令把 `--moge_pretrained` 传成了目录:
  - `/root/.cache/.../snapshots/<sha>`
- 结果报错:
  - `IsADirectoryError: [Errno 21] Is a directory`

### 原因分析
- 静态证据:
  - `inference/moge-v2_infer.py` 中最终调用:
    - `from_pretrained(pretrained_model_name_or_path)`
  - `moge.model.v2.from_pretrained` 后续会把该路径交给 `torch.load`.
- 动态证据:
  - 远程下载阶段:
    - `~/.cache/huggingface/xet/logs/...` 显示底层 `observed bytes sent so far` 持续增长
    - 说明不是完全挂死, 而是下载过慢且 tqdm 进度显示不可信
  - 本地目录路径阶段:
    - 直接抛 `IsADirectoryError`
    - 说明这里需要的是具体文件, 不是 snapshot 目录

### 修复方式
- 不再等待新的远程下载完成, 直接复用本机已缓存的完整权重:
  - `/root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`
- 把 `--moge_pretrained` 改成指向这个 `model.pt` 文件本身.

### 验证记录
- 错误命令:
  - `--moge_pretrained /root/.cache/.../snapshots/39c4...`
  - 结果: `IsADirectoryError`
- 正确命令:
  - `--moge_pretrained /root/.cache/.../snapshots/39c4.../model.pt`
  - 结果:
    - Step 1 深度估计成功
    - 后续 Step 5 / Step 6 也顺利完成
    - 最终输出 `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`

### 后续提醒
- 以后如果新环境第一次跑 `moge-v2_infer.py` 又卡在 `0.00/1.32G`, 先看 Xet 日志, 不要只看 tqdm 进度条.
- 若机器里已经有 `Ruicheng/moge-2-vitl` 的完整缓存, 优先直接传 `model.pt` 文件路径, 能显著减少首次验证等待时间.
