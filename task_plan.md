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

## [2026-03-16 03:36:00 UTC] 新任务启动: `demo_data/my3` 双 A800 0 号轨迹 60 步对比生成

### 目标
- 在不重跑 Step 1-5 的前提下, 基于现有 `my3` 控制图复跑双卡 Step 6.
- 生成 60 步版本, 与当前 10 步结果做对照.
- 保持其余关键约束不变:
  - 双 A800
  - `ulysses_degree=2`
  - `ring_degree=1`
  - `gpu_memory_mode=model_cpu_offload`

### 阶段
- [ ] 阶段1: 确认可复用产物与新的输出目录
- [ ] 阶段2: 执行双卡 60 步 Step 6
- [ ] 阶段3: 验证 60 步视频产物并回写记录

### 做出的决定
- 决定: 只复跑 Step 6.
  - 理由: `rendering_4D_maps` 已经存在且已验证有效, 没必要重复做深度估计和渲染.
- 决定: 新输出目录使用 `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare`.
  - 理由: 不覆盖当前 10 步结果, 便于后续并排比较.

### 状态
**目前在阶段1**
- 已确认可复用的 `rendering_4D_maps` 存在.
- 下一步直接启动双卡 60 步生成.

## [2026-03-16 04:17:00 UTC] 60 步对比生成完成

### 验证
- 60 步双卡 Step 6 已成功跑完.
- 最终输出文件存在:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare/generated_video_0.mp4`
- `ffprobe` 验证:
  - 分辨率: `1280x720`
  - 帧率: `16 fps`
  - 帧数: `81`
  - 时长: `5.0625 s`

### 状态
**当前 60 步任务完成**
- `my3` 当前已具备两版可对比结果:
  - 10 步: `demo_data/my3_dual_a800_test_v2/0/generated_videos/generated_video_0.mp4`
  - 60 步: `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare/generated_video_0.mp4`

## [2026-03-21 13:05:00 UTC] 新任务启动: 排查 `single_image_multi_trajectory.py` 在深度阶段强制使用 CUDA 失败

### 目标
- 搞清楚 `demo_data/my4` 这次运行失败的真实原因.
- 若问题在脚本设备选择逻辑, 给出并验证正确修复.
- 若问题纯属环境缺少可用 GPU, 让脚本更早给出清晰结论, 或在可接受时自动回退.

### 阶段
- [ ] 阶段1: 动态验证当前 Pixi 环境中的 GPU / CUDA 可见性
- [ ] 阶段2: 静态排查 `single_image_multi_trajectory.py` 与 `moge-v2_infer.py` 的设备选择逻辑
- [ ] 阶段3: 设计并实现最合理修复
- [ ] 阶段4: 运行验证命令, 回写日志与结论

### 现象
- 批处理入口始终调用:
  - `inference/moge-v2_infer.py ... --device cuda`
- 运行时在 `torch._C._cuda_init()` 报错:
  - `RuntimeError: No CUDA GPUs are available`
- 即使显式传入 `--moge_pretrained` 与 `--moge_version v2`, 报错保持不变.

### 当前主假设
- 主假设: 当前运行环境里 PyTorch 看不到可用 CUDA 设备, 但编排脚本没有在调用 MoGe 前做可用性判断, 仍无条件拼出 `--device cuda`.
- 备选假设: 机器有 GPU, 但当前 Pixi / Torch / 容器可见性配置异常, 使 `torch.cuda.is_available()` 为假.

### 验证计划
- 先动态执行:
  - `nvidia-smi`
  - `pixi run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"`
- 再静态检查:
  - `single_image_multi_trajectory.py` 中构造 MoGe 命令的位置
  - `moge-v2_infer.py` 中 `device` 的默认和错误处理

### 状态
**目前在阶段1**
- 已记录现象与候选假设.
- 下一步先拿动态证据确认当前环境里的 GPU 实际状态.

## [2026-03-21 13:18:00 UTC] 进入修复设计阶段

### 新结论
- 已有动态证据表明:
  - 物理 GPU 存在.
  - 但当前 CUDA runtime 对 PyTorch 不可用.
- 已有静态 / 外部资料线索表明:
  - 当前最强候选根因是 MIG 已开启但没有任何 MIG instance.

### 修复决策
- 不在仓库内偷偷改成 CPU fallback.
  - 理由: Step 6 VerseCrafter generation 仍然需要 CUDA, 只改 Step 1 会把失败延后, 不是根治.
