# 工作日志

## [2026-03-14 16:51:00 UTC] 任务名称: 生成仓库贡献指南 AGENTS.md

### 任务内容
- 新增根目录 `AGENTS.md`, 为贡献者整理仓库结构、开发命令、代码风格、测试和 PR 约定.
- 补建 `task_plan.md`、`notes.md`、`WORKLOG.md`、`LATER_PLANS.md`、`ERRORFIX.md`、`EPIPHANY_LOG.md` 作为本轮任务的文件上下文.

### 完成过程
- 阅读 `README.md`、`.gitmodules`、`requirements.txt`、`api_server.py`、`blender_addon/`、`inference/`、`versecrafter/` 等内容, 提炼仓库真实结构和常用命令.
- 检查根仓库是否存在测试与格式化配置, 并结合 `git log --oneline` 总结当前提交风格.
- 生成 `AGENTS.md` 后用 `wc -w AGENTS.md` 校验字数, 确认文档满足 200 到 400 词要求.

### 总结感悟
- 对于缺少统一测试配置的研究型仓库, 贡献指南要明确“当前事实”与“推荐做法”的边界, 不能把建议写成已存在流程.
- 子模块、Blender 插件和推理脚本三条工作流都是真实贡献入口, 文档必须同时覆盖, 否则很容易误导后续维护者.

## [2026-03-14 17:18:00 UTC] 任务名称: README 环境初始化迁移到 pixi

### 任务内容
- 将 `README.md` 的 Conda 环境初始化章节改为 `pixi` 工作流.
- 新增 `pixi.toml`, 让项目有真实的 pixi 环境清单与初始化任务入口.
- 更新 `.gitignore`, 避免 `.pixi/` 与 `pytorch3d/` 污染仓库状态.

### 完成过程
- 先读取旧安装流程, 再用 Context7 查询 `pixi.toml`、`pypi-dependencies`、Git / path 依赖与 `pixi run` 的官方能力边界.
- 根据仓库实际依赖结构, 将普通依赖放入 `pixi.toml`, 将 `MoGe`、`Grounded-SAM-2`、`grounding_dino`、`flash-attn`、`pytorch3d` 收敛到 `bootstrap` 任务.
- 为避免与 `Grounded-SAM-2` 版本约束冲突, 将 PyTorch 相关版本对齐到 `2.3.1 / 0.18.1 / 2.3.1`.
- 使用 `pixi task list`、`pixi workspace platform list`、`pixi workspace channel list` 验证 manifest 可读取.

### 总结感悟
- 环境迁移不能只改文档文案; 如果缺少真实 manifest, README 很快会再次失真.
- 对带本地 editable 包和 CUDA 扩展的研究仓库, `pixi` 最稳的姿势通常是“基础依赖声明式管理 + 特殊构建步骤任务化”.

## [2026-03-14 17:27:00 UTC] 任务名称: Wan2.1 下载源改为 ModelScope

### 任务内容
- 将 `README.md` 中 `Wan2.1-T2V-14B` 的下载命令从 Hugging Face 改为 ModelScope.
- 在 `pixi.toml` 中补入 `modelscope` 依赖, 让 README 命令在 pixi 环境内可直接使用.

### 完成过程
- 先核对 README 当前下载命令.
- 再查官方 CLI 语法, 确认 `modelscope download --model ... --local_dir ...` 为正确格式.
- 最后同步更新文档和环境依赖, 并用 `rg` 与 `sed` 校验片段结果.

### 总结感悟
- 文档里的下载命令一旦切换工具链, 环境清单也必须同步补齐对应 CLI, 否则贡献者会在第一步就卡住.

## [2026-03-15 04:02:00 UTC] 任务名称: 修复 pixi install-pytorch3d 任务解析错误

### 任务内容
- 修复根目录 `pixi.toml` 中 `install-pytorch3d` 任务因 Bash `if` 语法导致的 Pixi 解析失败.
- 为这类任务语法边界补齐最小复现实验和验证记录.

### 完成过程
- 先读取历史 `pixi` 迁移记录, 确认当前任务的来源和原始意图.
- 用 Context7 和检索资料确认 Pixi 任务默认由 `deno_task_shell` 执行, 不应直接按 Bash 脚本心智来写.
- 在当前仓库执行 `pixi run --manifest-path pixi.toml install-pytorch3d`, 复现用户同款 `Unsupported reserved word` 报错.
- 做最小实验验证两件事:
  - `test -d foo || echo missing` 这种 `test + ||` 形式可行.
  - 多行任务需要显式用 `&&` 承接, 普通换行不会自动串联命令.
