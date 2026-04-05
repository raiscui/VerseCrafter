## [2026-03-25 17:26:30 UTC] [Session ID: unknown] 任务名称: GitHub fetch 超时 / TLS 握手失败排查

### 问题现象
- VS Code Git 日志中出现:
  - `Failed to connect to github.com port 443 ... Connection timed out`
- 当前 shell 中进一步验证时, `git fetch --dry-run origin` / `upstream` 还会出现:
  - `gnutls_handshake() failed: The TLS connection was non-properly terminated.`

### 原因分析
- 现象:
  - 直连 GitHub 443 超时.
  - 带代理时 `git ls-remote` 可成功.
  - 带代理时 `git fetch` 在 TLS 握手阶段失败.
- 已验证结论:
  - 当前不是仓库 URL 错误.
  - 当前不是 GitHub 权限拒绝.
  - 当前是“直连不可用”, 且“代理链路对 Git fetch 的 TLS 握手不稳定”.

### 修复建议
- 先修代理 / 网络路径:
  - 重启本机代理工具.
  - 切换代理节点或端口.
  - 若当前网络本身屏蔽 GitHub, 切到另一条网络路径.
- 代理恢复后, 再验证:
  - `env GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/raiscui/VerseCrafter.git HEAD`
  - `env GIT_TERMINAL_PROMPT=0 git fetch --verbose --dry-run origin`
  - `env GIT_TERMINAL_PROMPT=0 git fetch --verbose --dry-run upstream`
- 若终端验证通过, 但 VS Code 仍失败:
  - 重启 VS Code 窗口, 让 Git 扩展重新继承代理环境.
  - 必要时再单独处理 `GIT_ASKPASS` 的交互副作用.

### 验证证据
- `env -u http_proxy -u https_proxy -u all_proxy ... curl -I --connect-timeout 8 https://github.com`
  - 结果: 直连超时
- `env GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/raiscui/VerseCrafter.git HEAD`
  - 结果: 成功返回远端 `HEAD`
- `env GIT_TERMINAL_PROMPT=0 GIT_CURL_VERBOSE=1 git fetch --verbose --dry-run origin`
  - 结果: `CONNECT github.com:443` 成功后, TLS 握手被中途终止