- 在批处理入口增加 CUDA 预检.
  - 理由: 让这类环境问题在任务真正开始前就被清晰暴露, 并给出 MIG 定位提示.
- 为预检逻辑补单测.
  - 理由: 防止以后重构时又退回到深栈报错.

### 状态
**目前在阶段3**
- 下一步修改 `single_image_multi_trajectory.py`.
- 同时新增针对 CUDA 预检分支的测试.

## [2026-03-21 13:22:00 UTC] 修复与验证完成

### 已完成
- [x] 阶段1: 动态验证当前 Pixi 环境中的 GPU / CUDA 可见性
- [x] 阶段2: 静态排查 `single_image_multi_trajectory.py` 与 `moge-v2_infer.py` 的设备选择逻辑
- [x] 阶段3: 设计并实现最合理修复
- [x] 阶段4: 运行验证命令, 回写日志与结论

### 验证命令
- `nvidia-smi`
- `pixi run python -c "import torch; ..."`
- `pixi run pytest tests/test_single_image_multi_trajectory_cuda_preflight.py tests/test_single_image_multi_trajectory_smoke.py -q`
- `pixi run python inference/single_image_multi_trajectory.py ...`

### 验证结果
- `nvidia-smi` 能看到 A800, 但 `torch.cuda.is_available() == False`.
- `nvidia-smi` 显示:
  - `MIG Mode: Enabled`
  - `No MIG devices found`
- 新增的 CUDA 预检已在真实命令中生效.
- 单测结果:
  - `7 passed in 0.84s`
- 真实命令现在会在真正起重流程前直接报出清晰错误, 并指出 MIG 无实例这一高概率原因.

### 最终结论
- 已验证结论: 当前失败不是 `--moge_pretrained` / `--moge_version` 参数问题.
- 已验证结论: 当前环境中的物理 GPU 存在, 但 CUDA runtime 对 PyTorch 不可用.
- 当前最强并已有静态 + 动态证据支撑的结论是:
  - 该 A800 处于 MIG Enabled 但无 MIG device 的状态, 导致 VerseCrafter / MoGe 无法取得可执行 CUDA 设备.
- 仓库内已完成的改进是:
  - 在批处理入口增加前置 CUDA 预检, 避免再次掉进深层栈报错.

### 状态
**任务已完成**
- 代码改动和验证都已完成.
- 若要让这条命令真正跑通, 下一步需要处理系统层的 MIG 配置.

## [2026-03-21 15:46:30 UTC] 新任务启动: 排查 `my4` 双进程 Step 6 的 `CUDA error: invalid device ordinal`

### 目标
- 复现并定位 `torchrun --nproc-per-node=2 inference/versecrafter_inference.py` 在 FSDP 分片阶段触发的 `invalid device ordinal`.
- 给出基于证据的修复, 避免继续靠猜测改多卡初始化逻辑.

### 阶段
- [ ] 阶段1: 核对运行环境与 GPU 可见性
- [ ] 阶段2: 阅读 Step 6 与 FSDP 设备选择代码, 建立主假设与备选假设
- [ ] 阶段3: 做最小验证并实施修复
- [ ] 阶段4: 运行测试与真实命令验证

### 现象
- 用户提供的失败日志显示:
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
  - 但 rank1 在 `third_party/VideoX-Fun/videox_fun/dist/fsdp.py` 的 `FSDP(...)` 初始化阶段报 `RuntimeError: CUDA error: invalid device ordinal`.
- 失败点位于 FSDP 将参数移动到 `device_id` 时, 说明“脚本认定的目标设备”和“该进程真实可用的 CUDA 设备”之间可能不一致.

### 主假设
- 当前主假设: FSDP 包装时使用了全局 rank 或错误的 device_id, 而不是当前进程真实可用的 local device, 导致某个进程尝试移动到不存在的 `cuda:1`.
- 最强备选解释: 当前机器或当前 `torchrun` 环境实际只暴露了 1 个 CUDA device, 前面的 `device=cuda:1` 只是字符串构造成功, 但真正访问设备时才失败.
- 可推翻主假设的证据: 若环境验证显示每个进程都能稳定访问 `cuda:0/1`, 且 FSDP 实际拿到的 `device_id` 与本进程 local rank 完全一致, 那就需要转向检查 `xfuser` / `dist.init_process_group` / `CUDA_VISIBLE_DEVICES` 的传播链.

