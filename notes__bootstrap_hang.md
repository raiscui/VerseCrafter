# 排查笔记: `pixi run bootstrap` 高 CPU

## [2026-03-25 09:49:30 UTC] [Session ID: bootstrap_hang_20260325] 笔记: 首轮证据整理

### 来源1: `/root/autodl-tmp/home/rais/VerseCrafter/README.md`
- 关键原文:
  - `# Install the remaining git / editable / build-from-source dependencies`
  - `# (this step compiles CUDA extensions and may take a while)`
  - `pixi run bootstrap`
- 结论:
  - README 已经明确把 `bootstrap` 定义为“安装剩余 git / editable / build-from-source 依赖”的步骤.
  - “compiles CUDA extensions” 是已写明的预期行为, 不是偶发现象.

### 来源2: `/root/autodl-tmp/home/rais/VerseCrafter/pixi.toml`
- `bootstrap` 只依赖 5 个子任务:
  - `install-moge`
  - `install-grounded-sam2`
  - `install-grounding-dino`
  - `install-flash-attn`
  - `install-pytorch3d`
- 其中安装命令显示:
  - `flash-attn` 使用 `python -m pip install --no-build-isolation flash-attn`
  - `pytorch3d` 先 `git clone`, 再 `python -m pip install --no-build-isolation ./pytorch3d`
  - `Grounded-SAM-2` 与 `grounding_dino` 都是 editable 安装

### 来源3: `pixi run --dry-run --frozen bootstrap`
- 动态结果:
  - Pixi 按顺序打印出 5 个子任务, 没有出现递归调用 `pixi run bootstrap` 或嵌套 `pixi run` 的迹象.
- 结论:
  - 当前没有证据支持“pixi 任务自身递归导致假死”.
  - 现象更像是某个依赖安装步骤本身耗时 / 耗 CPU.

### 来源4: `third_party/Grounded-SAM-2/setup.py`
- 关键行为:
  - 默认 `SAM2_BUILD_CUDA=1`
  - `get_extensions()` 会创建 `CUDAExtension("sam2._C", ...)`
- 结论:
  - `install-grounded-sam2` 默认会尝试构建 SAM2 的 CUDA 扩展.
  - 即使允许错误继续, 它仍然会先走一轮扩展构建流程.

### 来源5: `third_party/Grounded-SAM-2/grounding_dino/setup.py`
- 关键行为:
  - `get_extensions()` 在检测到 CUDA 环境后切到 `CUDAExtension`
  - `cmdclass={"build_ext": torch.utils.cpp_extension.BuildExtension}`
- 结论:
  - `install-grounding-dino` 不是纯 Python 安装, 会触发 C++ / CUDA 扩展编译.

### 来源6: Pixi 官方任务文档与 dry-run 行为
- Context7 / 官方文档要点:
  - `depends-on` 任务按顺序执行
  - `pixi run --dry-run <task>` 只打印将要执行的命令
  - `--skip-deps` 可以跳过依赖任务
- 结论:
  - 这次 dry-run 能作为“执行链”证据使用.

### 来源7: FlashAttention 官方安装文档
- 官方要点:
  - `pip install flash-attn --no-build-isolation`
  - 没有 `ninja` 时编译可能长达约 2 小时
  - 有 `ninja` 时会并行编译, 会明显吃 CPU
  - 可用 `MAX_JOBS=4` 限制并行度
- 结论:
  - `install-flash-attn` 是明确的源码编译热点.
  - “CPU 100%” 与官方描述一致.

### 来源8: PyTorch3D 官方安装文档
- 官方要点:
  - 从 GitHub 克隆后 `pip install -e .` / `pip install ./local_clone` 属于源码安装
  - CUDA 支持会在可用时一起参与构建
- 结论:
  - `install-pytorch3d` 也是明确的源码构建步骤.