- 将正式任务改为:
  - `git clone ... pytorch3d || test -d pytorch3d`
  - 下一行单独写 `&& python -m pip install --no-build-isolation ./pytorch3d`
- 最后用 `pixi run --dry-run` 与 `pixi task list` 验证修复后的任务定义可被正常读取.

### 总结感悟
- Pixi 任务看起来像 shell, 但不是 Bash; 复杂条件逻辑最好先做最小复现, 再决定是否要换成脚本文件或改写成 and/or list.
- 对“目录已存在时视为成功”这类需求, `cmd1 || test -d path` 比直接 `|| true` 更稳, 因为它不会吞掉真实失败.

## [2026-03-15 07:43:05 UTC] 任务名称: 核对仅相机运动时 Blender 产物是否必需

### 任务内容
- 核对 VerseCrafter 在“只控制相机运动”场景下, Blender 是否必须生成图片/视频.
- 区分 `demo_data/LXKcD2zSPMc_0351466_0353266_0001469_0001550` 中哪些文件是必需输入, 哪些只是演示或最终输出.

### 完成过程
- 阅读 `README.md` Step 4-6 和 `README_BLENDER.md`, 确认官方工作流把 Blender 定位为轨迹编辑与导出工具.
- 检查 `inference/rendering_4D_control_maps.py` 与 `inference/versecrafter_inference.py`, 确认渲染阶段依赖 `custom_camera_trajectory.npz` 和 `custom_3D_gaussian_trajectory.json`, 生成阶段依赖 `rendering_4D_maps/*.mp4`.
- 检查 demo 目录中的视频元数据, 确认 `generated_video_0.mp4` 与最终推理参数一致, `record.mov` 更像 Blender 视口预览/演示文件.
- 抽样检查 `custom_3D_gaussian_trajectory.json`, 发现该 demo 的对象中心在多帧间变化, 说明这是“相机 + 对象运动”的示例, 不是纯相机运动样例.

### 总结感悟
- 这个项目里 Blender 的核心价值不是产出预览视频, 而是交互式产出轨迹文件.
- 对“只做相机运动”的最简理解应该是: 可以不要 Blender 预览视频, 但当前官方管线仍需要相机轨迹文件, 且通常还要有配套的高斯轨迹 JSON 才能进入 Step 5.

## [2026-03-15 08:44:30 UTC] 任务名称: 初始化 VerseCrafter OpenSpec 并创建多轨迹脚本 change

### 任务内容
- 在 VerseCrafter 仓库初始化 OpenSpec 工作区.
- 为 VerseCrafter 单图 6 轨迹相机批处理脚本创建正式 change 入口.

### 完成过程
- 执行 `openspec init --tools codex`, 在仓库中创建 OpenSpec 结构并为 Codex 接入相关 skill/command.
- 基于探索阶段形成的命名, 准备创建 `add-versecrafter-single-image-multi-trajectory-script` change.

### 总结感悟
- 先把探索结论沉淀到 OpenSpec, 能避免直接进实现时丢失需求边界和设计取舍.

## [2026-03-15 09:18:57 UTC] 任务名称: 推送当前 main 到远端 my

### 任务内容
- 核对当前仓库分支、远端配置、工作区状态.
- 将当前 `main` 分支推送到远端 `my`.
- 用本地与远端提交哈希做最终校验, 确认推送结果.

### 完成过程
- 先检查 `git branch --show-current`、`git remote -v`、`git status --short --branch`.
- 确认当前位于 `main`, 工作区在推送前无未提交改动, 且远端 `my` 已配置.
- 执行 `git push my main`, 收到 `Everything up-to-date`.
- 继续用 `git rev-parse HEAD` 与 `git ls-remote my refs/heads/main` 交叉验证, 确认两端都指向 `2cee0c6c74b0783ae2f322c3d006550a7f9eb8ee`.

### 总结感悟
- 对 Git 推送结果, 不能只看一句成功文案, 还要把本地 `HEAD` 和远端分支哈希对齐核实清楚.
- 这次说明 `my/main` 之前就已经同步到了当前提交, 因此推送是幂等成功, 没有新增传输内容.

