# 工作日志: `pixi run bootstrap` 高 CPU 排查

## [2026-03-25 09:52:40 UTC] [Session ID: bootstrap_hang_20260325] 任务名称: 排查 `pixi run bootstrap` 高 CPU / 类卡死现象

### 任务内容
- 在不直接执行 `pixi run bootstrap` 的前提下, 分析其高 CPU 与“像卡死”的原因.
- 结合仓库配置、上游安装文档和最小 dry-run 证据, 判断是否存在递归执行或源码编译热点.

### 完成过程
- 先回读默认六文件上下文, 确认这次工作属于独立支线, 再新建 `__bootstrap_hang` 记录集.
- 阅读 `README.md` 与 `pixi.toml`, 确认 `bootstrap` 被设计为安装剩余 git / editable / build-from-source 依赖的入口.
- 使用 `pixi run --dry-run --frozen bootstrap` 做最小动态验证, 确认任务按顺序展开为:
  - `install-moge`
  - `install-grounded-sam2`
  - `install-grounding-dino`
  - `install-flash-attn`
  - `install-pytorch3d`
- 继续检查:
  - `third_party/Grounded-SAM-2/setup.py`
  - `third_party/Grounded-SAM-2/grounding_dino/setup.py`
  - Pixi 官方任务文档
  - FlashAttention 官方安装说明
  - PyTorch3D 官方安装说明
- 最终确认:
  - `bootstrap` 没有自递归迹象
  - 高 CPU 更符合多个本地 C++ / CUDA 扩展源码编译连续发生的表现

### 总结感悟
- 这类“别名任务看起来像卡死”的问题, 不能只盯着最外层 `pixi run bootstrap`, 要把任务链展开后逐个看安装方式.
- 当前仓库真正危险的不是单个命令慢, 而是多个源码构建被打包在一个无阶段提示的别名里, 用户很容易把“正在编译”误认成“Pixi 卡死”.

## [2026-03-25 10:05:30 UTC] [Session ID: bootstrap_hang_20260325] 任务名称: 聚焦 `install-flash-attn` 的卡住原因

### 任务内容
- 在不直接运行 `install-flash-attn` 的前提下, 判断它为什么更像当前的卡住点.
- 区分“镜像问题”“无匹配 wheel”“本地源码编译过重”这几类可能性.

### 完成过程
- 先读取 Pixi 环境的关键版本, 确认当前是:
  - Python 3.11.9
  - torch 2.3.1
  - torch CUDA runtime 12.1
  - `ninja 1.13.2`
  - 22 核 CPU
- 再用 `pip download --only-binary=:all:` 做最小动态探测, 验证当前环境拿不到 `flash-attn` 的现成 wheel.
- 继续检查 `pip index versions` 与 `pip config list`, 确认阿里云镜像上包版本可见, 不是“包不存在”.
- 最后直接查询官方 PyPI `flash-attn 2.8.3` 的 JSON 元数据, 确认该版本只有源码包, 没有 wheel.
- 结合 `/usr/local/cuda/bin/nvcc --version` 结果, 确认这台机器具备本地 CUDA 编译条件, 所以安装会真的进入高 CPU 的源码构建.

### 总结感悟
- 这次排查把“好像是 flash-attn 卡死”收敛成了更精确的判断:
  - 不是单纯镜像抽风.
  - 而是当前默认安装路径天然会走源码编译.
- 一旦 `flash-attn` 这类包的最新版本只发 sdist, 像 `pip install flash-attn` 这种未限流、未分流的默认写法, 就很容易把用户带进“100% CPU 但不知道在干什么”的体验.

## [2026-03-25 10:12:10 UTC] [Session ID: bootstrap_hang_20260325] 任务名称: 为 `install-flash-attn` 增加编译限流

### 任务内容
- 修改 `pixi.toml` 中的 `install-flash-attn`, 让它默认在编译时至少保留 4 个 CPU.
- 新增 `.envrc` 默认值, 让保留 CPU 数可配置.
- 同步更新 README 行为说明.

### 完成过程
- 将 `install-flash-attn` 从单行 pip 命令改为 `bash -lc` 脚本, 在安装前先计算:
  - `reserve = FLASH_ATTN_RESERVED_CPUS or 4`
  - `MAX_JOBS = max(nproc - reserve, 1)`
- 同时保留“外部显式设置 `MAX_JOBS` 时优先尊重手动覆盖”的逻辑.
- 新建 `.envrc`, 写入:
  - `FLASH_ATTN_RESERVED_CPUS=4` 的默认值
  - `MAX_JOBS` 的可选覆盖示例
- 更新 `README.md`, 明确说明 `install-flash-attn` 默认会保留 4 个 CPU.
- 最后完成两项验证:
  - `pixi run --dry-run --frozen install-flash-attn`
  - `direnv exec ...` 验证默认值与计算结果

