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


1. model_full_load
      - 已验证行为: 直接把整条 pipeline 放到 GPU 上, 对应 _pipeline.to(device).
      - 特点: 显存占用最高.
      - 推导结论: 一般也是最快的, 因为中间几乎没有 CPU/GPU 搬运.
      - 适合: 显存比较充裕时用.
  2. model_full_load_and_qfloat8
      - 已验证行为: 先把 transformer 做 float8 量化, 再整条 pipeline 放到 GPU.
      - 已验证细节: 代码里量化的是 transformer, 不是所有模块都全量量化.
      - 特点: 比 model_full_load 更省显存.
      - 适合: 显存有点紧, 但你还是想尽量保留 full load 的运行方式.
  3. model_cpu_offload
      - 已验证行为: 调用 _pipeline.enable_model_cpu_offload(device).
      - 注释说明: 模型在使用后会移回 CPU, 这样能省一部分 GPU 显存.
      - 推导结论: 通常会比 full load 慢一些, 因为会多出搬运开销.
      - 适合: 单卡能跑, 但 full load 已经比较吃紧的时候.
  4. model_cpu_offload_and_qfloat8
      - 已验证行为: transformer 先做 float8 量化, 再启用 model_cpu_offload.
      - 特点: 这是"offload + 量化"叠加版, 比 model_cpu_offload 更省显存.
      - 仓库现状: README 和 cmd.md:1 里, 当前单卡稳定命令主要都在用这个模式.
      - 适合: 单卡场景下, 先追求稳定跑通和显存安全边际.
  5. sequential_cpu_offload
      - 已验证行为: 每层用完就往 CPU 挪, 调用 _pipeline.enable_sequential_cpu_offload(device).
      - 注释说明: 这是最省显存的一档, 但会更慢.
      - 额外限制: 注释里明确写了, compile_dit 和它不兼容, 见 inference/versecrafter_inference.py:114.
      - 适合: 显存非常吃紧, 目标是"先跑起来".

  如果你只想快速选一个, 可以这样记:

  - 显存很充足: model_full_load
  - 显存略紧: model_full_load_and_qfloat8
  - 单卡最稳妥常用: model_cpu_offload_and_qfloat8
  - 显存特别紧张: sequential_cpu_offload

##  demo_data/my4  用这个图 跑下 单镜头 快速测试 命令是?

  pixi run python inference/single_image_multi_trajectory.py \
    --input_image_path demo_data/my4/a.png \
    --output_root demo_data/my4/quick_test \
    --transformer_path model/VerseCrafter \
    --prompt "A realistic natural video of the original scene, 新海诚卡通风格,卡通描边,保持丁达尔效应体积光束,保留好场景的炫光,镜头光晕,辉光,slight camera motion, high detail" \
    --camera_only \
    --preset_indices 0 \
    --num_inference_steps 12 \
    --sample_size "720,1280" \
    --gpu_memory_mode model_cpu_offload_and_qfloat8 \
    --ulysses_degree 1 \
    --moge_pretrained Ruicheng/moge-2-vitl \
    --moge_version v2 \
    --ring_degree 1


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
  --moge_pretrained Ruicheng/moge-2-vitl \
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
  --moge_pretrained Ruicheng/moge-2-vitl \
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

## 6. 已真实跑过: `demo_data/my3` 双 A800 0 号轨迹整链路 10 步命令

- 用途:
  - 使用 `demo_data/my3/generated-image (1).png`
  - 双 A800 多卡
  - 只跑 `0` 号轨迹
  - 只做相机运动
  - 最终采样步数固定为 `10`
  - 最终显存模式固定为 `model_cpu_offload`
- 当前输出:
  - `demo_data/my3_dual_a800_test_v2/0/generated_videos/generated_video_0.mp4`
- 已验证结果:
  - `1280x720`
  - `81` 帧
  - `16 fps`
  - `5.0625 s`
- 关键说明:
  - `moge_version=v2` 默认会走 `Ruicheng/moge-2-vitl-normal`.
  - 如果你想固定使用 `moge-2-vitl`, 更稳妥的写法是显式传 `--moge_pretrained Ruicheng/moge-2-vitl`.
  - 如果你一定要传本地文件, 要用当前用户自己可读的路径, 不要写成 `/root/.cache/...`.
  - VerseCrafter 双卡 Step 6 依赖 `xfuser` 和 `yunchang`, 没装的话会在最终 `torchrun` 阶段报 `RuntimeError: xfuser is not installed.`.

### 6.1 多卡前置依赖安装

```bash
# 如果安装时网络不稳定, 先开代理
export https_proxy=http://127.0.0.1:7897 \
       http_proxy=http://127.0.0.1:7897 \
       all_proxy=socks5://127.0.0.1:7897

pixi run pip install xfuser==0.4.2 yunchang==0.6.2 \
  --progress-bar off \
  -i https://mirrors.aliyun.com/pypi/simple/
```

### 6.2 整链路命令