## [2026-03-25 09:52:40 UTC] [Session ID: bootstrap_hang_20260325] 笔记: 风险补充

### 来源9: 仓库内额外搜索
- 已搜索关键字:
  - `MAX_JOBS`
  - `SAM2_BUILD_CUDA`
  - `SAM2_BUILD_ALLOW_ERRORS`
  - `flash-attn`
  - `pytorch3d`
- 结果:
  - 当前仓库根级没有发现对 `flash-attn` 编译并行度的限制.
  - 没有发现对 `SAM2_BUILD_CUDA` 的默认关闭或条件切换.
  - `README.md` 虽然提示“会编译 CUDA 扩展”, 但没有拆开说明哪个子任务最重, 也没有给出逐个执行的排查建议.

### 结论补充
- 用户体感上的“卡死”, 很可能是这几个因素叠加:
  - 一个别名任务里串了多个源码编译步骤
  - 其中部分步骤会长时间高 CPU
  - 仓库当前没有统一限制并行度
  - `bootstrap` 别名本身没有阶段性提示, 不容易知道卡在哪个子任务

### 综合判断
- 已观察到的现象:
  - `bootstrap` 是一个顺序任务链, 不是单条简单安装命令.
  - 其中至少 4 个子任务会触发本地扩展构建或源码安装.
- 当前主假设:
  - 高 CPU 的主要原因不是 Pixi 死循环, 而是 `flash-attn`、`pytorch3d`、`Grounded-SAM-2`、`grounding_dino` 这些步骤在当前环境下进行本地 C++ / CUDA 编译.
- 最强备选解释:
  - 某个子任务在下载源码或解析依赖时反复重试, 让人误以为“卡死”.
- 推翻主假设所需证据:
  - 真实运行日志显示 CPU 打满时并没有进入编译器 / `ninja` / `nvcc` / `c++` / `gcc` / `pip wheel` 流程, 而是卡在别的循环逻辑上.
- 当前可下的结论:
  - 已验证 `bootstrap` 是顺序安装链.
  - 已验证链路中包含多个会触发本地扩展编译的子任务.
  - 因此“100% CPU”本身是被当前配置设计出来的高概率现象, 不是无证据的偶发猜测.

## [2026-03-25 10:03:50 UTC] [Session ID: bootstrap_hang_20260325] 笔记: `install-flash-attn` 定位补充

### 来源10: 本机 Pixi 环境探针
- 动态结果:
  - `python=3.11.9`
  - `torch=2.3.1`
  - `torch.version.cuda=12.1`
  - `ninja=1.13.2`
  - `cpus=22`
  - `MAX_JOBS=None`
- 结论:
  - 当前环境具备会把源码编译并行跑满 CPU 的条件.
  - 仓库没有对 `flash-attn` 编译并行度做任何限制.

### 来源11: 二进制 wheel 探测
- 验证命令:
  - `timeout 120s pixi run python -m pip download --only-binary=:all: --no-deps --dest /tmp/flash_attn_wheel_probe flash-attn`
- 关键输出:
  - `ERROR: Could not find a version that satisfies the requirement flash-attn (from versions: none)`
  - `ERROR: No matching distribution found for flash-attn`
- 结论:
  - 在当前这套索引 + 环境组合下, `pip` 找不到可直接安装的 `flash-attn` wheel.
  - 因而 `pip install flash-attn` 只能转入源码构建路径.

### 来源12: 索引与官方 PyPI 交叉核对
- 动态结果:
  - `pip index versions flash-attn` 能看到版本列表, 说明镜像并不是“包不存在”.
  - `pip config list` 显示当前索引为 `http://mirrors.aliyun.com/pypi/simple`.
  - 查询 `https://pypi.org/pypi/flash-attn/2.8.3/json` 后发现:
    - `total_files=1`
    - `wheel_count=0`
    - `sdist_count=1`
