# 任务计划: GitHub fetch 超时 / 握手失败排查

## [2026-03-25 17:26:30 UTC] [Session ID: unknown] [记录类型]: 支线任务启动

### 目标
- 解释当前仓库访问 GitHub 时报 `Connection timed out` / `gnutls_handshake() failed` 的真实原因.
- 给出用户可以直接执行的修复路径和验证命令.

### 阶段
- [x] 阶段1: 读取当前仓库远端与项目上下文
- [x] 阶段2: 做最小连通性与代理对照实验
- [x] 阶段3: 验证最可能的修复方向
- [x] 阶段4: 回写结论并交付

### 关键问题
1. 这是仓库 URL / 权限问题, 还是本机到 GitHub 的网络路径问题.
2. 当前 shell 中的代理变量是否真的参与了 Git 访问, 它是“必需但不稳定”, 还是“纯粹错误配置”.
3. 失败点是在认证阶段, 还是在 TLS / 代理握手阶段.

### 现象
- 用户提供的 VS Code Git 日志显示:
  - `fatal: unable to access 'https://github.com/raiscui/VerseCrafter.git/': Failed to connect to github.com port 443 ... Connection timed out`
  - `fatal: unable to access 'https://github.com/TencentARC/VerseCrafter.git/': Failed to connect to github.com port 443 ... Connection timed out`
- 当前仓库远端配置正常:
  - `origin = https://github.com/raiscui/VerseCrafter.git`
  - `upstream = https://github.com/TencentARC/VerseCrafter.git`

### 候选假设
- 主假设:
  - 这台机器直连 GitHub 443 不通, 必须依赖本地代理.
  - 但当前代理链路不稳定, 导致 Git 在 TLS 握手阶段被中途终止.
- 备选解释:
  - VS Code Git 扩展使用的环境变量与当前 shell 不一致, 造成“终端能访问, 扩展不能访问”的分裂现象.
- 可推翻主假设的证据:
  - 若在完全去掉代理变量后, `git ls-remote` 或 `curl https://github.com` 能稳定成功, 则说明直连其实可用.

### 备选方向
- 方案A: 最完整方案.
  - 修复当前代理链路, 让 VS Code Git 扩展和终端都能稳定通过 HTTPS 访问 GitHub.
  - 适合长期日常开发.
- 方案B: 先能用方案.
  - 临时绕过当前不稳定链路, 比如切换网络、重启代理、仅在命令行里显式设置代理变量, 或改成别的可用传输路径.
  - 适合先恢复 fetch / pull / push.

### 当前已验证结论
- 已确认当前 shell 存在:
  - `http_proxy=http://127.0.0.1:7897`
  - `https_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
  - `GIT_ASKPASS=.../vscode/.../askpass.sh`
- 已确认:
  - 去掉代理变量后, `curl -I https://github.com` 连接 8 秒后超时.
  - 去掉代理变量后, `git ls-remote https://github.com/raiscui/VerseCrafter.git HEAD` 超时.
  - 保留当前代理变量时, `git ls-remote` 能成功返回远端 `HEAD`.
  - 但 `git fetch --dry-run origin` 和 `git fetch --dry-run upstream` 会失败:
    - `gnutls_handshake() failed: The TLS connection was non-properly terminated.`
- 失败位置已用 `GIT_CURL_VERBOSE=1` 验证:
  - HTTP proxy `CONNECT github.com:443` 已成功.
  - 失败发生在真正 TLS 握手阶段, 还没进入 Git HTTP 请求体传输.

### 做出的决定
- 决定: 不去贸然修改仓库远端 URL.
  - 理由: 现有静态与动态证据都指向网络链路, 不是仓库地址错误.
- 决定: 不建议现在把当前代理配置固化进 Git 全局配置.
  - 理由: 当前代理链路对 `fetch` 仍不稳定, 先修代理本身更稳妥.
- 决定: 交付“先恢复可用, 再稳定集成”的两段式建议.
  - 理由: 用户眼前最需要的是恢复 `fetch`, 其次才是让 VS Code Git 扩展稳定复用同一条链路.

### 状态
**目前已完成交付**
- 已经排除“仓库 URL 配错”这一类问题.
- 已确认当前结论是“直连 GitHub 不通 + 当前代理链路对 Git fetch 的 TLS 握手不稳定”.
- 下一步由用户按建议检查 / 重启代理或切换网络路径, 再用文末命令复验.
