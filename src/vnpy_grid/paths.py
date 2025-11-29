from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def src_dir() -> Path:
    return project_root() / "src"


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_output_dir(name: str = "outputs") -> Path:
    """Return a stable output directory under project root and ensure it exists."""
    return ensure_dir(project_root() / name)