- 结论:
  - 至少对 `2.8.3` 这个当前默认版本, 官方 PyPI 本身就只有源码包, 不是“阿里云镜像独有问题”.
  - 当前安装命令 `pip install flash-attn` 默认会落到源码编译.

### 来源13: CUDA toolkit 可用性
- 动态结果:
  - `torch.utils.cpp_extension.CUDA_HOME` 解析到 `'/usr/local/cuda'`
  - `/usr/local/cuda/bin/nvcc --version` 返回 `release 12.8, V12.8.93`
- 结论:
  - 这台机器具备本地 CUDA 编译条件.
  - 因此一旦 `flash-attn` 没有 wheel, 就会真的进入重型本地编译, 而不是秒失败.

### 对 `install-flash-attn` 的更新判断
- 已观察到的现象:
  - 当前默认版本 `flash-attn 2.8.3` 没有 wheel.
  - 当前机器有 `ninja`、22 核 CPU 和可用 `nvcc`.
- 当前主假设:
  - `install-flash-attn` 看起来像“卡死”, 本质上是因为 `pip install flash-attn` 被迫走源码编译, 并由 `ninja` 高并行占满 CPU.
- 最强备选解释:
  - 真实感知到的“卡死”不是编译本身, 而是编译日志太少, 用户不知道当前正在编译而误以为停住了.
- 推翻主假设所需证据:
  - 真实安装日志显示它既没有进入源码构建, 也没有出现 `ninja` / `build_ext` / `nvcc` / `c++` 等编译阶段迹象.

## [2026-03-25 10:12:10 UTC] [Session ID: bootstrap_hang_20260325] 笔记: 限流改造验证

### 来源14: `pixi run --dry-run --frozen install-flash-attn`
- 动态结果:
  - Pixi 成功解析新的 `bash -lc` 任务定义.
  - dry-run 输出里已包含:
    - `reserve="${FLASH_ATTN_RESERVED_CPUS:-4}"`
    - `jobs=$(( cpu_total > reserve ? cpu_total - reserve : 1 ))`
    - `MAX_JOBS="${jobs}" python -m pip install --no-build-isolation flash-attn`
- 结论:
  - `pixi.toml` 新语法有效.
  - 任务会在实际安装前先计算并导出受控的 `MAX_JOBS`.

### 来源15: `.envrc` 默认值验证
- 动态结果:
  - `direnv allow /root/autodl-tmp/home/rais/VerseCrafter`
  - `direnv exec ...` 输出:
    - `FLASH_ATTN_RESERVED_CPUS=4`
    - `cpu_total=22 reserve=4 jobs=18`
- 结论:
  - `.envrc` 默认值已生效.
  - 当前机器会为 `flash-attn` 编译保留 4 个 CPU, 并把并发限制为 `18`.

## [2026-03-25 10:40:40 UTC] [Session ID: bootstrap_hang_20260325] 笔记: 重新执行 `bootstrap` 时的网络判断

### 现象
- 当前 shell 默认带有:
  - `https_proxy=http://127.0.0.1:7897`
  - `http_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 第一次执行 `bootstrap` 时虽然没有手动设置代理, 但 pip 子进程实际通过 `127.0.0.1:7897` 下载.
- 因为用户要求“网络无问题不要用代理”, 所以中止了第一次执行, 改为显式 `unset` 代理重跑.

### 无代理验证
- 小流量直连验证都成功:
  - `git ls-remote https://github.com/microsoft/MoGe.git HEAD`
  - `git ls-remote https://github.com/facebookresearch/pytorch3d.git HEAD`
  - `pixi run python -m pip index versions flash-attn`
- 但真正执行 `bootstrap` 时, 无代理版本卡在:
  - `install-moge`
  - `git clone --filter=blob:none --quiet https://github.com/microsoft/MoGe.git ...`
  - 后台进程链停留在 `git-remote-https` + `git index-pack`
