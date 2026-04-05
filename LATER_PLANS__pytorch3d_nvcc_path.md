# 后续计划: `pytorch3d` 构建错误引用不存在的 `nvcc`

## [2026-03-31 12:39:27 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 审计其它重型安装脚本的显式路径校验
- 现状:
  - 本轮已经在 `install-pytorch3d.sh` 上补齐了显式 `CUDA_HOME` 路径校验.
  - 但 `bootstrap` 里还有其它会触发 CUDA / C++ 构建的安装脚本.
- 建议:
  - 后续审计 `install-grounded-sam2.sh`、`install-grounding-dino` 等入口.
  - 看它们是否也允许显式 CUDA / compiler 覆盖值, 以及是否缺少同类前置校验.
- 价值:
  - 可以把这次“坏路径透传到深层构建”的问题, 从单点修复变成统一规则.

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 将 Blackwell 可工作组合固化到声明式环境
- 现状:
  - 本轮成功安装采用的是“覆盖式 pip 安装到现有 Pixi 环境”.
  - `pixi.toml` 仍保留旧的 `torch 2.3.1.* / pytorch-cuda 12.1.*` 约束.
- 建议:
  - 如果项目后续要稳定支持 Blackwell, 需要评估并决定是否把当前可工作的 `torch / torchvision / torchaudio / pytorch3d` 组合写回 `pixi.toml` 或补充专门的 Blackwell 安装入口.
- 价值:
  - 避免后续 `pixi install`、重建环境或 CI 重放时把本轮成功组合覆盖回旧版本.

## [2026-03-31 13:06:37 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 清理 `OMP_NUM_THREADS=0` 的环境噪音
- 现状:
  - 当前 `pixi run env` 明确显示 `OMP_NUM_THREADS=0`.
  - 这会让 Python 命令先输出 `libgomp: Invalid value for environment variable OMP_NUM_THREADS`.
- 建议:
  - 后续追查这个变量的来源, 可能在 shell 初始化、Pixi 任务包装或外层调度环境.
  - 至少应修正为一个有效正整数, 或取消这个默认注入.
- 价值:
  - 减少运行日志噪音.
  - 避免把环境级警告误判成 CUDA / PyTorch3D 安装问题.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 进展记录: “将 Blackwell 可工作组合固化到声明式环境” 已完成
- 结果:
  - `pixi.toml` 已改为通过 PyTorch 官方 `cu128` index 声明 `torch / torchvision / torchaudio`.
  - `pixi.lock` 已刷新.
  - 运行时与最小 CUDA `knn_points` 验证已通过.
- 说明:
  - 上一条“将 Blackwell 可工作组合固化到声明式环境”可视为已落地完成.

## [2026-03-31 15:10:45 UTC] [Session ID: 019d43e0-6da5-7a33-910f-1a81ae037763] 评估 `transformers==4.57.0` 的 yanked 风险
- 现状:
  - `pixi install` 明确警告:
    - ``transformers==4.57.0` is yanked (reason: "Error in the setup causing installation issues")`
- 建议:
  - 后续确认项目是否必须锁定这个版本.
  - 如果没有强依赖理由, 建议寻找一个未被 yanked 的等价版本并补一次兼容性验证.
- 价值:
  - 降低后续安装或重建环境时踩上游已知问题版本的风险.

## [2026-03-31 16:21:52 UTC] [Session ID: 479d2a22-a939-4b0b-a4a5-b682a4a82617] 清理 flash_attn 的 ABI 失配环境
- 现状:
  - 当前渲染脚本已经不再依赖 flash_attn, 用户现场渲染命令已恢复.
  - 但环境里直接执行 import flash_attn 仍会报:
    - undefined symbol: _ZN3c105ErrorC2ENS_14SourceLocationESs
- 建议:
  - 后续单独核查 flash_attn 是旧 wheel 残留, 还是旧 torch 版本下编出来的本地扩展.
  - 再决定是移除它, 还是按当前 torch 2.7.0+cu128 / CUDA 12.8 重新编译.
- 价值:
  - 避免以后其它真正依赖 flash_attn 的路径再次踩到同一个 ABI 雷.

## [2026-03-31 16:37:23 UTC] [Session ID: 2b367480-3f87-4242-8b24-ffdb2788e798] 进展记录: “清理 flash_attn 的 ABI 失配环境” 已完成
- 结果:
  - 当前环境中的 flash_attn 已重新源码编译.
  - import flash_attn / import kornia 已恢复正常.
  - install-flash-attn 也已具备健康检查, 不会再把坏包静默跳过.
