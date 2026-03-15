# 当前只相机控制命令记录

## 说明

- 这里记录的是当前已经验证过, 或者与当前代码默认值对齐的“只控制相机运动”命令.
- 当前这套工作流的核心开关是:
  - `--camera_only`
- 当前默认轨迹调节参数保持为:
  - `--auto_center_depth_quantile 0.2`
  - `--translation_reference_depth_scale 0.95`
  - `--total_movement_distance_factor 1.5`
- 当前单卡稳定显存模式保持为:
  - `--gpu_memory_mode model_cpu_offload_and_qfloat8`

## 1. 推荐: 单图只相机控制整链路命令

- 用途:
  - 从单张图直接生成 VerseCrafter 的只相机控制结果
  - 跳过前景分割和 Gaussian 前景拟合
  - 默认生成 6 条固定轨迹

```bash
pixi run python inference/single_image_multi_trajectory.py \
  --input_image_path demo_data/my2/10000.png \
  --output_root demo_data/my2_timefreeze_10000 \
  --transformer_path model/VerseCrafter \
  --prompt "A frozen-in-time futuristic AI exhibition hall interior with polished white floors, blue digital wall graphics, a concept vehicle chassis display, a glowing tunnel-like doorway, aerospace exhibits, and crisp architectural lighting. The entire scene is a single perfectly frozen instant. Every screen image, reflection, specular highlight, LED strip, light beam, prop, aircraft model, robot arm, sign, and object remains completely motionless and unchanged for the whole video. No people move. No display content animates. No lighting flicker. No changing reflections. Time is stopped. Only the camera moves through the space. Stable perspective, physically plausible reflections, realistic lens behavior, and consistent illumination." \
  --negative_prompt "animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --camera_only \
  --moge_version v2 \
  --moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt \
  --auto_center_depth_quantile 0.2 \
  --translation_reference_depth_scale 0.95 \
  --total_movement_distance_factor 1.5 \
  --sample_size "720,1280" \
  --num_inference_steps 40 \
  --gpu_memory_mode model_cpu_offload_and_qfloat8 \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16
```

## 2. 只跑 0 号轨迹的整链路命令

- 用途:
  - 新场景快速验证
  - 只跑 `0` 号轨迹
  - 其余共享预处理仍按当前工作流生成
- 说明:
  - 这一条对应当前 `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`

```bash
pixi run python inference/single_image_multi_trajectory.py \
  --input_image_path demo_data/my2/10000.png \
  --output_root demo_data/my2_timefreeze_10000 \
  --transformer_path model/VerseCrafter \
  --prompt "A frozen-in-time futuristic AI exhibition hall interior with polished white floors, blue digital wall graphics, a concept vehicle chassis display, a glowing tunnel-like doorway, aerospace exhibits, and crisp architectural lighting. The entire scene is a single perfectly frozen instant. Every screen image, reflection, specular highlight, LED strip, light beam, prop, aircraft model, robot arm, sign, and object remains completely motionless and unchanged for the whole video. No people move. No display content animates. No lighting flicker. No changing reflections. Time is stopped. Only the camera moves through the space. Stable perspective, physically plausible reflections, realistic lens behavior, and consistent illumination." \
  --negative_prompt "animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --camera_only \
  --preset_indices 0 \
  --moge_version v2 \
  --moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt \
  --auto_center_depth_quantile 0.2 \
  --translation_reference_depth_scale 0.95 \
  --total_movement_distance_factor 1.5 \
  --sample_size "720,1280" \
  --num_inference_steps 40 \
  --gpu_memory_mode model_cpu_offload_and_qfloat8 \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16
```

## 3. 已真实跑过: 复用控制图, 单独重跑 Step 6 的 40 步命令

- 用途:
  - 不重跑 Step 1-5
  - 只复用 `rendering_4D_maps` 重跑最终视频
- 当前输出:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`

```bash
pixi run python inference/versecrafter_inference.py \
  --transformer_path model/VerseCrafter \
  --save_path demo_data/my2_timefreeze_10000/0/generated_videos \
  --rendering_maps_path demo_data/my2_timefreeze_10000/0/rendering_4D_maps \
  --prompt "A frozen-in-time futuristic AI exhibition hall interior with polished white floors, blue digital wall graphics, a concept vehicle chassis display, a glowing tunnel-like doorway, aerospace exhibits, and crisp architectural lighting. The entire scene is a single perfectly frozen instant. Every screen image, reflection, specular highlight, LED strip, light beam, prop, aircraft model, robot arm, sign, and object remains completely motionless and unchanged for the whole video. No people move. No display content animates. No lighting flicker. No changing reflections. Time is stopped. Only the camera moves through the space. Stable perspective, physically plausible reflections, realistic lens behavior, and consistent illumination." \
  --negative_prompt "animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --input_image_path demo_data/my2/10000.png \
  --num_inference_steps 40 \
  --sample_size "720,1280" \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16 \
  --gpu_memory_mode model_cpu_offload_and_qfloat8
```

## 4. 已真实跑过: 复用控制图, 单独重跑 Step 6 的 10 步对比命令

- 用途:
  - 保留 40 步正式结果不覆盖
  - 额外生成 10 步快速对比版
- 当前输出:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0.mp4`

```bash
pixi run python inference/versecrafter_inference.py \
  --transformer_path model/VerseCrafter \
  --save_path demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare \
  --rendering_maps_path demo_data/my2_timefreeze_10000/0/rendering_4D_maps \
  --prompt "A frozen-in-time futuristic AI exhibition hall interior with polished white floors, blue digital wall graphics, a concept vehicle chassis display, a glowing tunnel-like doorway, aerospace exhibits, and crisp architectural lighting. The entire scene is a single perfectly frozen instant. Every screen image, reflection, specular highlight, LED strip, light beam, prop, aircraft model, robot arm, sign, and object remains completely motionless and unchanged for the whole video. No people move. No display content animates. No lighting flicker. No changing reflections. Time is stopped. Only the camera moves through the space. Stable perspective, physically plausible reflections, realistic lens behavior, and consistent illumination." \
  --negative_prompt "animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --input_image_path demo_data/my2/10000.png \
  --num_inference_steps 10 \
  --sample_size "720,1280" \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16 \
  --gpu_memory_mode model_cpu_offload_and_qfloat8
```

## 5. 当前输出目录对照

- 40 步正式结果:
  - `demo_data/my2_timefreeze_10000/0/generated_videos/generated_video_0.mp4`
- 10 步对比结果:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0.mp4`
- 10 步接触图:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/frames_contact_sheet.jpg`
- 10 步 vs 40 步并排视频:
  - `demo_data/my2_timefreeze_10000/0/generated_videos_steps10_compare/generated_video_0_vs_steps40_side_by_side.mp4`
