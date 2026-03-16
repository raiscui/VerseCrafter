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

## [2026-03-15 17:36:00 UTC] 用户要求继续推送到 `my/main`

### 现象
- 当前本地 `HEAD` 已前进到:
  - `21e15cb`
- 远端 `my/main` 仍停在:
  - `49cae46`
- `my/main..main` 之间当前只剩 1 个本地提交:
  - `21e15cb`
- 当前工作区干净, submodule 状态可达:
  - `third_party/VideoX-Fun = 3811a69`

### 做出的决定
- 决定: 继续执行上次任务里尚未完成的下一步, 直接把 `21e15cb` 推到 `my/main`.
  - 理由: 用户明确要求“继续推送”, 而当前真正未完成的就是这 1 个本地提交的远端同步.

### 状态
**目前在执行继续推送**
- 下一步使用已验证过的 token askpass 方式把 `21e15cb` 推到 `my/main`, 并回读远端哈希确认结果.

## [2026-03-16 03:06:00 UTC] 新任务启动: `demo_data/my3` 双 A800 生成 0 号视角视频测试

### 目标
- 使用 `demo_data/my3` 跑通一次多卡(双 A800)生成流程.
- 目标产物是 0 号视角视频.
- 约束参数为 `step=10` 与 `model_cpu_offload`.

### 阶段
- [ ] 阶段1: 核对 README、脚本与数据目录, 确认正确命令
- [ ] 阶段2: 检查运行环境与 GPU 可用性
- [ ] 阶段3: 执行双卡生成测试
- [ ] 阶段4: 校验输出产物、日志并回写六文件

### 关键问题
1. 当前仓库推荐的推理入口, 对于 `demo_data/my3` 的 0 号视角视频生成, 是直接使用 `inference.sh` 还是分步骤脚本.
2. 多卡与 `model_cpu_offload` 的组合, 在这个仓库中需要通过哪些命令行参数或环境变量开启.

### 备选方向
- 方案A: 完整按 README / 官方脚本路径执行.
  - 优点: 最贴近仓库原始工作流.
  - 风险: 运行时间可能更长, 中间步骤更多.
- 方案B: 在确认最终视频生成入口后, 仅运行完成 0 号视角所需的最小闭环.
  - 优点: 更快验证双卡推理链路.
  - 风险: 若跳过前置产物, 可能因为缺依赖文件而失败.

### 做出的决定
- 决定: 先按方案A核对官方工作流, 再决定是否裁剪到最小闭环.
  - 理由: 先保证命令正确, 再谈加速, 避免因为误解脚本入口导致无效测试.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段1**
- 已完成六文件上下文读取.
- 正在核对 README、`inference.sh`、`inference/` 目录与 `demo_data/my3` 数据结构, 以确定双卡 0 号视角视频的正确测试命令.

## [2026-03-16 03:12:00 UTC] 阶段1核对完成, 切换到环境检查与执行准备

### 现象
- README 与脚本代码都指向同一条结论:
  - 0 号视角可以通过 `single_image_multi_trajectory.py --preset_indices 0` 执行.
  - 多卡生成会在 `nproc_per_node > 1` 时自动走 `torchrun`.
- `nvidia-smi` 与 `pixi run python` 已确认当前环境可见 2 张卡:
  - `GPU 0 = NVIDIA A800-SXM4-80GB`
  - `GPU 1 = NVIDIA A800-SXM4-80GB`
- `third_party/VideoX-Fun/README.md` 提示 `ring_degree` 通信成本更高.
- `demo_data/my3` 是静态展厅图, 而脚本普通模式要求 `num_objects > 0`.

### 做出的决定
- 决定: 本次测试采用 `--camera_only`.
  - 理由: 这是当前最稳的纯相机运动闭环, 能避免因为默认分割未命中前景而让整个测试提前失败.
- 决定: 双卡参数采用 `ulysses_degree=2`, `ring_degree=1`, `nproc_per_node=2`.
  - 理由: 14B 模型 head 数可被 2 整除, 且上游文档明确指出 `ring_degree` 通信成本更高, 所以优先把并行度给 `ulysses_degree`.
- 决定: 提示词采用现有 `cmd.md` 中已验证过的“frozen-in-time futuristic AI exhibition hall”描述, 以匹配 `my3` 图像内容.
  - 理由: 这比临时猜一个新 prompt 更稳.

### 状态
**目前在阶段2**
- 已完成命令路径和双卡组合确认.
- 下一步执行正式生成测试, 目标输出目录为 `demo_data/my3_dual_a800_test`.

## [2026-03-16 03:10:00 UTC] 用户补充约束后调整执行方案

### 现象
- 上一轮正式执行在 MoGe 深度模型阶段卡住.
- 静态代码证据显示 `moge-v2_infer.py` 的默认 `v2` 预训练模型是 `Ruicheng/moge-2-vitl-normal`.
- 用户明确要求:
  - 不要下载 `moge-2-vitl-normal`
  - 改用本地缓存的 `moge-2-vitl` 权重
  - 参考已验证的 time-freeze 命令结构来改进当前测试命令

### 做出的决定
- 决定: 放弃继续复用上一次的 `demo_data/my3_dual_a800_test` 目录.
  - 理由: 该目录已经留下被中断的 `manifest.json`, 继续复用会污染这次验证.
