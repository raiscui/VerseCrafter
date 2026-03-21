# 研究笔记

## [2026-03-15 17:06:00 UTC] 六文件摘要（用于续档后的持续学习）

### 任务目标（来自旧 `task_plan.md`）
- 已完成的主要工作集中在 VerseCrafter 环境治理、OpenSpec 落地、单图多轨迹脚本实现、真实推理验证与问题修复.
- 最近阶段的工作重点已经从“实现功能”转向“真实样本验证、参数收敛、文档沉淀和复跑命令整理”.

### 关键决定（来自旧 `task_plan.md`）
- `pixi` 复杂任务不能按 Bash 心智直接内联, 需要遵守 `deno_task_shell` 语法边界.
- VerseCrafter 单图多轨迹更适合先做编排层, 不急着把现有 CLI-first 脚本重构成库接口.
- 只相机运动需求最终通过 `camera_only` 模式落地, 而不是继续维护前景对象链路.

### 关键发现（来自旧 `notes.md`）
- 分析 bug 时持续遵守了“现象 -> 假设 -> 验证计划 -> 结论”的证据链模式, 这套写法已经证明可复用.
- `model_cpu_offload_and_qfloat8` 是当前已被真实动态验证通过的单卡稳态显存模式.
- `moge-2-vitl` 在当前主链路里可以作为深度估计的临时替代, 但并不等于对全仓库所有用途都完全等价.

### 实际变更（来自旧 `WORKLOG.md`）
- 已经落地:
  - `pixi.toml` 与 README 环境迁移
  - 单图 6 轨迹脚本
  - `camera_only` 模式
  - `VideoX-Fun` 可选音频依赖导入修复
- 已经完成多轮真实 GPU 样本验证, 并输出可复现命令与对比产物.

### 暂缓事项 / 后续方向（来自旧 `LATER_PLANS.md`）
- `pixi.lock` 仍待在完整 CUDA 环境下生成并提交.
- Step 6 仍有模型复用优化空间.
- MoGe 默认模型与 compare 工具仍有后续整理空间.

### 错误与根因（来自旧 `ERRORFIX.md`）
- `pixi` 任务解析错误的真正根因是 shell 方言边界, 不是 TOML 本身.
- Step 6 的 `librosa` 阻塞来自可选依赖被包初始化强导入.
- 单卡 OOM 的稳态解不是“只开 offload”, 而是“offload + qfloat8”.

### 重大风险 / 重要规律（来自旧 `EPIPHANY_LOG.md`）
- `pixi lock --dry-run` 对 PyPI 源码依赖存在验证边界, 容易被误判.
- OpenCV 坐标到 Blender 坐标的变换是多轨迹工作流里最容易被静默写错的地方.
- 研究型仓库的 CLI-first 结构决定了很多新需求更适合先做 orchestration, 再谈库化.

### 可复用点候选
- 研究型仓库里, `third_party/` 子模块一旦被修改, 要先确认子仓库提交是否已推远端, 再决定是否更新父仓库 gitlink.
- 对高成本推理链路, “最小复用已有产物”的重跑策略非常重要, 先复用 Step 5 再跑 Step 6 往往能省下大量时间.
- 对带可选依赖的模型包, 包初始化阶段不要强导入当前工作流不需要的子模块.

### 最适合写到哪里
- 现有根 `AGENTS.md` 已覆盖多数长期有效的仓库级约束.
- 本轮续档暂未发现必须额外同步到 `AGENTS.md`、`docs/` 或 `specs/` 的新规则.

### 是否提取或更新 skill
- 结论: 暂不新增 skill.
- 理由: 本轮续档提炼出的可复用知识, 目前已经分别沉淀在 `ERRORFIX`、`EPIPHANY_LOG`、README 和测试里, 暂无新的跨项目通用套路需要单独抽成 skill.

## [2026-03-15 17:06:00 UTC] 当前任务的已知事实

### 现象
- 主仓库当前为:
  - `main...origin/main [ahead 3]`
- 主仓库工作区显示:
  - `M third_party/VideoX-Fun`
