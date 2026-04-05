# 错误修复记录: `pixi run bootstrap` 高 CPU / 卡住

## [2026-03-25 11:40:00 UTC] [Session ID: bootstrap_hang_20260325_followup] 任务名称: 修复 `bootstrap` 中 `flash-attn` 高 CPU 与入口复验卡慢问题

### 现象
- `pixi run bootstrap` 在用户视角下表现为 CPU 很高, 像卡死.
- 进一步缩小范围后, `install-flash-attn` 会触发重型源码编译.
- 在入口复验阶段, `install-grounded-sam2` 又会启动 build isolation, 重复下载大体积 `torch` / `nvidia_nccl_cu13` 轮子, 导致流程再次变慢.

### 原因
- `flash-attn 2.8.3` 没有 wheel, 默认只能源码编译.
- 上游 `flash-attn` 默认会编译 `80;90;100;120` 多套架构, 且仓库原先没有限制编译并发.
- `Grounded-SAM-2` 的 pyproject 声明了 `torch>=2.3.1`, editable 安装默认 build isolation 时, 会在临时环境里再次拉取这些依赖.

### 修复
- 将 `install-flash-attn` 外提到 `scripts/install_flash_attn.sh`.
- 在脚本里加入:
  - `FLASH_ATTN_RESERVED_CPUS` 动态保留 CPU
  - `MAX_JOBS = max(nproc - reserve, 1)`
  - 自动探测 GPU 架构并默认只设置单一 `FLASH_ATTN_CUDA_ARCHS`
- 新增 `.envrc` 默认值与 README 说明.
- 将 `install-pytorch3d` 外提到 `scripts/install_pytorch3d.sh`, 使用浅克隆并复用本地仓库.
- 将 `install-grounded-sam2` 改为:
  - `python -m pip install --no-build-isolation -e ./third_party/Grounded-SAM-2`
  以复用现有 Pixi 环境, 避免重复下载隔离构建依赖.

### 验证
- `pixi run install-flash-attn` 已成功安装, 且动态证据显示只编译 `compute_120`.
- `pixi run install-pytorch3d` 已成功构建并安装 `pytorch3d-0.7.9`.
- `pixi run install-grounded-sam2` 在 `--no-build-isolation` 下已成功完成 editable 安装.
- `pixi run bootstrap` 已完整跑通.
- Python import 验证成功:
  - `flash_attn`
  - `pytorch3d`
  - `sam2`
  - `groundingdino`
  - `moge`

## [2026-03-31 09:05:20 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] 任务名称: 修复 `install-flash-attn` 在已安装场景下误报 GPU 架构探测失败

### 现象
- 用户执行 `pixi run install-flash-attn` 时, 输出:
  - `[install-flash-attn] cpu_total=1, reserved=4, MAX_JOBS=1`
  - `[install-flash-attn] 无法自动探测 GPU 架构. 请手动设置 FLASH_ATTN_CUDA_ARCHS, 例如 120.`
- 进一步动态验证发现:
  - `torch.cuda.is_available() = False`
  - `torch.cuda.device_count() = 0`
  - `/usr/bin/nvidia-smi` 不可执行
  - 当前没有 `/dev/nvidia*`

### 原因
- 脚本先执行 GPU 架构自动探测, 再决定是否继续安装.
- 但当前 Pixi 环境里 `flash-attn 2.8.3` 其实已经安装好了.
- 因此“已安装本应直接成功”的幂等场景, 被前置的环境敏感探测误伤成失败.

### 修复
- 在 `scripts/install_flash_attn.sh` 中新增“已安装短路”逻辑:
  - 先读取 `flash-attn` 的发行版元数据
  - 若已安装, 直接打印版本并退出成功
- 保留后续 GPU 架构探测逻辑, 但补充失败时的诊断信息:
  - `torch.cuda` 状态
  - `nvidia-smi` 路径与可执行性
  - `/dev/nvidia*` 设备节点是否存在

### 验证
- `bash -n scripts/install_flash_attn.sh`
- `pixi run bash ./scripts/install_flash_attn.sh`
- `pixi run install-flash-attn`
- `pixi run python` 读取 `flash-attn` 版本元数据为 `2.8.3`
- 修复后原命令退出码为 `0`, 并输出:
  - `检测到已安装 flash-attn 2.8.3, 跳过重复安装`

## [2026-03-31 10:19:20 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_cpu_limit_11606] 任务名称: 修复 `install-pytorch3d` 默认不限制编译并发

### 现象
- 用户执行 `install-pytorch3d` 时遇到:
  - `RuntimeError: Error compiling objects for extension`
  - `Failed building wheel for pytorch3d`
- 同时用户明确反馈编译阶段会把 CPU 吃得像“卡死”.
- 现场静态阅读确认旧 `scripts/install_pytorch3d.sh` 没有任何 CPU 并发限制.

### 原因
- `pytorch3d` 默认通过 `torch.utils.cpp_extension.BuildExtension` 走 ninja 构建.
- 本地 PyTorch 源码明确说明:
  - ninja 默认 worker 数是 `#CPUS + 2`
  - 可通过 `MAX_JOBS` 控制
- 旧入口没有给这条构建链传入 `MAX_JOBS`, 因而默认会尽量并行, 很容易把机器资源打满.

### 修复
- 在 `scripts/install_pytorch3d.sh` 中新增并发控制:
  - 默认读取 `PYTORCH3D_RESERVED_CPUS`
  - 默认保留 `4` 个 CPU
  - 自动计算 `MAX_JOBS = max(nproc - reserve, 1)`
