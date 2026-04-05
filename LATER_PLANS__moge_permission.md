# 后续计划: `moge_pretrained` 权限路径与小规模验证

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] 处理 Blackwell 上的 PyTorch 兼容性
- 现状:
  - 本地路径权限问题已经修正.
  - 但当前 `torch 2.3.1` 在 Blackwell `sm_120` 上连基础 CUDA matmul 都会报:
    - `no kernel image is available for execution on the device`
- 建议:
  - 优先把 Pixi 里的 PyTorch 升到真正支持 Blackwell `sm_120` 的版本, 再继续做 `my7` 的真实 GPU 测试.
  - 升级后先做最小 CUDA 张量运算探针, 再重跑 `moge-v2_infer.py` 小测试, 最后再回到整条 `single_image_multi_trajectory.py`.
- 价值:
  - 这样能先把最底层环境打通, 避免继续在上层命令参数上反复消耗时间.

## [2026-03-25 21:23:44 UTC] [Session ID: moge_permission_20260325] 处理 `moge-2-vitl` 大文件权重的长期解决方案
- 现状:
  - 代码层面的路径问题和 Blackwell 支持边界都已经查清.
  - 当前实际最慢的部分是 `Ruicheng/moge-2-vitl/model.pt` 的 1.3 GB 下载稳定性.
- 建议:
  - 如果后续能拿到 root 权限, 最快路径是把 root 用户已经存在的 Hugging Face 缓存(如果确实存在)复制到当前用户自己的 `~/.cache`.
  - 如果不走 root 路线, 更稳的是给项目准备一份当前用户可读的本地模型落点, 例如:
    - `~/.cache/huggingface/local-moge-2-vitl/model.pt`
  - 然后命令显式传:
    - `--moge_pretrained ~/.cache/huggingface/local-moge-2-vitl/model.pt`
- 价值:
  - 这样可以把“每次试跑都可能卡在外网大文件下载”变成“一次准备, 后续复用”.
