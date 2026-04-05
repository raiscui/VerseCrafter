# 工作日志: `pytorch3d` 构建错误引用不存在的 `nvcc`

## [2026-03-31 12:39:27 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 修复 `install-pytorch3d` 对坏 `CUDA_HOME` 路径缺少前置校验

### 任务内容
- 排查 `pytorch3d` 构建阶段为什么会调用不存在的 `/usr/local/cuda-12.9/bin/nvcc`.
- 修复安装入口, 让显式错误的 CUDA toolkit 路径在真正 clone / pip build 前就被清晰拦截.
- 同步更新 README 与回归测试, 避免同类误导再次出现.

### 完成过程
- 先回读 `__bootstrap_hang` 历史记录, 确认这次问题已经从“高 CPU / 像卡住”转成“坏工具链路径”.
- 再读取:
  - `scripts/install_pytorch3d.sh`
  - `.envrc`
  - `README.md`
  - `tests/test_install_pytorch3d_script.py`
- 用动态证据确认:
  - 当前 shell / `direnv` / Pixi 环境没有把 `PYTORCH3D_CUDA_HOME` 设成 `12.9`
  - 当前机器实际存在的是 `cuda-12.8`, 不存在 `cuda-12.9`
  - `torch.utils.cpp_extension._find_cuda_home()` 不会自己拼 `/usr/local/cuda-12.9`
- 最后实施修复:
  - 为 `scripts/install_pytorch3d.sh` 增加显式 `CUDA_HOME` 校验与现场候选提示
  - 把校验前移到 clone 之前
  - 把 README 的固定 `cuda-12.9` 示例改成基于真实 `nvcc` 的写法
  - 调整测试, 让“坏路径提前失败”成为受保护行为

### 总结感悟
- 这类安装脚本最危险的不是“推断失败”, 而是“坏路径被沉默透传”.
- 对工具链路径来说, 与其让编译阶段报一个远处的 `ENOENT`, 不如在入口就把“你给的目录里根本没有 `bin/nvcc`”说透.

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 按 Blackwell 参考方案完成 `pytorch3d` 源码安装

### 任务内容
- 在当前 Pixi 环境里按用户给出的 Blackwell 路线切换 PyTorch 版本组合.
- 使用本机真实 CUDA toolkit 和代理网络重新源码安装 `pytorch3d`.
- 做导入与最小 CUDA 算子验收, 确认不是“只装上包但扩展不可用”.

### 完成过程
- 先确认现场硬件和工具链:
  - GPU 为 `NVIDIA RTX PRO 6000 Blackwell Server Edition`
  - `/usr/local/cuda` 指向真实存在的 `cuda-12.8`
- 再覆盖升级 Python 包:
  - `torch==2.7.0+cu128`
  - `torchvision==0.22.0+cu128`
  - `torchaudio==2.7.0+cu128`
- 之后按用户给出的思路, 但改成现场可用路径执行源码构建:
  - `CUDA_HOME=/usr/local/cuda`
  - `TORCH_CUDA_ARCH_LIST=12.0`
  - 带代理安装 `git+https://github.com/facebookresearch/pytorch3d.git@stable`
- 最后做三层验收:
  - `torch` / CUDA 可见性验收
  - `pytorch3d` 与 `pytorch3d.ops` 导入验收
  - `knn_points` 最小 GPU 调用验收

### 总结感悟
- 用户给的 Blackwell 方案方向是对的, 但路径参数必须服从现场实际.
- 对这类“版本组合 + 本机工具链”问题, 真正有用的是:
  - 明确版本
  - 明确架构
  - 明确真实 `CUDA_HOME`
  - 最后再用一个最小 CUDA op 把“装好了”和“真能跑”区分开.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 任务名称: 将 Blackwell 可工作组合固化到 `pixi.toml` / `pixi.lock`

### 任务内容
- 把已经在现场验证通过的 `torch 2.7.0+cu128` 组合从“临时覆盖安装”收口成 Pixi 的声明式配置.
- 保证后续 `pixi install` 或重建环境时, 不会再回退到旧的 `torch 2.3.1 + cu121`.
- 同步修正文档和脚本注释里的旧口径.

