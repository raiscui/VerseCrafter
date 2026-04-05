# 关键洞察: `pixi run bootstrap` 高 CPU

## [2026-03-25 09:52:40 UTC] [Session ID: bootstrap_hang_20260325] 主题: Opaque bootstrap alias 会把“正在编译”伪装成“Pixi 卡死”

### 发现来源
- 本次对 `pixi run bootstrap` 高 CPU 现象的静态阅读与 dry-run 验证.

### 核心问题
- 一个名为 `bootstrap` 的入口太抽象.
- 但它实际串联了多个本地源码构建任务, 其中至少包含多个 C++ / CUDA 扩展编译.
- 用户看到的却只是:
  - 一个总任务名
  - 高 CPU
  - 不一定及时出现的阶段反馈

### 为什么重要
- 这会把正常但昂贵的“构建行为”误诊成“工具死循环”或“Pixi 假死”.
- 误诊后, 很容易把排查方向带到 Pixi 本身, 而不是具体的编译热点.

### 未来风险
- 后续如果继续往 `bootstrap` 里叠更多源码安装步骤, 首次装机体验会继续恶化.
- 一旦某台机器 CPU / 内存较紧, 用户甚至可能在构建阶段直接把终端或桌面拖慢.

### 当前结论
- 当前证据支持:
  - `bootstrap` 不是递归调用导致的明显死循环.
  - 它更像是“多个高成本源码构建步骤被一个抽象别名掩盖”.
- 仍未确认的部分:
  - 在用户那台具体机器上, 最重的瓶颈究竟是 `flash-attn`、`pytorch3d` 还是 `grounding_dino`.

### 后续讨论入口
- 下次如果要真正改善体验, 先看:
  - `pixi.toml`
  - `README.md`
  - `LATER_PLANS__bootstrap_hang.md`
