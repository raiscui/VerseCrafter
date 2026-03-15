# 任务计划: 生成仓库贡献指南 AGENTS.md

## [2026-03-14 16:45:00 UTC] 任务启动

### 目标
- 为当前仓库生成一份 `AGENTS.md`, 标题为 "Repository Guidelines", 内容覆盖项目结构、开发命令、代码风格、测试、提交与 PR 要求, 且信息基于仓库现状.

### 阶段
- [x] 阶段1: 计划和设置
- [ ] 阶段2: 研究仓库结构与工作流
- [ ] 阶段3: 编写并落地 `AGENTS.md`
- [ ] 阶段4: 校验内容并交付

### 关键问题
1. 这个仓库的主要运行入口是否以 Python 推理脚本和 Blender 插件为主.
2. 仓库内是否已有自动化测试或统一构建工具, 还是主要依赖手动推理验证.

### 做出的决定
- 决定: 先读取 `README.md`、根目录结构和 Git 历史, 再写文档.
  - 理由: 贡献指南必须贴合项目实际, 不能套通用模板.

### 遇到的错误
- 暂无.

### 状态
**目前在阶段2**
- 正在读取仓库现有文档、目录和提交历史, 提炼项目专属贡献约定.

## [2026-03-14 16:49:00 UTC] 研究完成, 开始编写

### 阶段
- [x] 阶段1: 计划和设置
- [x] 阶段2: 研究仓库结构与工作流
- [ ] 阶段3: 编写并落地 `AGENTS.md`
- [ ] 阶段4: 校验内容并交付

### 做出的决定
- 决定: `AGENTS.md` 采用短段落 + 精准命令示例的写法.
  - 理由: 用户要求 concise, 且贡献者最需要的是可执行指引而不是长篇背景介绍.
- 决定: 测试章节明确说明当前缺少根级自动化测试框架.
  - 理由: 这是已验证事实, 不应虚构不存在的 `pytest` 流程.

### 状态
**目前在阶段3**
- 已完成仓库结构、命令、提交历史和代码风格调研, 正在编写根目录 `AGENTS.md`.

## [2026-03-14 16:51:00 UTC] 编写与校验完成

### 阶段
- [x] 阶段1: 计划和设置
- [x] 阶段2: 研究仓库结构与工作流
- [x] 阶段3: 编写并落地 `AGENTS.md`
- [x] 阶段4: 校验内容并交付

### 做出的决定
- 决定: 保持文档为英文, 直接面向仓库贡献者.
  - 理由: 用户明确要求输出一个仓库级 contributor guide, 且标题与示例章节均为英文.

### 验证
- 已执行 `wc -w AGENTS.md`, 结果为 `351 AGENTS.md`.
- 已人工检查标题为 `Repository Guidelines`, 并包含项目结构、开发命令、代码风格、测试、提交与 PR 要求.

### 状态
**目前在阶段4**
- 所有计划项已完成, 准备向用户交付结果.

## [2026-03-14 17:03:00 UTC] 新任务启动: README 改用 pixi 管理环境

### 目标
- 将 `README.md` 中 "Create and activate the Conda environment" 一节改为基于 `pixi` 的环境初始化流程.
- 若 README 需要引用新的清单文件, 则补齐该文件, 保证文档与仓库状态一致.

### 阶段
- [x] 阶段1: 读取上下文与现有安装说明
- [ ] 阶段2: 调研 pixi 官方配置方式与仓库依赖形态
- [ ] 阶段3: 落地 `pixi.toml` 与 README 改写
- [ ] 阶段4: 校验 manifest 和文档内容

### 关键问题
1. 哪些依赖可以直接写进 `pixi.toml`, 哪些依赖需要通过 `pixi` 任务包装 `pip install` 完成.
2. 仓库是否需要保留 `requirements.txt`, 还是只把 README 入口切换到 `pixi`.

### 做出的决定
- 决定: 先查 `pixi` 官方文档, 再决定 manifest 结构.
  - 理由: 这属于环境配置设计, 必须按官方能力边界来写.

### 遇到的错误
- 查询 `third_party/Grounded-SAM-2/requirements.txt` 失败.
  - 决议: 改为阅读其 `setup.py`、`pyproject.toml` 与 `grounding_dino/requirements.txt` 来推断安装入口.

### 状态
**目前在阶段2**
- 正在核对 `pixi` 的 `pypi-dependencies`、本地 editable 包、git 依赖和任务配置方式.

## [2026-03-14 17:18:00 UTC] pixi 迁移完成并校验

### 阶段
- [x] 阶段1: 读取上下文与现有安装说明
- [x] 阶段2: 调研 pixi 官方配置方式与仓库依赖形态
- [x] 阶段3: 落地 `pixi.toml` 与 README 改写
- [x] 阶段4: 校验 manifest 和文档内容

### 做出的决定
- 决定: 将 `MoGe`、`Grounded-SAM-2`、`grounding_dino`、`flash-attn`、`pytorch3d` 全部放入 `pixi` 任务 `bootstrap`.
  - 理由: 这些依赖要么来自 Git / 本地 editable 包, 要么需要 `--no-build-isolation`, 用任务复刻原始安装语义更稳.
- 决定: 将 PyTorch 版本提升到 `2.3.1 / 0.18.1 / 2.3.1`.
  - 理由: 与 `Grounded-SAM-2` / `SAM2` 的静态版本约束保持一致.

### 验证
- 已执行 `pixi task list --manifest-path pixi.toml`, 成功识别 `bootstrap` 等任务.
- 已执行 `pixi workspace platform list --manifest-path pixi.toml`, 成功读取 `linux-64`.
- 已执行 `pixi workspace channel list --manifest-path pixi.toml`, 成功读取 `pytorch`、`nvidia`、`conda-forge`.
- 已执行 `pixi lock --manifest-path pixi.toml --dry-run`, 返回:
  - `installation of conda environment is required to solve PyPI source dependencies but --no-install flag has been set`
  - 结论: manifest 已被 pixi 读取, 但对包含 PyPI 依赖的项目, `--dry-run` 不是完整验证路径; 本轮未执行完整 `pixi install`, 以避免在当前回合拉起超大 CUDA 环境.

### 状态
**目前在阶段4**
- 本轮任务已完成, 准备向用户交付.

## [2026-03-15 03:51:00 UTC] 新任务启动: 修复 pixi 的 install-pytorch3d 任务解析错误

### 目标
- 解释并修复 `pixi run install-pytorch3d` 因 shell 语法不兼容导致的报错.
- 保持原始语义: 仅在本地不存在 `pytorch3d/` 目录时克隆源码, 然后以 `--no-build-isolation` 方式安装.

### 阶段
- [x] 阶段1: 读取上下文与历史 pixi 记录
- [x] 阶段2: 调研 Pixi 任务语法边界并定位现象
- [ ] 阶段3: 修改 `pixi.toml` 中的任务定义
- [ ] 阶段4: 验证修复后的任务语法与行为

### 关键问题
1. 当前报错究竟来自 `pixi.toml` TOML 语法, 还是 Pixi 任务执行时的 `deno_task_shell` 语法限制.
2. 在不依赖 Bash `if ... then ... fi` 的前提下, 如何保留“目录不存在才 clone”的语义, 同时不掩盖真实 clone 失败.

### 做出的决定
- 决定: 先收集官方文档证据与最小复现, 再改任务定义.
  - 理由: 这是配置执行错误, 先区分 `manifest` 可读与任务运行失败, 才不会误修.
- 决定: 优先改成 Pixi 默认 shell 能稳定解析的命令形式, 不假设用户当前 Pixi 版本已经支持自定义解释器.
  - 理由: 当前仓库没有显式约束 Pixi 新特性版本, 保守写法兼容性更好.

### 遇到的错误
- 现象: 用户执行 `pixi run install-pytorch3d` 时收到 `failed to parse shell script` 与 `Unsupported reserved word` 错误, 指向 `if [ ! -d pytorch3d ]; then`.
  - 决议: 继续做最小复现和语法替换验证.