## [2026-03-15 09:38:40 UTC] 任务名称: 补齐 VerseCrafter 单图多轨迹脚本的 OpenSpec artifacts

### 任务内容
- 基于已创建的 change `add-versecrafter-single-image-multi-trajectory-script`, 补齐实现前所需的 `design`、`specs`、`tasks` 三个 OpenSpec artifact.
- 将用户要求的 6 条固定轨迹、数字目录约定、确定性 movement distance、默认深度参数、manifest 和 0-object fail-fast 规则正式写入变更文档.

### 完成过程
- 重新读取 `openspec status` 与 `openspec instructions design/specs/tasks --json`, 确认 artifact 依赖顺序和模板要求.
- 复核 VerseCrafter 现有 Step 1-6 代码契约, 包括:
  - `custom_camera_trajectory.npz` 的 Blender c2w 语义
  - `custom_3D_gaussian_trajectory.json` 的多帧格式要求
  - `versecrafter_inference.py` 的控制图输入与视频输出命名
- 回读 `/workspace/lyra/docs/multi_trajectory_camera_implementation.md` 以及相关源码, 把 Lyra 的 6 条 preset、默认轨迹参数语义, 转译为 VerseCrafter 可落地的设计.
- 最终写出:
  - `design.md`
  - `specs/single-image-multi-trajectory-generation/spec.md`
  - `tasks.md`
- 最后执行 `openspec status` 校验, 确认 4/4 artifacts complete.

### 总结感悟
- 对这类“参考另一个项目做同款能力”的需求, 最关键的不是机械照抄参数表, 而是先拆清楚“用户想保留的行为语义”和“当前仓库真实的数据契约”.
- VerseCrafter 这次最核心的兼容点不是 prompt 或模型参数, 而是 Step 4 到 Step 5 之间那两个轨迹文件的格式与坐标语义.

## [2026-03-15 10:18:10 UTC] 任务名称: 实现 VerseCrafter 单图 6 轨迹批处理脚本

### 任务内容
- 根据 OpenSpec change `add-versecrafter-single-image-multi-trajectory-script` 实现 VerseCrafter 版单图多轨迹自动脚本.
- 自动复用 Step 1-3 共享预处理, 替代 Blender 手工 Step 4, 并串联 Step 5/6 完成 6 条固定轨迹的视频生成.

### 完成过程
- 先读取 apply 指令、proposal、design、spec、tasks, 明确本轮要交付的 13 个实现子任务.
- 在 `inference/` 下新增两层结构:
  - `single_image_multi_trajectory_lib.py`: 纯函数层, 封装轨迹数学、坐标变换、Gaussian trajectory 广播和输出完整性检查.
  - `single_image_multi_trajectory.py`: orchestrator 层, 负责编排现有 step 脚本、写 `manifest.json`、管理 resume 和 per-preset 状态.
- 对齐 Lyra 的 preset 语义, 但实际使用 VerseCrafter / Blender 坐标变换生成 `custom_camera_trajectory.npz`.
- 把 `gaussian_params.json` 自动广播为 Step 5 可读的多帧 `custom_3D_gaussian_trajectory.json`.
- 为了让 orchestrator 能完整透传用户给的命令心智模型, 额外给 `versecrafter_inference.py` 补上了 `--negative_prompt`.
- 新增 7 条测试:
  - 纯函数单测 6 条
  - resume smoke test 1 条
- 更新 `README.md`, 新增不依赖手工 Blender 编辑的 6 轨迹批处理命令示例和输出结构说明.
- 最后把 OpenSpec `tasks.md` 全部勾选为完成, 并用 `openspec status` 校验状态.

### 总结感悟
- 这次实现里最关键的不是“怎么起子进程”, 而是“哪一层坐标语义才是真正的契约”. 只要 OpenCV / Blender 的向量与协方差变换没有统一, 后面的轨迹和高斯都会错.
- 对研究型推理仓库来说, 增加 orchestrator 最稳的方式确实是“先围绕稳定文件契约做编排”, 等 workflow 成熟后再考虑把 CLI-first 脚本抽成 library-first.

## [2026-03-15 11:12:00 UTC] 任务名称: 跑通 VerseCrafter 单图多轨迹真实测试并修复 Step 5/6 阻塞

### 任务内容
- 对 `demo_data/my/0001.png` 执行 VerseCrafter 单图多轨迹真实测试.
- 修复 Step 5 的视频写出兼容问题.
- 修复 Step 6 的可选音频依赖导入阻塞.
- 为单卡 A800 80GB 找到真实可运行的显存模式, 并同步回批处理默认参数.

