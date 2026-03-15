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
