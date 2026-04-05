# 排查笔记: `pytorch3d` 构建阶段错误引用不存在的 `nvcc`

## [2026-03-31 12:35:33 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 笔记: 第一轮证据整理

### 来源1: 用户报错日志
- 已观察到的现象:
  - `Building wheel for pytorch3d (pyproject.toml) ... error`
  - 构建最终失败在:
    - `error: [Errno 2] No such file or directory: '/usr/local/cuda-12.9/bin/nvcc'`
- 初步含义:
  - 当前不是“编译太慢”或“C++ 被系统杀掉”的问题.
  - 是构建入口已经拿到了一个不存在的 CUDA toolkit 路径.

### 来源2: `scripts/install_pytorch3d.sh`
- 静态代码事实:
  - 只有以下几条路径会影响 `CUDA_HOME`:
    - `PYTORCH3D_CUDA_HOME`
    - 继承的 `CUDA_HOME`
    - `command -v nvcc`
    - `/usr/local/cuda`
    - `find /usr/local -maxdepth 1 -type d -name 'cuda-*' | sort -V | tail -n 1`
  - 脚本当前不会主动生成固定的 `/usr/local/cuda-12.9`.
  - 但脚本也没有在透传前验证 `CUDA_HOME/bin/nvcc` 是否真的存在.
- 结论:
  - 若外部显式给了坏路径, 当前脚本会把它原样透传给 pip 构建阶段.

### 来源3: 当前工作区真实环境
- 动态验证:
  - `env | rg 'PYTORCH3D_CUDA_HOME|CUDA_HOME|PYTORCH3D_TORCH_CUDA_ARCH_LIST|TORCH_CUDA_ARCH_LIST'`
  - `direnv exec ... env | rg ...`
  - `pixi run env | rg ...`
- 关键结果:
  - `PYTORCH3D_CUDA_HOME=` 空
  - `CUDA_HOME` 未设置
  - `PYTORCH3D_TORCH_CUDA_ARCH_LIST=` 空
- 结论:
  - 当前这台机器、当前 shell、当前 `.envrc`、当前 Pixi 环境里, 都没有把 `CUDA_HOME` 显式指向 `/usr/local/cuda-12.9`.

### 来源4: 当前机器实际 CUDA 目录
- 动态验证:
  - `ls -ld /usr/local/cuda /usr/local/cuda-*`
  - `readlink -f /usr/local/cuda`
- 关键结果:
  - 存在:
    - `/usr/local/cuda`
    - `/usr/local/cuda-12`
    - `/usr/local/cuda-12.8`
  - 不存在:
    - `/usr/local/cuda-12.9`
- 结论:
  - 报错里的 `cuda-12.9` 不是“现场真实存在但不可执行”的目录, 而是一个根本不存在的路径.

### 来源5: `pixi run python` + `torch.utils.cpp_extension`
- 动态结果:
  - `torch.__version__ = 2.3.1`
  - `torch.version.cuda = 12.1`
  - `torch.cuda.is_available() = True`
  - `env.CUDA_HOME = None`
  - `torch.utils.cpp_extension.CUDA_HOME = /usr/local/cuda`
- 读取 `_find_cuda_home()` 源码后确认:
  - 只会按顺序检查:
    - `CUDA_HOME` / `CUDA_PATH`
    - `which nvcc`
    - `/usr/local/cuda`
- 结论:
  - PyTorch 自己不会凭空推导出 `/usr/local/cuda-12.9`.
  - “PyTorch 内部自动拼错版本号”这个备选解释已被静态源码证伪.

### 来源6: `README.md`
- 当前用户可见说明包含:
  - `PYTORCH3D_CUDA_HOME=/usr/local/cuda-12.9`
  - `PYTORCH3D_TORCH_CUDA_ARCH_LIST=12.0`
- 风险判断:
  - 这个示例过于具体.
  - 如果读者机器实际装的是 `12.8` 或别的版本, 很容易直接复制后得到和本次完全一致的报错.

### 来源7: `tests/test_install_pytorch3d_script.py`
- 现有测试 `test_install_pytorch3d_forwards_stable_ref_and_build_env` 明确把:
  - `PYTORCH3D_CUDA_HOME=/usr/local/cuda-12.9`
  作为“正常透传”的示例.
- 动态验证:
  - `pixi run pytest tests/test_install_pytorch3d_script.py::test_install_pytorch3d_forwards_stable_ref_and_build_env -q`
  - 结果: `1 passed`
- 结论:
  - 当前仓库不仅 README 给了高风险示例, 测试也在强化“脚本应该无条件透传这个路径”的旧行为.

