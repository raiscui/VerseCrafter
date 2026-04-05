# 任务计划: `pytorch3d` 构建阶段错误引用不存在的 `nvcc`

## [2026-03-31 12:32:41 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 建立排查计划

### 目标
- 找出 `pytorch3d` 构建阶段为什么会尝试调用不存在的 `/usr/local/cuda-12.9/bin/nvcc`.
- 区分这是环境变量污染, 还是仓库安装脚本 / 文档配置错误.
- 给出并验证一个稳定的修复路径, 让后续安装不再掉进同一个坑.

### 阶段
- [x] 阶段1: 回读默认上下文与 `bootstrap` 历史记录
- [ ] 阶段2: 阅读当前 `install-pytorch3d` 入口和相关配置
- [ ] 阶段3: 做最小动态验证, 确认错误路径来源
- [ ] 阶段4: 实施修复并验证
- [ ] 阶段5: 回写记录并交付

### 关键问题
1. 当前报错中的 `/usr/local/cuda-12.9/bin/nvcc` 是从哪里来的?
2. 本机真实可用的 `nvcc` / `CUDA_HOME` 是什么?
3. 修复应该落在安装脚本, 还是环境默认值 / 文档说明?

### 做出的决定
- 决定1: 先不猜 root cause, 先找出错误路径的唯一来源.
- 决定2: 继续沿用 `__bootstrap_hang` 的历史证据, 但本轮单独开新支线, 避免把“性能问题”和“路径错误”混写.
- 决定3: 优先做最小可证伪实验, 例如检查环境变量、脚本逻辑、`which nvcc` 与 `torch.utils.cpp_extension.CUDA_HOME`.

### 当前状态
- **目前在阶段2**: 正在读取 `install-pytorch3d` 入口和 CUDA 相关配置.

## [2026-03-31 12:35:33 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 研究完成, 进入修复设计

### 阶段状态更新
- [x] 阶段1: 回读默认上下文与 `bootstrap` 历史记录
- [x] 阶段2: 阅读当前 `install-pytorch3d` 入口和相关配置
- [x] 阶段3: 做最小动态验证, 确认错误路径来源
- [ ] 阶段4: 实施修复并验证
- [ ] 阶段5: 回写记录并交付

### 已验证结论
- 当前仓库脚本不会自行生成 `/usr/local/cuda-12.9`.
- 当前 shell / `.envrc` / Pixi 环境也没有把 `PYTORCH3D_CUDA_HOME` 设成 `12.9`.
- 当前机器实际存在的是 `cuda-12.8`, 不存在 `cuda-12.9`.
- `torch.utils.cpp_extension` 的源码已证实: 它只会看显式环境变量、`which nvcc` 和 `/usr/local/cuda`, 不会自己拼版本目录.

### 修复方向
- 在 `scripts/install_pytorch3d.sh` 中增加 CUDA toolkit 路径校验.
- 把 README 里的固定 `cuda-12.9` 示例改成基于真实 `nvcc` 的写法.
- 调整测试, 让“坏路径被早发现”成为受保护行为.

### 当前状态
- **目前在阶段4**: 准备修改脚本、README 与测试.

## [2026-03-31 12:39:27 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 修复与验证完成

### 阶段状态更新
- [x] 阶段1: 回读默认上下文与 `bootstrap` 历史记录
- [x] 阶段2: 阅读当前 `install-pytorch3d` 入口和相关配置
- [x] 阶段3: 做最小动态验证, 确认错误路径来源
- [x] 阶段4: 实施修复并验证
- [x] 阶段5: 回写记录并交付

### 已完成事项
- 已在 `scripts/install_pytorch3d.sh` 中加入显式 CUDA toolkit 路径校验.
- 已把校验前移到 clone 前, 避免错误配置时浪费网络和构建时间.
- 已更新 `.envrc` 注释与 README 说明, 去掉高风险的固定 `cuda-12.9` 示例.
- 已更新 `tests/test_install_pytorch3d_script.py`, 新增无效路径回归测试.