#### 单卡
```bash
pixi run python inference/single_image_multi_trajectory.py \
  --input_image_path 'demo_data/my7/d.png' \
  --output_root demo_data/my7 \
  --transformer_path model/VerseCrafter \
  --prompt "A realistic natural video of the original scene, 新海诚卡通风格博物馆,卡通描边,保持束,保留好场景的体积光 / God rays,光束、光柱,镜头光晕,辉光,slight camera motion, high detail." \
  --negative_prompt "粉尘,animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --camera_only \
  --moge_version v2 \
  --moge_pretrained Ruicheng/moge-2-vitl \
  --auto_center_depth_quantile 0.2 \
  --translation_reference_depth_scale 0.95 \
  --total_movement_distance_factor 1.5 \
  --sample_size "720,1280" \
  --num_inference_steps 60 \
  --gpu_memory_mode model_cpu_offload \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --nproc_per_node 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16
```

```bash
pixi run python inference/single_image_multi_trajectory.py \
  --input_image_path 'demo_data/nt1/a.png' \
  --output_root demo_data/nt1 \
  --transformer_path model/VerseCrafter \
  --prompt "An exhibition hall showcasing aircraft and automobiles.A realistic natural video of the original scene, Keep the scene content unchanged during camera movement. Ensure stereo correctness and preserve the geometric structure. No specular reflections, no highly reflective ground.high detail." \
  --negative_prompt "直视太阳,刺眼的太阳光,粉尘,高反光,高光点,脏,闪光点,animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --camera_only \
  --moge_version v2 \
  --moge_pretrained Ruicheng/moge-2-vitl \
  --auto_center_depth_quantile 0.2 \
  --translation_reference_depth_scale 0.95 \
  --total_movement_distance_factor 1.0 \
  --sample_size "720,1280" \
  --known_horizontal_fov_degrees 90 \
  --num_inference_steps 60 \
  --gpu_memory_mode model_cpu_offload \
  --ulysses_degree 2 \
  --ring_degree 1 \
  --nproc_per_node 2 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 24


```
### 6.3 只重跑双卡 Step 6 的命令

- 用途:
  - 已经有 `rendering_4D_maps`
  - 不想重跑 Step 1-5
  - 只复用控制图重跑最终视频

```bash
export CUDA_VISIBLE_DEVICES=0,1
export PYTHONUNBUFFERED=1
export TORCH_CUDA_ARCH_LIST=8.0

pixi run torchrun --nproc-per-node=2 inference/versecrafter_inference.py \
  --transformer_path model/VerseCrafter \
  --save_path demo_data/my3_dual_a800_test_v2/0/generated_videos \
  --rendering_maps_path demo_data/my3_dual_a800_test_v2/0/rendering_4D_maps \
  --prompt "A frozen-in-time futuristic AI exhibition hall interior with polished white floors, blue digital wall graphics, a concept vehicle chassis display, a glowing tunnel-like doorway, aerospace exhibits, and crisp architectural lighting. The entire scene is a single perfectly frozen instant. Every screen image, reflection, specular highlight, LED strip, light beam, prop, aircraft model, robot arm, sign, and object remains completely motionless and unchanged for the whole video. No people move. No display content animates. No lighting flicker. No changing reflections. Time is stopped. Only the camera moves through the space. Stable perspective, physically plausible reflections, realistic lens behavior, and consistent illumination." \
  --negative_prompt "animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --input_image_path 'demo_data/my3/generated-image (1).png' \
  --num_inference_steps 60 \
  --sample_size '720,1280' \
  --ulysses_degree 2 \
  --ring_degree 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 16 \
  --gpu_memory_mode model_cpu_offload
```


单卡 test

pixi run python inference/single_image_multi_trajectory.py \
  --input_image_path 'demo_data/nt1/a.png' \
  --output_root demo_data/nt1 \
  --transformer_path model/VerseCrafter \
  --prompt "An exhibition hall showcasing aircraft and automobiles.A realistic natural video of the original scene, Keep the scene content unchanged during camera movement. Ensure stereo correctness and preserve the geometric structure. No specular reflections, no highly reflective ground.high detail." \
  --negative_prompt "直视太阳,刺眼的太阳光,粉尘,高反光,高光点,脏,闪光点,animated screen content, flickering LEDs, moving reflections, moving shadows, lighting change, object motion, robot arm motion, aircraft motion, prop motion, human motion, body motion, pose change, temporal deformation, geometry warping, ghosting, jitter, flicker, camera shake, unstable highlights, low quality" \
  --camera_only \
  --moge_version v2 \
  --moge_pretrained /root/.cache/huggingface/hub/models--Ruicheng--moge-2-vitl/snapshots/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/model.pt \
  --auto_center_depth_quantile 0.35 \
  --translation_reference_depth_scale 0.95 \
  --total_movement_distance_factor 1.0 \
  --sample_size "720,1280" \
  --num_inference_steps 10 \
  --gpu_memory_mode model_cpu_offload \
  --ulysses_degree 1 \
  --ring_degree 1 \
  --nproc_per_node 1 \
  --guidance_scale 5.0 \
  --seed 2025 \
  --fps 24