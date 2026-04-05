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

## [2026-03-25 10:12:10 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 限流改造完成

### 已完成
- 已修改 `pixi.toml`, 为 `install-flash-attn` 增加默认限流逻辑.
- 已新增 `.envrc`, 提供 `FLASH_ATTN_RESERVED_CPUS=4` 默认值.
- 已更新 `README.md`, 说明默认会保留 4 个 CPU.
- 已完成验证:
  - `pixi run --dry-run --frozen install-flash-attn`
  - `direnv allow` + `direnv exec ...`

### 验证结论
- 新任务定义可以被 Pixi 正常解析.
- 当前机器 `22` 核时会自动算出 `MAX_JOBS=18`.
- 这满足“保留至少 4 个 CPU”的目标.

### 当前状态
- **本轮修改已完成**: 可以向用户交付改动与验证结果.

## [2026-03-25 10:20:10 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 执行 `pixi run bootstrap`

### 新目标
- 按用户要求实际运行 `pixi run bootstrap`.
- 网络默认先直连探测, 只有确认网络问题时才临时启用代理.
- 继续保留本轮新增的 `flash-attn` 限流逻辑, 避免整机被重新打满.

### 验证计划
- 先做最小网络探测:
  - PyPI 镜像
  - GitHub 上 `MoGe` 与 `pytorch3d` 仓库可达性
- 若直连正常:
  - 用 `direnv exec` 保证 `.envrc` 生效后直接运行 `pixi run bootstrap`
- 若直连失败:
  - 再临时注入用户提供的 `http_proxy` / `https_proxy` / `all_proxy`

### 当前状态
- **目前在执行前检查**: 正在确认是否真的需要代理.

## [2026-03-25 10:33:10 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 代理纠偏