- 动态证据:
  - `tmp_pack_hy5QOO` 先增长到约 `2.2M`
  - 随后长时间不再增长
  - clone / fetch / index-pack 进程持续存在 6 分钟以上, 但 CPU 几乎为 0

### 结论
- 当前网络表现不是“完全不通”, 而是:
  - 小请求直连正常
  - 大一点的 GitHub clone 在直连路径上明显卡住
- 这已经满足“网络问题才启用代理”的条件.
- 后续为了把 `bootstrap` 跑完, 应该重新启用代理.

## [2026-03-25 18:58:40 UTC] [Session ID: bootstrap_hang_20260325_single_arch] 笔记: `flash-attn` 单架构化依据

### 来源14: 本地 `flash-attn` 源码 `setup.py`
- 读取位置:
  - `/tmp/pip-install-tw0obv69/flash-attn_e0d679bc533a4b41ae58f23cb2e81d31/setup.py`
- 关键代码事实:
  - `cuda_archs()` 读取 `FLASH_ATTN_CUDA_ARCHS`
  - 默认值是 `80;90;100;120`
  - `extra_compile_args["nvcc"]` 直接拼接 `cc_flag`
- 结论:
  - 当前多架构编译不是 PyTorch 自动猜出来的, 而是 `flash-attn` 上游自己默认要求编 4 套架构.
  - 只要把 `FLASH_ATTN_CUDA_ARCHS` 收窄到单值, 就能从源头减少编译目标.

### 来源15: 本地 PyTorch `torch.utils.cpp_extension`
- 读取位置:
  - `.pixi/envs/default/lib/python3.11/site-packages/torch/utils/cpp_extension.py`
- 关键代码事实:
  - `_get_cuda_arch_flags(cflags)` 如果发现传入 flag 里已经包含 `arch`, 会直接返回空列表.
  - 本地 torch 2.3.1 支持的 `TORCH_CUDA_ARCH_LIST` 最高只到 `9.0/9.0a`, 不认识 `12.0`.
- 结论:
  - 当前机器不能稳妥地通过 `TORCH_CUDA_ARCH_LIST=12.0` 解决问题, 因为这会触发本地 PyTorch 旧版本的架构校验限制.
  - 更稳的做法是只设置 `FLASH_ATTN_CUDA_ARCHS=120`, 让 `flash-attn` 直接把 `-gencode arch=compute_120,code=sm_120` 交给 nvcc.

### 来源16: 本机 GPU 能力探测
- 动态结果:
  - `torch.cuda.get_device_capability(0) -> 12.0`
  - `torch.cuda.get_arch_list() -> ... sm_90`
  - torch 会警告当前安装本身还不原生支持 `sm_120`
- 结论:
  - 这解释了为什么“设备实际是 12.0”与“torch 支持列表只有到 9.0”会同时成立.
  - 也解释了这次脚本为什么不能直接依赖 `TORCH_CUDA_ARCH_LIST`.

## [2026-03-25 19:15:30 UTC] [Session ID: bootstrap_hang_20260325_single_arch] 笔记: `install-flash-attn` 单架构验证通过

### 动态验证命令
- `direnv exec /root/autodl-tmp/home/rais/VerseCrafter pixi run install-flash-attn`

### 关键输出
- 脚本启动时打印:
  - `自动探测当前 GPU 架构: 120`
- `build.ninja` 中只存在:
  - `-gencode arch=compute_120,code=sm_120`
- 实时 `nvcc` / `cicc` 进程参数只出现:

## [2026-03-31 09:01:40 UTC] [Session ID: bootstrap_hang_20260331_flash_attn_detect_11606] 笔记: `install-flash-attn` 探测失败的现象与修复依据

### 来源17: 当前环境里的最小动态探针
- 验证命令:
  - `pixi run python` 下读取 `torch.cuda.is_available()` 与 `torch.cuda.device_count()`
  - `nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader`
  - `ls -l /usr/bin/nvidia-smi`
  - `ls -l /dev/nvidia*`
