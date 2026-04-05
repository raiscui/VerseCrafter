## [2026-03-25 17:26:30 UTC] [Session ID: unknown] 笔记: GitHub fetch 超时 / 握手失败排查

## 来源

### 来源1: 当前仓库与环境实测

- 命令:
  - `git remote -v`
  - `env | rg 'proxy|GIT_ASKPASS'`
  - `curl -I https://github.com`
  - `git ls-remote https://github.com/raiscui/VerseCrafter.git HEAD`
  - `git fetch --verbose --dry-run origin`
  - `GIT_CURL_VERBOSE=1 git fetch --verbose --dry-run origin`
- 要点:
  - 远端 URL 正常, 不是拼写错误.
  - 当前 shell 同时存在 HTTP 代理、SOCKS 代理和 VS Code `GIT_ASKPASS`.
  - 去掉代理后直连 GitHub 443 超时.
  - 保留代理后, `git ls-remote` 可成功.
  - 但 `git fetch --dry-run` 在 TLS 握手阶段失败.

### 来源2: 项目历史上下文

- 文件:
  - `archive/default_history/task_plan_2026-03-25_172630.md`
  - `archive/default_history/notes_2026-03-25_172630.md`
  - `archive/default_history/WORKLOG_2026-03-25_172630.md`
  - `archive/default_history/EPIPHANY_LOG_2026-03-25_172630.md`
- 要点:
  - 这个环境以前就出现过 `GIT_ASKPASS` 让 HTTPS Git 操作显得像“卡住”的情况.
  - 这个项目里还出现过一次 `git remote-https` helper 权限丢失, 当时根因不是网络.
  - 所以这次必须区分:
    - URL / 权限问题
    - 代理问题
    - 本地 Git helper 问题

## 综合发现

### 现象

- 用户看到的是 `Failed to connect to github.com port 443 after ...: Connection timed out`.
- 当前 shell 里, 更进一步的最小实验能复现两种路径:
  - 直连路径: 超时
  - 代理路径: `ls-remote` 成功, `fetch` TLS 握手失败

### 假设

- 当前机器直连 GitHub 443 不可用, 代理是必需前提.
- 代理链路本身不稳定, 或与当前 Git 2.34.1 + GnuTLS 组合兼容性不好.
- `GIT_ASKPASS` 不是本次 fetch 失败的主因, 因为失败发生在 TLS 握手前后, 还未进入认证交互.

### 已验证结论

- 这是“网络 / 代理 / TLS 链路”问题, 不是仓库地址错误.
- 这也是“直连不可用”的环境, 因为无代理时到 `github.com:443` 会超时.
- 当前最像根因的位置是:
  - 本地代理到 GitHub 的 CONNECT 已建立.
  - 但 TLS 握手被中途终止, 从而导致 `fetch` 失败.
- 代理来源也进一步缩小了:
  - `~/.bashrc` / `~/.profile` 中没有代理 export.
  - 当前目录链路上的 `.envrc` 与 `.envrc.private` 中也没有代理字段.
  - 更可能的来源是当前会话里曾手动 `export`, 或 VS Code 启动终端时注入.

### 对应建议

- 先处理代理, 再谈 Git:
  - 如果本机代理工具异常, 先重启它.
  - 如果 VS Code Git 扩展没有继承到正确代理环境, 先重启 VS Code 窗口或终端.
  - 如果只是命令行先恢复可用, 用显式环境变量执行 Git 命令.
- 若代理恢复后仍失败, 再考虑切到另一条网络路径:
  - 换一套代理端口 / 节点
  - 换网络
  - 换传输方式
