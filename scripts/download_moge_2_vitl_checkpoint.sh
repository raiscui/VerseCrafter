#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# 专用下载参数
# -------------------------------
repo_id="Ruicheng/moge-2-vitl"
filename="model.pt"
repo_dir="models--Ruicheng--moge-2-vitl"
blob_hash="3eefd4abb2102f38f12b2d1992e5ff15e4923e5431c67dd494afe157e0111cd5"
revision="39c4d5e957afe587e04eec59dc2bcc3be5ecd968"
expected_size="1305030700"

# -------------------------------
# 本地缓存落点
# -------------------------------
hf_home="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
hub_dir="${HF_HUB_CACHE:-${hf_home}/hub}"
blob_dir="${hub_dir}/${repo_dir}/blobs"
lock_dir="${hub_dir}/.locks/${repo_dir}"
snapshot_dir="${hub_dir}/${repo_dir}/snapshots/${revision}"
blob_path="${blob_dir}/${blob_hash}.incomplete"
snapshot_model_path="${snapshot_dir}/${filename}"
local_dir="${HOME}/.cache/huggingface/local-moge-2-vitl"
local_model_path="${local_dir}/${filename}"
local_part_path="${local_model_path}.part"

# -------------------------------
# 重试 / 超时控制
# -------------------------------
attempts="${MOGE_DOWNLOAD_ATTEMPTS:-400}"
per_attempt_timeout="${MOGE_DOWNLOAD_PER_ATTEMPT_TIMEOUT:-45}"
hf_endpoint="${MOGE_HF_ENDPOINT:-https://hf-mirror.com}"
chunk_size="${MOGE_DOWNLOAD_CHUNK_SIZE:-4194304}"
max_idle_attempts="${MOGE_DOWNLOAD_IDLE_ATTEMPTS:-2}"

mkdir -p "${blob_dir}" "${lock_dir}" "${snapshot_dir}" "${local_dir}"

# -------------------------------
# 统一落到当前用户自己的稳定本地路径
# -------------------------------
# 优先使用当前用户自己的本地文件.
# 如果历史上已经积累了 Hugging Face cache partial, 就把它接过来继续下.
if [ -f "${local_model_path}" ]; then
  echo "[download-moge-2-vitl] 复用现有本地模型: ${local_model_path}"
  exit 0
fi

if [ ! -f "${local_part_path}" ] && [ -f "${blob_path}" ]; then
  mv "${blob_path}" "${local_part_path}"
fi

echo "[download-moge-2-vitl] repo=${repo_id}"
echo "[download-moge-2-vitl] target=${local_model_path}"
echo "[download-moge-2-vitl] attempts=${attempts}, per_attempt_timeout=${per_attempt_timeout}s"
echo "[download-moge-2-vitl] hf_endpoint=${hf_endpoint}"
echo "[download-moge-2-vitl] chunk_size=${chunk_size}"
echo "[download-moge-2-vitl] max_idle_attempts=${max_idle_attempts}"

idle_attempts=0

for attempt in $(seq 1 "${attempts}"); do
  before_size="$(stat -c %s "${local_part_path}" 2>/dev/null || echo 0)"
  echo "[download-moge-2-vitl] attempt=${attempt} before=${before_size}/${expected_size}"

  if [ "${before_size}" -ge "${expected_size}" ]; then
    mv "${local_part_path}" "${local_model_path}"
    echo "[download-moge-2-vitl] 下载完成: ${local_model_path}"
    exit 0
  fi

  range_start="${before_size}"
  range_end=$((range_start + chunk_size - 1))
  if [ "${range_end}" -ge "${expected_size}" ]; then
    range_end=$((expected_size - 1))
  fi
  expected_chunk_size=$((range_end - range_start + 1))
  tmp_chunk="$(mktemp)"

  # -------------------------------
  # 单轮短超时分块下载
  # -------------------------------
  # 这里不再依赖 `hf_hub_download` 的整文件流程.
  # 而是直接对 resolve URL 做 Range 请求, 每轮只取一小块.
  # 成功时才追加到 `.part`, 避免半截块污染本地文件.
  timeout "${per_attempt_timeout}" \
    env \
      -u http_proxy \
      -u https_proxy \
      -u all_proxy \
      -u HTTP_PROXY \
      -u HTTPS_PROXY \
      -u ALL_PROXY \
      curl \
        -L \
        --fail \
        --silent \
        --show-error \
        -r "${range_start}-${range_end}" \
        -o "${tmp_chunk}" \
        "${hf_endpoint}/${repo_id}/resolve/main/${filename}" || true

  downloaded_chunk_size="$(stat -c %s "${tmp_chunk}" 2>/dev/null || echo 0)"
  if [ "${downloaded_chunk_size}" -eq "${expected_chunk_size}" ]; then
    cat "${tmp_chunk}" >> "${local_part_path}"
  fi
  rm -f "${tmp_chunk}"

  after_size="$(stat -c %s "${local_part_path}" 2>/dev/null || echo 0)"
  echo "[download-moge-2-vitl] attempt=${attempt} after=${after_size}/${expected_size} delta=$((after_size - before_size))"

  if [ "${after_size}" -ge "${expected_size}" ]; then
    mv "${local_part_path}" "${local_model_path}"
    echo "[download-moge-2-vitl] 下载完成: ${local_model_path}"
    exit 0
  fi

  # 有进展就清零 idle 计数并继续.
  # 没进展时允许少量重试, 避免因为单次网络抖动过早退出.
  if [ "${after_size}" -gt "${before_size}" ]; then
    idle_attempts=0
    continue
  fi

  idle_attempts=$((idle_attempts + 1))
  echo "[download-moge-2-vitl] idle_attempts=${idle_attempts}/${max_idle_attempts}" >&2
  if [ "${idle_attempts}" -ge "${max_idle_attempts}" ]; then
    echo "[download-moge-2-vitl] 连续无进展, 终止等待. 当前 partial: ${local_part_path}" >&2
    exit 1
  fi
done

echo "[download-moge-2-vitl] 已达到最大尝试次数, 但仍未完成. 当前 partial: ${local_part_path}" >&2
exit 1