### 总结感悟
- 这次改造的价值不只是“慢一点”, 而是把“整机打满”改成了“可控占用”.
- 对这种重编译步骤, 最有用的不是再堆一个新任务, 而是让默认入口本身就更温和、更可解释.

## [2026-03-25 11:40:00 UTC] [Session ID: bootstrap_hang_20260325_followup] 任务名称: 完成 `bootstrap` 实跑与入口复验

### 任务内容
- 继续前一轮已完成的 `flash-attn` / `pytorch3d` 修复, 把 `pixi run bootstrap` 真正跑通.
- 在用户限制代理流量的前提下, 只把代理用于确实需要 GitHub 网络的步骤.
- 把本轮新暴露出来的 `Grounded-SAM-2` 隔离构建问题一并修正.

### 完成过程
- 先接管正在运行的 `install-pytorch3d` 会话, 确认它已从浅克隆进入 wheel 编译, 最终成功安装 `pytorch3d-0.7.9`.
- 随后执行 `pixi run bootstrap` 入口复验, 发现 `install-grounded-sam2` 会因为 build isolation 重新下载大体积 `torch` / `nvidia_nccl_cu13` 轮子.
- 将 `pixi.toml` 中的 `install-grounded-sam2` 改为:
  - `python -m pip install --no-build-isolation -e ./third_party/Grounded-SAM-2`
- 单独验证 `pixi run install-grounded-sam2` 成功后, 再重新执行 `pixi run bootstrap`.
- 最终完整跑通整个任务链:
  - `install-moge`
  - `install-grounded-sam2`
  - `install-grounding-dino`
  - `install-flash-attn`
  - `install-pytorch3d`
- 最后补做 Python import 验证, 确认 `flash_attn`、`pytorch3d`、`sam2`、`groundingdino`、`moge` 都可导入.

### 总结感悟
- `flash-attn` 的高 CPU 体感问题, 真正该修的是“默认多架构源码编译 + 无并发约束”, 而不是只盯着 CPU 百分比本身.
- `bootstrap` 这类聚合入口在复验时, 很容易暴露出另一个隐藏问题: editable 安装默认 build isolation 会在已有 Pixi 环境里重复拉大包, 这会直接吞掉代理流量和等待时间.
- 这次收尾后, 入口链路已经可跑, 但 `install-moge` 依然是一个值得继续优化的网络热点.

## [2026-03-25 11:42:39 UTC] [Session ID: bootstrap_hang_20260325_followup] 任务名称: 将 `flash-attn` 单专用架构规则写入 `AGENTS.md`

### 任务内容
- 把这次已经验证过的 `flash-attn` 项目经验提升为项目级常驻规则.
- 避免后续 agent 再把 `install_flash_attn.sh` 改回多架构编译.

### 完成过程
- 回读项目根级 `AGENTS.md`, 确认它当前主要承载仓库级开发准则.
- 在 `Build, Test, and Development Commands` 区域追加一条面向后续维护者的明确规则:
  - 处理 `pixi run bootstrap` 或 `scripts/install_flash_attn.sh` 时, `flash-attn` 必须保持“当前机器专用单架构”策略.
  - 不要恢复多架构默认目标, 否则会显著拉长源码编译时间.

### 总结感悟
- 这类“已经被动态验证过, 且未来很容易被无意回退”的规则, 只留在临时任务记录里不够.
- 直接写进 `AGENTS.md`, 才能在后续维护时形成真正的防回归约束.

## [2026-03-31 09:04:10 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] 任务名称: 修复 `install-flash-attn` 在“已安装”场景下仍因自动探测失败而报错

### 任务内容
- 排查用户执行 `pixi run install-flash-attn` 时出现的:
  - `无法自动探测 GPU 架构`
- 区分这次失败到底是:
  - 当前环境里真的没有装上 `flash-attn`
  - 还是脚本前置校验顺序有问题

### 完成过程
- 先复现脚本当前行为, 确认失败点确实发生在 GPU 架构自动探测阶段.
- 再做最小动态验证:
  - `pixi run python` 下 `torch.cuda.is_available() = False`
  - `torch.cuda.device_count() = 0`
  - `/usr/bin/nvidia-smi` 不可执行
  - 当前没有 `/dev/nvidia*`
- 随后用 `FLASH_ATTN_CUDA_ARCHS=120` 做可证伪实验, 发现脚本立刻越过失败点并打印:
  - `Requirement already satisfied: flash-attn ... (2.8.3)`
- 由此确认问题不在安装链本身, 而在 `scripts/install_flash_attn.sh` 的前置顺序:
  - 先探测架构
  - 后判断是否其实已经安装