- 根仓库当前远程:
  - `my -> https://github.com/raiscui/VerseCrafter.git`
  - `origin -> https://github.com/TencentARC/VerseCrafter.git`

### 当前假设
- 当前用户要推送的对象是 `third_party/VideoX-Fun` 这个子模块仓库本身, 不是 VerseCrafter 主仓库.
- 主仓库里的 `M third_party/VideoX-Fun` 既可能是子模块内部有未提交修改, 也可能只是 gitlink 指向了一个还没推远端的新 commit.

### 下一步验证
- 进入 `third_party/VideoX-Fun` 检查:
  - `git status --short --branch`
  - `git remote -v`
  - `git log --oneline --decorate -n 5`
  - `git branch -vv`
  - `git rev-parse HEAD`

## [2026-03-15 17:10:00 UTC] `VideoX-Fun` 子模块推送前的静态证据

### 已观察到的事实
- 子模块当前是干净工作区, 不是“有未提交代码”.
- 当前 detached HEAD 提交:
  - `b7a3cc2`
- 该提交作者是:
  - `raiscui <vdcoolzi@gmail.com>`
- 该提交只改了:
  - `videox_fun/models/__init__.py`
- 目标仓库 `raiscui/VideoX-Fun` 已存在, 且其 `main` 与子模块上游 `origin/main` 一致, 都在:
  - `ad72867`

### 当前判断
- 用户要推送的实质内容, 就是把此前的可选音频依赖修复发布到自己的 `VideoX-Fun` fork.
- 但本地提交 `b7a3cc2` 是基于旧提交 `246a0e3` 做出来的 detached commit.
- 因此如果直接把 `b7a3cc2` 推到 `raiscui/VideoX-Fun:main`, 会变成非快进更新.

### 计划中的最小安全动作
- 从当前 `main` 创建临时本地分支.
- 把 `b7a3cc2` cherry-pick 到该分支.
- 验证工作区干净后, 再把这个线性提交推到 `https://github.com/raiscui/VideoX-Fun.git` 的 `main`.

## [2026-03-15 17:18:00 UTC] `VideoX-Fun` 推送任务的动态验证结果

### 动态证据
- 从 `main` 创建分支:
  - `push-raiscui-videox-fun`
- `cherry-pick b7a3cc2` 时在 `videox_fun/models/__init__.py` 出现冲突.
- 冲突实质:
  - 上游 `main` 新增了更多模型导出.
  - 我们只需要保留“音频编码器改为可选依赖导入”这一补丁.
- 解决后生成新提交:
  - `3811a69`

### 推送验证
- 直接 `git push` 在当前环境里会卡住, 但远端哈希不变.
- 环境静态证据:
  - 存在 `GITHUB_TOKEN`
  - 存在 `GIT_ASKPASS`
  - 当前 `GIT_ASKPASS` 是 VS Code 的交互脚本
- 改用临时 askpass 脚本后执行:
  - `timeout 30s env GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/workspace/VerseCrafter/.codex/tmp_git_askpass_token.sh git push my HEAD:main`
- 关键输出:
  - `Everything up-to-date`
  - 但随后核对本地 `3811a69` 与远端 `main` 哈希完全一致
- 结论:
  - 这里的 `Everything up-to-date` 指的是 push 目标已经被这次推送更新到同一个提交, 最终状态正确.

### 最终结论
- `https://github.com/raiscui/VideoX-Fun` 的 `main` 现在已经是:
  - `3811a6965d767bebcb8da1722835781291eb8d38`
- 父仓库未被我顺手改写 gitlink.
- 子模块本地工作树已恢复到推送前的 `b7a3cc2`, 只是额外保留了一个可追溯的本地分支:
  - `push-raiscui-videox-fun`

## [2026-03-15 17:25:00 UTC] 推送 VerseCrafter 主仓库前的 submodule 风险验证

### 现象
- 主仓库当前 `HEAD` 记录:
  - `third_party/VideoX-Fun = b7a3cc2`
- `.gitmodules` 当前仍指向:
  - `https://github.com/aigc-apps/VideoX-Fun.git`
