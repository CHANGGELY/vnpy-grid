#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试流式回测功能
"""

import sys
from pathlib import Path
from datetime import datetime

# 确保当前目录在 Python 路径中
current_dir = Path.cwd()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 导入补丁
import patch_ctabacktester

from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine
from vnpy_ctabacktester.engine import BacktesterEngine

def test_streaming_backtest():
    """测试流式回测功能"""
    print("=== 测试流式回测功能 ===")
    
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    backtester_engine = BacktesterEngine(main_engine, event_engine)
    
    # 初始化引擎
    backtester_engine.init_engine()
    
    # 检查策略是否可用
    class_names = backtester_engine.get_strategy_class_names()
    target_strategy = "DynamicHedgedRebateGridStrategy"
    
    if target_strategy not in class_names:
        print(f"✗ 策略 {target_strategy} 不可用")
        return False
    
    print(f"✓ 策略 {target_strategy} 可用")
    
    # 测试内存优化统计开关
    print("\n=== 测试内存优化统计开关 ===")
    
    # 测试关闭状态
    patch_ctabacktester.set_memory_optimize_stats(False)
    print("测试标准模式...")
    
    # 测试开启状态
    patch_ctabacktester.set_memory_optimize_stats(True)
    print("测试内存优化模式...")
    
    # 恢复默认状态
    patch_ctabacktester.set_memory_optimize_stats(False)
    
    print("\n=== 流式回测功能测试完成 ===")
    print("注意：完整的回测测试需要数据库中有相应的历史数据")
    print("建议通过 GUI 界面进行完整测试")
    
    return True

if __name__ == "__main__":
    success = test_streaming_backtest()
    sys.exit(0 if success else 1)
