# 后续计划

## [2026-03-14 17:19:00 UTC] pixi 完整环境落地

- 在具备 Linux CUDA 环境的机器上执行完整 `pixi install` 与 `pixi run bootstrap`.
- 若环境求解与源码扩展安装都稳定, 生成并提交 `pixi.lock`, 进一步提升环境复现性.
- 视结果决定是否把 `README_BLENDER.md` 中与服务端环境相关的提示也同步切到 `pixi`.

## [2026-03-15 11:15:00 UTC] 单图多轨迹批处理的 Step 6 模型复用优化

- 当前 `single_image_multi_trajectory.py` 每条轨迹都会单独启动一次 `versecrafter_inference.py`.
- 在 `model_cpu_offload_and_qfloat8` 模式下虽然已经能跑通, 但单条 10 step 仍接近 14 分钟, 主要时间花在模型加载与单进程推理上.
- 后续可考虑:
  - 让一个进程复用同一套已加载的 VerseCrafter 模型, 顺序消费多个 `rendering_maps_path`.
  - 或把 `versecrafter_inference.py` 抽出可复用函数入口, 由 batch orchestrator 直接循环调用.
- 这样可以明显减少 6 条轨迹的总耗时.

## [2026-03-15 12:46:40 UTC] 将“时间静止”条件沉淀为正式批处理参数模板

- 当前 0 号轨迹已经验证了:
  - 更强 frozen-in-time prompt
  - 更强 motion suppression negative prompt
  - `--num_inference_steps 40`
  能够稳定产出样本.
- 若用户确认效果足够接近“时间静止”, 后续可把这组参数沉淀为:
  - `single_image_multi_trajectory.py` 的显式 preset
  - 或 README 里的推荐“时间静止”命令模板
- 否则每次都只能靠手写长 prompt 复现, 容易漂.

## [2026-03-15 13:52:30 UTC] 为 MoGe 增加“优先使用本地缓存权重”的正式入口或文档

- 当前新场景验证暴露出:
  - 默认 `moge-2-vitl-normal` 远程下载很慢
  - 但本机往往已有 `moge-2-vitl` 的完整缓存
- 后续可考虑:
  - 在 README 里补一条 `--moge_pretrained <.../model.pt>` 的推荐写法
  - 或在脚本里增加更友好的本地缓存探测逻辑
- 这样后面做多场景快速验证时, 不会反复卡在 Step 1 权重拉取上.

## [2026-03-15 14:20:00 UTC] 让 MoGe 默认模型与当前下游契约显式对齐

- 当前事实:
  - 仓库默认 v2 模型还是 `moge-2-vitl-normal`
  - 但主工作流实际只消费 `depth` 和 `intrinsic`
  - `normal` 目前没有进入下游
- 后续可考虑:
  - 把默认值改成更贴近当前主链路的 `moge-2-vitl`
  - 或新增显式参数, 比如区分 `depth_only` 与 `depth_plus_normal`
  - 同步更新 README / API 文档, 讲清楚什么时候需要 `-normal`
- 这样可以减少默认下载体积与语义歧义, 也避免以后再次把“临时替代”误当成“官方等价”.

## [2026-03-15 14:52:00 UTC] 给 Step 6 结果补一个正式 compare 入口

- 当前 10 步 vs 40 步对比是通过手工复用同一份 `rendering_4D_maps`, 再额外写脚本生成:
  - contact sheet
  - side-by-side compare video
- 这个流程已经被证明很适合高成本场景下的 prompt / 步数快速验证.
- 后续可考虑把它正式收敛为:
  - `single_image_multi_trajectory.py` 的 `--compare_existing_video` / `--compare_steps`
  - 或单独一个 `inference/build_video_compare_bundle.py`
- 这样以后用户再做“10 步 vs 40 步”“旧 prompt vs 新 prompt”比较时, 不需要重复手写临时 Python 片段.
