#!/usr/bin/env bash
set -euo pipefail

repo_dir="${PYTORCH3D_REPO_DIR:-pytorch3d}"
repo_url="${PYTORCH3D_REPO_URL:-https://github.com/facebookresearch/pytorch3d.git}"
repo_ref="${PYTORCH3D_GIT_REF:-stable}"
force_reinstall="${PYTORCH3D_FORCE_REINSTALL:-0}"
use_system_compiler="${PYTORCH3D_USE_SYSTEM_COMPILER:-1}"

describe_cuda_candidates() {
  local available_cuda_dirs=""

  # -------------------------------
  # 输出现场可见的 CUDA toolkit 候选, 方便用户一眼看出“实际存在什么”.
  # 这里不做推断, 只做证据展示.
  # -------------------------------
  if command -v nvcc >/dev/null 2>&1; then
    echo "[install-pytorch3d] 当前 PATH 中的 nvcc: $(command -v nvcc)" >&2
  else
    echo "[install-pytorch3d] 当前 PATH 中没有可执行的 nvcc" >&2
  fi

  available_cuda_dirs="$(find /usr/local -maxdepth 1 -type d '(' -name 'cuda' -o -name 'cuda-*' ')' | sort -V || true)"
  if [ -n "${available_cuda_dirs}" ]; then
    echo "[install-pytorch3d] /usr/local 下可见的 CUDA 目录:" >&2
    while IFS= read -r cuda_dir; do
      [ -n "${cuda_dir}" ] || continue
      echo "  - ${cuda_dir}" >&2
    done <<<"${available_cuda_dirs}"
  else
    echo "[install-pytorch3d] /usr/local 下没有发现任何 cuda / cuda-* 目录" >&2
  fi
}

resolve_cuda_home() {
  local source_name="$1"
  local candidate="$2"
  local strict_mode="$3"
  local normalized=""

  [ -n "${candidate}" ] || return 1

  if [ ! -d "${candidate}" ]; then
    if [ "${strict_mode}" = "1" ]; then
      echo "[install-pytorch3d] ${source_name}=${candidate} 指向的目录不存在." >&2
      echo "[install-pytorch3d] 这个变量必须指向包含 bin/nvcc 的 CUDA toolkit 根目录." >&2
      echo '[install-pytorch3d] 请用 `dirname "$(dirname "$(command -v nvcc)")"` 取得真实 toolkit 路径, 再重试.' >&2
      describe_cuda_candidates
      exit 1
    fi
    return 1
  fi

  normalized="$(cd "${candidate}" && pwd -P)"
  if [ ! -x "${normalized}/bin/nvcc" ]; then
    if [ "${strict_mode}" = "1" ]; then
      echo "[install-pytorch3d] ${source_name}=${normalized} 不是有效的 CUDA toolkit 根目录." >&2
      echo "[install-pytorch3d] 缺少可执行文件: ${normalized}/bin/nvcc" >&2
      echo '[install-pytorch3d] 请用 `dirname "$(dirname "$(command -v nvcc)")"` 取得真实 toolkit 路径, 再重试.' >&2
      describe_cuda_candidates
      exit 1
    fi
    return 1
  fi

  export CUDA_HOME="${normalized}"
  return 0
}

# -------------------------------
# 编译并发控制
# -------------------------------
# pytorch3d 通过 torch.utils.cpp_extension.BuildExtension 默认走 ninja.
# PyTorch 文档里明确说明可用 MAX_JOBS 控制 worker 数, 否则会按默认策略尽量并行.
# 这里沿用 flash-attn 同样的“保留部分 CPU”策略, 避免把整机吃满.
if [ -n "${MAX_JOBS:-}" ]; then
  jobs="${MAX_JOBS}"
  echo "[install-pytorch3d] 使用外部指定的 MAX_JOBS=${jobs}"
