# 任务计划: `moge_pretrained` 权限路径与小规模验证

## [2026-03-25 11:42:39 UTC] [Session ID: moge_permission_20260325] [记录类型]: 建立排查与验证计划

### 目标
- 区分当前日志里的真正失败点与背景 warning.
- 把 `--moge_pretrained /root/.cache/...` 改成当前用户可访问的形式.
- 基于修正后的命令做一次小规模真实测试, 确认链路至少能越过当前报错点.

### 阶段
- [x] 阶段1: 阅读日志与调用点, 区分现象和候选根因
- [x] 阶段2: 确认模型路径来源与当前用户权限边界
- [x] 阶段3: 修正命令或代码中的危险路径/提示
- [x] 阶段4: 执行小规模测试并记录结论

### 关键问题
1. 当前失败究竟是 Blackwell + 旧 PyTorch 警告, 还是 `--moge_pretrained` 指向了无权限路径?
2. 最稳妥的修正应该是“改命令参数”, 还是“加代码前置校验/提示”?
3. 小规模测试应该缩到什么程度, 才既能验证链路, 又不浪费太多 GPU 时间?

### 当前判断
- 现象:
  - 日志最前面出现 `sm_120` 不受当前 PyTorch 官方支持的 warning.
  - 真实 traceback 停在 `Path(...).exists()` 对 `/root/.cache/.../model.pt` 的 `PermissionError`.
- 当前假设:
  - 主假设: 当前轮直接失败的根因是 `rais` 用户无法访问 `root` 私有缓存目录.
  - 备选解释: 即使修掉权限问题, 旧版 PyTorch 对 Blackwell 的兼容性仍可能成为下一步运行风险.

### 当前状态
- **目前在阶段2**: 正在核对路径来源、权限边界与最小测试方案.

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] [记录类型]: 修正与小规模验证完成

### 已验证结论
- 直接失败的根因已经确认:
  - 不是最前面的 `sm_120` warning 本身
  - 而是命令把 `--moge_pretrained` 写成了 `/root/.cache/.../model.pt`, 当前 `rais` 用户没有权限读取
- 但在修正这条路径之后, 小规模动态验证又确认了下一个更硬的阻塞:
  - 当前 `torch 2.3.1 + CUDA 12.1` 在这台 Blackwell `sm_120` 机器上连最基础的 CUDA 张量运算都会报:
    - `RuntimeError: CUDA error: no kernel image is available for execution on the device`

### 已完成动作
- 已给 `inference/moge-v2_infer.py` 增加本地 checkpoint 路径前置校验:
  - 提前识别 `/root/.cache/...` 这类无权限路径
  - 给出可执行提示, 不再落到深层 `Path.exists()` 的晦涩报错
- 已更新 `inference/single_image_multi_trajectory.py` 的 `--moge_pretrained` help 文案.
- 已更新 `cmd.md`, 把多个 `/root/.cache/.../model.pt` 示例改成更可移植的:
  - `--moge_pretrained Ruicheng/moge-2-vitl`
- 已完成小规模验证:
  - 语法验证: `py_compile`
  - GPU 最小探针: 基础 CUDA matmul 失败
  - 整链路小规模 `--dry_run`: 成功展开修正后的命令

### 当前状态
- **阶段4已完成**: 路径问题已修正并验证, 真实 GPU 运行当前被 PyTorch / Blackwell 兼容性阻塞.

## [2026-03-25 12:36:28 UTC] [Session ID: moge_permission_20260325] [记录类型]: 开始处理 PyTorch / Blackwell 兼容性

### 新目标
- 找到官方支持 Blackwell `sm_120` 的 PyTorch 版本与安装路径.
- 在当前 Pixi 环境中完成升级或替换.
- 用最小 CUDA 张量运算和 `moge-v2_infer.py` 小测试验证升级是否真正生效.

### 验证计划
- 先查官方文档 / 官方发布信息, 明确支持边界.
- 再检查当前 channels 能否解出可用版本, 尽量保持项目现有 Pixi / conda 工作流.
- 升级后先做最小 CUDA probe, 通过后再重试 `my7` 小规模真实运行.

### 当前状态
- **目前在新一轮阶段1**: 正在确认官方支持版本与本地可安装版本.

## [2026-03-25 20:45:40 UTC] [Session ID: moge_permission_20260325] [记录类型]: 继续等待 cu128 升级并准备复验

### 当前现象
- `pixi run python -m pip install ... --index-url https://download.pytorch.org/whl/cu128` 仍在后台运行.
- 重新读取当前环境时, 仍然导入到旧版:
  - `torch 2.3.1`
  - `CUDA 12.1`
  - 仍会打印 `sm_120` 不兼容 warning

