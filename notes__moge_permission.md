# 排查笔记: `moge_pretrained` 权限路径与 Blackwell 小规模验证

## [2026-03-25 12:07:59 UTC] [Session ID: moge_permission_20260325] 笔记: 权限边界与动态验证

### 来源1: 当前用户与路径权限
- 动态结果:
  - `whoami -> rais`
  - `HOME=/home/rais`
  - `/root/.cache` 权限为 `drwx------ root root`
- 结论:
  - 当前进程以 `rais` 用户运行.
  - 因此 `/root/.cache/...` 不是“路径写法不优雅”, 而是天然不可读的错误路径.

### 来源2: 当前用户缓存目录
- 动态结果:
  - `~/.cache/huggingface/hub` 可读
  - 但当前 `~/.cache` 下并没有 `Ruicheng/moge-2-vitl` 的 `model.pt`
- 结论:
  - 把 `/root/.cache/...` 机械替换成 `~/.cache/...` 还不够.
  - 当前用户缓存里根本没有这份本地 checkpoint.

### 来源3: `moge-v2_infer.py` 与 `moge.model.v2.MoGeModel.from_pretrained`
- 静态代码事实:
  - `moge-v2_infer.py` 原先会把 `--pretrained` 原样传给 `from_pretrained`
  - `MoGeModel.from_pretrained` 内部先做 `Path(pretrained_model_name_or_path).exists()`
  - 对不可访问路径, 这里会直接抛 `PermissionError`
- 结论:
  - 当前报错点和日志完全吻合.
  - 路径权限问题确实是现象和 traceback 对应的直接根因.

### 来源4: Hugging Face 直连探针
- 动态结果:
  - `model_info("Ruicheng/moge-2-vitl")` 直连成功
- 结论:
  - 至少 Hugging Face 的小请求直连是通的.
  - 因而 `--moge_pretrained Ruicheng/moge-2-vitl` 是一个成立的替代写法.

### 来源5: CUDA 最小探针
- 验证命令:
  - 在 Pixi 环境里执行最小 CUDA matmul
- 关键输出:
  - `torch_version 2.3.1`
  - `compiled_cuda 12.1`
  - `cuda_available True`
  - `device_name NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - `RuntimeError: CUDA error: no kernel image is available for execution on the device`
- 结论:
  - 当前 Blackwell 机器并不是“只是有 warning 但还能勉强跑”.
  - 真实动态证据表明: 当前 PyTorch 安装连基础 CUDA kernel 都无法在这张卡上执行.

### 来源6: 小规模整链路 dry-run
- 验证命令:
  - `single_image_multi_trajectory.py --preset_indices 0 --num_inference_steps 4 --sample_size 360,640 --dry_run`
- 关键输出:
  - `depth` 阶段命令已经改成:
    - `--pretrained Ruicheng/moge-2-vitl`
  - 只选择了 `preset 0`
  - 最终生成阶段缩成了:
    - `--num_inference_steps 4`
    - `--sample_size 360,640`
- 结论:
  - 修正后的命令组装正确.
  - 当前没法真实开跑的原因已经不是 `--moge_pretrained /root/.cache/...` 这条老问题.

## [2026-03-25 20:49:48 UTC] [Session ID: moge_permission_20260325] 笔记: `cu128` 升级下载链路复核

### 来源1: 后台 pip 安装会话
- 动态结果:
  - 当前会话仍停留在 `nvidia-cuda-nvrtc-cu12-12.8.61`
  - 输出明确出现:
    - `WARNING: Connection timed out while downloading.`
    - `WARNING: Attempting to resume incomplete download (3.1 MB/88.0 MB, attempt 1)`
- 结论:
  - 当前“完整 pip 安装”不是纯粹在解包.
  - 它确实被卡在 `pypi.nvidia.com` 的依赖下载阶段.

### 来源2: 主 wheel 元数据
- 动态结果:
  - `torch==2.7.1+cu128` 元数据可以快速获取.
  - 主 wheel URL:
    - `https://download.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp311-cp311-manylinux_2_28_x86_64.whl`
  - `content-length`:
    - `1039389795`