### 验证结果
- `bash -n scripts/install_pytorch3d.sh`
- `pixi run pytest tests/test_install_pytorch3d_script.py -q`
- 结果:
  - `3 passed in 0.16s`

### 当前状态
- **本轮任务已完成**: 可以向用户交付现象、结论、修复点与后续建议.

## [2026-03-31 12:47:02 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 按用户给出的 Blackwell 方案继续安装

### 新目标
- 按用户提供的可工作参考方案, 在当前 Pixi 环境中切到更适合 Blackwell 的 PyTorch 组合, 再重新源码安装 `pytorch3d`.

### 当前约束
- 用户参考方案使用:
  - `torch 2.7.0+cu128`
  - `TORCH_CUDA_ARCH_LIST=12.0`
  - `git+https://github.com/facebookresearch/pytorch3d.git@stable`
- 但这台机器当前真实存在的 CUDA toolkit 是 `12.8`, 不是 `12.9`.
- 当前项目 `pixi.toml` 仍固定:
  - `pytorch = 2.3.1.*`
  - `pytorch-cuda = 12.1.*`

### 做出的决定
- 决定1: 按用户选择执行“覆盖式安装”, 先不改 `pixi.toml`.
- 决定2: 将 `CUDA_HOME` 调整为这台机器真实存在的 `/usr/local/cuda` -> `cuda-12.8`.
- 决定3: 先核对官方安装矩阵, 再执行升级, 避免把用户参考方案里的具体版本号机械照抄到不匹配的现场.

### 当前状态
- **目前在新阶段**: 正在核对 `torch 2.7.0 + cu128` 与 `pytorch3d@stable` 的官方安装路径.

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: Blackwell 方案安装与验收完成

### 阶段状态更新
- [x] 阶段1: 回读默认上下文与 `bootstrap` 历史记录
- [x] 阶段2: 阅读当前 `install-pytorch3d` 入口和相关配置
- [x] 阶段3: 做最小动态验证, 确认错误路径来源
- [x] 阶段4: 实施修复并验证
- [x] 阶段5: 回写记录并交付
- [x] 阶段6: 按用户给出的 Blackwell 组合做覆盖安装
- [x] 阶段7: 做源码构建后的导入与 CUDA 算子验收

### 已完成事项
- 已在当前 Pixi 环境中升级:
  - `torch==2.7.0+cu128`
  - `torchvision==0.22.0+cu128`
  - `torchaudio==2.7.0+cu128`
- 已使用本机真实 CUDA toolkit:
  - `CUDA_HOME=/usr/local/cuda`
  - 实际指向 `cuda-12.8`
- 已按 Blackwell 架构设置:
  - `TORCH_CUDA_ARCH_LIST=12.0`
- 已通过代理执行源码安装:
  - `git+https://github.com/facebookresearch/pytorch3d.git@stable`
- 已确认安装结果:
  - `pytorch3d 0.7.8`

### 验证结果
- `pixi run python -c "import torch; ..."`
  - `torch 2.7.0+cu128`
  - `torch CUDA 12.8`
  - `cuda available True`
  - `device NVIDIA RTX PRO 6000 Blackwell Server Edition`
- `pixi run python -c "import pytorch3d; ..."`
  - `pytorch3d OK 0.7.8`
- `pixi run python -c "from pytorch3d.ops import knn_points; ..."`
  - `ops import OK knn_points`
- `OMP_NUM_THREADS=1 pixi run python -c "... knn_points(...)" `
  - `knn dists shape (1, 8, 2)`
  - `knn idx shape (1, 8, 2)`
  - `knn device cuda:0`

### 当前状态
- **本轮按用户指定方案的安装已完成**: 当前环境已经切到 Blackwell 可工作的组合并通过最小 CUDA 扩展验收.
- **剩余风险已识别但未落地**:
  - 当前是对 Pixi 环境做的覆盖式安装, `pixi.toml` 仍保留旧的 `torch 2.3.1 / cu121` 约束.
  - 若后续重新 `pixi install` 或重建环境, 这套组合有被回滚的风险.