else
  cpu_total="$(nproc)"
  reserve="${PYTORCH3D_RESERVED_CPUS:-4}"

  # 只接受非负整数, 避免把非法值传给后续构建工具.
  if ! [[ "${reserve}" =~ ^[0-9]+$ ]]; then
    echo "[install-pytorch3d] PYTORCH3D_RESERVED_CPUS 必须是非负整数, 当前值: ${reserve}" >&2
    exit 1
  fi

  # 至少保留 reserve 个 CPU, 但再小也给编译留下 1 个 worker.
  if [ "${cpu_total}" -gt "${reserve}" ]; then
    jobs=$((cpu_total - reserve))
  else
    jobs=1
  fi

  echo "[install-pytorch3d] cpu_total=${cpu_total}, reserved=${reserve}, MAX_JOBS=${jobs}"
fi

# -------------------------------
# 幂等短路
# -------------------------------
# `install-pytorch3d` 的语义和 `install-flash-attn` 一样, 本质上是“确保依赖存在”.
# 如果现场已经装好了, 默认直接成功, 避免用户重复触发整轮 C++ / CUDA 重编译.
if [ "${force_reinstall}" != "1" ]; then
  installed_version="$(
    python - <<'PY'
import importlib.metadata as metadata
import sys

try:
    print(metadata.version("pytorch3d"))
except metadata.PackageNotFoundError:
    sys.exit(1)
PY
  )" || installed_version=""

  if [ -n "${installed_version}" ]; then
    echo "[install-pytorch3d] 检测到已安装 pytorch3d ${installed_version}, 跳过重复安装"
    exit 0
  fi
fi

# -------------------------------
# CUDA toolkit 路径校验
# -------------------------------
# 这一步放在 clone 之前, 避免显式配置本来就错时还白跑一轮网络和源码准备.
# 对显式传入的路径, 我们选择“失败即说清楚”, 不再把坏路径静默透传到编译阶段.
if [ -n "${PYTORCH3D_CUDA_HOME:-}" ]; then
  resolve_cuda_home "PYTORCH3D_CUDA_HOME" "${PYTORCH3D_CUDA_HOME}" "1"
elif [ -n "${CUDA_HOME:-}" ]; then
  resolve_cuda_home "CUDA_HOME" "${CUDA_HOME}" "1"
else
  if command -v nvcc >/dev/null 2>&1; then
    nvcc_path="$(command -v nvcc)"
    resolve_cuda_home "PATH:nvcc" "$(dirname "$(dirname "${nvcc_path}")")" "0" || true
  fi

  if [ -z "${CUDA_HOME:-}" ] && [ -d /usr/local/cuda ]; then
    resolve_cuda_home "/usr/local/cuda" "/usr/local/cuda" "0" || true
  fi

  if [ -z "${CUDA_HOME:-}" ]; then
    latest_cuda_dir="$(find /usr/local -maxdepth 1 -type d -name 'cuda-*' | sort -V | tail -n 1)"
    if [ -n "${latest_cuda_dir}" ]; then
      resolve_cuda_home "latest:/usr/local/cuda-*" "${latest_cuda_dir}" "0" || true
    fi
  fi
fi

# -------------------------------
# 源码引用控制
# -------------------------------
clone_repo() {
  echo "[install-pytorch3d] 使用浅克隆拉取 pytorch3d (${repo_ref}), 以减少 bootstrap 的网络开销"
  rm -rf "${repo_dir}"
  git clone \
    --branch "${repo_ref}" \
    --single-branch \
    --depth 1 \
    --filter=blob:none \
    "${repo_url}" \
    "${repo_dir}"
}

# PyTorch3D 官方安装文档明确提供了 `git+...@stable` 的 released 版本安装方式.
# 这里把默认仓库引用改成 `stable`, 避免每次都无条件追 `main`.
if [ -d "${repo_dir}/.git" ]; then
  current_branch="$(git -C "${repo_dir}" symbolic-ref --short -q HEAD 2>/dev/null || true)"
  if [ -n "${current_branch}" ] && [ "${current_branch}" = "${repo_ref}" ]; then
    echo "[install-pytorch3d] 复用现有仓库: ${repo_dir} (ref=${current_branch})"
  elif [ -n "$(git -C "${repo_dir}" status --porcelain 2>/dev/null || true)" ]; then
    echo "[install-pytorch3d] 现有仓库 ${repo_dir} 有未提交改动, 保持原样继续使用" >&2
  else
    echo "[install-pytorch3d] 现有仓库 ref=${current_branch:-detached} 与目标 ${repo_ref} 不一致, 重新拉取目标引用"
    clone_repo
  fi
