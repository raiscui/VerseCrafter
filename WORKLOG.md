# 工作日志

## [2026-03-22 12:35:40 UTC] 任务名称: 将 7 号镜头从 `clockwise_1.5` 调整为逆时针轨迹

### 任务内容
- 将单图多轨迹批处理里的 7 号镜头从顺时针大半径 orbit, 改成逆时针大半径 orbit.
- 保持索引 `7` 不变, 同时同步修正用户可见名称、prompt、README、OpenSpec 与测试.

### 完成过程
- 先定位确认当前 canonical preset 中索引 `7` 确实对应 `clockwise_1.5`.
- 回读轨迹生成逻辑后, 没有给 7 号镜头单独打特判, 而是为 `TrajectoryPreset` 新增 `orbit_direction` 元数据.
- 将统一 orbit 公式改造成 `_generate_orbit_offsets_cv(...)`, 让半径倍率和顺/逆时针方向都由 preset 数据决定.
- 把索引 `7` 的名称和文案同步更新为:
  - `counterclockwise_1.5`
  - `Camera is orbiting counterclockwise around the scene with a wider radius`
- 同步更新:
  - `README.md`
  - `openspec/changes/add-clockwise-radius-variants/*`
  - `tests/test_single_image_multi_trajectory_lib.py`
  - `tests/test_single_image_multi_trajectory_smoke.py`
- 最后用 `py_compile`、`pytest` 和一段动态数值检查确认方向与半径都已正确变化.

### 总结感悟
- 这类镜头 preset 变更, 不能只盯着几何轨迹, 因为这个项目已经把 prompt 和 dry-run 也做成了用户承诺的一部分.
- 把 orbit 的方向也数据化之后, 后面再加顺/逆时针档位时会更自然, 不需要继续扩展名字分支.

## [2026-03-22 12:18:55 UTC] 任务名称: 解释 `demo_data/my4` 跑到 8 号镜头时为何仍只有 1 张 GPU 工作

### 任务内容
- 排查用户在 `demo_data/my4` 批处理运行中, 已进入 8 号镜头但仍只看到 1 张 GPU 工作的原因.
- 不修改代码, 先基于真实运行中的父子进程与 manifest 做证据核对.

### 完成过程
- 先回读历史上下文, 确认近期确实已经完成了多轨迹扩展和 prompt 补充, 且此前也做过多卡相关排查.
- 再读取当前父进程 `single_image_multi_trajectory.py` 与 8 号镜头子进程 `versecrafter_inference.py` 的 `/proc/<pid>/cmdline`.
- 验证到当前 8 号镜头的 Step 6 并没有走 `torchrun`, 而是直接以单进程方式运行.
- 同时核对 `demo_data/my4/manifest.json`, 发现当前记录的也是单卡设置:
  - `ulysses_degree = 1`
  - `ring_degree = 1`
  - `nproc_per_node = 1`
  - `num_inference_steps = 30`
- 因此将问题收敛为“当前真实运行参数与用户口头预期不一致”, 而不是“已经进入双卡步骤但第二张卡没有干活”.

### 总结感悟
- 对多卡任务, 最容易误导人的不是 GPU 本身, 而是“我以为自己跑的是哪条命令”与“系统里真正跑起来的是哪条命令”之间的偏差.
- 在这种场景里, 直接看 `/proc/<pid>/cmdline` 和实际子进程, 比只看终端历史或复制出来的命令更可靠.

## [2026-03-22 12:36:50 UTC] 任务名称: 将 `demo_data/my4` 的 8-11 号镜头按双卡参数重启

### 任务内容
- 复用 `demo_data/my4` 已完成的共享产物和前 0-7 号镜头结果.
- 只对 8-11 号镜头按双卡参数重启, 确认真正使用两张 A800.

### 完成过程
- 先核对脚本 `resume` 行为, 确认复跑同一 `output_root` 时会复用共享步骤和已完成镜头.
- 再检查 `manifest.json`, 确认当前待处理的是 8-11 号镜头.
- 用 `pixi run python` 验证:
  - `torch.cuda.device_count() = 2`
  - `xfuser` / `yunchang` 导入正常
