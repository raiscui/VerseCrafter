## 1. Preset catalog and orbit generation

- [ ] 1.1 扩展 `TrajectoryPreset` 元数据与 preset 列表, 新增 `clockwise_0.65` 和 `clockwise_1.5`, 并保持现有 `0..5` 索引不变.
- [ ] 1.2 调整 orbit 轨迹生成逻辑, 让两个新 preset 复用现有 `clockwise` 语义, 仅按 `0.65` 和 `1.5` 缩放 orbit 半径.

## 2. User-facing preset surfaces

- [ ] 2.1 更新 preset 选择和批处理展示链路, 确保 `--preset_indices`、canonical 顺序、dry-run / manifest 中都能正确显示新 preset 的索引和名称.
- [ ] 2.2 更新 README 中单图多轨迹批处理说明, 把 preset 数量和名称从 6 个同步到 8 个.

## 3. Verification

- [ ] 3.1 扩展 `tests/test_single_image_multi_trajectory_lib.py`, 覆盖新的 preset 目录顺序、deterministic movement distance 与 orbit 半径比例关系.
- [ ] 3.2 扩展 `tests/test_single_image_multi_trajectory_smoke.py`, 覆盖新 preset 的 subset 选择与 dry-run 输出.
- [ ] 3.3 运行聚焦测试, 验证 `test_single_image_multi_trajectory_lib.py` 和 `test_single_image_multi_trajectory_smoke.py` 通过.
