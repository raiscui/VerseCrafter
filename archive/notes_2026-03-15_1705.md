# 研究笔记

## [2026-03-14 16:45:00 UTC] 仓库贡献指南调研

- 待补充: 记录目录结构、命令入口、测试现状与提交风格.

## [2026-03-14 16:49:00 UTC] 调研结论补充

### 现象
- 根目录主要文件包括 `api_server.py`、`model_server.py`、`inference.sh`、`requirements.txt`、`README.md`、`README_BLENDER.md`.
- 主要目录为 `versecrafter/`、`inference/`、`blender_addon/`、`config/`、`demo_data/`、`asset/`、`third_party/`.
- `third_party/` 通过 `.gitmodules` 引入 `Grounded-SAM-2` 和 `VideoX-Fun` 两个子模块.
- 根仓库没有 `tests/`、`pytest.ini`、`pyproject.toml`、`ruff.toml` 等测试或格式化配置.
- Git 历史提交信息以简短祈使句为主, 例如 `update readme`、`add third_party`、`update inference code`.

### 假设
- 当前仓库的主要开发与验证方式, 是通过 README 中的推理脚本和 Blender 插件工作流进行手动验证, 而不是依赖现成 CI 测试套件.
- 代码风格应以现有 Python 文件为准: 4 空格缩进、`snake_case` 函数、`PascalCase` 类名, Blender 相关符号使用 `VERSECRAFTER_OT_*`、`VERSECRAFTER_PT_*` 这样的约定.

### 验证
- 静态证据:
  - `README.md` 明确给出 `python api_server.py --port 8188 --num_gpus 8`、`bash inference.sh`、`zip -r blender_addon.zip blender_addon/` 等命令.
  - `blender_addon/__init__.py` 中存在 `VERSECRAFTER_OT_*` 和 `VERSECRAFTER_PT_*` 的命名模式.
  - `versecrafter/pipeline/pipeline_wan_versecrafter.py` 和 `api_server.py` 均采用 Python 习惯命名和 4 空格缩进.
- 动态证据:
  - 通过 `find`、`rg --files` 和 `git log --oneline -n 12` 已确认根目录缺少统一测试配置, 且历史提交风格偏简短描述.

### 结论
- `AGENTS.md` 应强调:
  - 以 Python 推理管线、Blender 插件和 Git 子模块为核心.
  - 构建与验证命令优先引用 README 现有命令.
  - 测试部分要明确说明“当前以手动 smoke test 为主”, 同时给新增逻辑补 `pytest` 测试作为建议.

## [2026-03-14 17:03:00 UTC] pixi 迁移调研

### 现象
- 当前 README 安装流程使用 `conda create`、`conda install pytorch... pytorch-cuda=12.1` 和多段 `pip install`.
- 根目录没有 `pixi.toml`、`pyproject.toml` 或任何现成的 pixi 清单.
- 本机已安装 `pixi 0.65.0`.
- 项目依赖分成四类:
  - 基础 Python 依赖来自根 `requirements.txt`.
  - `MoGe` 通过 Git URL 安装.
  - `Grounded-SAM-2` 与 `grounding_dino` 通过本地 editable 安装, 并伴随 C++/CUDA 扩展编译.
  - `flash-attn`、`pytorch3d` 需要特殊安装方式, 原 README 使用 `--no-build-isolation`.

### 假设
- `pixi` 可以稳定管理 Python 版本、CUDA/PyTorch 和大多数 PyPI 依赖.
- 对于 `flash-attn`、`pytorch3d` 这类需要额外构建参数或源码安装的依赖, 更稳妥的方式是通过 `pixi` 任务统一触发 `pip install`, 而不是强塞进静态依赖表里.

### 验证计划
- 用官方文档确认以下能力:
  1. `pixi.toml` 是否支持 `pypi-dependencies`.
  2. 是否支持 Git 依赖与本地 `path + editable = true`.
  3. 是否支持 `pixi run` / `pixi shell` 作为 README 的主入口.
- 用仓库源码确认 `VideoX-Fun` 是否需要额外安装, 还是仅通过 `sys.path` 引入.

### 已验证事实
- Context7 官方文档确认:
  - `pixi.toml` 支持 `[pypi-dependencies]`.
  - 支持 `git = "..."` 形式的 Git 依赖.
  - 支持 `{ path = "...", editable = true }` 形式的本地 editable 依赖.
  - 支持 `pixi install`、`pixi shell`、`pixi run <task>`.
- 静态代码确认:
  - `api_server.py`、`model_server.py`、`versecrafter/pipeline/pipeline_wan_versecrafter.py` 都是通过 `sys.path` 引入 `third_party/VideoX-Fun`, 因此不必额外 `pip install -e third_party/VideoX-Fun`.
  - `inference/grounded_sam2_infer.py` 通过 `sys.path` 引入 `third_party/Grounded-SAM-2`, 但其 README 仍要求安装本地包, 说明安装主要为了扩展和依赖完整性.

### 结论
- 候选方案1: 仅修改 README, 继续用 `pip install -r requirements.txt` + 手写额外 `pip` 命令.
  - 优点: 改动小.
  - 风险: `pixi` 只成了壳, 没有真正管理环境.
- 候选方案2: 新增 `pixi.toml`, 让基础依赖、Git 依赖、本地 editable 依赖都进入 pixi 清单, 把 `flash-attn` / `pytorch3d` 收敛到 pixi 任务.
  - 优点: README 可执行, 项目环境定义更集中.
  - 当前判断: 这是更正确的落地方式.

## [2026-03-14 17:18:00 UTC] 本轮落地后的验证结论

### 现象
- 新增了根目录 `pixi.toml`.
- README 的 Conda 安装块已替换为 `pixi install -> pixi run bootstrap -> pixi shell`.
- `.gitignore` 已新增 `.pixi/` 和 `pytorch3d/`.

### 假设
- `pixi.toml` 当前已经足够表达基础环境, `bootstrap` 负责补齐特殊构建依赖.
- `pixi lock --dry-run` 的失败更像是 pixi 对 PyPI 求解阶段的执行限制, 而不是 manifest 结构错误.

### 验证
- 静态证据:
  - `pixi.toml` 中已声明工作区 channels、platform、PyTorch/CUDA 版本、PyPI 依赖和 `bootstrap` 任务.
  - README 已不再引用 `conda create` / `conda install` / `pip install --upgrade huggingface_hub`.
- 动态证据:
  - `pixi task list --manifest-path pixi.toml` 成功列出 `bootstrap, install-flash-attn, install-grounded-sam2, install-grounding-dino, install-moge, install-pytorch3d`.
  - `pixi workspace platform list --manifest-path pixi.toml` 成功返回 `linux-64`.
  - `pixi workspace channel list --manifest-path pixi.toml` 成功返回 `pytorch`, `nvidia`, `conda-forge`.
  - `pixi lock --manifest-path pixi.toml --dry-run` 失败原因是 `--dry-run` 禁止为 PyPI 求解初始化 conda 环境.

### 结论
- 当前主结论: README 与仓库状态已经对齐到 `pixi` 工作流.
- 仍未执行的验证: 完整 `pixi install` 与 `pixi run bootstrap`.
  - 原因: 该步骤会实际下载并安装大型 CUDA / PyTorch 环境与源码扩展, 超出本轮轻量文档改造验证范围.

## [2026-03-14 17:27:00 UTC] Wan2.1 切换到 ModelScope 下载源