- 在执行 `pip install` 时同时导出:
  - `MAX_JOBS`
  - `CMAKE_BUILD_PARALLEL_LEVEL`
- 在 `.envrc` 中新增:
  - `PYTORCH3D_RESERVED_CPUS="${PYTORCH3D_RESERVED_CPUS:-4}"`
- 在 `README.md` 中补充该入口的限流说明与覆盖方式.

### 验证
- `bash -n scripts/install_pytorch3d.sh`
- 使用 fake `python` 包装器做最小动态验证:
  - 默认路径输出:
    - `[install-pytorch3d] cpu_total=1, reserved=4, MAX_JOBS=1`
    - `FAKE_PYTHON MAX_JOBS=1 CMAKE_BUILD_PARALLEL_LEVEL=1 ...`
  - 手动覆盖路径输出:
    - `[install-pytorch3d] 使用外部指定的 MAX_JOBS=3`
    - `FAKE_PYTHON MAX_JOBS=3 CMAKE_BUILD_PARALLEL_LEVEL=3 ...`
- 结论:
  - 当前入口已经具备默认限流能力.
  - 但如果后续仍报 `Error compiling objects for extension`, 那就是编译错误本身还需要继续排查, 不能再把“CPU 吃满”与“编译失败原因”混为一谈.

## [2026-03-31 10:27:20 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] 任务名称: 用 `MAX_JOBS=1` 受控重跑 `install-pytorch3d`

### 现象
- 用户要求停止后台编译并重新用限制 CPU 的方式开始.
- 重新执行:
  - `env MAX_JOBS=1 pixi run install-pytorch3d`
- 输出已确认:
  - `Using envvar MAX_JOBS (1) as the number of workers...`
  - 真实进程链包含 `ninja -v -j 1`

### 原因判断
- “CPU 会不会吃满”这个问题已经被证伪:
  - 本轮只有单 worker 编译
  - 不是高并发导致的再次失败
- 新暴露出的失败信号是:
  - `c++: fatal error: Killed signal terminated program cc1plus`
- 这类信号更像是编译进程被系统资源管理器直接杀掉, 常见方向是 OOM / 容器内存限制.

### 验证
- 运行会话已结束, 当前没有残留 `install-pytorch3d` / `ninja` / `cc1plus` 进程.
- `pixi run python` 仍可成功导入 `pytorch3d 0.7.9`.

### 结论
- 这轮“限制 CPU 后重新开始”已经走完了.
- 结果不是卡住, 而是失败退出.
- 下一步要查的不是 CPU 并发, 而是为什么 `cc1plus` 被系统杀掉.

## [2026-03-31 11:34:19 UTC] [Session ID: codex-20260331T112445Z-45312] 任务名称: 修复 `install-pytorch3d` 对 Blackwell / 新 CUDA 环境不够友好的构建入口

### 现象
- 用户再次遇到:
  - `RuntimeError: Error compiling objects for extension`
  - `Failed building wheel for pytorch3d`
- 同时补充了一个在 RTX 50 系列 / CUDA 12.8+ 上可工作的上游源码构建方案.
- 当前仓库脚本此前只处理了:
  - 浅克隆
  - CPU 限流
  没有处理新卡环境更敏感的构建变量, 也没有“已安装短路”.

### 原因
- 旧脚本默认追 `main`, 没有对齐 PyTorch3D 官方文档中的 `@stable` released 安装路径.
- 旧脚本没有统一处理:
  - system compiler
  - `CUDA_HOME`
  - `TORCH_CUDA_ARCH_LIST`
- 旧脚本重复执行时总会再次尝试重编译, 这会把真正的问题和“重复重建噪音”混在一起.
- 但 Blackwell 方案不能直接硬编码为仓库默认值, 因为当前 Pixi 环境仍是:
  - `torch 2.3.1 + cu121`

### 修复
- 在 `scripts/install_pytorch3d.sh` 中加入:
  - `PYTORCH3D_FORCE_REINSTALL` 之外默认短路已安装版本
  - `PYTORCH3D_GIT_REF` 默认值 `stable`
  - `PYTORCH3D_USE_SYSTEM_COMPILER`
  - `PYTORCH3D_CUDA_HOME`
  - `PYTORCH3D_TORCH_CUDA_ARCH_LIST`
- 自动策略改成:
  - 默认优先 system `gcc/g++`
  - 默认推断 `CUDA_HOME`
  - `TORCH_CUDA_ARCH_LIST` 只在明确的 Blackwell 条件下保守自动设置
- 在 `.envrc` 中补齐上述变量默认值与中文注释.
- 在 `README.md` 中补齐 Blackwell / 新 CUDA 场景的使用说明.
- 新增脚本级回归测试, 锁住安装编排行为.

### 验证
- `bash -n scripts/install_pytorch3d.sh`
- `pixi run pytest tests/test_install_pytorch3d_script.py -q`
- `pixi run install-pytorch3d`
- 关键结果:
  - `2 passed in 0.31s`
  - `[install-pytorch3d] 检测到已安装 pytorch3d 0.7.9, 跳过重复安装`

### 结论
- 这次修复解决的是“安装入口不够可控”的问题.
- 如果用户后续在真正的 Blackwell / CUDA 12.8+ 环境里仍有编译错误, 下一步就该继续看更早的编译器报错与 PyTorch 主版本兼容性, 而不是再回到“重复重编译入口”这一层.