### 状态
**目前在阶段1**
- 已重建六文件上下文.
- 下一步先核对 GPU 可见性、`torchrun` 环境变量与相关源码实现.

## [2026-03-21 16:17:20 UTC] 阶段1完成, 进入修复设计

### 已完成
- [x] 阶段1: 核对运行环境与 GPU 可见性
- [x] 阶段2: 阅读 Step 6 与 FSDP 设备选择代码, 建立主假设与备选假设
- [ ] 阶段3: 做最小验证并实施修复
- [ ] 阶段4: 运行测试与真实命令验证

### 验证结果
- 宿主 Python 进程当前 `torch.cuda.device_count() == 1`.
- 最小复现实验 `torchrun --standalone --nproc-per-node=2 /tmp/torchrun_rank_probe.py` 已证明:
  - rank0: `local_rank=0`, count=1
  - rank1: `local_rank=1`, count=1
  - `device_name(1)` 对两个 rank 都是 `Invalid device id`
- 结合 `fuser.py` 中 `device = torch.device(f"cuda:{get_world_group().local_rank}")`, 已可确认当前直接触发条件是:
  - 请求了 2 个本地 worker, 但当前仅 1 张可见 CUDA 设备.

### 修复决策
- 决定: 不做静默单卡降级.
  - 理由: 会隐式改变用户请求的多卡拓扑.
- 决定: 增加双层预检.
  - 批处理入口先拦截 `nproc_per_node > visible_cuda_devices`.
  - Step 6 分布式入口再做本地 rank / visible device 校验, 并显式 `torch.cuda.set_device(local_rank)`.

### 状态
**目前在阶段3**
- 下一步开始修改 `single_image_multi_trajectory.py`、`videox_fun/dist/fuser.py` 与对应测试.

## [2026-03-21 13:40:00 UTC] 新任务启动: 为 `clockwise` 增加两个半径变体镜头动作

### 目标
- 使用 OpenSpec 新建一个变更, 描述新增两个镜头动作:
  - `clockwise_0.65`
  - `clockwise_1.5`
- 这两个动作的轨迹语义与现有 `clockwise` 一致, 但轨道半径分别为当前 `clockwise` 的 `0.65` 倍和 `1.5` 倍.
- 只创建 change 与读取第一个 artifact 模板, 不提前起草 artifact 内容.

### 阶段
- [x] 阶段1: 读取上下文文件与 skill 说明
- [ ] 阶段2: 确定 change 名称并检查是否已存在
- [ ] 阶段3: 创建 OpenSpec change
- [ ] 阶段4: 查看 change 状态并读取首个 artifact 指令
- [ ] 阶段5: 汇总 change 信息并等待用户决定是否继续起草 artifact

### 关键问题
1. 这个变更名应该强调“新增镜头动作”, 还是强调“clockwise 半径变体”.
2. 当前仓库是否已经存在同名或高度重叠的 change, 需要避免重复创建.

### 备选方向
- 方案A: `add-clockwise-radius-variants`
  - 优点: 直接表达“在现有 clockwise 基础上增加半径变体”.
- 方案B: `add-clockwise-camera-motion-presets`
  - 优点: 更强调用户可见层面的“新增镜头动作 preset”.

### 做出的决定
- 暂定优先尝试方案A: `add-clockwise-radius-variants`.
  - 理由: 用户需求核心不是新增任意镜头, 而是基于现有 `clockwise` 派生两个半径尺度变体.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段2**
- 已完成六文件上下文回读和 `openspec-new-change` skill 说明读取.
- 正在确认 change 名称可用, 然后创建 OpenSpec change.

## [2026-03-21 13:43:00 UTC] OpenSpec change 创建完成, 已到首个 artifact 指令阶段

### 验证
- 已创建 change:
  - `openspec/changes/add-clockwise-radius-variants/`
- OpenSpec 状态:
  - Schema: `spec-driven`
  - Progress: `0/4 artifacts complete`
  - `proposal`: ready
  - `design`: blocked by `proposal`
  - `specs`: blocked by `proposal`
  - `tasks`: blocked by `design, specs`
- 已读取首个 artifact:
  - `proposal`
  - 输出路径: `openspec/changes/add-clockwise-radius-variants/proposal.md`