### 当前假设
- 主假设: 安装尚未完成, 当前环境还没有切到新 wheel.
- 备选解释: 安装过程可能卡在某个大包下载或解包阶段, 最终也可能失败.

### 下一步
- 继续监控安装会话是否结束.
- 一旦安装完成, 立即做最小 CUDA 张量探针.
- 若探针通过, 再进入 `flash-attn` / 小规模真实推理验证.

### 当前状态
- **目前在新一轮阶段2**: 正在等待 `cu128` 安装完成, 并准备做动态复验.

## [2026-03-25 20:50:12 UTC] [Session ID: moge_permission_20260325] [记录类型]: 放弃继续硬等完整 pip 安装

### 现象
- 后台安装会话明确报 `Connection timed out while downloading`.
- 当前被卡住的包是 `pypi.nvidia.com` 上的 `nvidia-cuda-nvrtc-cu12-12.8.61`.
- 小样本测速显示这条链路仅约 `18 KB/s`.

### 判断
- 主假设: 当前完整安装路径的主要瓶颈是 `pypi.nvidia.com` 依赖链下载过慢.
- 备选解释: 即使继续等待, 后续其他 `nvidia-*` 包也大概率会重复这个问题.

### 新的验证计划
- 停掉当前后台安装, 避免继续浪费时间和流量.
- 建一个临时隔离环境, 只安装 `torch 2.7.1+cu128` 主 wheel(`--no-deps`), 配合系统 `/usr/local/cuda-12.8` 做最小 CUDA 可证伪实验.
- 如果隔离实验通过, 再把相同策略落到 Pixi 环境.
- 如果隔离实验失败, 再回头评估完整安装或其他包源.

### 当前状态
- **目前在新一轮阶段2**: 正准备切换到更小的可证伪实验.

## [2026-03-25 21:09:05 UTC] [Session ID: moge_permission_20260325] [记录类型]: 切换到现成本机 `cu128` 环境验证

### 已验证结论
- `torch 2.6.0+cu124` 在 Blackwell 上仍然失败.
- `torch 2.7.0+cu128` 与 `torch 2.10.0+cu128` 都已通过最小 CUDA matmul.
- 因而当前最可行的验证路径, 是借本机现成的 `cu128` 环境先把 VerseCrafter 小规模链路跑通.

### 已执行动作
- 已为 `video_to_world` 的 `cu128` 环境建立精确 overlay, 让它能导入 VerseCrafter 所需的:
  - `transformers`
  - `diffusers`
  - `accelerate`
  - `moge`
  - `utils3d`
  - 以及必要的兼容依赖
- 已用这套环境成功执行用户命令的 `dry_run`.

### 新的阻塞
- 真实运行时发现 Hugging Face 下载被当前 shell 的全局代理环境变量拖住.
- 去掉代理后, `Ruicheng/moge-2-vitl/model.pt` 已开始稳定直连下载.

### 当前状态
- **目前在新一轮阶段3**: 正在预下载 `moge-2-vitl` 权重, 完成后立刻重跑小规模真实验证.

## [2026-03-25 21:26:40 UTC] [Session ID: moge_permission_20260325] [记录类型]: 按用户选择优先落本地可读 `model.pt`

### 现象
- 现有续传方式能推进 `moge-2-vitl/model.pt`, 但会在若干十 MB 后再次挂住.
- 当前 `.incomplete` 已累计到约 `157 MB`, 说明并非权限或 repo id 错误.

### 决策
- 按用户选择的第 1 条路径执行:
  - 优先把一份当前用户可读的本地 `model.pt` 落到 `~/.cache` 下
  - 再用本地路径重跑小规模真实验证

### 下一步
- 先确认 `huggingface_hub` 官方有没有可控超时/续传入口.
- 如果官方入口仍不足以避免长时间挂死, 就落一个项目内的小脚本, 用短超时 + Range/续传把 `model.pt` 收完整.
- 下载完成后, 用本地路径替换 `--moge_pretrained` 重新执行 `my7` 小规模真实运行.

### 当前状态
- **目前在新一轮阶段3**: 正在实现“本地 `model.pt` 优先”方案.

## [2026-03-25 14:52:39 UTC] [Session ID: moge_permission_20260325] [记录类型]: 继续监控本地 `model.pt` 下载并准备接真实测试

### 当前现象
- 已有后台续传会话在推进:
  - `session_id=16853`
- 当前已知 partial 路径:
  - `/home/rais/.cache/huggingface/local-moge-2-vitl/model.pt.part`