else
  clone_repo
fi

# -------------------------------
# 编译环境整理
# -------------------------------
# Blackwell / CUDA 12.8+ 这类较新的环境, 对编译器和 CUDA toolkit 路径更敏感.
# 这里尽量把“可安全自动化”的部分统一起来, 其余仍允许用户通过环境变量显式覆盖.
if [ "${use_system_compiler}" = "1" ]; then
  if [ -x /usr/bin/gcc ] && [ -x /usr/bin/g++ ]; then
    if [ -z "${CC:-}" ]; then
      export CC="/usr/bin/gcc"
    fi
    if [ -z "${CXX:-}" ]; then
      export CXX="/usr/bin/g++"
    fi
    if [ -z "${CUDAHOSTCXX:-}" ]; then
      export CUDAHOSTCXX="/usr/bin/g++"
    fi
    echo "[install-pytorch3d] 使用 system gcc/g++ 作为 CUDA/C++ host compiler"
  else
    echo "[install-pytorch3d] 未找到 /usr/bin/gcc 与 /usr/bin/g++, 跳过 system compiler 绑定" >&2
  fi
fi

if [ -n "${CUDA_HOME:-}" ]; then
  case ":${PATH}:" in
    *":${CUDA_HOME}/bin:"*) ;;
    *) export PATH="${CUDA_HOME}/bin:${PATH}" ;;
  esac
  if [ -d "${CUDA_HOME}/lib64" ]; then
    case ":${LD_LIBRARY_PATH:-}:" in
      *":${CUDA_HOME}/lib64:"*) ;;
      *) export LD_LIBRARY_PATH="${CUDA_HOME}/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" ;;
    esac
  fi
  echo "[install-pytorch3d] CUDA_HOME=${CUDA_HOME}"
fi

if [ -n "${PYTORCH3D_TORCH_CUDA_ARCH_LIST:-}" ]; then
  export TORCH_CUDA_ARCH_LIST="${PYTORCH3D_TORCH_CUDA_ARCH_LIST}"
  echo "[install-pytorch3d] 使用显式指定的 TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
elif [ -n "${TORCH_CUDA_ARCH_LIST:-}" ]; then
  echo "[install-pytorch3d] 使用外部指定的 TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
else
  detected_torch_arch="$(
    python - <<'PY'
import re
import sys

try:
    import torch
except Exception:
    sys.exit(0)

if not hasattr(torch, "cuda") or not torch.cuda.is_available() or torch.cuda.device_count() == 0:
    sys.exit(0)

caps = sorted(
    {
        f"{major}.{minor}"
        for major, minor in (
            torch.cuda.get_device_capability(index)
            for index in range(torch.cuda.device_count())
        )
    }
)
if len(caps) != 1:
    sys.exit(0)

torch_match = re.match(r"^(\d+)\.(\d+)", torch.__version__)
cuda_match = re.match(r"^(\d+)\.(\d+)", torch.version.cuda or "")
if not torch_match or not cuda_match:
    sys.exit(0)

torch_version = tuple(int(part) for part in torch_match.groups())
cuda_version = tuple(int(part) for part in cuda_match.groups())
arch = caps[0]

# 只自动处理当前已知最明确的 Blackwell 路径:
# PyTorch 2.7+ + CUDA 12.8+ + 单一 12.0 capability.
# 其它组合继续保持“用户显式指定”, 避免把旧 torch 不认识的架构硬塞进去.
if arch == "12.0" and torch_version >= (2, 7) and cuda_version >= (12, 8):
    print(arch)
PY
  )"

  if [ -n "${detected_torch_arch}" ]; then
    export TORCH_CUDA_ARCH_LIST="${detected_torch_arch}"
    echo "[install-pytorch3d] 自动设置 TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
  fi
fi

# 保持原有 no-build-isolation 安装语义, 只优化源码获取方式与构建环境.
# 同时把并发值传给 ninja / CMake 路径, 避免不同构建后端各走各的默认并行度.
MAX_JOBS="${jobs}" \
CMAKE_BUILD_PARALLEL_LEVEL="${jobs}" \
python -m pip install --no-build-isolation "./${repo_dir}"
