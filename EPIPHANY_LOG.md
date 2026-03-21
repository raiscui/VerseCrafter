# 关键洞察

## [2026-03-15 17:18:00 UTC] 主题: 当前终端环境里的 VS Code `GIT_ASKPASS` 可能让 HTTPS `git push` 静默卡住

### 发现来源
- 在把 `third_party/VideoX-Fun` 推送到 `https://github.com/raiscui/VideoX-Fun` 的过程中, 普通 `git push my HEAD:main` 长时间无输出, 也没有立即失败.

### 核心问题
- 当前环境的 `GIT_ASKPASS` 指向 VS Code 的交互脚本:
  - `/root/.vscode-server/.../git/dist/askpass.sh`
- 在这个纯终端场景里, 它可能让 HTTPS 推送停在认证环节, 但终端侧没有清晰错误.

### 为什么重要
- 这种现象很容易被误判成:
  - GitHub 网络慢
  - `git push` 命令本身挂死
  - 远端仓库拒绝连接
- 如果没有记录, 以后做任何需要 HTTPS 写权限的 git 操作时, 都可能重复浪费排查时间.

### 当前结论
- 这类场景下更稳的方式是:
  - 保留 `GITHUB_TOKEN` 在环境变量里
  - 临时提供一个极小的 askpass 脚本
  - 配合 `GIT_TERMINAL_PROMPT=0` 与 `timeout`
- 这样可以让认证失败或成功都在有限时间内显性化.

### 后续讨论入口
- 下次如果再遇到 `git push` / `git fetch` 在 HTTPS 远端静默卡住, 先检查:
  - `env | cut -d= -f1 | rg 'GITHUB_TOKEN|GIT_ASKPASS'`
  - 当前 `GIT_ASKPASS` 的实际脚本来源

## [2026-03-16 03:32:00 UTC] 主题: VerseCrafter 的双卡问题会延迟到 Step 6 才暴露, 而 `moge_version=v2` 默认也可能悄悄换模型

### 发现来源
- 在 `demo_data/my3` 的双 A800 0 号视角测试中, 先后经历了:
  - `moge-2-vitl-normal` 下载卡住
  - `xfuser is not installed` 的多卡运行时失败

### 核心问题
- `inference/moge-v2_infer.py` 中 `model_version=v2` 的默认模型不是很多人本地常缓存的 `moge-2-vitl`, 而是 `Ruicheng/moge-2-vitl-normal`.
- VerseCrafter 的前 1~5 步即使没有 `xfuser` / `yunchang` 也能全部成功, 真正的双卡依赖缺失只会在 Step 6 `torchrun` 时才爆出来.

### 为什么重要
- 这两个点叠在一起时, 很容易让人产生错觉:
  - 误以为是命令写错了
  - 误以为是 GPU / NCCL 本身坏了
  - 误以为前置流程成功就代表双卡环境已经就绪
- 实际上, 一个是默认模型选择偏移, 另一个是延迟暴露的多卡依赖问题.

### 当前结论
- 如果本地已有旧版 `moge-2-vitl` 缓存, 又不想下载 `moge-2-vitl-normal`, 必须显式传 `--moge_pretrained`.
- 如果目标是 VerseCrafter 双卡测试, 环境检查不能只做到 `nvidia-smi`; 还必须额外验证:
  - `import xfuser`
  - `import yunchang`

### 未来风险
- 后续任何人第一次做双卡测试时, 都可能重复浪费十几分钟到数十分钟在:
  - 深度模型下载等待
  - Step 6 才暴露的依赖缺失

### 后续讨论入口
- 下次若再做 VerseCrafter 多卡测试, 优先先查:
  - `pixi run python -c "import xfuser, yunchang"`
  - 是否需要显式传 `--moge_pretrained`

## [2026-03-16 04:20:00 UTC] 主题: VerseCrafter 长步数任务的总时长不会按步数线性增长, TeaCache 在前 5 步后开始显著起效

### 发现来源
- 在 `demo_data/my3` 双 A800 0 号轨迹测试中, 已先后跑过:
  - 10 步版本
  - 60 步版本

### 核心问题
- 直觉上容易把 60 步估成 10 步耗时的 6 倍.
- 但当前 VerseCrafter 默认启用了 TeaCache, 并且配置为前 5 步不跳缓存, 后续才逐步吃到缓存收益.

