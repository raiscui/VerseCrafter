# 任务计划: `pixi run bootstrap` 高 CPU 排查

## [2026-03-25 09:49:30 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 建立排查计划

### 目标
- 在不直接执行 `pixi run bootstrap` 的前提下, 解释它为什么会出现高 CPU 且像“卡死”的表现.

### 阶段
- [x] 阶段1: 回读默认上下文与 README / `pixi.toml`
- [x] 阶段2: 用最小动态验证确认 `bootstrap` 实际任务链
- [x] 阶段3: 归纳候选原因并区分“已验证结论”与“仍待验证项”
- [x] 阶段4: 形成交付说明与后续建议

### 关键问题
1. `bootstrap` 本身有没有递归调用 `pixi` 或死循环迹象?
2. 高 CPU 更像是卡死, 还是本地 C++ / CUDA 扩展源码编译?
3. 哪几个子任务最可能贡献主要 CPU 占用?

### 做出的决定
- 决定1: 不直接运行 `pixi run bootstrap`, 只做 dry-run 与静态阅读.
- 决定2: 先看任务链, 再看每个子任务的安装方式与扩展编译行为.

### 当前状态
- **目前在阶段4**: 已完成证据收集与结论整理, 正准备向用户交付排查结果.

## [2026-03-25 09:52:40 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 阶段收束

### 已验证结论
- `bootstrap` 是顺序任务链, 不是递归 `pixi` 调用.
- 任务链里包含多个源码安装 / 本地扩展编译步骤.
- 当前最可能导致高 CPU 的热点是:
  - `install-flash-attn`
  - `install-pytorch3d`
  - `install-grounding-dino`
  - `install-grounded-sam2`

### 仍待动态确认的点
- 若未来需要进一步精确定位, 需要在真实执行时按子任务逐个观察, 看具体卡在哪一步.

### 交付策略
- 对用户明确区分:
  - 已观察事实
  - 当前结论
  - 还没有直接运行证据支撑的剩余不确定项

## [2026-03-25 09:58:20 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 聚焦 `install-flash-attn`

### 新现象
- 用户反馈当前更怀疑 `install-flash-attn` 是卡住点.

### 当前假设
- 主假设: 当前环境组合拿不到合适的 `flash-attn` 预编译 wheel, 因而退回到本地源码编译, 导致长时间高 CPU.
- 备选解释: wheel 本来可用, 但本机工具链 / `ninja` / `nvcc` / 内存条件让源码编译阶段特别慢, 所以看起来像挂死.

### 验证计划
- 先读取本机 Pixi 环境里的 Python / PyTorch / CUDA / `ninja` 版本.
- 再检查 `flash-attn` 当前发布信息与 wheel 可用性线索.
- 不直接运行 `install-flash-attn`, 继续保持“只读 + 最小网络查询”策略.

### 当前状态
- **目前在补充验证**: 正在确认 `flash-attn` 是否属于“无 wheel 退源码编译”场景.

## [2026-03-25 10:03:50 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: `install-flash-attn` 结论收束

### 已验证结论
- 当前默认解析到的 `flash-attn` 版本为 `2.8.3`.
- 官方 PyPI 上该版本只有源码包, 没有 wheel.
- 当前机器具备 `ninja`、多核 CPU 与 `nvcc 12.8`, 会真正进入高并行本地编译.
- 因而 `install-flash-attn` 的“100% CPU 像卡死”更符合“源码编译中”的表现.

### 仍待确认的点
- 若后续要进一步量化, 可在真实运行时观察:
  - 是否出现 `ninja`
  - 是否出现 `build_ext`
  - 是否出现 `nvcc` / `c++`
  - 单步耗时多久

### 当前状态
- **本轮排查已可交付**: 已将问题从“怀疑 flash-attn”收敛到“默认安装路径就是源码编译”.

## [2026-03-25 10:09:20 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 执行限流改造

### 目标
- 修改 `install-flash-attn` 任务, 默认在编译时至少预留 4 个 CPU.
- 保留可调入口, 避免把限流值写死到无法覆盖.
- 同步补齐 `.envrc` 与 README 说明, 减少后续误判.

### 计划
- 在 `pixi.toml` 中为 `install-flash-attn` 增加计算逻辑:
  - 默认读取 `FLASH_ATTN_RESERVED_CPUS`
  - 未设置时默认为 `4`
  - 计算 `MAX_JOBS = max(nproc - reserve, 1)`
- 新增 `.envrc` 默认值与中文注释.
- 更新 `README.md`, 明确说明 flash-attn 会限流编译.

### 当前状态
- **目前在执行修改**: 正在编辑 `pixi.toml`、`.envrc` 与 `README.md`.
