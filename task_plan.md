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