### 做出的决定
- 决定: 使用默认 `spec-driven` workflow, 不额外传 `--schema`.
  - 理由: 用户没有指定其他 schema, 按 `openspec-new-change` skill 应使用默认流程.
- 决定: 采用 change 名称 `add-clockwise-radius-variants`.
  - 理由: 这个名字最准确表达“在现有 `clockwise` 基础上新增半径尺度变体”.

### 状态
**目前在阶段5**
- change 已创建完成.
- 已拿到 `proposal` 的模板与写作要求.
- 当前按 skill 要求停止在“等待用户决定是否继续起草第一个 artifact”.

## [2026-03-21 16:22:30 UTC] 修复与验证完成

### 已完成
- [x] 阶段1: 核对运行环境与 GPU 可见性
- [x] 阶段2: 阅读 Step 6 与 FSDP 设备选择代码, 建立主假设与备选假设
- [x] 阶段3: 做最小验证并实施修复
- [x] 阶段4: 运行测试与真实命令验证

### 实施内容
- 在 `inference/single_image_multi_trajectory.py` 中新增多卡 Step 6 预检:
  - 记录 `CUDA_VISIBLE_DEVICES`
  - 判断本次是否真的会进入多进程 Step 6
  - 若 `nproc_per_node > torch.cuda.device_count()` 则直接抛出清晰错误
- 在 `third_party/VideoX-Fun/videox_fun/dist/fuser.py` 中新增本地 worker 拓扑校验:
  - 读取 `LOCAL_RANK` / `LOCAL_WORLD_SIZE`
  - 校验 `LOCAL_RANK` 是否落在可见 GPU 范围内
  - 显式 `torch.cuda.set_device(local_rank)`
  - 修正日志里的 `classifier_free_guidance_degree` 格式串
- 在 `tests/test_single_image_multi_trajectory_cuda_preflight.py` 中补充多卡预检单测.

### 验证命令
- `./.pixi/envs/default/bin/python -m pytest tests/test_single_image_multi_trajectory_cuda_preflight.py tests/test_single_image_multi_trajectory_smoke.py -q`
- `./.pixi/envs/default/bin/python inference/single_image_multi_trajectory.py ... --ulysses_degree 2 --ring_degree 1 --nproc_per_node 2`
- `./.pixi/envs/default/bin/torchrun --nproc-per-node=2 inference/versecrafter_inference.py ...`
- `./.pixi/envs/default/bin/python -m py_compile inference/single_image_multi_trajectory.py tests/test_single_image_multi_trajectory_cuda_preflight.py third_party/VideoX-Fun/videox_fun/dist/fuser.py`

### 验证结果
- 单测:
  - `10 passed in 0.76s`
- 整链路入口现在会在 Step 1 前直接报出:
  - `多卡预检失败`
  - `torch.cuda.device_count(): 1`
  - `--nproc-per-node: 2`
- 直接运行 Step 6 现在会在 `set_multi_gpus_devices` 处更早失败:
  - `Distributed CUDA preflight failed: torchrun requested 2 local workers, but this process only sees 1 CUDA device(s).`
- `py_compile` 通过.

### 最终结论
- 已验证结论: 当前机器这次只暴露了 1 张 CUDA 设备, 与请求的 2 个本地 worker 不匹配.
- 已验证结论: 现在无论走批处理入口还是直跑 Step 6, 都能在更早的位置给出可读错误, 不再掉进 FSDP 深层 `invalid device ordinal` 栈.

### 状态
**任务已完成**
- 代码修改、测试验证、日志回写均已完成.

## [2026-03-21 16:45:30 UTC] 新任务启动: 解释 `my4` 为何报 `RuntimeError: xfuser is not installed`

### 目标
- 解释 `demo_data/my4` 当前命令里 `Preset left failed` 与 `RuntimeError: xfuser is not installed.` 的真实触发关系.
- 区分这是参数触发的功能依赖, 还是用户命令本身写错.
- 给出最直接可执行的后续处理路径.

### 阶段
- [ ] 阶段1: 回读历史上下文与已有排障记录
- [ ] 阶段2: 核对 `single_image_multi_trajectory.py` 与 `versecrafter_inference.py` 的调用链
- [ ] 阶段3: 核对 `xfuser` 在 `VideoX-Fun` 中的触发条件与依赖说明
- [ ] 阶段4: 汇总现象、假设、验证结论并答复用户