- `my/main` 与 `origin/main` 记录的旧 gitlink 都是:
  - `246a0e3`

### 动态证据
- `git ls-remote https://github.com/aigc-apps/VideoX-Fun.git b7a3cc2... 3811a69...`
  - 没有返回任何结果
- 结论: 无论 `b7a3cc2` 还是 `3811a69`, 都不在上游 `aigc-apps/VideoX-Fun` 远端命名空间中可直接解析.

### 当前判断
- 如果此时直接把 VerseCrafter `HEAD` 推到 `raiscui/VerseCrafter`, 别人在主仓库里执行:
  - `git submodule update --init --recursive`
  很可能会因为 `.gitmodules` 仍指向上游仓库而拿不到 `b7a3cc2`.
- 因此主仓库推送前必须同时修:
  - `.gitmodules` 的 submodule URL
  - 主仓库 gitlink 指针

## [2026-03-15 17:31:00 UTC] VerseCrafter 主仓库推送的最终动态证据

### 实施动作
- 将 `.gitmodules` 中 `third_party/VideoX-Fun` 改为:
  - `https://github.com/raiscui/VideoX-Fun.git`
- 将子模块检出切到:
  - `3811a6965d767bebcb8da1722835781291eb8d38`
- 在主仓库中只提交:
  - `.gitmodules`
  - `third_party/VideoX-Fun`
- 新提交:
  - `49cae46 update videox-fun submodule`

### 推送验证
- 使用临时 askpass 脚本执行:
  - `timeout 30s env GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/workspace/VerseCrafter/.codex/tmp_git_askpass_token.sh git push my main`
- 终端返回:
  - `To https://github.com/raiscui/VerseCrafter.git`
  - `2cee0c6..49cae46  main -> main`
- 二次回读验证:
  - 本地 `HEAD = 49cae46`
  - 远端 `my/main = 49cae46`

### 结论
- `https://github.com/raiscui/VerseCrafter` 已经包含本次主仓库修复提交.
- 这次推送避免了一个真实风险:
  - 主仓库引用了上游远端不可达的 submodule commit
- 本地上下文文件变更未被一并提交, 因此远端只包含项目本身需要的修复.

## [2026-03-16 03:12:00 UTC] `demo_data/my3` 双卡 0 号视角测试命令核对

### 来源
- `README.md`
- `inference/single_image_multi_trajectory.py`
- `inference/versecrafter_inference.py`
- `third_party/VideoX-Fun/README.md`
- 对 `demo_data/my3/generated-image (1).png` 的本地查看

### 已观察到的事实
- `demo_data/my3` 当前只有一张输入图:
  - `demo_data/my3/generated-image (1).png`
- 图像尺寸是 `1366x768`, 内容是偏静态的未来展厅场景, 更像“相机运动”测试场景.
- `README.md` 已明确说明 Step 6 的多卡入口是 `torchrun --nproc-per-node=N inference/versecrafter_inference.py`.
- `single_image_multi_trajectory.py` 在 `nproc_per_node > 1` 时会自动切到 `torchrun`.
- `single_image_multi_trajectory.py` 支持 `--preset_indices 0`, 可只跑 0 号视角.
- `single_image_multi_trajectory.py` 普通模式下要求 `gaussian_params.json` 的 `num_objects > 0`, 否则会报错:
  - `Zero-object scenes are not supported by this workflow version.`
- 同一脚本支持 `--camera_only`, 该模式会显式写入 `num_objects=0` 占位 JSON, 允许纯相机运动流程继续.
- `third_party/VideoX-Fun/README.md` 说明:
  - `ulysses_degree * ring_degree == GPU 数量`
  - `ring_degree` 通信成本高于 `ulysses_degree`
  - 对 14B 模型, 优先让 `ulysses_degree` 去吃并行度更合理

### 当前判断
- 主假设:
  - 对 `demo_data/my3` 这类展厅静态图, 本次“0 号视角视频测试”最稳妥路径是:
    - 使用 `single_image_multi_trajectory.py`
    - 限定 `--preset_indices 0`
    - 使用 `--camera_only`
    - 双卡配置设为 `ulysses_degree=2`, `ring_degree=1`, `nproc_per_node=2`
    - 生成参数使用用户要求的 `--num_inference_steps 10 --gpu_memory_mode model_cpu_offload`