- 关键输出:
  - `torch.cuda.is_available() = False`
  - `torch.cuda.device_count() = 0`
  - `/usr/bin/nvidia-smi` 当前是 `0` 字节且不可执行
  - 当前没有任何 `/dev/nvidia*` 设备节点
- 结论:
  - 这次会话里的自动探测失败确实有动态证据支撑.
  - 但这还不能直接推出“flash-attn 没安装”, 只能说明“当前 shell / 容器里无法靠 GPU 可见性自动推断架构”.

### 来源18: 手动覆盖 `FLASH_ATTN_CUDA_ARCHS=120` 的最小可证伪实验
- 验证命令:
  - `env FLASH_ATTN_CUDA_ARCHS=120 pixi run bash ./scripts/install_flash_attn.sh`
- 关键输出:
  - `使用外部指定的 FLASH_ATTN_CUDA_ARCHS=120`
  - `Requirement already satisfied: flash-attn ... (2.8.3)`
- 结论:
  - 当前失败不是 `pip install flash-attn` 这一步真的装不上.
  - 真正的问题是脚本在检查“是否需要安装”之前, 就先要求完成 GPU 架构自动探测.

### 来源19: 修复后回归验证
- 验证命令:
  - `bash -n scripts/install_flash_attn.sh`
  - `pixi run bash ./scripts/install_flash_attn.sh`
  - `pixi run install-flash-attn`
  - `pixi run python - <<'PY' ... metadata.version('flash-attn') ... PY`
- 关键输出:
  - 脚本语法检查通过
  - `检测到已安装 flash-attn 2.8.3, 跳过重复安装`
  - `pixi run install-flash-attn` 退出码为 `0`
- 结论:
  - 已验证修复后的入口在“已安装”场景下会直接短路成功.
  - 没有再被 GPU 自动探测失败误伤.

### 综合判断
- 已观察到的现象:
  - 当前环境看不到 GPU, `nvidia-smi` 也不可执行.
  - 但 Pixi 环境里 `flash-attn 2.8.3` 已经存在.
- 当前已验证结论:
  - 本次用户看到的失败并不是“flash-attn 未安装”.
  - 根因是 `install_flash_attn.sh` 的前置顺序不合理:
    - 先做硬件相关架构探测
    - 后做“其实已经安装”的检查
  - 调整顺序后, 原命令已经恢复成功.
  - `compute_120`
- 安装结论:
  - `Successfully built flash-attn`
  - `Successfully installed flash-attn-2.8.3`

## [2026-03-31 10:16:50 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_cpu_limit_11606] 笔记: `install-pytorch3d` CPU 限流依据与验证

### 来源20: 当前脚本与本地 PyTorch 源码
- 验证位置:
  - `scripts/install_pytorch3d.sh`
  - `pytorch3d/setup.py`
  - `.pixi/envs/default/lib/python3.11/site-packages/torch/utils/cpp_extension.py`
- 关键事实:
  - 旧 `install_pytorch3d.sh` 只有浅克隆与 `python -m pip install`, 没有并发限制.
  - `pytorch3d/setup.py` 默认直接使用 `torch.utils.cpp_extension.BuildExtension`.
  - PyTorch 本地源码明确写明:
    - ninja 默认会用 `#CPUS + 2 workers`
    - 可通过环境变量 `MAX_JOBS` 覆盖
    - `_run_ninja_build(...)` 会把 `MAX_JOBS` 转成 `ninja -j N`
- 结论:
  - 当前入口确实没有限流.
  - `MAX_JOBS` 不是猜测式方案, 而是本地 PyTorch 扩展构建链的正式控制入口.

### 来源21: 修复后的最小动态验证
- 验证命令:
  - `bash -n scripts/install_pytorch3d.sh`
  - 用临时 fake `python` 包装器执行脚本, 避免真实进入重编译