### 关键问题
1. 这次日志里的 `Preset left failed` 是真正根因, 还是只是批处理包装层对内部异常的摘要.
2. `xfuser` 是否只在多卡路径下需要, 以及当前参数是否明确进入了这条路径.

### 备选方向
- 方案A: 最完整解释.
  - 追完整调用链.
  - 结合 README 与代码说明为什么会报这个错误.
  - 给出继续跑通所需依赖或参数改法.
- 方案B: 快速解释.
  - 只说明 `xfuser` 没装, 多卡所以报错.
  - 不展开调用链.

### 做出的决定
- 决定: 先按方案A核对.
  - 理由: 用户问的是“为什么报告这个错误”, 需要把外层 `Preset left failed` 和内层真实异常拆开讲清楚.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段2**
- 已完成六文件上下文回读.
- 正在核对多轨迹入口、Step 6 推理入口与 `xfuser` 触发条件.

## [2026-03-21 16:55:00 UTC] 用户要求快进 `add-clockwise-radius-variants` 到 apply-ready

### 目标
- 使用 `openspec-ff-change` 流程, 直接为现有 change `add-clockwise-radius-variants` 生成全部实施前必需 artifacts.
- 目标状态是至少达到 schema 的 `apply.requires` 要求, 让后续可以直接进入实现.
- 生成顺序遵循 OpenSpec 的依赖链, 不跳过 proposal / design / specs / tasks.

### 阶段
- [ ] 阶段1: 读取 JSON 状态与 artifact 指令
- [ ] 阶段2: 调研现有代码与历史 change, 确定 capability 边界
- [ ] 阶段3: 创建 proposal
- [ ] 阶段4: 创建 design
- [ ] 阶段5: 创建 specs
- [ ] 阶段6: 创建 tasks 并达到 apply-ready
- [ ] 阶段7: 校验状态并回写日志

### 关键问题
1. 这次 capability 应该定义成“新增两个具体 preset”, 还是“支持可缩放的 clockwise 半径变体”.
2. 仓库当前没有 `openspec/specs/` 既有规格, 是否应把这次作为一个全新的 capability, 而不是修改已有 capability.
3. 除了轨迹数学本身, 用户可见面还涉及 CLI 展示、选择列表、文档和测试, 这些是否应纳入 tasks.

### 做出的决定
- 决定: 继续使用已存在的 change `add-clockwise-radius-variants`, 不新建同名 change.
  - 理由: `openspec-ff-change` guardrail 明确要求同名 change 已存在时应继续该 change.
- 决定: 先读取 OpenSpec JSON 指令, 再写 artifact.
  - 理由: 要严格按 schema 的模板、规则和输出路径来生成.

### 状态
**目前在阶段1**
- 正在读取 change 的 JSON 状态、apply 依赖与各 artifact JSON 指令.

## [2026-03-21 16:54:00 UTC] 报错归因核对完成

### 验证
- 已核对调用链:
  - `single_image_multi_trajectory.py` 会在 `nproc_per_node > 1` 时构造 `torchrun --nproc-per-node=... inference/versecrafter_inference.py`
  - `versecrafter_inference.py` 一进入即调用 `set_multi_gpus_devices(ulysses_degree, ring_degree)`
- 已核对触发条件:
  - 当前命令传入 `--ulysses_degree 2 --ring_degree 1 --nproc_per_node 2`
  - 这会强制进入多卡路径
- 已做动态验证:
  - `find_spec('xfuser') == True`
  - 但 `videox_fun.dist.fuser` 导入后 `get_sp_group is None`
  - 直接 `import xfuser` 目前会因 CUDA 初始化报 `DeferredCudaCallError`

### 结论
- `Preset left failed` 只是轨迹级包装日志, 不是根因.
- `RuntimeError: xfuser is not installed.` 的直接含义是:
  - 多卡依赖初始化失败.
- 这句报错在当前代码里是宽泛提示, 不一定严格等于“包缺失”.
  - 也可能是 `xfuser` 导入阶段被别的异常打断后, 被 `fuser.py` 统一掩盖.