### 现象
- 当前 shell 预设了:
  - `https_proxy=http://127.0.0.1:7897`
  - `http_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 虽然本轮没有手动设置代理, 但第一次 `bootstrap` 实际已经沿用了这些环境变量.

### 决定
- 按用户要求停止这轮走代理的安装.
- 接下来改为显式 `unset http_proxy https_proxy all_proxy`, 再重新运行 `bootstrap`.

### 当前状态
- **目前在重新验证直连**: 准备无代理重跑.

## [2026-03-25 10:40:40 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 直连回退到代理

### 已观察事实
- 无代理时:
  - 小流量网络探测正常
  - 但 `install-moge` 的 `git clone` 在 `git-remote-https` / `index-pack` 阶段卡住超过 6 分钟
  - pack 临时文件不再继续增长

### 决定
- 认定当前“真正执行 bootstrap 的网络路径”仍存在问题.
- 按用户给的规则, 重新启用代理继续跑 `bootstrap`.

### 当前状态
- **目前准备重启**: 将停止无代理版本, 再用代理环境继续执行.

## [2026-03-25 10:49:20 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 修复 `install-flash-attn` 任务解析错误

### 现象
- `bootstrap` 已成功跑过:
  - `install-moge`
  - `install-grounded-sam2`
  - `install-grounding-dino`
- 进入 `install-flash-attn` 时, Pixi 报错:
  - `failed to parse shell script`
  - `Failed parsing command substitution in double quoted string`

### 判断
- 这是我们刚才把复杂 Bash 逻辑直接内嵌进 Pixi task 后, 被 `deno_task_shell` 预解析触发的语法兼容问题.
- 问题在任务定义层, 不是 `flash-attn` 本身.

### 修复计划
- 把 `install-flash-attn` 的计算逻辑移到独立 shell 脚本文件.
- Pixi task 改成只负责调用脚本, 避免再次被内联解析器误伤.
- 修复后重新验证 `install-flash-attn`, 再继续执行剩余安装步骤.

### 当前状态
- **目前在修任务定义**: 正在把内联脚本外提到独立文件.

## [2026-03-25 18:52:30 UTC] [Session ID: bootstrap_hang_20260325_single_arch] [记录类型]: 继续处理 `install-flash-attn` 单架构化

### 新目标
- 停止上一轮仍在运行的 `flash-attn` 多架构源码编译, 避免继续浪费 CPU.
- 把 `install-flash-attn` 改成默认只编当前机器所需架构, 不再一次编译多套 CUDA 目标.
- 在单架构模式下重新执行 `install-flash-attn`, 成功后继续完成 `install-pytorch3d`.

### 当前现象
- 现场仍有残留 `cicc` 进程, 且参数里可见 `compute_90`、`compute_100` 等多架构目标.
- 用户最新要求很明确: 不需要多个版本, 只需要当前机器专用版本.

### 当前假设
- 主假设: 仅设置 `MAX_JOBS` 只能限并发, 不能限制目标架构集合, 所以 `flash-attn` 仍会按默认策略编译多套架构.
- 备选解释: 当前 PyTorch / CUDA 环境对 Blackwell 的识别不完整, 即便设了单架构变量, 上游构建逻辑也可能回退到一组保守默认架构.

### 验证计划
- 先彻底停掉残留编译进程.
- 再读取本地脚本与上游构建逻辑, 确认 `TORCH_CUDA_ARCH_LIST` 或等价变量的生效方式.
- 最后修改脚本并重新执行, 用真实编译日志验证是否只剩单一目标架构.

### 当前状态
- **目前在阶段3**: 正在做“止血 + 单架构验证”的正式修复.

## [2026-03-25 18:58:40 UTC] [Session ID: bootstrap_hang_20260325_single_arch] [记录类型]: 单架构脚本已落地, 进入验证阶段

### 已完成
- 已停止上一轮残留的 `flash-attn` 多架构编译进程.
- 已将 `scripts/install_flash_attn.sh` 改成:
  - 默认保留至少 4 个 CPU
  - 默认自动探测当前 GPU 架构
  - 默认只给 `flash-attn` 传入单一 `FLASH_ATTN_CUDA_ARCHS`
- 已同步更新 `.envrc` 与 `README.md`.

### 下一步验证
- 先做脚本语法检查与 dry-run 级检查.
- 再用代理环境真实执行 `pixi run install-flash-attn`, 观察是否只剩单一目标架构.
- 成功后继续执行 `pixi run install-pytorch3d`.

### 当前状态
- **目前在阶段4**: 正在验证单架构编译是否真正生效.

## [2026-03-25 19:15:30 UTC] [Session ID: bootstrap_hang_20260325_single_arch] [记录类型]: `flash-attn` 单架构安装完成

### 已验证结果
- `install-flash-attn` 已安装成功.
- `FLASH_ATTN_CUDA_ARCHS=120` 的单架构策略已经生效.
- 真实编译过程中只观察到 `compute_120`.

### 下一步
- 使用代理继续执行 `pixi run install-pytorch3d`.
- 完成后补齐本轮 `WORKLOG__bootstrap_hang.md` 与 `ERRORFIX__bootstrap_hang.md`.

### 当前状态
- **目前在阶段4**: 正在完成 `bootstrap` 的最后一个剩余子任务.

## [2026-03-25 19:27:10 UTC] [Session ID: bootstrap_hang_20260325_single_arch] [记录类型]: `pytorch3d` 下载路径优化后重试

### 新现象
- 原始 `install-pytorch3d` 在代理下做全量 clone 过慢, 5 分钟以上仍停留在约 20% 左右.

### 决定
- 将 `install-pytorch3d` 外提到独立脚本.
- 改为优先使用 shallow clone + blob filter, 以减少代理流量和首次装机等待时间.

### 当前状态
- **目前在阶段4**: 准备按新下载策略重新执行 `install-pytorch3d`.

## [2026-03-25 11:25:55 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: 接管续跑并核对当前安装状态

### 当前现象
- 代理环境下的 `install-pytorch3d` 会话 `37979` 仍在持续推进.

## [2026-03-31 08:57:20 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] [记录类型]: 继续处理 `install-flash-attn` 探测失败

### 新现象
- 用户这次执行 `pixi run install-flash-attn` 时, 没有进入编译阶段.
- 当前直接失败在脚本的 GPU 架构自动探测阶段, 输出:
  - `[install-flash-attn] 无法自动探测 GPU 架构. 请手动设置 FLASH_ATTN_CUDA_ARCHS, 例如 120.`

### 现象 -> 假设
- 已观察现象:
  - CPU 限流逻辑已执行并打印 `cpu_total=1, reserved=4, MAX_JOBS=1`.
  - 失败点是 `FLASH_ATTN_CUDA_ARCHS` 自动探测.
- 当前主假设:
  - 这次运行环境里, `pixi` 子进程看不到可用 GPU, 因而 `torch.cuda.is_available()` 与 `nvidia-smi --query-gpu=compute_cap` 两条探测路径都返回空.
- 最强备选解释:
  - GPU 实际可见, 但当前 `nvidia-smi` 输出格式或 `torch` 行为和脚本假设不一致, 导致解析失败.

### 验证计划
- 先最小复现脚本中的两条探测路径:
  - `pixi run python` 下的 `torch.cuda` 探针
  - `nvidia-smi --query-gpu=compute_cap --format=csv,noheader`
- 再根据动态证据决定:
  - 如果是环境问题, 给出立即可用的运行方式.
  - 如果是脚本退化, 直接修脚本并回归验证.

### 当前状态
- **目前在阶段2/3之间**: 正在补充动态证据, 确认探测失败的真实原因.

## [2026-03-31 09:03:10 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] [记录类型]: 修复完成并验证通过

### 已验证结论
- 当前环境里的 `torch.cuda.is_available()` 为 `False`, `torch.cuda.device_count()` 为 `0`.
- `/usr/bin/nvidia-smi` 当前不可执行, 且没有 `/dev/nvidia*` 设备节点.
- 但 `pixi` 环境里 `flash-attn 2.8.3` 已经安装完成.
- 因此本次失败并不是“安装步骤坏了”, 而是脚本在“已安装短路”之前就做了 GPU 架构探测.

### 已完成修复
- 在 `scripts/install_flash_attn.sh` 里增加“已安装短路”:
  - 先检测 `flash-attn` 发行版元数据
  - 若已存在, 直接成功返回
- 同时补充自动探测失败时的诊断输出, 让后续能直接看到:
  - `torch.cuda` 状态
  - `nvidia-smi` 可执行性
  - `/dev/nvidia*` 设备节点情况

### 回归验证
- `bash -n scripts/install_flash_attn.sh`
- `pixi run bash ./scripts/install_flash_attn.sh`
- `pixi run install-flash-attn`
- `pixi run python` 读取 `flash-attn` 版本元数据

### 当前状态
- **目前在阶段4**: 修复与验证已完成, 正在整理交付与后续建议.

## [2026-03-31 10:13:35 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_cpu_limit_11606] [记录类型]: 继续处理 `install-pytorch3d` 编译打满 CPU

### 新现象
- 用户执行 `install-pytorch3d` 时遇到:
  - `RuntimeError: Error compiling objects for extension`
  - `Failed building wheel for pytorch3d`
- 用户同时明确反馈: 编译阶段会把 CPU 吃得像“卡死”, 希望不要用完整机 CPU.

### 现象 -> 假设
- 已观察现象:
  - 当前 `scripts/install_pytorch3d.sh` 只有浅克隆与 `pip install`, 没有任何 CPU 限流逻辑.
  - 本地 PyTorch `torch.utils.cpp_extension` 明确支持通过 `MAX_JOBS` 控制 ninja worker 数.
- 当前主假设:
  - 当前入口没有给 `pytorch3d` 构建传入并发上限, 所以编译会按 ninja 默认策略尽量吃满可用 CPU.
- 最强备选解释:
  - 即使限流后, 这次 `Error compiling objects for extension` 仍可能来自别的编译错误, 只是 CPU 打满让体感更差.

### 验证计划
- 先给 `install-pytorch3d` 补上与 `flash-attn` 一致的默认 CPU 预留策略.
- 再做脚本语法验证与 dry-run / 轻量执行验证, 确认新的并发变量确实被导出.
- 若用户后续继续跑到编译失败, 再基于新的日志继续定位真实编译错误.

### 当前状态
- **目前在阶段3**: 正在实施 `pytorch3d` CPU 限流改造.

## [2026-03-31 10:17:20 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_cpu_limit_11606] [记录类型]: 限流改造完成并验证通过

### 已验证结论
- 旧 `install-pytorch3d` 入口没有 CPU 并发限制.
- `pytorch3d/setup.py` 默认走 `torch.utils.cpp_extension.BuildExtension`.
- 本地 PyTorch 源码明确支持 `MAX_JOBS` 控制 ninja worker 数.

### 已完成修复
- 在 `scripts/install_pytorch3d.sh` 中加入与 `flash-attn` 对齐的 CPU 预留策略:
  - 默认读取 `PYTORCH3D_RESERVED_CPUS`
  - 未设置时默认为 `4`
  - 计算 `MAX_JOBS = max(nproc - reserve, 1)`
- 在进入 `pip install` 前同时导出:
  - `MAX_JOBS`
  - `CMAKE_BUILD_PARALLEL_LEVEL`
- 在 `.envrc` 中新增 `PYTORCH3D_RESERVED_CPUS` 默认值.
- 在 `README.md` 中补充 `install-pytorch3d` 的限流说明.

### 回归验证
- `bash -n scripts/install_pytorch3d.sh`
- 使用 fake `python` 包装器验证:
  - 默认路径会导出计算后的 `MAX_JOBS`
  - 手动 `MAX_JOBS=3` 会被原样透传

### 当前状态
- **目前在阶段4**: 限流修复已完成. 如果用户后续仍遇到 `Error compiling objects for extension`, 下一步应继续抓取更早的编译错误行定位真正的编译失败原因.

## [2026-03-31 10:21:40 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] [记录类型]: 停止后台编译并按限流参数重启

### 新目标
- 用户明确要求停止当前后台 `pytorch3d` 编译.
- 重新启动时使用固定的限流参数, 避免再次把 CPU 吃满.

### 执行计划
- 先定位当前 `pixi` / `pip` / `ninja` / `c++` / `pytorch3d` 相关进程.
- 确认进程树后优先结束对应父进程或整个进程组, 避免只杀掉外层留下一堆子进程.
- 再用固定 `MAX_JOBS` 重启 `pixi run install-pytorch3d`.

### 当前状态
- **目前在阶段3**: 正在做“止血 + 限流重启”.

## [2026-03-31 10:23:40 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] [记录类型]: 限流重启已生效

### 已观察事实
- 当前没有残留的 `install-pytorch3d` / `ninja` / `gcc` / `cc1plus` 后台编译进程.
- 已按固定并发重新启动:
  - `env MAX_JOBS=1 pixi run install-pytorch3d`
- 真实进程链已经显示:
  - `python -m pip install --no-build-isolation ./pytorch3d`
  - `ninja -v -j 1`
  - 单个 `cc1plus` 编译进程

### 当前结论
- “停止旧后台编译并重新按限流参数启动”这一步已经完成.
- 当前编译不再是多 worker 抢占 CPU, 而是单 worker 受控编译.

### 当前状态
- **目前在阶段4**: 正在观察这一轮受控编译是否继续推进或暴露更早的真实编译错误.

## [2026-03-31 10:26:40 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] [记录类型]: 受控编译已结束, 暴露出新的失败信号

### 已观察事实
- 这轮 `env MAX_JOBS=1 pixi run install-pytorch3d` 已经结束.
- 失败关键信息是:
  - `Using envvar MAX_JOBS (1) as the number of workers...`
  - `c++: fatal error: Killed signal terminated program cc1plus`
  - `RuntimeError: Error compiling objects for extension`
- 当前没有残留编译进程.
- 现有 Pixi 环境仍能 `import pytorch3d`, 版本为 `0.7.9`.

### 当前结论
- “重新用限制 CPU 的方式开始”这一步已经完成并跑到结束.
- 这轮不是卡住, 而是失败退出.
- 当前主问题已经从“CPU 并发过高”转移到“单 worker 编译时 `cc1plus` 被系统杀掉”.

### 当前状态
- **目前在阶段4**: 已拿到新的根因线索. 下一步若继续排查, 应先查内存 / OOM 证据, 而不是继续调 CPU 并发.

## [2026-03-31 10:31:20 UTC] [Session ID: bootstrap_hang_20260331_sam2_cpu_limit_11606] [记录类型]: 继续处理 `install-grounded-sam2` 的 CPU 限流

### 新现象
- 用户反馈 `Building editable for SAM-2 (pyproject.toml)` 看起来像卡死.
- 当前要确认的不是“是不是一定真卡死”, 而是这条入口默认是否有限制 CPU 并发.

### 现象 -> 假设
- 已观察现象:
  - `install-grounded-sam2` 当前仍是直接执行 `python -m pip install --no-build-isolation -e ./third_party/Grounded-SAM-2`
  - `third_party/Grounded-SAM-2/setup.py` 使用 `torch.utils.cpp_extension.BuildExtension`
  - 本地 PyTorch 源码表明 `BuildExtension` 默认会让 ninja 使用较高并发, 可通过 `MAX_JOBS` 控制
- 当前主假设:
  - 当前 `install-grounded-sam2` 入口没有内建 CPU 限流, 如果进入扩展编译, 默认可能把 CPU 吃得很高.
- 最强备选解释:
  - 用户看到的“卡住”未必发生在编译阶段, 但即便如此, 当前入口没有限流这个事实本身依然成立.

### 验证计划
- 外提独立脚本, 加入与 `flash-attn` / `pytorch3d` 一致的 CPU 预留策略.
- 用脚本语法检查与 fake `python` 包装器验证变量透传, 避免真实重编译.
- 同步更新 `.envrc` 与 `README.md`.

### 当前状态
- **目前在阶段3**: 正在为 `install-grounded-sam2` 增加默认 CPU 限流.
- 已观察到下载从约 `79%` 继续推进到 `100%`, 随后顺利进入:
  - `Processing ./pytorch3d`
  - `Preparing metadata (pyproject.toml)`
  - `Building wheel for pytorch3d`

### 当前判断
- 这轮不再符合“网络阶段卡死”的特征.
- 当前主要阶段已经从 GitHub 下载切换为本地源码编译.

### 下一步
- 继续监控 `37979`, 等待 `pytorch3d` 编译结果.
- 若安装成功, 再补做一次 `pixi run bootstrap` 全链路复验.
- 若编译失败, 记录失败输出并按证据继续修正.

### 当前状态
- **目前在阶段4**: 正在等待 `install-pytorch3d` 编译完成, 准备做 bootstrap 收尾验证.

## [2026-03-25 11:27:19 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: `install-pytorch3d` 安装成功, 准备执行入口复验

### 已验证结果
- `pytorch3d-0.7.9` 已成功构建并安装.
- 当前安装路径已经完成:
  - 浅克隆源码
  - `Preparing metadata`
  - `Building wheel`
  - `Successfully installed pytorch3d-0.7.9`

### 决定
- 按用户要求继续执行 `pixi run bootstrap` 入口命令做最终复验.
- 网络策略沿用前面已验证的判断:
  - 直连对 GitHub 大一点的 clone 不稳定
  - 因此这次入口复验继续使用代理, 只把代理用在确实需要联网的这一步

### 当前状态
- **目前在阶段4**: 正在进行 `bootstrap` 入口收尾验证.

## [2026-03-25 11:31:36 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: 入口复验时发现 `install-grounded-sam2` 重复构建隔离环境

### 现象
- 重新执行 `pixi run bootstrap` 时, 链路已成功推进过 `install-moge`.
- 但在 `install-grounded-sam2` 阶段, `pip` 又启动了隔离构建环境:
  - `pip install --ignore-installed ... setuptools>=62.3.0,<75.9 torch>=2.3.1`
- 动态证据显示它正在下载额外的大轮子, 包括 `nvidia_nccl_cu13` 这类数百 MB 级文件.

### 当前判断
- 这不是 `flash-attn` 或 `pytorch3d` 的问题.
- 主要慢点变成了 SAM2 editable 安装默认启用 build isolation, 导致重复拉取本来已经在 Pixi 环境里的 `torch` / `setuptools`.

### 修正动作
- 已中止这轮会白白消耗代理流量的 `bootstrap` 复验.
- 准备把 `install-grounded-sam2` 改成 `--no-build-isolation`, 再做单步验证和入口复验.

### 当前状态
- **目前在阶段4**: 正在修正 `install-grounded-sam2` 的重复构建环境问题.

## [2026-03-25 11:40:00 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: `bootstrap` 入口复验完成

### 已验证结果
- `pixi run bootstrap` 已完整跑通.
- `install-grounded-sam2` 改为 `--no-build-isolation` 后, 不再重复下载隔离环境里的 `torch` / `nvidia_nccl_cu13`.
- `install-flash-attn` 在入口链路里继续保持:
  - `cpu_total=22, reserved=4, MAX_JOBS=18`
  - 自动探测单架构 `120`
  - `Requirement already satisfied: flash-attn`
- `install-pytorch3d` 成功复用本地浅克隆仓库并重新安装成功.

### 补充验证
- 已执行 Python import 验证:
  - `flash_attn`
  - `pytorch3d`
  - `sam2`
  - `groundingdino`
  - `moge`
- 关键输出显示:
  - `flash_attn 2.8.3`
  - `pytorch3d 0.7.9`

### 当前状态
- **阶段4已完成**: 这条支线的修复与复验已结束, 正在写入 WORKLOG / ERRORFIX 并准备交付.

## [2026-03-25 11:42:39 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: 将 `flash-attn` 单专用架构规则沉淀到 `AGENTS.md`

### 新目标
- 把本轮已经验证过的长期规则写入项目级 `AGENTS.md`.
- 明确要求后续 agent 在处理 `flash-attn` 时保持“当前机器专用单架构”策略, 不要回退到多架构编译.

### 当前判断
- 这条规则已经有足够动态证据支撑.
- 它属于跨会话、跨后续任务都会复用的项目经验, 适合进入 `AGENTS.md`.

### 当前状态
- **目前在收尾补充**: 正在更新 `AGENTS.md` 与对应工作记录.

## [2026-03-25 11:42:39 UTC] [Session ID: bootstrap_hang_20260325_followup] [记录类型]: 支线索引 - `__moge_permission`

### 启用原因
- 新问题已经从 `bootstrap` 安装链路切换到运行期的 `MoGe --moge_pretrained` 权限路径与 Blackwell 运行验证.
- 为避免继续污染 `__bootstrap_hang` 上下文, 这一轮改用独立支线文件:
  - `task_plan__moge_permission.md`
  - `notes__moge_permission.md`
  - `WORKLOG__moge_permission.md`
  - `LATER_PLANS__moge_permission.md`
  - `EPIPHANY_LOG__moge_permission.md`
  - `ERRORFIX__moge_permission.md`

## [2026-03-31 11:26:10 UTC] [Session ID: codex-20260331T112445Z-45312] [记录类型]: 继续处理 `install-pytorch3d` 的 Blackwell / 新 CUDA 构建兼容性

### 新现象
- 用户再次反馈 `install-pytorch3d` 失败, 并补充了一个在 RTX 50 系列 / CUDA 12.8+ 上可工作的上游来源构建方案.
- 当前仓库脚本虽然已经具备:
  - 浅克隆
  - CPU 限流
- 但仍缺少:
  - `stable` 源码引用控制
  - system compiler 显式绑定
  - `CUDA_HOME` 明确传递
  - `TORCH_CUDA_ARCH_LIST` 等新卡相关构建环境

### 已观察事实
- 当前 `scripts/install_pytorch3d.sh` 仍默认克隆 `main`, 而不是 PyTorch3D 官方安装文档里提到的 `@stable`.
- 当前 Pixi 环境是:
  - `torch 2.3.1`
  - `torch.version.cuda = 12.1`
- 本机当前 shell 下 `torch.cuda.is_available() = False`, 所以无法直接在这台机器上动态复现用户的 Blackwell 现场.
- 历史动态证据显示, 本机上一轮受控编译失败时的直接信号是:
  - `c++: fatal error: Killed signal terminated program cc1plus`

### 当前判断
- 主假设: 现有脚本对“传统环境能编”的路径覆盖尚可, 但对 RTX 50 系列 / CUDA 12.8+ 这种更敏感的新组合, 还缺少必要的构建环境编排.
- 备选解释: 用户现场如果仍沿用当前仓库默认的 `torch 2.3.1 + cu121`, 那么仅补脚本环境变量还不够, 还需要进一步处理 PyTorch 主版本与 CUDA runtime 的兼容边界.

### 验证计划
- 先补齐官方 PyTorch3D 安装文档与用户提到的上游兼容线索.
- 再把“可安全自动化”的部分写进 `scripts/install_pytorch3d.sh`.
- 对当前仓库仍无法自动安全判断的部分, 则通过 `.envrc` 和 README 给出显式覆盖入口, 避免硬编码出错.

### 当前状态
- **目前在阶段3**: 正在把 `install-pytorch3d` 从“只会浅克隆 + 限流”升级为“可控的源码构建入口”.

## [2026-03-31 11:34:19 UTC] [Session ID: codex-20260331T112445Z-45312] [记录类型]: `install-pytorch3d` Blackwell 兼容入口改造完成

### 已完成
- 已将 `install-pytorch3d` 默认源码引用从无条件追 `main` 调整为跟随官方文档的 `stable`.
- 已补上:
  - 已安装短路
  - system compiler 默认绑定
  - `CUDA_HOME` 自动推断 / 显式覆盖
  - `TORCH_CUDA_ARCH_LIST` 显式覆盖入口
  - Blackwell 明确场景下的保守自动设置
- 已同步更新:
  - `.envrc`
  - `README.md`
  - `tests/test_install_pytorch3d_script.py`

### 验证结果
- `bash -n scripts/install_pytorch3d.sh`
- `pixi run pytest tests/test_install_pytorch3d_script.py -q`
- `pixi run install-pytorch3d`
- 当前真实环境验证结果为:
  - 已成功短路到 `pytorch3d 0.7.9`
  - 没有再次触发整轮源码编译

### 当前状态
- **阶段4已完成**: 本轮 `install-pytorch3d` 入口改造与验证已经结束, 正在写入 WORKLOG / ERRORFIX / EPIPHANY 并准备交付.