- 备选解释:
  - 如果希望把展台中的车体、机械臂等也拆成独立前景对象, 则可以不用 `--camera_only`, 改成更贴图的 `object_prompt`, 但这会增加 Grounded-SAM-2 命中不稳定性.
- 能推翻主假设的证据:
  - 若 `camera_only` 模式在 Step 5 或 Step 6 出现契约错误.
  - 若用户明确要求保留独立物体 3D Gaussian 控制, 而不是纯相机运动.

### 动态验证
- 已执行 dry-run:
  - `pixi run python inference/single_image_multi_trajectory.py ... --preset_indices 0 --ulysses_degree 2 --ring_degree 1 --nproc_per_node 2 --num_inference_steps 10 --gpu_memory_mode model_cpu_offload --dry_run`
- Dry-run 已生成符合预期的最终 Step 6 命令:
  - `torchrun --nproc-per-node=2 inference/versecrafter_inference.py ... --ulysses_degree 2 --ring_degree 1 --num_inference_steps 10 --gpu_memory_mode model_cpu_offload`

## [2026-03-16 03:10:00 UTC] 用户中断后补充的命令修正

### 现象
- 上一轮执行在 `moge-v2_infer.py` 的默认预训练模型下载阶段停住.
- 代码静态阅读已确认 `inference/moge-v2_infer.py` 中 `model_version=v2` 的默认模型是:
  - `Ruicheng/moge-2-vitl-normal`

### 用户提供的新约束
- 不要下载 `moge-2-vitl-normal`.
- 改用本地缓存的 `moge-2-vitl` 权重文件.
- 参考命令中的其他稳定参数包括:
  - 更强的 `negative_prompt`
  - `camera_only`
  - `auto_center_depth_quantile=0.2`
  - `translation_reference_depth_scale=0.95`
  - `total_movement_distance_factor=1.5`

### 当前结论
- 对当前 `my3` 双 A800 测试, 应在保留用户原始目标的前提下改成:
  - `--moge_version v2`
  - `--moge_pretrained <本地 model.pt>`
  - 仍保持 `--preset_indices 0`
  - 仍保持双卡 `--ulysses_degree 2 --ring_degree 1 --nproc_per_node 2`
  - 仍保持用户原始测试约束 `--num_inference_steps 10 --gpu_memory_mode model_cpu_offload`

## [2026-03-16 03:14:00 UTC] 双卡 Step 6 失败定位

### 现象
- 新命令已经成功完成:
  - 深度估计
  - camera_only 共享占位输出
  - 0 号视角轨迹生成
  - 4D 控制图渲染
- 真正失败的位置在 Step 6 双卡生成入口 `torchrun --nproc-per-node=2 inference/versecrafter_inference.py`.

### 动态证据
- 日志报错:
  - `RuntimeError: xfuser is not installed.`
- 进一步验证:
  - `import xfuser` -> `ModuleNotFoundError`
  - `import yunchang` -> `ModuleNotFoundError`

### 静态证据
- `third_party/VideoX-Fun/README.md` 明确写出多卡前置依赖:
  - `xfuser==0.4.2`
  - `yunchang==0.6.2`

### 结论
- 当前失败不是命令参数错误, 也不是 `moge` 权重问题.
- 当前阻塞点是双卡运行时依赖缺失.
- 下一步应先为 Pixi 环境安装 `xfuser==0.4.2` 和 `yunchang==0.6.2`, 再从已生成的 `rendering_4D_maps` 继续重跑 Step 6.

## [2026-03-16 04:17:00 UTC] `demo_data/my3` 双卡 60 步 Step 6 复跑结果

### 现象
- 基于现有 `rendering_4D_maps` 直接重跑双卡 Step 6.
- 参数保持不变, 仅将 `num_inference_steps` 从 `10` 提升到 `60`.

