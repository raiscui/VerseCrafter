# 关键洞察

## [2026-03-14 17:20:00 UTC] 主题: pixi 对带 PyPI 源码依赖的 dry-run 校验有边界

### 发现来源
- 在 VerseCrafter 将 README 的环境管理从 Conda 迁移到 `pixi` 时, 使用 `pixi lock --manifest-path pixi.toml --dry-run` 验证新 manifest.

### 核心问题
- `pixi lock --dry-run` 在求解包含 PyPI 依赖的环境时, 可能因为 `--no-install` 禁止初始化 conda 环境而提前失败.
- 这种失败不等价于 `pixi.toml` 语法错误或依赖声明错误.

### 为什么重要
- 如果把这个报错误读成 manifest 本身有问题, 很容易在错误方向上反复修改依赖表.
- 正确理解这个边界后, 才能把“manifest 可读”与“完整环境可安装”分开验证.

### 未来风险
- 后续如果项目继续增加 Git / 本地 editable / 需要编译的 PyPI 依赖, 会更频繁碰到这个现象.
- 如果没有记录, 下次迁移环境工具或补 lockfile 时还会重复踩坑.

### 当前结论
- `pixi task list`、`pixi workspace channel/platform list` 可用于轻量验证 manifest 可读取.
- 完整的求解与安装验证, 仍需要真实执行 `pixi install` 或等价流程.

### 后续讨论入口
- 继续推进时先看 `pixi.toml`、`LATER_PLANS.md` 中关于 `pixi.lock` 的后续计划.

## [2026-03-15 04:04:00 UTC] 主题: pixi 多行任务不是 Bash 脚本, 复杂条件应避免直接内联

### 发现来源
- 在修复 `install-pytorch3d` 任务时报 `Unsupported reserved word`, 并通过最小复现实验验证 Pixi 任务语法边界.

### 核心问题
- Pixi 默认 `deno_task_shell` 不能直接按 Bash 心智使用 `if ... then ... fi`.
- 多行任务中的普通换行也不会自动代表“下一条命令”; 如果上一行使用 `&&` / `||`, 下一条命令需要明确接在布尔链里.

### 为什么重要
- 研究型仓库经常喜欢把安装逻辑直接塞进 `pixi.toml`; 一旦逻辑稍微复杂, 很容易写成“看起来像 shell, 实际不能跑”的配置.
- 如果没有记录, 下次继续给 `bootstrap` 增加任务时, 还会重复踩同一个解析坑.

### 未来风险
- 后续如果继续往 `pixi.toml` 里堆更多带条件判断、循环、here-doc 的任务, 出错概率会快速升高.
- 把复杂逻辑长期保留在内联任务里, 可读性和可维护性都会下降.

### 当前结论
- 简单条件优先改写成 and/or list, 例如 `cmd1 || test -d path`.
- 若逻辑再复杂一个层级, 更适合迁移到独立脚本文件, 再由 Pixi 调脚本.

### 后续讨论入口
- 下次扩展 `bootstrap` 任务时, 先回看这条记录和 `ERRORFIX.md` 中的最小复现实验结论.

## [2026-03-15 09:38:40 UTC] 主题: VerseCrafter 当前 inference 脚本偏 CLI-first, 新 workflow 更适合先做编排层而不是库化重构

### 发现来源
- 在为单图 6 轨迹批处理脚本编写 OpenSpec design 时, 复核了 `versecrafter_inference.py`、`rendering_4D_control_maps.py` 等现有入口的实际结构.

### 核心问题
- 多个 inference 脚本当前是“作为命令直接运行”优先设计, 不是“可以稳定 import 的库模块”优先设计.
- 例如 `versecrafter_inference.py` 在文件顶层就解析 CLI 参数并继续执行主逻辑. 这让它不适合作为 orchestrator 中的普通函数来复用.

### 为什么重要
- 以后只要再出现“批处理工作流”“服务化封装”“Web API 编排”“多镜头自动生成”这类需求, 都会碰到同一类结构边界.
- 如果没有记录, 后续很容易一上来就误判为“直接 import 最干净”, 结果把一次中等需求放大成整仓库推理入口重构.

### 未来风险
- 如果继续新增更多批处理入口, 但每次都只在外层堆脚本, 长期可能形成第二层 CLI 套 CLI 的可维护性问题.
- 如果未来确实要做服务端或 UI 深度集成, 迟早要把 Step 5/6 抽成更稳定的库接口.

### 当前结论
- 当前阶段最稳的路线是: 先新增编排层, 复用现有 CLI, 把新需求集中到最小新增模块里.
- 等 workflow 行为稳定后, 再考虑把高价值步骤逐步抽成可 import 的 library API.

### 后续讨论入口
- 下次如果进入实现阶段或再做第二个批处理入口, 建议先回看这条记录和本次 `design.md` 的 Decisions 1、6.

## [2026-03-15 10:18:10 UTC] 主题: Lyra 到 VerseCrafter 的轨迹迁移里, 最容易出错的是把 OpenCV 方向直接当成 Blender 方向