- 决定: 改用新的输出目录 `demo_data/my3_dual_a800_test_v2`.
  - 理由: 让本轮验证结果和中断现场彻底隔离.
- 决定: 引入 `--moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/.../model.pt`.
  - 理由: 直接走本地权重, 避免再次触发 `moge-2-vitl-normal` 下载.
- 决定: 保留原始用户目标不变.
  - 保留双卡.
  - 保留 `preset_indices=0`.
  - 保留 `num_inference_steps=10`.
  - 保留 `gpu_memory_mode=model_cpu_offload`.

### 状态
**目前仍在阶段3**
- 已完成新命令 dry-run 验证.
- 正在确认本地 MoGe 权重路径真实存在, 确认后立即正式执行.

## [2026-03-16 03:14:00 UTC] 正式执行遇到多卡依赖缺失, 转入补环境

### 现象
- 改进后的命令已成功使用本地 `moge-2-vitl` 权重完成了深度估计, 没有再次触发 `moge-2-vitl-normal` 下载.
- `camera_only` 路径也已成功完成 Step 5 渲染.
- Step 6 双卡生成失败, 具体错误为:
  - `RuntimeError: xfuser is not installed.`
- 当前环境中模块状态已验证为:
  - `xfuser`: 缺失
  - `yunchang`: 缺失

### 做出的决定
- 决定: 不回退到单卡.
  - 理由: 用户明确要求双 A800 多卡测试.
- 决定: 按 `third_party/VideoX-Fun/README.md` 的上游建议补装:
  - `xfuser==0.4.2`
  - `yunchang==0.6.2`
- 决定: 安装完成后不重做前面 5 步, 直接复用 `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps` 重跑 Step 6.
  - 理由: 当前失败发生在最终生成阶段, 前置产物已经完整生成, 没必要重复浪费时间.

### 遇到的错误
- 错误: 多卡依赖缺失导致 `torchrun` 入口失败.
  - 决议: 先补齐 `xfuser` 与 `yunchang`, 再验证双卡生成.

### 状态
**目前仍在阶段3**
- 已确认阻塞点是双卡依赖缺失.
- 下一步安装多卡依赖, 然后仅重跑 Step 6.

## [2026-03-16 03:15:00 UTC] 多卡依赖安装完成, 转入 Step 6 复跑

### 验证
- `pixi run pip install xfuser==0.4.2 yunchang==0.6.2 ...` 已成功完成.
- 导入验证结果:
  - `xfuser`: 可导入
  - `yunchang`: 可导入, 版本 `0.6.2`
- 已确认可复用的 Step 5 产物存在:
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps/background_RGB.mp4`
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps/background_depth.mp4`
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps/3D_gaussian_RGB.mp4`
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps/3D_gaussian_depth.mp4`
  - `demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps/merged_mask.mp4`

### 做出的决定
- 决定: 不再通过整条 `single_image_multi_trajectory.py` 链路重跑.
  - 理由: 当前只剩 Step 6 未验证, 直接运行 `torchrun inference/versecrafter_inference.py` 更快, 也更聚焦.

### 状态
**目前仍在阶段3**
- 已补齐多卡依赖.
- 下一步直接复跑双卡 Step 6, 目标文件为 `demo_data/my3_dual_a800_test_v2/0/generated_videos/generated_video_0.mp4`.

## [2026-03-16 03:31:00 UTC] 阶段3与阶段4完成

### 验证
- 双卡 Step 6 已成功跑完 10 步采样.
- 最终输出文件存在:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos/generated_video_0.mp4`
- `ffprobe` 验证:
  - 分辨率: `1280x720`
  - 帧率: `16 fps`
  - 帧数: `81`
  - 时长: `5.0625 s`
- `--resume` 收尾后, `manifest.json` 已回写为成功状态.

### 状态
**目前在阶段4完成态**
- `demo_data/my3` 的双 A800 0 号视角视频测试已完成.
- 用户要求的关键约束均已满足:
  - 双卡
  - `preset_indices=0`
  - `num_inference_steps=10`
  - `gpu_memory_mode=model_cpu_offload`

## [2026-03-16 03:34:00 UTC] 用户要求将本次成功命令沉淀到 `cmd.md`

### 目标
- 将 `demo_data/my3` 双 A800 0 号视角成功命令记录到 `cmd.md`.
- 同时补充这次真正踩到的关键约束, 避免未来重复踩坑.

### 做出的决定
- 决定: 不只记录裸命令.
  - 理由: 这次成功依赖于几个关键修正点, 包括 `--moge_pretrained`、双卡依赖安装、以及必要时的代理环境变量; 只记命令不记上下文, 以后很容易重复失败.

### 状态
**目前在收尾记录阶段**
- 正在读取 `cmd.md` 当前结构.
- 下一步按现有文档风格追加新的命令段与注意事项.

## [2026-03-16 03:35:00 UTC] `cmd.md` 记录完成

### 验证
- 已将 `demo_data/my3` 双 A800 0 号轨迹成功命令追加到 `cmd.md`.
- 已补充:
  - 多卡依赖安装命令
  - 代理环境变量示例
  - 整链路命令
  - 只重跑 Step 6 的命令

### 状态
**当前收尾任务完成**
- 成功命令已沉淀到仓库文档.
- 后续可直接从 `cmd.md` 复制执行.
