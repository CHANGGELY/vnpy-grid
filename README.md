<p align="center">
  <img src="assets/logo.svg" alt="vnpy-grid logo" width="120" />
</p>

# vnpy-grid — 明星级开源量化网格与回测补丁集 | A star-quality grid toolkit for VN.PY

面向 VN.PY 生态的专业网格交易工具包与 CTA 回测引擎优化补丁。提供低内存流式回测、策略加载修复、可选的统计聚合模式，以及一套可复用的策略与数据工具，聚焦工程可用与开源协作体验。

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-black)
![CI](https://img.shields.io/github/actions/workflow/status/REPO_OWNER/vnpy-grid/ci.yml?branch=main)
![PyPI](https://img.shields.io/pypi/v/vnpy-grid?label=PyPI)
![Codecov](https://img.shields.io/codecov/c/github/REPO_OWNER/vnpy-grid?label=coverage)

## 为什么值得使用 | Why it matters

- 低内存流式回测：长区间、大数据量也能稳定运行。
- 策略加载增强：GUI 中稳定发现与注册自定义策略。
- 统计聚合开关：保留指标计算的同时大幅降低内存占用。
- 非侵入式补丁：不改动 site-packages，升级不丢失补丁。
- 结构清晰：`src/vnpy_grid` 提供策略、数据与工具三大模块。

- Streaming backtest with low memory footprint for long horizons
- Robust strategy discovery & registration in GUI
- Optional aggregated statistics mode to cut memory usage while keeping metrics
- Non-intrusive patches (no site-packages modifications)
- Clear structure across strategies, data and tools

## 安装 | Install

```powershell
python -X utf8 -m pip install -U pip
pip install -e .
```

依赖：`python>=3.11`，`vnpy>=2.4.0`。

Requirements: `python>=3.11`, `vnpy>=2.4.0`.

## 快速开始 | Quickstart

启动带补丁的 VN Trader：

```powershell
python start_vntrader_with_patches.py
```

或在脚本中启用补丁：

```python
import patch_ctabacktester
```

GUI 操作路径：应用 → CTA策略回测 → 选择 `DynamicHedgedRebateGridStrategy` → 配置参数 → 可选勾选“内存优化统计” → 开始回测。

GUI path: App → CTA Backtest → choose `DynamicHedgedRebateGridStrategy` → configure params → optionally check "Aggregated statistics" → start.

## 示例与工具 | Examples & tools

- 回测脚本：`src/vnpy_grid/tools/run_backtest_from_h5.py`
- 数据导入：`src/vnpy_grid/tools/import_h5_to_vnpy_sqlite.py`
- ETH/USDT 回测：`src/vnpy_grid/tools/run_backtest_ethusdt.py`
- 动态返利网格策略：`src/vnpy_grid/strategies/dynamic_hedged_rebate_grid.py`

示例脚本要求实际历史数据或可用的 H5/SQLite 数据源，避免使用虚构数据。请参见“数据准备”。

Examples require real historical data (H5/SQLite). No mock data.

## 数据准备 | Data preparation

- 若已有 H5 历史数据，可使用 `import_h5_to_vnpy_sqlite.py` 导入至 VN.PY 默认数据库。
- 若从交易所获取，可用官方 API 下载并写入 SQLite，再使用上述工具导入。

- If you have H5 data, import via `import_h5_to_vnpy_sqlite.py` into VN.PY DB.
- If fetching from exchange, download via official API, write to SQLite, then import.

## 主要特性详情 | Key features

- 流式回测：按时间分块加载数据（默认 15 天），实时进度显示，显著降低峰值内存。
- 统计聚合模式：仅保留计算所需聚合统计，减少对象保留，提高稳定性。
- 策略发现与注册：多目录扫描与异常信息输出，便于快速定位问题。

- Streaming backtest by time chunks (default 15 days) with progress
- Aggregated statistics mode retains metrics while cutting memory
- Strategy discovery with multiple search paths and detailed errors

## 项目结构 | Project layout

```
src/vnpy_grid/
  data/        数据导入与转换
  strategies/  可复用策略
  tools/       回测与数据处理脚本
```

## 与 VN.PY 集成 | Integration with VN.PY

- 运行 GUI：`python start_vntrader_with_patches.py`
- 全局启用：将 `sitecustomize.py` 放入 Python 路径以自动加载补丁。

- Run GUI: `python start_vntrader_with_patches.py`
- Global auto-load: place `sitecustomize.py` on `PYTHONPATH`

## 补丁文档 | Patch docs

详见《VN.PY CTA 回测引擎补丁》：`README_PATCHES.md`

## 路线图 | Roadmap

- 提升测试覆盖率与回测稳定性。
- 增强跨交易所数据导入与校验。
- 发布 PyPI 包与版本化文档站点。

- Improve test coverage and robustness
- Enhance multi-exchange data import & validation
- Publish to PyPI and host versioned docs

## 贡献 | Contributing

欢迎提交 Issue 与 Pull Request。请先阅读 `CONTRIBUTING.md`，并遵守 `CODE_OF_CONDUCT.md`。

Issues & PRs welcome. Please read `CONTRIBUTING.md` and follow `CODE_OF_CONDUCT.md`.

## 安全 | Security

安全问题请参考 `SECURITY.md`，并通过私信渠道报告。

See `SECURITY.md` and report via private channels.

## 许可协议 | License

MIT License。详情见 `LICENSE`。

MIT License. See `LICENSE`.
