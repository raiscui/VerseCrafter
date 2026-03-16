# 工作日志

## [2026-03-15 17:18:00 UTC] 任务名称: 推送 `third_party/VideoX-Fun` 到 `raiscui/VideoX-Fun`

### 任务内容
- 将 VerseCrafter 子模块 `third_party/VideoX-Fun` 中此前的音频可选依赖修复, 推送到 `https://github.com/raiscui/VideoX-Fun`.
- 保持父仓库不做额外提交, 避免把本轮操作扩散成主仓库 gitlink 更新任务.

### 完成过程
- 先核对子模块状态, 确认它不是未提交工作区, 而是一个 detached HEAD 提交 `b7a3cc2`.
- 再核对目标远端 `raiscui/VideoX-Fun` 的 `main`, 确认其仍停在 `ad72867`, 不能直接被 `b7a3cc2` 快进覆盖.
- 以 `main` 为基线创建本地分支 `push-raiscui-videox-fun`, 将 `b7a3cc2` 的补丁 cherry-pick 过去.
- 解决 `videox_fun/models/__init__.py` 的冲突时, 保留了上游新增模型导出, 只移植“音频编码器改为可选依赖导入”的修复.
- 排查发现普通 `git push` 会被 VS Code 的 `GIT_ASKPASS` 交互脚本卡住, 最终改用临时 token askpass 脚本完成非交互推送.
- 推送成功后, 用 `git ls-remote` 回读确认远端 `main = 3811a69`.
- 最后把子模块本地检出恢复到原来的 `b7a3cc2`, 仅保留本地分支和远端结果, 不额外扩大父仓库工作区差异.

### 总结感悟
- 对 submodule 做“推送到 fork”这类操作时, 不能只看当前 detached HEAD 有没有提交, 还必须验证它是不是目标远端 `main` 的线性后继.
- 在当前 Codex / VS Code 终端环境下, HTTPS `git push` 可能被默认 `GIT_ASKPASS` 静默挂住; 更稳的做法是用一次性的 token askpass 脚本和显式超时, 让认证路径可控、可验证.

## [2026-03-15 17:31:00 UTC] 任务名称: 推送 VerseCrafter 主仓库到 `raiscui/VerseCrafter`

### 任务内容
- 将当前 VerseCrafter 主仓库推送到 `https://github.com/raiscui/VerseCrafter.git`.
- 在推送前修复 `VideoX-Fun` submodule 指针不可达的问题, 避免把主仓库推成坏状态.

### 完成过程
- 先核对主仓库 `HEAD`、`my/main`、`.gitmodules` 和 `third_party/VideoX-Fun` gitlink.
- 发现主仓库 `HEAD` 记录的是 `b7a3cc2`, 但 `.gitmodules` 仍指向上游 `aigc-apps/VideoX-Fun`, 而该提交在上游远端不可达.
- 将 `.gitmodules` 改为 `https://github.com/raiscui/VideoX-Fun.git`, 并把子模块切到已推送可达的 `3811a69`.
- 只提交这两个必要修复项, 生成:
  - `49cae46 update videox-fun submodule`
- 用临时 askpass 脚本完成 `git push my main`, 再用 `git ls-remote my refs/heads/main` 回读确认远端已更新到 `49cae46`.

### 总结感悟
- 推送含 submodule 的主仓库时, 真正要验证的不是“本地能不能 push”, 而是“别人 clone 后能不能把 submodule 正常检出来”.
- 对这类仓库, `.gitmodules` URL 和 gitlink commit 必须一起看; 只修其中一个, 很容易留下 `not our ref` 这种延后爆炸的问题.

## [2026-03-16 03:31:00 UTC] 任务名称: `demo_data/my3` 双 A800 0 号视角视频生成测试

### 任务内容
- 使用 `demo_data/my3/generated-image (1).png` 执行 0 号视角相机运动视频测试.
- 保持用户要求的双 A800、多卡、`num_inference_steps=10`、`gpu_memory_mode=model_cpu_offload`.
- 将默认会下载 `moge-2-vitl-normal` 的深度模型入口改为本地缓存的 `moge-2-vitl` 权重.

### 完成过程
- 先核对 `README.md`、`inference/single_image_multi_trajectory.py`、`inference/versecrafter_inference.py` 与 `third_party/VideoX-Fun/README.md`, 确认 0 号视角应通过 `--preset_indices 0` 走批处理入口, 双卡应使用 `torchrun`.
- 观察到 `demo_data/my3` 是单张静态展厅图, 而普通分割路径要求 `num_objects > 0`, 因此改为更稳的 `--camera_only` 纯相机运动模式.
- 首轮正式执行卡在 `moge-2-vitl-normal` 下载阶段后, 根据用户补充改成 `--moge_pretrained /root/.cache/.../moge-2-vitl/.../model.pt`, 成功完成深度估计与 Step 5 控制图渲染.
- 第二轮进入双卡 Step 6 时, 动态报错 `RuntimeError: xfuser is not installed.`; 随后核实 `xfuser` 与 `yunchang` 均缺失.
- 按 `third_party/VideoX-Fun/README.md` 的多卡说明, 在 Pixi 环境中安装 `xfuser==0.4.2` 与 `yunchang==0.6.2`.
- 安装后直接复用已有 `rendering_4D_maps`, 用 `torchrun --nproc-per-node=2 inference/versecrafter_inference.py` 成功跑完 10 步采样.
- 最后再用一次批处理 `--resume` 快速收尾, 让 `manifest.json` 与真实视频产物状态对齐.

### 总结感悟
- 这个项目里 `moge_version=v2` 的默认模型并不是 `moge-2-vitl`, 而是 `moge-2-vitl-normal`; 如果本地已经缓存了旧版 `moge-2-vitl`, 需要显式传 `--moge_pretrained`, 否则很容易在下载阶段浪费时间.
- VerseCrafter 的双卡不是“有两张 GPU 就能跑”, 还依赖 `xfuser` 与 `yunchang`; 只要缺这两个, 前置步骤全都能成功, 但会在 Step 6 才暴露问题.

## [2026-03-16 03:35:00 UTC] 任务名称: 将 `demo_data/my3` 双卡成功命令沉淀到 `cmd.md`

### 任务内容
- 将本次 `demo_data/my3` 双 A800 0 号轨迹成功命令记录到 `cmd.md`.
- 一并补上本次真实踩到的前置依赖与代理提示, 避免命令脱离上下文后不可复用.

### 完成过程
- 先回读 `cmd.md` 当前结构, 确认它已经按“用途 + 命令 + 输出路径”组织.
- 在尾部追加新的 `my3` 双卡命令段, 记录:
  - 多卡依赖安装命令
  - 安装网络异常时的代理环境变量
  - 完整整链路命令
  - 只重跑 Step 6 的双卡命令
- 保持本次关键差异可见:
  - `--moge_pretrained` 避免默认下载 `moge-2-vitl-normal`
  - `xfuser` / `yunchang` 是 VerseCrafter 双卡前置依赖

### 总结感悟
- 命令文档真正有用的前提, 不是“命令看起来完整”, 而是把那些只有跑过一次才知道的隐含约束也写进去.
- 对多卡这类流程, 最容易浪费时间的往往不是主命令本身, 而是前置依赖和默认模型选择.
