# 错误修复记录: `pytorch3d` 构建错误引用不存在的 `nvcc`

## [2026-03-31 12:39:27 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 修复 `install-pytorch3d` 对无效 CUDA toolkit 路径的错误透传

### 现象
- 用户构建 `pytorch3d` 时失败在:
  - `error: [Errno 2] No such file or directory: '/usr/local/cuda-12.9/bin/nvcc'`
- 这说明失败点不是一般性的编译报错, 而是构建链路已经拿到了一个不存在的 CUDA toolkit 根目录.

### 原因
- `scripts/install_pytorch3d.sh` 会接受:
  - `PYTORCH3D_CUDA_HOME`
  - 继承的 `CUDA_HOME`
  这类显式路径.
- 旧逻辑没有在入口验证这些路径是否真的包含 `bin/nvcc`.
- README 还提供了一个过于具体的 `PYTORCH3D_CUDA_HOME=/usr/local/cuda-12.9` 示例, 容易被直接复制到并不匹配的机器上.

### 修复
- 在 `scripts/install_pytorch3d.sh` 中新增:
  - 显式 `PYTORCH3D_CUDA_HOME` / `CUDA_HOME` 的前置校验
  - 目录不存在时的清晰报错
  - 缺少 `bin/nvcc` 时的清晰报错
  - 当前 `nvcc` 与 `/usr/local/cuda*` 候选目录提示
- 将 CUDA toolkit 校验前移到 clone 之前, 避免错误配置时还白白跑一轮网络和源码准备.
- 更新 `README.md` 与 `.envrc` 注释, 强调显式路径必须是真实 toolkit 根目录.
- 更新 `tests/test_install_pytorch3d_script.py`, 新增“坏路径应提前失败”的回归测试.

### 验证
- `bash -n scripts/install_pytorch3d.sh`
- `pixi run pytest tests/test_install_pytorch3d_script.py -q`
- 关键结果:
  - `3 passed in 0.16s`
- 额外动态结论:
  - 当前工作区里 `PYTORCH3D_CUDA_HOME` 默认是空
  - 当前机器存在 `cuda-12.8`, 不存在 `cuda-12.9`
  - `torch.utils.cpp_extension._find_cuda_home()` 源码不包含自动拼 `cuda-12.9` 的逻辑

### 复盘提醒
- 以后看到这类 `.../bin/nvcc: No such file or directory`, 不要先怀疑 PyTorch3D 本身.
- 先检查:
  - 是否手动设置了错误的 `CUDA_HOME`
  - README / 文档示例是不是写得过于具体
  - 安装脚本有没有在入口做路径真实性校验

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 在 Blackwell 机器上用可工作的版本组合重新安装 `pytorch3d`

### 现象
- 用户希望按一套已知可工作的 Blackwell 参考方案重新安装 `pytorch3d`.
- 当前机器真实现场是:
  - GPU: `NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - CUDA toolkit: `/usr/local/cuda` -> `cuda-12.8`
- 用户参考方案里的 `CUDA_HOME=/usr/local/cuda-12.9` 与现场不一致, 不能直接照抄.

### 原因
- 已验证结论:
  - 这台机器不存在 `/usr/local/cuda-12.9`
  - 当前可用 toolkit 根目录是 `/usr/local/cuda`
- 因此, 即使版本路线参考用户方案, 也必须把硬编码路径换成现场真实路径.
- 同时, 旧 Pixi 环境里的 PyTorch 组合较旧, 不适合作为本轮 Blackwell 安装基线.

### 修复
- 在当前 Pixi 环境里覆盖升级:
  - `torch==2.7.0+cu128`
  - `torchvision==0.22.0+cu128`
  - `torchaudio==2.7.0+cu128`
- 使用:
  - `CUDA_HOME=/usr/local/cuda`
  - `TORCH_CUDA_ARCH_LIST=12.0`
  - `CC=/usr/bin/g++`
  - `CXX=/usr/bin/g++`
  - `CUDAHOSTCXX=/usr/bin/g++`
- 带代理执行:
  - `pixi run python -m pip install -v --force-reinstall --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable"`

### 验证
- `pixi run python -c "import torch; print(...)" `
  - `torch 2.7.0+cu128`
  - `torch CUDA 12.8`
  - `cuda available True`
- `pixi run python -c "import pytorch3d; print(...)" `
  - `pytorch3d OK 0.7.8`
