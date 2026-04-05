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

## [2026-04-05 06:11:21 UTC] 平滑 `single_image_multi_trajectory.py` 生成视频的开头几帧
- 现状: `versecrafter_inference.py` 会把第一路 RGB control 的第 0 帧替换成原始输入图, 但第 1 帧立即切到渲染 control.
- 动态证据: 在 `demo_data/nt1`, `input -> ctrl1` 与 `gen0 -> gen1` 的相关系数达到 `0.9828`, 说明开头抖动和这段条件断层高度相关.
- 建议: 后续实现时优先比较这 3 种方案:
  - 前 `N` 帧 hold/ease-in 轨迹, 降低开场真实视差
  - 用输入图对前 `N` 帧 RGB control 做渐变混合, 不只替换第 0 帧
  - 暴露 `subject_ref_images` 或等价参考图路径, 给 GeoAda 更强的多帧参考锚点
- 价值: 能直接改善“第一秒不稳, 后面正常”的观感问题.

## [2026-04-05 07:18:09 UTC] 更新: 开头平滑方案的一期已落地
- 已完成:
  - 前 `N` 帧 hold/ease-in 轨迹
  - 当前默认实现为:
    - 前 2 帧 hold
    - 到第 5 帧追平原始轨迹
- 仍值得继续:
  - 用输入图对前几帧 RGB control 做渐变混合
  - 暴露 `subject_ref_images` 或等价参考图路径, 给 GeoAda 更强的多帧参考锚点
  - 如果后续需要更细调参, 再考虑把 lead-in 参数暴露成 CLI 选项
