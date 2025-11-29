import importlib
import sys
from pathlib import Path


def test_sitecustomize_adds_src_to_path(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setenv("PYTHONPATH", "")

    if "sitecustomize" in sys.modules:
        del sys.modules["sitecustomize"]

    importlib.import_module("sitecustomize")

    src_path = root / "src"
    assert str(src_path) in sys.path