- 关键输出:
  - 默认路径:
    - `[install-pytorch3d] cpu_total=1, reserved=4, MAX_JOBS=1`
    - `FAKE_PYTHON MAX_JOBS=1 CMAKE_BUILD_PARALLEL_LEVEL=1 ...`
  - 手动覆盖路径:
    - `[install-pytorch3d] 使用外部指定的 MAX_JOBS=3`
    - `FAKE_PYTHON MAX_JOBS=3 CMAKE_BUILD_PARALLEL_LEVEL=3 ...`
- 结论:
  - 修复后的脚本已经会在进入 `pip install` 之前导出受控并发.
  - 默认值与手动覆盖两条路径都已验证通过.

### 综合判断
- 已观察到的现象:
  - 用户遇到的是 `pytorch3d` 编译失败, 同时 CPU 体感过高.
  - 当前入口此前没有任何 CPU 限流.
- 当前已验证结论:
  - “CPU 会被吃满”这件事在旧脚本里是成立的风险.
  - 本轮已把 `install-pytorch3d` 改成与 `flash-attn` 一致的受控并发策略.
  - 这会改善机器被打满的问题, 但 `RuntimeError: Error compiling objects for extension` 本身若仍出现, 还需要看更早的编译报错行继续定位.

## [2026-03-31 10:23:10 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] 笔记: 按限流参数重新启动 `install-pytorch3d`

### 来源22: 后台编译现场核对
- 验证命令:
  - `ps` / `pgrep` 搜索 `install-pytorch3d`、`ninja`、`gcc`、`cc1plus`
- 关键输出:
  - 当前没有残留的 `pytorch3d` 编译进程
- 结论:
  - 现场是干净的, 不需要盲目强杀无关进程.

### 来源23: 限流重启后的动态证据
- 启动命令:
  - `env MAX_JOBS=1 pixi run install-pytorch3d`
- 关键输出:
  - `[install-pytorch3d] 使用外部指定的 MAX_JOBS=1`
  - `Processing ./pytorch3d`
  - `Building wheel for pytorch3d (pyproject.toml) ...`
- 进程级旁证:
  - `python -m pip install --no-build-isolation ./pytorch3d`
  - `ninja -v -j 1`
  - 单个 `cc1plus` 编译进程在跑
- 结论:
  - 本轮重启已经真正进入“单 worker 编译”状态.
  - 当前不是多并发把 CPU 打满, 而是一个受控的慢编译过程.

## [2026-03-31 10:26:10 UTC] [Session ID: bootstrap_hang_20260331_pytorch3d_restart_11606] 笔记: 单 worker 受控编译结果

### 来源24: 这轮 `MAX_JOBS=1` 真实结束输出
- 关键输出:
  - `Using envvar MAX_JOBS (1) as the number of workers...`
  - `[1/36] c++ ... ball_query_cpu.cpp`
  - `c++: fatal error: Killed signal terminated program cc1plus`
  - `RuntimeError: Error compiling objects for extension`
- 结论:
  - 这轮已经结束, 但结果是失败.
  - 失败时并发已经被严格限制为 `1`, 所以这次不该再把问题归因到“CPU 并发太高”.
  - 当前更像是编译进程在单 worker 状态下仍被系统直接杀掉, 常见触发点是内存 / 容器资源限制.

### 来源25: 结束后的现场核对
- 关键输出:
  - 当前没有残留的 `install-pytorch3d` / `ninja` / `cc1plus` 进程
  - `pixi run python` 仍可 `import pytorch3d`, 版本是 `0.7.9`
- 结论:
  - 这轮失败已经完全退出, 现场是干净的.
  - 现有环境里仍保留着此前安装成功过的 `pytorch3d 0.7.9`, 这说明失败的是“这次重建 wheel”, 不是“当前环境里完全不可用”.

