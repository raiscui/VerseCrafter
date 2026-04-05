## [2026-03-25 17:34:56 UTC] [Session ID: unknown] 笔记: 当前项目与远端最新状态比对

## 来源

### 来源1: 当前仓库本地状态

- 命令:
  - `git status --short --branch`
  - `git branch -vv`
  - `git submodule status --recursive`
- 要点:
  - 当前分支是 `main`
  - 当前跟踪的是 `origin/main`
  - 工作区不是干净状态
  - 子模块状态也不是完全对齐:
    - `third_party/VideoX-Fun` 处于 `+3811a69...`
    - `third_party/Grounded-SAM-2` 显示为 `b7a9c29...`

### 来源2: 远端最新提交比对

- 命令:
  - `git rev-parse HEAD`
  - `env GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/main`
  - `env GIT_TERMINAL_PROMPT=0 git ls-remote upstream refs/heads/main`
- 要点:
  - 本地 `HEAD = b9ccbd8bd592f33614144caab25efd1f12e3720e`
  - `origin/main = b9ccbd8bd592f33614144caab25efd1f12e3720e`
  - `upstream/main = 008693b52aa74367afb34d183046fecf88100bdc`

## 综合发现

### 现象

- 按当前跟踪远端 `origin/main` 来看, 本地已经是最新.
- 但上游 `upstream/main` 比当前 fork 更前.

### 已验证结论

- 如果“远端最新”指的是当前分支跟踪的 `origin/main`, 那本地无需更新.
- 如果用户实际想要“跟上 upstream 最新”, 那是一次不同的同步任务.
- 当前工作区脏状态和子模块偏移, 都让“直接同步上游”变得不适合默认自动执行.