- 当前主目标不再是继续分析代码, 而是确认下载是否完成, 然后立刻切到 `my7` 小规模真实运行.

### 本轮行动计划
- 先读取后台下载会话最新输出, 判断是否仍在前进.
- 同时检查 `.part` 文件大小与最终 `model.pt` 是否已经落盘.
- 如果下载完成, 立即用本地路径重跑:
  - `--moge_pretrained /home/rais/.cache/huggingface/local-moge-2-vitl/model.pt`
- 如果下载停住, 则继续复用现有专用脚本推进, 不回退到整文件官方下载.

### 当前状态
- **目前在新一轮阶段3**: 正在做下载进度复验, 一旦完成就进入真实测试.

## [2026-03-25 15:03:19 UTC] [Session ID: moge_permission_20260325] [记录类型]: 提前暴露 overlay 环境导入阻塞

### 当前现象
- `moge-2-vitl` 本地下载仍在推进, 当前 `.part` 已进入 `900 MB+`.
- 但在 `video_to_world + /tmp/versecrafter_py310_overlay` 环境里预导入 VerseCrafter 相关模块时, 提前报出:
  - `NameError: name 'EncodingFast' is not defined`
- 同时确认该环境:
  - `xformers` 可导入
  - `flash_attn` 不存在

### 当前假设
- 主假设:
  - 当前真正更靠前的阻塞不是 `flash_attn`, 而是某个 transformers / tokenizers / typing 兼容性问题, 让 VerseCrafter 模块在 import 阶段就失败.
- 备选解释:
  - 也可能是 overlay 组合时混入了不完全兼容的包版本, 导致注解或类型别名在运行期解析失败.

### 下一步
- 先拿到完整 traceback, 定位 `EncodingFast` 是在哪个模块里被求值.
- 判断这是“缺少符号的版本兼容问题”, 还是“overlay 拼装方式导致的混装问题”.
- 在下载继续进行的同时, 先把这个导入阻塞修掉或至少收敛到可执行修复方案.

### 当前状态
- **目前在新一轮阶段3**: 一边继续下载本地 `model.pt`, 一边并行排查真实运行前的 import 阻塞.

## [2026-03-25 15:23:24 UTC] [Session ID: moge_permission_20260325] [记录类型]: 转向“混合 Python 环境”执行渲染步骤

### 当前现象
- `video_to_world` 的 `cu128` 环境适合跑:
  - MoGe
  - VerseCrafter generation
- 但它没有真正安装的 `pytorch3d`.
- 当前仓库根目录下的 `./pytorch3d/` 只是源码 checkout, 会制造“顶层 import 看起来存在”的假象.
- VerseCrafter 自己的 `py311` 环境则能正常启动:
  - `inference/rendering_4D_control_maps.py --help`

### 新决策
- 不再继续为 `video_to_world` 环境临时补 `pytorch3d`.
- 改为让工作流支持:
  - 默认仍使用统一 `python_bin`
  - 但必要时可单独指定 `render_python_bin` 与 `render_device`
- 这样本轮小规模真实测试就可以采用:
  - MoGe / generation: `video_to_world` 的 `cu128` Python
  - render: VerseCrafter 自带 `py311` Python + `cpu`

### 当前状态
- **目前在新一轮阶段3**: 正在把混合执行入口落到批处理脚本, 为最终真实测试铺路.

## [2026-03-25 16:00:02 UTC] [Session ID: moge_permission_20260325] [记录类型]: 真实测试卡在 CPU 背景点云渲染

### 当前现象
- 真实测试会话 `27673` 已经越过 `MoGe` 阶段.
- `shared/estimated_depth/depth_intrinsics.npz` 已生成.
- `shared/fitted_3D_gaussian/gaussian_params.json` 明确是:
  - `num_objects = 0`
  - `gaussian_params = {}`
- 当前活跃子进程:
  - `inference/rendering_4D_control_maps.py --device cpu`
  - 持续 `100%+ CPU`
  - `18` 分钟以上仍未产出 `rendering_4D_maps/*.mp4`

### 当前判断
- 现象:
  - `--moge_fp16` 已经成功让深度估计跑通.
  - 当前耗时点已经切换到 Step 5 的 CPU 背景点云渲染.
- 当前假设:
  - 主假设: 这轮 smoke test 的主要时间被 `230400` 个背景点在 `81` 帧轨迹上的 CPU 渲染吃掉.
  - 备选解释: 也不排除 PyTorch3D 的 CPU 路径在当前参数组合下存在额外低效实现.