- 先执行一轮 `--dry_run`, 确认 Step 6 命令已经明确拼成 `torchrun --nproc-per-node=2`.
- 随后正式启动双卡批处理, 参数聚焦为:
  - `--num_inference_steps 60`
  - `--gpu_memory_mode model_cpu_offload`
  - `--ulysses_degree 2`
  - `--ring_degree 1`
  - `--nproc_per_node 2`
  - `--preset_indices 8 9 10 11`
- 启动后立即验证进程树和运行日志, 确认:
  - 有 `torchrun`
  - 有两个 worker
  - `rank=0 device=cuda:0`
  - `rank=1 device=cuda:1`
- 最后用 `nvidia-smi` 复核到两张 A800 同时有显存占用和计算利用率.

### 总结感悟
- 真正把“双卡是否生效”说清楚, 最稳的是四件事一起看:
  - `dry_run` 组装出的命令
  - 实际进程树
  - 运行日志里的 rank -> device 映射
  - `nvidia-smi` 实时占用
- 只看其中一项, 都很容易误判.

## [2026-03-24 18:00:55 UTC] 任务名称: 排查单图多轨迹命令如何跳过联网检查并直接复用本地缓存

### 任务内容
- 排查 `inference/single_image_multi_trajectory.py` 这条链路里哪些模型加载点可能触发联网.
- 判断当前用户命令能否在不改代码的情况下直接走离线缓存.

### 完成过程
- 回读六文件上下文, 确认近期多轨迹与双卡逻辑的历史改动, 避免把旧问题和本次离线诉求混在一起.
- 逐段检查:
  - `inference/single_image_multi_trajectory.py`
  - `inference/versecrafter_inference.py`
  - `inference/moge-v2_infer.py`
  - MoGe 安装包里的 `from_pretrained` 实现
- 确认当前链路中:
  - VerseCrafter transformer 走本地目录 `model/VerseCrafter`
  - VerseCrafter base model 走本地目录 `model/Wan2.1-T2V-14B`
  - MoGe 在传入本地 `model.pt` 时不会走 `hf_hub_download`
- 做了最小动态验证:
  - `HF_HUB_OFFLINE=1` 下成功加载本地 tokenizer
  - `HF_HUB_OFFLINE=1` 下成功加载本地 MoGe checkpoint
- 额外检查 `demo_data/my5`, 确认共享深度和 camera-only 的共享产物已经存在, 可直接靠默认 `resume` 复用.

### 总结感悟
- 这类“明明给了缓存路径, 为什么还联网”的问题, 很多时候不是模型真要重新下载, 而是没有把“本地路径是否真实存在”和“库的离线开关”一起确认.
- 对这个项目来说, 最省事的路径是双保险:
  - 所有模型参数显式走本地路径
  - 命令前加 `HF_HUB_OFFLINE=1`
  - 不要换 `output_root`, 直接吃 `resume` 的共享产物

## [2026-03-25 13:12:09 UTC] 任务名称: 在 `my6` 完成后接手启动 `demo_data/my7`

### 任务内容
- 确认 `demo_data/my6` 是否真正完成.
- 检查上一轮挂起的自动接力是否真的已经把 `demo_data/my7` 启动起来.
- 若未启动, 直接按用户提供的参数手动启动 `demo_data/my7`, 并核对运行状态.

### 完成过程
- 先回读 `task_plan.md`, 再检查进程、`demo_data/my6/manifest.json` 与 `demo_data/my7` 目录状态.
- 验证到 `my6` 实际已经全部完成, 但系统中只剩一个等待脚本, 没有真实的 `my7` 推理进程.
- 进一步用 `pgrep -af 'single_image_multi_trajectory.py.*demo_data/my6'` 证实:
  - 等待脚本把自己也匹配进去了
  - 所以一直错误地判断 `my6` 仍在运行
