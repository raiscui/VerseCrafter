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
