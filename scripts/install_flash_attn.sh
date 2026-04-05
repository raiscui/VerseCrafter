#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# 编译并发控制
# -------------------------------
# 如果用户已经显式指定 MAX_JOBS, 则尊重手动覆盖.
if [ -n "${MAX_JOBS:-}" ]; then
  jobs="${MAX_JOBS}"
  echo "[install-flash-attn] 使用外部指定的 MAX_JOBS=${jobs}"
else
  cpu_total="$(nproc)"
  reserve="${FLASH_ATTN_RESERVED_CPUS:-4}"

  # 只接受非负整数, 避免把非法环境变量传给编译阶段.
  if ! [[ "${reserve}" =~ ^[0-9]+$ ]]; then
    echo "[install-flash-attn] FLASH_ATTN_RESERVED_CPUS 必须是非负整数, 当前值: ${reserve}" >&2
    exit 1
  fi

  # 至少保留 reserve 个 CPU, 但最少仍给编译留 1 个 worker.
  if [ "${cpu_total}" -gt "${reserve}" ]; then
    jobs=$((cpu_total - reserve))
  else
    jobs=1
  fi

  echo "[install-flash-attn] cpu_total=${cpu_total}, reserved=${reserve}, MAX_JOBS=${jobs}"
fi

# -------------------------------
# 已安装短路
# -------------------------------
# 这条任务的语义本来就是“确保 flash-attn 可用”, 不只是“元数据存在”.
# 如果 torch 先升级了, 旧的 flash-attn `.so` 可能还在, 但 import 已经因为 ABI 失配失败.
# 因此这里先做两层判断:
# 1. 已安装并且可导入 -> 直接跳过
# 2. 已安装但导入失败 -> 继续走重编
# 此外也支持显式 `FLASH_ATTN_FORCE_REINSTALL=1` 强制重装.
force_reinstall="${FLASH_ATTN_FORCE_REINSTALL:-0}"
if ! [[ "${force_reinstall}" =~ ^(0|1)$ ]]; then
  echo "[install-flash-attn] FLASH_ATTN_FORCE_REINSTALL 只能是 0 或 1, 当前值: ${force_reinstall}" >&2
  exit 1
fi

installed_version=""
if [ "${force_reinstall}" = "1" ]; then
  echo "[install-flash-attn] 收到 FLASH_ATTN_FORCE_REINSTALL=1, 将强制重新编译 flash-attn"
elif installed_version="$(
  python - <<'PY'
import importlib.metadata as metadata
import sys

try:
    print(metadata.version("flash-attn"))
except metadata.PackageNotFoundError:
    sys.exit(1)
PY
)"; then
  if python - <<'PY'
import traceback
import sys

try:
    import flash_attn  # noqa: F401
except Exception:
    traceback.print_exc()
    sys.exit(1)
PY
  then
    echo "[install-flash-attn] 检测到已安装且可导入的 flash-attn ${installed_version}, 跳过重复安装"
    exit 0
  fi

  echo "[install-flash-attn] 检测到已安装 flash-attn ${installed_version}, 但当前环境下导入失败, 准备重新编译" >&2
fi

# -------------------------------
# CUDA 架构选择
# -------------------------------
# 这版 flash-attn 默认会编 80;90;100;120 四套架构.
# 用户已经明确要求只保留当前机器专用版本, 所以默认改为单架构.
if [ -n "${FLASH_ATTN_CUDA_ARCHS:-}" ]; then
  flash_attn_archs="${FLASH_ATTN_CUDA_ARCHS}"
  echo "[install-flash-attn] 使用外部指定的 FLASH_ATTN_CUDA_ARCHS=${flash_attn_archs}"
else
  # 先用 torch 读取可见 GPU 的 capability.
  # 这里故意不设置 TORCH_CUDA_ARCH_LIST.
  # flash-attn 自己支持 FLASH_ATTN_CUDA_ARCHS, 直接交给它最稳,
  # 也避免把其它 torch extension 的架构策略混进来.
  detected_archs="$(
    python - <<'PY'
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
from shutil import which


