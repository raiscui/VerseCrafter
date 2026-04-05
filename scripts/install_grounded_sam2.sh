#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# 编译并发控制
# -------------------------------
# Grounded-SAM-2 的 setup.py 默认走 torch 的 BuildExtension + ninja.
# 如果不显式限制, ninja 会按默认策略尽量并行, 容易把 CPU 拉满.
# 这里沿用项目里 flash-attn / pytorch3d 的口径, 默认至少保留 4 个 CPU.
if [ -n "${MAX_JOBS:-}" ]; then
  jobs="${MAX_JOBS}"
  echo "[install-grounded-sam2] 使用外部指定的 MAX_JOBS=${jobs}"
else
  cpu_total="$(nproc)"
  reserve="${SAM2_RESERVED_CPUS:-4}"

  # 只接受非负整数, 避免把非法值继续传给构建链.
  if ! [[ "${reserve}" =~ ^[0-9]+$ ]]; then
    echo "[install-grounded-sam2] SAM2_RESERVED_CPUS 必须是非负整数, 当前值: ${reserve}" >&2
    exit 1
  fi

  # 至少保留 reserve 个 CPU, 但最少仍给构建留 1 个 worker.
  if [ "${cpu_total}" -gt "${reserve}" ]; then
    jobs=$((cpu_total - reserve))
  else
    jobs=1
  fi

  echo "[install-grounded-sam2] cpu_total=${cpu_total}, reserved=${reserve}, MAX_JOBS=${jobs}"
fi

# 继续复用当前 Pixi 环境中的 torch / setuptools, 避免再次拉隔离构建依赖.
MAX_JOBS="${jobs}" CMAKE_BUILD_PARALLEL_LEVEL="${jobs}" python -m pip install --no-build-isolation -e ./third_party/Grounded-SAM-2
