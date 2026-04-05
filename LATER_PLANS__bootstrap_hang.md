# 后续计划: `pixi run bootstrap` 高 CPU

## [2026-03-25 09:52:40 UTC] [Session ID: bootstrap_hang_20260325] 改善 `bootstrap` 可观察性与可控性
- 现状:
  - `bootstrap` 将多个源码安装步骤打包到一个别名里.
  - 用户只能看到一个总任务名, 不容易判断当前卡在 `flash-attn`、`grounding_dino` 还是 `pytorch3d`.
  - 仓库内没有统一的 `MAX_JOBS` 示例或分步执行建议.
- 建议:
  - 在 `README.md` 明确标出每个子任务的性质, 例如“会编译 CUDA 扩展 / 会 clone 源码 / 可能长时间高 CPU”.
  - 给出分步执行方案, 例如先 `pixi run install-grounded-sam2`, 再 `pixi run install-flash-attn`, 最后 `pixi run install-pytorch3d`.
  - 为 `flash-attn` 提供受控并行度示例, 例如 `MAX_JOBS=4`.
  - 视需求考虑新增轻量任务, 例如跳过最重的扩展编译, 方便先完成纯 Python 链路验证.
- 价值:
  - 能显著降低“命令卡死”的误判成本.
  - 也更适合在机器资源有限时逐段定位真正的慢点.