- 关键元数据:
  - `requires_dist` 明确依赖一整串 `nvidia-*` 包:
    - `nvidia-cuda-nvrtc-cu12==12.8.61`
    - `nvidia-cuda-runtime-cu12==12.8.57`
    - `nvidia-cublas-cu12==12.8.3.14`
    - `nvidia-cudnn-cu12==9.7.1.26`
    - 以及其他 CUDA 运行库
- 结论:
  - `--no-deps` 不是官方完整安装.
  - 但它可以作为“系统 CUDA 12.8 是否足以兜底”的最小可证伪实验.

### 来源3: 本机 CUDA 条件
- 动态结果:
  - `nvidia-smi` 显示:
    - `Driver Version: 580.95.05`
    - `CUDA Version: 13.0`
  - 本机存在:
    - `/usr/local/cuda-12.8`
    - `/usr/local/cuda-12.8/targets/x86_64-linux/lib/libnvrtc.so.12.8.93`
    - `/usr/local/cuda-12.8/targets/x86_64-linux/lib/libcudart.so.12.8.90`
    - `/usr/local/cuda-12.8/targets/x86_64-linux/lib/libcublas.so.12.8.4.1`
    - `/usr/local/cuda-12.8/targets/x86_64-linux/lib/libcusparse.so.12.5.8.93`
- 结论:
  - 本机至少具备尝试“torch 主 wheel + 系统 CUDA 库”的静态前提.

### 来源4: 代理链路测速
- 动态结果:
  - `pypi.nvidia.com` 的 1 MB 小样本测速结果约为:
    - `18397 bytes/s`
    - `56.996183s`
- 结论:
  - 当前代理对 `pypi.nvidia.com` 的有效吞吐只有约 `18 KB/s`.
  - 因此继续等待完整依赖链下载, 时间成本不可接受.

## [2026-03-25 21:08:47 UTC] [Session ID: moge_permission_20260325] 笔记: 现成 `cu128` 环境与 Hugging Face 直连验证

### 来源1: 本机其他环境的最小 CUDA 探针
- 动态结果:
  - `FlashVSR-Pro`:
    - `torch 2.6.0+cu124`
    - 仍报 `no kernel image is available for execution on the device`
  - `root/miniconda3`:
    - `torch 2.7.0+cu128`
    - `matmul_ok`
  - `video_to_world`:
    - `torch 2.10.0+cu128`
    - `matmul_ok`
- 结论:
  - Blackwell 的支持边界已经被动态证据钉死:
    - `cu124` 线不够
    - `cu128` 线可用

### 来源2: `video_to_world` 环境的 overlay 实验
- 动态结果:
  - `video_to_world` 原生缺:
    - `transformers`
    - `diffusers`
    - `accelerate`
    - `utils3d`
    - `moge`
  - 通过精确 overlay:
    - `accelerate`
    - `diffusers`
    - `moge`
    - `utils3d`
    - `transformers`
    - `tokenizers`
    - `psutil`
    - `huggingface_hub`
    - `regex`
  - 最终这些核心包都能在 `video_to_world` 的 `cu128` 环境里成功导入
- 结论:
  - 不必先把 VerseCrafter 自己的 `py311 + cu128` torch 装好, 也能先借现成的 `cu128` 环境做链路验证.

### 来源3: Hugging Face 代理与直连对比
- 动态结果:
  - 当前 shell 残留全局代理:
    - `https_proxy=http://127.0.0.1:7897`
    - `http_proxy=http://127.0.0.1:7897`
    - `all_proxy=socks5://127.0.0.1:7897`
  - 带代理跑 `Ruicheng/moge-2-vitl` 时:
    - 只创建了 `0` 字节 `.incomplete`
    - 长时间没有任何增长
  - 去掉代理后:
    - `model_info("Ruicheng/moge-2-vitl")` 秒回
    - `hf_hub_download(..., filename="model.pt")` 已开始稳定增长
    - 当前已观测到:
      - `30 MB`
      - `70 MB`
      - `100 MB`
  - 远端元数据给出的 `model.pt` 总大小:
    - `1305030700`
