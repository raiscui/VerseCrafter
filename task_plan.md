# 任务计划: 默认主线上下文索引

## [2026-03-25 17:26:30 UTC] [Session ID: unknown] [记录类型]: 默认六文件续档并启用 Git 网络排查支线

### 续档原因
- 旧默认六文件已经累计较长, 其中旧 `task_plan.md` 超过 1000 行.
- 已按项目规则续档到 `archive/default_history/`, 避免后续上下文继续膨胀.

### 持续学习摘要
- 已回读旧默认六文件中的近期 Git / 网络相关记录.
- 当前可复用经验有 3 条:
  - VS Code 注入的 `GIT_ASKPASS` 可能让 HTTPS `git push` / `git fetch` 表现出“像网络挂住”的假象.
  - `git: 'remote-https' is not a git command` 在本项目里曾被验证为本地 Git helper 权限问题, 不是 GitHub 仓库不可达.
  - 诊断 GitHub 连通性时, `GIT_TERMINAL_PROMPT=0` 与 `GIT_CURL_VERBOSE=1` 是最小而有效的证据采集组合.

### 支线索引
- 本轮支线主题: GitHub `fetch` 超时 / TLS 握手失败排查
- 支线后缀: `__git_fetch_timeout`
- 当前使用文件:
  - `task_plan__git_fetch_timeout.md`
  - `notes__git_fetch_timeout.md`
  - `WORKLOG__git_fetch_timeout.md`
  - `ERRORFIX__git_fetch_timeout.md`

### 状态
**目前状态**
- 默认主线已完成续档.
- 当前网络问题转入支线 `__git_fetch_timeout` 继续处理.

## [2026-03-25 17:34:56 UTC] [Session ID: unknown] [记录类型]: 启用仓库同步支线

### 支线索引追加
- 新支线主题: 将当前 VerseCrafter 工作区同步到远端最新
- 支线后缀: `__git_update_latest`
- 当前使用文件:
  - `task_plan__git_update_latest.md`
  - `notes__git_update_latest.md`
  - `WORKLOG__git_update_latest.md`
  - `ERRORFIX__git_update_latest.md`

### 当前判断
- 当前工作区不是干净状态.
- 先确认本地 `HEAD`、`origin/main`、`upstream/main` 三者关系, 再决定是否真的需要拉取.

## [2026-03-25 09:49:30 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 启用 `pixi bootstrap` 高 CPU 排查支线

### 支线索引追加
- 新支线主题: `pixi run bootstrap` 导致高 CPU / 看起来卡死的原因排查
- 支线后缀: `__bootstrap_hang`
- 当前使用文件:
  - `task_plan__bootstrap_hang.md`
  - `notes__bootstrap_hang.md`

### 当前判断
- 用户已明确要求不要直接运行 `pixi run bootstrap`.
- 本轮先采用只读分析 + `pixi run --dry-run --frozen bootstrap` 的最小验证方式, 确认任务链与潜在高 CPU 来源.
### 备选方向
- 方案A: 只把内容留在六文件里.
  - 优点: 改动最少.
  - 缺点: 以后检索成本高, 新会话仍容易重复踩坑.
- 方案B: 分流沉淀到长期载体.
  - 优点: repo-specific 规则和跨项目经验都能被更早召回.
  - 缺点: 需要额外做一次文档和 skill 整理.

### 做出的决定
- 决定: 采用方案B.
  - 理由: 这轮提炼出的 `pixi` 版本核对规则和 `pgrep -af` 自匹配问题, 都已经具备明确触发条件和可验证解法, 继续只留在六文件里会浪费这轮发现.
- 决定: 旧 `task_plan.md` 直接续档到 `archive/`.
  - 理由: 本轮已完成持续学习回读, 旧文件已被覆盖分析, 且当前文件长度已经超过项目阈值.

### 状态
**任务已完成**
- 已完成六文件摘要.
- 已更新 `AGENTS.md` 与 `README.md`.
- 已新增 `self-learning.shell-pgrep-self-match-wait-loop`.
- 已把旧 `task_plan.md` 续档到 `archive/task_plan_2026-03-29_152846.md`.

## [2026-03-29 17:41:11 UTC] 新任务启动

### 目标
- 监督当前 `demo_data/nt1` 批处理的真实进度.
- 在 `nt1` 全部完成后, 立即接力启动 `demo_data/nt2`.
- 确认 `nt2` 已经成功进入新的生成流程, 并把本轮接力信息写回上下文文件.

### 阶段
- [x] 阶段1: 回读六文件并核对 `nt1` 当前现场
- [ ] 阶段2: 持续监督 `nt1` 直到批处理完成
- [ ] 阶段3: 按用户给定参数启动 `nt2`
- [ ] 阶段4: 验证 `nt2` 已稳定运行并回写日志