### 完成过程
- 先用最小 smoke 验证 `rendering_4D_control_maps.py` 中新的 `cv2.VideoWriter` 写出逻辑, 确认 mp4 可写可读.
- 再做真实链路测试, 观察到 Step 5 已通过, 新阻塞转移到 Step 6 的 `librosa` 缺失.
- 将 `third_party/VideoX-Fun/videox_fun/models/__init__.py` 中两个音频编码器导入改为可选依赖导入, 避免无音频推理路径被 `librosa` 硬阻塞.
- 为该导入边界新增回归测试, 并把 `pytest` 补入 `pixi.toml`, 让 pixi 默认环境能直接执行仓库测试.
- 在真实 GPU 上分别验证了三种显存模式:
  - `model_full_load`: OOM
  - `model_cpu_offload`: 仍 OOM
  - `model_cpu_offload_and_qfloat8`: 成功
- 把 `gpu_memory_mode` 做成 `versecrafter_inference.py` 的正式 CLI 参数, 再由 `single_image_multi_trajectory.py` 透传.
- 将批处理默认值切到 `model_cpu_offload_and_qfloat8`, 并同步更新 README 示例与 dry-run / smoke 测试.
- 真实批处理已连续成功产出:
  - `demo_data/my/0/generated_videos/generated_video_0.mp4`
  - `demo_data/my/1/generated_videos/generated_video_0.mp4`
  - `demo_data/my/2/generated_videos/generated_video_0.mp4`
- 当前长跑任务仍在继续后续轨迹生成.

### 总结感悟
- 这次最关键的不是单一 bug 修补, 而是把三个不同层次的问题拆开:
  - Step 5 编码兼容
  - Step 6 可选依赖导入边界
  - 单卡显存策略默认值
- 对研究型仓库, “能导入” 和 “能在真实 GPU 上完整采样” 是两种完全不同的验证, 两者都必须拿到动态证据.

## [2026-03-15 11:24:00 UTC] 任务名称: 为单图多轨迹脚本新增 camera-only 纯相机模式

### 任务内容
- 回应用户“不要前景运动, 只要相机运动”的要求.
- 证明当前结果不是直接拷贝 demo 动态前景轨迹.
- 在批处理脚本中新增纯相机模式.

### 完成过程
- 对 `demo_data/my/0001.png` 和 demo 输入图做哈希比较, 确认两者是同一张图.
- 对 `custom_3D_gaussian_trajectory.json` 做逐帧检查, 确认 my 目录是静态轨迹, demo 才是动态轨迹.
- 在 `single_image_multi_trajectory.py` 中新增 `--camera_only`:
  - 跳过 segmentation
  - 跳过 Gaussian fitting
  - 生成空 mask 目录
  - 生成 `num_objects=0` 的共享 Gaussian JSON
- 在 `single_image_multi_trajectory_lib.py` 中新增空 Gaussian payload helper.
- 补充 2 条测试并更新 README.
- 最终验证:
  - `py_compile` 通过
  - `pytest` 11 条测试通过
  - actual dry-run 明确显示 `camera_only: True` 与 `camera_only_empty`

### 总结感悟
- “输出看起来像 demo” 不一定是偷拷结果, 也可能只是输入图本来就是同一张.
- 对这种“我只要相机动, 不要前景动”的需求, 正确解法不是继续调前景轨迹, 而是从工作流层面彻底切到背景刚体模式.

## [2026-03-15 12:46:40 UTC] 任务名称: 0 号轨迹“时间静止”40 步样本重跑与对照验证

### 任务内容
- 基于现有 `camera_only` 控制图, 只重跑 `demo_data/my/0` 的 Step 6.
- 将 prompt / negative prompt 改成更强的“时间静止, 所有人物与车辆完全不动”版本.
- 按用户要求把 `--num_inference_steps` 提升到 `40`.
- 为旧版和新版额外生成对照资产, 方便后续判断效果.

### 完成过程
- 先确认没有残留生成进程, 再确认 `demo_data/my/0/rendering_4D_maps` 已完整可复用.
- 选择不覆盖旧结果, 将新样本输出到:
  - `demo_data/my/0/generated_videos_timefreeze_test_40steps`