### 发现来源
- 在实现单图 6 轨迹批处理脚本时, 需要把 Lyra 的相机运动语义迁移到 VerseCrafter 的 Blender 轨迹文件格式.

### 核心问题
- Lyra 的轨迹公式是在 OpenCV 坐标里表达的:
  - X=right
  - Y=down
  - Z=forward
- VerseCrafter 最终落盘给 Step 5 的 `custom_camera_trajectory.npz` 和 `custom_3D_gaussian_trajectory.json` 却是 Blender 坐标:
  - X=right
  - Y=forward
  - Z=up
- 如果只是按名字去猜方向, 很容易把 `up`、orbit 的竖直分量、Gaussian mean/covariance 的轴交换写反.

### 为什么重要
- 这类错误通常不会直接报异常, 而是表现成“视频能生成, 但镜头方向微妙地不对”.
- 一旦没有测试锁定, 后续很难靠肉眼追溯到底是轨迹公式错了, 还是渲染器/Blender 导出错了.

### 未来风险
- 以后如果继续增加 `down`、`counterclockwise` 或自定义轨迹, 只要有人绕开统一的 `COORD_TRANSFORM_CV2BLENDER`, 就会再次掉进同一类坑.
- 对象运动如果未来也要自动化, 协方差矩阵的轴变换同样不能省略.

### 当前结论
- 最稳的做法是:
  - 先在 OpenCV 坐标里沿用参考实现的轨迹定义
  - 再统一使用 `COORD_TRANSFORM_CV2BLENDER` 变换到 Blender
- 相机位姿、Gaussian mean、Gaussian covariance 都要走同一套变换口径.
- 已用单测锁死以下语义:
  - `up` -> Blender `z` 正方向
  - `zoom_in/out` -> Blender `y` 正/负方向
  - `clockwise` -> Blender `x-z` 平面 orbit

### 后续讨论入口
- 下次如果继续扩展轨迹类型, 先看:
  - `inference/single_image_multi_trajectory_lib.py`
  - `tests/test_single_image_multi_trajectory_lib.py`
  - `inference/blender_script/build_4d_control_scene.py` 中的 `COORD_TRANSFORM_CV2BLENDER`

## [2026-03-15 11:12:00 UTC] 主题: VerseCrafter 单卡 720p 多控制推理的真正稳定点不在 offload 本身, 而在 qfloat8 + offload 组合

### 发现来源
- 在 `demo_data/my/0001.png` 的单图多轨迹真实测试中, 对同一份控制图和同一张 A800 80GB 连续做了三种显存模式实验.

### 核心问题
- 仅把模型做 CPU offload, 不足以解决 VerseCrafter 当前 720p / 81 帧 / 多控制视频输入下的瞬时显存峰值.
- 如果默认参数只改到 `model_cpu_offload`, 用户仍会在第 1 步采样附近 OOM.

### 为什么重要
- 这说明“常驻显存下降”不等于“峰值显存安全”.
- 如果以后继续做单卡脚本、批处理工具或 Web 默认参数, 不能把 `offload` 当成已经足够的安全选项.

### 未来风险
- 如果后续有人只看静态代码, 可能会误以为 `model_cpu_offload` 已经是稳态解.
- 一旦默认值回退, 用户会在真实推理时重新踩到同样的 OOM, 而且通常发生在采样刚开始, 排查成本很高.

### 当前结论
- 对当前 VerseCrafter 单卡批处理工作流, 更稳的默认值是 `model_cpu_offload_and_qfloat8`.
- `model_full_load` 与 `model_cpu_offload` 都已被真实动态证据否定.

### 后续讨论入口
- 下次若继续优化单卡工作流, 建议先看:
  - `inference/versecrafter_inference.py`
  - `inference/single_image_multi_trajectory.py`
  - `ERRORFIX.md` 中本条记录对应的动态验证结果

## [2026-03-15 11:24:00 UTC] 主题: 当测试图与 demo 图相同, 仅靠“输出长得像”无法证明流程抄了 demo

### 发现来源
- 用户质疑 `demo_data/my/shared/fitted_3D_gaussian` 看起来像 demo 输出, 怀疑脚本直接拷贝了 demo 目录.

### 核心问题
- 视觉相似不能直接当作“复制证据”.
- 如果输入图本身相同, 重新估计出来的深度、mask、Gaussian 参数天然就会非常接近.

### 为什么重要
- 如果不先核对输入源, 很容易把“同输入导致的同输出”误判为“代码直接偷用了旧产物”.
- 这类误判会把排查方向从真实流程逻辑带偏到“有没有 copy 文件”.

### 当前结论
- `demo_data/my/0001.png` 与 demo 的 `0001.png` 哈希完全一致.
- 当前 my 目录的 `custom_3D_gaussian_trajectory.json` 仍然是静态重复轨迹, 并不是 demo 的动态轨迹拷贝.
- 真正需要改的不是“防 copy”, 而是增加 `camera_only` 模式来匹配用户需求.