### 阶段更新
- [x] 阶段1: 回读历史上下文与已有排障记录
- [x] 阶段2: 核对 `single_image_multi_trajectory.py` 与 `versecrafter_inference.py` 的调用链
- [x] 阶段3: 核对 `xfuser` 在 `VideoX-Fun` 中的触发条件与依赖说明
- [x] 阶段4: 汇总现象、假设、验证结论并答复用户

### 状态
**任务已完成**
- 已拿到静态代码证据与当前环境动态证据.
- 下一步只需向用户说明“外层摘要报错”和“内层真实触发条件”的关系, 并给出后续建议.

## [2026-03-21 17:05:00 UTC] 阶段1-2完成, 开始创建 proposal

### 已完成
- [x] 阶段1: 读取 JSON 状态与 artifact 指令
- [x] 阶段2: 调研现有代码与历史 change, 确定 capability 边界
- [ ] 阶段3: 创建 proposal
- [ ] 阶段4: 创建 design
- [ ] 阶段5: 创建 specs
- [ ] 阶段6: 创建 tasks 并达到 apply-ready
- [ ] 阶段7: 校验状态并回写日志

### 研究结论
- 当前仓库没有既有 `openspec/specs/` 能复用, 所以这次适合作为新的 capability.
- capability 名称确定为 `clockwise-radius-variants`.
- 需求核心是“新增两个命名 preset, 仅缩放 clockwise 半径, 不改变现有 clockwise 的语义与索引”.
- 这次不仅影响轨迹生成, 还影响 preset 列表、`--preset_indices`、dry-run 输出、README 与测试.

### 状态
**目前在阶段3**
- 正在创建 `proposal.md`.

## [2026-03-21 17:12:00 UTC] `proposal` 完成, 开始创建 `design` 与 `specs`

### 已完成
- [x] 阶段1: 读取 JSON 状态与 artifact 指令
- [x] 阶段2: 调研现有代码与历史 change, 确定 capability 边界
- [x] 阶段3: 创建 proposal
- [ ] 阶段4: 创建 design
- [ ] 阶段5: 创建 specs
- [ ] 阶段6: 创建 tasks 并达到 apply-ready
- [ ] 阶段7: 校验状态并回写日志

### 状态
**目前在阶段4-5**
- `proposal.md` 已创建.
- 正在创建 `design.md` 与 `specs/clockwise-radius-variants/spec.md`.

## [2026-03-21 17:16:00 UTC] `add-clockwise-radius-variants` 已达到 apply-ready

### 已完成
- [x] 阶段1: 读取 JSON 状态与 artifact 指令
- [x] 阶段2: 调研现有代码与历史 change, 确定 capability 边界
- [x] 阶段3: 创建 proposal
- [x] 阶段4: 创建 design
- [x] 阶段5: 创建 specs
- [x] 阶段6: 创建 tasks 并达到 apply-ready
- [x] 阶段7: 校验状态并回写日志

### 验证
- `openspec status --change "add-clockwise-radius-variants"` 返回:
  - `Progress: 4/4 artifacts complete`
  - `All artifacts complete!`
- `applyRequires = ["tasks"]` 已满足.
- 当前已创建 artifact:
  - `proposal.md`
  - `design.md`
  - `specs/clockwise-radius-variants/spec.md`
  - `tasks.md`

### 状态
**任务已完成**
- 该 change 已可直接进入实现阶段.
- 下一步应基于 `tasks.md` 开始修改代码和测试.

## [2026-03-22 07:21:40 UTC] 开始 apply `add-clockwise-radius-variants`

### 目标
- 按 `openspec/changes/add-clockwise-radius-variants/tasks.md` 完成 7 个待办.
- 在不破坏现有 `clockwise` 语义和索引 `0..5` 的前提下, 新增 `clockwise_0.65` 与 `clockwise_1.5`.
- 同步补齐 README、回归测试与 OpenSpec task 勾选状态, 最后跑聚焦测试验证通过.

### 阶段
- [ ] 阶段1: 回读六文件与 OpenSpec 上下文, 锁定实现边界
- [ ] 阶段2: 实现 preset 元数据与 orbit 半径变体
- [ ] 阶段3: 更新选择链路、dry-run / manifest 与 README
- [ ] 阶段4: 扩展 lib / smoke 测试
- [ ] 阶段5: 运行聚焦验证并回写日志

