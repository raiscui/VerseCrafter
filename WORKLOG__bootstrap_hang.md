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
