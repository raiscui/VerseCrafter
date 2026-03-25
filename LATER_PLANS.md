# 后续计划

## [2026-03-22 12:18:55 UTC] 改善 `single_image_multi_trajectory.py` 的“最终生效参数”可见性
- 现状: 用户即使传了自己以为正确的命令, 也不容易第一时间确认当前真正生效的是不是双卡参数.
- 建议: 后续在批处理入口显式打印并落盘以下信息:
  - 本轮 `manifest` 的核心运行参数摘要
  - 每个镜头 Step 6 是否走 `torchrun`
  - 关键参数如 `nproc_per_node`、`ulysses_degree`、`ring_degree`、`gpu_memory_mode`
- 价值: 能显著减少“明明以为在跑双卡, 其实实际进程是单卡”这类误判.