def dedupe(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def from_torch(diagnostics):
    try:
        import torch
    except Exception as exc:
        diagnostics.append(f"torch 导入失败: {exc!r}")
        return []

    try:
        available = torch.cuda.is_available()
        count = torch.cuda.device_count()
    except Exception as exc:
        diagnostics.append(f"torch.cuda 探测失败: {exc!r}")
        return []

    diagnostics.append(f"torch.cuda.is_available()={available}")
    diagnostics.append(f"torch.cuda.device_count()={count}")

    if not available or count == 0:
        return []

    caps = []
    for index in range(count):
        try:
            major, minor = torch.cuda.get_device_capability(index)
        except Exception as exc:
            diagnostics.append(f"torch 读取 GPU[{index}] capability 失败: {exc!r}")
            continue

        diagnostics.append(f"torch 检测到 GPU[{index}] capability={major}.{minor}")
        caps.append(f"{major}{minor}")
    return dedupe(caps)


def from_nvidia_smi(diagnostics):
    nvidia_smi = which("nvidia-smi")
    if nvidia_smi is None and Path("/usr/bin/nvidia-smi").exists():
        nvidia_smi = "/usr/bin/nvidia-smi"

    if nvidia_smi is None:
        diagnostics.append("未找到 nvidia-smi")
        return []

    diagnostics.append(f"nvidia-smi 路径={nvidia_smi}")
    if not os.access(nvidia_smi, os.X_OK):
        diagnostics.append("nvidia-smi 不可执行")
        return []

    try:
        output = subprocess.check_output(
            [nvidia_smi, "--query-gpu=compute_cap", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        diagnostics.append(f"nvidia-smi 查询 compute_cap 失败: {exc!r}")
        return []

    caps = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(".")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            continue

        caps.append(f"{parts[0]}{parts[1]}")
    if caps:
        diagnostics.append(f"nvidia-smi 检测到 capability={';'.join(dedupe(caps))}")
    else:
        diagnostics.append("nvidia-smi 没有返回可解析的 compute_cap")
    return dedupe(caps)


def describe_device_nodes(diagnostics):
    nodes = sorted(str(path) for path in Path("/dev").glob("nvidia*"))
    if nodes:
        diagnostics.append(f"检测到设备节点: {', '.join(nodes)}")
    else:
        diagnostics.append("未检测到 /dev/nvidia* 设备节点")


torch_stderr = io.StringIO()
diagnostics = []
with contextlib.redirect_stderr(torch_stderr):
    archs = from_torch(diagnostics)

if not archs:
    archs = from_nvidia_smi(diagnostics)

if not archs:
    describe_device_nodes(diagnostics)
    stderr_output = torch_stderr.getvalue().strip()
    if stderr_output:
        diagnostics.append(f"torch stderr={stderr_output}")

    print("[install-flash-attn] 自动探测失败诊断:", file=sys.stderr)
    for line in diagnostics:
        print(f"  - {line}", file=sys.stderr)
    sys.exit(2)

print(";".join(archs))
PY
  )" || {
    echo "[install-flash-attn] 无法自动探测 GPU 架构. 如果当前 shell / 容器没有挂载 GPU, 请手动设置 FLASH_ATTN_CUDA_ARCHS, 例如 120." >&2
    exit 1
  }

  # 如果可见 GPU 有多种架构, 仍按“单专用版本”策略默认取第一张卡.
  # 这样不会偷偷回退成多架构全量编译, 用户也还能手动覆盖.
  flash_attn_archs="${detected_archs%%;*}"
  if [[ "${detected_archs}" == *";"* ]]; then
    echo "[install-flash-attn] 检测到多个可见 GPU 架构: ${detected_archs}. 当前按单专用策略选择第一项 ${flash_attn_archs}" >&2
  else
    echo "[install-flash-attn] 自动探测当前 GPU 架构: ${flash_attn_archs}"
  fi
fi

if ! [[ "${flash_attn_archs}" =~ ^[0-9]+$ ]]; then
  echo "[install-flash-attn] FLASH_ATTN_CUDA_ARCHS 必须是纯数字架构编号, 当前值: ${flash_attn_archs}" >&2
  exit 1
fi

pip_install_args=(
  --no-build-isolation
  --no-deps
  --no-binary
  flash-attn
)

if [ "${force_reinstall}" = "1" ] || [ -n "${installed_version}" ]; then
  # 既然当前现场已经存在旧安装, 就显式禁用缓存并强制覆盖,
  # 避免 pip 继续复用之前那个 ABI 不匹配的 wheel.
  pip_install_args+=(
    --no-cache-dir
    --force-reinstall
  )
fi

echo "[install-flash-attn] 即将执行源码安装: python -m pip install ${pip_install_args[*]} flash-attn"
MAX_JOBS="${jobs}" FLASH_ATTN_CUDA_ARCHS="${flash_attn_archs}" python -m pip install "${pip_install_args[@]}" flash-attn
