# 项目经验

## [2026-03-25 17:26:30 UTC] [Session ID: unknown] 主题: Git / GitHub 网络问题要先分清“直连失败”还是“代理链路失败”

### 适用场景
- `git fetch` / `git pull` / `git push` 在 GitHub HTTPS 远端上超时、握手失败、或表现得像“卡住”.

### 可复用经验
- 不要一看到 `unable to access https://github.com/...` 就认定是仓库 URL 或权限错了.
- 先用最小实验把路径拆开:
  - `env | rg 'proxy|GIT_ASKPASS'`
  - `env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY curl -I --connect-timeout 8 https://github.com`
  - `env GIT_TERMINAL_PROMPT=0 GIT_CURL_VERBOSE=1 git ls-remote <repo> HEAD`
- 如果“无代理直连超时”, 但“带代理 `ls-remote` 成功”, 说明这台机器依赖代理访问 GitHub.
- 如果随后 `git fetch` 在 `CONNECT` 成功后又报:
  - `gnutls_handshake() failed: The TLS connection was non-properly terminated.`
  这更像是代理 / TLS 链路不稳定, 而不是远端 URL 错误.

### 相关旁证
- VS Code 注入的 `GIT_ASKPASS` 可能让 HTTPS Git 命令表现出“像网络挂住”的假象.
- 若报错变成:
  - `git: 'remote-https' is not a git command`
  在本项目里曾被验证为本地 Git helper 权限问题, 不要误判成 GitHub 宕机.