### 关键问题
1. 当前真正运行中的 `nt1` 进程是不是用户期望的那一轮, 而不是旧进程或等待脚本残留.
2. 以什么完成条件作为接力闸门最稳, 才不会出现过早启动 `nt2`.

### 备选方向
- 方案A: 以 `nt1` 主进程退出 + `manifest.json` 顶层状态为 `completed` 作为双条件闸门.
  - 优点: 最稳, 不容易误把中间子进程抖动当成已完成.
  - 缺点: 需要持续观察, 接力动作会比“只看一个 PID”更谨慎.
- 方案B: 只要当前 Step 6 子进程退出, 就立刻启动 `nt2`.
  - 优点: 接力更快.
  - 缺点: 风险高, 因为 `single_image_multi_trajectory.py` 在镜头切换时也会短暂更换子进程.

### 做出的决定
- 决定: 采用方案A.
  - 理由: 这条链路本身就是多阶段批处理, 只看单个 Step 6 worker 容易误判“这一镜头完成”成“整个批次完成”.

### 状态
**目前在阶段2**
- 已确认 `nt1` 主进程为 `173293`, 父层封装进程为 `173232`.
- 当前 `nt1` 正在 `demo_data/nt1/9/generated_videos` 执行双卡 `torchrun`.
- 已补充动态判断: `manifest.json` 在 Step 6 期间不会实时刷新, 现场进度应优先看真实 worker 与产物时间戳.
- 参考 `7` / `8` 号镜头的时间戳, 单个镜头的 Step 6 约为 `33-34` 分钟, 当前等待仍在合理区间内.
- 下一步持续监控 `manifest`、真实 PID 和 GPU 状态, 等满足完成闸门后立即启动 `nt2`.

## [2026-03-29 17:56:32 UTC] 状态更新

### 阶段
- [x] 阶段1: 回读六文件并核对 `nt1` 当前现场
- [ ] 阶段2: 持续监督 `nt1` 直到批处理完成
- [ ] 阶段3: 按用户给定参数启动 `nt2`
- [ ] 阶段4: 验证 `nt2` 已稳定运行并回写日志

### 状态
**目前仍在阶段2, 但监督已转为脱离会话的后台门闩**
- 当前 `nt1` 轨迹进度:
  - `generation_completed = 0-8`
  - `inflight = 9`
  - `pending = 10, 11`
- 已创建后台脚本:
  - `demo_data/nt1_to_nt2_handoff.sh`
- 已成功用 `setsid + nohup + /dev/null` 挂起独立监督进程:
  - PID: `252616`
  - Runner 输出: `demo_data/nt2_handoff_runner.out`
  - 监督日志: `demo_data/nt2_handoff_monitor.log`
- 当前会话内已确认后台脚本每 30 秒正常写入一次监督信息.
- 后续当 `nt1` 主进程退出且 `manifest` 顶层状态变为 `completed` 后, 该脚本会自动启动 `nt2`.

## [2026-03-30 00:55:09 UTC] 新任务启动

### 目标
- 监督当前正在运行的 `demo_data/nt2` 批处理真实进度.
- 在 `nt2` 完成后, 自动执行用户给出的 `demo_data/nt3` 命令.
- 确保新的接力逻辑也能脱离当前对话会话持续运行.

### 阶段
- [x] 阶段1: 回读六文件并核对当前活跃批次
- [ ] 阶段2: 为 `nt2 -> nt3` 建立并验证新的后台接力门闩
- [ ] 阶段3: 持续监督 `nt2` 直到批处理完成
- [ ] 阶段4: 验证 `nt3` 已被自动拉起并进入稳定运行

### 关键问题
1. 当前“正在运行的生成程序”到底是不是 `nt2`, 而不是旧的 `nt1` 门闩残留或其它孤儿进程.
2. 新的 `nt2 -> nt3` 接力逻辑, 怎样挂载才不会受当前会话结束影响.

### 备选方向
- 方案A: 新建独立的 `nt2 -> nt3` 后台门闩, 继续沿用“真实 PID + manifest completed”双条件闸门.
  - 优点: 与上一轮验证过的可靠方案一致, 风险最小.
  - 缺点: 会新增一个专用脚本.
- 方案B: 直接修改正在运行的 `nt1_to_nt2_handoff.sh`, 让它在 `nt2` 结束后继续接 `nt3`.
  - 优点: 少一个脚本文件.
  - 缺点: 会动到当前仍在运行的脚本本体, 风险高, 容易把现有链路搞断.

### 做出的决定
- 决定: 采用方案A.
  - 理由: 现有 `nt1_to_nt2_handoff.sh` 仍在运行并托管着当前 `nt2`, 现在直接改它属于高风险热修改. 先用新的独立门闩把 `nt3` 接上更稳.

