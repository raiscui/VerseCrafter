# 关键洞察: `moge_pretrained` 权限路径与 Blackwell 小规模验证

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] 主题: 修掉上层参数错误后, 反而更快暴露出底层环境阻塞

### 发现来源
- 本轮先修正 `--moge_pretrained /root/.cache/...` 权限路径, 再做最小 CUDA 动态验证.

### 核心问题
- 用户表面上看到的是一条 `PermissionError`.
- 但这只是第一层问题.
- 真正决定这条链能不能在当前机器上跑通的, 是下面那层:
  - 当前 `torch 2.3.1` 对 Blackwell `sm_120` 还不能执行基础 CUDA kernel.

### 为什么重要
- 如果只停留在“把 `/root/.cache` 改掉了”这个层面, 很容易误以为问题已经解决.
- 实际上继续跑下去还会立刻撞上更底层的 CUDA 兼容性错误.

### 未来风险
- 后续任何依赖 CUDA 的步骤, 包括 MoGe、rendering、VerseCrafter generation, 都可能在这台机器上继续失败.
- 如果不先解决 PyTorch / Blackwell 兼容性, 再多上层参数微调都只是绕圈.

### 当前结论
- 第一层错误:
  - `/root/.cache/...` 路径对 `rais` 用户不可读
  - 已修正并给出更清晰的错误提示
- 第二层错误:
  - 当前 PyTorch 在 Blackwell 上 `no kernel image is available for execution on the device`
  - 这才是当前真实 GPU 跑不起来的硬阻塞

### 后续讨论入口
- 下次继续时优先看:
  - `LATER_PLANS__moge_permission.md`
  - `notes__moge_permission.md`
  - `inference/moge-v2_infer.py`