### 完成过程
- 先按最直觉的方向尝试, 把 `torch` 组合继续写成 conda `pytorch + pytorch-cuda 12.8.*`.
- 然后立即用 `pixi install` 做动态证伪.
  - 结果明确失败:
    - `No candidates were found for pytorch-cuda 12.8.*`
- 据此调整方案:
  - 把 `torch / torchvision / torchaudio` 从 conda 依赖迁移到 Pixi 的 `[pypi-dependencies]`
  - 为每个包显式固定 `https://download.pytorch.org/whl/cu128` index
- 再执行:
  - `pixi install`
  - `pixi.lock` 检查
  - 运行时导入与最小 CUDA `knn_points` 调用
- 最后同步:
  - `README.md`
  - `scripts/install_flash_attn.sh`

### 总结感悟
- 新 CUDA 组合不一定会在 conda `pytorch-cuda` 路线上同步提供候选包.
- 真正稳的做法不是执着于“全部都走 conda”, 而是让声明式配置忠实复现现场已验证成功的来源.
- 对当前项目来说, 现在最关键的收获是:
  - `pixi.toml`
  - `pixi.lock`
  - 运行时环境
  这三者终于被重新拉回同一个真相源上了.

## [2026-03-31 16:21:52 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] 任务名称: 修复 rendering_4D_control_maps.py 被 kornia / flash_attn 导入链阻断

### 任务内容
- 排查 single_image_multi_trajectory.py 在渲染阶段调用 rendering_4D_control_maps.py 时的运行期崩溃.
- 区分“环境里的 flash_attn ABI 失配”和“渲染脚本依赖边界过宽”这两个问题.
- 让用户日志中的真实渲染命令恢复可运行.

### 完成过程
- 先用最小实验分别验证:
  - import flash_attn
  - import kornia
  - from kornia.geometry.depth import depth_to_3d_v2
  - import inference.rendering_4D_control_maps
- 再读取 kornia 0.8.0 源码, 确认它的 __init__ 会无条件带入 feature/lightglue, 进而触发 flash_attn.
- 同时读取 rendering_4D_control_maps.py, 确认它对 kornia 的唯一真实需求只是 depth_to_3d_v2 这一个几何函数.
- 最后把这段反投影逻辑本地化为 depth_to_3d_v2_compatible, 并补充回归测试.
- 验证时不仅跑了单测和模块导入, 还重跑了用户现场的一条真实渲染命令, 最终成功输出 Rendering complete.

### 总结感悟
- 这次真正修掉的不是 flash_attn 本身, 而是“一个不需要 flash_attn 的脚本却被它卡死”的依赖边界错误.
- 对运行脚本来说, 最稳的设计不是把可选加速库都装好, 而是只依赖自己真实需要的那一小段能力.

## [2026-03-31 16:37:23 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] 任务名称: 重编 flash_attn 并修复安装入口的健康检查缺陷

### 任务内容
- 重新编译当前 Pixi 环境中的 flash_attn, 消除它和 torch 2.7.0+cu128 之间的 ABI 失配.
- 修正 install_flash_attn.sh 只看“是否装过”而不看“是否还能导入”的缺陷.
- 补回归测试, 防止以后 torch 升级后再次静默跳过坏包.

### 完成过程
- 先读取 scripts/install_flash_attn.sh、包元数据和官方 README 的安装建议.
- 确认根因不是“缺少 flash_attn”, 而是“旧 flash_attn 已装但 .so 和新 torch ABI 不匹配”.
- 然后修改脚本:
  - 已安装且可导入才跳过
  - 已安装但导入失败则重编
  - 支持 FLASH_ATTN_FORCE_REINSTALL=1 强制重编
  - 明确走源码安装, 并在重编时禁用缓存
- 最后在真实环境中卸载旧包并重编, 再用 import flash_attn / import kornia / pixi run install-flash-attn 做验收.

### 总结感悟
- 对 CUDA 扩展来说, “包名还在 site-packages 里”远远不够.
- 真正可靠的健康检查必须至少经过一次 import, 否则 ABI 坏包会一直伪装成“已经安装”.