### 状态
**目前在阶段2**
- 已确认 `pixi.toml` 中的 `install-pytorch3d` 使用了 Bash 风格 `if` 块, 正在验证 Pixi 默认任务 shell 的真实语法边界.

## [2026-03-15 04:01:00 UTC] pixi install-pytorch3d 修复与验证完成

### 阶段
- [x] 阶段1: 读取上下文与历史 pixi 记录
- [x] 阶段2: 调研 Pixi 任务语法边界并定位现象
- [x] 阶段3: 修改 `pixi.toml` 中的任务定义
- [x] 阶段4: 验证修复后的任务语法与行为

### 做出的决定
- 决定: 不使用 `interpreter = "bash"` 方案, 而是保留 Pixi 默认 shell, 将任务改写为 `git clone ... || test -d ...` 再接 `&& python -m pip install ...`.
  - 理由: 当前仓库更需要兼容 Pixi 现有稳定能力, 而不是依赖可能存在版本差异的新字段.

### 验证
- 已执行 `pixi run --manifest-path pixi.toml install-pytorch3d`, 在修改前稳定复现用户同款报错:
  - `failed to parse shell script`
  - `Unsupported reserved word`
  - 指向 `if [ ! -d pytorch3d ]; then`
- 已执行两个最小实验:
  - `test -d foo || echo missing` 可正常执行, 证明 `test` 与 `||` 路径成立.
  - `mkdir foo || test -d foo` 换成多行并在下一行单独写 `&& pwd` 可正常执行, 证明 Pixi 可接受这种 and/or list 写法.
- 已执行 `pixi run --manifest-path pixi.toml --dry-run install-pytorch3d`, 成功输出任务命令且无解析错误.
- 已执行 `pixi task list --manifest-path pixi.toml`, 任务列表可正常读取.

### 状态
**目前在阶段4**
- 本轮修复已完成, 准备同步给用户现象、原因、修复和后续建议.

## [2026-03-15 14:05:00 UTC] 新任务启动: 核对 `moge-2-vitl-normal` 是否真的被项目使用

### 目标
- 回答当前仓库为什么提到 `moge-2-vitl-normal`.
- 核对代码是否真的使用 normal 输出, 还是只用了 depth / points.
- 判断在本项目里用 `moge-2-vitl` 替代 `moge-2-vitl-normal` 是否妥当.

### 阶段
- [x] 阶段1: 读取上下文文件与历史记录
- [ ] 阶段2: 检查仓库内 MoGe 相关配置、脚本和调用链
- [ ] 阶段3: 核对上游 MoGe 模型差异与输出语义
- [ ] 阶段4: 形成结论并回复用户

### 关键问题
1. 当前 `inference/moge-v2_infer.py` 默认到底写的是哪个模型 ID.
2. 该脚本输出的 normal 是否被后续步骤读取, 还是仅保存不消费.
3. 如果仓库只依赖 depth / point cloud, 那么替换为不带 normal 的权重会不会引入行为退化或兼容风险.

### 做出的决定
- 决定: 先沿着本仓库真实调用链找动态输入输出契约, 再回看上游 MoGe 文档.
  - 理由: 先回答“项目是否用到了”, 再讨论“模型差异是否重要”, 结论才不会倒置.

### 状态
**目前在阶段2**
- 正在检查 `moge-v2_infer.py`、调用它的编排脚本, 以及后续步骤有没有读取 normal 相关文件.

## [2026-03-15 14:20:00 UTC] MoGe 模型使用范围核对完成

### 阶段
- [x] 阶段1: 读取上下文文件与历史记录
- [x] 阶段2: 检查仓库内 MoGe 相关配置、脚本和调用链
- [x] 阶段3: 核对上游 MoGe 模型差异与输出语义
- [x] 阶段4: 形成结论并回复用户

### 已验证事实
- 仓库默认 v2 MoGe 确实写成了 `Ruicheng/moge-2-vitl-normal`.
- 当前主工作流和 API 预处理真正传给下游的只有 `depth_intrinsics.npz`, 内含 `depth` 和 `intrinsic`.
- `normal` 在当前仓库里只停留在 `moge-v2_infer.py` 的可选读取与 mesh / ply 导出分支, `--maps` 主路径没有实际保存 `normal.png`.
- 官方 README 明确说明:
  - `moge-2-vitl` 是 metric-scale MoGe-2
  - `moge-2-vitl-normal` 是额外支持 normal estimation 的变体
  - 两者性能几乎相同
- 本仓库已有真实运行 manifest 证明 `moge-2-vitl` 已成功跑通当前多轨迹主链路.

### 做出的决定
- 决定: 回答用户时区分“当前主链路是否用到 normal”和“全仓库默认值是否应该永久替换”.
  - 理由: 前者答案基本是“没有真正消费”; 后者则仍要保留对 GLB / PLY / 未来 normal 下游的兼容判断.

### 状态
**目前在阶段4**
- 本轮分析已完成, 准备按证据向用户说明适用边界和后续建议.

## [2026-03-14 17:27:00 UTC] 新任务完成: Wan2.1 下载源切到 ModelScope

### 阶段
- [x] 阶段1: 核对现有 README 下载入口
- [x] 阶段2: 验证 ModelScope CLI 语法
- [x] 阶段3: 更新 README 与环境依赖
- [x] 阶段4: 片段校验

### 做出的决定
- 决定: 仅将 `Wan2.1-T2V-14B` 的下载入口改到 ModelScope, `VerseCrafter` 权重保持现有 Hugging Face 下载方式.
  - 理由: 用户只指定了基座模型的下载源变更.
- 决定: 在 `pixi.toml` 中新增 `modelscope`.
  - 理由: README 里既然使用 `modelscope download`, 环境里就应提供对应 CLI.

### 验证
- 已确认 [README.md](/workspace/VerseCrafter/README.md) 下载段改为:
  - `modelscope download --model Wan-AI/Wan2.1-T2V-14B --local_dir model/Wan2.1-T2V-14B`
- 已确认 [pixi.toml](/workspace/VerseCrafter/pixi.toml) 包含 `modelscope = "*"` .

### 状态
**目前在阶段4**
- 本轮任务已完成, 准备向用户交付.

## [2026-03-15 07:41:16 UTC] 新任务启动: 判断仅做相机运动时是否仍需要 Blender 产物

### 目标
- 基于仓库 README、推理脚本和 `demo_data/LXKcD2zSPMc_0351466_0353266_0001469_0001550` 的实际文件, 说明“只做相机运动控制”时哪些文件是必须的, 哪些只是演示产物.
- 明确 Blender 在这个工作流里承担的是“轨迹编辑/导出”还是“最终图片/视频生成”.

### 阶段
- [x] 阶段1: 读取历史上下文与示例目录
- [ ] 阶段2: 核对 README 与脚本中的输入输出关系
- [ ] 阶段3: 汇总结论并回答用户

### 关键问题
1. Step 4 的 Blender 是否只是生成 `custom_camera_trajectory.npz` 与 `custom_3D_gaussian_trajectory.json`.
2. `camera_object_0/record.mov`、`generated_video_0.mp4` 这些文件分别属于 Blender 预览产物还是最终模型生成产物.
3. 如果用户只想控制相机而不动对象, `custom_3D_gaussian_trajectory.json` 是否仍然需要保留静态对象信息.

### 做出的决定
- 决定: 先从 README 和脚本里提取“步骤输入输出链”, 再结合 demo 目录判定文件用途.
  - 理由: 这样可以避免把示例目录中的文件名误解成必需输入.

## [2026-03-15 11:48:44 UTC] 新任务启动: 将单图多轨迹生成改成“时间静止”并重跑验证

