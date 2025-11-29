# VN.PY CTA 回测引擎补丁

## 概述

本补丁解决了 VN.PY CTA 回测引擎的以下问题：

1. **策略加载问题**：修复自定义策略无法在 GUI 中显示的问题
2. **内存暴涨问题**：实现流式回测，避免一次性加载全量历史数据
3. **内存优化统计**：可选择不保存完整成交记录，进一步降低内存占用

## 功能特性

### ✅ 已实现功能

1. **策略加载修复**
   - 显示详细的策略加载异常信息
   - 支持多个可能的策略目录路径
   - 自动发现并加载 `DynamicHedgedRebateGridStrategy`

2. **流式回测**
   - 分块加载历史数据（默认 15 天一块）
   - 实时显示回测进度
   - 显著降低内存峰值占用

3. **内存优化统计开关**
   - GUI 中添加"内存优化统计"复选框
   - 开启时不保存完整 TradeData 对象
   - 仍能正确计算所有统计指标
   - 无法查看逐笔成交明细（权衡）

4. **非侵入式设计**
   - 不修改 site-packages 源码
   - 使用 monkey-patch 技术
   - 包升级不会覆盖补丁

## 文件说明

- `patch_ctabacktester.py` - 主补丁文件
- `sitecustomize.py` - Python 启动时自动加载补丁
- `start_vntrader_with_patches.py` - 带补丁的 VN Trader 启动器
- `test_strategy_loading.py` - 策略加载测试脚本
- `test_streaming_backtest.py` - 流式回测测试脚本

## 使用方法

### 方法一：使用启动器（推荐）

```bash
python start_vntrader_with_patches.py
```

### 方法二：手动导入补丁

在任何使用 VN.PY 的脚本开头添加：

```python
import patch_ctabacktester
```

### 方法三：自动加载（全局）

将 `sitecustomize.py` 放在 Python 路径中，补丁会在 Python 启动时自动加载。

## GUI 使用说明

1. 启动 VN Trader
2. 打开 "应用" → "CTA策略回测"
3. 在"交易策略"下拉框中选择 `DynamicHedgedRebateGridStrategy`
4. 配置回测参数
5. **可选**：勾选"内存优化统计"复选框（适用于大区间重负荷回测）
6. 点击"开始回测"

## 内存优化效果

- **标准模式**：保存所有成交记录，内存占用较高，可查看逐笔明细
- **优化模式**：只保存统计聚合，内存占用显著降低，无法查看逐笔明细

建议：
- 小区间回测：使用标准模式
- 大区间重负荷回测：使用优化模式

## 技术细节

### 补丁内容

1. **BacktesterEngine.load_strategy_class** - 修复策略加载
2. **BacktesterEngine.run_backtesting** - 实现流式回测
3. **DailyResult.add_trade** - 内存优化统计
4. **DailyResult.calculate_pnl** - 兼容优化模式的统计计算
5. **BacktesterManager.init_ui** - 添加 GUI 复选框

### 兼容性

- VN.PY 4.1+
- vnpy_ctastrategy 1.3.3+
- vnpy_ctabacktester
- Python 3.11+

## 注意事项

1. **数据依赖**：流式回测需要数据库中有相应的历史数据
2. **内存权衡**：内存优化模式无法查看逐笔成交明细
3. **补丁更新**：VN.PY 包升级后可能需要重新应用补丁
4. **测试建议**：建议先在小区间测试，确认功能正常后再用于大区间回测

## 故障排除

### 策略不显示
- 检查 strategies 目录是否存在
- 检查策略文件语法是否正确
- 查看控制台输出的详细错误信息

### 内存仍然过高
- 确认已勾选"内存优化统计"
- 检查策略本身是否有内存泄漏
- 考虑缩小回测区间

### 补丁不生效
- 确认补丁文件在正确位置
- 检查 Python 路径设置
- 重启 Python 进程

## 开发者信息

- 作者：Augment Agent
- 版本：1.0
- 更新日期：2025-08-19