### 状态
**目前在阶段2**
- 已确认 `nt1` 顶层 `manifest` 为 `completed`.
- 当前真实活跃批次是 `demo_data/nt2`, 主 Python 进程为 `276596`.
- 当前 `nt2` 进度:
  - `generation_completed = 0-8`
  - `inflight = 9`
  - `pending = 10, 11`
- `demo_data/nt3` 当前只有输入图 `c.png`, 还没有 `manifest.json`, 适合在完成闸门后干净启动.

## [2026-03-30 00:56:52 UTC] 状态更新

### 阶段
- [x] 阶段1: 回读六文件并核对当前活跃批次
- [x] 阶段2: 为 `nt2 -> nt3` 建立并验证新的后台接力门闩
- [ ] 阶段3: 持续监督 `nt2` 直到批处理完成
- [ ] 阶段4: 验证 `nt3` 已被自动拉起并进入稳定运行

### 状态
**目前在阶段3, 监督已转为脱离会话的后台门闩**
- 已创建后台脚本:
  - `demo_data/nt2_to_nt3_handoff.sh`
- 已成功用 `setsid + nohup + /dev/null` 挂起独立监督进程:
  - PID: `340573`
  - Runner 输出: `demo_data/nt3_handoff_runner.out`
  - 监督日志: `demo_data/nt3_handoff_monitor.log`
- 当前会话内已验证后台脚本连续两轮写入:
  - `00:56:12 nt2-alive`
  - `00:56:42 nt2-alive`
- 当前 `nt2` 仍在 9 号镜头双卡 Step 6:
  - `generation_completed = 0-8`
  - `inflight = 9`
  - `pending = 10, 11`
- 后续当 `nt2` 主进程退出且 `demo_data/nt2/manifest.json` 顶层状态变为 `completed` 后, 该脚本会自动启动 `nt3`.
### 支线索引
- 本轮支线主题: GitHub `fetch` 超时 / TLS 握手失败排查
- 支线后缀: `__git_fetch_timeout`
- 当前使用文件:
  - `task_plan__git_fetch_timeout.md`
  - `notes__git_fetch_timeout.md`
  - `WORKLOG__git_fetch_timeout.md`
  - `ERRORFIX__git_fetch_timeout.md`

### 状态
**目前状态**
- 默认主线已完成续档.
- 当前网络问题转入支线 `__git_fetch_timeout` 继续处理.

## [2026-03-25 17:34:56 UTC] [Session ID: unknown] [记录类型]: 启用仓库同步支线

### 支线索引追加
- 新支线主题: `pytorch3d` 构建阶段报 `No such file or directory: /usr/local/cuda-12.9/bin/nvcc`
- 支线后缀: `__pytorch3d_nvcc_path`
- 当前使用文件:
  - `task_plan__pytorch3d_nvcc_path.md`
  - `notes__pytorch3d_nvcc_path.md`
  - `WORKLOG__pytorch3d_nvcc_path.md`
  - `ERRORFIX__pytorch3d_nvcc_path.md`

### 当前判断
- 当前工作区不是干净状态.
- 先确认本地 `HEAD`、`origin/main`、`upstream/main` 三者关系, 再决定是否真的需要拉取.

## [2026-03-25 09:49:30 UTC] [Session ID: bootstrap_hang_20260325] [记录类型]: 启用 `pixi bootstrap` 高 CPU 排查支线

### 支线索引追加
- 新支线主题: `pixi run bootstrap` 导致高 CPU / 看起来卡死的原因排查
- 支线后缀: `__bootstrap_hang`
- 当前使用文件:
  - `task_plan__bootstrap_hang.md`
  - `notes__bootstrap_hang.md`

### 当前判断
- 用户已明确要求不要直接运行 `pixi run bootstrap`.
- 本轮先采用只读分析 + `pixi run --dry-run --frozen bootstrap` 的最小验证方式, 确认任务链与潜在高 CPU 来源.

## [2026-03-31 12:32:41 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 启用 `pytorch3d` 构建失败支线

### 支线索引追加
- 新支线主题: `pytorch3d` 构建阶段报 `No such file or directory: /usr/local/cuda-12.9/bin/nvcc`
- 支线后缀: `__pytorch3d_nvcc_path`
- 当前使用文件:
  - `task_plan__pytorch3d_nvcc_path.md`
  - `notes__pytorch3d_nvcc_path.md`
  - `WORKLOG__pytorch3d_nvcc_path.md`
  - `ERRORFIX__pytorch3d_nvcc_path.md`

### 当前判断
- 这次现象已经从“CPU 吃满像卡住”转成“编译入口明确引用了不存在的 CUDA 目录”.
- 先验证到底是当前 shell / `.envrc` / Pixi 环境里把 `CUDA_HOME` 指到了 `/usr/local/cuda-12.9`, 还是安装脚本把路径写死了.