- 停掉误挂的等待脚本后, 直接按用户原命令启动 `my7`.
- 启动后立刻核对:
  - `demo_data/my7/manifest.json` 已创建
  - `shared/estimated_depth/*` 已落盘
  - `shared/fitted_3D_gaussian/gaussian_params.json` 已落盘
  - 当前子进程正在执行 `rendering_4D_control_maps.py`
  - 当前日志已进入 0 号镜头背景渲染

### 总结感悟
- 对这种“等待某个进程结束再接力”的脚本, 只靠 `pgrep -af` 这种基于命令行全文匹配的写法很危险.
- 如果匹配模式被脚本自己的命令行文本包含进去, 就会出现“目标早就结束了, 但等待脚本还在无限等待”的假象.
- 这次 `my7` 已经真正启动, 但当前还是前置单卡阶段, 还没到后面的双卡生成段.

## [2026-03-25 18:33:10 UTC] 任务名称: 核对 `pixi` 默认环境中的 `PyTorch` / `pytorch3d` 真实版本

### 任务内容
- 在不只依赖静态配置的前提下, 动态确认项目默认 `pixi` 环境里真实安装的 `torch` / `torchvision` / `torchaudio` / `pytorch3d` 版本.
- 额外区分普通系统 `python3` 与项目 `pixi` 环境的差异, 避免被本地源码目录误导.

### 完成过程
- 先回读六文件上下文, 避免把此前“系统 Python 版本”和“项目环境版本”混在一起.
- 再用 `pixi run --manifest-path ... python -m pip show ...` 读取安装元数据.
- 接着用 `pixi run ... python` 动态验证:
  - `sys.executable`
  - `torch.__version__`
  - `torch.version.cuda`
  - `torch.cuda.is_available()`
  - `pytorch3d.__file__` 与 `pytorch3d.__version__`
- 最后补做一轮对照验证, 确认普通 `python3` 在仓库根目录下会把本地 `pytorch3d/` 源码目录当成可导入模块, 从而误导版本判断.

### 总结感悟
- 查 Python 包真实版本时, `pip show`、`importlib.metadata` 和模块 `__file__` 要一起看, 单看 `import` 是否成功不够稳.
- 这个仓库里真正应该信任的运行环境是 `pixi` 默认环境, 不是外部系统 Python.

## [2026-03-26 08:07:57 UTC] 任务名称: 修复 `left_up` / `right_up` 始终看向中心的问题

### 任务内容
- 调整 `left_up` / `right_up` 两个轨迹在 `center_facing` 模式下的注视目标点.
- 让 `left_up` 轻微偏向左看, `right_up` 轻微偏向右看.
- 补充回归测试, 把“看向哪里”这层语义锁住.

### 完成过程
- 先定位到核心问题不在平移轨迹, 而在 `generate_blender_camera_trajectory()` 对 `center_facing` 统一使用同一个中心目标点.
- 没有给 `left_up` / `right_up` 加硬编码名字分支, 而是给 `TrajectoryPreset` 增加:
  - `center_facing_target_offset_scale_cv`
- 为两个 diagonal up preset 设置轻微水平偏移:
  - `left_up = (-0.35, 0.0, 0.0)`
  - `right_up = (0.35, 0.0, 0.0)`
- 偏移量按 `movement_distance * translation_reference_depth` 缩放后, 再统一转换到 Blender 坐标.
- 新增测试通过射线和平面交点反推出实际 look-at 目标点 X 坐标, 验证左右偏移确实生效.
- 额外修正两条已漂移的旧测试, 让断言重新匹配当前:
  - orbit 方向元数据
  - diagonal down 垂直缩放常量

### 总结感悟
- “镜头怎么移动”和“镜头看向哪里”是两套独立语义, 不能只靠位移方向去暗示视线方向.
- 轨迹测试如果只校验 translation, 很容易漏掉这种“机位走对了, 但视线语义还是错的”回归.

## [2026-03-27 09:58:40 UTC] 任务名称: 终止当前生成链并清理自动接力后的残留推理进程

### 任务内容
- 根据用户要求停止当前仍在运行的生成任务.
- 核对到底是 `my10` 还在跑, 还是后台接力已经把 `my4` 自动拉起.
- 确保停止后不再有推理继续占用 GPU.

