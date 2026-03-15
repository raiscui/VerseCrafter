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