### 现象
- 用户明确要求 `Wan2.1-T2V-14B` 使用 `https://modelscope.cn/models/Wan-AI/Wan2.1-T2V-14B`.
- README 原先仍使用 `hf download --local-dir model/Wan2.1-T2V-14B Wan-AI/Wan2.1-T2V-14B`.

### 验证
- 官方 ModelScope CLI 文档显示下载语法为:
  - `modelscope download --model <model_id> --local_dir <dir>`
- 仓库环境清单 `pixi.toml` 原先未包含 `modelscope`.

### 结论
- README 应改为 `modelscope download --model Wan-AI/Wan2.1-T2V-14B --local_dir model/Wan2.1-T2V-14B`.
- 为保持文档与环境一致, `pixi.toml` 同步补入 `modelscope`.

## [2026-03-15 03:52:00 UTC] pixi install-pytorch3d 解析错误排查

### 现象
- 用户执行 `pixi run install-pytorch3d` 时, Pixi 报错:
  - `failed to parse shell script`
  - `Unsupported reserved word`
  - 报错位置指向 `if [ ! -d pytorch3d ]; then`
- 当前仓库的 `pixi.toml` 中, `install-pytorch3d` 任务确实写成:
  - 先 `if [ ! -d pytorch3d ]; then git clone ... fi`
  - 再执行 `python -m pip install --no-build-isolation ./pytorch3d`

### 假设
- 主假设: 问题不在 TOML, 而在 Pixi 默认任务执行器 `deno_task_shell` 对 shell 语法支持有限, 不支持 Bash 的 `if ... then ... fi`.
- 备选解释: 也可能是多行任务块的换行拼接方式有问题, 不是 `if` 本身.
- 推翻主假设的证据:
  - 如果最小复现里去掉 `if` 后仍出现同类 `Unsupported reserved word`, 那就说明问题可能在多行块或其他 token.

### 已有静态证据
- `pixi.toml` 中 `install-pytorch3d` 任务使用了 Bash 保留字 `if`.
- Pixi 官方文档说明:
  - 任务默认由 `deno_task_shell` 执行.
  - 这是一个“有限的 bourne-shell 实现”.
- Exa 检索到的 Pixi 相关 issue / PR 显示:
  - `deno_task_shell` 存在条件语句和参数展开能力边界.
  - 自定义 `interpreter = "bash"` 是后来扩展方向, 不能默认假设所有现有环境都支持.

### 当前判断
- 候选修复方向1: 直接改用 `interpreter = "bash"` 保留原写法.
  - 优点: 表达最直观.
  - 风险: 依赖 Pixi 版本支持该字段, 兼容性不够稳.
- 候选修复方向2: 改写为 Pixi 默认 shell 可接受的单行命令, 避免 `if`.
  - 优点: 与当前清单风格一致, 更稳.
  - 当前更倾向这个方向.

### 额外动态证据
- 在当前仓库直接执行:
  - `pixi run --manifest-path pixi.toml install-pytorch3d`
  - 稳定复现用户提供的报错, 且在真正 clone 之前就失败.
- 最小复现实验:
  - `repro = "test -d foo || echo missing"` 可成功执行, 输出 `missing`.
  - `repro = """mkdir foo || test -d foo\n&& pwd\n"""` 在目录不存在和目录已存在两种情况下都可成功执行.
  - `repro = """mkdir foo || test -d foo\necho done\n"""` 会再次解析失败, 说明普通换行不会自动承接下一条命令, 必须显式通过布尔操作符组织.

### 已验证结论
- 结论1: 根因不是 `pixi.toml` TOML 结构错误, 而是 `install-pytorch3d` 的任务体使用了 Pixi 默认 `deno_task_shell` 不支持的 Bash `if ... then ... fi`.
- 结论2: Pixi 默认任务里, 适合本仓库的稳定修复方式是:
  - 用 `git clone ... || test -d pytorch3d` 代替 `if [ ! -d pytorch3d ]; then git clone ... fi`
  - 再用单独一行的 `&&` 承接安装命令
- 结论3: 这种写法保留了原有语义:
  - 目录不存在时执行 clone
  - 目录已存在时跳过 clone 并继续安装
  - 若 clone 因网络等其他原因失败且目录也不存在, 则任务仍会失败, 不会被静默吞掉

### 修复后验证
- `pixi run --manifest-path pixi.toml --dry-run install-pytorch3d` 成功输出:
  - `git clone https://github.com/facebookresearch/pytorch3d.git pytorch3d || test -d pytorch3d`
  - `&& python -m pip install --no-build-isolation ./pytorch3d`
- `pixi task list --manifest-path pixi.toml` 成功列出 `install-pytorch3d`.

## [2026-03-15 07:41:16 UTC] 仅相机运动工作流核对

### 已观察到的事实
- `demo_data/LXKcD2zSPMc_0351466_0353266_0001469_0001550` 根目录包含预处理输入与中间结果:
  - `0001.png`
  - `estimated_depth/*`
  - `object_mask/*`
  - `fitted_3D_gaussian/*`
- `camera_object_0/` 目录包含轨迹和视频相关产物:
  - `custom_camera_trajectory.npz`
  - `custom_3D_gaussian_trajectory.json`
  - `record.mov`
  - `generated_video_0.mp4`

### 当前假设
- Blender 的核心职责是“加载预处理结果 -> 交互编辑轨迹 -> 导出轨迹文件”.
- `record.mov` 更像 Blender 里的操作/预览录屏产物.
- `generated_video_0.mp4` 更像 Step 6 的最终模型生成结果.
- 还需要继续用 README 和脚本验证上述假设.

## [2026-03-15 07:41:16 UTC] README 与脚本核对后的结论补充

### 静态证据
- `README.md` Step 4 明确写明 Blender 阶段的输出是 `custom_camera_trajectory.npz` 和 `custom_3D_gaussian_trajectory.json`.
- `README.md` Step 5 明确要求同时输入:
  - `--trajectory_npz`
  - `--ellipsoid_json`
- `inference/rendering_4D_control_maps.py` 的参数定义中, `--trajectory_npz` 与 `--ellipsoid_json` 都是 `required=True`.
- `inference/versecrafter_inference.py` 只吃 `rendering_maps_path`, 不直接吃 Blender 视频.
- `README_BLENDER.md` 的工作目录结构把 `generated_video_0.mp4` 标成最终输出视频, 没有把 `record.mov` 列成必需输入.

### 动态证据
- `camera_object_0/rendering_4D_maps/` 实际存在 6 个控制视频, 说明真正喂给 Step 6 的是控制图视频目录, 不是 Blender 录屏.
- `generated_video_0.mp4` 元数据:
  - 1280x720
  - 16 fps
  - 81 frames
  - 与 README Step 6 默认设置高度一致.
- `record.mov` 元数据:
  - 1540x1540
  - 约 56.35 fps
  - 216 frames
  - 明显不像 Step 6 的模型输出, 更像 Blender 视口录制或演示视频.

### 当前判断
- `record.mov` 是 Blender 阶段的演示/预览类产物这一点, 目前有较强证据支持, 但仓库里没有直接代码写出它, 因此表述时应标成“高可信推断”, 不写成代码级已确认事实.

## [2026-03-15 11:48:44 UTC] “时间静止”重跑前的最小验证设计

### 现象
- 用户在 `camera_only` 模式下观察到最终视频里人物和车辆仍有运动.
- 当前共享数据已经切到空前景版本:
  - `demo_data/my/shared/fitted_3D_gaussian/gaussian_params.json` 中 `num_objects = 0`
  - `demo_data/my/0/custom_3D_gaussian_trajectory.json` 中 `metadata.num_objects = 0`