### 为什么重要
- 如果不了解这个规律, 很容易:
  - 把长步数任务估时估得过高
  - 因为看到前几步很慢, 就误以为整轮都会一样慢
  - 错误地提前终止任务

### 当前结论
- 在当前 `my3` 双卡环境中:
  - 10 步大约用了 `8m56s`
  - 60 步大约用了 `33m55s`
- 这明显低于简单线性外推的 `~53m36s`.
- 更合理的经验是:
  - 前几步按“冷启动 + 无 TeaCache 收益”估时
  - 5 步之后再根据新速度修正总时长预估

### 后续讨论入口
- 下次评估 VerseCrafter 长步数任务耗时时, 不要在前 1~5 步就下结论.
- 应至少观察到 TeaCache 生效后的若干步再判断剩余时间.

## [2026-03-21 13:22:00 UTC] 主题: `nvidia-smi` 看得到 GPU, 不等于 Torch 就真的拿得到 CUDA 设备

### 发现来源
- 在 `demo_data/my4` 的 VerseCrafter 单图多轨迹排查中, 终端表面上能看到 A800, 但 PyTorch 仍报 `No CUDA GPUs are available`.

### 核心问题
- 对 MIG 机器来说, 物理卡可见只是第一层.
- 如果 GPU 处于 `MIG Mode: Enabled`, 但没有任何 `MIG device`, 应用层依然会表现得像“没有可用 CUDA GPU”.

### 为什么重要
- 这种状态极其容易误导排查方向.
- 人很容易把时间浪费在:
  - `--moge_pretrained` 是否写错
  - Torch / CUDA 版本是否不匹配
  - 命令参数是否拼错
- 实际上, 真正的问题可能在系统层的 MIG 实例状态.

### 当前结论
- `nvidia-smi` 可见 + `torch.cuda.device_count() == 1` 并不能单独证明 CUDA 可用.
- 还必须结合:
  - `torch.cuda.is_available()`
  - `torch.cuda.get_device_name(0)`
  - MIG 是否开启且是否真的创建了实例
- 对 VerseCrafter 这类长链路编排脚本, 最好在入口显式做 CUDA 预检.

### 未来风险
- 以后任何多步骤 CUDA 工作流, 只要运行在 MIG 机器上, 都可能重复踩到“前面看起来像有 GPU, 但真正跑时说没有设备”的坑.

### 后续讨论入口
- 如果下一步要真正把命令跑通, 先看当前机器是要:
  - 创建 MIG instance
  - 还是直接关闭 MIG
- 然后再重新验证 `torch.cuda.is_available()` 与 `torch.cuda.get_device_name(0)`.

## [2026-03-21 16:22:30 UTC] 主题: 多卡工作流里 `torch.cuda.is_available()` 为真, 仍可能因为本地 worker 数超过 `device_count()` 而失败

### 发现来源
- 在 `demo_data/my4` 的 Step 6 多进程推理排查中, 看到:
  - `torch.cuda.is_available() == True`
  - 但 `torch.cuda.device_count() == 1`
  - 同时命令请求 `torchrun --nproc-per-node=2`

### 核心问题
- 人很容易把 “CUDA 可用” 误解成 “多卡配置也可用”.
- 实际上, 多卡是否能跑通, 还取决于当前进程真实可见的本地 GPU 数是否足够承载每个 `LOCAL_RANK`.

### 为什么重要
- 如果只做 `cuda.is_available()` 预检, 仍然会把错误延后到 FSDP / DDP / 张量分配深层, 最终得到很难读的 `invalid device ordinal`.
- 对使用 `torchrun` 的工作流来说, 这是一类非常值得统一前置拦截的错误.

### 当前结论
- 多卡预检至少要同时检查:
  - `torch.cuda.is_available()`
  - `torch.cuda.device_count()`
  - `nproc_per_node` / `LOCAL_WORLD_SIZE`
  - `LOCAL_RANK < device_count`
- 仅检查 “有没有 CUDA” 不够.

### 后续讨论入口
- 后续若再给其他多卡入口做预检, 优先复用这条规则:
  - 先比较本地 worker 数和 `torch.cuda.device_count()`
  - 再进入真正的分布式初始化与 FSDP / DDP 封装