### 综合判断
- 现象:
  - 构建失败在不存在的 `nvcc` 路径.
- 主假设:
  - 用户或运行环境显式注入了错误的 `PYTORCH3D_CUDA_HOME` / `CUDA_HOME`, 而脚本缺少前置校验, 于是坏路径被一路透传到 PyTorch3D 构建.
- 最强备选解释:
  - PyTorch / PyTorch3D 在构建过程中根据版本信息自动拼出了 `/usr/local/cuda-12.9`.
- 已有证据如何推翻备选解释:
  - `torch.utils.cpp_extension._find_cuda_home()` 源码不包含任何“按 CUDA 版本号拼 `/usr/local/cuda-<version>`”的逻辑.

### 当前结论
- 可以进入正式修复:
  - 在 `install_pytorch3d.sh` 中对显式 `CUDA_HOME` 做前置校验.
  - README 不再给固定的 `/usr/local/cuda-12.9` 示例, 改成“用真实 `nvcc` 所在 toolkit 路径”.
  - 测试从“透传坏路径”改成“验证有效路径 + 验证坏路径会被提早拦截”.

## [2026-03-31 12:39:27 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 笔记: 修复后验证

### 来源8: 脚本与测试验证
- 执行命令:
  - `bash -n scripts/install_pytorch3d.sh`
  - `pixi run pytest tests/test_install_pytorch3d_script.py -q`
- 关键结果:
  - `bash -n` 通过
  - `3 passed in 0.16s`
- 当前被锁住的行为:
  - 已安装时幂等短路仍然成立
  - 显式有效 `PYTORCH3D_CUDA_HOME` 会继续被透传
  - 显式无效 `PYTORCH3D_CUDA_HOME` 会在 clone / pip install 之前被提前拦截

### 修复后的结论
- 本轮修的不是“把默认值换成 12.8”.
- 真正修的是:
  - 显式 CUDA toolkit 路径现在必须先通过存在性和 `bin/nvcc` 校验
  - README 不再鼓励复制一个具体版本目录
  - 测试把“坏路径应早失败”纳入了回归保护

## [2026-03-31 12:41:29 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 笔记: 现场安装入口复验

### 来源9: `pixi run install-pytorch3d`
- 执行结果:
  - 当前 Pixi 环境里的 `pytorch3d` 版本为 `0.7.9`
  - `pixi run install-pytorch3d` 输出:
    - `检测到已安装 pytorch3d 0.7.9, 跳过重复安装`
- 结论:
  - 当前仓库入口已经恢复幂等.
  - 至少在这个工作区里, 再次执行不会重现之前那种“直接闯进构建失败”的体验.

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 笔记: Blackwell 参考组合现场安装证据

### 来源10: 现场 CUDA / GPU 事实
- 动态结果:
  - GPU: `NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - `torch.cuda.is_available() = True`
  - 当前使用的 CUDA toolkit 根目录: `/usr/local/cuda`
  - 该路径实际指向 `cuda-12.8`
- 结论:
  - 用户给出的 Blackwell 路线可以沿用, 但 `CUDA_HOME` 必须改成现场真实存在的 `/usr/local/cuda`, 不能继续写死 `cuda-12.9`.

### 来源11: 覆盖升级后的 PyTorch 组合
- 执行命令:
  - `pixi run python -m pip install -U pip setuptools wheel cmake ninja`
  - `pixi run python -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0`
- `pip show` 结果:
  - `torch 2.7.0+cu128`
  - `torchvision 0.22.0+cu128`
  - `torchaudio 2.7.0+cu128`
- 验证结果:
  - `torch.version.cuda = 12.8`
  - 设备可见且可初始化
- 结论:
  - 当前 Pixi 环境已经从旧的 `torch 2.3.1 + cu121` 覆盖切换到更适合 Blackwell 的 `2.7.0 + cu128`.

### 来源12: 通过代理源码安装 `pytorch3d`
- 执行命令:
  - `env https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897 all_proxy=socks5://127.0.0.1:7897 CC=/usr/bin/g++ CXX=/usr/bin/g++ CUDAHOSTCXX=/usr/bin/g++ CUDA_HOME=/usr/local/cuda PATH=/usr/local/cuda/bin:$PATH LD_LIBRARY_PATH=/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=16 pixi run python -m pip install -v --force-reinstall --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable"`
- 关键结果:
  - `stable` 解析为 `pytorch3d 0.7.8`
  - 编译与 wheel 安装完成
  - 最终输出:
    - `Successfully installed ... pytorch3d-0.7.8`