## [2026-03-31 14:43:55 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: 用户要求将可工作组合写回 `pixi.toml`

### 新目标
- 将已经在当前 Blackwell 现场验证通过的 PyTorch 组合写回 `pixi.toml`.
- 尽量让后续 `pixi install` / 重建环境时保持与当前成功现场一致.
- 如有必要, 一并同步 `pixi.lock` 与相关文档口径.

### 当前疑问
1. `pixi.toml` 中 `pytorch` 系列版本约束应该精确写到什么粒度, 才既稳定又不至于过度脆弱?
2. 写回后是否需要同步刷新 `pixi.lock`, 才能让声明式环境真正落地?
3. README 当前对“仓库仍 pinned 到旧 torch 组合”的说明是否需要同步更正?

### 当前状态
- **目前在新阶段**: 正在读取 `pixi.toml`、相关文档与 Pixi 配置语法, 准备实施收口修改.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] [记录类型]: `pixi.toml` 声明式收口完成

### 阶段状态更新
- [x] 阶段1: 回读默认上下文与 `bootstrap` 历史记录
- [x] 阶段2: 阅读当前 `install-pytorch3d` 入口和相关配置
- [x] 阶段3: 做最小动态验证, 确认错误路径来源
- [x] 阶段4: 实施修复并验证
- [x] 阶段5: 回写记录并交付
- [x] 阶段6: 按用户给出的 Blackwell 组合做覆盖安装
- [x] 阶段7: 做源码构建后的导入与 CUDA 算子验收
- [x] 阶段8: 将已验证组合写回 `pixi.toml` 与 `pixi.lock`

### 关键转折
- 第一版收口方案把 `torch` 组合继续写成 conda 依赖:
  - `pytorch = 2.7.0.*`
  - `torchvision = 0.22.0.*`
  - `torchaudio = 2.7.0.*`
  - `pytorch-cuda = 12.8.*`
- 但 `pixi install` 的动态证据直接否定了这条路线:
  - `No candidates were found for pytorch-cuda 12.8.*`
- 因此最终改为:
  - 将 `torch / torchvision / torchaudio` 移到 `[pypi-dependencies]`
  - 并为每个包显式固定 `https://download.pytorch.org/whl/cu128` index

### 已完成事项
- 已更新 `pixi.toml`, 不再依赖不存在候选包的 conda `pytorch-cuda 12.8.*`.
- 已刷新 `pixi.lock`, 将 `torch 2.7.0+cu128`、`torchvision 0.22.0+cu128`、`torchaudio 2.7.0+cu128` 锁定到 PyTorch `cu128` wheel 来源.
- 已同步更新 README 中关于 Blackwell / `TORCH_CUDA_ARCH_LIST` 的说明.
- 已修正 `scripts/install_flash_attn.sh` 中过期的 `torch 2.3.1` 注释口径.

### 验证结果
- `env ... pixi install`
  - 结果: `✔ The default environment has been installed.`
- `rg -n "download\\.pytorch\\.org/whl/cu128" pixi.lock`
  - 已命中 `torch-2.7.0+cu128` wheel 来源
- `OMP_NUM_THREADS=1 pixi run python - <<'PY' ...`
  - `torch 2.7.0+cu128`
  - `torch_cuda 12.8`
  - `cuda_available True`
  - `pytorch3d 0.7.8`
  - `knn_device cuda:0`

### 当前状态
- **本轮“写回 `pixi.toml`”任务已完成**: 当前 manifest、lockfile 与运行时现场已经重新对齐.
- **新增但不阻塞的观察**:
  - `pixi install` 过程中出现 `transformers==4.57.0` 被 upstream yanked 的警告, 需要后续单独评估是否继续固定这个版本.

## [2026-03-31 16:14:30 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] [记录类型]: 进入运行期 flash_attn / kornia 导入故障排查

