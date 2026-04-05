# 错误修复记录: `moge_pretrained` 权限路径与小规模验证

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] 问题: `--moge_pretrained` 指向 `/root/.cache/...` 导致 Step 1 直接失败

### 现象
- 用户执行 `single_image_multi_trajectory.py` 时, 日志先出现 Blackwell `sm_120` warning.
- 真正 traceback 停在:
  - `Path(pretrained_model_name_or_path).exists()`
  - `PermissionError: [Errno 13] Permission denied: '/root/.cache/.../model.pt'`

### 原因
- 当前进程用户是 `rais`, 不是 `root`.
- 原命令把 `--moge_pretrained` 写成了 root 私有缓存目录下的模型路径.
- 对这种路径, `Path.exists()` 本身就会抛权限异常, 还没进入真正的模型加载阶段.

### 修复
- 在 `inference/moge-v2_infer.py` 中增加 `resolve_pretrained_model_reference()`:
  - 对本地路径先做 `expanduser()`
  - 对 `/root/.cache/...` 这类不可访问路径提前抛出更明确的提示
  - 对不存在的本地文件提示改用 `Ruicheng/moge-2-vitl` 这类 HF repo id
- 在 `inference/single_image_multi_trajectory.py` 中把 `--moge_pretrained` 的 help 文案改得更明确.
- 在 `cmd.md` 中把多处 `/root/.cache/.../model.pt` 示例替换为更稳妥的 repo id 写法.

### 验证
- `py_compile` 通过.
- 直接执行带坏路径的 `moge-v2_infer.py` 后, 已输出新的清晰报错:
  - 明确指出 `/root/.cache/...` 对当前用户不可读
  - 明确建议改用 `~/.cache/.../model.pt` 或 `Ruicheng/moge-2-vitl`
- 小规模整链路 `--dry_run` 已确认新的命令展开正确.

### 后续发现
- 在修掉这层路径问题后, 最小 CUDA 运算探针又确认:
  - 当前 `torch 2.3.1` 在 Blackwell `sm_120` 上会报 `no kernel image is available for execution on the device`
- 因此当前真实 GPU 运行仍被 PyTorch / Blackwell 兼容性阻塞.

## [2026-03-25 21:23:28 UTC] [Session ID: moge_permission_20260325] 问题: `my7` 小规模真实运行卡在 `moge-2-vitl` 权重下载

### 现象
- 借现成 `cu128` 环境后, `single_image_multi_trajectory.py` 的 `dry_run` 已通过.
- 真实运行进入 `moge-v2_infer.py` 之后, 没有立刻触发 CUDA 报错, 而是卡在 Hugging Face 模型下载阶段.
- 带全局代理时:
  - `~/.cache/huggingface/.../blobs/...incomplete` 长时间停在 `0` 字节
- 去掉代理后:
  - 下载能推进到 `125 MB`
  - 后续又会停住

### 原因
- 当前 shell 残留了全局代理:
  - `http_proxy=http://127.0.0.1:7897`
  - `https_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 这会把 Hugging Face 的大文件请求带到一个并不稳定的链路上.
- 即使明确取消代理, 当前外网到 `moge-2-vitl/model.pt` 的 1.3 GB 大文件下载也仍然会中途卡住.

### 修复 / 绕行尝试
- 已明确把 Hugging Face 探针切成:
  - `env -u http_proxy -u https_proxy -u all_proxy ...`
- 已把“整条流水线下载模型”拆成“先单独直连下载模型, 再重跑流水线”.
- 已尝试两种续传方式:
  - `hf_hub_download`
  - `curl -C -`
- 目前能确认:
  - 直连比误走代理更好
  - 但链路仍然不够稳定, 暂未下载完成

### 验证
- `model_info("Ruicheng/moge-2-vitl")` 在去代理后可以秒回.
- `model.pt` 的远端大小已确认:
  - `1305030700`
- 当前本地已成功积累过的 partial 体积:
  - `125829120`
  - `157286400`
- 说明这不是 repo id 错误, 也不是鉴权错误, 而是单纯的大文件下载稳定性问题.
