# 后续计划

## [2026-03-22 12:18:55 UTC] 改善 `single_image_multi_trajectory.py` 的“最终生效参数”可见性
- 现状: 用户即使传了自己以为正确的命令, 也不容易第一时间确认当前真正生效的是不是双卡参数.
- 建议: 后续在批处理入口显式打印并落盘以下信息:
  - 本轮 `manifest` 的核心运行参数摘要
  - 每个镜头 Step 6 是否走 `torchrun`
  - 关键参数如 `nproc_per_node`、`ulysses_degree`、`ring_degree`、`gpu_memory_mode`
- 价值: 能显著减少“明明以为在跑双卡, 其实实际进程是单卡”这类误判.

## [2026-03-27 09:58:40 UTC] 改善自动接力后异常中断时的状态回写与父子进程一致性
- 现状: 这次 `my4` 被自动接力启动后, 现场只剩两个 orphan `versecrafter_inference.py` worker, 但 `manifest` 仍停留在 `running`.
- 建议: 后续为单图多轨迹批处理补强以下能力:
  - 父进程退出时主动回收全部 Step 6 worker
  - 中断/异常退出时把 `manifest` 更新为明确的中止状态, 而不是一直保留 `running`
  - 提供一个官方的“停止当前批处理”命令或脚本, 避免手动按 PID 清理
- 价值: 能减少“GPU 还在跑, 但批处理主进程已经没了”这类误导场景.