- 结论:
  - 当前 Hugging Face 下载真正的阻塞是“误走全局代理”.
  - 对 Hugging Face 这一步, 应该显式 `unset` 代理变量再下载.

## [2026-03-25 22:03:54 UTC] [Session ID: moge_permission_20260325] 笔记: 本地 `model.pt` 专用下载方案收敛

### 来源1: `hf_hub_download` 与镜像分片探针
- 动态结果:
  - `HF_ENDPOINT=https://hf-mirror.com` 下:
    - `model_info("Ruicheng/moge-2-vitl")` 正常返回
    - `HEAD` 能拿到:
      - `x-linked-size: 1305030700`
  - 对 `hf-mirror` 做 `4 MB` Range 探针:
    - `http=206`
    - `speed ~= 352730 bytes/s`
  - 对官方 `huggingface.co` 做相同 Range 探针:
    - 在同样时间窗口内超时
- 结论:
  - 当前现场更适合走 `hf-mirror` 的小块 Range 下载, 不适合继续赌官方整文件链路.

### 来源2: 专用下载脚本的参数试验
- 动态结果:
  - 先尝试 `8 MB` 分块:
    - 前几块能动
    - 但在 `268 MB` 左右更容易停住
  - 切回 `4 MB` 分块后:
    - 连续多个块都成功
    - 当前已从 `230686720` 推进到 `415236096`
- 结论:
  - 这台机器当前更稳的参数组合是:
    - 端点: `https://hf-mirror.com`
    - 分块: `4 MB`
    - 单轮超时: `45s`
    - 连续空转容忍: `2`

### 来源3: 本地稳定落点
- 动态结果:
  - 旧的 Hugging Face cache partial 已迁移到:
    - `~/.cache/huggingface/local-moge-2-vitl/model.pt.part`
- 结论:
  - 现在已经不依赖 Hugging Face 的内部 cache 路径结构.
  - 一旦下载完成, 就能直接把最终路径传给:
    - `--moge_pretrained ~/.cache/huggingface/local-moge-2-vitl/model.pt`

## [2026-03-25 14:56:37 UTC] [Session ID: moge_permission_20260325] 笔记: 下载继续推进, 小规模参数边界复核

### 来源1: 后台续传会话 `16853`
- 动态结果:
  - 本轮继续读取会话后, `.part` 已从:
    - `822083584`
  - 推进到:
    - `859832320`
  - 中间虽然会出现单次 `delta=0`, 但后续 attempt 仍能继续拿到新的 `4 MB` 分块.
- 结论:
  - 当前 `hf-mirror + 4 MB Range + 外层重试` 方案仍然有效.
  - 现在不应该打断它或切回其他下载路径.

### 来源2: 本机已有缓存复查
- 动态结果:
  - 在 `/root/.cache` 与 `/home/rais/.cache` 范围内, 没有找到可直接复用的完整:
    - `moge-2-vitl/model.pt`
- 结论:
  - 这轮不能靠“复制现成完整文件”来跳过等待.
  - 继续把当前 `.part` 推到完成, 仍是最快路径.

### 来源3: 小规模真实测试的进一步缩减边界
- 静态代码事实:
  - `single_image_multi_trajectory.py` 虽然暴露了 `--num_frames`, 但在主流程里会强校验:
    - `args.num_frames == DEFAULT_NUM_FRAMES`
  - `DEFAULT_NUM_FRAMES = 81`
- 结论:
  - 当前工作流不能通过减小帧数进一步缩短真实测试.
  - 因此小规模参数应继续保持:
    - `--camera_only`
    - `--preset_indices 0`
    - `--sample_size 360,640`
    - `--num_inference_steps 4`

## [2026-03-25 15:12:16 UTC] [Session ID: moge_permission_20260325] 笔记: overlay 元数据缺失导致 `EncodingFast` 导入失败

