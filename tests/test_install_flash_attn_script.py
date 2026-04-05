from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "install_flash_attn.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _make_fake_python(bin_dir: Path) -> None:
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

                if 'metadata.version("flash-attn")' in payload:
                    version = os.environ.get("FAKE_FLASH_ATTN_INSTALLED_VERSION", "")
                    if version:
                        print(version)
                        raise SystemExit(0)
                    raise SystemExit(1)

                if "import flash_attn" in payload:
                    if os.environ.get("FAKE_FLASH_ATTN_IMPORT_OK", "0") == "1":
                        raise SystemExit(0)
                    print("ImportError: fake flash_attn ABI mismatch", file=sys.stderr)
                    raise SystemExit(1)

                raise SystemExit(0)

            if args[:3] == ["-m", "pip", "install"]:
                log_path = Path(os.environ["FAKE_PYTHON_LOG"])
                log_path.write_text(
                    json.dumps(
                        {
                            "args": args,
                            "MAX_JOBS": os.environ.get("MAX_JOBS"),
                            "FLASH_ATTN_CUDA_ARCHS": os.environ.get("FLASH_ATTN_CUDA_ARCHS"),
                        }
                    ),
                    encoding="utf-8",
                )
                raise SystemExit(0)

            raise SystemExit(0)
            """
        ),
    )


def _base_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_python(bin_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["FAKE_PYTHON_LOG"] = str(tmp_path / "python-log.json")
    return env


def test_install_flash_attn_skips_when_installed_and_importable(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["FAKE_FLASH_ATTN_INSTALLED_VERSION"] = "2.8.3"
    env["FAKE_FLASH_ATTN_IMPORT_OK"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "检测到已安装且可导入的 flash-attn 2.8.3, 跳过重复安装" in result.stdout
    assert not Path(env["FAKE_PYTHON_LOG"]).exists()


def test_install_flash_attn_rebuilds_when_import_is_broken(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["FAKE_FLASH_ATTN_INSTALLED_VERSION"] = "2.8.3"
    env["FAKE_FLASH_ATTN_IMPORT_OK"] = "0"
    env["FLASH_ATTN_CUDA_ARCHS"] = "120"
    env["MAX_JOBS"] = "5"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "检测到已安装 flash-attn 2.8.3, 但当前环境下导入失败, 准备重新编译" in result.stderr

    pip_log = json.loads(Path(env["FAKE_PYTHON_LOG"]).read_text(encoding="utf-8"))
    assert pip_log["MAX_JOBS"] == "5"
    assert pip_log["FLASH_ATTN_CUDA_ARCHS"] == "120"
    assert pip_log["args"] == [
        "-m",
        "pip",
        "install",
        "--no-build-isolation",
        "--no-deps",
        "--no-binary",
        "flash-attn",
        "--no-cache-dir",
        "--force-reinstall",
        "flash-attn",
    ]


def test_install_flash_attn_force_reinstall_bypasses_skip(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["FAKE_FLASH_ATTN_INSTALLED_VERSION"] = "2.8.3"
    env["FAKE_FLASH_ATTN_IMPORT_OK"] = "1"
    env["FLASH_ATTN_FORCE_REINSTALL"] = "1"
    env["FLASH_ATTN_CUDA_ARCHS"] = "120"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "收到 FLASH_ATTN_FORCE_REINSTALL=1" in result.stdout

    pip_log = json.loads(Path(env["FAKE_PYTHON_LOG"]).read_text(encoding="utf-8"))
    assert pip_log["args"] == [
        "-m",
        "pip",
        "install",
        "--no-build-isolation",
        "--no-deps",
        "--no-binary",
        "flash-attn",
        "--no-cache-dir",
        "--force-reinstall",
        "flash-attn",
    ]