- 实际执行 `pixi run python inference/versecrafter_inference.py ... --num_inference_steps 40 --gpu_memory_mode model_cpu_offload_and_qfloat8`.
- 持续跟踪 40 步采样进度, 确认:
  - 成功进入采样
  - 未出现新的导入错误
  - 未 OOM
  - 最终成功落盘 `generated_video_0.mp4`
- 用 `ffprobe` 校验视频基础元数据.
- 额外生成:
  - 旧版 / 新版接触图
  - 局部裁剪接触图
  - `timefreeze_compare_old_vs_new.mp4` 并排对照视频

### 总结感悟
- “先用 1 条轨迹做最小可证伪实验”在这里非常值, 因为 40 步单条实测已经接近 43 分钟.
- 对这种“人物到底还动不动”的问题, 只给一个新视频路径不够, 还要把旧新版对照资产一起准备好, 这样判断会快很多.

## [2026-03-15 13:52:30 UTC] 任务名称: 新场景 `demo_data/my2/10000.png` 的时间静止单轨迹验证

### 任务内容
- 为 `single_image_multi_trajectory.py` 增加只跑指定轨迹的能力.
- 使用更强的“时间静止”提示词, 在新场景 `demo_data/my2/10000.png` 上只跑 `0` 号轨迹.
- 保持 `camera_only` 和 `40` 步采样, 真实验证新场景输出.

### 完成过程
- 先给批处理脚本新增 `--preset_indices`, 让默认行为仍然是全 6 条, 但显式指定时可以只跑子集.
- 同步补了:
  - 纯函数单测
  - dry-run smoke test
  - README 中关于 `--preset_indices` 的说明
- 新场景真实运行时, 先遇到 Step 1 默认下载 `Ruicheng/moge-2-vitl-normal` 过慢的问题.
- 进一步检查 Hugging Face Xet 日志后确认:
  - 远程下载不是彻底挂死
  - 只是慢到不适合作为当前验证路径
- 改为使用本地已缓存的:
  - `/root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`
- 之后顺利完成:
  - Step 1 深度估计
  - Step 5 camera-only 控制图渲染
  - Step 6 40 步最终生成
- 最终产出:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`
  - `demo_data/my2_timefreeze_10000/0/generated_videos/frames_contact_sheet.jpg`

### 总结感悟
- 给高成本批处理补一个 subset 入口, 往往比继续调 prompt 更先提升工作效率.
- 对依赖 Hugging Face 大模型文件的推理脚本, “本地缓存快照路径怎么写”本身就是一条很值钱的工程经验.

## [2026-03-15 14:20:00 UTC] 任务名称: 核对 `moge-2-vitl-normal` 与 `moge-2-vitl` 在 VerseCrafter 中的实际差异

### 任务内容
- 回答仓库是否真的用到了 `normal`.
- 核对 `moge-2-vitl-normal` 与 `moge-2-vitl` 在当前项目里的适用边界.
- 给出“临时替代是否妥当”的证据化结论.

### 完成过程
- 先检查 `inference/moge-v2_infer.py` 与 `api_server.py`, 确认仓库默认 v2 模型确实写成 `Ruicheng/moge-2-vitl-normal`.
- 再沿 `single_image_multi_trajectory.py` -> `fit_3D_gaussian.py` -> `rendering_4D_control_maps.py` 追下游消费链, 确认主链路只读取 `depth_intrinsics.npz` 内的 `depth` 与 `intrinsic`.
- 复核 `moge-v2_infer.py` 的 `--maps` 分支, 确认 `normal.png` 保存逻辑当前被注释, 主路径不会实际落盘 normal.
- 对照官方 MoGe README, 确认:
  - `moge-2-vitl` 是 metric-scale 版本
  - `moge-2-vitl-normal` 是额外支持 normal estimation 的版本
  - 两者性能几乎相同
- 再核对本地 manifest 与产物, 证明 `moge-2-vitl` 已真实跑通当前多轨迹工作流.

### 总结感悟
- 这次最重要的不是“模型名像不像”, 而是先分清楚“默认值写了什么”与“下游真的消费了什么”.
- 对当前 VerseCrafter 主链路, `moge-2-vitl` 作为临时替代是成立的.
- 但如果以后要恢复 normal 导出或强化 GLB / PLY 法线质量, 默认值策略仍然值得再设计一次.

## [2026-03-15 14:50:00 UTC] 任务名称: 补跑新场景 0 号轨迹的 10 步对比样本

### 任务内容
- 在不覆盖现有 40 步结果的前提下, 为 `demo_data/my2/10000.png` 的 0 号轨迹补跑 10 步时间静止版本.
- 生成便于肉眼比较的 contact sheet 和 10/40 步并排对比视频.

### 完成过程
- 先确认:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare` 不存在
  - `demo_data/my2_timefreeze_10000/0/rendering_4D_maps` 已完整存在
