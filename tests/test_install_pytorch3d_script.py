from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "install_pytorch3d.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _make_fake_python(bin_dir: Path) -> None:
    # 这个假 python 只模拟脚本里真正会走到的几条分支:
    # 1. 元数据查询, 用来测试“已安装短路”
    # 2. `python -m pip install ...`, 用来记录最终透传的环境变量
    _write_executable(
        bin_dir / "python",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]

            if args == ["-"]:
                payload = sys.stdin.read()
                if 'metadata.version("pytorch3d")' in payload:
                    version = os.environ.get("FAKE_PYTORCH3D_INSTALLED_VERSION", "")
                    if version:
                        print(version)
                        raise SystemExit(0)
                    raise SystemExit(1)

                arch = os.environ.get("FAKE_PYTORCH3D_ARCH_PROBE", "")
                if arch:
                    print(arch)
                raise SystemExit(0)

            if args[:3] == ["-m", "pip", "install"]:
                log_path = Path(os.environ["FAKE_PYTHON_LOG"])
                log_path.write_text(
                    json.dumps(
                        {
                            "args": args,
                            "MAX_JOBS": os.environ.get("MAX_JOBS"),
                            "CMAKE_BUILD_PARALLEL_LEVEL": os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL"),
                            "CC": os.environ.get("CC"),
                            "CXX": os.environ.get("CXX"),
                            "CUDAHOSTCXX": os.environ.get("CUDAHOSTCXX"),
                            "CUDA_HOME": os.environ.get("CUDA_HOME"),
                            "TORCH_CUDA_ARCH_LIST": os.environ.get("TORCH_CUDA_ARCH_LIST"),
                        }
                    ),
                    encoding="utf-8",
                )
                raise SystemExit(0)

            raise SystemExit(0)
            """
        ),
    )


def _make_fake_git(bin_dir: Path) -> None:
    _write_executable(
        bin_dir / "git",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import os
            import sys
            from pathlib import Path

            log_path = Path(os.environ["FAKE_GIT_LOG"])
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(" ".join(sys.argv[1:]) + "\\n")

            args = sys.argv[1:]
            if args and args[0] == "clone":
                repo_dir = Path(args[-1])
                (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
                raise SystemExit(0)

            raise SystemExit(0)
            """
        ),
    )


def _make_fake_nvcc_tree(tmp_path: Path, name: str = "cuda-12.8") -> Path:
    cuda_home = tmp_path / name
    bin_dir = cuda_home / "bin"
    bin_dir.mkdir(parents=True)
    _write_executable(
        bin_dir / "nvcc",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            exit 0
            """
        ),
    )
    return cuda_home


def _base_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_python(bin_dir)
    _make_fake_git(bin_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["FAKE_PYTHON_LOG"] = str(tmp_path / "python-log.json")
    env["FAKE_GIT_LOG"] = str(tmp_path / "git-log.txt")
    env["PYTORCH3D_REPO_DIR"] = "pytorch3d"
    return env


def test_install_pytorch3d_skips_rebuild_when_already_installed(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["FAKE_PYTORCH3D_INSTALLED_VERSION"] = "0.7.9"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "检测到已安装 pytorch3d 0.7.9, 跳过重复安装" in result.stdout
    assert not Path(env["FAKE_GIT_LOG"]).exists()
    assert not Path(env["FAKE_PYTHON_LOG"]).exists()


def test_install_pytorch3d_forwards_stable_ref_and_build_env(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    fake_cuda_home = _make_fake_nvcc_tree(tmp_path)
    env["MAX_JOBS"] = "3"
    env["PYTORCH3D_GIT_REF"] = "stable"
    env["PYTORCH3D_CUDA_HOME"] = str(fake_cuda_home)
    env["PYTORCH3D_TORCH_CUDA_ARCH_LIST"] = "12.0"
    env["PYTORCH3D_USE_SYSTEM_COMPILER"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "使用浅克隆拉取 pytorch3d (stable)" in result.stdout
    assert "使用显式指定的 TORCH_CUDA_ARCH_LIST=12.0" in result.stdout
    assert f"CUDA_HOME={fake_cuda_home}" in result.stdout

    git_log = Path(env["FAKE_GIT_LOG"]).read_text(encoding="utf-8")
    assert "--branch stable" in git_log
    assert "--single-branch" in git_log
    assert "--depth 1" in git_log
    assert "--filter=blob:none" in git_log

    pip_log = json.loads(Path(env["FAKE_PYTHON_LOG"]).read_text(encoding="utf-8"))
    assert pip_log["args"] == ["-m", "pip", "install", "--no-build-isolation", "./pytorch3d"]
    assert pip_log["MAX_JOBS"] == "3"
    assert pip_log["CMAKE_BUILD_PARALLEL_LEVEL"] == "3"
    assert pip_log["CUDA_HOME"] == str(fake_cuda_home)
    assert pip_log["TORCH_CUDA_ARCH_LIST"] == "12.0"
    assert pip_log["CC"] == "/usr/bin/gcc"
    assert pip_log["CXX"] == "/usr/bin/g++"
    assert pip_log["CUDAHOSTCXX"] == "/usr/bin/g++"


def test_install_pytorch3d_rejects_invalid_explicit_cuda_home(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["PYTORCH3D_CUDA_HOME"] = str(tmp_path / "cuda-12.9")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "PYTORCH3D_CUDA_HOME=" in result.stderr
    assert "bin/nvcc" in result.stderr
    assert "真实 toolkit 路径" in result.stderr
    assert not Path(env["FAKE_GIT_LOG"]).exists()
    assert not Path(env["FAKE_PYTHON_LOG"]).exists()