### 完成过程
- 先核对真实进程、`manifest` 和等待会话状态.
- 验证到 `my10` 实际已经完成, `demo_data/my10/manifest.json` 顶层状态为 `completed`.
- 同时确认后台接力已经结束, 并且新的 `my4` 任务已经被自动启动.
- 进一步发现当前残留的并不是完整的批处理进程树, 而是两个直接挂在 `init` 下的 `versecrafter_inference.py` orphan worker.
- 这两个 worker 正在执行:
  - `demo_data/my4/8/generated_videos`
- 对两个 worker 发送 `SIGTERM`, 随后复核:
  - `/proc/724715` 消失
  - `/proc/724716` 消失
  - 无相关推理进程残留
  - 两张 GPU 占用回到 0

### 总结感悟
- 这次真正需要停掉的对象不是最初盯着的 `my10`, 而是接力后已经切换到的 `my4`.
- 判断“当前到底是谁在跑”时, 真实进程和 `manifest` 的交叉核对, 比只盯住旧 PID 更可靠.
- 自动接力一旦成功放行, 现场的主任务对象会切换, 停止动作也必须跟着切换.

## [2026-03-29 17:56:32 UTC] 任务名称: 为 `nt1 -> nt2` 挂载独立后台接力门闩

### 任务内容
- 监督当前 `demo_data/nt1` 批处理的真实进度.
- 在 `nt1` 完成后, 自动执行用户提供的 `demo_data/nt2` 命令.
- 让监督与接力逻辑脱离当前对话会话, 避免长时间等待时丢失执行连续性.

### 完成过程
- 先回读六文件, 再核对真实进程, 确认当前主进程为 `173293`, 当前正在双卡生成 `demo_data/nt1/9`.
- 进一步读取 `manifest.json` 与产物时间戳, 确认:
  - `0-8` 已完成
  - `9` 正在 Step 6
  - `10-11` 尚未开始
- 发现 `manifest` 在 Step 6 期间不实时刷新, 因而把监督依据调整为:
  - 主进程存活
  - `torchrun` / worker 存活
  - GPU 占用持续
  - 最终视频产物是否落盘
- 新建后台脚本 `demo_data/nt1_to_nt2_handoff.sh`, 内部使用双条件闸门:
  - `nt1` 主进程退出
  - `demo_data/nt1/manifest.json` 顶层状态为 `completed`
- 首次使用普通 `nohup` 挂后台未成功, 随后通过最小前台验证排除了脚本逻辑错误.
- 最终改为 `setsid + nohup + /dev/null` 成功脱离会话, 后台进程 PID 为 `252616`.
- 已验证该后台门闩会每 30 秒持续写入:
  - `demo_data/nt2_handoff_runner.out`
  - `demo_data/nt2_handoff_monitor.log`

### 总结感悟
- 对这种要跨很长时间窗的批处理接力, 与其把对话挂着硬等, 不如尽早把监督逻辑变成独立门闩.
- 这次再次证明:
  - `manifest` 适合做完成闸门
  - 真实进程与 GPU 占用更适合做运行期心跳
- 在当前工具环境里, 想让后台任务真正脱离会话, 仅用 `nohup` 不一定够, `setsid + nohup + /dev/null` 更稳.

## [2026-03-30 00:56:52 UTC] 任务名称: 为 `nt2 -> nt3` 挂载独立后台接力门闩

### 任务内容
- 监督当前 `demo_data/nt2` 批处理的真实进度.
- 在 `nt2` 完成后, 自动执行用户提供的 `demo_data/nt3` 命令.
- 避免去热修改仍在运行的 `nt1 -> nt2` 门闩, 将新接力逻辑独立隔离.

### 完成过程
- 先回读六文件并核对现场, 确认:
  - `nt1` 已完成
  - 当前真正运行的是 `nt2`
  - 当前正在双卡生成 `demo_data/nt2/9`