### 来源1: VerseCrafter 模块导入 traceback
- 动态结果:
  - 在 `video_to_world + /tmp/versecrafter_py310_overlay` 环境里导入:
    - `versecrafter.models`
    - `versecrafter.pipeline.pipeline_wan_versecrafter`

## [2026-03-25 16:00:02 UTC] [Session ID: moge_permission_20260325] 笔记: 真实测试卡点从 `MoGe` 切到 CPU 背景点云渲染

### 来源1: 真实测试会话 `27673`
- 动态结果:
  - `single_image_multi_trajectory.py` 当前仍在运行.
  - `rendering_4D_control_maps.py` 子进程 PID `565933`
  - 进程状态持续为:
    - `%CPU ~= 101`
    - `TIME ~= 18m+`
  - `/proc/565933/stat` 连续两秒采样:
    - `delta_utime = 200`
- 结论:
  - 这不是“完全卡死不动”.
  - 当前子进程仍在稳定消耗 CPU 做计算.

### 来源2: 当前共享 Gaussian 与 trajectory 产物
- 动态结果:
  - `shared/fitted_3D_gaussian/gaussian_params.json`:
    - `num_objects = 0`
    - `gaussian_params = {}`
  - `0/custom_3D_gaussian_trajectory.json`:
    - `metadata.num_objects = 0`
    - `metadata.num_frames = 81`
    - 每帧 `objects` 为空
- 结论:
  - 当前场景确实是纯背景 camera-only 路径.
  - `--moge_fp16` 没有把流程卡在 `MoGe`.

### 来源3: 当前渲染代码与输出目录
- 静态代码事实:
  - `render_video_with_bg_and_fg(..., mode='background')` 仍会对全部背景点执行 PyTorch3D 点云渲染.
  - 这轮目标尺寸是:
    - `360 x 640`
    - 对应背景点总数约 `230400`
  - `rendering_4D_maps/` 在背景渲染结束前不会提前落 `background_RGB.mp4`
- 动态结果:
  - 当前输出目录仍为空.
- 结论:
  - 目前最重的耗时不是前景空 mesh, 而是 CPU 背景点云渲染本身.

### 当前判断
- 主假设:
  - smoke test 更适合增加一个“背景点数量上限”参数, 让 Step 5 可控降采样.
- 备选解释:
  - 也可能需要后续继续检查 PyTorch3D CPU 路径的 batch 参数是否存在更优组合.

## [2026-03-25 16:20:16 UTC] [Session ID: moge_permission_20260325] 笔记: Step 5 render 分辨率可以独立于最终生成尺寸

### 来源1: `versecrafter_inference.py` 与 `VideoX-Fun`
- 静态代码事实:
  - `versecrafter_inference.py` 读取控制视频时调用:
    - `get_video_to_video_latent(control_video_path_full, video_length=video_length, sample_size=sample_size, fps=fps, ref_image=None)`
  - `third_party/VideoX-Fun/videox_fun/utils/utils.py` 里:
    - `get_video_to_video_latent(...)` 会对每帧执行:
      - `cv2.resize(frame, (sample_size[1], sample_size[0]))`
- 结论:
  - 控制视频的原始分辨率不必与最终生成 `sample_size` 完全一致.
  - 对 smoke test 来说, Step 5 render 可以先用更小尺寸, 最终生成阶段会再 resize.

### 来源2: `background_point_limit=60000` 的真实测试
- 动态结果:
  - 日志已确认:
    - `Background point cloud throttled for smoke test: 230400 -> 60000`
  - 但 `rendering_4D_maps/` 在 `10+` 分钟后仍未写出文件
- 结论:
  - 只限制背景点数量还不够.
  - 当前瓶颈更像是“点云渲染 + 目标分辨率”的组合成本.

### 当前判断
- 主假设:
  - 把 Step 5 render 分辨率单独降到更小尺寸, 比继续单纯砍点数更有效.
- 备选解释:
  - 如果分辨率下调后仍无明显改善, 则需要重新审视 PyTorch3D CPU 路径本身是否适合继续做 smoke test.

