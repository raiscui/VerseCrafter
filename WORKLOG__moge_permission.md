# 工作日志: `moge_pretrained` 权限路径与小规模验证

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] 任务名称: 修正 MoGe 本地路径写法并完成小规模验证

### 任务内容
- 处理 `single_image_multi_trajectory.py` 在 Step 1 因 `--moge_pretrained /root/.cache/...` 触发的权限报错.
- 基于用户给出的 `demo_data/my7/d.png` 命令, 改成可移植写法并做小规模验证.

### 完成过程
- 先确认当前进程用户是 `rais`, 而 `/root/.cache` 为 root 私有目录, 因此原命令的本地模型路径天然不可读.
- 再确认当前 `~/.cache/huggingface/hub` 虽然可读, 但并没有现成的 `moge-2-vitl` 本地模型文件.
- 修改 `inference/moge-v2_infer.py`, 加入本地 checkpoint 路径前置校验:
  - 本地路径会先 `expanduser()`
  - 对无权限路径给出更明确的中文报错
  - 对不存在的本地文件提示改用 HF repo id
- 修改 `inference/single_image_multi_trajectory.py` 的 `--moge_pretrained` help 文案.
- 修改 `cmd.md`, 将多处 `/root/.cache/.../model.pt` 命令示例替换为:
  - `--moge_pretrained Ruicheng/moge-2-vitl`
- 完成三组验证:
  - `py_compile`
  - 直接错误提示验证
  - 小规模整链路 `--dry_run`
- 另外做了一个最小 CUDA 运算探针, 发现当前 PyTorch 在 Blackwell 上还存在更底层的运行阻塞.

### 总结感悟
- 这次 `PermissionError` 是一个真实 bug, 但它不是终点.
- 修掉命令里的 `/root/.cache` 之后, 才真正暴露出更底层的环境问题: 当前 PyTorch 还跑不动 Blackwell 的 CUDA kernel.
- 所以这轮结果不是“命令彻底恢复可跑”, 而是“第一层错误已修正, 第二层阻塞已被动态证据确认”.

## [2026-03-25 21:23:12 UTC] [Session ID: moge_permission_20260325] 任务名称: 借现成本机 `cu128` 环境推进 `my7` 小规模真实验证

### 任务内容
- 在 VerseCrafter 自己的 `py311 + torch 2.3.1` 环境暂时无法升级成功的前提下, 借本机其他环境先验证 `my7` 的小规模真实链路.
- 继续排查为什么真实运行卡在模型下载, 并把现象收敛到最小阻塞点.

### 完成过程
- 动态验证了三套现成环境:
  - `torch 2.6.0+cu124` 仍不支持 Blackwell.
  - `torch 2.7.0+cu128` 支持.
  - `torch 2.10.0+cu128` 支持.
- 选择 `video_to_world` 的 `torch 2.10.0+cu128` 环境作为临时验证底座.
- 为该环境建立了最小 overlay, 让它能导入 VerseCrafter 所需的:
  - `transformers`
  - `diffusers`
  - `accelerate`
  - `moge`
  - `utils3d`
  - `tokenizers`
  - `regex`
  - `huggingface_hub`
- 用这套环境成功跑通了用户命令的 `--dry_run`, 并确认:
  - 只跑 `preset 0`
  - `sample_size 360,640`
  - `num_inference_steps 4`
  - `moge_pretrained` 已改成 `Ruicheng/moge-2-vitl`
- 真实运行时又定位到新的最小阻塞:
  - 全局代理环境变量会把 Hugging Face 下载卡住
  - 去掉代理后, `Ruicheng/moge-2-vitl/model.pt` 能开始下载, 但外网大文件链路仍不稳定

### 总结感悟
- 这轮最大的价值, 不是“已经跑完视频”, 而是把验证路径从“必须先装好 VerseCrafter 的新 torch”缩短成了“先借现成 `cu128` 环境做真实链路探针”.
- 当前最小阻塞点已经非常明确:
  - 不是代码
  - 不是 Blackwell 支持判断
  - 而是 `moge-2-vitl` 这份 1.3 GB 权重的大文件下载稳定性

## [2026-03-25 22:04:18 UTC] [Session ID: moge_permission_20260325] 任务名称: 固化本地 `model.pt` 专用下载脚本

### 任务内容
- 按用户选择的“先拿当前用户可读本地 `model.pt`”路径, 为 `Ruicheng/moge-2-vitl` 落一个专用下载脚本.
- 把大文件下载从“整文件长时间挂住”改成“镜像 + 小块 Range + 可重复推进”.

### 完成过程
- 新增脚本:
  - `scripts/download_moge_2_vitl_checkpoint.sh`
- 脚本职责:
  - 默认走 `hf-mirror`
  - 显式取消代理
  - 按 `4 MB` 分块下载
  - 只在整块成功后才追加到本地 `.part`
  - 落点固定为:
    - `~/.cache/huggingface/local-moge-2-vitl/model.pt.part`
- 先验证了 `hf-mirror` 的 `206 Range` 请求是通的.
- 再通过脚本把 partial 从约 `230 MB` 推进到了约 `415 MB`.

### 总结感悟
- 当前已经不需要再围绕 `/root/.cache` 或 Hugging Face cache 内部结构折腾.
- 下载逻辑现在变成了一个可重复调用、可观察进度、可在后续继续接跑的稳定工具.