- `pixi run python -c "from pytorch3d.ops import knn_points; print(...)" `
  - `ops import OK knn_points`
- `OMP_NUM_THREADS=1 pixi run python -c "... knn_points(...)" `
  - `knn dists shape (1, 8, 2)`
  - `knn idx shape (1, 8, 2)`
  - `knn device cuda:0`

### 复盘提醒
- 用户提供的“可工作版本组合”可以作为方向参考, 但路径类参数绝不能机械照抄.
- 在 Blackwell 现场, 真正起作用的是:
  - 正确的 PyTorch 版本组合
  - 正确的 `TORCH_CUDA_ARCH_LIST`
  - 与本机真实 toolkit 一致的 `CUDA_HOME`
- 另外, 当前是对 Pixi 环境做的覆盖式安装, 不是已经固化到 `pixi.toml` 的声明式状态.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 将 Blackwell 成功组合写回 `pixi.toml` 时, 发现 conda `pytorch-cuda 12.8.*` 无候选包

### 现象
- 用户要求把已验证通过的 `torch 2.7.0+cu128` 组合正式写回 `pixi.toml`.
- 第一版写法沿用了原项目思路, 继续使用 conda:
  - `pytorch = "2.7.0.*"`
  - `torchvision = "0.22.0.*"`
  - `torchaudio = "2.7.0.*"`
  - `pytorch-cuda = "12.8.*"`
- 但执行 `pixi install` 后直接失败:
  - `No candidates were found for pytorch-cuda 12.8.*`

### 原因
- 已验证结论:
  - 当前项目 channels 下不存在可供 Pixi 求解的 conda `pytorch-cuda 12.8.*` 候选包.
- 所以问题不是:
  - TOML 语法写错
  - `pixi install` 没走代理
  - 运行时 GPU 不兼容
- 真正的问题是:
  - 当前成功现场使用的是 PyTorch 官方 `cu128` wheel
  - 但第一版 manifest 仍试图用 conda `pytorch-cuda` 去描述这套来源

### 修复
- 从 `[dependencies]` 中移除:
  - `pytorch`
  - `torchvision`
  - `torchaudio`
  - `pytorch-cuda`
- 改为在 `[pypi-dependencies]` 中显式固定:
  - `torch = { version = "==2.7.0", index = "https://download.pytorch.org/whl/cu128" }`
  - `torchvision = { version = "==0.22.0", index = "https://download.pytorch.org/whl/cu128" }`
  - `torchaudio = { version = "==2.7.0", index = "https://download.pytorch.org/whl/cu128" }`
- 再执行 `pixi install`, 让 `pixi.lock` 与环境一起刷新.

### 验证
- `env ... pixi install`
  - 结果: `✔ The default environment has been installed.`
- `rg -n "download\\.pytorch\\.org/whl/cu128" pixi.lock`
  - 已命中 `torch-2.7.0+cu128`
- `pixi run python -m pip show torch torchvision torchaudio pytorch3d`
  - `torch 2.7.0+cu128`
  - `torchvision 0.22.0+cu128`
  - `torchaudio 2.7.0+cu128`
  - `pytorch3d 0.7.8`
- `OMP_NUM_THREADS=1 pixi run python - <<'PY' ...`
  - `cuda_available True`
  - `knn_device cuda:0`

### 复盘提醒
- 当你要把“现场成功的 PyPI wheel 组合”写回 Pixi 时, 不要默认认为 conda 会有完全对应的 `pytorch-cuda` 候选包.
- 先让 solver 说话:
  - 如果 conda 路线无候选包, 就应该直接切到 Pixi 官方支持的 `pypi-dependencies + per-package index` 方案.
- 这次真正被证明可复现的, 不是“conda 12.8”, 而是“PyTorch 官方 `cu128` wheel 来源”.

## [2026-03-31 16:21:52 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] 任务名称: 修复 rendering_4D_control_maps.py 因 kornia 顶层导入触发 flash_attn ABI 报错

### 现象
- single_image_multi_trajectory.py 在调用 rendering_4D_control_maps.py 时失败.
- 失败堆栈表面上停在:
  - from kornia.geometry.depth import depth_to_3d_v2
- 继续展开后实际落到:
  - flash_attn_2_cuda.cpython-311-x86_64-linux-gnu.so: undefined symbol: _ZN3c105ErrorC2ENS_14SourceLocationESs