### 后续讨论入口
- 若以后再遇到“看起来像 demo”的质疑, 先做:
  - 输入文件哈希比对
  - 中间 JSON 的逐帧差异比对
  - 再判断是不是流程复用还是结果复制

## [2026-03-15 12:46:40 UTC] 主题: 40 步“时间静止”版单条轨迹已经进入接近小时级成本, 没有 subset / model reuse 会放大验证代价

### 发现来源
- 在 `demo_data/my/0` 上做“更强冻结 prompt + 40 steps”的 Step 6 最小实验.

### 核心问题
- 当前单条 `81` 帧、`720p`、`model_cpu_offload_and_qfloat8`、`40 steps` 的 VerseCrafter 生成, 实测耗时约 `42 分 53 秒`.
- 现有批处理脚本没有“只重跑某一条轨迹”的正式参数, 也没有 Step 6 模型复用.

### 为什么重要
- 一旦用户想做“先试 1 条, 再决定要不要全量 6 条”, 现在只能:
  - 手动改目录
  - 或手动调用 `versecrafter_inference.py`
- 如果不记录这个事实, 后续很容易在高成本条件下误触发整批重跑.

### 未来风险
- 6 条轨迹全量切到 40 steps 时, 纯 Step 6 总时长会非常可观.
- 没有 subset / model reuse 时, 每次验证 prompt 调整都要付出高昂等待成本.

### 当前结论
- “先做 1 条最小实验”不是保守, 而是当前工作流下唯一合理的验证策略.
- 后续若继续围绕“时间静止”迭代, 优先级最高的工程增强不是再加轨迹类型, 而是:
  - subset 选择
  - Step 6 模型复用

### 后续讨论入口
- 继续演进时优先看:
  - `inference/single_image_multi_trajectory.py`
  - `LATER_PLANS.md` 中 Step 6 模型复用优化
  - 本轮生成的 `demo_data/my/0/timefreeze_compare_old_vs_new.mp4`

## [2026-03-15 13:52:30 UTC] 主题: Hugging Face Xet 的 tqdm 进度条不能直接当“是否卡死”的证据

### 发现来源
- 在新场景 `demo_data/my2/10000.png` 的 Step 1 中, `moge-v2_infer.py` 默认拉取 `Ruicheng/moge-2-vitl-normal`.

### 核心问题
- 终端里 `model.pt` 的 tqdm 进度条长时间停在 `0.00/1.32G`, 很容易让人误判为完全卡死.
- 但同一时刻查看 `~/.cache/huggingface/xet/logs/...` 会发现底层字节数仍在增长.

### 为什么重要
- 如果只看 tqdm, 很容易做出错误决策:
  - 误判网络彻底坏掉
  - 或在其实还能继续的情况下盲目重试
- 这类误判会把排查方向从“下载太慢”带偏到“代码逻辑有 bug”.

### 当前结论
- 对这类 Hugging Face Xet 下载:
  - tqdm 只能当表面现象
  - 真正判断是否卡死, 要看:
    - `xet` 日志里的 `observed bytes sent so far`
    - 或本地缓存文件的实际增长
- 如果机器里已有兼容的本地缓存快照, 直接传本地 `model.pt` 往往比继续等远程下载更实际.

### 后续讨论入口
- 以后再遇到类似“0.00/1.32G”卡住时, 先看:
  - `ERRORFIX.md` 中 MoGe 本地快照记录
  - `notes.md` 本轮新场景验证记录

## [2026-03-15 14:20:00 UTC] 主题: 默认模型名和真实下游契约不一致, 会持续制造“到底需不需要 normal”的认知成本

### 发现来源
- 本轮核对 `moge-2-vitl-normal` 是否真的被 VerseCrafter 使用时, 同时追了默认配置、Step 1 输出以及后续消费链.

### 核心问题
- 当前仓库默认 v2 模型是 `moge-2-vitl-normal`, 语义上暗示“normal 是重要输出”.
- 但主工作流实际只把 `depth_intrinsics.npz` 里的 `depth` 和 `intrinsic` 传给后续步骤.
- 这会让后来者很容易把“默认模型名”误读成“当前主链路真的依赖 normal”.

### 为什么重要
- 一旦默认名和真实契约不一致:
  - 调试下载问题时会怀疑错方向
  - 替换成本评估会反复重做
  - 后续如果真要接 normal 下游, 也更难看清“这是新增能力”还是“恢复既有能力”

### 当前结论
- 对当前主链路, `moge-2-vitl` 作为临时 `--moge_pretrained` 替代是成立的.
- 但仓库默认策略仍值得后续显式化, 不能长期依赖口头约定.

### 后续讨论入口
- 若后面决定收敛默认值策略, 建议先看:
  - `inference/moge-v2_infer.py`
  - `api_server.py`
  - `notes.md` 中本轮 MoGe 模型差异分析