### 动态证据
- 命令成功退出 `code 0`.
- 终端最终输出:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare/generated_video_0.mp4`
- 60 步采样总耗时约 `33m55s`.
- 进度表现上, TeaCache 在前 5 步后开始明显降低单步耗时, 所以 60 步总时长没有线性膨胀到 10 步的 6 倍.

### 产物验证
- 60 步视频路径:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos_steps60_compare/generated_video_0.mp4`
- `ffprobe` 验证:
  - `1280x720`
  - `81` 帧
  - `16 fps`
  - `5.0625 s`

### 当前结论
- `demo_data/my3` 的双 A800 0 号轨迹在 `num_inference_steps=60`、`gpu_memory_mode=model_cpu_offload` 下也已成功跑通.
- 当前目录里已经同时有可对比的两版结果:
  - 10 步: `generated_videos/generated_video_0.mp4`
  - 60 步: `generated_videos_steps60_compare/generated_video_0.mp4`

## [2026-03-21 13:12:00 UTC] `my4` CUDA 初始化失败的动态证据

### 已验证现象
- `nvidia-smi` 能看到物理 GPU:
  - `NVIDIA A800-SXM4-80GB`
- 但 Pixi 环境里的 PyTorch 不能真正初始化 CUDA:
  - `torch.cuda.is_available() -> False`
  - `torch.cuda.device_count() -> 1`
  - `torch.cuda.get_device_name(0)` 报:
    - `RuntimeError: No CUDA GPUs are available`
  - `torch.tensor([1.0], device="cuda")` 同样报:
    - `RuntimeError: No CUDA GPUs are available`

### 新假设
- 单纯说“没有 GPU”并不准确.
- 更像是: NVML / 驱动层能看到物理卡, 但 CUDA 运行时拿不到可执行计算的设备实例.

### 静态 + 外部资料线索
- `nvidia-smi` 输出里明确显示:
  - `MIG Mode: Enabled`
  - `No MIG devices found`
- NVIDIA MIG User Guide 写明:
  - “Without creating GPU instances (and corresponding compute instances), CUDA workloads cannot be run on the GPU.”
- 这与当前现象吻合:
  - 物理卡在
  - CUDA workload 仍报无可用 GPU

### 当前判断
- 当前最强主假设是:
  - 这张 A800 被切到了 MIG 模式, 但还没有创建 GPU / Compute instance, 所以 VerseCrafter / MoGe 这类 CUDA 程序都无法真正拿到可执行设备.
- 备选解释仍然是:
  - 还存在别的 CUDA 运行时初始化问题.
- 但要推翻当前主假设, 至少要出现这样的证据之一:
  - 创建 MIG instance 或关闭 MIG 后, PyTorch 仍旧 `No CUDA GPUs are available`
  - 或在另一个已知正常的 CUDA 程序里也表现为完全不同的底层错误.

## [2026-03-21 16:16:30 UTC] `my4` Step 6 `invalid device ordinal` 的证据链

### 现象
- 用户日志中, `torchrun --nproc-per-node=2` 进入 `inference/versecrafter_inference.py` 后:
  - rank0 打印 `device=cuda:0`
  - rank1 打印 `device=cuda:1`
- rank1 在 `third_party/VideoX-Fun/videox_fun/dist/fsdp.py` 的 `FSDP(..., device_id=device)` 初始化阶段失败:
  - `RuntimeError: CUDA error: invalid device ordinal`

### 静态证据
- `third_party/VideoX-Fun/videox_fun/dist/fuser.py:set_multi_gpus_devices`
  - 当 `ulysses_degree > 1 or ring_degree > 1` 时, 会:
    - `dist.init_process_group("nccl")`
    - `device = torch.device(f"cuda:{get_world_group().local_rank}")`
- `third_party/VideoX-Fun/videox_fun/dist/fsdp.py:shard_model`
  - 会把上面的 `device` 直接作为 `FSDP(..., device_id=device)`.
- 这说明 FSDP 最终访问的设备索引直接来自 `LOCAL_RANK` / `local_rank` 语义.

### 动态证据
- 当前宿主 Python 进程里:
  - `torch.cuda.is_available() == True`
  - `torch.cuda.device_count() == 1`
  - 仅有 `cuda:0`