### 目标
- 保持 `camera_only` 纯相机工作流不变.
- 将最终视频的语义从“背景刚体 + 模型自由补运动”进一步收紧为“时间静止, 所有人物与车辆保持完全不动”.
- 按用户要求把 `--num_inference_steps` 提升到 `40`, 并重新验证生成结果.

### 阶段
- [x] 阶段1: 读取历史上下文与当前脚本入口
- [ ] 阶段2: 明确这次需要改的生成条件与验证路径
- [ ] 阶段3: 执行最小可证伪实验并观察结果
- [ ] 阶段4: 若实验趋势正确, 再决定是否扩展到 6 条轨迹全量重跑

### 关键问题
1. 当前“人物仍在动”的主因, 是不是 `camera_only` 失效.
2. 还是 `camera_only` 已经生效, 但 Step 6 的 prompt / negative prompt 对“绝对静止”约束不够强.
3. 在不重做 Step 1-5 的前提下, 能否直接复用现有 `rendering_4D_maps`, 只重跑 Step 6 做快速验证.

### 做出的决定
- 决定: 先做 `0` 号轨迹的最小实验, 不直接全量跑 6 条.
  - 理由: 当前最需要验证的是“更强冻结语义 + 40 步采样”是否有效, 不是重复付出整批 6 条的时间成本.
- 决定: 优先复用 `demo_data/my/0/rendering_4D_maps`, 仅重跑 Step 6.
  - 理由: 现象发生在最终生成视频阶段, 先隔离变量最稳.

### 状态
**目前在阶段2**
- 已确认当前没有残留生成进程.
- 已确认 `single_image_multi_trajectory.py` 当前默认 `num_inference_steps=30`, 且默认 negative prompt 对“时间静止所有人物完全不动”的约束不足.
- 下一步将把验证计划补充到 `notes.md`, 然后执行 0 号轨迹的 Step 6 重跑实验.

## [2026-03-15 11:55:40 UTC] 0 号轨迹 Step 6 “时间静止”实验已启动

### 阶段
- [x] 阶段1: 读取历史上下文与当前脚本入口
- [x] 阶段2: 明确这次需要改的生成条件与验证路径
- [ ] 阶段3: 执行最小可证伪实验并观察结果
- [ ] 阶段4: 若实验趋势正确, 再决定是否扩展到 6 条轨迹全量重跑

### 做出的决定
- 决定: 先不覆盖 `demo_data/my/0/generated_videos`, 改为写入 `demo_data/my/0/generated_videos_timefreeze_test_40steps`.
  - 理由: 旧结果保留后, 更方便做前后对照, 也避免把实验样本和正式结果混在一起.

### 动态验证
- 已实际启动命令:
  - `pixi run python inference/versecrafter_inference.py ... --save_path demo_data/my/0/generated_videos_timefreeze_test_40steps ... --num_inference_steps 40 ... --gpu_memory_mode model_cpu_offload_and_qfloat8`
- 已观察到:
  - 权重与 pipeline 初始化完成
  - 采样进度已进入 `0/40 -> 1/40`
  - 进程未出现新的导入错误或 OOM

### 状态
**目前在阶段3**
- 当前正在等待 0 号轨迹 40 步“时间静止”样本完成.

## [2026-03-15 12:46:40 UTC] 0 号轨迹“时间静止”样本已完成并完成基础验证

### 阶段
- [x] 阶段1: 读取历史上下文与当前脚本入口
- [x] 阶段2: 明确这次需要改的生成条件与验证路径
- [x] 阶段3: 执行最小可证伪实验并观察结果
- [x] 阶段4: 若实验趋势正确, 再决定是否扩展到 6 条轨迹全量重跑

### 动态验证
- Step 6 命令已完整跑完, 退出码为 `0`.
- 新视频已生成:
  - `demo_data/my/0/generated_videos_timefreeze_test_40steps/generated_video_0.mp4`
- `ffprobe` 验证结果:
  - `1280x720`
  - `16 fps`
  - `81 frames`
  - `duration 5.0625s`
- 已额外生成对照资产:
  - 旧版多帧接触图: `demo_data/my/0/generated_videos/frames_contact_sheet.jpg`
  - 新版多帧接触图: `demo_data/my/0/generated_videos_timefreeze_test_40steps/frames_contact_sheet.jpg`
  - 旧新版并排对照视频: `demo_data/my/0/timefreeze_compare_old_vs_new.mp4`

### 当前判断
- 已确认“更强冻结语义 + 40 steps”这一组条件可以稳定完成生成.
- 但仅凭静态接触图, 还不足以诚实地断言“人物已经完全时间静止”.
- 由于当前单条 40 steps 实测耗时约 `42 分 53 秒`, 若直接扩到 6 条, 时间成本会很高.

### 状态
**目前在阶段4**
- 本轮最小验证已经完成.
- 当前更合适的下一步, 是先让用户基于对照视频确认效果是否足够接近“时间静止”, 再决定是否全量 6 条重跑.

## [2026-03-15 12:54:30 UTC] 新任务启动: 更强时间静止提示词 + 新场景 `demo_data/my2/10000.png`

### 目标
- 进一步增强“时间静止”语义约束.
- 将验证场景切换到新的输入图 `demo_data/my2/10000.png`.
- 避免在新场景上直接全量重跑 6 条轨迹, 先做一个可复用、成本可控的单轨迹验证入口.

### 阶段
- [x] 阶段1: 读取 OpenSpec / 六文件 / 新场景输入状态
- [ ] 阶段2: 为批处理脚本增加单轨迹选择能力
- [ ] 阶段3: 用新场景执行 0 号轨迹“时间静止”真实生成
- [ ] 阶段4: 校验新视频产物并整理结论

### 关键问题
1. 新场景验证是否必须全跑 6 条轨迹.
2. 当前脚本是否缺少“只跑指定轨迹”的正式入口.
3. 更强提示词是否应该沉淀为本轮真实命令模板, 而不是只保留在终端历史里.

### 做出的决定
- 决定: 给 `single_image_multi_trajectory.py` 增加 `--preset_indices`.
  - 理由: 当前单条 `40 steps` 已经接近 43 分钟, 没有 subset 能力的话, 新场景验证成本过高.
- 决定: 新场景先只跑 `0` 号轨迹.
  - 理由: 这仍然是最小可证伪实验, 并且更符合当前“先验证 prompt 再扩展”的阶段目标.

### 状态
**目前在阶段2**
- 已确认 `demo_data/my2/10000.png` 存在.
- 已确认 OpenSpec 旧 change 已全部完成, 这轮属于小幅增强 + 新场景验证.

## [2026-03-15 13:11:30 UTC] 新场景 0 号轨迹真实链路已推进到 Step 6

### 阶段
- [x] 阶段1: 读取 OpenSpec / 六文件 / 新场景输入状态
- [x] 阶段2: 为批处理脚本增加单轨迹选择能力
- [ ] 阶段3: 用新场景执行 0 号轨迹“时间静止”真实生成
- [ ] 阶段4: 校验新视频产物并整理结论

### 现象
- 第一次直接运行新场景时, Step 1 默认去拉 `Ruicheng/moge-2-vitl-normal`, 终端进度条长时间停在 `0.00/1.32G`.
- 进一步检查 Hugging Face Xet 日志后确认:
  - 下载底层字节数在增长
  - 但远程拉权重过慢, 不适合作为当前验证路径
- 改用本地已缓存的 `Ruicheng/moge-2-vitl/model.pt` 后:
  - Step 1 深度估计已成功完成
  - Step 5 控制图渲染已成功完成
  - Step 6 已进入 `40` 步采样

### 做出的决定
- 决定: 新场景临时使用 `--moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`.
  - 理由: 避开远程下载瓶颈, 先完成本轮“时间静止”样本验证.

### 状态
**目前在阶段3**
- 新场景 `demo_data/my2_timefreeze_10000/0` 已完成共享深度与控制图, 当前正在等待 40 步最终视频落盘.

## [2026-03-15 13:52:30 UTC] 新场景 0 号轨迹时间静止样本已完成