### 新目标
- 解释为什么 single_image_multi_trajectory.py 在渲染阶段进入 rendering_4D_control_maps.py 后失败.
- 区分这是 flash-attn 与当前 torch 的 ABI 不匹配, 还是脚本不必要地触发了 kornia 的宽导入副作用.
- 给出并验证一条稳定修复路径, 让多轨迹渲染能继续执行.

### 阶段
- [x] 阶段1: 回读历史支线与已验证环境事实
- [ ] 阶段2: 阅读 rendering_4D_control_maps.py 与相关依赖边界
- [ ] 阶段3: 做最小动态验证, 确认失败发生在什么导入链路
- [ ] 阶段4: 实施最合适的修复
- [ ] 阶段5: 运行最小验收与回写记录

### 关键问题
1. 当前失败是不是由 flash_attn 与 torch 2.7.0+cu128 的二进制 ABI 不匹配直接引起?
2. rendering_4D_control_maps.py 是否真的需要完整导入 kornia, 还是只需要一个深度工具函数?
3. 更稳的修复点应该放在运行脚本自身的导入边界, 还是放在重编 flash-attn?

### 做出的决定
- 决定1: 先严格按 现象 -> 假设 -> 验证 的顺序推进, 暂不直接重装任何重型依赖.
- 决定2: 先验证脚本是否能通过收窄导入边界避开无关依赖, 因为这条路径更接近脚本真实需求.
- 决定3: 如果脚本确实依赖当前 kornia 导入链必须经过 flash_attn, 再转向重编 flash-attn.

### 当前状态
- **目前在阶段2**: 正在读取渲染脚本、依赖版本和最小导入链, 准备做可证伪实验.

## [2026-03-31 16:17:12 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] [记录类型]: 根因调查完成, 进入脚本级修复

### 阶段状态更新
- [x] 阶段1: 回读历史支线与已验证环境事实
- [x] 阶段2: 阅读 rendering_4D_control_maps.py 与相关依赖边界
- [x] 阶段3: 做最小动态验证, 确认失败发生在什么导入链路
- [ ] 阶段4: 实施最合适的修复
- [ ] 阶段5: 运行最小验收与回写记录

### 已验证结论
- flash_attn 在当前环境中单独导入就会失败, 说明 ABI 失配是真实存在的运行时问题.
- kornia 0.8.0 的 __init__ 会无条件拉入 feature/lightglue, 进一步触发 flash_attn 导入.
- rendering_4D_control_maps.py 对 kornia 的真实需求只有 depth_to_3d_v2 这一处几何反投影.
- 因此, 当前更合适的修复点是先缩小脚本依赖边界, 避免无关的可选特性阻断渲染流程.

### 当前状态
- **目前在阶段4**: 准备在渲染脚本内实现本地 depth 反投影 helper, 并补回归测试.

## [2026-03-31 16:21:52 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] [记录类型]: 修复与验收完成

### 阶段状态更新
- [x] 阶段1: 回读历史支线与已验证环境事实
- [x] 阶段2: 阅读 rendering_4D_control_maps.py 与相关依赖边界
- [x] 阶段3: 做最小动态验证, 确认失败发生在什么导入链路
- [x] 阶段4: 实施最合适的修复
- [x] 阶段5: 运行最小验收与回写记录

### 已完成事项
- 已在 rendering_4D_control_maps.py 中移除对 kornia 的运行时导入依赖.
- 已本地实现 depth_to_3d_v2_compatible, 覆盖脚本实际需要的深度反投影逻辑.
- 已新增 tests/test_rendering_4d_control_maps.py, 锁住模块导入和几何行为.
- 已用用户现场的一条真实渲染命令完成动态复验.

### 验证结果
- OMP_NUM_THREADS=1 pixi run pytest tests/test_rendering_4d_control_maps.py -q
  - 结果: 2 passed in 2.14s
- OMP_NUM_THREADS=1 pixi run python -c "import inference.rendering_4D_control_maps"
  - 结果: 导入成功
- OMP_NUM_THREADS=1 pixi run python inference/rendering_4D_control_maps.py ...
  - 结果: Rendering complete

