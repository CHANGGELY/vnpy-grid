#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python 启动时自动执行的定制化脚本。
职责：
- 确保项目根目录和 src/ 在 sys.path 中，支持基于 src 的包结构。
- 如设置环境变量 LHHC_AUTO_PATCH=1，则自动加载 patch_ctabacktester。
"""

import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
current_dir = Path.cwd()
src_dir = root_dir / "src"

# 将关键路径加入 sys.path（前插，优先生效）
for p in (root_dir, current_dir, src_dir):
    try:
        s = str(p)
        if p.exists() and s not in sys.path:
            sys.path.insert(0, s)
    except Exception:
        pass

# 可选自动加载补丁
if os.environ.get("LHHC_AUTO_PATCH") == "1":
    try:
        import patch_ctabacktester  # type: ignore
        print("Loaded patch_ctabacktester via LHHC_AUTO_PATCH=1")
    except Exception as e:
        print(f"Patch load failed: {e}")