- 最小复现实验:
  - `torchrun --standalone --nproc-per-node=2 /tmp/torchrun_rank_probe.py`
- 关键输出:
  - `rank=0 local_rank=0 world_size=2 count=1 avail=True`
  - `rank=1 local_rank=1 world_size=2 count=1 avail=True`
  - 两个进程访问 `device_name(1)` 都报 `AssertionError('Invalid device id')`

### 当前判断
- 已验证结论:
  - 当前失败不是 VerseCrafter 权重加载本身的问题.
  - 当前失败也不是 FSDP auto_wrap 深层逻辑先天坏掉.
  - 真正的直接触发条件是: 本机当前只暴露 1 张 CUDA 设备, 但 Step 6 请求了 2 个本地 worker.
- 主修复方向:
  1. 在批处理入口 `single_image_multi_trajectory.py` 里提前检查 `nproc_per_node <= torch.cuda.device_count()`.
  2. 在 `videox_fun/dist/fuser.py` 里补本地 rank / 可见 GPU 数校验, 并显式 `torch.cuda.set_device(local_rank)`, 让直接调用 Step 6 的场景也能更早失败并报清楚原因.
- 备选方向:
  - 静默自动降级为单卡.
- 为什么暂不选备选方向:
  - 这会偷偷改变用户请求的并行拓扑和显存 / 速度特征.
  - 对多卡工作流, 静默降级比显式失败更容易制造后续误解.

## [2026-03-21 16:52:30 UTC] `my4` 的 `xfuser is not installed` 报错核对

### 现象
- 用户在 `2026-03-21 16:40:34 UTC` 的日志里看到:
  - `Preset left failed`
  - `RuntimeError: xfuser is not installed.`
- 乍看像是当前环境单纯缺少 `xfuser` 包.

### 静态证据
- `inference/single_image_multi_trajectory.py` 中:
  - `args.nproc_per_node` 默认等于 `ulysses_degree * ring_degree`
  - `build_generation_command()` 在 `nproc_per_node > 1` 时会走:
    - `torchrun --nproc-per-node=... inference/versecrafter_inference.py`
- `inference/versecrafter_inference.py` 中:
  - 一进入主流程就执行 `set_multi_gpus_devices(ulysses_degree, ring_degree)`
- `third_party/VideoX-Fun/videox_fun/dist/fuser.py` 中:
  - 顶部先 `import xfuser`
  - 但用了 `except Exception` 把任意导入异常都吞掉
  - 之后只要 `get_sp_group is None`, 就统一抛:
    - `RuntimeError("xfuser is not installed.")`
- `third_party/VideoX-Fun/README.md` 也明确写了:
  - 多卡推理需要安装 `xfuser==0.4.2` 和 `yunchang==0.6.2`

### 动态证据
- 当前环境里 `importlib.util.find_spec('xfuser') is not None`:
  - 结果为 `True`
- 但把 `third_party/VideoX-Fun` 加入 `sys.path` 后导入 `videox_fun.dist.fuser`:
  - `get_sp_group is None`
  - `init_distributed_environment is None`
- 进一步直接 `import xfuser` 时, 当前环境实际报错不是 `ModuleNotFoundError`, 而是:
  - `torch.cuda.DeferredCudaCallError`
- `xfuser/envs.py` 第 70~71 行会在导入阶段直接执行:
  - `device = torch.device("cuda" if torch.cuda.is_available() else "cpu")`
  - `gpu_name = torch.cuda.get_device_name(device)`
- 这说明:
  - 只要 `xfuser` 导入阶段因为 CUDA 初始化等原因抛异常, `fuser.py` 也会把它伪装成“xfuser 没安装”.

### 当前结论
- 已验证结论1:
  - `Preset left failed` 不是根因.
  - 它只是 `single_image_multi_trajectory.py` 对单个轨迹失败的包装日志.
- 已验证结论2:
  - 你这次命令明确进入了多卡 Step 6 路径.
  - 原因是 `--ulysses_degree 2 --ring_degree 1 --nproc_per_node 2`.
