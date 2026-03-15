# 错误修复记录
## [2026-03-15 04:03:00 UTC] 问题: pixi install-pytorch3d 任务使用 Bash if 导致解析失败

### 问题现象
- 执行 `pixi run --manifest-path pixi.toml install-pytorch3d` 时, 在任务真正开始 clone / install 前就报错:
  - `failed to parse shell script`
  - `Unsupported reserved word`
- 报错位置指向 `if [ ! -d pytorch3d ]; then`.

### 原因分析
- 静态证据:
  - `pixi.toml` 中 `install-pytorch3d` 任务使用了 Bash 风格 `if ... then ... fi`.
  - Pixi 官方文档说明任务默认运行在 `deno_task_shell`, 这是有限的 bourne-shell 实现.
- 动态证据:
  - 直接执行原任务可稳定复现同款报错.
  - 最小实验表明 `test -d foo || echo missing` 可以, 但 Bash `if` 不行.
  - 最小实验还表明多行命令之间需要显式 `&&` / `||` 连接, 不能把普通换行当 Bash 脚本分号.

### 修复方式
- 将任务从:
  - `if [ ! -d pytorch3d ]; then ... fi`
- 改为:
  - `git clone https://github.com/facebookresearch/pytorch3d.git pytorch3d || test -d pytorch3d`
  - 下一行 `&& python -m pip install --no-build-isolation ./pytorch3d`

### 修复后的行为
- 如果 `pytorch3d/` 不存在, 会执行 clone, 成功后继续安装.
- 如果 `pytorch3d/` 已存在, clone 失败后 `test -d pytorch3d` 返回成功, 继续安装.
- 如果 clone 因网络或权限等原因失败, 且目录也不存在, 任务会保持失败, 不会被静默吞掉.

### 验证记录
- `pixi run --manifest-path pixi.toml --dry-run install-pytorch3d`
  - 成功输出新任务命令, 无解析错误.
- `pixi task list --manifest-path pixi.toml`
  - 成功列出 `install-pytorch3d`.
