# 关键洞察

## [2026-03-14 17:20:00 UTC] 主题: pixi 对带 PyPI 源码依赖的 dry-run 校验有边界

### 发现来源
- 在 VerseCrafter 将 README 的环境管理从 Conda 迁移到 `pixi` 时, 使用 `pixi lock --manifest-path pixi.toml --dry-run` 验证新 manifest.

### 核心问题
- `pixi lock --dry-run` 在求解包含 PyPI 依赖的环境时, 可能因为 `--no-install` 禁止初始化 conda 环境而提前失败.
- 这种失败不等价于 `pixi.toml` 语法错误或依赖声明错误.

### 为什么重要
- 如果把这个报错误读成 manifest 本身有问题, 很容易在错误方向上反复修改依赖表.
- 正确理解这个边界后, 才能把“manifest 可读”与“完整环境可安装”分开验证.

### 未来风险
- 后续如果项目继续增加 Git / 本地 editable / 需要编译的 PyPI 依赖, 会更频繁碰到这个现象.
- 如果没有记录, 下次迁移环境工具或补 lockfile 时还会重复踩坑.

### 当前结论
- `pixi task list`、`pixi workspace channel/platform list` 可用于轻量验证 manifest 可读取.
- 完整的求解与安装验证, 仍需要真实执行 `pixi install` 或等价流程.

### 后续讨论入口
- 继续推进时先看 `pixi.toml`、`LATER_PLANS.md` 中关于 `pixi.lock` 的后续计划.

## [2026-03-15 04:04:00 UTC] 主题: pixi 多行任务不是 Bash 脚本, 复杂条件应避免直接内联

### 发现来源
- 在修复 `install-pytorch3d` 任务时报 `Unsupported reserved word`, 并通过最小复现实验验证 Pixi 任务语法边界.

### 核心问题
- Pixi 默认 `deno_task_shell` 不能直接按 Bash 心智使用 `if ... then ... fi`.
- 多行任务中的普通换行也不会自动代表“下一条命令”; 如果上一行使用 `&&` / `||`, 下一条命令需要明确接在布尔链里.

### 为什么重要
- 研究型仓库经常喜欢把安装逻辑直接塞进 `pixi.toml`; 一旦逻辑稍微复杂, 很容易写成“看起来像 shell, 实际不能跑”的配置.
- 如果没有记录, 下次继续给 `bootstrap` 增加任务时, 还会重复踩同一个解析坑.

### 未来风险
- 后续如果继续往 `pixi.toml` 里堆更多带条件判断、循环、here-doc 的任务, 出错概率会快速升高.
- 把复杂逻辑长期保留在内联任务里, 可读性和可维护性都会下降.

### 当前结论
- 简单条件优先改写成 and/or list, 例如 `cmd1 || test -d path`.
- 若逻辑再复杂一个层级, 更适合迁移到独立脚本文件, 再由 Pixi 调脚本.

### 后续讨论入口
- 下次扩展 `bootstrap` 任务时, 先回看这条记录和 `ERRORFIX.md` 中的最小复现实验结论.
