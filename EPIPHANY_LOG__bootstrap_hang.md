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

## [2026-03-25 11:40:00 UTC] [Session ID: bootstrap_hang_20260325_followup] 主题: 已有 Pixi 环境里继续用 build isolation, 会把“复验”变成“重复装机”

### 发现来源
- 本轮对 `pixi run bootstrap` 做入口复验时, `install-grounded-sam2` 重新拉取隔离构建依赖的动态证据.

### 核心问题
- 当 Pixi 已经提供了 `torch`、`setuptools`、CUDA 运行时后, editable 安装如果仍默认 build isolation, `pip` 可能再去拉一整套大体积 wheel.
- 这会让“我只是想复验一下入口命令”退化成“又走了一遍半个装机流程”.

### 为什么重要
- 这不只是慢.
- 它会直接消耗代理流量, 还会把真正的问题点藏起来, 让人误以为是别的步骤挂住了.

### 未来风险
- 后续如果 `bootstrap` 再加入更多 pyproject editable 包, 只要默认 build isolation 没被约束, 这种重复下载会继续出现.
- 对带代理约束的远程 GPU 机器来说, 这会显著恶化维护体验.

### 当前结论
- 本轮已经用 `install-grounded-sam2 -> --no-build-isolation` 证实:
  - 现有 Pixi 环境足够支持它完成 editable 构建.
  - 重复下载大包并不是必要成本.

### 后续讨论入口
- 下次如果要继续清理 bootstrap 入口的重复安装问题, 先看:
  - `pixi.toml`
  - `README.md`
  - `LATER_PLANS__bootstrap_hang.md`

## [2026-03-31 09:06:00 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] 主题: 安装脚本里的“环境敏感 preflight”不该先于“已满足状态短路”

### 发现来源
- 本轮排查 `pixi run install-flash-attn` 时, 用户遇到 GPU 架构自动探测失败.
- 继续验证后发现 `flash-attn 2.8.3` 其实已经在 Pixi 环境里安装完成.

### 核心问题
- 如果安装脚本先做 GPU / 权限 / 网络之类的环境敏感 preflight, 再判断“依赖是否其实已经满足”, 那么:
  - 已安装场景也会被误判成失败
  - 幂等入口就失去了“多跑一次也安全”的性质

### 为什么重要
- 这类问题很隐蔽.
- 用户看到的是“某个探测失败”, 但真正被破坏的是命令的幂等性.
- 之后再排查时, 很容易把焦点放到 GPU、驱动、容器挂载, 反而忽略“其实根本不需要重装”.

### 当前结论
- 对安装类任务, 更稳的默认顺序应该是:
  - 先检查当前状态是否已经满足
  - 再做昂贵或环境敏感的前置校验
- 本轮已经在 `scripts/install_flash_attn.sh` 上用真实动态证据验证了这条规律.

### 后续讨论入口
- 后续如果继续整理 `bootstrap` 子任务, 可以优先筛查:
  - 是否还有别的安装脚本先做重型 preflight, 后做“已安装短路”
  - 是否需要把这种顺序约束补进公共脚本规范

## [2026-03-31 11:34:19 UTC] [Session ID: codex-20260331T112445Z-45312] 主题: 重型源码安装任务应先做“已安装短路”, 再做 repo / toolchain / CUDA 探测

### 发现来源
- 本轮 `install-pytorch3d` 入口改造.
- 历史上 `install-flash-attn` 也出现过“前置探测比真正安装语义更先失败”的同类问题.

### 核心问题
- 如果脚本一上来就去:
  - 同步仓库
  - 探测 GPU 架构
  - 准备 toolchain
  - 重新触发编译
- 那么一个本来已经满足的环境, 会被重复重编译和前置探测噪音重新拖回故障态.

### 为什么重要
- 这会让排查失真.
- 人会误以为“当前安装入口仍有问题”, 其实真正的问题可能只属于“强制重装路径”.

### 当前结论
- 对 `flash-attn`、`pytorch3d` 这类重型依赖安装器, 更稳的顺序应该是:
  - 先确认目标依赖是否已经满足
  - 只有确实需要重装时, 才进入 repo / compiler / CUDA / arch 的准备逻辑
- 这不是性能优化, 而是排查纪律的一部分.

### 后续讨论入口
- 后续若继续改造其它 `bootstrap` 子任务, 优先检查它们是否也缺“已安装短路”.
