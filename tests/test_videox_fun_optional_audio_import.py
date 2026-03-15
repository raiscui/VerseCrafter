from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest


def test_videox_fun_models_import_keeps_non_audio_workflow_available() -> None:
    """缺少 librosa 时, 非音频工作流的导入不应被整体拖垮."""

    root = Path(__file__).resolve().parents[1]
    videox_fun_root = root / "third_party" / "VideoX-Fun"

    if str(videox_fun_root) not in sys.path:
        sys.path.insert(0, str(videox_fun_root))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # 这里显式重新导入包初始化模块, 锁定本次修复的真实入口.
    sys.modules.pop("videox_fun.models", None)
    models = importlib.import_module("videox_fun.models")

    assert models.AutoencoderKLWan.__name__ == "AutoencoderKLWan"
    assert models.WanT5EncoderModel.__name__ == "WanT5EncoderModel"

    from versecrafter.pipeline import WanVerseCrafterPipeline

    assert WanVerseCrafterPipeline.__name__ == "WanVerseCrafterPipeline"

    # 当前测试环境没有 librosa, 这里应返回清晰的可选依赖错误,
    # 而不是在导入 `videox_fun.models` 时提前把整条链路炸掉.
    if importlib.util.find_spec("librosa") is None:
        with pytest.raises(ModuleNotFoundError, match="librosa"):
            models.FantasyTalkingAudioEncoder()
        with pytest.raises(ModuleNotFoundError, match="librosa"):
            models.WanAudioEncoder()