### 下一步
- 为 Step 5 增加默认关闭的“背景点数量上限”参数, 只在 smoke test 时启用.
- 重新执行更快的小规模真实测试, 继续保留:
  - `--moge_fp16`
  - 单 preset
  - 低步数
  - 混合 Python 环境

### 当前状态
- **目前在新一轮阶段3**: 正在为 CPU 渲染阶段增加 smoke-test 提速参数.

## [2026-03-25 16:20:16 UTC] [Session ID: moge_permission_20260325] [记录类型]: 将 Step 5 render 分辨率与最终生成分辨率解耦

### 当前现象
- 即使把背景点从 `230400` 限到 `60000`, Step 5 的 CPU render 仍然在 `10+` 分钟量级.
- `versecrafter_inference.py` 加载控制视频时, 会通过 `get_video_to_video_latent(..., sample_size=sample_size)` 再次按最终 `sample_size` 做 `cv2.resize`.

### 当前判断
- 主假设:
  - smoke test 的真正提速杠杆应该是“单独降低 Step 5 render 分辨率”, 而不是只继续砍背景点数量.
- 备选解释:
  - 若分辨率下调后仍然没有明显改善, 就说明瓶颈更偏向 PyTorch3D CPU 内部实现, 需要再换验证策略.

### 下一步
- 为批处理脚本新增单独的 Step 5 render 尺寸参数, 默认仍跟随 `sample_size`.
- 重新执行更激进的 smoke test:
  - 最终生成仍保持 `360,640`
  - 但 render 先降到更小尺寸
  - 继续叠加背景点上限

### 当前状态
- **目前在新一轮阶段3**: 正在把 Step 5 render 尺寸从最终 `sample_size` 中解耦.

## [2026-03-25 16:30:11 UTC] [Session ID: moge_permission_20260325] [记录类型]: render 已跑通, Step 6 暴露 TeaCache 边界错误

### 当前现象
- 新 smoke test 组合:
  - `render_sample_size=180,320`
  - `render_background_point_limit=20000`
- 已经成功跑完整个 render 阶段:
  - `background_RGB.mp4`
  - `background_depth.mp4`
  - `merged_mask.mp4`
  - 以及其他控制视频都已落盘
- 但 Step 6 最终生成失败, traceback 明确停在:
  - `pipeline.transformer.enable_teacache(...)`
  - `ValueError: num_skip_start_steps ... must be <= num_steps=4 but is 5`

### 当前判断
- 主假设:
  - `inference/versecrafter_inference.py` 把 `TeaCache` 的默认 `num_skip_start_steps` 固定为 `5`.
  - 当小规模测试把 `--num_inference_steps` 降到 `4` 时, 这里会越界.
- 备选解释:
  - 如果修掉这个边界后仍失败, 才继续看 `TeaCache` 或推理配置的下一层兼容问题.

### 下一步
- 修正 `TeaCache` 初始化前的步数边界, 让它在 `num_inference_steps < 5` 时自动收缩到合法范围.
- 复用已经完成的 render 输出直接重跑, 不重复执行前面的慢步骤.

### 当前状态
- **目前在新一轮阶段4**: 正在修复 Step 6 的 `TeaCache` 小步数边界问题.

## [2026-03-25 15:54:17 UTC] [Session ID: moge_permission_20260325] [记录类型]: 真实测试已进入 CPU render, 当前最慢点明确

### 已验证结论
- `moge-2-vitl` 本地 `model.pt` 已完整落盘.
- `demo_data/my7/d.png` 在当前机器上缺失, 不能直接按用户原路径复跑.
- 改用仓库现成 `demo_data/my5/b.png` 后:
  - MoGe 在 `fp32` 下会因 Blackwell + xformers 限制失败
  - MoGe 在 `--fp16` 下可稳定完成 depth estimation
- 混合执行方案已生效:
  - MoGe / generation: `video_to_world` `cu128`
  - render: VerseCrafter `py311` + `cpu`

### 当前现象
- 当前真实测试还在进行.
- 共享深度与轨迹资产已经完成.
- `rendering_4D_control_maps.py` 正在 CPU 上持续高占用运行, 但尚未进入 generation.

### 当前判断
- 主假设:
  - 当前最慢点是 `camera_only` 路径下的 CPU render, 不是新的报错或死锁.
- 备选解释:
  - 也不排除 render 后半段还会暴露新的性能或 IO 问题, 需要继续等待动态证据.

### 当前状态
- **目前在新一轮阶段4**: 正在等待当前真实测试从 render 阶段继续推进, 并准备记录最终结果或新的最小阻塞点.