- 结论:
  - 现场已证明:
    - `torch 2.7.0+cu128`
    - `CUDA_HOME=/usr/local/cuda`
    - `TORCH_CUDA_ARCH_LIST=12.0`
    - `pytorch3d@stable`
    这组组合在当前 Blackwell 机器上可成功安装.

### 来源13: 安装后验收
- 执行命令:
  - `pixi run python -c "import pytorch3d; print('pytorch3d OK', pytorch3d.__version__)"`
  - `pixi run python -c "from pytorch3d.ops import knn_points; print('ops import OK', knn_points.__name__)"`
  - `OMP_NUM_THREADS=1 pixi run python -c "import torch; from pytorch3d.ops import knn_points; ..."`
- 关键结果:
  - `pytorch3d OK 0.7.8`
  - `ops import OK knn_points`
  - `knn dists shape (1, 8, 2)`
  - `knn idx shape (1, 8, 2)`
  - `knn device cuda:0`
- 结论:
  - 当前不只是“包能 import”.
  - `pytorch3d` 的 CUDA 扩展已经至少完成了一次真实的 GPU 算子执行.

### 来源14: 环境噪音
- 动态结果:
  - `pixi run env | rg '^OMP_NUM_THREADS='`
  - 输出: `OMP_NUM_THREADS=0`
- 现象:
  - 不手动覆盖时, 相关 Python 命令会先打印:
    - `libgomp: Invalid value for environment variable OMP_NUM_THREADS`
- 结论:
  - 这不是本轮安装失败的根因.
  - 但它会污染后续运行输出, 也可能影响线程行为判断.
  - 适合后续单独清理为环境级问题.

### 综合发现

### 已验证结论
- 本轮安装成功的现场版本组合是:
  - `torch 2.7.0+cu128`
  - `torchvision 0.22.0+cu128`
  - `torchaudio 2.7.0+cu128`
  - `pytorch3d 0.7.8`
  - `CUDA_HOME=/usr/local/cuda` -> `cuda-12.8`
  - `TORCH_CUDA_ARCH_LIST=12.0`
- 这套组合已经通过:
  - Python 导入
  - `pytorch3d.ops` 导入
  - 最小 CUDA `knn_points` 调用

### 仍需明确标注的风险
- 当前成功安装是“覆盖式安装到已有 Pixi 环境”.
- `pixi.toml` 仍保留旧的 `torch 2.3.1.* / pytorch-cuda 12.1.*` 约束.
- 因此, 这次成功安装目前还不是“声明式可重建状态”, 后续若重建环境可能回退.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 笔记: 将 Blackwell 成功组合写回 Pixi 声明式环境

### 来源15: Pixi 官方文档
- Context7 文档结论:
  - Pixi 支持 conda MatchSpec 风格版本约束.
  - 改完 `pixi.toml` 后, `pixi install` 会在需要时同步更新 `pixi.lock`.
  - Pixi 也支持对单个 PyPI 包指定自定义 index, 示例形如:
    - `torch = { version = "*", index = "https://download.pytorch.org/whl/cu118" }`
- 结论:
  - 这次把 PyTorch `cu128` wheel 固化到 manifest, 在语法上是被 Pixi 官方明确支持的.

### 来源16: 第一版“继续用 conda `pytorch-cuda`”方案的失败证据
- 现象:
  - 将 `pixi.toml` 先改成:
    - `pytorch = "2.7.0.*"`
    - `torchvision = "0.22.0.*"`
    - `torchaudio = "2.7.0.*"`
    - `pytorch-cuda = "12.8.*"`
  - 之后执行:
    - `env ... pixi install`
  - 得到失败:
    - `No candidates were found for pytorch-cuda 12.8.*`
- 结论:
  - “把现场成功组合原样继续声明成 conda `pytorch + pytorch-cuda`”这个假设被动态证据推翻.
  - 问题不在 TOML 语法, 而在当前 channels 下没有对应的 conda 候选包.

### 来源17: 最终可工作的 Pixi 声明式方案
- 采取的修正:
  - 从 `[dependencies]` 移除:
    - `pytorch`
    - `torchvision`
    - `torchaudio`
    - `pytorch-cuda`
  - 改为在 `[pypi-dependencies]` 中声明:
    - `torch = { version = "==2.7.0", index = "https://download.pytorch.org/whl/cu128" }`
    - `torchvision = { version = "==0.22.0", index = "https://download.pytorch.org/whl/cu128" }`
    - `torchaudio = { version = "==2.7.0", index = "https://download.pytorch.org/whl/cu128" }`