- 进一步从 `demo_data/nt2/manifest.json` 汇总到:
  - `0-8` 已完成
  - `9` 正在进行
  - `10-11` 尚未开始
- 确认 `demo_data/nt3` 当前只有输入图 `c.png`, 没有历史 `manifest`, 适合在完成闸门后干净启动.
- 新建后台脚本 `demo_data/nt2_to_nt3_handoff.sh`, 内部沿用:
  - 真实 PID 退出
  - `manifest` 顶层 `completed`
  这两个条件作为接力闸门
- 用 `bash -n` 校验脚本语法后, 以 `setsid + nohup + /dev/null` 启动独立进程.
- 最终后台门闩 PID 为 `340573`, 并已验证 `runner` 与 `monitor` 日志连续增长.

### 总结感悟
- 当前仍在运行的后台脚本本体, 不适合在中途热修改.
- 对链式批处理来说, “每一跳一个独立门闩”虽然多一个脚本, 但风险隔离更清晰.
- 延续上一轮经验, 现在这套接力方式已经形成稳定模板:
  - 用真实主 PID 做运行期存活判据
  - 用 `manifest completed` 做最终完成判据
  - 用 `setsid + nohup + /dev/null` 做脱离会话的后台挂载

## [2026-03-27 18:45:44 UTC] 任务名称: 当前 `single_image_multi_trajectory.py` 完成后自动关机

### 任务内容
- 为当前正在运行的 `single_image_multi_trajectory.py` 批处理挂一个完成后自动关机的门闩.
- 确保不是盲等文本匹配, 而是绑定到真实 PID 和最终 manifest 状态.

### 完成过程
- 先核对当前真实运行中的批处理实例, 确认主 Python 进程为 `785968`, 输出目录为 `demo_data/my4-1`.
- 额外检查关机命令路径, 发现本机不存在 `/usr/bin/shutdown`, 实际可用路径是 `/usr/sbin/shutdown`.
- 随后建立后台等待会话 `28278`.
- 这条门闩采用双条件:
  - 真实 PID 退出
  - `demo_data/my4-1/manifest.json` 顶层状态为 `completed`
- 只有两者同时成立时, 才执行:
  - `/usr/sbin/shutdown -h now`
- 如果批处理异常退出或 manifest 没有完成, 则会跳过关机, 避免误关机.

### 总结感悟
- 这类“任务结束后自动关机”最怕两种错:
  - 等错了进程
  - 关机命令路径本身就不存在
- 这次用真实 PID 加 manifest 双确认, 比简单的 `pgrep` 或“进程一退就关”更稳.

## [2026-03-29 15:28:46 UTC] 任务名称: 持续学习沉淀与 `task_plan.md` 续档

### 任务内容
- 回读当前六文件, 提炼最近一轮工作里真正可复用的知识.
- 判断这些知识应该沉淀到 `AGENTS.md`, `README.md`, 新 skill, 还是继续保留在计划类文件里.
- 处理当前 `task_plan.md` 超过 1000 行的续档问题.

### 完成过程
- 先列出并通读当前六文件, 确认本轮没有可额外回读的历史版本文件.
- 再聚焦最新追加段, 把事实收敛成三类知识:
  - repo-specific 的运行约定
  - 跨项目可复用的 shell 排障模式
  - 已存在但仍未落地的后续工程
- 将 `pixi` 环境版本核对规则同步补进:
  - `AGENTS.md`
  - `README.md`
- 新增跨项目 skill:
  - `/root/.codex/skills/self-learning.shell-pgrep-self-match-wait-loop/SKILL.md`
- 最后把旧的超长 `task_plan.md` 续档到:
  - `archive/task_plan_2026-03-29_152846.md`
  并重新创建新的当前 `task_plan.md`.

### 总结感悟
- 持续学习最有价值的, 不是“再写一份流水账”, 而是把知识分流到最合适的长期载体.
- 这轮最值得固化的两个点很明确:
  - 这个仓库的依赖版本核对必须站在 `pixi` 环境里完成.
  - shell 编排里只靠 `pgrep -af` 等待进程, 风险比看上去大得多.