### 关键问题
1. 新增 preset 应该用元数据表达半径倍率, 还是继续堆名字分支.
2. 现有 canonical 索引、subset 选择与 dry-run 输出, 哪些地方会直接依赖 preset 列表长度和顺序.
3. orbit 半径比例要用什么动态证据锁定, 才能保证“只改半径, 不改语义”.

### 做出的决定
- 决定: 严格按 OpenSpec `design.md` 的数据驱动方案实现 orbit 半径倍率.
  - 理由: 这样能避免继续新增 `if trajectory_name == ...` 的特殊分支.
- 决定: 先读实现与测试文件, 再动代码.
  - 理由: 这次变化同时影响 preset 注册表、用户可见输出与测试口径, 不能凭记忆改.

### 状态
**目前在阶段1**
- 已确认 change: `add-clockwise-radius-variants`
- schema: `spec-driven`
- 进度: `0/7` tasks complete
- 正在回读实现文件与测试文件, 准备开始代码修改.

## [2026-03-22 07:24:30 UTC] 阶段1完成, 开始实现 preset / orbit / CLI 改造

### 已完成
- [x] 阶段1: 回读六文件与 OpenSpec 上下文, 锁定实现边界
- [ ] 阶段2: 实现 preset 元数据与 orbit 半径变体
- [ ] 阶段3: 更新选择链路、dry-run / manifest 与 README
- [ ] 阶段4: 扩展 lib / smoke 测试
- [ ] 阶段5: 运行聚焦验证并回写日志

### 新发现
- `inference/single_image_multi_trajectory_lib.py` 当前只定义了 6 个 preset, 且 `generate_blender_camera_trajectory()` 仍硬编码 `trajectory_name == "clockwise"`.
- `inference/single_image_multi_trajectory.py` 的 `--preset_indices` 仍写死为 `choices=range(6)`, 这是新增索引 `6` / `7` 的直接拦截点.
- dry-run 与 manifest 本身是跟着 `preset_specs` 走的, 只要 preset 列表和 CLI choices 更新, 展示链路大多会自动扩展.

### 当前动作
- 先把 orbit 半径倍率抽进 `TrajectoryPreset` 元数据.
- 再把 orbit 分发从“按名字硬编码”改成“按 preset.kind + 半径倍率”决定.
- 同步放开 `--preset_indices` 到新的 canonical 索引集合.

### 状态
**目前在阶段2-3**
- 正在修改 `single_image_multi_trajectory_lib.py` 与 `single_image_multi_trajectory.py`.

## [2026-03-22 07:30:30 UTC] 阶段2-3完成, 开始补测试与验证

### 已完成
- [x] 阶段1: 回读六文件与 OpenSpec 上下文, 锁定实现边界
- [x] 阶段2: 实现 preset 元数据与 orbit 半径变体
- [x] 阶段3: 更新选择链路、dry-run / manifest 与 README
- [ ] 阶段4: 扩展 lib / smoke 测试
- [ ] 阶段5: 运行聚焦验证并回写日志

### 已落地变更
- `TrajectoryPreset` 已新增 orbit 半径倍率元数据, canonical preset 已扩展到 8 个.
- `generate_blender_camera_trajectory()` 已改为按 `preset.kind` 决定 linear / orbit 分发, orbit 变体只缩放半径倍率.
- `--preset_indices` 已改为跟随 preset 索引集合, 不再硬编码 `range(6)`.
- README 已把单图批处理说明从 6 个 preset 同步到 8 个.

### 当前动作
- 扩展 lib 测试, 锁定新 preset 列表、movement distance 和 orbit 半径比例.
- 扩展 smoke 测试, 锁定 resume、dry-run 默认输出和 subset 选择输出.

### 状态
**目前在阶段4**
- 正在修改 `tests/test_single_image_multi_trajectory_lib.py` 与 `tests/test_single_image_multi_trajectory_smoke.py`.

## [2026-03-22 07:31:30 UTC] `add-clockwise-radius-variants` apply 完成

### 已完成
- [x] 阶段1: 回读六文件与 OpenSpec 上下文, 锁定实现边界
- [x] 阶段2: 实现 preset 元数据与 orbit 半径变体
- [x] 阶段3: 更新选择链路、dry-run / manifest 与 README
- [x] 阶段4: 扩展 lib / smoke 测试
- [x] 阶段5: 运行聚焦验证并回写日志

### 验证
- 静态验证:
  - `python3 -m py_compile inference/single_image_multi_trajectory_lib.py inference/single_image_multi_trajectory.py tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`
  - 结果: 通过