- 相关同步修改:
  - README 改成说明 Blackwell 默认环境下 `TORCH_CUDA_ARCH_LIST=12.0` 会被自动推断.
  - `scripts/install_flash_attn.sh` 去掉过期的 `torch 2.3.1` 注释.

### 来源18: 声明式收口后的验证
- 执行命令:
  - `env ... pixi install`
  - `rg -n "download\\.pytorch\\.org/whl/cu128" pixi.lock`
  - `OMP_NUM_THREADS=1 pixi run python - <<'PY' ...`
  - `pixi run python -m pip show torch torchvision torchaudio pytorch3d`
- 关键结果:
  - `✔ The default environment has been installed.`
  - `pixi.lock` 已出现:
    - `torch-2.7.0+cu128`
    - `torchaudio-2.7.0+cu128`
    - `torchvision-0.22.0+cu128`
  - 运行时仍然是:
    - `torch 2.7.0+cu128`
    - `torch_cuda 12.8`
    - `pytorch3d 0.7.8`
    - `knn_device cuda:0`
- 结论:
  - 当前已经不只是“工作区现场装好了”.
  - 而是 `pixi.toml`、`pixi.lock` 和运行时环境三者已经重新对齐.

### 来源19: 非阻塞告警
- 现象:
  - `pixi install` 过程中出现:
    - ``transformers==4.57.0` is yanked (reason: "Error in the setup causing installation issues")`
- 结论:
  - 这没有阻止本轮 lockfile 与环境安装成功.
  - 但它说明当前 manifest 里固定的 `transformers==4.57.0` 带有上游风险标记, 适合后续单独评估.

### 综合发现

### 已验证结论
- 对当前项目和当前 Blackwell 机器来说, 最稳的声明式方案不是继续追 conda `pytorch-cuda`.
- 更稳的做法是:
  - conda 继续管理 Python / 构建工具
  - PyTorch 三件套改由 Pixi 的 `pypi-dependencies + per-package index` 固定到 `cu128` wheel
- 这条方案已经通过:
  - `pixi install`
  - `pixi.lock` 检查
  - 运行时导入
  - 最小 CUDA `knn_points` 调用

## [2026-03-31 16:17:12 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] 笔记: flash_attn / kornia 导入故障根因调查

### 来源15: 最小运行时导入实验
- 执行命令:
  - OMP_NUM_THREADS=1 pixi run python -c "import flash_attn"
  - OMP_NUM_THREADS=1 pixi run python -c "import kornia"
  - OMP_NUM_THREADS=1 pixi run python -c "from kornia.geometry.depth import depth_to_3d_v2"
  - OMP_NUM_THREADS=1 pixi run python -c "import inference.rendering_4D_control_maps"
- 动态结果:
  - 单独导入 flash_attn 直接失败.
  - 单独导入 kornia 也失败.
  - 只导入 depth_to_3d_v2 仍然失败.
  - 直接导入 rendering_4D_control_maps.py 失败位置正是文件顶部的 from kornia.geometry.depth import depth_to_3d_v2.
- 共同错误:
  - flash_attn_2_cuda.cpython-311-x86_64-linux-gnu.so: undefined symbol: _ZN3c105ErrorC2ENS_14SourceLocationESs

### 来源16: kornia 0.8.0 包初始化逻辑
- 静态代码事实:
  - kornia/__init__.py 会先导入 filters 和 geometry.
  - 随后又无条件导入 augmentation、contrib、feature 等多个大模块.
  - 其中 feature/lightglue.py 会继续导入 flash_attn.modules.mha.
- 结论:
  - 当前脚本并不是“主动使用 LightGlue 或 flash_attn”.
  - 它只是因为 Python 需要先执行 kornia 包的 __init__, 被顶层宽导入副作用拖进了 flash_attn.

### 来源17: 渲染脚本真实需求边界
- inference/rendering_4D_control_maps.py 中和 kornia 相关的唯一使用点:
  - 读取 depth_to_3d_v2
  - 在构建背景点云时调用 1 次, 把 depth + intrinsic 反投影成相机坐标系点云.
- kornia 源码中 depth_to_3d_v2 的实现已读取确认:
  - 本质是基于内参对像素网格做归一化反投影.
  - 不依赖 augmentation、feature、LightGlue 或 flash_attn.
- 结论:
  - 让整个渲染脚本为了一个简单几何函数承受 kornia 顶层导入副作用, 依赖边界过宽.

### 当前判断
- 现象:
  - rendering_4D_control_maps.py 在导入阶段失败, 尚未进入实际渲染逻辑.