### 结论
- 单架构化已经被静态证据与动态证据同时验证.
- 这轮编译不再包含先前观察到的 `compute_90` / `compute_100` 多架构目标.

## [2026-03-25 19:27:10 UTC] [Session ID: bootstrap_hang_20260325_single_arch] 笔记: `install-pytorch3d` 改用浅克隆

### 现象
- 代理环境下直接执行原始 `install-pytorch3d` 时, `git clone` 5 分钟以上仍只推进到约 20% 出头.
- 实时速度多次掉到个位数 KiB/s, 明显不适合继续用全量历史拉取完成 bootstrap.

### 当前判断
- 这里的主要瓶颈不是 `pytorch3d` 编译, 而是 GitHub 全量仓库历史在代理链路上的下载体积.
- 对“只为安装依赖”这个场景来说, 全量历史不是必要条件.

### 修正动作
- 新增 `scripts/install_pytorch3d.sh`.
- 默认在本地没有有效 git 仓库时使用:
  - `git clone --depth 1 --filter=blob:none`
- 仍保持最终安装命令不变:
  - `python -m pip install --no-build-isolation ./pytorch3d`

### 结论
- 这次调整的目标是减少代理流量和首次 bootstrap 等待时间.
- 它不改变 `pytorch3d` 的源码安装语义, 只改变源码获取方式.

## [2026-03-25 11:40:00 UTC] [Session ID: bootstrap_hang_20260325_followup] 笔记: 入口复验与最终验证

### 来源17: `pixi run bootstrap`
- 动态结果:
  - `install-moge` 通过代理完成 `git clone --filter=blob:none`
  - `install-grounded-sam2` 使用 `--no-build-isolation` 后直接复用现有 Pixi 环境中的 `torch>=2.3.1`
  - `install-grounding-dino` 可正常重建 editable wheel
  - `install-flash-attn` 在入口链路中打印:
    - `cpu_total=22, reserved=4, MAX_JOBS=18`
    - `自动探测当前 GPU 架构: 120`
    - `Requirement already satisfied: flash-attn`
  - `install-pytorch3d` 复用现有 `pytorch3d` 仓库并成功重新构建安装
- 结论:
  - `bootstrap` 入口本身已经恢复为可执行状态.
  - 这次真正阻碍入口复验的, 已不再是 `flash-attn`, 而是 `install-grounded-sam2` 默认 build isolation 带来的重复大包下载.

### 来源18: 关键包 import 验证
- 验证命令:
  - `direnv exec ... pixi run python - <<'PY'`
- 关键输出:
  - `flash_attn    2.8.3`
  - `pytorch3d     0.7.9`
  - `sam2          <no __version__>`
  - `groundingdino <no __version__>`
  - `moge          <no __version__>`
- 结论:
  - 关键安装目标都已能在当前 Pixi 环境内直接 import.
  - 这说明本轮修复不只是“命令退出成功”, 运行时模块可见性也正常.

## [2026-03-31 11:34:19 UTC] [Session ID: codex-20260331T112445Z-45312] 笔记: `install-pytorch3d` Blackwell 兼容入口的上游依据与验证

### 来源26: PyTorch3D 官方 `INSTALL.md`
- 读取位置:
  - `pytorch3d/INSTALL.md`
  - 上游同源文档: https://github.com/facebookresearch/pytorch3d/blob/main/INSTALL.md
- 关键原文:
  - `pip install "git+https://github.com/facebookresearch/pytorch3d.git@stable"`
- 结论:
  - 官方文档明确提供了 released `stable` 的安装方式.
  - 当前仓库原脚本无条件追 `main`, 并不是官方唯一推荐路径.
  - 因此把默认源码引用改成 `stable`, 有明确上游依据.

### 来源27: FoundationPose issue #398 的 Blackwell 实战反馈
- 读取位置:
  - https://github.com/NVlabs/FoundationPose/issues/398
