# 任务计划: 推送 VideoX-Fun 到 raiscui/VideoX-Fun

## [2026-03-15 17:06:00 UTC] 续档后新任务启动

### 目标
- 将 `third_party/VideoX-Fun` 当前需要发布的本地提交安全推送到 `https://github.com/raiscui/VideoX-Fun`.
- 不误动主仓库中与用户无关的改动, 并确认 submodule 目标提交在远端真实可达.

### 阶段
- [x] 阶段1: 六文件续档与持续学习
- [ ] 阶段2: 核对 `VideoX-Fun` 子模块状态、分支与远程
- [ ] 阶段3: 必要时补提交并推送 `VideoX-Fun`
- [ ] 阶段4: 校验远端可达性并回写日志

### 关键问题
1. `third_party/VideoX-Fun` 当前到底是工作区未提交修改, 还是已经生成了待推送提交但父仓库 gitlink 尚未同步.
2. 子模块目标远程是否已经指向 `raiscui/VideoX-Fun`, 以及当前 commit 是否已经存在于该远端.

### 备选方向
- 方案A: 最完整方案.
  - 处理子模块提交.
  - 推送子模块远端.
  - 若需要, 再更新父仓库 gitlink 并推送父仓库.
- 方案B: 先满足当前需求.
  - 仅把 `VideoX-Fun` 子仓库推到目标 GitHub 仓库.
  - 父仓库 gitlink 变化先保留在当前工作区.

### 做出的决定
- 决定: 先按方案B检查并执行.
  - 理由: 用户当前明确指向 `VideoX-Fun` 仓库本身, 没有要求同步推送 VerseCrafter 主仓库.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段2**
- 已完成六文件续档与上下文重建.
- 正在检查 `third_party/VideoX-Fun` 内部的提交状态、远程配置和待推送范围.

## [2026-03-15 17:10:00 UTC] 子模块远程状态核对完成

### 现象
- `third_party/VideoX-Fun` 当前工作区干净, 没有未提交修改.
- 子模块当前停在 detached HEAD:
  - `b7a3cc2ca6352b73042fd16a6e0afb341c2aa2b7`
- 该提交只修改了:
  - `videox_fun/models/__init__.py`
- 子模块上游 `origin/main` 和目标仓库 `https://github.com/raiscui/VideoX-Fun.git` 的 `main` 当前都在:
  - `ad72867c0f5fef880bcdbc85d5bfdeb2af65965b`
- `b7a3cc2` 不是 `ad72867` 的后继提交, 不能直接 fast-forward 推送到目标 `main`.

### 做出的决定
- 决定: 不直接把 detached HEAD 强推到远端 `main`.
  - 理由: 这样会覆盖目标仓库当前已经同步的上游历史, 风险不必要.
- 决定: 以当前 `main` 为基线重放这一个补丁, 再把新线性提交推到 `raiscui/VideoX-Fun`.
  - 理由: 这是满足用户目标且最安全的推送路径.

### 状态
**目前在阶段3**
- 已确认需要先把 `b7a3cc2` 的补丁移植到当前 `main`, 再执行推送与远端校验.

## [2026-03-15 17:18:00 UTC] 推送与收尾校验完成

### 验证
- 已在 `third_party/VideoX-Fun` 中生成线性提交:
  - `3811a6965d767bebcb8da1722835781291eb8d38`
- 已验证目标远端:
  - `git ls-remote https://github.com/raiscui/VideoX-Fun.git refs/heads/main`
  - 返回 `3811a6965d767bebcb8da1722835781291eb8d38`
- 已验证子模块本地保留分支:
  - `push-raiscui-videox-fun -> 3811a69`
- 已将子模块工作树检出恢复到原来的:
  - `b7a3cc2`
  - 这样父仓库不会额外增加新的 gitlink 偏移.

### 遇到的错误
- 普通 `git push my HEAD:main` 在当前终端环境里会静默卡住.
  - 决议: 排查后确认当前 `GIT_ASKPASS` 是 VS Code 交互脚本, 改为临时 token askpass 脚本 + `timeout 30s` 后成功推送.

### 状态
**目前在阶段4**
- `VideoX-Fun` 已成功推送到 `https://github.com/raiscui/VideoX-Fun`.
- 当前父仓库只保留本轮新增的上下文文件变化与 `archive/` 目录, 没有额外提交主仓库.

## [2026-03-15 17:25:00 UTC] 新任务启动: 推送 VerseCrafter 主仓库到 raiscui/VerseCrafter

### 目标
- 将当前 VerseCrafter 主仓库安全推送到 `https://github.com/raiscui/VerseCrafter.git`.
- 避免把主仓库推成 submodule 指针不可达的坏状态.

### 阶段
- [x] 阶段1: 核对主仓库分支、远端与待推送提交
- [x] 阶段2: 验证 submodule 远端可达性
- [ ] 阶段3: 修复主仓库中的 `VideoX-Fun` submodule 指针与 URL
- [ ] 阶段4: 提交主仓库并推送到 `my`

### 关键问题
1. 当前 `main` 相对 `my/main` 的领先提交里, 是否已经包含一个不可从 `.gitmodules` 远端检出的 submodule commit.
2. 若存在该问题, 最安全的修复是更新 gitlink 到 `3811a69`, 还是仅修改 `.gitmodules`.

### 做出的决定
- 决定: 不直接推送当前 `HEAD`.
  - 理由: 已验证 `HEAD` 中的 `third_party/VideoX-Fun = b7a3cc2`, 而 `.gitmodules` 仍指向 `aigc-apps/VideoX-Fun`, 这会让别人拉 submodule 时失败.
- 决定: 先把 `.gitmodules` 改到 `https://github.com/raiscui/VideoX-Fun.git`, 再把 gitlink 对齐到已推送可达的 `3811a69`.
  - 理由: 这是当前能保证主仓库 clone + submodule update 都正常的最稳方案.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段3**
- 已确认需要先修复主仓库 submodule 指针, 再做主仓库提交与推送.

## [2026-03-15 17:31:00 UTC] 主仓库推送完成

### 验证
- 已创建并推送主仓库提交:
  - `49cae461b7b13325ac11a65aea7ecbe9d29560eb`
  - 提交说明: `update videox-fun submodule`
- 已验证:
  - `git rev-parse HEAD`
  - `git ls-remote my refs/heads/main`
  两者都返回 `49cae461b7b13325ac11a65aea7ecbe9d29560eb`
- 推送输出:
  - `To https://github.com/raiscui/VerseCrafter.git`
  - `2cee0c6..49cae46  main -> main`

### 做出的决定
- 决定: 只提交 `.gitmodules` 和 `third_party/VideoX-Fun` 这两个修复项.
  - 理由: 当前工作区中的 `task_plan.md`、`notes.md`、`WORKLOG.md`、`archive/` 等属于本地上下文记录, 用户并未要求把这些一并推上主仓库.

### 状态
**目前在阶段4**
- VerseCrafter 已成功推送到 `https://github.com/raiscui/VerseCrafter.git`.
- 本地仍保留未提交的上下文文件与 `archive/`, 但它们没有进入这次远端提交.