- `single_image_multi_trajectory.py` 当前默认:
  - `--num_inference_steps = 30`
  - `--negative_prompt` 仍是通用低质负面词, 只有少量 `static`、`walking backwards` 等描述.

### 主假设
- `camera_only` 已经正确移除了显式前景运动链路.
- 但 VerseCrafter 在 Step 6 仍会基于视频先验自行补出人物/车流的细小运动.
- 因此, 当前问题更像“生成条件约束不足”, 不是“前景轨迹文件还在偷偷驱动物体”.

### 最强备选解释
- 备选解释1: Step 5 控制图里仍残留了会诱导运动的信号, 即使 `num_objects = 0` 也会让模型倾向输出动态人物.
- 备选解释2: 当前 seed / guidance / 采样步数组合过弱, 即使 prompt 已经强调静止, 模型仍然会漂.

### 会推翻主假设的证据
- 如果仅重跑 Step 6, 只修改 prompt / negative prompt / `num_inference_steps`, 人物运动依旧和之前几乎一致, 那说明问题不只是文本条件太弱.
- 如果换更强文本约束后, 人物运动明显收敛, 那就支持“问题主要在 Step 6 条件不足”的判断.

### 验证计划
- 先复用 `demo_data/my/0/rendering_4D_maps`.
- 只清理并重跑 `demo_data/my/0/generated_videos`.
- 使用更强的“时间静止” prompt:
  - 明确写出 `Every person, car, motorcycle, and object is perfectly motionless`
  - 明确写出 `Time is stopped`
  - 明确写出 `Only the camera moves through the scene`
- 使用更强的 negative prompt:
  - 显式压制 `walking`, `body motion`, `wheel rotation`, `cloth flutter`, `subject motion`, `pose change`
- 把 `--num_inference_steps` 调到 `40`.
- 其余保持不变:
  - `--camera_only` 的 Step 1-5 产物继续复用
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`
  - `--seed 2025`
  - `--guidance_scale 5.0`

### 当前结论
- 现在最有价值的动作, 不是继续怀疑“是不是复制了 demo”, 也不是重做 Step 1-5.
- 最小实验应该先盯住 Step 6, 看“更强冻结条件 + 40 steps”能否把人物运动明显压下去.

## [2026-03-15 12:46:40 UTC] 0 号轨迹“时间静止”实验的动态结果

### 验证命令
- 实际执行:
  - `pixi run python inference/versecrafter_inference.py --transformer_path model/VerseCrafter --save_path demo_data/my/0/generated_videos_timefreeze_test_40steps --rendering_maps_path demo_data/my/0/rendering_4D_maps --prompt "<更强 frozen-in-time prompt>" --negative_prompt "<更强 motion suppression negative>" --input_image_path demo_data/my/0001.png --num_inference_steps 40 --sample_size 720,1280 --ulysses_degree 1 --ring_degree 1 --guidance_scale 5.0 --seed 2025 --fps 16 --gpu_memory_mode model_cpu_offload_and_qfloat8`

### 动态证据
- 运行过程中观察到:
  - 权重初始化完成
  - 采样进度从 `0/40` 持续推进到 `40/40`
  - 未出现新的导入错误
  - 未出现 OOM
- 终端最终输出:
  - 生成 prompt 原文
  - `demo_data/my/0/generated_videos_timefreeze_test_40steps/generated_video_0.mp4`

### 输出校验
- `ffprobe` 验证新视频:
  - 编码: `h264`
  - 分辨率: `1280x720`
  - 帧率: `16 fps`
  - 帧数: `81`
  - 时长: `5.0625s`
- 文件大小对照:
  - 旧版 `demo_data/my/0/generated_videos/generated_video_0.mp4`: `2321468`
  - 新版 `demo_data/my/0/generated_videos_timefreeze_test_40steps/generated_video_0.mp4`: `2020749`

### 可视化辅助证据
- 已生成整帧接触图:
  - `demo_data/my/0/generated_videos/frames_contact_sheet.jpg`
  - `demo_data/my/0/generated_videos_timefreeze_test_40steps/frames_contact_sheet.jpg`
- 已生成局部裁剪接触图:
  - `demo_data/my/0/generated_videos/pedestrian_crop_sheet_v2.jpg`
  - `demo_data/my/0/generated_videos_timefreeze_test_40steps/pedestrian_crop_sheet_v2.jpg`
- 已生成并排对照视频:
  - `demo_data/my/0/timefreeze_compare_old_vs_new.mp4`

### 观察与边界
- 从接触图能看出新视频已成功生成, 且整体构图与镜头运动保持稳定.
- 但因为镜头本身始终在移动, 仅靠抽帧接触图, 不能充分证明“人物已经完全不动”.
- 因此目前最诚实的结论是:
  - “新的冻结条件已成功落地并产出样本”
  - “是否达到用户要的绝对时间静止, 仍应以播放 `timefreeze_compare_old_vs_new.mp4` 的主观观感为最终判断”

## [2026-03-15 12:54:30 UTC] 新场景验证前的设计补充

### 现象
- 用户要求:
  - 进一步增强“时间静止”提示词
  - 换用新场景 `demo_data/my2/10000.png`
- 当前脚本缺少“只跑指定轨迹”的正式入口.
- 现有 40 步单条样本实测约 `42 分 53 秒`, 若新场景直接全量 6 条, 时间成本会很高.

### 主假设
- 这轮更合适的落地方式是:
  1. 先给脚本补一个 `--preset_indices` 能力
  2. 再用新场景只跑 `0` 号轨迹做真实验证
- 这样既不会破坏现有 6 轨迹默认行为, 也能把 prompt 迭代成本压下来.

### 最强备选解释
- 备选解释: 不改脚本, 直接手写一套新场景的 Step 1 / Step 5 / Step 6 命令也能完成验证.
- 之所以不优先走这个方案, 是因为后面大概率还要继续调 prompt 或扩到 1-5, 没有 subset 入口会反复支付人工成本.

### 当前结论
- 给批处理脚本增加一个轻量的 subset 参数, 是这轮最划算的改良.
- 新场景验证输出应独立于 `demo_data/my2/` 原图目录, 以免输入图和生成目录混在一起.

## [2026-03-15 13:52:30 UTC] 新场景 `demo_data/my2/10000.png` 的时间静止验证结果

### 代码改动验证
- 新增 CLI 子集参数:
  - `--preset_indices 0 5`
- 测试结果:
  - `pixi run python -m pytest tests/test_single_image_multi_trajectory_smoke.py tests/test_single_image_multi_trajectory_lib.py`
  - 结果: `13 passed`
- dry-run 结果确认:
  - `selected_preset_indices: [0]`
  - 只展示 `0` 号轨迹, 不再展示 `1-5`

### 新场景运行中的现象
- 直接使用默认 `moge_version=v2` 时, Step 1 会去拉:
  - `Ruicheng/moge-2-vitl-normal`
- 终端进度条长时间停在 `0.00/1.32G`, 但进一步查看 `~/.cache/huggingface/xet/logs/...` 可见底层字节数在持续增长.
- 本地已存在完整缓存:
  - `Ruicheng/moge-2-vitl`
  - 路径: `/root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`

### 验证结论
- `--moge_pretrained` 需要传具体文件路径, 不能传目录.
- 正确命令中使用:
  - `--moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt`
- 这样可以直接绕过远程下载瓶颈, 并成功完成 Step 1.

### 新场景动态证据
- 实际执行:
  - `pixi run python inference/single_image_multi_trajectory.py ... --camera_only --preset_indices 0 --num_inference_steps 40 --moge_pretrained <local model.pt> ...`
- 动态结果:
  - Step 1 深度估计成功
  - Step 5 渲染时明确输出 `Loaded 0 mask files`
  - Step 5 明确输出 `No objects detected; generated empty Gaussian projection video`
  - Step 6 成功从 `0/40` 跑到 `40/40`
  - 最终视频落盘:
    - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`