### 阶段
- [x] 阶段1: 读取 OpenSpec / 六文件 / 新场景输入状态
- [x] 阶段2: 为批处理脚本增加单轨迹选择能力
- [x] 阶段3: 用新场景执行 0 号轨迹“时间静止”真实生成
- [x] 阶段4: 校验新视频产物并整理结论

### 验证
- 已执行测试:
  - `pixi run python -m pytest tests/test_single_image_multi_trajectory_smoke.py tests/test_single_image_multi_trajectory_lib.py`
  - 结果: `13 passed`
- 已完成真实生成:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`
- 已完成元数据校验:
  - `1280x720`
  - `16 fps`
  - `81 frames`
  - `duration 5.0625s`
- 已完成状态校验:
  - `manifest.status = completed`
  - `selected_preset_indices = [0]`

### 做出的决定
- 决定: 新场景本轮暂时不继续扩展到 `1-5`.
  - 理由: 这轮目标已经完成, 并且单条 `40 steps` 仍是高成本验证项.

### 状态
**目前在阶段4**
- 新场景样本已经完成, 准备向用户交付结果和后续建议.

## [2026-03-15 14:17:31 UTC] 新任务启动: 为新场景 0 号轨迹补跑 10 步对比样本

### 目标
- 保留现有 `40` 步结果不变.
- 基于同一份 `rendering_4D_maps`, 额外生成一份 `10` 步版本视频.
- 让用户直接比较 `10` 步和 `40` 步的画质差异.

### 阶段
- [x] 阶段1: 核对现有 40 步输出、控制图和进程状态
- [ ] 阶段2: 重跑新场景 0 号轨迹的 Step 6, 输出到新目录
- [ ] 阶段3: 校验 10 步视频并准备对照资产

### 做出的决定
- 决定: 不重复 Step 1 和 Step 5, 只重跑 Step 6.
  - 理由: 当前要比较的是采样步数, 复用同一份控制图才能把变量收紧到最小.
- 决定: 新输出目录使用 `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare`.
  - 理由: 明确表达用途, 同时避免覆盖现有 `generated_videos`.

### 状态
**目前在阶段2**
- 已确认当前没有残留生成进程.
- 已确认 `demo_data/my2_timefreeze_10000/0/rendering_4D_maps` 完整存在, 可以直接复用.

## [2026-03-15 14:25:00 UTC] 10 步对比样本已暂停, 先核对 MoGe fallback 是否合理

### 现象
- 用户对 `moge-2-vitl` 代替 `moge-2-vitl-normal` 的合理性提出质疑.
- 当时 10 步对比样本已跑到 Step 6 `5/10`, 但这个问题属于上游几何模型语义问题.

### 做出的决定
- 决定: 先中断 10 步生成, 优先回答模型差异问题.
  - 理由: 如果上游替代本身不成立, 继续跑对比样本没有意义.

### 已验证结论
- 本项目默认 `v2` 确实指向 `moge-2-vitl-normal`.
- `moge-2-vitl-normal` 与 `moge-2-vitl` 不完全相同:
  - 前者有 normal capability
  - 后者没有
- 但当前 VerseCrafter 下游只消费 `depth` 和 `intrinsic`, 不消费 `normal`.
- 因此:
  - 把 `moge-2-vitl` 当成“当前链路的临时 fallback”有依据
  - 但不能把它说成与默认模型完全等价

### 状态
**目前在阶段2**
- 已暂停 10 步对比样本, 等待基于这次核对结果再决定是否继续重跑.

### 状态
**目前在阶段2**
- 已完成目录盘点, 正在核对 README、Blender 插件和渲染/生成脚本中的真实依赖关系.

## [2026-03-15 07:43:05 UTC] 核对完成, 准备回答用户

### 阶段
- [x] 阶段1: 读取历史上下文与示例目录
- [x] 阶段2: 核对 README 与脚本中的输入输出关系
- [x] 阶段3: 汇总结论并回答用户

### 验证
- 已核对 `README.md` Step 4-6 与 `README_BLENDER.md` 的工作流说明.
- 已核对 `inference/rendering_4D_control_maps.py` 与 `inference/versecrafter_inference.py` 的参数和输入输出链.
- 已检查示例目录中 `record.mov`、`generated_video_0.mp4`、`rendering_4D_maps/*.mp4` 的实际存在和视频元数据.
- 已抽样检查 `custom_3D_gaussian_trajectory.json` 与 `custom_camera_trajectory.npz`, 确认该 demo 不只是相机运动, 还包含对象运动.

### 状态
**目前在阶段3**
- 结论已形成, 正在向用户说明“Blender 必需产物”和“仅用于演示的图片/视频”的区别.

## [2026-03-15 07:45:30 UTC] 用户追问: object_mask 是否必需以及用途

### 状态
**目前在阶段2**
- 正在补核对 `object_mask/masks` 在预处理、渲染背景构建和最终控制图中的真实作用, 以回答用户“干嘛的”和“是否需要”.

## [2026-03-15 07:49:20 UTC] 用户追问: 场景里没有人/前景对象时怎么办

### 状态
**目前在阶段2**
- 正在核对分割、3D Gaussian 拟合和渲染流程是否支持 `0 objects`, 以准确回答用户“没有人时是否还需要 object_mask / gaussian / Blender 物体轨迹”.

## [2026-03-15 07:52:40 UTC] 0 个对象分支核对完成

### 验证
- 已确认 `api_server.py` 对 `0 detections` 的现行为直接失败.
- 已确认 `fit_3D_gaussian.py` 对空 `masks_dir` 的现行为报错返回.
- 已确认 `rendering_4D_control_maps.py` 能把空 mask 场景当作纯背景处理, 但仍要求 `ellipsoid_json` 文件存在.
- 已确认 Blender 导出脚本在 `0 ellipsoid` 时不会生成高斯轨迹 JSON.

### 状态
**目前在阶段3**
- 正在向用户解释: “没有人”分两种情况, 一种是还有别的前景物体, 一种是真正 0 对象; 当前仓库对后者支持不完整.

## [2026-03-15 07:56:10 UTC] 用户追问: object_mask 的生成方式

### 状态
**目前在阶段3**
- 准备基于 `inference/grounded_sam2_infer.py`、`api_server.py` 与 README, 说明 `object_mask` 是如何自动生成的, 以及用户可直接使用哪些入口来生成它.

## [2026-03-15 08:24:30 UTC] 新探索: 设计 VerseCrafter 版单图 6 轨迹批量脚本

### 目标
- 不实现代码, 只探索并明确 VerseCrafter 中最合适的 6 条相机轨迹批量生成脚本设计.
- 对齐用户给出的 Lyra 单图命令心智模型, 但落地为 VerseCrafter 的工作流和文件结构.

### 阶段
- [x] 阶段1: 理解 Lyra 参考实现与默认参数语义
- [ ] 阶段2: 映射到 VerseCrafter 的预处理 / 轨迹 / 渲染 / 生成链路
- [ ] 阶段3: 给出 VerseCrafter 版脚本设计方案与取舍

### 关键问题
1. VerseCrafter 里最自然的入口是“一个大脚本串全流程”,还是“预处理一次 + 批量轨迹 + 批量渲染/生成”.
2. 在只控制相机运动时, 高斯轨迹 JSON 应该是“复写成静态 81 帧”,还是让渲染脚本支持单帧高斯自动 broadcast.
3. 输出组织应该沿用 `camera_object_0` 风格, 还是改成 Lyra 式 `0..5` 轨迹编号目录.

### 状态
**目前在阶段2**
- 已完成 Lyra 参考实现拆解, 正在把它映射到 VerseCrafter 的真实输入输出链和可复用模块.

## [2026-03-15 08:35:20 UTC] 继续探索: 细化 VerseCrafter 多轨迹脚本规格

### 阶段
- [x] 阶段1: 理解 Lyra 参考实现与默认参数语义
- [x] 阶段2: 映射到 VerseCrafter 的预处理 / 轨迹 / 渲染 / 生成链路
- [ ] 阶段3: 给出 VerseCrafter 版脚本设计方案与取舍

### 状态
**目前在阶段3**
- 正在把方案细化为可直接实现的规格: CLI 参数表、输入输出契约、manifest 字段、失败处理策略、坐标映射与静态高斯适配规则.

## [2026-03-15 08:38:50 UTC] 规格细化完成

### 阶段
- [x] 阶段1: 理解 Lyra 参考实现与默认参数语义
- [x] 阶段2: 映射到 VerseCrafter 的预处理 / 轨迹 / 渲染 / 生成链路
- [x] 阶段3: 给出 VerseCrafter 版脚本设计方案与取舍

### 验证
- 已核对 VerseCrafter 现有 Step 2/3/5/6 的 CLI 参数与文件契约.
- 已确认渲染脚本输出的视频文件名集合和生成脚本真实读取的控制图列表.
- 已确认 `background_and_3D_gaussian.mp4` 不是最终生成必需输入.
- 已确认第一版可采用“共享预处理一次 + 6 个数字目录逐条渲染/生成”的设计.

### 状态
**目前在阶段3**
- 探索目标已完成, 可以据此进入正式实现阶段.

## [2026-03-15 09:18:14 UTC] 执行任务: 推送当前 main 到远端 my

### 阶段
- [x] 阶段1: 确认当前分支与远端配置
- [ ] 阶段2: 执行推送到 `my`
- [ ] 阶段3: 记录结果并收尾

### 关键问题
1. 当前本地是否存在尚未提交的改动会导致“以为已经推上去, 实际没有”.
2. 远端 `my` 是否已经配置, 且当前分支是否就是用户要推送的目标.

### 目前已知
- 当前分支为 `main`.
- `git status --short --branch` 显示本地相对 `origin/main` 超前 1 个提交.
- 远端 `my` 已存在, 指向 `https://github.com/raiscui/VerseCrafter.git`.
- 工作区当前没有未提交改动.

### 状态
**目前在阶段2**
- 已完成推送前确认, 接下来执行 `git push my main`.

## [2026-03-15 08:42:40 UTC] 开始正式创建 OpenSpec 变更

### 目标
- 在 VerseCrafter 仓库中初始化 OpenSpec 工作区.
- 基于已完成的探索结果创建一个新的 change, 作为 VerseCrafter 单图 6 轨迹相机脚本的正式实现入口.

### 做出的决定
- 决定: change 名暂定为 `add-versecrafter-single-image-multi-trajectory-script`.
  - 理由: 与前面探索阶段形成的命名一致, 能准确表达“VerseCrafter / 单图 / 多轨迹 / 脚本”四个核心要素.
- 决定: 先只创建 change 和读取首个 artifact 模板, 不在这一步直接写 proposal/design/tasks.
  - 理由: 这符合 OpenSpec 新建 change 的标准起手流程, 也便于在继续实现前让用户确认变更入口.

### 阶段
- [ ] 阶段4: 初始化 OpenSpec 并创建 change

### 状态
**目前在阶段4**
- 正在初始化 VerseCrafter 的 OpenSpec 工作区, 并准备创建新的 change.

## [2026-03-15 09:18:57 UTC] 推送结果: `my/main` 已与本地 `HEAD` 对齐

### 阶段
- [x] 阶段1: 确认当前分支与远端配置
- [x] 阶段2: 执行推送到 `my`
- [x] 阶段3: 记录结果并收尾

### 验证
- 执行命令: `git push my main`
- 终端输出: `Everything up-to-date`
- 本地 `HEAD`: `2cee0c6c74b0783ae2f322c3d006550a7f9eb8ee`
- 远端 `my/main`: `2cee0c6c74b0783ae2f322c3d006550a7f9eb8ee`

### 结论
- 推送动作执行成功.
- 这次没有产生新的上传对象, 因为远端 `my/main` 在执行前就已经和当前本地提交一致.

### 状态
**目前在阶段3**
- 推送任务已完成, 接下来补写 `WORKLOG.md` 并结束本轮.

## [2026-03-15 08:50:10 UTC] 执行 openspec-ff-change: 快速补齐实现前 artifacts

### 目标
- 基于已创建的 change `add-versecrafter-single-image-multi-trajectory-script`, 一次性补齐进入实现所需的 OpenSpec artifacts.
- 产出 `proposal`、`design`、`specs`、`tasks`, 让后续可以直接进入实现阶段.

### 做出的决定
- 决定: 继续使用已创建的 change, 不重新创建同名 change.
  - 理由: change 已存在, 且前序探索结论已经稳定.
- 决定: capabilities 先按“新增 capability”为主来建模, 不强行声明修改现有 capability.
  - 理由: VerseCrafter 当前仓库刚初始化 OpenSpec, 没有现成 specs 需要增量修改.

### 阶段
- [ ] 阶段5: 读取 JSON 状态与 instructions
- [ ] 阶段6: 生成 proposal / design / specs / tasks
- [ ] 阶段7: 校验 OpenSpec 状态并准备进入实现

### 状态
**目前在阶段5**
- 正在读取 change 的 JSON 状态、artifact build order 和 schema instructions.

## [2026-03-15 08:53:30 UTC] 开始编写 proposal artifact

### 阶段
- [x] 阶段5: 读取 JSON 状态与 instructions
- [ ] 阶段6: 生成 proposal / design / specs / tasks
- [ ] 阶段7: 校验 OpenSpec 状态并准备进入实现

### 状态
**目前在阶段6**
- 正在编写 `proposal.md`, 明确本次 change 的 Why / What Changes / Capabilities / Impact.

## [2026-03-15 09:24:30 UTC] 继续执行 openspec-ff-change: 补齐剩余 artifacts

### 阶段
- [x] 阶段5: 读取 JSON 状态与 instructions
- [ ] 阶段6: 生成 proposal / design / specs / tasks
- [ ] 阶段7: 校验 OpenSpec 状态并准备进入实现

### 当前行动
- 重新读取 `openspec instructions design/specs/tasks` 的完整输出.
- 读取 `openspec-ff-change` 与 `humanizer-zh` skill 的关键说明, 确保本轮产物格式和表达方式都对齐要求.
- 然后直接落盘 `design.md`、capability spec、`tasks.md`.

### 状态
**目前在阶段6**
- proposal 已完成, 当前正在补齐 design / specs / tasks 所需的最后约束信息.

## [2026-03-15 09:38:40 UTC] OpenSpec artifacts 已补齐并完成状态校验

### 阶段
- [x] 阶段5: 读取 JSON 状态与 instructions
- [x] 阶段6: 生成 proposal / design / specs / tasks
- [x] 阶段7: 校验 OpenSpec 状态并准备进入实现

### 验证
- 已创建:
  - `openspec/changes/add-versecrafter-single-image-multi-trajectory-script/design.md`
  - `openspec/changes/add-versecrafter-single-image-multi-trajectory-script/specs/single-image-multi-trajectory-generation/spec.md`
  - `openspec/changes/add-versecrafter-single-image-multi-trajectory-script/tasks.md`
- 已执行:
  - `openspec status --change add-versecrafter-single-image-multi-trajectory-script --json`
  - `openspec status --change add-versecrafter-single-image-multi-trajectory-script`
- 状态结果:
  - `proposal = done`
  - `design = done`
  - `specs = done`
  - `tasks = done`
  - `All artifacts complete!`

### 状态
**目前在阶段7**
- OpenSpec fast-forward 已完成. 该 change 已进入 apply-ready 状态, 下一步可以直接开始实现代码.

## [2026-03-15 09:46:10 UTC] 开始执行 openspec-apply-change

### 目标
- 基于 `add-versecrafter-single-image-multi-trajectory-script` 的 OpenSpec artifacts, 开始正式实现 VerseCrafter 单图 6 轨迹批处理脚本.
- 严格按 `tasks.md` 顺序推进, 每完成一个实现阶段就更新任务状态与日志.

### 阶段
- [ ] 阶段8: 读取 apply 指令与上下文文件
- [ ] 阶段9: 实现 orchestrator / 轨迹生成 / 高斯适配核心能力
- [ ] 阶段10: 串联渲染与最终生成, 补齐 manifest / resume
- [ ] 阶段11: 文档与验证, 更新 OpenSpec tasks 状态

### 状态
**目前在阶段8**
- 正在读取 apply 指令、上下文文件和当前任务进度, 准备进入代码实现.

## [2026-03-15 10:18:10 UTC] OpenSpec apply 实现完成并通过本地验证

### 阶段
- [x] 阶段8: 读取 apply 指令与上下文文件
- [x] 阶段9: 实现 orchestrator / 轨迹生成 / 高斯适配核心能力
- [x] 阶段10: 串联渲染与最终生成, 补齐 manifest / resume
- [x] 阶段11: 文档与验证, 更新 OpenSpec tasks 状态

### 已完成实现
- 新增 `inference/single_image_multi_trajectory.py`
- 新增 `inference/single_image_multi_trajectory_lib.py`
- 新增轨迹 / 高斯适配 / resume / manifest 单测与 smoke test
- 更新 `README.md`
- 更新 `inference/versecrafter_inference.py`, 支持 `--negative_prompt`
- 将 OpenSpec `tasks.md` 全部勾选完成

### 验证
- `python3 -m py_compile inference/single_image_multi_trajectory_lib.py inference/single_image_multi_trajectory.py inference/versecrafter_inference.py`
- `python3 -m pytest tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`
- `python3 inference/single_image_multi_trajectory.py --help`
- `openspec status --change add-versecrafter-single-image-multi-trajectory-script`

### 状态
**目前在阶段11**
- 本次 OpenSpec apply 已完成. 代码、文档、测试和 tasks 状态已同步, 接下来可以进入真实环境 smoke run 或归档该 change.

## [2026-03-15 10:24:40 UTC] 新任务: 对单图 6 轨迹脚本做 dry-run 与实跑测试

### 目标
- 先对新实现的 `inference/single_image_multi_trajectory.py` 做一次 dry-run.
- 然后以 `demo_data/my/0001.png` 作为测试素材, `demo_data/my` 作为数据目录, 尝试做真实运行验证.
- 若真实运行失败, 要明确区分是环境依赖问题、模型权重问题, 还是脚本逻辑问题.

### 阶段
- [ ] 阶段12: 确认测试素材与环境可运行性
- [ ] 阶段13: 补充并执行 dry-run
- [ ] 阶段14: 对 `demo_data/my` 做真实测试
- [ ] 阶段15: 记录结果与后续建议

### 状态
**目前在阶段12**
- 正在确认 `demo_data/my/0001.png` 与运行环境, 然后再进行 dry-run 和实际测试.

## [2026-03-15 10:29:20 UTC] 继续测试: 先补 `--dry_run`, 再对 `demo_data/my` 执行 dry-run

### 阶段
- [x] 阶段12: 确认测试素材与环境可运行性
- [ ] 阶段13: 补充并执行 dry-run
- [ ] 阶段14: 对 `demo_data/my` 做真实测试
- [ ] 阶段15: 记录结果与后续建议

### 已知事实
- `demo_data/my/0001.png` 已存在, 尺寸为 `1280x720`.
- 全局 `python3` 环境缺少 `diffusers` / `omegaconf`, 但 `pixi run python` 环境完整.
- GPU 可用: `NVIDIA A800-SXM4-80GB`.
- `model/VerseCrafter` 与 `model/Wan2.1-T2V-14B` 权重目录已存在.

### 状态
**目前在阶段13**
- 正在为新 orchestrator 增加 `--dry_run`, 这样后续测试能先验证命令编排和输出规划, 再进入真实执行.

## [2026-03-15 10:34:20 UTC] 测试中遇到首个阻塞: MoGe 默认权重下载卡住

### 现象
- `pixi run python inference/single_image_multi_trajectory.py ...` 已进入 Step 1.
- 但 `moge-v2_infer.py` 默认下载 `Ruicheng/moge-2-vitl-normal/model.pt` 时, 进度长时间停在 `0.00/1.32G`.

### 假设
- 当前阻塞不是 orchestrator 逻辑错误.
- 更像是默认 MoGe v2 checkpoint 的下载/缓存问题.
- 同机缓存里已经有可复用的本地 MoGe 权重变体, 但 orchestrator 还没有把 `--pretrained` 透传给 Step 1.

### 验证证据
- `~/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl-normal/...incomplete` 大小为 `0`.
- 同时存在:
  - `models--Ruicheng--moge-vitl/.../model.pt`
  - `models--Ruicheng--moge-2-vitl/.../model.pt`

### 当前决策
- 先终止本轮卡住的下载进程.
- 给 orchestrator 增加 `--moge_pretrained` 参数, 直接透传到 `moge-v2_infer.py --pretrained`.
- 然后使用本机已缓存的 MoGe 权重重新测试.

### 状态
**目前在阶段14**
- 正在绕过 Step 1 的默认权重下载阻塞, 以便继续验证整条链路.

## [2026-03-15 10:37:40 UTC] 真实测试失败定位: Step 5 视频保存与 torchvision/av 兼容性问题

### 现象
- `demo_data/my` 的共享 Step 1-3 已全部跑通.
- 第 1 条轨迹在 `rendering_4D_control_maps.py::save_video_from_frames()` 保存 `background_RGB.mp4` 时失败.
- 堆栈落点:
  - `torchvision.io.write_video`
  - `av.video.frame.VideoFrame.pict_type.__set__`
  - `TypeError: an integer is required`

### 假设
- 这不是新 orchestrator 的逻辑错误.
- 更像是当前 `torchvision` 与 `PyAV` 版本组合导致的 API 兼容性问题.
- 由于 Step 5 的渲染本身已经完成, 问题集中在“写 mp4 文件”这一步.

### 验证计划
- 先阅读 `save_video_from_frames()` 当前实现.
- 若它只是在做 RGB 帧写视频, 则改为更稳定的 `cv2.VideoWriter` 路线, 避免 `torchvision.write_video`.
- 增加一个最小回归测试, 验证给几帧 `uint8` 图像时确实能落出非空 mp4 文件.
- 然后重新跑 `demo_data/my` 测试.

### 状态
**目前在阶段14**
- 正在修复 Step 5 的视频写出兼容性 bug, 修好后继续真实测试.

## [2026-03-15 10:25:00 UTC] 新任务启动: 验证单图多轨迹真实测试中的 Step 5 视频写出修复

### 目标
- 先验证 `inference/rendering_4D_control_maps.py` 中新写入的 `cv2.VideoWriter` 修复是否正确.
- 再基于 `demo_data/my/0001.png` 继续真实跑通 VerseCrafter 单图 6 轨迹工作流.
- 在不破坏已生成 shared 产物的前提下, 尽量复用已有 Step 1-4 结果, 完成 0-5 六条轨迹的视频生成验证.

### 阶段
- [x] 阶段1: 读取六文件上下文与已有实现状态
- [ ] 阶段2: 核对 Step 5 失败现象与当前修复代码
- [ ] 阶段3: 最小验证视频写出修复
- [ ] 阶段4: 继续真实跑通 6 条轨迹测试
- [ ] 阶段5: 汇总结论并回写文档日志

### 关键问题
1. 当前 Step 5 失败是否确实来自 `torchvision.io.write_video` 与 `av` 的兼容问题.
2. 切到 `cv2.VideoWriter` 后, 是否还能保持 Step 5 产出文件格式被 Step 6 正常消费.
3. 真实测试是否还会暴露新的链路问题, 尤其是 Step 6 与输出目录组织.

### 做出的决定
- 决定: 先不盲目重跑整条 6 轨迹链路, 而是先做 `save_video_from_frames()` 的最小验证.
  - 理由: 这是当前唯一已知阻塞点, 先缩小验证范围更快.
- 决定: 真实测试继续使用 `pixi run python`, 并显式传 `--moge_pretrained` 指向本地缓存.
  - 理由: 已有证据表明系统 Python 缺关键依赖, 且默认 MoGe 下载会卡住.

### 遇到的错误
- 暂无新错误, 正在读取当前 Step 5 修复后的代码与数据状态.

### 状态
**目前在阶段2**
- 正在核对 `rendering_4D_control_maps.py` 的写视频修复, 准备做最小 smoke 验证.

## [2026-03-15 10:29:00 UTC] Step 5 写视频最小验证通过, 准备继续真实链路

### 阶段
- [x] 阶段1: 读取六文件上下文与已有实现状态
- [x] 阶段2: 核对 Step 5 失败现象与当前修复代码
- [x] 阶段3: 最小验证视频写出修复
- [ ] 阶段4: 继续真实跑通 6 条轨迹测试
- [ ] 阶段5: 汇总结论并回写文档日志

### 验证
- 已执行 `python3 -m py_compile inference/rendering_4D_control_maps.py`, 成功退出.
- 已执行最小 smoke:
  - 用 `save_video_from_frames()` 写出 `demo_data/my/_tmp_smoke/cv2_writer_smoke.mp4`
  - 再用 `torchvision.io.read_video` 读回
  - 结果: `read_shape=(4, 64, 96, 3)`, `fps=8.0`, `smoke_ok`

### 状态
**目前在阶段4**
- `cv2.VideoWriter` 写出路径已完成最小可证伪验证, 现在开始继续真实 6 轨迹生成测试.

## [2026-03-15 10:33:00 UTC] 真实测试推进到 Step 6, 暴露新的依赖阻塞

### 阶段
- [x] 阶段1: 读取六文件上下文与已有实现状态
- [x] 阶段2: 核对 Step 5 失败现象与当前修复代码
- [x] 阶段3: 最小验证视频写出修复
- [ ] 阶段4: 继续真实跑通 6 条轨迹测试
- [ ] 阶段5: 汇总结论并回写文档日志

### 现象
- 真实测试中, `left` 轨迹的 Step 5 已经完整通过, `demo_data/my/0/rendering_4D_maps` 已成功落盘.
- 新的首个阻塞出现在 Step 6 初始化阶段:
  - `ModuleNotFoundError: No module named 'librosa'`
  - 调用链: `inference/versecrafter_inference.py` -> `videox_fun.models.__init__` -> `fantasytalking_audio_encoder.py`.
- 这说明当前工作流已经越过了原来的视频写出问题.

### 状态
**目前仍在阶段4**
- 当前正在排查 Step 6 的 `librosa` 缺依赖问题, 准备决定是补环境依赖还是消除无关的音频模块强导入.

## [2026-03-15 10:42:00 UTC] 验证阶段暴露 pixi 环境缺少 pytest

### 现象
- 执行 `pixi run python -m pytest ...` 时失败:
  - `/workspace/VerseCrafter/.pixi/envs/default/bin/python: No module named pytest`
- 这不是本次功能逻辑错误, 但会导致仓库在官方 pixi 环境中无法直接运行已有测试.

### 当前决定
- 先补齐 pixi 环境中的 `pytest`, 再继续验证当前修复与真实生成链路.

### 状态
**目前仍在阶段4**
- 正在修补验证环境, 之后继续跑 pytest 与真实生成.

## [2026-03-15 10:47:00 UTC] Step 6 导入修复验证通过, 继续真实生成

### 阶段
- [x] 阶段1: 读取六文件上下文与已有实现状态
- [x] 阶段2: 核对 Step 5 失败现象与当前修复代码
- [x] 阶段3: 最小验证视频写出修复
- [ ] 阶段4: 继续真实跑通 6 条轨迹测试
- [ ] 阶段5: 汇总结论并回写文档日志

### 验证
- 已执行 `pixi install`, 成功把 `pytest` 装入默认环境.
- 已执行 `pixi run python -m pytest tests/test_videox_fun_optional_audio_import.py tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`.
- 结果: `8 passed`.
- 已执行最小导入 smoke, 确认在缺少 `librosa` 的环境里:
  - `from videox_fun.models import AutoencoderKLWan, WanT5EncoderModel`
  - `from versecrafter.pipeline import WanVerseCrafterPipeline`
  都可成功导入.

### 状态
**目前仍在阶段4**
- Step 5 与 Step 6 的当前已知阻塞都已分别验证并修复, 现在重新回到真实 6 轨迹生成测试.

## [2026-03-15 10:36:00 UTC] Step 6 显存模式验证完成, 默认值切到 qfloat8 offload

### 现象
- `model_cpu_offload` 虽然把常驻显存压低到了约 22 GiB, 但在第 1 步采样阶段仍然 OOM.
- `model_cpu_offload_and_qfloat8` 在同样的 A800 80GB、720x1280、10 步、81 帧配置下, 已完整跑通第 0 条轨迹并成功输出 `generated_video_0.mp4`.

### 已验证结论
- 对当前单图多轨迹单卡工作流来说, 默认显存模式应改为 `model_cpu_offload_and_qfloat8`, 而不是 `model_cpu_offload`.
- 已将该模式做成显式 CLI 参数, 并把批处理脚本默认值切到这个已验证模式.

### 验证证据
- 失败证据:
  - `--gpu_memory_mode model_cpu_offload`
  - 运行到 `1/10` 后报 `torch.cuda.OutOfMemoryError`.
- 成功证据:
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`
  - 运行 `14:02` 后成功输出 `demo_data/my/0/generated_videos/generated_video_0.mp4`.

### 状态
**目前仍在阶段4**
- 当前准备让批处理脚本重新接管状态, 跳过已完成的 0 号轨迹, 从后续轨迹继续生成.

## [2026-03-15 11:22:00 UTC] 新增 camera-only 模式, 用于纯相机运动且无前景运动

### 阶段
- [x] 阶段1: 读取六文件上下文与已有实现状态
- [x] 阶段2: 核对 Step 5 失败现象与当前修复代码
- [x] 阶段3: 最小验证视频写出修复
- [x] 阶段4: 继续真实跑通 6 条轨迹测试
- [x] 阶段5: 汇总结论并回写文档日志
- [x] 阶段6: 分析“前景看起来像 demo 拷贝”并新增 camera-only 模式

### 已验证事实
- `demo_data/my/0001.png` 与 `demo_data/LXKcD2zSPMc_0351466_0353266_0001469_0001550/0001.png` 的 SHA-256 完全一致.
- `demo_data/my/0/custom_3D_gaussian_trajectory.json` 是静态重复轨迹:
  - frame0 mean == frame1 mean
- demo 目录中的同名轨迹不是静态重复:
  - frame0 mean != frame1 mean
- 因此当前 my 目录的前景轨迹不是直接抄 demo 的“移动轨迹”, 而是基于同一张输入图重新拟合出的静态版本.

### 做出的决定
- 决定: 新增 `--camera_only` 模式.
  - 理由: 用户明确要求只做相机运动, 不需要前景运动; 继续保留分割 + Gaussian 前景链路会让模型有更多机会把人车当成独立前景去发挥.

### 状态
**目前已完成本轮修复与验证**
- 新脚本已支持 `--camera_only`, dry-run 与测试全部通过. 是否用 `demo_data/my` 覆盖重跑, 需要根据用户是否接受覆盖现有结果来决定.

## [2026-03-15 11:30:00 UTC] 用户确认覆盖重跑: 使用 camera-only 模式重新生成 6 条视频

### 目标
- 覆盖 `demo_data/my` 中旧的前景版结果.
- 使用 `--camera_only --no_resume` 重新生成 6 条纯相机运动视频.
- prompt 同步改成“人车静止, 无独立前景运动”的语义, 降低模型自由发挥前景运动的倾向.

### 做出的决定
- 决定: 保持同一输入图与同一输出目录 `demo_data/my`, 直接覆盖旧结果.
  - 理由: 用户已明确同意覆盖.
- 决定: 不沿用之前带 `pedestrians walking` / `light traffic` 的 prompt.
  - 理由: 该语义会主动鼓励模型生成人车运动, 与当前目标冲突.

### 状态
**目前在执行覆盖重跑**
- 正在启动 camera-only 版本的 6 轨迹批处理.

## [2026-03-15 11:50:00 UTC] 用户要求改成“时间静止”并将步数提升到 40, 先做 0 号轨迹验证

### 现象
- 即使在 `camera_only` 下, 用户仍观察到人物在动.

### 当前主假设
- 主假设: 这主要是生成模型的时间先验在发挥作用, `camera_only` 只移除了显式前景控制, 还不足以单靠几何完全冻结人物.
- 最强备选解释: 当前 prompt / negative prompt 对“时间静止”的约束还不够强.

### 做出的决定
- 决定: 先只重跑 0 号轨迹, 用更强的时间静止 prompt 和 `--num_inference_steps 40` 验证.
  - 理由: 单卡 40 步全量 6 条会非常久, 先验证一条更稳.

### 状态
**目前在执行 0 号轨迹的时间静止验证**
- 若 0 号效果正确, 再继续把同一设置扩展到 1-5.

## [2026-03-15 14:31:00 UTC] 用户选择方案 2, 继续补跑新场景 10 步对比样本

### 现象
- 用户已经确认接受 `moge-2-vitl` 作为当前链路的临时 fallback, 不再停留在模型语义争论阶段.
- 现有 40 步时间静止样本已经存在:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`
- 10 步对比目录当前不存在:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare`
- 0 号轨迹的 Step 5 控制图目录已经存在:
  - `demo_data/my2_timefreeze_10000/0/rendering_4D_maps`

### 做出的决定
- 决定: 不重跑 Step 1-5, 直接复用现有 `rendering_4D_maps`, 只补跑 Step 6.
  - 理由: 用户当前目标是对比 10 步与 40 步画质, 不是重建整条链路.
- 决定: 10 步输出使用独立目录 `generated_videos_steps10_compare`, 不覆盖现有 40 步结果.
  - 理由: 用户明确要求保留旧结果用于并排比较.
- 决定: 保持同一组 frozen-in-time prompt 与 negative prompt, 只改 `--num_inference_steps 10`.
  - 理由: 这样对比才聚焦在步数变化, 不把 prompt 变量混进去.

### 状态
**目前在执行 10 步对比样本补跑**
- 下一步直接启动 `demo_data/my2_timefreeze_10000/0` 的 Step 6, 跑完后生成 contact sheet 与 10/40 步并排对比视频.

## [2026-03-15 14:51:00 UTC] 10 步对比样本、接触图和并排对比视频已完成

### 验证
- 已成功输出:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0.mp4`
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/frames_contact_sheet.jpg`
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0_vs_steps40_side_by_side.mp4`
- `ffprobe` 已确认 10 步版与 40 步版主视频元数据一致:
  - `1280x720`
  - `16 fps`
  - `81 frames`
  - `5.0625s`
- 并排对比视频元数据:
  - `2560x784`
  - `16 fps`
  - `81 frames`
  - `5.0625s`

### 状态
**目前已完成本轮 10 步对比验证**
- 当前已经具备可直接观看的 10 步样本、40 步样本和并排对比视频, 可以进入用户决策阶段: 是继续全量 6 条跑 10 步, 还是保留 40 步做正式输出.

## [2026-03-15 15:00:00 UTC] 记录当前只相机控制命令到 `cmd.md`

### 现象
- 用户要求把“现在只相机控制”的实际使用命令整理成单独文档, 便于后续复跑和对照.
- 仓库根目录当前不存在 `cmd.md`.

### 做出的决定
- 决定: 新建根目录 `cmd.md`.
  - 理由: 这类命令需要被长期复用, 直接落成文档比散落在对话和日志里更稳.
- 决定: 文档同时记录两类命令:
  - `single_image_multi_trajectory.py` 的 `--camera_only` 整链路命令
  - `versecrafter_inference.py` 的 Step 6 复跑命令
  - 理由: 一个适合全流程复现, 一个适合高成本场景下只重跑最终生成.

### 验证
- 已新建:
  - `cmd.md`
- 已确认文档内包含:
  - `--camera_only`
  - `--moge_pretrained`
  - `--auto_center_depth_quantile 0.2`
  - `--translation_reference_depth_scale 0.95`
  - `--total_movement_distance_factor 1.5`
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`

### 状态
**目前已完成命令文档记录**
- 当前 `cmd.md` 已可作为只相机控制工作流的命令备忘与复现入口.

## [2026-03-15 15:08:00 UTC] 新任务: 用 `demo_data/my3` 跑 0 号镜头 20 step 快速版

### 现象
- 用户要求对新场景 `demo_data/my3` 执行当前只相机控制工作流.
- 输入目录当前只有一张图:
  - `demo_data/my3/generated-image (1).png`
- 目标输出目录当前不存在:
  - `demo_data/my3_shinkai_quick20`

### 做出的决定
- 决定: 使用 `single_image_multi_trajectory.py` 整链路跑法, 而不是只重跑 Step 6.
  - 理由: `my3` 是新场景, 还没有现成的深度、控制图和轨迹可复用.
- 决定: 只跑 `0` 号轨迹, 采样步数设为 `20`.
  - 理由: 用户明确要“快速版本”, 先做最小样本最省时间.
- 决定: 保持 `--camera_only`, 并继续使用已验证过的本地 `moge-2-vitl` 权重路径和单卡显存模式.
  - 理由: 这样最贴近当前稳定工作流, 也能避免重新卡在远程模型下载.

### 状态
**目前在执行 `my3` 新场景快速验证**
- 下一步直接启动 `demo_data/my3/generated-image (1).png` 的 0 号轨迹 20 step 生成.

## [2026-03-15 15:54:00 UTC] `my3` 的 0 号镜头 20 step 快速版已完成

### 验证
- 已成功输出:
  - `demo_data/my3_shinkai_quick20/0/generated_videos/generated_video_0.mp4`
  - `demo_data/my3_shinkai_quick20/0/generated_videos/frames_contact_sheet.jpg`
- `manifest.json` 已确认:
  - `status = completed`
  - `selected_preset_indices = [0]`
  - `camera_only = True`
  - `trajectory0_status = completed`
- `ffprobe` 已确认视频元数据:
  - `1280x720`
  - `16 fps`
  - `81 frames`
  - `5.0625s`
  - `h264`

### 状态
**目前已完成 `my3` 快速版生成**
- 当前已经有可直接查看的 20 step 快速样本. 如果后面用户认可这条风格和镜头方向, 下一步就可以升到 40 step 或扩展到更多轨迹.

## [2026-03-15 16:00:00 UTC] 新任务: 排查 `rendering_4D_maps` 视频为何“看不了”

### 现象
- 用户反馈:
  - `demo_data/my3_shinkai_quick20/0/rendering_4D_maps` 里的视频“看不了”.
- 当前还不知道是:
  - 视频文件本身损坏
  - 编码 / 像素格式不兼容
  - 还是这些控制图视频本来就不适合普通观看

### 做出的决定
- 决定: 先做最小证据收集.
  - 理由: 必须先区分“文件坏了”和“文件能被模型读但不适合普通播放器”.
- 决定: 优先检查:
  - 文件列表与大小
  - `ffprobe` 元数据
  - OpenCV 能否读回
  - `rendering_4D_control_maps.py` 的写出逻辑

### 状态
**目前在排查控制图视频可视化问题**
- 下一步先验证 `background_RGB.mp4`、`background_depth.mp4`、`merged_mask.mp4` 等控制图的编码与像素格式.