## [2026-03-25 16:30:11 UTC] [Session ID: moge_permission_20260325] 笔记: render 已通过, generation 失败点锁定为 TeaCache 步数边界

### 来源1: 新 smoke test 的动态结果
- 动态结果:
  - `render_sample_size=180,320`
  - `render_background_point_limit=20000`
  - render 进度条明确推进:
    - `1/3` 用时约 `115.97s`
    - `2/3` 用时约 `116.17s`
    - `3/3` 用时约 `116.36s`
  - 最终输出目录已生成:
    - `background_RGB.mp4`
    - `background_depth.mp4`
    - `merged_mask.mp4`
    - `3D_gaussian_RGB.mp4`
    - `3D_gaussian_depth.mp4`
    - `background_and_3D_gaussian.mp4`
- 结论:
  - 当前 render 提速策略已经成立.
  - 真实链路的前半段已经打通.

### 来源2: Step 6 失败 traceback
- 动态结果:
  - `inference/versecrafter_inference.py` 在启用 TeaCache 时抛出:
    - `ValueError: num_skip_start_steps must be ... <= num_steps=4 but is 5`
  - traceback 停在:
    - `pipeline.transformer.enable_teacache(...)`
    - `third_party/VideoX-Fun/videox_fun/models/cache_utils.py`
- 结论:
  - 当前失败与 `pytorch3d`、render 分辨率、`moge_fp16` 都无关.
  - 它是 Step 6 的小步数配置边界问题.

### 来源3: `inference/versecrafter_inference.py`
- 静态代码事实:
  - 文件里固定写了:
    - `num_skip_start_steps = 5`
  - 之后无条件调用:
    - `pipeline.transformer.enable_teacache(..., num_skip_start_steps=num_skip_start_steps, ...)`
- 结论:
  - 只要 `--num_inference_steps < 5`, 小规模测试就会撞到这里.
  - 初始都会在:
    - `transformers/tokenization_utils_base.py`
  - 报:
    - `NameError: name 'EncodingFast' is not defined`
- 调用链关键点:
  - `versecrafter.models` -> `transformers` -> `tokenization_utils_base.py`
  - 错误不在 VerseCrafter 自己代码, 而在 overlay 中的 `transformers 4.57.0` 初始化阶段.

### 来源2: `transformers` 的动态可用性判断
- 动态结果:
  - 同一环境里:
    - `import tokenizers` 成功
    - `tokenizers.__version__ == 0.22.2`
  - 但:
    - `transformers.utils.import_utils.is_tokenizers_available() == False`
  - 进一步验证:
    - `importlib.util.find_spec('tokenizers')` 指向 `/tmp/versecrafter_py310_overlay/tokenizers/__init__.py`
    - `importlib.metadata.version('tokenizers')` 报 `PackageNotFoundError`
- 结论:
  - 当前真正问题不是“tokenizers 包不存在”.
  - 而是 overlay 只挂了包目录, 没挂 `tokenizers-0.22.2.dist-info`, 让 `transformers` 的元数据探测误判为不可用.

### 来源3: 最小环境修正与复验
- 动态结果:
  - 已把这些元数据目录一起挂进 overlay:
    - `accelerate-1.13.0.dist-info`
    - `diffusers-0.37.0.dist-info`
    - `moge-2.0.0.dist-info`
    - `psutil-7.2.2.dist-info`
    - `regex-2026.2.28.dist-info`
    - `tokenizers-0.22.2.dist-info`
    - `transformers-4.57.0.dist-info`
  - 修正后:
    - `is_tokenizers_available() == True`
    - `versecrafter.models` 导入成功
    - `versecrafter.pipeline.pipeline_wan_versecrafter` 导入成功
    - `inference/versecrafter_inference.py --help` 可正常输出 CLI
- 伴随现象:
  - 仍会有 `librosa` 缺失 warning
  - 但日志已明确说明这不影响 VerseCrafter 的非音频工作流
- 结论:
  - 这套 `cu128 + overlay` 环境目前已经越过了导入阶段的硬阻塞.
  - 后续真实测试的主要剩余门槛又回到了:
    - `moge-2-vitl/model.pt` 下载完成