- 关键事实:
  - 2026-01-28 的回复明确提到:
    - CUDA 12.8+ / `sm_120` 没有可直接用的 PyTorch3D 预编译 wheel
    - 可工作的路径是:
      - system compiler
      - `CUDA_HOME=/usr/local/cuda-12.9`
      - `TORCH_CUDA_ARCH_LIST=12.0`
      - `pip install ... pytorch3d.git@stable`
- 结论:
  - 用户这次提供的方案不是孤立经验, 与公开上游讨论一致.
  - 但它成立的前提是“新 torch + 新 CUDA + Blackwell”这组环境真的具备.

### 来源28: 当前仓库环境与脚本差距
- 动态结果:
  - `pixi run python` 当前输出:
    - `torch 2.3.1`
    - `torch_cuda 12.1`
    - `cuda_available False`
- 静态结果:
  - 旧 `scripts/install_pytorch3d.sh` 只有:
    - 浅克隆
    - CPU 限流
    - `python -m pip install --no-build-isolation ./pytorch3d`
  - 没有:
    - 已安装短路
    - `stable` 引用控制
    - system compiler 绑定
    - `CUDA_HOME` 传递
    - `TORCH_CUDA_ARCH_LIST` 覆盖入口
- 结论:
  - 把 Blackwell 方案“原样硬编码”为默认值并不安全, 因为当前仓库自带环境还是 `torch 2.3.1 + cu121`.
  - 更稳的落地方式是:
    - 默认切到 `stable`
    - 默认优先 system compiler
    - 默认尝试推断 `CUDA_HOME`
    - `TORCH_CUDA_ARCH_LIST` 只在用户显式给出, 或者脚本能确认是 `torch 2.7+ / CUDA 12.8+ / sm_120` 时才自动写入 `12.0`

### 来源29: 本轮最小验证
- 验证命令:
  - `bash -n scripts/install_pytorch3d.sh`
  - `pixi run pytest tests/test_install_pytorch3d_script.py -q`
  - `pixi run install-pytorch3d`
- 关键输出:
  - `2 passed in 0.31s`
  - `[install-pytorch3d] 检测到已安装 pytorch3d 0.7.9, 跳过重复安装`
- 结论:
  - 新脚本至少已经验证了 3 件事:
    - 已安装时不会重复重编译
    - fresh install 路径会透传 `stable` / `CUDA_HOME` / `TORCH_CUDA_ARCH_LIST`
    - 仓库当前真实环境下可以安全短路成功

## [2026-03-31 12:06:41 UTC] [Session ID: codex-20260331T112445Z-45312] 笔记: `cc1plus` 被 Killed 的直接环境证据

### 来源30: 当前容器 / cgroup 内存限制核对
- 验证命令:
  - `free -h`
  - `rg 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo`
  - `cat /sys/fs/cgroup/memory.max`
  - `cat /sys/fs/cgroup/memory.current`
  - `cat /sys/fs/cgroup/memory.swap.max`
- 关键输出:
  - 宿主机总内存约 `1.0Ti`
  - `MemAvailable` 约 `977Gi`
  - 但当前 cgroup:
    - `memory.max = 2147483648`
    - `memory.current = 899203072`
    - `memory.swap.max = 0`
- 结论:
  - 失败不是“整台机器没内存”, 而是“当前容器 / cgroup 只有 2GiB 内存且无 swap”.
  - 在这种限制下, 即使 `MAX_JOBS=1`, 单个 `cc1plus` 编译进程也足以被系统直接杀掉.

### 结论更新
- 现象:
  - `MAX_JOBS=1`
  - 第一条纯 CPU C++ 编译就失败
  - `cc1plus` 被 `Killed`
- 已验证结论:
  - 根因候选已经从“并发太高”收敛为“当前 cgroup 内存上限过低”.
  - 继续在同一个 2GiB cgroup 里强制重装 `pytorch3d`, 预期收益很低.