### 原因
- 已验证:
  - flash_attn 在当前 torch 2.7.0+cu128 环境下单独导入就会失败.
  - kornia 0.8.0 的 __init__ 会无条件导入 feature/lightglue.
  - lightglue.py 又会继续导入 flash_attn.
- 但 rendering_4D_control_maps.py 的真实需求只是 depth_to_3d_v2 这一个几何反投影函数.
- 所以真正的问题不是“脚本需要 flash_attn 却没装好”, 而是“脚本被第三方包的顶层宽导入副作用拖进了一个无关的坏依赖”.

### 修复
- 删除 rendering_4D_control_maps.py 顶部的:
  - from kornia.geometry.depth import depth_to_3d_v2
- 在脚本内本地实现 depth_to_3d_v2_compatible:
  - 用 torch.meshgrid + pinhole intrinsics 完成像素到相机坐标系的反投影
  - 只覆盖当前脚本真实使用的几何能力
- 将背景点云构建处改为调用本地 helper.
- 新增 tests/test_rendering_4d_control_maps.py:
  - 验证模块导入不再被 kornia / flash_attn 卡死
  - 验证反投影几何结果正确

### 验证
- OMP_NUM_THREADS=1 pixi run pytest tests/test_rendering_4d_control_maps.py -q
  - 结果: 2 passed in 2.14s
- OMP_NUM_THREADS=1 pixi run python -c "import inference.rendering_4D_control_maps"
  - 结果: 导入成功
- OMP_NUM_THREADS=1 pixi run python inference/rendering_4D_control_maps.py --png_path demo_data/my7/d.png --npz_path demo_data/my7/shared/estimated_depth/depth_intrinsics.npz --mask_dir demo_data/my7/shared/foreground_masks/masks --trajectory_npz demo_data/my7/11/custom_camera_trajectory.npz --ellipsoid_json demo_data/my7/11/custom_3D_gaussian_trajectory.json --output_dir demo_data/my7/11/rendering_4D_maps --device cuda --point_size 0.005 --fps 16 --render_batch_size 27 --target_height 720 --target_width 1280
  - 结果: Rendering complete

### 复盘提醒
- 以后遇到“导一个很小的几何函数却炸在别的加速库上”时, 不要只盯着表层 import 语句.
- 先拆成两层问题:
  - 环境里坏掉的可选依赖是什么
  - 当前脚本是否真的应该依赖它
- 如果答案是“不应该”, 优先收窄脚本依赖边界, 再决定是否另行修环境.

## [2026-03-31 16:37:23 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] 任务名称: 修复 flash_attn 在 torch 升级后的 ABI 失配与安装脚本误判

### 现象
- 当前环境直接 import flash_attn 会报:
  - undefined symbol: _ZN3c105ErrorC2ENS_14SourceLocationESs
- 但 pixi run install-flash-attn 旧逻辑仍会直接输出“已安装, 跳过重复安装”.

### 原因
- 旧 flash_attn 扩展是在之前的 torch ABI 现场下产生的, 与当前 torch 2.7.0+cu128 不兼容.
- scripts/install_flash_attn.sh 只检查 importlib.metadata.version("flash-attn"), 没有验证运行时 import 健康度.
- 所以它会把“坏掉但还留着 dist-info 的包”误判成可用.

### 修复
- 修改 scripts/install_flash_attn.sh:
  - 已安装并且 import 成功才跳过
  - 已安装但 import 失败则自动重编
  - 支持 FLASH_ATTN_FORCE_REINSTALL=1
  - 重编时使用 no-build-isolation、no-deps、no-binary flash-attn、no-cache-dir、force-reinstall
- 新增 tests/test_install_flash_attn_script.py 保护上述行为.
- 在真实环境中卸载旧 flash_attn 后, 以 CUDA_HOME=/usr/local/cuda 和 FLASH_ATTN_CUDA_ARCHS=120 重新源码编译.

### 验证
- bash -n scripts/install_flash_attn.sh
- OMP_NUM_THREADS=1 pixi run pytest tests/test_install_flash_attn_script.py -q
  - 结果: 3 passed in 0.18s
- 真实环境:
  - Successfully installed flash-attn-2.8.3
  - import flash_attn 成功
  - import kornia 成功
  - install-flash-attn 健康跳过成功

### 复盘提醒
- 以后只要升级了 torch, 就不要把“flash_attn 发行版元数据还在”当成它仍然可用的证据.
- 对这类 torch CUDA 扩展, import 成功才是最低限度的健康线.