- 最后修改脚本:
  - 先检测 `flash-attn` 是否已安装
  - 已安装则直接短路成功
  - 未安装时再进入 GPU 架构自动探测
  - 探测失败时额外打印诊断细节

### 总结感悟
- 硬件相关 preflight 如果放在“幂等短路”之前, 很容易把本来已经满足的场景误伤成失败.
- 对安装类任务, 更稳的顺序通常是:
  - 先判断当前状态是否已经满足
  - 只有确实需要执行重动作时, 再做昂贵或环境敏感的前置校验

## [2026-03-31 10:18:10 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_cpu_limit_11606] 任务名称: 为 `install-pytorch3d` 增加默认 CPU 限流

### 任务内容
- 处理用户反馈的 `install-pytorch3d` 编译时 CPU 占满问题.
- 确认当前入口到底有没有限流, 然后把默认行为改成“不要吃满整机”.

### 完成过程
- 先读取现有 `scripts/install_pytorch3d.sh`, 确认它此前只有:
  - 浅克隆仓库
  - `python -m pip install --no-build-isolation ./pytorch3d`
  没有任何并发控制.
- 再回读本地 `pytorch3d/setup.py` 与 PyTorch `torch.utils.cpp_extension.py`, 验证到:
  - `pytorch3d` 默认走 `BuildExtension`
  - ninja 默认并发是 `#CPUS + 2`
  - `MAX_JOBS` 是官方支持的 worker 覆盖入口
- 随后把脚本改成与 `flash-attn` 同风格:
  - 默认读取 `PYTORCH3D_RESERVED_CPUS`
  - 未设置时保留 4 个 CPU
  - 计算 `MAX_JOBS=max(nproc-reserve,1)`
  - 同时导出 `MAX_JOBS` 与 `CMAKE_BUILD_PARALLEL_LEVEL`
- 同步更新:
  - `.envrc`
  - `README.md`
- 最后用 fake `python` 包装器做最小动态验证, 确认:
  - 默认值会被正确传进构建链
  - 手动 `MAX_JOBS` 覆盖也会生效

### 总结感悟
- 这次问题和 `flash-attn` 很像, 但本质不是“编译一定会失败”, 而是“入口默认对机器不够友好”.
- 对这类重型源码构建, 最好别让不同依赖各自凭默认值乱跑. 统一的限流口径, 会比事后靠用户临时手动降并发可靠得多.

## [2026-03-31 11:34:19 UTC] [Session ID: codex-20260331T112445Z-45312] 任务名称: 改良 `install-pytorch3d` 的 Blackwell / 新 CUDA 源码构建入口

### 任务内容
- 处理用户再次遇到的 `pytorch3d` 源码编译失败问题.
- 参考上游 Blackwell 实战方案, 但不把 `sm_120` 环境变量粗暴硬编码到当前 `torch 2.3.1 + cu121` 的仓库默认环境里.
- 把真正可安全自动化的构建步骤沉淀回脚本、文档与测试.

### 完成过程
- 先回读 `__bootstrap_hang` 支线历史, 区分这次问题里的两层现象:
  - 本机旧失败里出现过 `cc1plus` 被 `Killed`
  - 用户提供的新方案针对的是 Blackwell / CUDA 12.8+ 的构建兼容性
- 再核对上游依据:
  - PyTorch3D 官方 `INSTALL.md` 明确支持 `git+...@stable`
  - FoundationPose issue #398 里有 Blackwell `sm_120` 的实际源码构建方案
- 随后改造 `scripts/install_pytorch3d.sh`:
  - 已安装时默认短路成功, 避免重复重编译
  - 默认源码引用切到 `stable`
  - 默认优先绑定 system `gcc/g++`
  - 自动推断 `CUDA_HOME`, 并允许 `.envrc` 显式覆盖
  - `TORCH_CUDA_ARCH_LIST` 允许显式覆盖, 仅在脚本能确认是 `torch 2.7+ / CUDA 12.8+ / sm_120` 时才自动设置为 `12.0`
- 同步更新 `.envrc` 与 `README.md`, 把可调入口和 Blackwell 注意事项写清楚.
- 新增 `tests/test_install_pytorch3d_script.py`, 用 fake `git` / `python` 验证:
  - 已安装短路
  - `stable` / `CUDA_HOME` / `TORCH_CUDA_ARCH_LIST` 的透传

### 总结感悟
- 用户给出的“可工作命令串”往往不是该原样硬编码的默认值, 更适合拆成:
  - 哪些是普适改进
  - 哪些只对特定硬件栈成立
- 对安装器脚本来说, “已安装短路”不是小优化, 而是排查噪音控制的一部分. 没有它, 每次复验都可能重新掉进长时间 C++ / CUDA 编译.
