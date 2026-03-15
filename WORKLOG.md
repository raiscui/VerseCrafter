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