### 来源4: 下载并行推进状态
- 动态结果:
  - 本轮记录时 `.part` 已增长到:
    - `994050048 / 1305030700`
- 结论:
  - 下载和环境修正两条线已经同时收敛.
  - 当前距离真实运行只剩最后一段本地 `model.pt` 落盘.

## [2026-03-25 15:54:17 UTC] [Session ID: moge_permission_20260325] 笔记: `model.pt` 已落盘, 小规模真实测试收敛到 Blackwell + MoGe 半精度与 CPU render

### 来源1: 本地 `model.pt` 完整落盘
- 动态结果:
  - 最终文件:
    - `/home/rais/.cache/huggingface/local-moge-2-vitl/model.pt`
  - 文件大小:
    - `1305030700`
- 结论:
  - `Ruicheng/moge-2-vitl` 的本地可读 checkpoint 已准备完成.
  - 后续测试已经不再依赖外网下载.

### 来源2: `my7` 原图路径复查
- 动态结果:
  - `demo_data/my7/` 下只剩:
    - `manifest.json`
  - 仓库和 `/root/autodl-tmp/home/rais` 范围内都找不到:
    - `demo_data/my7/d.png`
    - 任意名为 `d.png` 的文件
- 结论:
  - 用户原命令里的 `demo_data/my7/d.png` 在当前机器上已经缺失.
  - 为了继续验证链路, 本轮改用仓库内现成存在的:
    - `demo_data/my5/b.png`

### 来源3: Blackwell 上 MoGe 的 `fp32` / `fp16` 对照
- 动态结果:
  - 用 `video_to_world` 的 `cu128` 环境直接跑 MoGe:
    - 不加 `--fp16` 时, 会在 `xformers.memory_efficient_attention` 报 `NotImplementedError`
    - 关键原因:
      - 当前 Blackwell `sm_120`
      - 该路径的 `xformers` 只接受 `float16 / bfloat16`, 不接受这次的 `float32`
  - 单独验证:
    - `inference/moge-v2_infer.py ... --fp16`
    - 能完整生成:
      - `depth_vis.png`
      - `depth_gray.png`
      - `depth_intrinsics.npz`
- 结论:
  - 当前环境下, `--moge_fp16` 不是“锦上添花”, 而是 Blackwell 上 MoGe v2 能否跑通的必要开关.
  - 这一步确实可能带来一定深度精度损失, 但当前 `fp32` 基线在这套环境里无法跑通, 因而暂时无法做同图直接量化对照.

### 来源4: 批处理脚本的新增调度能力
- 动态结果:
  - 已给 `single_image_multi_trajectory.py` 增加:
    - `--render_python_bin`
    - `--render_device`
    - `--moge_fp16`
  - `--dry_run` 已验证:
    - MoGe: `video_to_world` `cu128` Python + `--fp16`
    - render: VerseCrafter 自带 `py311` Python + `cpu`
    - generation: `video_to_world` `cu128` Python
- 结论:
  - 当前批处理脚本已经支持“按步骤切环境”的混合执行方案.

### 来源5: 当前真实测试的动态状态
- 动态结果:
  - 已成功完成:
    - 本地 `model.pt` 加载
    - MoGe depth estimation(`demo_data/my5/b.png`, `--moge_fp16`)
    - 共享深度 / 空 mask / 空 Gaussian 占位
    - 轨迹资产生成
  - 当前运行中的最慢步骤:
    - `inference/rendering_4D_control_maps.py`
    - `device=cpu`
    - 持续 `100%+ CPU`
    - 已运行超过 `10` 分钟
  - 当前 manifest:
    - `shared.status = completed`
    - `trajectory_assets_status = completed`
    - `render_status = pending`
    - `generation_status = pending`
- 结论:
  - 当前没有新的报错证据.
  - 这轮小规模真实测试已经把最小阻塞点收敛成:
    - `camera_only` 路径下的 CPU render 很慢, 但仍在持续计算