- 已验证结论3:
  - `RuntimeError: xfuser is not installed.` 的直接触发点, 是 `set_multi_gpus_devices()` 发现 `xfuser` 分布式能力没有初始化成功.
- 已验证结论4:
  - 这句报错并不严格等于“包没装”.
  - 它也可能表示“包在, 但导入阶段已经因为别的异常失败了”.

### 备选解释与推翻条件
- 主解释:
  - 当次失败是多卡路径触发后, `xfuser` 能力不可用.
  - 这可能是未安装, 也可能是导入期 CUDA 异常被掩盖.
- 备选解释:
  - 用户只是参数写错.
- 目前备选解释不成立的原因:
  - 调用链和日志都能对应到多卡分支的固定代码路径.
  - 不是参数拼写错误导致的未知行为.

## [2026-03-21 16:58:00 UTC] OpenSpec fast-forward 调研: `clockwise` 半径变体

### 现象
- 当前 `inference/single_image_multi_trajectory_lib.py` 中 `TRAJECTORY_PRESETS` 只有 6 个 preset:
  - `left`
  - `right`
  - `up`
  - `zoom_out`
  - `zoom_in`
  - `clockwise`
- `clockwise` 轨迹的真正位移生成逻辑在 `_generate_clockwise_offsets_cv(...)`.
- 当前圆轨迹半径由 `radius_x_factor` 和 `radius_y_factor` 共同控制, 默认值分别是 `0.15` 与 `0.10`.
- 当前 `generate_blender_camera_trajectory(...)` 只把 `trajectory_name == "clockwise"` 作为 orbit 分支入口.
- README 目前明确写的是 “six deterministic presets”, 与新增两个 preset 后的用户可见行为不一致.
- 现有测试已锁定 `clockwise` 的 Blender x-z 平面 orbit 行为, 但还没有覆盖“半径变体相对基准半径的比例关系”.

### 初步结论
- 这次变更不是单纯多加两个字符串.
- 它至少会影响:
  - preset 注册表
  - 轨迹生成分发逻辑
  - CLI / smoke test 中的 preset 数量预期
  - README 中的用户文案
  - 新的比例关系单测
- 由于 `openspec/specs/` 目前为空, 这次 capability 更适合作为一个新的 capability 来建 spec, 而不是修改已有 capability.

### 候选 capability 命名
- `clockwise-radius-variants`
  - 更贴近本次具体需求
- `multi-trajectory-camera-presets`
  - 范围更宽, 但对本次 change 来说略大

### 当前倾向
- proposal 的 New Capability 先用 `clockwise-radius-variants`.
- spec 聚焦“系统必须提供三个 clockwise 半径档位中的两个新增档位, 且轨迹语义保持一致, 仅半径按倍率变化”.

### 补充动态验证
- 最小复现实验:
  - 仅导入 `videox_fun.dist.fuser` 并调用 `set_multi_gpus_devices(2, 1)`
- 输出:
  - `RuntimeError: xfuser is not installed.`
- 这证明:
  - 即使不加载 VerseCrafter 权重、不进入采样流程, 只要命中多卡初始化层, 当前环境就会先在这里失败.

## [2026-03-21 17:08:00 UTC] OpenSpec fast-forward 调研补充: 选择与展示层

### 新证据
- `select_preset_run_specs(...)` 会把用户传入的 `preset_indices` 规范化为 canonical index 顺序, 并校验是否重复、是否超出可选范围.
- dry-run 输出会打印:
  - `selected_preset_indices`
  - `planned trajectories:`
  - 每个 preset 的 `[index] name`
- 这意味着新增 preset 不仅要能生成, 还必须:
  - 进入 canonical preset 列表
  - 被 subset 选择逻辑接受
  - 在 dry-run / stdout 里正确展示名称与索引

### 设计含义
- specs 里应该明确“现有索引不变, 新增索引追加”.
- specs 里应该明确“subset 选择接受新索引并按 canonical 顺序输出”.
- tasks 里需要覆盖:
  - lib 单测中的 preset 名单与比例关系
  - smoke test 中的 dry-run / subset 输出
  - README 从 six 改到 eight
