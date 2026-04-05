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