### 输出校验
- `ffprobe` 结果:
  - 编码: `h264`
  - 分辨率: `1280x720`
  - 帧率: `16 fps`
  - 帧数: `81`
  - 时长: `5.0625s`
- `manifest.json` 结果:
  - `status = completed`
  - `selected_preset_indices = [0]`
  - `shared.status = completed`
  - `trajectory_0.status = completed`
  - `center_depth = 7.81640625`
  - `translation_reference_depth = 7.425585937499999`

### 可视化辅助证据
- 已生成新场景接触图:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/frames_contact_sheet.jpg`
- 从接触图看, 画面主体是室内展厅和静态展陈, 没有明显人物或车流这种高风险独立运动源.
- 当前更接近“镜头在动, 场景本体保持冻结”的目标.

## [2026-03-15 14:17:31 UTC] `moge-2-vitl-normal` 与 `moge-2-vitl` 的差异核对

### 现象
- 本项目的 `inference/moge-v2_infer.py` 默认把 `v2` 映射到:
  - `Ruicheng/moge-2-vitl-normal`
- 我在新场景验证时为了绕开慢下载, 临时改用了本机已缓存的:
  - `Ruicheng/moge-2-vitl`
- 用户质疑这个替代是否合理.

### 静态证据
- [moge-v2_infer.py](/workspace/VerseCrafter/inference/moge-v2_infer.py#L60) 到 [moge-v2_infer.py](/workspace/VerseCrafter/inference/moge-v2_infer.py#L66):
  - 默认 `v2 -> Ruicheng/moge-2-vitl-normal`
- [v2.py](/workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages/moge/model/v2.py#L30) 到 [v2.py](/workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages/moge/model/v2.py#L36):
  - `MoGeModel` 结构里 `normal_head` 是可选头
- [v2.py](/workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages/moge/model/v2.py#L165) 到 [v2.py](/workspace/VerseCrafter/.pixi/envs/default/lib/python3.11/site-packages/moge/model/v2.py#L190):
  - 模型只会在有 `normal_head` 时返回 `normal`
- [moge-v2_infer.py](/workspace/VerseCrafter/inference/moge-v2_infer.py#L129) 到 [moge-v2_infer.py](/workspace/VerseCrafter/inference/moge-v2_infer.py#L165):
  - 当前项目真正落盘给下游的是 `depth_intrinsics.npz`
  - `normal.png` 的写出代码其实被注释掉了
- [rendering_4D_control_maps.py](/workspace/VerseCrafter/inference/rendering_4D_control_maps.py#L958) 到 [rendering_4D_control_maps.py](/workspace/VerseCrafter/inference/rendering_4D_control_maps.py#L961):
  - Step 5 只从 NPZ 里读取 `depth` 和 `intrinsic`

### 官方资料证据
- 官方 MoGe README 的预训练模型表写明:
  - `Ruicheng/moge-2-vitl`: `Metric scale = yes`, `Normal = no`
  - `Ruicheng/moge-2-vitl-normal`: `Metric scale = yes`, `Normal = yes`
- 同一份官方 README 还明确说明:
  - `moge-2-vitl-normal` 提供完整能力
  - 与 `moge-2-vitl` 性能几乎同级, 但额外多了 normal estimation

### 已验证结论
- 结论1:
  - 这个项目当前“默认想用”的确实是 `moge-2-vitl-normal`, 不是我瞎猜的.
- 结论2:
  - `moge-2-vitl` 和 `moge-2-vitl-normal` 不是同一个模型, 不能表述成“完全等价”.
- 结论3:
  - 但在 VerseCrafter 当前这条链路里, 下游实际只消费 `depth` 和 `intrinsic`, 没有消费 `normal`.
  - 因此把 `moge-2-vitl` 作为“临时绕开下载阻塞的 fallback”是有工程依据的.
- 结论4:
  - 这个 fallback 只能表述成“对当前下游契约来说大概率可用且有官方近似性能说明支持”, 不能表述成“和默认模型完全一样”.
- 如果用户只想控制相机, 依然需要导出相机轨迹; 在当前官方工作流里, 同时也需要保留/导出 `custom_3D_gaussian_trajectory.json`, 因为 Step 5 渲染脚本和 Blender 插件都要求它存在.

## [2026-03-15 07:45:30 UTC] object_mask 用途待核对

### 当前问题
- 用户追问 `object_mask` 是否还需要, 以及它的作用是什么.
- 需要从渲染脚本中确认 `mask_dir` 是否用于把前景对象从背景点云中扣掉, 避免背景和高斯前景重复渲染.

## [2026-03-15 07:49:20 UTC] 0 个对象场景支持性核对

### 当前问题
- 用户追问: 如果场景里没有人, 是否还需要 `object_mask`.
- 需要确认项目是否允许 `masks/` 为空、`gaussian_params.json` 为空对象集、以及渲染阶段是否会自动生成空的前景控制视频.

## [2026-03-15 07:49:20 UTC] 0 个对象场景核对结果

### 现象
- `api_server.py` 的预处理流程里, 如果分割结果 `len(detections['masks']) == 0`, 会直接把任务标记为失败: `No objects detected`.
- `inference/fit_3D_gaussian.py` 在 `masks_dir` 里没有任何 `mask_*.png` 时, 会记录 `No mask files found` 并返回.
- `inference/rendering_4D_control_maps.py` 的 `build_background()` 可以接受空的 `mask_dir`; 这时 `combined_mask` 保持全 False, 整张图都会被视为背景.
- 同一个渲染脚本在没有高斯对象时, 会生成空的 `3D_gaussian_RGB.mp4`, 并记录 `No objects detected; generated empty Gaussian projection video`.
- 但 `rendering_4D_control_maps.py` 仍要求 `--ellipsoid_json` 必填.
- `export_blender_custom_trajectories.py` 在 `0` 个 ellipsoid 时会 `Skipping ellipsoid export`, 也就是不会帮你写出空的 `custom_3D_gaussian_trajectory.json`.

### 结论
- 概念上: 纯背景 + 相机运动 是可表达的.
- 当前官方预处理/导出链路上: `0 objects` 不是一条被完整打通的平滑路径.
- 如果场景里没有人, 但有别的可控前景物体, 仍然需要 `object_mask/masks` 去描述那些物体.
- 如果场景里真的一个前景对象都没有:
  - 语义上不需要对象 mask 去做对象控制.
  - 但按当前原版流程, 预处理会失败, Blender 导出也不会自动给你空高斯轨迹 JSON.
  - 想跑通的话, 需要人为提供一个空的高斯轨迹 JSON, 或者改一下脚本让 `0 objects` 成为受支持分支.

## [2026-03-15 07:56:10 UTC] object_mask 生成方式

### 已确认事实
- `object_mask` 由分割步骤自动生成, 不是 Blender 手工画出来的.
- 入口包括:
  - `inference/grounded_sam2_infer.py`
  - `api_server.py` 的 preprocess Step 2
  - Blender addon 的 Step 1 预处理
- 产物包括:
  - `object_mask/masks/mask_XX_label.png`
  - `object_mask/*_mask_combined.png`
  - `object_mask/*_visualization.png`
  - `object_mask/*_annotations.txt`

## [2026-03-15 08:18:30 UTC] 单图 6 轨迹相机脚本探索结论

### 已确认事实
- `/workspace/lyra/cosmos_predict1/diffusion/inference/gen3c_single_image_sdg.py` 已内置 `demo_multi_trajectory(args)`.
- 这段内置逻辑枚举的正是用户要的 6 条轨迹:
  - left / right / up / zoom_out / zoom_in / clockwise
- 它也已经硬编码了 orbit 参数:
  - `radius_x_factor=0.15`
  - `radius_y_factor=0.10`
  - `num_circles=2`
- 它对 `movement_distance` 的实际计算是:
  - `random.uniform(range_min, range_max) * args.total_movement_distance_factor`
- `gen3c_single_image_sdg.py` 生成轨迹前会调用:
  - `_resolve_trajectory_center_depth(args, moge_depth, moge_mask)`
  - `_resolve_translation_reference_depth(args, center_depth)`
  - 再把 `translation_reference_depth` 传给 `generate_camera_trajectory(...)`
- `translation_reference_depth_scale` 只影响平移/环绕的位移幅度缩放, 不改变 look-at center depth.
- `Gen3cPersistentModel` 可以只加载一次模型与 MoGe, 然后多次 `inference_on_cameras(...)`, 很适合同一场景多条相机轨迹.

### 重要推断
- 当前内置 `demo_multi_trajectory(args)` 虽然轨迹 preset 正确, 但它是循环里反复调用 `demo(args)`.
- `demo(args)` 内部会重新做 seed、pipeline 初始化、MoGe 初始化和 cache 初始化.
- 因而现有 `--multi_trajectory` 更像“功能可用但效率不优”的基线方案.
- 另外, `movement_distance` 的采样发生在 `demo(args)` 之前, 而 `misc.set_random_seed(args.seed)` 在 `demo(args)` 内部, 说明当前内置多轨迹模式的距离采样可复现性并不理想.

### 对用户默认参数的影响解释
- `--auto_center_depth_quantile 0.2`
  - 让 `center_depth` 取中心裁剪区域有效深度的 20% 分位.
  - 相比默认 0.5, 会把 look-at center 往更近处拉.
- `--translation_reference_depth_scale 0.95`
  - 在 auto center 打开时, 会令 `translation_reference_depth = center_depth * 0.95`.
  - 这几乎让位移尺度接近 look-at depth 本身.
- `--total_movement_distance_factor 1.5`
  - 将 6 条 preset 的基础区间整体放大 1.5 倍.
  - 有效区间变为:
    - left/right: [0.3, 0.45]
    - up: [0.15, 0.3]
    - zoom_out/zoom_in: [0.45, 0.6]
    - clockwise: [0.6, 0.9]

## [2026-03-15 08:27:40 UTC] VerseCrafter 版多轨迹脚本的格式约束

### 已确认事实
- VerseCrafter 渲染阶段读取的相机轨迹文件 `custom_camera_trajectory.npz` 中, 键名是 `extrinsics`, 内容是 `[T,4,4]` 的 Blender 坐标系 camera-to-world 矩阵.
- `rendering_4D_control_maps.py::load_camera_trajectory()` 会先把该 Blender c2w 矩阵做轴翻转, 再求逆, 得到 OpenCV 风格 w2c 供渲染使用.
- 因此, 如果不经过 Blender 导出脚本而是程序直接产轨迹, 最稳的方式不是“伪造渲染端需要的 w2c”, 而是直接写出与 Blender 导出一致的 `c2w_blender` 轨迹文件.
- `rendering_4D_control_maps.py::load_ellipsoid_parameters()` 只接受多帧格式 JSON (`metadata` + `frames`).
- 相比之下, `fitted_3D_gaussian/gaussian_params.json` 是单帧格式 (`gaussian_params`).
- 所以 VerseCrafter 版自动脚本至少需要一个“单帧高斯 -> 静态多帧轨迹 JSON”的适配层.

## [2026-03-15 08:38:50 UTC] VerseCrafter 多轨迹脚本规格细化

### CLI 与现有脚本契约
- `versecrafter_inference.py` 当前直接暴露的关键参数:
  - `--transformer_path`
  - `--save_path`
  - `--rendering_maps_path`
  - `--prompt`
  - `--input_image_path`
  - `--num_inference_steps`
  - `--sample_size`
  - `--ulysses_degree`
  - `--ring_degree`
  - `--guidance_scale`
  - `--seed`
  - `--fps`
- `rendering_4D_control_maps.py` 当前关键参数:
  - `--png_path`
  - `--npz_path`
  - `--mask_dir`
  - `--trajectory_npz`
  - `--ellipsoid_json`
  - `--output_dir`
  - `--point_size`
  - `--fps`
  - `--render_batch_size`
  - `--target_height`
  - `--target_width`
- `grounded_sam2_infer.py` 当前关键参数:
  - `--image_path`
  - `--text_prompt`
  - `--output_dir`
  - `--box_threshold`
  - `--text_threshold`
  - `--keep_topk`
  - `--min_area_ratio`
  - `--max_area_ratio`
- `fit_3D_gaussian.py` 当前关键参数:
  - `--image_path`
  - `--npz_path`
  - `--masks_dir`
  - `--output_dir`
  - `--no_visualization`

### 控制图与生成输入契约
- `rendering_4D_control_maps.py` 固定会产出:
  - `background_RGB.mp4`
  - `background_depth.mp4`
  - `3D_gaussian_RGB.mp4`
  - `3D_gaussian_depth.mp4`
  - `merged_mask.mp4`
  - `background_and_3D_gaussian.mp4`
- `versecrafter_inference.py` 实际读取的是:
  - `background_RGB.mp4`
  - `background_depth.mp4`
  - `3D_gaussian_RGB.mp4`
  - `3D_gaussian_depth.mp4`
  - `merged_mask.mp4`
- 其中 `background_and_3D_gaussian.mp4` 目前只是渲染侧附加输出, 不是最终生成的必需输入.

### 设计上的关键决定
- VerseCrafter 版多轨迹脚本的外层入口应使用 `python`, 作为 orchestrator, 而不是直接让用户跑 `torchrun inference/versecrafter_inference.py`.
- 内部应顺序调用现有 Step 1-6 能力, 而不是第一版就重写成持久化推理服务.
- `movement_distance` 固定为轨迹区间中值再乘 `total_movement_distance_factor`, 不做随机采样.
- 根输出目录下保留 `0..5` 六个数字子目录, 并用根级 `manifest.json` 提供轨迹名映射.

### 建议的失败策略
- 共享预处理失败时, 直接终止整批任务.
- 单条轨迹渲染失败时:
  - 记录到 `manifest.json`
  - 不影响其他轨迹继续跑
- 单条轨迹生成失败时:
  - 保留其 `trajectory_npz` 与 `rendering_4D_maps`
  - 记录失败状态与命令参数, 方便仅重跑 Step 6
- 若 `num_objects == 0`, 第一版建议直接 fail-fast 并明确报错, 不在第一版支持“纯背景 0 对象”自动分支.

## [2026-03-15 08:53:30 UTC] proposal 起草决策

### 新 capability 命名
- `single-image-multi-trajectory-generation`
  - 含义: 为 VerseCrafter 新增一个单图输入、多条固定相机轨迹、共享预处理一次的自动化生成工作流.

### 不声明 modified capabilities 的原因
- 当前 VerseCrafter 仓库刚初始化 OpenSpec, `openspec/specs/` 为空.
- 本次需求更适合作为新增 capability 落地, 而不是伪造一个“修改现有 spec”的关系.

## [2026-03-15 09:26:40 UTC] OpenSpec design 前的最终静态证据

### OpenSpec artifact 指令约束
- `design.md` 需要覆盖:
  - `Context`
  - `Goals / Non-Goals`
  - `Decisions`
  - `Risks / Trade-offs`
  - 另外 instruction 还要求补上 `Migration Plan` 与 `Open Questions`
- `specs` 需要为 proposal 中每个 capability 建一个 `specs/<capability>/spec.md`
- `tasks.md` 必须使用 `- [ ] X.Y ...` 的复选框格式, 否则 apply 阶段不会识别

### 关键源码证据
- `inference/blender_script/export_blender_custom_trajectories.py`
  - Blender 导出相机轨迹时, 直接保存 `np.savez(..., extrinsics=extrinsics_array)`
  - 注释和代码都表明该矩阵是 Blender 坐标系下的 camera-to-world
- `inference/rendering_4D_control_maps.py::load_camera_trajectory`
  - 读取 `extrinsics`
  - 对 `:,:3,1:3` 做轴翻转后求逆, 转成 OpenCV world-to-camera
  - 说明自动脚本最稳的兼容方式, 是直接产出 Blender c2w 轨迹文件, 而不是绕过它去猜渲染端内部坐标
- `inference/fit_3D_gaussian.py`
  - 输出 `gaussian_params.json`
  - 顶层格式是 `gaussian_params` + `num_objects` + `obj_id_to_color_idx`
  - 这不是渲染端所需的多帧格式
- `inference/rendering_4D_control_maps.py::load_ellipsoid_parameters`
  - 明确要求 JSON 含 `metadata.num_frames`、`metadata.num_objects`、`metadata.obj_id_to_color_idx`
  - 以及 `frames[].frame_index`、`frames[].objects[].gaussian_3d.mean/covariance`
  - 因此第一版必须做“单帧高斯参数广播成静态多帧轨迹 JSON”的适配层
- `inference/versecrafter_inference.py`
  - 最终读取控制图目录中的 `background_RGB.mp4`、`background_depth.mp4`、`3D_gaussian_RGB.mp4`、`3D_gaussian_depth.mp4`
  - 同时读取 `merged_mask.mp4`
  - 生成结果以 `generated_video_<index>.mp4` 命名保存在 `save_path`

### design 里应明确的文件约定
- 新增 orchestrator 脚本位于 `inference/`
- 根输出目录下保留共享预处理产物, 以及 `0..5` 六个数字轨迹目录
- 根目录生成 `manifest.json`, 用于轨迹名映射、距离、中心深度和阶段状态记录

## [2026-03-15 09:38:40 UTC] Lyra 默认轨迹参数与 VerseCrafter 设计对齐结论

### Lyra 文档与源码确认
- `/workspace/lyra/docs/multi_trajectory_camera_implementation.md` 明确了 6 条 preset:
  - `left`
  - `right`
  - `up`
  - `zoom_out`
  - `zoom_in`
  - `clockwise`
- Lyra 的 preset 区间分别是:
  - left/right: `[0.2, 0.3]`
  - up: `[0.1, 0.2]`
  - zoom_out/zoom_in: `[0.3, 0.4]`
  - clockwise: `[0.4, 0.6]`
- Lyra 原始实现会随机采样 `movement_distance`, 但本次 VerseCrafter 设计改为“区间中值 × factor”确定性策略.

### Lyra 默认调参语义
- `estimate_trajectory_center_depth(...)` 默认使用:
  - `mode = center_crop`
  - `depth_quantile = 0.5`
  - `center_crop_ratio = 0.5`
  - `fallback_depth = 1.0`
- `_resolve_trajectory_center_depth(...)` 会在估计值上再乘 `auto_center_depth_scale`
- `_resolve_translation_reference_depth(...)` 会在 auto center 开启时优先使用:
  - `center_depth * translation_reference_depth_scale`
- 因此:
  - `center_depth` 决定 look-at center
  - `translation_reference_depth` 只决定位移尺度
  - `total_movement_distance_factor` 决定 preset 距离整体放大倍数

### 本次 OpenSpec 最终落定内容
- `design.md` 已明确采用 `inference/single_image_multi_trajectory.py` 作为 orchestrator.
- `specs/single-image-multi-trajectory-generation/spec.md` 已把共享预处理、固定 6 轨迹、默认深度参数、Blender 兼容轨迹文件、manifest 和 0-object fail-fast 写成 REQUIREMENTS.
- `tasks.md` 已拆成 6 组实现任务, 可直接进入 apply / implementation 阶段.

## [2026-03-15 10:18:10 UTC] OpenSpec apply 实现阶段结论

### 本轮新增文件
- `inference/single_image_multi_trajectory.py`
- `inference/single_image_multi_trajectory_lib.py`
- `tests/conftest.py`
- `tests/test_single_image_multi_trajectory_lib.py`
- `tests/test_single_image_multi_trajectory_smoke.py`

### 关键实现点
- 新增 `single_image_multi_trajectory_lib.py` 作为纯函数核心层, 负责:
  - 6 条 preset 表与确定性 `movement_distance`
  - 中心裁剪深度分位数估计
  - `translation_reference_depth = center_depth * scale`
  - OpenCV -> Blender 向量/协方差变换
  - Blender `camera-to-world` 轨迹矩阵生成
  - 单帧 `gaussian_params.json` -> 多帧 `custom_3D_gaussian_trajectory.json`
  - render 输出完整性和生成视频发现
- 新增 `single_image_multi_trajectory.py` 作为 orchestrator, 负责:
  - 共享 Step 1-3
  - 6 条轨迹目录 `0..5`
  - per-preset Step 5/6
  - `manifest.json`
  - resume / skip 逻辑
- 修改 `inference/versecrafter_inference.py`
  - 新增 `--negative_prompt`
  - 若未传则继续回退到原来的默认 negative prompt

### 一个重要设计修正
- 之前 design 里把 VerseCrafter / Blender 坐标下的 `up` 写成了 `z` 负方向.
- 结合 `COORD_TRANSFORM_CV2BLENDER` 与 Lyra 的 OpenCV `y` 负方向平移公式重新核对后, 正确映射应为:
  - `up` -> Blender `z` 正方向
- 该文档已同步修正, 单测也已经锁定这个方向关系.

### 验证结果
- `python3 -m py_compile inference/single_image_multi_trajectory_lib.py inference/single_image_multi_trajectory.py inference/versecrafter_inference.py`
  - 通过
- `python3 -m pytest tests/test_single_image_multi_trajectory_lib.py tests/test_single_image_multi_trajectory_smoke.py`
  - 7 项测试全部通过
- `python3 inference/single_image_multi_trajectory.py --help`
  - CLI 正常输出
- `openspec status --change add-versecrafter-single-image-multi-trajectory-script`
  - artifacts 全完成

### 当前未做的事
- 没有执行真实 Step 5 / Step 6 的重量级模型推理, 因为当前环境缺少 `diffusers` 等运行依赖.
- 但新 orchestrator 的 resume smoke test 已覆盖:
  - 目录契约
  - manifest 状态收敛
  - 6 条轨迹完成态跳过逻辑

## [2026-03-15 10:25:00 UTC] Step 5 视频写出修复验证准备

### 现象
- 上一轮真实测试已经跑通 Step 1-4, 并在 Step 5 写出 `rendering_4D_maps/*.mp4` 时失败.
- 报错栈指向 `torchvision.io.write_video` -> `av.video.frame.VideoFrame.pict_type.__set__` -> `TypeError: an integer is required`.

### 当前主假设
- 主假设: 当前环境中的 `torchvision` 与 `av` 版本组合在 `write_video` 路径上存在兼容问题, 与当前 orchestrator 无关.
- 备选解释: 也可能是传给 `write_video` 的 frame dtype / shape / contiguous 状态异常, 只是刚好在 `av` 内部暴露.

### 最小验证计划
1. 先阅读 `save_video_from_frames()` 当前实现, 确认改动是否完整移除了 `write_video`.
2. 用最小样本帧调用该函数, 验证 `cv2.VideoWriter` 是否能独立成功写出 mp4.
3. 若最小验证成功, 再恢复真实链路运行, 观察 Step 5 是否通过.
4. 若仍失败, 回到现象 -> 假设 -> 验证计划流程继续缩小范围.

## [2026-03-15 10:29:00 UTC] Step 5 写视频最小验证结果

### 已验证事实
- `save_video_from_frames()` 当前确实已经完全移除了 `torchvision.io.write_video`.
- `cv2.VideoWriter` + `mp4v` 在当前 pixi 环境可成功写出 mp4.
- 写出后的 mp4 可被 `torchvision.io.read_video` 正常读回, 说明至少容器和基础编码没有立即损坏.

### 当前结论
- 之前的失败现象至少不再能通过最小样本复现.
- 这还不能直接证明真实 Step 5 已完全修好, 但已经证明“新的写视频实现本身可工作”.
- 下一步需要真实跑 Step 5/6, 检查大分辨率、多段视频、后续推理消费链路是否正常.

## [2026-03-15 10:33:00 UTC] 真实测试中的新阻塞: Step 6 缺少 librosa

### 已观察到的事实
- `rendering_4D_control_maps.py` 在真实测试里已经成功执行完成.
- 失败发生在 `versecrafter_inference.py` 启动阶段, 不是 Step 5.
- 精确堆栈:
  - `from videox_fun.models import (AutoencoderKLWan, AutoTokenizer, WanT5EncoderModel)`
  - 进入 `third_party/VideoX-Fun/videox_fun/models/__init__.py`
  - 再导入 `fantasytalking_audio_encoder.py`
  - 最终 `import librosa` 失败.

### 当前主假设
- 主假设: 当前 pixi / requirements 环境缺少 `librosa`, 而 `VideoX-Fun` 的模型包在 `__init__` 中做了全量导入, 导致无音频推理路径也被音频依赖阻塞.
- 备选解释: 也可能仓库原本假定 `librosa` 由某个未声明的间接依赖提供, 只是 pixi 让这个隐式依赖暴露出来.

### 验证方向
1. 看 `requirements.txt`、`pixi.toml`、`third_party/VideoX-Fun` 自身依赖文件是否声明 `librosa`.
2. 看 `versecrafter_inference.py` 实际使用的模型类型, 判断是否真的需要 `FantasyTalkingAudioEncoder`.
3. 如果不需要, 优先消除无关强导入; 如果确实需要, 再补齐环境依赖.

## [2026-03-15 10:47:00 UTC] Step 6 导入阻塞修复后的验证结论

### 已验证事实
- `third_party/VideoX-Fun/videox_fun/models/__init__.py` 现在把音频编码器改成了可选依赖导入.
- 当前环境缺少 `librosa` 时:
  - 非音频类 `AutoencoderKLWan`、`WanT5EncoderModel`、`WanVerseCrafterPipeline` 仍可正常导入.
  - 音频类 `FantasyTalkingAudioEncoder`、`WanAudioEncoder` 会在实例化时抛出清晰的 `ModuleNotFoundError`.
- 当前 pixi 默认环境已补入 `pytest`, 并通过 8 条测试.

### 当前结论
- 这次修复解决的是“包初始化把可选音频依赖变成硬阻塞”的问题.
- 对 VerseCrafter 当前单图相机轨迹生成工作流来说, 这是比直接安装 `librosa` 更准确的修复.

## [2026-03-15 10:36:00 UTC] Step 6 显存模式实验结论

### 已观察到的事实
- `model_full_load` 在 A800 80GB 上会在采样初期 OOM.
- `model_cpu_offload` 把基线显存降下来了, 但没有解决瞬时大块显存申请失败.
- `model_cpu_offload_and_qfloat8` 是当前唯一已被动态验证通过的模式.

### 当前结论
- 这次真正起作用的不是“仅 offload”, 而是“offload + transformer qfloat8”.
- 因此批处理默认值应该直接指向这个已验证模式, 否则用户按默认参数仍会踩 OOM.

## [2026-03-15 11:22:00 UTC] 关于“是不是抄 demo 输出”的最终证据

### 现象
- 用户观察到 `demo_data/my/shared/fitted_3D_gaussian` 和 demo 很像, 怀疑是直接拷贝.

### 验证
- 动态 / 文件证据:
  - `sha256sum demo_data/my/0001.png demo_data/LXK.../0001.png`
  - 结果完全一致, 说明当前测试输入图就是 demo 那张图.
- 静态代码证据:
  - `single_image_multi_trajectory.py` 会调用 `inference/fit_3D_gaussian.py` 重新拟合 `shared/fitted_3D_gaussian/gaussian_params.json`.
  - `custom_3D_gaussian_trajectory.json` 由 `convert_static_gaussian_json_to_trajectory()` 从共享 `gaussian_params.json` 广播生成.
- 轨迹差异证据:
  - my 版本 `custom_3D_gaussian_trajectory.json` 同一对象 frame0 == frame1, 是静态轨迹.
  - demo 版本同一对象 frame0 != frame1, 是动态轨迹.

### 结论
- `shared/fitted_3D_gaussian` 看起来像 demo, 主要因为输入图本来就是同一张图, 不是因为脚本偷拷 demo 结果.
- `custom_3D_gaussian_trajectory.json` 当前也不是抄 demo 的动态前景轨迹, 而是我们自己从静态 Gaussian 参数广播出来的静态版本.
- 但用户“不需要前景运动”这一需求是成立的, 因此继续保留前景链路仍然不合适.

## [2026-03-15 11:22:00 UTC] camera-only 模式实现结论

### 实现内容
- 新增 `--camera_only`.
- 在该模式下:
  - 跳过 Grounded-SAM-2 segmentation
  - 跳过 `fit_3D_gaussian.py`
  - 创建空 mask 目录
  - 创建 `num_objects=0` 的 `gaussian_params.json`
  - 为每条轨迹生成空对象的 `custom_3D_gaussian_trajectory.json`

### 为什么这样更对
- 这样 Step 5 会把整张图都放进背景点云.
- 人车会作为背景的一部分 rigid 地跟着相机走, 而不是被当成独立前景对象处理.
- 这更贴近用户“只做相机运动”的真实需求.

## [2026-03-15 11:50:00 UTC] 时间静止需求的当前判断

### 现象
- 用户明确反馈: 即使在纯相机模式下, 人物仍然在动.

### 当前判断
- `camera_only` 已经保证没有显式前景轨迹和前景 Gaussian.
- 但 VerseCrafter 仍然可能基于 prompt 和视频先验, 自发补出人物微动.
- 因此下一步要验证的不是几何链路, 而是“更强时间静止语义 + 更高步数”是否足以压住这种自发运动.

## [2026-03-15 14:18:00 UTC] `moge-2-vitl-normal` vs `moge-2-vitl` 在当前仓库中的真实使用范围

### 现象
- 仓库里有两处默认把 MoGe v2 指向 `Ruicheng/moge-2-vitl-normal`:
  - `inference/moge-v2_infer.py`
  - `api_server.py`
- 但当前 VerseCrafter 主工作流 Step 1 之后真正传递给下游的核心产物是:
  - `depth_intrinsics.npz`
  - 内容只有 `depth` 和 `intrinsic`

### 静态证据
- `inference/moge-v2_infer.py`
  - 默认模型:
    - `v2 -> Ruicheng/moge-2-vitl-normal`
  - 推理后读取:
    - `points`, `depth`, `mask`, `intrinsics`
    - `normal` 仅在 `output` 存在时可选读取
  - `--maps` 路径实际只落盘:
    - `depth_vis.png`
    - `depth_gray.png`
    - `depth_intrinsics.npz`
  - `normal.png` 保存逻辑当前被注释掉了
- `inference/fit_3D_gaussian.py`
  - 只从 NPZ 读取:
    - `depth`
    - `intrinsic`
- `inference/rendering_4D_control_maps.py`
  - 也只从 NPZ 读取:
    - `depth`
    - `intrinsic`
- `inference/single_image_multi_trajectory.py`
  - Step 1 调 `moge-v2_infer.py --maps`
  - Step 3 / Step 5 都只消费 `depth_intrinsics.npz`
- `api_server.py`
  - 预处理 Step 1 同样只保存 `depth_intrinsics.npz` 和 `depth_vis.png`
  - 没有保存或传递 `normal`

### 上游官方证据
- Microsoft MoGe README 明确写了:
  - `Ruicheng/moge-2-vitl` = metric scale, 无 normal
  - `Ruicheng/moge-2-vitl-normal` = metric scale + normal
  - 备注: `moge-2-vitl-normal` 与 `moge-2-vitl` 性能几乎相同, 只是额外提供 normal map estimation
- 同一 README 还写了 `output["normal"]` 是 optional, 且只对 `MoGe-2-normal` 可用

### 动态证据
- 当前仓库已有两次真实运行 manifest 明确记录使用了本地:
  - `/root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/.../model.pt`
- 且相关产物实际存在:
  - `demo_data/my/shared/estimated_depth/depth_intrinsics.npz`
  - `demo_data/my/0/generated_videos/generated_video_0.mp4`
  - `demo_data/my2_timefreeze_10000/shared/estimated_depth/depth_intrinsics.npz`
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`

### 当前结论
- 对当前 VerseCrafter 主链路来说, normal 目前没有被真正消费.
- 因此把 `moge-2-vitl` 作为临时 `--moge_pretrained` 替代, 对现有多轨迹 / camera-only / API 预处理深度链路是妥当的.
- 但它不是“全仓库无差别等价替换”:
  - 如果以后恢复 `normal.png` 导出
  - 或更依赖 `--glb` / `--ply` 的法线质量
  - 或新增下游直接读取 `output["normal"]`
  那么 `moge-2-vitl-normal` 仍然更完整.

## [2026-03-15 14:49:00 UTC] 新场景 0 号轨迹 10 步对比样本补跑完成

### 现象
- 用户已经确认继续采用 `moge-2-vitl` 临时 fallback.
- 现有 40 步样本位于:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`
- 10 步样本按要求输出到独立目录:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0.mp4`

### 验证
- 静态证据:
  - 本次仅复用了已有:
    - `demo_data/my2_timefreeze_10000/0/rendering_4D_maps`
  - prompt / negative prompt 与 40 步版保持一致, 只把 `--num_inference_steps` 从 `40` 改成 `10`.
- 动态证据:
  - 10 步采样实际进度:
    - `1/10` 出现在 `01:39`
    - `5/10` 出现在 `07:08`
    - `10/10` 出现在 `14:00`
  - `ffprobe` 结果表明 10 步视频为:
    - `1280x720`
    - `16 fps`
    - `81 frames`
    - `5.0625s`
  - 与 40 步版元数据一致, 可以逐帧并排比较.
  - 另外已经生成:
    - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/frames_contact_sheet.jpg`
    - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0_vs_steps40_side_by_side.mp4`

### 视觉观察
- 10 步版整体镜头路径和“时间静止”约束都保持住了.
- 与 40 步版相比, 10 步版在远处人物轮廓、屏幕边缘和高光细节上略软.
- 40 步版的小结构更干净, 但 10 步版已经足够做快速验证和 prompt 方向判断.

### 结论
- 当前新场景已经同时具备:
  - 40 步正式样本
  - 10 步快速对比样本
  - 10/40 步并排对比视频
- 后续如果要决定全量 6 条是优先速度还是优先细节, 现在已经有直接证据可看.

## [2026-03-15 15:52:00 UTC] `my3` 新海诚风格展厅场景的 0 号轨迹 20 step 快速版

### 现象
- 新输入图位于:
  - `demo_data/my3/generated-image (1).png`
- 画面内容是蓝白色未来展厅, 带玻璃天窗、强反射地面、概念车展示位和远处科技展项.
- 用户要求:
  - 只相机控制
  - 0 号镜头
  - 20 step 快速版
  - 新海诚风格

### 执行命令
- 实际执行:
  - `pixi run python inference/single_image_multi_trajectory.py --input_image_path "demo_data/my3/generated-image (1).png" --output_root demo_data/my3_shinkai_quick20 --transformer_path model/VerseCrafter --prompt "in the style of Makoto Shinkai, a frozen-in-time futuristic AI exhibition hall ..." --negative_prompt "human motion, object motion, animated screen content, flickering LEDs, ..." --camera_only --preset_indices 0 --moge_version v2 --moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt --auto_center_depth_quantile 0.2 --translation_reference_depth_scale 0.95 --total_movement_distance_factor 1.5 --sample_size "720,1280" --num_inference_steps 20 --gpu_memory_mode model_cpu_offload_and_qfloat8 --ulysses_degree 1 --ring_degree 1 --guidance_scale 5.0 --seed 2025 --fps 16`

### 动态证据
- Step 1:
  - 本地 `moge-2-vitl` 权重直接加载成功
  - 成功输出 `depth_intrinsics.npz`
- Step 5:
  - 明确输出 `Loaded 0 mask files`
  - 明确输出 `No objects detected; generated empty Gaussian projection video`
- Step 6:
  - 采样从 `0/20` 推进到 `20/20`
  - 最终输出:
    - `demo_data/my3_shinkai_quick20/0/generated_videos/generated_video_0.mp4`

### 输出校验
- `manifest.json`:
  - `status = completed`
  - `selected_preset_indices = [0]`
  - `camera_only = True`
  - `trajectory0_status = completed`
- `ffprobe`:
  - 编码: `h264`
  - 分辨率: `1280x720`
  - 帧率: `16 fps`
  - 帧数: `81`
  - 时长: `5.0625s`
- 额外生成:
  - `demo_data/my3_shinkai_quick20/0/generated_videos/frames_contact_sheet.jpg`

### 视觉观察
- 20 step 快速版已经把“蓝白高光展厅 + 天窗光束 + 大面积反射地面”的主观风格保住了.
- 0 号镜头的横向移动关系清楚, 场景保持 rigid, 没有引入独立前景运动.
- 作为快速版, 它已经足够拿来判断 prompt 和镜头趋势; 若后面要更干净的高光与结构细节, 再升到 40 step 会更稳.