### 当前状态
- **本轮运行期导入故障已修复**: 用户日志中的渲染命令已能继续运行到完成.
- **仍有单独环境问题待后续处理**:
  - flash_attn 直接导入仍会因 ABI 不匹配失败, 但它不再阻断这个渲染脚本.

## [2026-03-31 16:26:53 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] [记录类型]: 进入 flash_attn 重编阶段

### 新目标
- 让当前 Pixi 环境中的 flash_attn 与 torch 2.7.0+cu128 / CUDA 12.8 / sm_120 重新对齐.
- 清除现有 ABI 不匹配的 flash_attn 扩展, 再完成一次可验证的源码重编.
- 用最小导入验收确认 import flash_attn 与 import kornia 都恢复正常.

### 阶段
- [x] 阶段1: 回读支线状态与上轮动态证据
- [ ] 阶段2: 阅读 install_flash_attn 入口、当前安装来源与官方构建建议
- [ ] 阶段3: 清理旧安装并执行重编
- [ ] 阶段4: 做导入与脚本级验收
- [ ] 阶段5: 回写记录并交付

### 关键问题
1. 当前坏掉的 flash_attn 是来自旧 wheel, 还是旧 torch 环境下残留的本地编译产物?
2. 仓库现有 scripts/install_flash_attn.sh 是否已经和 torch 2.7.0+cu128 对齐?
3. 重编后最小验收应该包含哪些层次, 才能证明 ABI 问题真的消失?

### 做出的决定
- 决定1: 先读脚本和现场元数据, 不直接盲目 force-reinstall.
- 决定2: 重编前先卸掉现有 flash_attn, 避免旧 `.so` 残留干扰结果.
- 决定3: 验收至少要覆盖 import flash_attn、import kornia 和一个受影响脚本导入.

### 当前状态
- **目前在阶段2**: 正在读取 flash_attn 安装脚本、环境元数据和官方构建建议.

## [2026-03-31 16:31:06 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] [记录类型]: 进入真实环境重编

### 阶段状态更新
- [x] 阶段1: 回读支线状态与上轮动态证据
- [x] 阶段2: 阅读 install_flash_attn 入口、当前安装来源与官方构建建议
- [ ] 阶段3: 清理旧安装并执行重编
- [ ] 阶段4: 做导入与脚本级验收
- [ ] 阶段5: 回写记录并交付

### 当前状态
- **目前在阶段3**: 准备卸载当前 ABI 不匹配的 flash_attn, 然后用修好的安装入口重新源码编译.

## [2026-03-31 16:37:23 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] [记录类型]: flash_attn 重编与验收完成

### 阶段状态更新
- [x] 阶段1: 回读支线状态与上轮动态证据
- [x] 阶段2: 阅读 install_flash_attn 入口、当前安装来源与官方构建建议
- [x] 阶段3: 清理旧安装并执行重编
- [x] 阶段4: 做导入与脚本级验收
- [x] 阶段5: 回写记录并交付

### 已完成事项
- 已修复 scripts/install_flash_attn.sh 的短路逻辑, 不再把“装了但 import 已坏”的现场误判成成功.
- 已新增 tests/test_install_flash_attn_script.py, 锁住健康跳过、坏包重编和强制重编三种行为.
- 已在真实 Pixi 环境中卸载旧 flash_attn 并重新源码编译.
- 已确认 flash_attn、kornia 和 rendering_4D_control_maps.py 都可导入.

### 验证结果
- bash -n scripts/install_flash_attn.sh
  - 结果: 通过
- OMP_NUM_THREADS=1 pixi run pytest tests/test_install_flash_attn_script.py -q
  - 结果: 3 passed in 0.18s
- 真实环境重编后:
  - Successfully installed flash-attn-2.8.3
  - flash_attn import OK
  - kornia import OK
  - install-flash-attn skip OK

### 当前状态
- **本轮 flash_attn ABI 问题已完成修复**: 当前环境和安装入口都已经重新对齐.