- 决定直接复用 Step 5 控制图, 只重跑 Step 6, 保持 frozen-in-time prompt 不变, 仅把 `--num_inference_steps` 改为 `10`.
- 实际执行:
  - `pixi run python inference/versecrafter_inference.py ... --save_path demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare --num_inference_steps 10 --gpu_memory_mode model_cpu_offload_and_qfloat8`
- 持续跟踪采样进度, 确认在 `14:00` 左右完成 `10/10`.
- 用 `ffprobe` 校验 10 步视频和 40 步视频元数据一致.
- 再用 `pixi run python` + `cv2` 生成:
  - `frames_contact_sheet.jpg`
  - `generated_video_0_vs_steps40_side_by_side.mp4`

### 总结感悟
- 对这种“只想比较步数”的需求, 最省时间的做法就是复用同一份控制图, 避免重复支付 Step 1-5 的成本.
- 10 步版已经能保住时间静止的主观效果, 但 40 步版在细节干净度上还是更稳, 所以两者适合不同阶段:
  - 10 步用于快速试错
  - 40 步用于正式导出

## [2026-03-15 15:01:00 UTC] 任务名称: 将当前只相机控制命令整理到 `cmd.md`

### 任务内容
- 新建根目录 `cmd.md`, 记录当前只相机控制工作流的关键命令.
- 同时覆盖整链路命令和 Step 6 单独复跑命令.

### 完成过程
- 先核对 `README.md`、`single_image_multi_trajectory.py`、`versecrafter_inference.py` 当前参数入口, 避免文档里的命令和现有代码脱节.
- 再把本轮真实使用过的参数口径整理成 4 组命令:
  - 6 轨迹 `camera_only` 整链路命令
  - 仅 `0` 号轨迹整链路命令
  - 40 步 Step 6 复跑命令
  - 10 步 Step 6 对比命令
- 额外在文档尾部补了当前输出目录对照, 方便直接定位结果文件.

### 总结感悟
- 对高成本推理链路来说, “命令本身”就是资产, 不能只保留在聊天记录和临时日志里.
- 这次把整链路命令和 Step 6 局部命令同时记下来后, 后续再做轨迹扩展、步数对比和 prompt 对比都会更顺手.

## [2026-03-15 15:53:00 UTC] 任务名称: 跑通 `my3` 新海诚风格展厅场景的 0 号镜头 20 step 快速版

### 任务内容
- 使用 `demo_data/my3/generated-image (1).png` 作为新输入图.
- 维持当前只相机控制工作流, 只跑 `0` 号轨迹.
- 使用新海诚风格展厅 prompt, 生成 `20 step` 快速版视频.

### 完成过程
- 先确认 `demo_data/my3` 目录只有一张输入图, 并确认输出根目录 `demo_data/my3_shinkai_quick20` 不存在, 避免覆盖旧结果.
- 通过看输入图, 将 prompt 对齐到真实画面内容:
  - 蓝白科技展厅
  - 玻璃天窗
  - 高反射地面
  - 概念车展示位
  - 远处科技展项
- 执行 `single_image_multi_trajectory.py` 整链路命令, 保持:
  - `--camera_only`
  - `--preset_indices 0`
  - `--num_inference_steps 20`
  - `--moge_pretrained <local model.pt>`
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`
- 动态运行中确认:
  - Step 1 深度估计成功
  - Step 5 显式进入无前景对象分支
  - Step 6 从 `0/20` 跑到 `20/20`
- 最终补做:
  - `ffprobe` 元数据校验
  - `frames_contact_sheet.jpg` 接触图生成

### 总结感悟
- 对新场景的快速验证, 先看输入图再写 prompt 很值, 因为这样能明显减少“风格词对了, 场景词却偏了”的浪费.
- `camera_only + preset 0 + 20 step` 很适合作为新场景试片入口:
  - 成本比 40 step 低
  - 但已经足以判断镜头趋势和整体风格是否成立
