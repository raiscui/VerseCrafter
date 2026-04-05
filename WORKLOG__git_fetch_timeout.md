## [2026-03-25 17:26:30 UTC] [Session ID: unknown] 任务名称: GitHub fetch 超时 / TLS 握手失败排查

### 任务内容
- 排查 VS Code Git 日志中访问 `origin` / `upstream` 时出现的 GitHub HTTPS 超时问题.
- 区分仓库 URL、权限、代理、TLS 与本地 Git 环境这几类可能原因.

### 完成过程
- 先核对当前仓库 `origin` 与 `upstream` 远端, 确认 URL 都正常.
- 再读取当前 shell 的环境变量, 确认存在:
  - `http_proxy`
  - `https_proxy`
  - `all_proxy`
  - `GIT_ASKPASS`
- 做了 3 组最小实验:
  - 去掉代理后的 `curl` / `git ls-remote`
  - 保留代理后的 `git ls-remote`
  - 保留代理后的 `git fetch --dry-run` + `GIT_CURL_VERBOSE=1`
- 最终确认:
  - 直连 GitHub 443 不可用
  - 当前代理可以让部分 GitHub 请求成功
  - 但 `fetch` 在 TLS 握手阶段被中途终止

### 总结感悟
- 这类报错不能只看最表面的 “Connection timed out”.
- 真正有效的排查方法是把“直连路径”和“代理路径”拆开验证, 再用 `GIT_CURL_VERBOSE=1` 看失败卡在什么层.