- 主假设:
  - flash-attn 与当前 torch 2.7.0+cu128 确实存在 ABI 不匹配.
- 最强备选解释:
  - 即使 flash-attn 失配属实, 当前脚本也不该被这个无关依赖阻断.
- 已验证结论:
  - 对当前用户命令来说, 更正确的第一修复点是收窄 rendering_4D_control_maps.py 的依赖边界, 用本地实现替代这一个 depth_to_3d_v2 用途.
  - 重编 flash-attn 可以作为环境后续修复项, 但不应成为这个渲染脚本继续运行的前置条件.

## [2026-03-31 16:21:52 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] 笔记: 修复后验证

### 来源18: 单测与模块导入验收
- 执行命令:
  - OMP_NUM_THREADS=1 pixi run pytest tests/test_rendering_4d_control_maps.py -q
  - OMP_NUM_THREADS=1 pixi run python -c "import inference.rendering_4D_control_maps"
- 结果:
  - 2 passed in 2.14s
  - 模块导入成功, depth_to_3d_v2_compatible 可见
- 结论:
  - 当前渲染脚本已经不再依赖 kornia 顶层导入链才能完成模块初始化.

### 来源19: 真实现场命令复验
- 执行命令:
  - OMP_NUM_THREADS=1 pixi run python inference/rendering_4D_control_maps.py --png_path demo_data/my7/d.png --npz_path demo_data/my7/shared/estimated_depth/depth_intrinsics.npz --mask_dir demo_data/my7/shared/foreground_masks/masks --trajectory_npz demo_data/my7/11/custom_camera_trajectory.npz --ellipsoid_json demo_data/my7/11/custom_3D_gaussian_trajectory.json --output_dir demo_data/my7/11/rendering_4D_maps --device cuda --point_size 0.005 --fps 16 --render_batch_size 27 --target_height 720 --target_width 1280
- 动态结果:
  - 成功进入背景渲染与前景渲染阶段
  - 最终输出 Rendering complete
  - exit code = 0
- 结论:
  - 用户日志里那条失败命令在修复后已可跑通.

## [2026-03-31 16:37:23 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] 笔记: flash_attn 重编证据与结果

### 来源20: 当前安装脚本与官方构建建议对齐
- 现场脚本事实:
  - scripts/install_flash_attn.sh 原先只看发行版元数据, 不验证 import 是否健康.
  - 这会让 torch 升级后的 ABI 失配现场被误判成“已安装, 可跳过”.
- 官方资料:
  - 通过 Context7 读取 Dao-AILab flash-attention README.
  - 官方推荐的基础安装命令是 pip install flash-attn --no-build-isolation.
  - 官方也明确给出 MAX_JOBS=4 pip install flash-attn --no-build-isolation 这类并发限制写法.
- 当前收口方案:
  - 保留项目现有的 no-build-isolation 路线.
  - 增加 no-deps, 避免 pip 在重编 flash_attn 时碰当前已经对齐好的 torch 组合.
  - 增加 no-binary flash-attn, 明确要求走源码构建.
  - 当检测到旧安装或强制重编时, 再附加 no-cache-dir 和 force-reinstall.

### 来源21: 真实环境重编
- 先执行:
  - OMP_NUM_THREADS=1 pixi run python -m pip uninstall -y flash-attn
- 再执行:
  - 代理 + CUDA_HOME=/usr/local/cuda + FLASH_ATTN_CUDA_ARCHS=120 + MAX_JOBS=16 + pixi run install-flash-attn
- 动态结果:
  - 成功下载 flash_attn-2.8.3.tar.gz
  - 成功构建 wheel
  - 最终输出 Successfully installed flash-attn-2.8.3
- 补充观察:
  - 构建输出较安静, 但源码目录里提前生成了 wheel 文件, 说明实际编译已经完成, 只是 pip 最后的收尾输出延后显示.

### 来源22: 重编后验收
- 执行命令:
  - OMP_NUM_THREADS=1 pixi run python -c "import flash_attn; import kornia; import inference.rendering_4D_control_maps"
  - FLASH_ATTN_CUDA_ARCHS=120 OMP_NUM_THREADS=1 pixi run install-flash-attn
- 结果:
  - flash_attn 导入成功
  - kornia 0.8.0 顶层导入成功
  - rendering_4D_control_maps.py 导入成功
  - install-flash-attn 能正确识别“已安装且可导入”, 并跳过重复编译
- 结论:
  - 当前 ABI 失配已经被真实重编消除.
  - 项目安装入口也已经从“只看元数据”提升到了“看运行时健康度”.