- 动态验证:
  - `pixi run pytest tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py -q`
  - 结果: `14 passed in 0.89s`

### 结果
- OpenSpec `tasks.md` 已全部勾选完成.
- 新增 preset:
  - `clockwise_0.65`
  - `clockwise_1.5`
- 现有索引 `0..5` 保持不变, 新增索引为 `6` 和 `7`.
- dry-run、subset 选择、manifest、README 与测试已同步到 8 个 preset.

### 状态
**任务已完成**
- 当前 change 已进入“可归档”状态.
- 如需继续 OpenSpec 流程, 下一步可执行 archive.

## [2026-03-22 08:05:00 UTC] 新需求: 增加 4 个对角线镜头 preset

### 目标
- 在现有单图多轨迹 preset 体系中新增:
  - `left_up`
  - `right_up`
  - `left_down`
  - `right_down`
- 保持已有 `0..7` 索引稳定, 新动作只追加到列表尾部.
- 满足用户约束:
  - `left_down`
  - `right_down`
  的向下幅度要明显小于“`up` 的反方向”, 先按一半实现, 避免镜头扎向地面.

### 阶段
- [ ] 阶段1: 回读现有 preset / 测试 / README, 锁定新增动作的命名和比例
- [ ] 阶段2: 把 linear 轨迹改造成数据驱动方向向量, 新增 4 个 preset
- [ ] 阶段3: 同步 README 与测试到新的 preset 集合
- [ ] 阶段4: 运行聚焦验证并回写日志

### 关键问题
1. 新动作应如何命名, 才和现有英文 preset 风格一致.
2. 新动作的 movement distance 应沿用哪一档, 才不会让对角镜头过弱或过强.
3. “向下只给一半” 应该落在公式哪一层, 才能既可读又容易回归验证.

### 做出的决定
- 决定: 命名采用 `left_up` / `right_up` / `left_down` / `right_down`.
  - 理由: 与当前 `left` / `right` / `zoom_in` 的下划线风格一致, 同时贴近用户中文顺序.
- 决定: 继续保留旧索引稳定, 新动作追加为 `8..11`.
  - 理由: 这样不会破坏当前已经存在的 `0..7` 语义和 dry-run / subset 用法.
- 决定: 把 linear 方向抽成 preset 元数据, 不继续增加 `if trajectory_name == ...`.
  - 理由: 这是当前最值得一起改良的结构点, 以后再加线性动作也只需要加数据.

### 状态
**目前在阶段1**
- 正在把新增对角镜头的命名、索引策略和向下半幅规则写入外部记忆.

## [2026-03-22 07:52:36 UTC] 4 个对角线镜头 preset 已完成

### 已完成
- [x] 阶段1: 回读现有 preset / 测试 / README, 锁定新增动作的命名和比例
- [x] 阶段2: 把 linear 轨迹改造成数据驱动方向向量, 新增 4 个 preset
- [x] 阶段3: 同步 README 与测试到新的 preset 集合
- [x] 阶段4: 运行聚焦验证并回写日志

### 验证
- 静态验证:
  - `python3 -m py_compile inference/single_image_multi_trajectory_lib.py inference/single_image_multi_trajectory.py tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`
  - 结果: 通过
- 动态验证:
  - `pixi run pytest tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py -q`
  - 第 1 轮现象:
    - `tests/test_single_image_multi_trajectory_smoke.py::test_resume_smoke_skips_existing_outputs_and_completes` 失败
  - 第 1 轮原因:
    - 测试把 manifest 的字符串索引键按字典序排序, 导致 `'10'` 排在 `'2'` 前面
  - 修正后结果:
    - `15 passed in 1.15s`

### 结果
- 默认 preset 集合已从 8 个扩展到 12 个.
- 新增 preset:
  - `left_up`
  - `right_up`
  - `left_down`
  - `right_down`
- 新索引为:
  - `8`
  - `9`
  - `10`
  - `11`
- 向上对角镜头的竖向比例按 `0.6` 落地.
- 向下对角镜头的竖向比例按 `0.3` 落地, 恰好是向上的一半.

### 状态
**任务已完成**
- 代码、README 和聚焦测试已同步完成.
- 如果下一步还要继续扩充镜头 preset, 当前 linear preset 已经改造成可直接加元数据的结构.
