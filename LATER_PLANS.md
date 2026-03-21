# 后续计划

## [2026-03-21 16:55:30 UTC] 改善 `xfuser` 初始化失败时的报错可读性
- 现状: `third_party/VideoX-Fun/videox_fun/dist/fuser.py` 会把任意 `xfuser` 导入异常统一改写成 `RuntimeError("xfuser is not installed.")`.
- 建议: 后续补一个小修复, 在报错里保留原始异常类型与摘要, 至少区分:
  - 真正未安装 `xfuser`
  - `xfuser` 已安装, 但导入阶段因为 CUDA / 依赖 / 环境问题失败
- 价值: 能显著减少误判和重复安装依赖的时间浪费.
